from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from multiprocessing import Queue
from typing import Optional

import numpy as np
import pytest
import retriever

from retriever.config import VizConfig
from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from retriever.ir.core import IR, IRNode, IRVizPolicy
from retriever.lib import rerun as rerun_lib
from retriever.rt.backend.dora.channel import DoraPublisher
from retriever.rt.backend.multiprocessing.channel import MPChannel
from retriever.rt.runtime import execute_ir


@io
@dataclass
class SampleOut:
    value: int
    image: np.ndarray
    label: Optional[str] = None


@io
@dataclass
class TickOut:
    value: int


class TickSource(Flow[None, TickOut]):
    def step(self, _):  # type: ignore[override]
        return TickOut(value=1)


class Drain(Flow[TickOut, None]):
    def step(self, input: TickOut) -> None:
        return None


def _install_fake_rerun(monkeypatch):
    state = {
        "inits": [],
        "connects": [],
        "times": [],
        "logs": [],
    }

    # Keep tests isolated from prior elapsed-time state in the local rerun module.
    if hasattr(rerun_lib, "reset_pipeline_time"):
        rerun_lib.reset_pipeline_time()

    rerun_mod = types.ModuleType("rerun")
    archetypes_mod = types.ModuleType("rerun.archetypes")

    def init(app_id, spawn=False, recording_id=None):
        state["inits"].append(
            {
                "app_id": app_id,
                "spawn": spawn,
                "recording_id": recording_id,
            }
        )

    def connect_grpc(address=None):
        state["connects"].append(address)

    def set_time(timeline, *, duration=None, timestamp=None, sequence=None):
        state["times"].append(
            {
                "timeline": timeline,
                "duration": duration,
                "timestamp": timestamp,
                "sequence": sequence,
            }
        )

    def log(path, payload):
        state["logs"].append((path, payload))

    rerun_mod.init = init
    rerun_mod.connect_grpc = connect_grpc
    rerun_mod.set_time = set_time
    rerun_mod.log = log
    class _FakeImage:
        def __init__(self, value):
            self._shape = np.asarray(value).shape
            self.compress_calls = []
        def compress(self, **kwargs):
            self.compress_calls.append(kwargs)
            return ("Image", self._shape)
        def __iter__(self):
            return iter(("Image", self._shape))
    rerun_mod.Image = _FakeImage
    rerun_mod.Tensor = lambda value: ("Tensor", np.asarray(value).shape)
    rerun_mod.TextLog = lambda value: ("TextLog", str(value))
    rerun_mod.BarChart = lambda value: ("BarChart", list(value))
    rerun_mod.spawn = (
        lambda *args, **kwargs: state.setdefault("spawns", []).append((args, kwargs))
    )
    rerun_mod.disconnect = lambda: state.setdefault("disconnects", 0) or None
    rerun_mod._retriever_env_connected = False

    archetypes_mod.Scalars = lambda value: ("Scalars", value)

    monkeypatch.setitem(sys.modules, "rerun", rerun_mod)
    monkeypatch.setitem(sys.modules, "rerun.archetypes", archetypes_mod)
    monkeypatch.setattr(rerun_lib, "rr", None)
    return state


def test_log_value_from_env_logs_plain_io_dataclass_fields(monkeypatch):
    state = _install_fake_rerun(monkeypatch)
    monkeypatch.setenv("RERUN_CONNECT_ADDR", "127.0.0.1:9876")
    monkeypatch.setenv("RERUN_APP_ID", "rerun_test")
    monkeypatch.setenv("RERUN_RECORDING_ID", "shared-recording")

    out = SampleOut(value=7, image=np.zeros((4, 5, 3), dtype=np.uint8), label=None)

    assert rerun_lib.log_value_from_env(
        "flows/source/output",
        out,
        time_seconds=1.25,
        sequence=3,
    )

    assert state["inits"] == [
        {
            "app_id": "rerun_test",
            "spawn": False,
            "recording_id": "shared-recording",
        }
    ]
    assert state["connects"] == ["rerun+http://127.0.0.1:9876/proxy"]

    logged_paths = [path for path, _payload in state["logs"]]
    assert "flows/source/output/value" in logged_paths
    assert "flows/source/output/image" in logged_paths
    assert "flows/source/output/label" not in logged_paths

    timelines = {
        (row["timeline"], row["sequence"], row["timestamp"], row["duration"])
        for row in state["times"]
    }
    assert ("step", 3, None, None) in timelines
    assert ("retriever_time", None, None, 0.0) in timelines
    image_logs = [payload for path, payload in state["logs"] if path.endswith("/image")]
    assert image_logs


