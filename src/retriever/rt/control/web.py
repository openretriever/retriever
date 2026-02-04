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
    ):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI and uvicorn required: pip install fastapi uvicorn")

        self.controller = controller
        self.host = host
        self.port = port

        self.app = FastAPI(title="Retriever Dashboard")
        self._setup_routes()

        # Connected WebSocket clients
        self._clients: Set[WebSocket] = set()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._server_thread: Optional[threading.Thread] = None

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

    def _get_dashboard_html(self) -> str:
        """Return the dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Retriever Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #eee; padding: 20px;
        }
        h1 { margin-bottom: 20px; color: #4fc3f7; }
        .container { max-width: 1200px; margin: 0 auto; }
        .controls {
            display: flex; gap: 10px; margin-bottom: 20px;
            background: #16213e; padding: 15px; border-radius: 8px;
        }
        button {
            padding: 10px 20px; border: none; border-radius: 5px;
            cursor: pointer; font-size: 14px; font-weight: 500;
            transition: transform 0.1s, opacity 0.2s;
        }
        button:hover { transform: scale(1.02); }
        button:active { transform: scale(0.98); }
        .btn-pause { background: #ff9800; color: #000; }
        .btn-resume { background: #4caf50; color: #fff; }
        .btn-reset { background: #2196f3; color: #fff; }
        .btn-stop { background: #f44336; color: #fff; }

        .status-bar {
            background: #16213e; padding: 15px; border-radius: 8px;
            margin-bottom: 20px; display: flex; justify-content: space-between;
        }
        .status-bar .state { font-size: 18px; font-weight: bold; }
        .state-running { color: #4caf50; }
        .state-paused { color: #ff9800; }
        .state-stopped { color: #f44336; }

        .nodes-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
        }
        .node-card {
            background: #16213e; padding: 15px; border-radius: 8px;
            border-left: 4px solid #4fc3f7;
        }
        .node-card.paused { border-left-color: #ff9800; }
        .node-card.stopped { border-left-color: #f44336; }
        .node-card.error { border-left-color: #f44336; background: #2d1b1b; }

        .node-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 10px;
        }
        .node-name { font-weight: bold; font-size: 16px; }
        .node-state {
            padding: 3px 8px; border-radius: 4px; font-size: 12px;
            text-transform: uppercase;
        }
        .node-state.running { background: #1b5e20; }
        .node-state.paused { background: #e65100; }
        .node-state.stopped { background: #b71c1c; }

        .node-stats { color: #aaa; font-size: 13px; }
        .node-stats span { margin-right: 15px; }

        .node-actions { margin-top: 10px; display: flex; gap: 5px; }
        .node-actions button { padding: 5px 10px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Retriever Pipeline Dashboard</h1>

        <div class="controls">
            <button class="btn-pause" onclick="pauseAll()">Pause All</button>
            <button class="btn-resume" onclick="resumeAll()">Resume All</button>
            <button class="btn-reset" onclick="resetAll()">Reset All</button>
            <button class="btn-stop" onclick="stopPipeline()">Stop Pipeline</button>
        </div>

        <div class="status-bar">
            <div>
                Pipeline: <strong id="pipeline-name">-</strong>
            </div>
            <div class="state" id="pipeline-state">-</div>
            <div>
                Nodes: <span id="node-count">0</span>
            </div>
        </div>

        <div class="nodes-grid" id="nodes-container"></div>
    </div>

    <script>
        let ws = null;

        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'status') {
                    updateStatus(msg.data);
                }
            };

            ws.onclose = () => {
                setTimeout(connect, 1000);
            };
        }

        function updateStatus(status) {
            document.getElementById('pipeline-name').textContent = status.name;
            document.getElementById('node-count').textContent = status.node_count;

            const stateEl = document.getElementById('pipeline-state');
            stateEl.textContent = status.state.toUpperCase();
            stateEl.className = 'state state-' + status.state;

            const container = document.getElementById('nodes-container');
            container.innerHTML = '';

            for (const [nodeId, node] of Object.entries(status.nodes)) {
                const card = document.createElement('div');
                card.className = 'node-card ' + node.state;
                card.innerHTML = `
                    <div class="node-header">
                        <span class="node-name">${nodeId}</span>
                        <span class="node-state ${node.state}">${node.state}</span>
                    </div>
                    <div class="node-stats">
                        <span>Class: ${node.flow_class}</span>
                        <span>Steps: ${node.step_count}</span>
                    </div>
                    <div class="node-actions">
                        <button onclick="pauseNode('${nodeId}')">Pause</button>
                        <button onclick="resumeNode('${nodeId}')">Resume</button>
                        <button onclick="resetNode('${nodeId}')">Reset</button>
                    </div>
                `;
                container.appendChild(card);
            }
        }

        function sendAction(action, node = null) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action, node }));
            }
        }

        function pauseAll() { sendAction('pause'); }
        function resumeAll() { sendAction('resume'); }
        function resetAll() { sendAction('reset'); }
        function pauseNode(node) { sendAction('pause', node); }
        function resumeNode(node) { sendAction('resume', node); }
        function resetNode(node) { sendAction('reset', node); }

        async function stopPipeline() {
            if (confirm('Stop the pipeline?')) {
                await fetch('/api/stop', { method: 'POST' });
            }
        }

        connect();
    </script>
</body>
</html>
        """

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

            # Start broadcast task
            self._broadcast_task = asyncio.create_task(self._broadcast_status())

            await server.serve()

        if blocking:
            asyncio.run(start_server())
        else:
            def run_in_thread():
                asyncio.run(start_server())

            self._server_thread = threading.Thread(target=run_in_thread, daemon=True)
            self._server_thread.start()
            print(f"[WebDashboard] Started at http://{self.host}:{self.port}")
