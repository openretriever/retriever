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



def test_multiprocessing_fanin_latest_is_independent_of_queue_drain_order():
    from multiprocessing import Queue

    from retriever.rt.backend.multiprocessing.channel import MPChannel

    q1 = Queue()
    q2 = Queue()
    channel = MPChannel(q1, buffer_size=1)
    channel.add_queue(q2)

    q1.put((0.03, "newer-from-q1"))
    q2.put((0.01, "older-from-q2"))
    channel.drain()

    assert channel.sample(Latest(), now=0.04) == "newer-from-q1"
