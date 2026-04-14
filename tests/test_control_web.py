"""Tests for the web dashboard control surface."""

import asyncio
import json
import socket
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from retriever.rt.control.channel import ControlCommand, ControlMessage
from retriever.rt.control.output_capture import LogEntry
from retriever.rt.control.web import WebDashboard


class _DummyStatus:
    def to_dict(self):
        return {
            "name": "dashboard-test",
            "state": "running",
            "node_count": 1,
            "nodes": {},
            "timestamp": time.time(),
        }


class _DummyChannel:
    def __init__(self):
        self._logs = []

    def push_log(self, target="node", level="INFO", message="hello"):
        self._logs.append(
            ControlMessage(
                command=ControlCommand.LOG_OUTPUT,
                target=target,
                payload={"timestamp": time.time(), "level": level, "message": message},
            )
        )

    def receive_log(self, timeout=0.0):
        if self._logs:
            return self._logs.pop(0)
        return None


class _DummyController:
    def __init__(self):
        self.calls = []
        self._channel = _DummyChannel()

    def get_state(self):
        return _DummyStatus()

    def pause(self, node=None):
        self.calls.append(("pause", node))
        return True

    def resume(self, node=None):
        self.calls.append(("resume", node))
        return True

    def reset(self, node=None):
        self.calls.append(("reset", node))
        return True

    def stop(self):
        self.calls.append(("stop", None))
        return True


class _DummyWebSocket:
    def __init__(self):
        self.messages = []

    async def send_text(self, data):
        self.messages.append(json.loads(data))


def _make_dashboard():
    return WebDashboard(_DummyController(), host="127.0.0.1", port=8123)


class TestWebDashboardRoutes:
    def test_root_and_status_routes(self):
        dashboard = _make_dashboard()
        client = TestClient(dashboard.app)

        root = client.get("/")
        assert root.status_code == 200
        assert "Pipeline Control Dashboard" in root.text

        status = client.get("/api/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["name"] == "dashboard-test"
        assert payload["state"] == "running"

    def test_control_routes_call_controller(self):
        dashboard = _make_dashboard()
        client = TestClient(dashboard.app)

        assert client.post("/api/pause", params={"node": "camera"}).json()["success"] is True
        assert client.post("/api/resume", params={"node": "camera"}).json()["success"] is True
        assert client.post("/api/reset", params={"node": "camera"}).json()["success"] is True
        assert client.post("/api/stop").json()["success"] is True

        assert dashboard.controller.calls == [
            ("pause", "camera"),
            ("resume", "camera"),
            ("reset", "camera"),
            ("stop", None),
        ]


class TestWebDashboardLogs:
    def test_logs_websocket_history_and_filter(self):
        dashboard = _make_dashboard()
        dashboard.log_buffer.add(LogEntry(time.time(), "cam", "INFO", "frame"))
        dashboard.log_buffer.add(LogEntry(time.time(), "planner", "WARN", "stale"))
        client = TestClient(dashboard.app)

        with client.websocket_connect("/ws/logs") as ws:
            history = ws.receive_json()
            assert history["type"] == "history"
            assert len(history["logs"]) == 2

            ws.send_json({"action": "filter", "node_id": "planner", "level": "WARN"})
            filtered = ws.receive_json()
            assert filtered["type"] == "filtered"
            assert len(filtered["logs"]) == 1
            assert filtered["logs"][0]["node_id"] == "planner"

        assert not dashboard._log_clients

    def test_control_websocket_cleans_up_on_close(self):
        dashboard = _make_dashboard()
        client = TestClient(dashboard.app)

        with client.websocket_connect("/ws") as ws:
            ws.send_text('{"action": "pause", "node": "camera"}')

        assert dashboard.controller.calls == [("pause", "camera")]
        assert not dashboard._clients


class TestWebDashboardHelpers:
    def test_get_url_uses_localhost_for_wildcard_host(self):
        dashboard = WebDashboard(_DummyController(), host="0.0.0.0", port=8080)
        assert dashboard.get_url() == "http://localhost:8080"

    def test_find_available_port_falls_forward(self):
        dashboard = WebDashboard(_DummyController(), host="127.0.0.1", port=8080)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        busy_port = sock.getsockname()[1]
        try:
            port = dashboard._find_available_port(busy_port, max_tries=5)
            assert port is not None
            assert port != busy_port
        finally:
            sock.close()


class TestWebDashboardBackgroundTasks:
    def test_broadcast_status_streams_current_state(self):
        dashboard = _make_dashboard()
        ws = _DummyWebSocket()
        dashboard._clients.add(ws)

        async def exercise():
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(dashboard._broadcast_status(), timeout=0.05)

        asyncio.run(exercise())
        assert ws.messages
        assert ws.messages[0]["type"] == "status"
        assert ws.messages[0]["data"]["name"] == "dashboard-test"

    def test_log_collector_streams_channel_logs(self):
        dashboard = _make_dashboard()
        ws = _DummyWebSocket()
        dashboard._log_clients.add(ws)
        dashboard.controller._channel.push_log(target="camera", level="WARN", message="late frame")

        async def exercise():
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(dashboard._collect_logs(), timeout=0.05)

        asyncio.run(exercise())
        assert ws.messages
        assert ws.messages[0]["type"] == "log"
        assert ws.messages[0]["data"]["node_id"] == "camera"
        assert ws.messages[0]["data"]["level"] == "WARN"
