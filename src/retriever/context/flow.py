import asyncio
import threading
from typing import Any, Dict, Optional
from dataclasses import dataclass

from retriever import Flow
from retriever.error import FlowError, ErrCode
from retriever.flow import flow_io
from retriever.context import MCPClient

import json

@flow_io
@dataclass
class MCPRequest:
    """Request to invoke an MCP tool. Serialized as JSON string for atomicity."""
    content: str

@flow_io
@dataclass
class MCPResponse:
    """Response from an MCP tool."""
    content: str
    error: Optional[str] = None

class MCPToolFlow(Flow[MCPRequest, MCPResponse]):
    """
    A Flow that wraps a connection to an MCP server.
    Input: Request to call a tool
    Output: Result of the tool call
    """
    def __init__(self, server_name: str, config_path: str):
        super().__init__()
        self.server_name = server_name
        self.config_path = config_path
        self.mcp: MCPClient = None
        self._loop = None
        self._thread = None

    def init_config(self) -> dict:
        return {"server_name": self.server_name, "config_path": self.config_path}

    def reset(self):
        """Initialize connection in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        future = asyncio.run_coroutine_threadsafe(self._async_connect(), self._loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            raise FlowError(ErrCode.FLOW_RUNTIME_ERROR, f"MCP Connect failed: {e}")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _async_connect(self):
        self.mcp = await MCPClient.from_config(self.config_path)
        print(f"MCPToolFlow: Connected to '{self.server_name}'")

    def step(self, request: MCPRequest) -> MCPResponse:
        """Synchronous step that delegates to async client."""
        if not self._loop:
            raise FlowError(ErrCode.FLOW_NOT_INITIALIZED, "MCPToolFlow not initialized")
            
        future = asyncio.run_coroutine_threadsafe(self._async_step(request), self._loop)
        return future.result()

    async def _async_step(self, request: MCPRequest) -> MCPResponse:
        try:
            payload = json.loads(request.content)
            tool_name = payload["tool_name"]
            arguments = payload.get("args", {})
            
            print(f"[MCPFlow] Calling {tool_name}({json.dumps(arguments)})...")
            
            result = await self.mcp.call_tool(self.server_name, tool_name, arguments)
            # Simplification: just taking first text content
            text = result.content[0].text if result.content else ""
            return MCPResponse(content=text)
        except Exception as e:
            return MCPResponse(content="", error=str(e))

    def finalize(self):
        """Clean up background loop and connection."""
        if self.mcp and self._loop and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self.mcp.close(), self._loop)
                future.result(timeout=2)
            except Exception:
                pass
        
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        if self._thread:
            self._thread.join(timeout=1)
        
        self.mcp = None
        self._loop = None
        self._thread = None

    # Backward compatibility helpers for manual asyncio usage (like 02_reactive_flow.py was doing)
    # We map setup/teardown to reset/finalize, but keep them async-compatible conceptually.
    # For compatibility with 02 example code structure:
    async def setup(self):
        # Allow async setup for manual scripts, but just call reset.
        self.reset()

    async def teardown(self):
        self.finalize()
