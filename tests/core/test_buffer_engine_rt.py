from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.core.flow import flow_io
from retriever.core.flow.adapter import Events, Hold, Latest, Window
from retriever.core.rt.buffer_engine import PythonBufferEngine
from retriever.core.rt.signal import Signal


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

    @flow_io
    @dataclass
    class In:
        x: int

    sub = SampleOnlySubscriber(123)
    sig = Signal({"x": sub}, fields_filter=["..."], now=1.0).sample(
        In,
        adapters={"x": Latest()},
        now=1.0,
    )
    assert sig.instance.x == 123
    assert sub.sample_called is True

