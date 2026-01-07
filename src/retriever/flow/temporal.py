"""
Core Temporal Primitives for Retriever Flow.

This module provides general-purpose timing and coordination utilities that serve
as the foundation for time-aware execution.
"""

from dataclasses import dataclass, field
import time
from typing import List, Optional, Deque, TYPE_CHECKING
from collections import deque

if TYPE_CHECKING:
    from retriever.flow.handle import FlowHandle

from retriever.flow.handle import FlowHandle

# Alias for backward compatibility and semantic clarity
TemporalFlow = FlowHandle


@dataclass
class ExecutionMetrics:
    """Metrics captured during execution."""
    duration_s: float
    timestamp: float
    violations: List["TimingViolation"] = field(default_factory=list)


@dataclass
class TimingViolation:
    """Record of a timing constraint violation."""
    expected_s: float
    actual_s: float
    type: str  # "deadline", "period"


@dataclass
class TimeConstraint:
    """Configuration for timing constraints."""
    deadline_s: Optional[float] = None
    period_s: Optional[float] = None


class ExecutionTimer:
    """
    Timer for tracking execution duration and enforcing constraints.
    """
    def __init__(self, constraints: Optional[TimeConstraint] = None):
        self.constraints = constraints or TimeConstraint()
        self.history: Deque[float] = deque(maxlen=100)
        self._start_time: float = 0.0

    def start_execution(self) -> None:
        """Mark start of execution."""
        self._start_time = time.time()

    def end_execution(self) -> ExecutionMetrics:
        """
        Mark end of execution and calculate metrics.
        Returns metrics including any violations.
        """
        end_time = time.time()
        duration = end_time - self._start_time
        self.history.append(duration)

        violations = []
        if self.constraints.deadline_s and duration > self.constraints.deadline_s:
            violations.append(TimingViolation(
                expected_s=self.constraints.deadline_s,
                actual_s=duration,
                type="deadline"
            ))

        return ExecutionMetrics(
            duration_s=duration,
            timestamp=end_time,
            violations=violations
        )
