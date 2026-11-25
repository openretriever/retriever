"""Sync reads see only events committed up to the consumer tick (ts <= now)."""
from __future__ import annotations

import pytest

from retriever.error import FlowError
from retriever.flow import io
from retriever.flow.adapter import (
    Chunking,
    Events,
    Exact,
    Hold,
    Latest,
    Linear,
    Prev,
    Window,
)
from retriever.flow.types import TimedBuffer, visible
from retriever.rt.buffer_engine import PythonBufferEngine
from retriever.rt.step import IOStep


@io
class Value:
    value: object


class _ListSubscriber:
    """Subscriber without `sample`: exercises the IOStep fallback path."""

    def __init__(self, events):
        self._events = TimedBuffer(events)

    def empty(self):
        return not self._events

    def get_all(self):
        return self._events


def _engine(events, buffer_size=4):
    eng = PythonBufferEngine(buffer_size=buffer_size)
    for ts, value in events:
        eng.push(ts, value)
    return eng


MIXED = [(0.1, 1), (0.35, 9), (0.6, 16)]
FUTURE = [(0.6, 16), (0.7, 25)]


def _fallback_sample(events, adapter, now):
    step = IOStep({"value": _ListSubscriber(events)}, ["..."])
    step.sample(Value, {"value": adapter}, now=now)
    return step.instance.value


def test_visible_helper():
    assert visible(TimedBuffer(MIXED), 0.5) == [(0.1, 1), (0.35, 9)]
    assert visible(TimedBuffer(MIXED), 0.35) == [(0.1, 1), (0.35, 9)]
    assert visible(TimedBuffer(FUTURE), 0.5) == []


def test_hold_reads_visible_value_not_future():
    assert _engine(MIXED).sample(Hold(), now=0.5) == 9
    assert _fallback_sample(MIXED, Hold(), 0.5) == 9


def test_events_excludes_future():
    events = Events(buffer_size=4, duration=None)
    assert list(_engine(MIXED).sample(events, now=0.5)) == [(0.1, 1), (0.35, 9)]
    assert list(_fallback_sample(MIXED, events, 0.5)) == [(0.1, 1), (0.35, 9)]


@pytest.mark.parametrize(
    "adapter",
    [
        Latest(),
        Latest(max_age=1.0),
        Hold(),
        Window(duration=1.0),
        Events(buffer_size=4),
        Exact(),
        Linear(),
        Chunking(),
        Prev(),
    ],
    ids=lambda a: type(a).__name__,
)
def test_all_future_buffer_gives_no_signal(adapter):
    with pytest.raises(IndexError):
        _engine(FUTURE).sample(adapter, now=0.5)
    assert _fallback_sample(FUTURE, adapter, 0.5) is None


def test_latest_and_prev_unchanged():
    assert _engine(MIXED).sample(Latest(), now=0.5) == 9
    assert _engine(MIXED).sample(Prev(), now=0.5) == 9
    assert _engine(MIXED).sample(Prev(), now=0.35) == 1
    # Prev keeps its initial fallback even when every event is in the future.
    assert _engine(FUTURE).sample(Prev(initial=0), now=0.5) == 0
    # Without `now`, no visibility filter applies.
    assert _engine(MIXED).sample(Hold()) == 16
    assert _engine(MIXED).sample(Latest()) == 16


# --- Window -----------------------------------------------------------------

WINDOW_BUF = TimedBuffer([(0.10, 1), (0.20, 4), (0.35, 9), (0.60, 16)])


def test_window_default_returns_list_in_time_order():
    assert Window(duration=0.30)(WINDOW_BUF, now=0.50) == [4, 9]
    assert Window(duration=0.45)(WINDOW_BUF, now=0.50) == [1, 4, 9]
    assert Window(duration=0.30).buffer_size == 64


def test_window_only_future_events_gives_no_signal():
    with pytest.raises(IndexError):
        Window(duration=0.05)(WINDOW_BUF, now=0.50)
    with pytest.raises(IndexError):
        Window(duration=0.30)(TimedBuffer([(0.60, 16)]), now=0.50)


def test_window_missing_duration_raises():
    with pytest.raises(FlowError):
        Window()


# --- Latest bounded staleness --------------------------------------------------

def test_latest_max_age():
    fresh = TimedBuffer([(0.1, 1), (0.35, 9)])
    stale = TimedBuffer([(0.1, 1)])
    assert Latest(max_age=0.2)(fresh, now=0.5) == 9
    with pytest.raises(IndexError):
        Latest(max_age=0.2)(stale, now=0.5)
    assert Latest()(stale, now=0.5) == 1
    # Buffer-engine path honors max_age too (no fast-path bypass).
    assert _engine(fresh).sample(Latest(max_age=0.2), now=0.5) == 9
    with pytest.raises(IndexError):
        _engine(stale).sample(Latest(max_age=0.2), now=0.5)
    assert _engine(stale).sample(Latest(), now=0.5) == 1


def test_latest_max_age_must_be_non_negative():
    with pytest.raises(FlowError):
        Latest(max_age=-0.1)
