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

        /* Tabs */
        .tabs {
            display: flex; gap: 2px; margin-bottom: 20px;
            background: #0f3460; border-radius: 8px 8px 0 0; overflow: hidden;
        }
        .tab {
            padding: 12px 24px; cursor: pointer; background: #16213e;
            border: none; color: #aaa; font-size: 14px; font-weight: 500;
            transition: background 0.2s, color 0.2s;
        }
        .tab:hover { background: #1a2844; color: #eee; }
        .tab.active { background: #0f3460; color: #4fc3f7; border-bottom: 3px solid #4fc3f7; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }
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

        /* Logs tab */
        .logs-controls {
            background: #16213e; padding: 15px; border-radius: 8px;
            margin-bottom: 15px; display: flex; gap: 10px; align-items: center;
            flex-wrap: wrap;
        }
        .logs-controls select, .logs-controls input {
            padding: 8px 12px; border: 1px solid #0f3460; border-radius: 5px;
            background: #0f3460; color: #eee; font-size: 13px;
        }
        .logs-controls label {
            display: flex; align-items: center; gap: 5px; font-size: 13px;
        }
        .logs-controls button {
            padding: 8px 16px; font-size: 13px;
        }

        #logs-container {
            height: 600px; overflow-y: auto; font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px; background: #0d1117; color: #c9d1d9; padding: 15px;
            border-radius: 8px; line-height: 1.5;
        }
        .log-entry { margin: 2px 0; white-space: pre-wrap; word-wrap: break-word; }
        .log-entry .time { color: #8b949e; }
        .log-entry .node { color: #79c0ff; font-weight: 500; }
        .log-entry .level { font-weight: bold; margin: 0 5px; }
        .log-entry .level.INFO { color: #3fb950; }
        .log-entry .level.WARN { color: #d29922; }
        .log-entry .level.ERROR { color: #f85149; }
        .log-entry .level.DEBUG { color: #a371f7; }
        .log-entry .message { color: #c9d1d9; }

        #logs-container::-webkit-scrollbar { width: 10px; }
        #logs-container::-webkit-scrollbar-track { background: #161b22; }
        #logs-container::-webkit-scrollbar-thumb { background: #30363d; border-radius: 5px; }
        #logs-container::-webkit-scrollbar-thumb:hover { background: #484f58; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Retriever Pipeline Dashboard</h1>

        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('logs')">Logs</button>
        </div>

        <!-- Overview Tab -->
        <div id="overview" class="tab-content active">
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

        <!-- Logs Tab -->
        <div id="logs" class="tab-content">
            <div class="logs-controls">
                <select id="node-filter">
                    <option value="">All Flows</option>
                </select>
                <select id="level-filter">
                    <option value="">All Levels</option>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARN">WARN</option>
                    <option value="ERROR">ERROR</option>
                </select>
                <button onclick="clearLogs()" class="btn-reset">Clear</button>
                <button onclick="exportLogs()" class="btn-resume">Export</button>
                <label>
                    <input type="checkbox" id="auto-scroll" checked>
                    Auto-scroll
                </label>
            </div>
            <div id="logs-container"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let logsWs = null;
        let allLogs = [];
        let nodeIds = new Set();

        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));

            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

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

        // Logs WebSocket
        function connectLogs() {
            logsWs = new WebSocket(`ws://${window.location.host}/ws/logs`);

            logsWs.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'history') {
                    allLogs = data.logs;
                    renderLogs();
                    updateNodeFilter();
                } else if (data.type === 'log') {
                    allLogs.push(data.data);
                    if (allLogs.length > 10000) allLogs.shift();
                    appendLog(data.data);
                    updateNodeFilter();
                }
            };

            logsWs.onclose = () => {
                setTimeout(connectLogs, 1000);
            };
        }

        function renderLogs() {
            const container = document.getElementById('logs-container');
            container.innerHTML = '';
            allLogs.forEach(log => appendLog(log));
        }

        function appendLog(log) {
            const container = document.getElementById('logs-container');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="time">${log.time_str}</span> <span class="node">[${log.node_id}]</span> <span class="level ${log.level}">${log.level}</span> <span class="message">${escapeHtml(log.message)}</span>`;
            container.appendChild(entry);

            if (document.getElementById('auto-scroll').checked) {
                container.scrollTop = container.scrollHeight;
            }
        }

        function updateNodeFilter() {
            const select = document.getElementById('node-filter');
            const currentValue = select.value;

            // Extract unique node IDs
            allLogs.forEach(log => nodeIds.add(log.node_id));

            // Rebuild options
            select.innerHTML = '<option value="">All Flows</option>';
            Array.from(nodeIds).sort().forEach(nodeId => {
                const option = document.createElement('option');
                option.value = nodeId;
                option.textContent = nodeId;
                select.appendChild(option);
            });

            select.value = currentValue;
        }

        function clearLogs() {
            allLogs = [];
            document.getElementById('logs-container').innerHTML = '';
        }

        function exportLogs() {
            const text = allLogs.map(l => `${l.time_str} [${l.node_id}] ${l.level} ${l.message}`).join('\\n');
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `logs_${Date.now()}.txt`;
            a.click();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Apply filters
        document.getElementById('node-filter').addEventListener('change', function() {
            applyFilters();
        });

        document.getElementById('level-filter').addEventListener('change', function() {
            applyFilters();
        });

        function applyFilters() {
            const nodeFilter = document.getElementById('node-filter').value;
            const levelFilter = document.getElementById('level-filter').value;

            const filtered = allLogs.filter(log => {
                if (nodeFilter && log.node_id !== nodeFilter) return false;
                if (levelFilter && log.level !== levelFilter) return false;
                return true;
            });

            const container = document.getElementById('logs-container');
            container.innerHTML = '';
            filtered.forEach(log => appendLog(log));
        }

        connect();
        connectLogs();
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
            print(f"[WebDashboard] Started at http://{self.host}:{self.port}")
