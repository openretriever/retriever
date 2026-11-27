"""Causal reads: notifications match readable values, stateful policies reset, direct
and runtime reads agree, and run_logical starts a fresh rate cursor."""
import itertools

import pytest

from retriever.flow import Flow, Hold, Latest, Pipeline, Rate, Trigger, io
from retriever.flow.adapter import Chunking, Events, Exact, Linear
from retriever.flow.types import TimedBuffer
from retriever.rt.buffer_engine import PythonBufferEngine
from retriever.rt.stepper import InMemoryChannel


@io
class Value:
    value: int


class Source(Flow[None, Value]):
    def reset(self):
        self.i = 0

    def step(self, _):
        self.i += 1
        return Value(value=self.i)


class Relay(Flow[Value, Value]):
    def step(self, inputs):
        return Value(value=inputs.value)


def _times(results, node):
    return [r.now for r in results if node in r.executed]


def _engine(events, buffer_size=8):
    eng = PythonBufferEngine(buffer_size=buffer_size)
    for ts, value in events:
        eng.push(ts, value)
    return eng


# --- Arrival notifications follow the retained values -------------------------

def test_evicted_value_takes_its_notification_with_it():
    ch = InMemoryChannel(buffer_size=1)
    ch.put_one(1, 0.0)
    ch.put_one(2, 0.1)  # evicts the value at 0.0
    assert ch.new_arrival(0.0) is False
    assert ch.new_arrival(0.1) is True


def test_future_burst_does_not_drop_an_eligible_arrival():
    ch = InMemoryChannel(buffer_size=2048)
    ch.put_one(0, 0.0)
    for k in range(1024):
        ch.put_one(k, 1.0 + k)
    assert ch.new_arrival(0.0) is True
    assert ch.new_arrival(0.5) is False


def test_trigger_never_fires_without_a_readable_value():
    with Pipeline() as pipe:
        (Source() @ Rate(10)).named("ticker")
        (Relay() @ Trigger("value")).named("echo")
    pipe.inject_input("echo", "value", 1, timestamp=0.0)
    pipe.inject_input("echo", "value", 2, timestamp=0.1)  # depth one: evicts 1
    res = pipe.run_logical(0.2)
    assert _times(res, "echo") == pytest.approx([0.1])
    echo = next(r for r in res if "echo" in r.executed)
    assert echo.inputs["echo"].value == 2


# --- Stateful sync policies ------------------------------------------------------

def test_debounced_hold_drops_a_cached_value_from_a_later_time():
    eng = _engine([(1.0, "a"), (2.0, "b")])
    hold = Hold(buffer_size=8, debounce=0.5)
    assert eng.sample(hold, now=2.0) == "b"
    assert eng.sample(hold, now=1.0) == "a"  # rewind: "b" is not visible at 1.0


_counter = itertools.count(1)


class RunningSource(Flow[None, Value]):
    """Keeps counting across pipeline resets, so each run emits new values."""

    def step(self, _):
        return Value(value=next(_counter))


def test_reset_clears_stateful_sync_policies():
    with Pipeline() as pipe:
        src = (RunningSource() @ Rate(10)).named("src")
        sink = (Relay() @ Rate(10)).named("sink")
        src.then(sink, sync=Hold(debounce=10.0))

    pipe.run_logical(0.3)
    pipe.reset()
    second = pipe.run_logical(0.3)
    first_tick = second[0]
    # After reset, the held value comes from this run, not the previous one.
    assert first_tick.inputs["sink"].value == first_tick.outputs["src"].value


# --- Direct reads match runtime reads ----------------------------------------------

MIXED = TimedBuffer([(0.1, 1), (0.6, 16)])


def test_direct_reads_never_see_the_future():
    assert Hold()(MIXED, now=0.5) == 1
    assert list(Events(buffer_size=4)(MIXED, now=0.5)) == [(0.1, 1)]
    assert Chunking(dt=0.1)(TimedBuffer([(0.6, [1, 2, 3])]), now=0.5) is None
    with pytest.raises(IndexError):
        Hold()(TimedBuffer([(0.6, 16)]), now=0.5)


def test_linear_and_exact_agree_with_the_engine_on_unsorted_input():
    unsorted = [(0.0, 0.0), (0.4, 9.0), (0.2, 8.0)]
    assert Linear()(TimedBuffer(unsorted), now=0.5) == 9.0
    assert _engine(unsorted).sample(Linear(), now=0.5) == 9.0
    assert Exact(tolerance=0.2)(TimedBuffer(unsorted), now=0.5) == 9.0
    assert _engine(unsorted).sample(Exact(tolerance=0.2), now=0.5) == 9.0


def test_exact_with_only_future_events_gives_no_signal_both_ways():
    future = [(0.6, 16)]
    with pytest.raises(IndexError):
        Exact()(TimedBuffer(future), now=0.5)
    with pytest.raises(IndexError):
        _engine(future).sample(Exact(), now=0.5)


# --- run_logical starts a fresh rate cursor --------------------------------------

def test_manual_step_does_not_suppress_the_first_logical_ticks():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(10)).named("fast")
        slow = (Relay() @ Rate(10)).named("slow")
        fast.then(slow, sync=Latest())
    pipe.step(now=3.0)
    res = pipe.run_logical(0.2)
    assert _times(res, "fast") == pytest.approx([0.0, 0.1])
