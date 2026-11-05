"""Opt-in replay timing and legacy sequential compatibility."""

import pytest

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from retriever.rt.stepper import replay_flow, replay_handle


@io
class Value:
    value: int


class Source(Flow[None, Value]):
    def step(self, _):
        return Value(value=-1)


class Sink(Flow[Value, None]):
    def reset(self):
        self.seen = []

    def step(self, value):
        self.seen.append(value.value)


def test_timestamped_replay_waits_preserves_times_and_resets():
    pipe = Pipeline("timestamped")
    source = Source() @ Rate(hz=10)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest(buffer_size=8))
    samples = [
        (10.0, Value(value=1)),
        (10.7, Value(value=2)),
        (10.7, Value(value=3)),
        (12.5, Value(value=4)),
    ]
    replay = pipe.replay(source, buffer=samples, timestamped=True)
    try:
        for now, expected in [
            (9.0, []),
            (10.0, [1]),
            (10.2, [1]),
            (11.0, [1, 2]),
            (11.0, [1, 2, 3]),
            (12.4, [1, 2, 3]),
            (13.0, [1, 2, 3, 4]),
        ]:
            pipe.step(now=now)
            assert sink.flow.seen == expected
        node_id = pipe.get_node_id(sink)
        events = pipe._stepper._inputs[node_id]["value"].get_all()
        assert [ts for ts, _ in events] == [10.0, 10.7, 10.7, 12.5]
        pipe.step(now=14.0)
        assert replay.flow.done
        pipe.reset_stepper()
        pipe.step(now=9.0)
        assert sink.flow.seen == []
        pipe.step(now=10.0)
        assert sink.flow.seen == [1]
    finally:
        pipe.close_stepper()


def test_default_replay_ignores_timestamps_and_keeps_order():
    flow = replay_flow(
        [(100.0, Value(value=1)), (0.0, Value(value=2))], output_type=Value
    )
    flow.reset()
    assert [flow.step(None).value for _ in range(3)] == [1, 2, None]
    assert flow.done


@pytest.mark.parametrize("timestamps", [[2.0, 1.0], [float("nan")], [float("inf")]])
def test_timestamped_replay_rejects_invalid_recorded_times(timestamps):
    with pytest.raises(ValueError, match="finite.*nondecreasing"):
        replay_flow(
            [(ts, Value(value=1)) for ts in timestamps],
            output_type=Value,
            timestamped=True,
        )


def test_timestamped_replay_requires_stepper_time():
    flow = replay_flow([(1.0, Value(value=1))], output_type=Value, timestamped=True)
    flow.reset()
    with pytest.raises(RuntimeError, match="in-process"):
        flow.step(None)


def test_timestamped_replay_handle_and_backward_tick():
    pipe = Pipeline("replay_handle")
    source = replay_handle(
        [(1.0, Value(value=1))], Rate(hz=10), output_type=Value, timestamped=True
    )
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    try:
        pipe.step(now=0.5)
        with pytest.raises(ValueError, match="nondecreasing"):
            pipe.step(now=0.4)
    finally:
        pipe.close_stepper()


def test_timestamped_replay_from_recorded_file(tmp_path):
    from retriever.rt.stepper import save_timed_buffer

    path = tmp_path / "samples.pkl.gz"
    save_timed_buffer(path, [(0.25, Value(value=7)), (1.5, Value(value=8))])
    pipe = Pipeline("replay_from")
    source = Source() @ Rate(hz=10)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    pipe.replay_from(path, inputs=[source], timestamped=True)
    try:
        for now in [0.0, 0.25, 1.0]:
            pipe.step(now=now)
        assert sink.flow.seen == [7]
        pipe.step(now=1.5)
        assert sink.flow.seen == [7, 8]
    finally:
        pipe.close_stepper()


def test_empty_timestamped_replay_finishes_without_publishing():
    pipe = Pipeline("empty_replay")
    source = replay_handle([], Rate(hz=10), output_type=Value, timestamped=True)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    try:
        pipe.step(now=0.0)
        assert source.flow.done
        assert sink.flow.seen == []
    finally:
        pipe.close_stepper()


