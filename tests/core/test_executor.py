"""
Tests for LocalExecutor with both pure and effectful computations.

This file tests the executor functionality with Flow graphs,
including both pure computations and stateful operations.
"""

from retriever.flow import Flow, Arrow
from retriever.executor import LocalExecutor
from retriever.types import Eff, pure


def test_executor_pure():
    """Tests the executor with a pure function graph using Flow."""
    add_one = Flow.from_module(lambda x: x + 1)
    double = Flow.from_module(lambda x: x * 2)
    flow = add_one >> double  # (10 + 1) * 2 = 22
    executor = LocalExecutor()
    result = executor.run(flow, 10)
    assert result == 22


def test_executor_effectful_then():
    """Tests the executor with an effectful `then` composition."""

    def add_and_log(x: int) -> Eff[list[str], int]:
        def run(s: list[str]) -> tuple[int, list[str]]:
            return (x + 1, s + [f"Added 1 to {x}"])
        return Eff(run)

    def double_and_log(x: int) -> Eff[list[str], int]:
        def run(s: list[str]) -> tuple[int, list[str]]:
            return (x * 2, s + [f"Doubled {x}"])
        return Eff(run)

    flow = Flow.from_module(add_and_log) >> Flow.from_module(double_and_log)
    executor = LocalExecutor()
    result, log = executor.run_eff(flow, 10, [])

    assert result == 22  # (10 + 1) * 2
    assert log == ["Added 1 to 10", "Doubled 11"]


def test_executor_effectful_fanout():
    """Tests the executor with an effectful `fanout` composition."""

    def add_and_log(x: int) -> Eff[list[str], int]:
        def run(s: list[str]) -> tuple[int, list[str]]:
            return (x + 1, s + ["Added 1"])
        return Eff(run)

    def double_and_log(x: int) -> Eff[list[str], int]:
        def run(s: list[str]) -> tuple[int, list[str]]:
            return (x * 2, s + ["Doubled"])
        return Eff(run)

    flow = Flow.from_module(add_and_log) & Flow.from_module(double_and_log)
    executor = LocalExecutor()
    result, log = executor.run_eff(flow, 10, [])

    assert result == (11, 20)
    assert log == ["Added 1", "Doubled"]


def test_backward_compatibility():
    """Tests that Arrow syntax still works with deprecation warnings."""
    import pytest
    
    with pytest.warns(DeprecationWarning):
        add_one = Arrow.arr(lambda x: x + 1)
        double = Arrow.arr(lambda x: x * 2)
        arrow = add_one >> double
    
    executor = LocalExecutor()
    result = executor.execute_sync(arrow, 10)  # Use old API for backward compatibility test
    assert result == 22 