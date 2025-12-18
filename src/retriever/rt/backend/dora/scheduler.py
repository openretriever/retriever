"""
DoraScheduler - Scheduler implementation for dora backend.

Non-blocking event-driven scheduling with external tick events.
"""

import time
from typing import Dict, Any, Optional

from retriever.flow.clock import Clock, Rate, Trigger, Hybrid
from retriever.rt.backend.interface import Scheduler, ScheduleResult, Subscriber
from retriever.error import RTError, ErrCode


import logging
logger = logging.getLogger(__name__)


class DoraScheduler(Scheduler):
    """
    Scheduler implementation for dora backend.

    Attributes:
        clock: Clock configuration
        _tick_received: Tick event flag (Rate/Hybrid)
        _last_tick_time: Timestamp of last processed tick
        _min_interval: Minimum interval between ticks (seconds)
    """

    def __init__(self, clock: Clock):
        """Initialize scheduler with clock configuration."""
        self.clock = clock
        self._tick_received = False
        self._pending_tick_ts: Optional[float] = None
        self._last_tick_ts: Optional[float] = None
        self._last_lag_log: float = 0.0

        if isinstance(clock, (Rate, Hybrid)):
            self._min_interval = 1.0 / clock.hz
        else:
            self._min_interval = 0.0

    def reset(self) -> None:
        """Reset scheduler timing state."""
        self._tick_received = False
        self._pending_tick_ts = None
        self._last_tick_ts = None

    @staticmethod
    def _extract_tick_ts(event: Dict[str, Any]) -> float:
        """
        Extract a float seconds timestamp from a dora event.

        Our publishers set `metadata["_timestamp"] = str(time.time())`.
        Dora timers are expected to include the same key; if missing/unparseable,
        fall back to wall clock.
        """
        meta = event.get("metadata") or {}
        raw = meta.get("_timestamp")
        if raw is None:
            return time.time()
        try:
            return float(raw)
        except Exception:
            return time.time()

    def _on_lag_policy(self) -> str:
        return Rate._normalize_on_lag(getattr(self.clock, "on_lag", "warn"))

    def push_tick_event(self, event: Dict[str, Any]) -> None:
        """
        Called by executor when tick event arrives.

        Skips ticks that arrive too early based on configured rate.
        Uses 0.9 threshold to allow 10% timing jitter.

        Args:
            event: Dora tick event dict
        """
        current_time = time.time()
        tick_ts = self._extract_tick_ts(event)
        policy = self._on_lag_policy()

        # Drop stale tick events (prevents unbounded backlog on Dora when nodes can't keep up).
        if policy in ("drop", "warn", "error"):
            lag_s = current_time - tick_ts
            if lag_s >= self._min_interval:
                if policy == "error":
                    raise RTError(
                        ErrCode.RT_SCHEDULER_LAG,
                        "dora tick lag exceeded one interval",
                        hz=getattr(self.clock, "hz", None),
                        interval=self._min_interval,
                        lag_s=lag_s,
                        tick_ts=tick_ts,
                    )

                if policy == "warn" and current_time - self._last_lag_log >= 1.0:
                    logger.warning(
                        "Dropping stale dora tick (lag %.3fs >= %.3fs); node can't keep up with target hz",
                        lag_s,
                        self._min_interval,
                    )
                    self._last_lag_log = current_time

                return

        if self._last_tick_ts is not None:
            elapsed = tick_ts - self._last_tick_ts
            threshold = self._min_interval * 0.9

            if elapsed < threshold:
                logger.debug(
                    f"Skipping early tick: {elapsed:.3f}s < {threshold:.3f}s"
                )
                return

        self._tick_received = True
        self._pending_tick_ts = tick_ts

    def next(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """
        Advance to next execution point.

        Non-blocking check called after each dora event.

        Args:
            inputs: Dict mapping port name to Subscriber

        Returns:
            ScheduleResult with execution decision and fields to sample
        """
        if isinstance(self.clock, Rate):
            return self._check_rate()
        elif isinstance(self.clock, Trigger):
            return self._check_trigger(inputs)
        elif isinstance(self.clock, Hybrid):
            return self._check_hybrid(inputs)
        else:
            raise ValueError(f"Unknown clock type: {type(self.clock)}")

    def _check_rate(self) -> ScheduleResult:
        """Check if tick event received."""
        if self._tick_received:
            self._tick_received = False
            now = self._pending_tick_ts or time.time()
            self._pending_tick_ts = None
            self._last_tick_ts = now
            return ScheduleResult(
                should_execute=True,
                fields_to_sample=self.clock.fields,
                now=now,
            )
        return ScheduleResult(should_execute=False)

    def _check_trigger(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """Check if any trigger field has new data."""
        for field in self.clock.fields:
            if field in inputs and inputs[field].new_arrival():
                return ScheduleResult(
                    should_execute=True,
                    fields_to_sample=[field],
                    now=time.time(),
                )
        return ScheduleResult(should_execute=False)

    def _check_hybrid(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """Check tick or trigger fields."""
        # Check tick first
        if self._tick_received:
            self._tick_received = False
            now = self._pending_tick_ts or time.time()
            self._pending_tick_ts = None
            self._last_tick_ts = now
            return ScheduleResult(
                should_execute=True,
                fields_to_sample=self.clock.rate_fields,
                now=now,
            )

        # Check trigger fields
        for field in self.clock.trigger_fields:
            if field in inputs and inputs[field].new_arrival():
                return ScheduleResult(
                    should_execute=True,
                    fields_to_sample=[field],
                    now=time.time(),
                )

        return ScheduleResult(should_execute=False)