def test_log_image_falls_back_when_compress_is_unavailable(monkeypatch):
    class _NoCompressImage:
        def __init__(self, value):
            self.shape = np.asarray(value).shape

    class _FakeRR:
        def __init__(self):
            self.logged = []

        Image = _NoCompressImage

        def log(self, path, payload):
            self.logged.append((path, payload))

    rr_module = _FakeRR()
    rerun_lib._log_image(rr_module, "camera/frame", np.zeros((2, 3, 3), dtype=np.uint8))
    assert rr_module.logged
    path, payload = rr_module.logged[0]
    assert path == "camera/frame"
    assert isinstance(payload, _NoCompressImage)


def test_mpchannel_put_one_emits_worker_rerun_log(monkeypatch):
    calls = []

    def fake_log_value_from_env(path, value, *, time_seconds=None, sequence=None, fields=None):
        calls.append((path, value, time_seconds, sequence, fields))
        return True

    monkeypatch.setattr(
        "retriever.rt.backend.multiprocessing.channel.log_value_from_env",
        fake_log_value_from_env,
    )

    queue = Queue()
    try:
        channel = MPChannel(queue, buffer_size=4)
        channel.rerun_path = "flows/source/output"

        payload = TickOut(value=5)
        channel.put_one(payload, 0.5, block=False)

        assert calls == [("flows/source/output", payload, 0.5, None, None)]

        ts, queued = queue.get(timeout=1.0)
        assert ts == 0.5
        assert queued.value == 5
    finally:
        queue.close()
        queue.join_thread()


def test_execute_ir_rerun_config_sets_shared_recording_env(monkeypatch):
    import retriever.rt.runtime as runtime_module

    state = _install_fake_rerun(monkeypatch)
    captured = {}

    class DummyEngine:
        def build(self):
            return None

        def start(self):
            return None

        def wait(self, timeout=None):
            return None

        def stop(self):
            return None

    class DummyFactory:
        def validate_dependencies(self):
            return True

        def create_engine(self, ir_struct, backend_config):
            captured["ir_struct"] = ir_struct
            captured["backend_config"] = backend_config
            return DummyEngine()

    monkeypatch.setattr(runtime_module, "get_backend", lambda backend: (lambda: DummyFactory()))
    monkeypatch.setenv("RERUN_RECORDING_ID", "shared-runtime-id")

    pipe = Pipeline("rerun_runtime_env")
    with pipe:
        src = TickSource() @ Rate(hz=1)
        sink = Drain() @ Trigger("value")
        pipe.connect(src, sink, sync=Latest())
    ir = pipe.validate()

    engine = execute_ir(
        ir,
        backend="multiprocessing",
        blocking=False,
        backend_config={
            "rerun_config": {
                "spawn": False,
                "connect_addr": "127.0.0.1:9000",
            }
        },
    )

    assert isinstance(engine, DummyEngine)
    assert captured["backend_config"]["env_overrides"]["RERUN_CONNECT_ADDR"] == "127.0.0.1:9000"
    assert captured["backend_config"]["env_overrides"]["RERUN_APP_ID"] == "rerun_runtime_env"
    assert captured["backend_config"]["env_overrides"]["RERUN_RECORDING_ID"] == "shared-runtime-id"
    assert os.environ["RERUN_CONNECT_ADDR"] == "127.0.0.1:9000"
    assert os.environ["RERUN_APP_ID"] == "rerun_runtime_env"
    assert os.environ["RERUN_RECORDING_ID"] == "shared-runtime-id"
    assert state["inits"][-1] == {
        "app_id": "rerun_runtime_env",
        "spawn": False,
        "recording_id": "shared-runtime-id",
    }
    assert state["connects"][-1] == "rerun+http://127.0.0.1:9000/proxy"


def test_mpchannel_respects_worker_viz_policy(monkeypatch):
    calls = []

    def fake_log_value_from_env(path, value, *, time_seconds=None, sequence=None, fields=None):
        calls.append((path, time_seconds, tuple(fields) if fields is not None else None))
        return True

    monkeypatch.setattr(
        "retriever.rt.backend.multiprocessing.channel.log_value_from_env",
        fake_log_value_from_env,
    )

    queue = Queue()
    try:
        channel = MPChannel(queue, buffer_size=4)
        channel.rerun_path = "flows/source/output"
        channel.rerun_policy = IRVizPolicy(enabled=True, hz=2.0, fields=["value"])

        channel.put_one(TickOut(value=1), 0.00, block=False)
        channel.put_one(TickOut(value=2), 0.10, block=False)
        channel.put_one(TickOut(value=3), 0.60, block=False)

        assert calls == [
            ("flows/source/output", 0.00, ("value",)),
            ("flows/source/output", 0.60, ("value",)),
        ]
    finally:
        queue.close()
        queue.join_thread()


