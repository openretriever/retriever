from __future__ import annotations


import pytest

from retriever.flow import io
from retriever.flow.adapter import Events, Hold, Latest, Window
from retriever.rt.buffer_engine import PythonBufferEngine
from retriever.rt.step import IOStep


def test_python_buffer_engine_samples_builtin_adapters_without_list_materialization():
    eng = PythonBufferEngine(buffer_size=10)
    eng.push(1.0, 1)
    eng.push(3.5, 3)
    eng.push(4.5, 5)

    assert eng.sample(Latest()) == 5

    hold = Hold(debounce=0.5)
    assert eng.sample(hold) == 5

    # Debounce: if a new event arrives quickly, Hold returns the previous held value.
    eng.push(4.7, 9)
    assert eng.sample(hold) == 5

    window = Window(buffer_size=10, duration=2.0, agg="mean")
    assert eng.sample(window, now=5.0) == pytest.approx((3 + 5 + 9) / 3)

    events = Events(buffer_size=10, duration=1.0, include_timestamps=False)
    assert eng.sample(events, now=5.0) == [5, 9]


def test_latest_samples_by_timestamp_not_append_order():
    eng = PythonBufferEngine(buffer_size=10)
    eng.push(0.03, "newer")
    eng.push(0.01, "older")

    assert eng.sample(Latest()) == "newer"
    assert eng.sample(Latest(), now=0.02) == "older"


def test_latest_ignores_future_records_at_sample_time():
    eng = PythonBufferEngine(buffer_size=10)
    eng.push(0.01, "ready")
    eng.push(0.03, "future")

    assert eng.sample(Latest(), now=0.02) == "ready"
    assert eng.sample(Latest(), now=0.03) == "future"


def test_bounded_buffer_drops_oldest_timestamp_not_first_append():
    eng = PythonBufferEngine(buffer_size=1)
    eng.push(0.03, "newer")
    eng.push(0.01, "older")

    assert list(eng.events()) == [(0.03, "newer")]
    assert eng.sample(Latest(), now=0.04) == "newer"


def test_signal_prefers_subscriber_sample_fast_path():
    class SampleOnlySubscriber:
        def __init__(self, value):
            self.value = value
            self.sample_called = False

        def new_arrival(self) -> bool:
            return True

        def empty(self) -> bool:
            return False

        def clear(self) -> None:
            return None

        def sample(self, adapter, *, now=None):
            self.sample_called = True
            return self.value

        def get_all(self):
            raise AssertionError("Signal should not call get_all when sample() exists")

    @io
    class In:
        x: int

    sub = SampleOnlySubscriber(123)
    sig = IOStep({"x": sub}, fields_filter=["..."], now=1.0).sample(
        In,
        adapters={"x": Latest()},
        now=1.0,
    )
    assert sig.instance.x == 123
    assert sub.sample_called is True



def test_all_future_events_read_as_no_signal_not_node_death():
    """A non-empty buffer whose every event is stamped after `now` (producer
    clock ahead of the consumer's, e.g. cross-machine dora skew) must behave
    like an empty buffer at the runtime call site: no signal this tick, no
    exception escaping into the executor loop (which would kill the node).
    The adapter itself stays strict and raises; IOStep absorbs it."""

    @io
    class In:
        x: int

    # Path 1: subscriber.sample fast path (mp/dora channels -> buffer engine).
    class EngineSubscriber:
        def __init__(self):
            self._eng = PythonBufferEngine(buffer_size=1)
            self._eng.push(10.0, 42)  # stamped after the sampling tick below

        def new_arrival(self) -> bool:
            return True

        def empty(self) -> bool:
            return self._eng.empty()

        def clear(self) -> None:
            self._eng.clear()

        def sample(self, adapter, *, now=None):
            return self._eng.sample(adapter, now=now)

        def get_all(self):
            return self._eng.events()

    sig = IOStep({"x": EngineSubscriber()}, fields_filter=["..."], now=1.0).sample(
        In, adapters={"x": Latest()}, now=1.0
    )
    assert sig.instance.x is None  # no signal this tick, no crash

    # Path 2: get_all fallback (in-process stepper channels).
    class PlainSubscriber:
        def new_arrival(self) -> bool:
            return True

        def empty(self) -> bool:
            return False

        def clear(self) -> None:
            return None

        def get_all(self):
            from retriever.flow.types import TimedBuffer

            return TimedBuffer([(10.0, 42)])

    sig2 = IOStep({"x": PlainSubscriber()}, fields_filter=["..."], now=1.0).sample(
        In, adapters={"x": Latest()}, now=1.0
    )
    assert sig2.instance.x is None

    # The engine itself keeps the documented strict contract.
    eng = PythonBufferEngine(buffer_size=1)
    eng.push(10.0, 42)
    with pytest.raises(IndexError):
        eng.sample(Latest(), now=1.0)


