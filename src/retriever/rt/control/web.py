"""
Web-based control dashboard for Retriever pipelines.

Provides:
- Real-time status monitoring via WebSocket
- Control buttons (pause/resume/reset)
- Flow output visualization
- State inspection
"""

from typing import Any, Dict, List, Optional, Set
import asyncio
import json
import time
import threading

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from retriever.rt.control.output_capture import LogBuffer, LogEntry
from retriever.rt.control.channel import ControlCommand


def _print_dashboard_banner(url: str, config_info: Optional[Dict[str, Any]] = None) -> None:
    """Print prominent dashboard banner with URL and config info.

    Args:
        url: Dashboard URL
        config_info: Optional configuration information to display
    """
    # ANSI color codes
    BOLD = "\033[1m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    GREEN = "\033[92m"

    # Try to generate QR code
    qr_lines = []
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make()

        # Get QR code as text
        matrix = qr.get_matrix()
        for row in matrix:
            line = ""
            for cell in row:
                line += "██" if cell else "  "
            qr_lines.append(line)
    except ImportError:
        qr_lines = ["(Install qrcode for mobile QR: pip install qrcode)"]

    # Build banner
    print()
    print("=" * 70)
    print(f"{BOLD}{BLUE}🎮 Pipeline Control Dashboard{RESET}")
    print("=" * 70)
    print()
    print(f"{BOLD}{CYAN}Dashboard URL:{RESET} {BOLD}{BLUE}{url}{RESET}")
    print()

    if config_info:
        print(f"{BOLD}Configuration:{RESET}")
        for key, value in config_info.items():
            print(f"  • {key}: {GREEN}{value}{RESET}")
        print()

    if len(qr_lines) > 1:
        print(f"{BOLD}Mobile Access (Scan QR Code):{RESET}")
        for line in qr_lines:
            print(f"  {line}")
        print()
    else:
        print(f"{CYAN}{qr_lines[0]}{RESET}")
        print()

    print(f"{BOLD}Controls:{RESET}")
    print(f"  • Web: Visit the URL above")
    print(f"  • Individual Flow Control: Pause/resume/reset specific flows")
    print(f"  • Global Controls: Manage all flows at once")
    print(f"  • Live Logs: Real-time flow output streaming")
    print()
    print("=" * 70)
    print()


class WebDashboard:
    """
    FastAPI-based web dashboard for pipeline control.

    Features:
    - Real-time status via WebSocket
    - Control API endpoints
    - HTML dashboard UI
    - Flow output streaming (optional)
    """

    def __init__(
        self,
        controller: "PipelineController",
        host: str = "0.0.0.0",
        port: int = 8080,
        config_info: Optional[Dict[str, Any]] = None,
    ):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI and uvicorn required: pip install fastapi uvicorn")

        self.controller = controller
        self.host = host
        self.port = port
        self.config_info = config_info or {}

        self.app = FastAPI(title="Retriever Dashboard")
        self._setup_routes()

        # Connected WebSocket clients
        self._clients: Set[WebSocket] = set()
        self._log_clients: Set[WebSocket] = set()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._log_collector_task: Optional[asyncio.Task] = None
        self._server_thread: Optional[threading.Thread] = None

        # Log buffer for output capture
        self.log_buffer = LogBuffer(maxlen=10000)

    def _setup_routes(self) -> None:
        """Configure FastAPI routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            return self._get_dashboard_html()

        @self.app.get("/api/status")
        async def get_status():
            status = self.controller.get_state()
            return status.to_dict()

        @self.app.post("/api/pause")
        async def pause(node: Optional[str] = None):
            success = self.controller.pause(node)
            return {"success": success, "node": node}

        @self.app.post("/api/resume")
        async def resume(node: Optional[str] = None):
            success = self.controller.resume(node)
            return {"success": success, "node": node}

        @self.app.post("/api/reset")
        async def reset(node: Optional[str] = None):
            success = self.controller.reset(node)
            return {"success": success, "node": node}

        @self.app.post("/api/stop")
        async def stop():
            success = self.controller.stop()
            return {"success": success}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._clients.add(websocket)
            try:
                while True:
                    # Keep connection alive, handle client messages
                    data = await websocket.receive_text()
                    msg = json.loads(data)

                    if msg.get("action") == "pause":
                        self.controller.pause(msg.get("node"))
                    elif msg.get("action") == "resume":
                        self.controller.resume(msg.get("node"))
                    elif msg.get("action") == "reset":
                        self.controller.reset(msg.get("node"))
            except WebSocketDisconnect:
                self._clients.discard(websocket)

        @self.app.websocket("/ws/logs")
        async def logs_websocket(websocket: WebSocket):
            await websocket.accept()
            self._log_clients.add(websocket)

            try:
                # Send recent log history
                recent = self.log_buffer.get_recent(100)
                await websocket.send_json({
                    "type": "history",
                    "logs": [entry.to_dict() for entry in recent]
                })

                # Keep connection alive and handle client filter requests
                while True:
                    data = await websocket.receive_json()
                    # Handle filter requests if needed
                    if data.get("action") == "filter":
                        node_id = data.get("node_id")
                        level = data.get("level")
                        filtered = self.log_buffer.filter(node_id=node_id, level=level)
                        await websocket.send_json({
                            "type": "filtered",
                            "logs": [entry.to_dict() for entry in filtered]
                        })

            except WebSocketDisconnect:
                self._log_clients.discard(websocket)

    async def _broadcast_status(self) -> None:
        """Periodically broadcast status to all WebSocket clients."""
        while True:
            if self._clients:
                try:
                    status = self.controller.get_state()
                    data = json.dumps({
                        "type": "status",
                        "data": status.to_dict()
                    })

                    # Broadcast to all clients
                    disconnected = set()
                    for client in self._clients:
                        try:
                            await client.send_text(data)
                        except Exception:
                            disconnected.add(client)

                    self._clients -= disconnected
                except Exception:
                    pass

            await asyncio.sleep(0.5)

    async def _collect_logs(self) -> None:
        """
        Collect log messages from control channel and broadcast to log clients.

        Polls the control channel for LOG_OUTPUT messages and forwards them
        to all connected WebSocket clients on /ws/logs.
        """
        while True:
            try:
                # Poll control channel for LOG_OUTPUT messages
                message = self.controller._channel.receive_command(timeout=0.01)

                if message and message.command == ControlCommand.LOG_OUTPUT:
                    # Create log entry
                    entry = LogEntry(
                        timestamp=message.payload["timestamp"],
                        node_id=message.target,
                        level=message.payload["level"],
                        message=message.payload["message"]
                    )

                    # Add to buffer
                    self.log_buffer.add(entry)

                    # Broadcast to all connected log clients
                    if self._log_clients:
                        log_data = json.dumps({
                            "type": "log",
                            "data": entry.to_dict()
                        })

                        disconnected = set()
                        for client in self._log_clients:
                            try:
                                await client.send_text(log_data)
                            except Exception:
                                disconnected.add(client)

                        self._log_clients -= disconnected

            except Exception:
                pass

            await asyncio.sleep(0.01)

    def _get_dashboard_html(self) -> str:
        """Return the dashboard HTML."""
        import os
        template_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
        try:
            with open(template_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return "<html><body><h1>Dashboard template not found</h1></body></html>"

    def start(self, blocking: bool = True) -> None:
        """Start the web dashboard server."""
        async def start_server():
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning",
            )
            server = uvicorn.Server(config)

            # Start broadcast tasks
            self._broadcast_task = asyncio.create_task(self._broadcast_status())
            self._log_collector_task = asyncio.create_task(self._collect_logs())

            await server.serve()

        if blocking:
            asyncio.run(start_server())
        else:
            def run_in_thread():
                asyncio.run(start_server())

            self._server_thread = threading.Thread(target=run_in_thread, daemon=True)
            self._server_thread.start()

            # Print prominent dashboard banner
            url = self.get_url()
            _print_dashboard_banner(url, self.config_info)

    def get_url(self) -> str:
        """Get the dashboard URL."""
        # Use localhost if bound to 0.0.0.0 for better user experience
        host = "localhost" if self.host == "0.0.0.0" else self.host
        return f"http://{host}:{self.port}"