def test_dora_publisher_respects_worker_viz_policy(monkeypatch):
    emitted = []
    sent = []

    def fake_log_value_from_env(path, value, *, time_seconds=None, sequence=None, fields=None):
        emitted.append((path, time_seconds, tuple(fields) if fields is not None else None))
        return True

    monkeypatch.setattr(
        "retriever.rt.backend.dora.channel.log_value_from_env",
        fake_log_value_from_env,
    )

    publisher = DoraPublisher(
        lambda port, arrow, metadata: sent.append((port, metadata)),
        "out",
        rerun_path="flows/source/output/out",
        rerun_policy=IRVizPolicy(enabled=True, hz=2.0, fields=["value"]),
    )

    publisher.put_one(TickOut(value=1), 0.00)
    publisher.put_one(TickOut(value=2), 0.10)
    publisher.put_one(TickOut(value=3), 0.60)

    assert emitted == [
        ("flows/source/output/out", 0.00, ("value",)),
        ("flows/source/output/out", 0.60, ("value",)),
    ]
    assert len(sent) == 3


def test_log_value_from_env_filters_selected_fields(monkeypatch):
    state = _install_fake_rerun(monkeypatch)
    monkeypatch.setenv("RERUN_CONNECT_ADDR", "127.0.0.1:9876")
    monkeypatch.setenv("RERUN_APP_ID", "rerun_test")
    monkeypatch.setenv("RERUN_RECORDING_ID", "shared-recording")

    out = SampleOut(value=7, image=np.zeros((4, 5, 3), dtype=np.uint8), label="kept-out")

    assert rerun_lib.log_value_from_env(
        "flows/source/output",
        out,
        time_seconds=1.25,
        fields=["value"],
    )

    logged_paths = [path for path, _payload in state["logs"]]
    assert "flows/source/output/value" in logged_paths
    assert "flows/source/output/image" not in logged_paths
    assert "flows/source/output/label" not in logged_paths


def test_ir_viz_policy_validates_and_loads_from_json():
    with pytest.raises(ValueError):
        IRVizPolicy(enabled=True, hz=0)

    ir_json = '{"version":"1","metadata":{"name":"p","created_at":"t","validated":true,"optimized":false},"nodes":[{"id":"n","type":"TickSource","module":"m","init_config":{},"config":{"clock":{"Rate":{"hz":1}}},"viz_policy":{"enabled":true,"hz":5.0,"fields":["value"],"path":"custom/path"},"inputs":{},"outputs":{"out":"TickOut"},"successors":[],"predecessors":[],"service_handlers":[],"service_callers":[]}],"edges":[],"topology":{"sources":["n"],"sinks":["n"],"groups":[["n"]],"node_count":1,"edge_count":0,"has_cycle":false,"is_connected":true},"optimization":null}'
    loaded = IR.from_json(ir_json)
    assert loaded.nodes[0].viz_policy is not None
    assert loaded.nodes[0].viz_policy.fields == ["value"]


def test_execute_ir_preserves_default_viz_as_runtime_fallback(monkeypatch):
    import retriever.rt.runtime as runtime_module

    captured = {}

    class DummyEngine:
        def build(self):
            return None

        def start(self):
            return None

        def wait(self, timeout=None):
            return None

        def stop(self):
            return None

    class DummyFactory:
        def validate_dependencies(self):
            return True

        def create_engine(self, ir_struct, backend_config):
            captured["ir_struct"] = ir_struct
            captured["backend_config"] = backend_config
            return DummyEngine()

    monkeypatch.setattr(runtime_module, "get_backend", lambda backend: (lambda: DummyFactory()))

    retriever.init(default_viz=VizConfig(hz=2.0, fields=["value"], path="custom/root"))
    try:
        pipe = Pipeline("rerun_runtime_env")
        with pipe:
            src = TickSource() @ Rate(hz=1)
            sink = Drain() @ Trigger("value")
            pipe.connect(src, sink, sync=Latest())
        ir = pipe.validate()
        assert ir.nodes[0].viz_policy is None
        engine = execute_ir(
            ir,
            backend="multiprocessing",
            blocking=False,
            backend_config={"rerun_config": {"spawn": False, "connect_addr": "127.0.0.1:9000"}},
        )
        assert isinstance(engine, DummyEngine)
    finally:
        retriever.init(default_viz=None)
