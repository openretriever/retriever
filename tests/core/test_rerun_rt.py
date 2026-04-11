from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from multiprocessing import Queue
from typing import Optional

import numpy as np

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from retriever.lib import rerun as rerun_lib
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
    rerun_mod.Image = lambda value: ("Image", np.asarray(value).shape)
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
    assert ("retriever_time", None, None, 1.25) in timelines
    assert ("log_time", None, 1.25, None) in timelines


def test_mpchannel_put_one_emits_worker_rerun_log(monkeypatch):
    calls = []

    def fake_log_value_from_env(path, value, *, time_seconds=None, sequence=None):
        calls.append((path, value, time_seconds, sequence))
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

        assert calls == [("flows/source/output", payload, 0.5, None)]

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
