"""
Tests for Flow combinators and basic operations.

This file tests the core Flow functionality and maintains backward compatibility
tests for the deprecated Arrow terminology.
"""

from retriever.core.flow import Flow, Arrow
from retriever.core.executor import LocalExecutor
import pytest


def test_flow_then():
    """Tests the `then` combinator with Flow (new preferred syntax)."""

    def add_one(x: int) -> int:
        return x + 1

    def multiply_by_two(x: int) -> int:
        return x * 2

    flow = Flow.from_module(add_one).then(Flow.from_module(multiply_by_two))
    executor = LocalExecutor()
    result = executor.run(flow, 10)

    assert result == 22  # (10 + 1) * 2


def test_flow_fanout():
    """Tests the `fanout` combinator with Flow."""

    def add_one(x: int) -> int:
        return x + 1

    def multiply_by_two(x: int) -> int:
        return x * 2

    flow = Flow.from_module(add_one).fanout(Flow.from_module(multiply_by_two))
    executor = LocalExecutor()
    result = executor.run(flow, 10)

    assert result == (11, 20)  # (10 + 1, 10 * 2)


def test_flow_complex_composition():
    """Tests a more complex composition of `then` and `fanout` with Flow."""

    def add_one(x: int) -> int:
        return x + 1

    def multiply_by_two(x: int) -> int:
        return x * 2

    def subtract_three(x: tuple[int, int]) -> int:
        return x[0] - x[1]

    # ((10 + 1), (10 * 2)) -> 11 - 20 = -9
    flow = (
        Flow.from_module(add_one)
        .fanout(Flow.from_module(multiply_by_two))
        .then(Flow.from_module(subtract_three))
    )

    executor = LocalExecutor()
    result = executor.run(flow, 10)

    assert result == -9 


def test_flow_operator_overloading():
    """Tests the >> and & operator overloads for Flow."""

    def add_one(x: int) -> int:
        return x + 1

    def multiply_by_two(x: int) -> int:
        return x * 2

    def negate(x: int) -> int:
        return -x

    # Test >> operator (equivalent to .then())
    flow1 = Flow.from_module(add_one) >> Flow.from_module(multiply_by_two)
    
    # Test & operator (equivalent to .fanout())
    flow2 = Flow.from_module(add_one) & Flow.from_module(negate)

    executor = LocalExecutor()
    
    result1 = executor.run(flow1, 5)
    assert result1 == 12  # (5 + 1) * 2

    result2 = executor.run(flow2, 5)
    assert result2 == (6, -5)  # (5 + 1, -(5))