def test_timestamped_mcap_replay_matches_original_fractional_ticks(tmp_path):
    from retriever.lib.mcap import MCAPReader, MCAPWriter

    path = tmp_path / "fractional.mcap"
    times = [
        1.0812599999999999,
        1.0812599999999999,
        1.0812600000000001,
        1.37,
        2.8123399999999998,
    ]
    original = Pipeline("fractional")
    source = Source() @ Rate(hz=10)
    sink = Sink() @ Trigger("value")
    original.connect(source, sink, sync=Latest(buffer_size=8))
    try:
        with MCAPWriter(path) as writer:
            for index, now in enumerate(times):
                writer.write_step(original.step(now=now), index)
        expected = sink.flow.seen[:]
        node_id = original.get_node_id(source)
    finally:
        original.close_stepper()

    # Legacy reads keep their existing nanosecond-derived timestamps.
    with MCAPReader(path) as reader:
        assert [ts for ts, _ in reader.read_node_stream(node_id)] == [
            int(now * 1e9) / 1e9 for now in times
        ]

    replayed = Pipeline("fractional")
    replacement = Source() @ Rate(hz=10)
    target = Sink() @ Trigger("value")
    replayed.connect(replacement, target, sync=Latest(buffer_size=8))
    replayed.replay(replacement, path=path, timestamped=True)
    try:
        for index, now in enumerate(times):
            replayed.step(now=now)
            assert target.flow.seen == expected[: index + 1]
        target_id = replayed.get_node_id(target)
        assert [
            ts for ts, _ in replayed._stepper._inputs[target_id]["value"].get_all()
        ] == times
    finally:
        replayed.close_stepper()


def test_timestamped_replay_rejects_rrd_before_reading(tmp_path):
    pipe = Pipeline("unsupported_timing")
    source = Source() @ Rate(hz=10)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    with pytest.raises(ValueError, match="Timestamped.*MCAP|timestamped.*MCAP"):
        pipe.replay(source, path=tmp_path / "session.rrd", timestamped=True)


def test_default_replay_publishes_at_current_tick():
    pipe = Pipeline("sequential_times")
    source = Source() @ Rate(hz=10)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest(buffer_size=8))
    pipe.replay(source, buffer=[(100.0, Value(value=7)), (200.0, Value(value=8))])
    try:
        pipe.step(now=1.0)
        pipe.step(now=2.0)
        assert sink.flow.seen == [7, 8]
        node_id = pipe.get_node_id(sink)
        assert [ts for ts, _ in pipe._stepper._inputs[node_id]["value"].get_all()] == [
            1.0,
            2.0,
        ]
    finally:
        pipe.close_stepper()


def test_timestamped_dt_replay_requires_anchor_then_waits():
    pipe = Pipeline("delta_times")
    source = replay_handle(
        [(0.25, Value(value=1)), (1.5, Value(value=2))],
        Rate(hz=10),
        output_type=Value,
        timestamped=True,
    )
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    try:
        with pytest.raises(ValueError, match="now=.*before.*dt"):
            pipe.step(dt=0.25)
        assert not hasattr(sink.flow, "seen")
        pipe.step(now=0.0)
        pipe.step(dt=0.25)
        assert sink.flow.seen == [1]
        pipe.step(dt=0.5)
        assert sink.flow.seen == [1]
        pipe.step(dt=0.75)
        assert sink.flow.seen == [1, 2]
    finally:
        pipe.close_stepper()


def test_replay_from_default_supports_existing_replay_override(tmp_path):
    class CustomPipeline(Pipeline):
        def replay(self, handle, *, path):
            self.called = (handle, path)
            return handle

    pipe = CustomPipeline("override")
    source = Source() @ Rate(hz=10)
    path = tmp_path / "session.mcap"
    pipe.replay_from(path, inputs=[source])
    assert pipe.called == (source, path)


def test_timestamped_replay_does_not_round_future_buffer_time():
    pipe = Pipeline("future_precision")
    before = 1.0812599999999999
    due = 1.0812600000000001
    source = replay_handle(
        [(due, Value(value=1))], Rate(hz=10), output_type=Value, timestamped=True
    )
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    try:
        pipe.step(now=before)
        assert sink.flow.seen == []
        pipe.step(now=due)
        assert sink.flow.seen == [1]
    finally:
        pipe.close_stepper()


def test_timestamped_mcap_rejects_missing_step_metadata(tmp_path):
    from retriever.lib.mcap import MCAPReader, MCAPWriter

    path = tmp_path / "missing_step.mcap"
    with MCAPWriter(path) as writer:
        channel = writer._get_channel_id(
            "/retriever/flows/source/output", "retriever.Value", b'{"type":"object"}'
        )
        writer._writer.add_message(
            channel_id=channel,
            log_time=1000000000,
            data=b'{"value":1}',
            publish_time=1000000000,
        )
    with MCAPReader(path) as reader:
        assert len(reader.read_node_stream("source")) == 1
    with MCAPReader(path) as reader:
        with pytest.raises(ValueError, match="matching step time metadata"):
            reader.read_node_stream("source", preserve_step_time=True)
