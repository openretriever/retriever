import contextlib
from typing import Any, Dict, Optional, List

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, CallToolResult
    _MCP_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as exc:  # Optional dependency for retriever.context
    ClientSession = Any  # type: ignore[assignment]
    StdioServerParameters = Any  # type: ignore[assignment]
    Tool = Any  # type: ignore[assignment]
    CallToolResult = Any  # type: ignore[assignment]
    stdio_client = None  # type: ignore[assignment]
    _MCP_IMPORT_ERROR = exc

from .config import MCPConfig


def _require_mcp() -> None:
    if _MCP_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(
            "retriever.context requires the optional 'mcp' dependency. "
            "Install retriever with the '[mcp]' extra or add the Python 'mcp' package to your environment."
        ) from _MCP_IMPORT_ERROR


class MCPClient:
    """
    A client to interact with multiple MCP servers.
    """
    def __init__(self):
        _require_mcp()
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack = contextlib.AsyncExitStack()

    @classmethod
    async def from_config(cls, config_path: Optional[str] = None) -> "MCPClient":
        """
        Create and connect an MCPClient from a configuration file.
        """
        client = cls()
        config = MCPConfig.load(config_path)

        try:
            for name, server_cfg in config.items():
                await client.connect_stdio(
                    name,
                    server_cfg.command,
                    server_cfg.args,
                    server_cfg.env,
                )
        except Exception as e:
            await client.close()
            raise e

        return client

    async def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tools from all connected servers as OpenAI-compatible schemas.
        """
        schemas = []
        for name, session in self._sessions.items():
            result = await session.list_tools()
            for tool in result.tools:
                schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                schemas.append(schema)
        return schemas

    async def connect_stdio(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Connect to an MCP server via stdio.
        """
        _require_mcp()
        server_params = StdioServerParameters(command=command, args=args, env=env)

        transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        read, write = transport

        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        self._sessions[name] = session
        print(f"Connected to MCP server '{name}'")

    async def list_tools(self, server_name: str) -> List[Tool]:
        """List tools available on a connected server."""
        if server_name not in self._sessions:
            raise ValueError(f"Server '{server_name}' not connected")

        result = await self._sessions[server_name].list_tools()
        return result.tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a tool on a connected server."""
        if server_name not in self._sessions:
            raise ValueError(f"Server '{server_name}' not connected")

        return await self._sessions[server_name].call_tool(tool_name, arguments)

    async def close(self):
        """Close all connections."""
        await self._exit_stack.aclose()
        self._sessions.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
