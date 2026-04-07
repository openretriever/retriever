from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.config import RecordConfig
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, flow_io
from retriever.lib.mcap import _deserialize_value
from retriever.recording import build_recording_sink, read_node_stream_from_recording
from retriever.rt.stepper import EventStreamRecorder, StepResult


@flow_io
@dataclass
class Value:
    value: int


class Counter(Flow[None, Value]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return Value(value=self.count)


class Passthrough(Flow[Value, Value]):
    def step(self, input: Value) -> Value:
        return Value(value=input.value)


class Recorder(Flow[Value, None]):
    def reset(self) -> None:
        self.seen = []

    def step(self, input: Value) -> None:
        self.seen.append(input.value)
        return None


class UnsupportedValue:
    pass


def test_pipeline_step_propagates_values_in_process():
    pipe = Pipeline("step_demo")

    src = Counter() @ Rate(hz=10)
    mid = Passthrough() @ Trigger("value")
    sink = Recorder() @ Rate(hz=10)

    pipe.connect(src, mid, sync=Latest())
    pipe.connect(mid, sink, sync=Latest())

    res1 = pipe.step(dt=0.1)
    assert res1.executed  # at least one node ran
    assert sink.flow.seen == [1]

    res2 = pipe.step(dt=0.1)
    assert sink.flow.seen == [1, 2]
    assert res2.now > res1.now


def test_pipeline_record_to_and_replay_helpers(tmp_path):
    rec_path = tmp_path / "recording.pkl.gz"

    # Record a short stream (in-process).
    pipe1 = Pipeline("record_demo")
    src1 = Counter() @ Rate(hz=10)
    drain1 = Recorder() @ Trigger("value")
    pipe1.connect(src1, drain1, sync=Latest())

    try:
        buffer = pipe1.record_to(src1, rec_path, steps=3, dt=0.1)
    finally:
        pipe1.close_stepper()

    assert [out.value for _ts, out in buffer] == [1, 2, 3]

    # Replay into a fresh pipeline and verify we see the same values.
    pipe2 = Pipeline("replay_demo")
    src2 = Counter() @ Rate(hz=10)  # placeholder (will be replaced)
    sink2 = Recorder() @ Trigger("value")
    pipe2.connect(src2, sink2, sync=Latest())

    replay = pipe2.replay(src2, path=rec_path)
    try:
        for _ in range(10):
            pipe2.step(dt=0.1)
            if getattr(replay.flow, "done", False):
                break
    finally:
        pipe2.close_stepper()

    assert sink2.flow.seen == [1, 2, 3]


def test_event_stream_recorder_supports_single_step_and_multi_step_recording():
    pipe = Pipeline("recorder_demo")
    src = Counter() @ Rate(hz=10)
    sink = Recorder() @ Trigger("value")
    pipe.connect(src, sink, sync=Latest())

    recorder = EventStreamRecorder(pipe, src, name="counter")
    try:
        first = recorder.step(dt=0.1)
        second = recorder.step(dt=0.1)
        assert [out.value for _ts, out in recorder.buffer] == [1, 2]
        assert second.now > first.now

        recorder.buffer.clear()
        recorder.record(steps=3, dt=0.1)
    finally:
        pipe.close_stepper()

    assert [out.value for _ts, out in recorder.buffer] == [3, 4, 5]


def test_pipeline_record_config_can_emit_rrd_and_mcap(tmp_path):
    pytest.importorskip("rerun")

    rrd_path = tmp_path / "session.rrd"
    mcap_path = tmp_path / "session.mcap"

    pipe = Pipeline("record_both_demo")
    src = Counter() @ Rate(hz=10)
    drain = Recorder() @ Trigger("value")
    pipe.connect(src, drain, sync=Latest())

    cfg = RecordConfig(path=rrd_path, mirrors=(mcap_path,))

    try:
        pipe.record(cfg, steps=3, dt=0.1)
    finally:
        pipe.close_stepper()

    assert rrd_path.exists()
    assert rrd_path.stat().st_size > 0
    assert mcap_path.exists()
    assert mcap_path.stat().st_size > 0


@pytest.mark.parametrize("suffix", [".mcap", ".rrd"])
def test_pipeline_replay_supports_session_recordings(tmp_path, suffix):
    if suffix == ".rrd":
        pytest.importorskip("rerun")

    record_path = tmp_path / f"session{suffix}"

    pipe1 = Pipeline("record_session_demo")
    src1 = Counter() @ Rate(hz=10)
    drain1 = Recorder() @ Trigger("value")
    pipe1.connect(src1, drain1, sync=Latest())

    try:
        pipe1.record(record_path, steps=3, dt=0.1)
    finally:
        pipe1.close_stepper()

    pipe2 = Pipeline("replay_session_demo")
    src2 = Counter() @ Rate(hz=10)
    sink2 = Recorder() @ Trigger("value")
    pipe2.connect(src2, sink2, sync=Latest())

    replay = pipe2.replay(src2, path=record_path)
    try:
        for _ in range(10):
            pipe2.step(dt=0.1)
            if getattr(replay.flow, "done", False):
                break
    finally:
        pipe2.close_stepper()

    assert sink2.flow.seen == [1, 2, 3]


@pytest.mark.parametrize("suffix", [".mcap", ".rrd"])
def test_session_recordings_preserve_optional_none_outputs(tmp_path, suffix):
    if suffix == ".rrd":
        pytest.importorskip("rerun")

    record_path = tmp_path / f"optional_session{suffix}"
    sink = build_recording_sink(RecordConfig(path=record_path), app_id="optional_demo")
    sink.open()
    try:
        sink.write_step(
            StepResult(
                now=0.1,
                executed=["MaybeValue"],
                inputs={},
                outputs={"MaybeValue": None},
            ),
            0,
        )
        sink.write_step(
            StepResult(
                now=0.2,
                executed=["MaybeValue"],
                inputs={},
                outputs={"MaybeValue": Value(value=2)},
            ),
            1,
        )
    finally:
        sink.close()

    buffer = read_node_stream_from_recording(record_path, "MaybeValue", output_type=Value | None)
    assert [None if value is None else value.value for _ts, value in buffer] == [None, 2]


def test_mcap_recording_rejects_unsupported_values(tmp_path):
    record_path = tmp_path / "unsupported_session.mcap"
    sink = build_recording_sink(RecordConfig(path=record_path), app_id="unsupported_demo")
    sink.open()
    try:
        with pytest.raises(TypeError, match="Unsupported value for stable MCAP recording"):
            sink.write_step(
                StepResult(
                    now=0.1,
                    executed=["BadNode"],
                    inputs={},
                    outputs={"BadNode": UnsupportedValue()},
                ),
                0,
            )
    finally:
        sink.close()


def test_mcap_reader_rejects_legacy_pickled_payloads():
    import pickle

    payload = pickle.dumps({"legacy": True})
    with pytest.raises(RuntimeError, match="Legacy pickled MCAP payload"):
        _deserialize_value(payload, "retriever.LegacyThing")
