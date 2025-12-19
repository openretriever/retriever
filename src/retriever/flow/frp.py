"""
FRP Combinators and Utilities.

This module provides high-level functional reactive programming combinators
built on top of the core runtime primitives. These allow users to compose
complex temporal behaviors from simple blocks.
"""

from typing import TypeVar, Any, Callable
from retriever.rt.frp import Behavior, EventStream

T = TypeVar("T")


def constant_behavior(value: T) -> Behavior[T]:
    """Create behavior that always returns the same value."""
    return Behavior(lambda t: value)


def time_behavior() -> Behavior[float]:
    """Create behavior that returns current time."""
    return Behavior(lambda t: t)


def switch_behavior(control: Behavior[bool], 
                   true_behavior: Behavior[T], 
                   false_behavior: Behavior[T]) -> Behavior[T]:
    """Switch between two behaviors based on control behavior."""
    def switched_sample(t: float) -> T:
        if control.at(t):
            return true_behavior.at(t)
        else:
            return false_behavior.at(t)
    
    return Behavior(switched_sample)


def until_event(behavior: Behavior[T], 
                event_stream: EventStream[Any],
                default_value: T) -> Behavior[T]:
    """
    Behavior that switches to default value (or stops) when event occurs.
    
    Checks for very recent events to trigger the switch.
    """
    def until_sample(t: float) -> T:
        # Check window suitable for the tick rate (e.g. 1ms)
        recent_events = event_stream.get_recent(t, window=0.001) 
        if recent_events:
            return default_value
        else:
            return behavior.at(t)
    
    return Behavior(until_sample)
