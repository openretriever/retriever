"""Regression coverage for synchronized clock construction and scheduling."""

import pytest

from retriever._internal import as_tagged
from retriever.error import ErrCode, FlowError
from retriever.flow.clock import Synchronized, Trigger
from retriever.ir.core import IRNode


def test_synchronized_preserves_positional_fields_and_tolerance():
    clock = Synchronized("a", "b", tolerance=0.25)

    assert isinstance(clock, Trigger)
    assert clock.fields == ["a", "b"]
    assert clock.tolerance == 0.25
    assert repr(clock) == "Synchronized(on=['a', 'b'], tol=0.25)"


def test_synchronized_requires_at_least_one_field():
    with pytest.raises(FlowError) as excinfo:
        Synchronized()

    assert excinfo.value.code == ErrCode.FLOW_CLOCK_INVALID


def test_synchronized_clock_round_trip_preserves_fields_and_tolerance():
    clock = Synchronized("a", "b", tolerance=0.25)

    restored = IRNode.instantiate_clock({"clock": as_tagged(clock)})

    assert isinstance(restored, Synchronized)
    assert restored.fields == ["a", "b"]
    assert restored.tolerance == 0.25


class BufferedInput:
    def __init__(self, timestamps):
        self.timestamps = timestamps

    readers = []

    def get_all(self):
        return [(timestamp, None) for timestamp in self.timestamps]

    def drain(self):
        pass

    def new_arrival(self):
        # A plain Trigger would fire even when the timestamps do not match.
        return True


@pytest.fixture(params=["multiprocessing", "dora"])
def scheduler(request, monkeypatch):
    clock = Synchronized("a", "b", tolerance=1.0)
    if request.param == "multiprocessing":
        from retriever.rt.backend.multiprocessing import scheduler as scheduler_module

        # Empty readers have no incoming transport data. Keep the timeout path
        # deterministic without sleeping; still exercise next() dispatch.
        monkeypatch.setattr(scheduler_module, "connection_wait", lambda *args, **kwargs: [])
        return scheduler_module.MPScheduler(clock)

    from retriever.rt.backend.dora.scheduler import DoraScheduler

    return DoraScheduler(clock)


def test_synchronized_schedulers_currently_require_exact_timestamps(scheduler):
    # A large tolerance must not silently change existing scheduler semantics.
    inputs = {"a": BufferedInput([1.0]), "b": BufferedInput([1.01])}
    assert not scheduler.next(inputs).should_execute

    inputs["b"] = BufferedInput([1.0])
    result = scheduler.next(inputs)
    assert result.should_execute
    assert result.fields_to_sample == ["a", "b"]
    assert result.now == 1.0
    assert not scheduler.next(inputs).should_execute


def test_synchronized_schedulers_skip_nonincreasing_timestamps(scheduler):
    from retriever.rt.backend.multiprocessing.scheduler import MPScheduler

    inputs = {field: BufferedInput([-1.0, 0.0, 2.0, 3.0]) for field in ("a", "b")}
    # Multiprocessing starts at zero; Dora starts before any timestamp.
    expected = [2.0, 3.0] if isinstance(scheduler, MPScheduler) else [-1.0, 0.0, 2.0, 3.0]
    for timestamp in expected:
        result = scheduler.next(inputs)
        assert result.should_execute
        assert result.now == timestamp
    assert not scheduler.next(inputs).should_execute

    # Matching data that arrives behind the last executed timestamp is skipped.
    inputs = {field: BufferedInput([1.0, 3.0]) for field in ("a", "b")}
    assert not scheduler.next(inputs).should_execute
