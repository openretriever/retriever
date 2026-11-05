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
    samples = [(10.0, Value(value=1)), (10.7, Value(value=2)),
               (10.7, Value(value=3)), (12.5, Value(value=4))]
    replay = pipe.replay(source, buffer=samples, timestamped=True)
    try:
        for now, expected in [(9.0, []), (10.0, [1]), (10.2, [1]),
                              (11.0, [1, 2]), (11.0, [1, 2, 3]),
                              (12.4, [1, 2, 3]), (13.0, [1, 2, 3, 4])]:
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
    flow = replay_flow([(100.0, Value(value=1)), (0.0, Value(value=2))],
                       output_type=Value)
    flow.reset()
    assert [flow.step(None).value for _ in range(3)] == [1, 2, None]
    assert flow.done


@pytest.mark.parametrize("timestamps", [[2.0, 1.0], [float("nan")], [float("inf")]])
def test_timestamped_replay_rejects_invalid_recorded_times(timestamps):
    with pytest.raises(ValueError, match="finite.*nondecreasing"):
        replay_flow([(ts, Value(value=1)) for ts in timestamps],
                    output_type=Value, timestamped=True)


def test_timestamped_replay_requires_stepper_time():
    flow = replay_flow([(1.0, Value(value=1))], output_type=Value, timestamped=True)
    flow.reset()
    with pytest.raises(RuntimeError, match="in-process"):
        flow.step(None)


def test_timestamped_replay_handle_and_backward_tick():
    pipe = Pipeline("replay_handle")
    source = replay_handle([(1.0, Value(value=1))], Rate(hz=10),
                           output_type=Value, timestamped=True)
    sink = Sink() @ Trigger("value")
    pipe.connect(source, sink, sync=Latest())
    try:
        pipe.step(now=0.5)
        with pytest.raises(ValueError, match="nondecreasing"):
            pipe.step(now=0.4)
    finally:
        pipe.close_stepper()
