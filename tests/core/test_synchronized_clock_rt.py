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
