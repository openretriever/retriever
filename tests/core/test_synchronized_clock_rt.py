"""Regression coverage for synchronized clock construction and scheduling."""

import pytest

from retriever.error import ErrCode, FlowError
from retriever.flow.clock import Synchronized, Trigger


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


class BufferedInput:
    def __init__(self, timestamps):
        self.timestamps = timestamps

    def get_all(self):
        return [(timestamp, None) for timestamp in self.timestamps]


@pytest.mark.parametrize("backend", ["multiprocessing", "dora"])
def test_synchronized_schedulers_currently_require_exact_timestamps(backend):
    # A large tolerance must not silently change existing scheduler semantics.
    if backend == "multiprocessing":
        from retriever.rt.backend.multiprocessing.scheduler import MPScheduler

        scheduler = MPScheduler(Synchronized("a", "b", tolerance=1.0))
    else:
        from retriever.rt.backend.dora.scheduler import DoraScheduler

        scheduler = DoraScheduler(Synchronized("a", "b", tolerance=1.0))

    inputs = {"a": BufferedInput([1.0]), "b": BufferedInput([1.01])}
    assert not scheduler._check_synchronized(inputs).should_execute

    inputs["b"] = BufferedInput([1.0])
    result = scheduler._check_synchronized(inputs)
    assert result.should_execute
    assert result.fields_to_sample == ["a", "b"]
    assert result.now == 1.0
    assert not scheduler._check_synchronized(inputs).should_execute