def test_equal_timestamp_ties_resolve_identically_on_both_sampling_paths():
    """The stepper path (TimedBuffer.latest via Latest.__call__) and the
    buffer-engine fast path must pick the same winner for equal timestamps,
    or replaying a backend-recorded trace through step() flips tie samples.
    The documented rule: insertion order — last-inserted among ties wins."""
    from retriever.flow.types import TimedBuffer

    tie_events = [(0.02, "first-arrived"), (0.02, "second-arrived")]

    eng = PythonBufferEngine(buffer_size=10)
    for ts, value in tie_events:
        eng.push(ts, value)
    engine_winner = eng.sample(Latest(), now=0.03)

    types_winner = Latest()(TimedBuffer(tie_events), now=0.03)

    assert engine_winner == types_winner == "second-arrived"


def test_out_of_order_pushes_keep_events_timestamp_sorted():
    """EventStream.events() documents a chronologically-ordered snapshot, and
    consumers rely on it (Window agg="first"/"last" pick by buffer position;
    Behavior.hold early-breaks on sortedness). Out-of-order arrival must not
    leak arrival order into the snapshot; equal timestamps keep arrival order."""
    eng = PythonBufferEngine(buffer_size=8)
    for ts, value in [(0.30, "c"), (0.10, "a"), (0.20, "b"), (0.20, "b-tie")]:
        eng.push(ts, value)

    assert list(eng.events()) == [(0.10, "a"), (0.20, "b"), (0.20, "b-tie"), (0.30, "c")]


def test_stepper_channel_buffers_identically_to_backend_engine():
    """The in-process channel is backed by the same buffer engine as the
    backends, so inject_input() with out-of-order custom timestamps yields the
    same retained set, order, and Latest winner as multiprocessing/dora —
    previously it appended in arrival order and evicted by arrival, not
    timestamp."""
    from retriever.rt.stepper import InMemoryChannel

    # Out-of-order arrival plus an equal-timestamp tie, one over capacity.
    events = [(0.50, "n1"), (0.70, "n2"), (0.10, "late-old"), (0.70, "n2-tie")]

    eng = PythonBufferEngine(buffer_size=3)
    chan = InMemoryChannel(buffer_size=3)
    for ts, value in events:
        eng.push(ts, value)
        chan.put_one(value, ts, block=False)

    # Identical retained set and order; the late old event is the one evicted.
    assert list(chan.get_all()) == list(eng.events())
    assert list(chan.get_all()) == [(0.50, "n1"), (0.70, "n2"), (0.70, "n2-tie")]

    # And the sampled winner agrees across paths, including the tie rule.
    assert Latest()(chan.get_all(), now=1.0) == eng.sample(Latest(), now=1.0) == "n2-tie"


def test_multiprocessing_fanin_latest_is_independent_of_queue_drain_order():
    # This exercises MPChannel's drain + buffer semantics, not the transport.
    # multiprocessing.Queue hands puts to a feeder thread, so an immediate
    # drain races it (flaky); stdlib queue.Queue has the identical
    # get_nowait()/queue.Empty interface with no feeder thread, making the
    # drain deterministic while running the exact same channel code path.
    from queue import Queue

    from retriever.rt.backend.multiprocessing.channel import MPChannel

    q1 = Queue()
    q2 = Queue()
    channel = MPChannel(q1, buffer_size=1)
    channel.add_queue(q2)

    q1.put((0.03, "newer-from-q1"))
    q2.put((0.01, "older-from-q2"))
    channel.drain()  # drains q1 fully, then q2: the older event is pushed LAST

    assert channel.sample(Latest(), now=0.04) == "newer-from-q1"
