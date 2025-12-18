"""
MPScheduler - Scheduler implementation for multiprocessing backend.

Sleep-based timing for Rate, connection.wait() for Trigger/Hybrid.
"""

import time
from typing import Dict
from multiprocessing.connection import wait as connection_wait
from retriever.core.flow.clock import Clock, Rate, Trigger, Hybrid
from retriever.core.rt.backend.interface import Scheduler, ScheduleResult, Subscriber
from retriever.core.error import RTError, ErrCode

import logging
logger = logging.getLogger(__name__)


class MPScheduler(Scheduler):
    """
    Scheduler implementation for multiprocessing backend.

    Attributes:
        clock: Clock configuration
        next_tick: Next scheduled tick time (Rate/Hybrid only)
    """

    def __init__(self, clock: Clock):
        """Initialize scheduler with clock configuration."""
        self.clock = clock
        self.next_tick = None
        self._last_lag_log: float = 0.0

    def reset(self) -> None:
        """Reset scheduler timing state."""
        if isinstance(self.clock, (Rate, Hybrid)):
            self.next_tick = time.time()

    def _drain_all(self, inputs: Dict[str, Subscriber]) -> None:
        """Drain all input channels."""
        for channel in inputs.values():
            channel.drain()

    def _check_arrival(
        self, inputs: Dict[str, Subscriber], fields: list
    ) -> ScheduleResult:
        """Check new_arrival on fields, return result if found."""
        for field in fields:
            if field in inputs and inputs[field].new_arrival():
                return ScheduleResult(
                    should_execute=True,
                    fields_to_sample=[field],
                    now=time.time(),
                )
        return ScheduleResult(should_execute=False)

    def next(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """
        Advance to next execution point.

        Blocks until flow should execute based on clock type.

        Args:
            inputs: Dict mapping port name to Subscriber

        Returns:
            ScheduleResult with execution decision and fields to sample
        """
        if isinstance(self.clock, Rate):
            return self._next_rate(inputs)
        elif isinstance(self.clock, Trigger):
            return self._next_trigger(inputs)
        elif isinstance(self.clock, Hybrid):
            return self._next_hybrid(inputs)
        else:
            raise ValueError(f"Unknown clock type: {type(self.clock)}")

    def _next_rate(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """Sleep-based timing with drift correction."""
        if self.next_tick is None:
            self.next_tick = time.time()

        # Advance absolute target time
        self.next_tick += self.clock.interval

        now = time.time()
        sleep_time = self.next_tick - now

        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            lag_s = -sleep_time
            if lag_s >= self.clock.interval:
                missed = int(lag_s // self.clock.interval)
                policy = Rate._normalize_on_lag(getattr(self.clock, "on_lag", "warn"))

                if policy == "error":
                    raise RTError(
                        ErrCode.RT_SCHEDULER_LAG,
                        "Rate scheduler cannot keep up with requested hz",
                        hz=self.clock.hz,
                        interval=self.clock.interval,
                        lag_s=lag_s,
                        missed=missed,
                        policy=policy,
                    )

                if policy == "warn":
                    # Throttle warnings to avoid spam.
                    if now - self._last_lag_log >= 1.0:
                        logger.warning(
                            "Rate scheduler lagging by %.3fs (~%d ticks behind); dropping missed ticks",
                            lag_s,
                            missed,
                        )
                        self._last_lag_log = now

                if policy in ("drop", "warn"):
                    # Skip missed ticks: execute once "now" and schedule the next tick from now.
                    self.next_tick = now

        # Drain all inputs
        self._drain_all(inputs)

        return ScheduleResult(
            should_execute=True,
            fields_to_sample=self.clock.fields,
            now=time.time(),
        )

    def _next_trigger(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """Block on input queues until data arrives or timeout."""
        timeout = 1.0  # FIXME: hardcode
        fields = self.clock.fields

        # Check for leftover arrivals (data already in buffer)
        result = self._check_arrival(inputs, fields)
        if result.should_execute:
            return result

        # Block until any reader has data or timeout
        readers = []
        for field in fields:
            if field in inputs:
                readers.append(inputs[field].reader)
        if not connection_wait(readers, timeout=timeout):
            return ScheduleResult(should_execute=False)

        # Drain all inputs and check for arrivals
        self._drain_all(inputs)
        return self._check_arrival(inputs, fields)

    def _next_hybrid(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """Block for triggers until rate tick is due."""
        if self.next_tick is None:
            self.next_tick = time.time()

        trigger_fields = self.clock.trigger_fields

        # Check if rate tick is due
        now = time.time()
        if self.next_tick - now <= 0:
            # Rate tick fires (priority over leftover trigger)
            lag_s = now - self.next_tick
            if lag_s >= self.clock.interval:
                missed = int(lag_s // self.clock.interval)
                policy = Rate._normalize_on_lag(getattr(self.clock, "on_lag", "warn"))

                if policy == "error":
                    raise RTError(
                        ErrCode.RT_SCHEDULER_LAG,
                        "Hybrid rate scheduler cannot keep up with requested hz",
                        hz=self.clock.hz,
                        interval=self.clock.interval,
                        lag_s=lag_s,
                        missed=missed,
                        policy=policy,
                    )

                if policy == "warn":
                    if now - self._last_lag_log >= 1.0:
                        logger.warning(
                            "Hybrid rate tick lagging by %.3fs (~%d ticks behind); dropping missed ticks",
                            lag_s,
                            missed,
                        )
                        self._last_lag_log = now

                if policy in ("drop", "warn"):
                    self.next_tick = now

            self._drain_all(inputs)
            self.next_tick += self.clock.interval
            return ScheduleResult(
                should_execute=True,
                fields_to_sample=self.clock.rate_fields,
                now=time.time(),
            )

        # Check for leftover trigger arrivals (data already in buffer)
        result = self._check_arrival(inputs, trigger_fields)
        if result.should_execute:
            return result

        # Block until trigger or rate tick
        readers = []
        for field in trigger_fields:
            if field in inputs:
                readers.append(inputs[field].reader)
        time_until_tick = self.next_tick - time.time()
        connection_wait(readers, timeout=max(0, time_until_tick))

        # Drain all inputs and check for trigger arrivals
        self._drain_all(inputs)
        result = self._check_arrival(inputs, trigger_fields)
        if result.should_execute:
            return result

        # Timeout = rate tick fires
        self.next_tick += self.clock.interval
        return ScheduleResult(
            should_execute=True,
            fields_to_sample=self.clock.rate_fields,
            now=time.time()
        )
