"""
Advanced time trigger patterns (runtime-aligned).

Covers:
1) Conditional one-shot trigger with deadline
2) Timeout watchdog trigger
3) Recurring timer with explicit reset events

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.18_advanced_time_patterns --steps 20 --dt 0.2
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io


@io
class Tick:
    step_idx: int | None = None
    t_sim: float | None = None


@io
class Conditions:
    step_idx: int | None = None
    t_sim: float | None = None
    sensor_ok: bool | None = None
    heartbeat_ok: bool | None = None
    reset_requested: bool | None = None


@io
class TimerEvent:
    event: str | None = None
    pattern: str | None = None
    status: str | None = None
    t_sim: float | None = None


class SimClock(Flow[None, Tick]):
    def __init__(self, *, dt: float):
        super().__init__()
        self.dt = float(dt)

    def init_config(self) -> dict:
        return {"dt": self.dt}

    def reset(self) -> None:
        self._step = 0
        self._t_sim = 0.0

    def step(self, _):  # type: ignore[override]
        self._step += 1
        self._t_sim += self.dt
        return Tick(step_idx=self._step, t_sim=self._t_sim)


class ConditionScript(Flow[Tick, Conditions]):
    """
    Deterministic mock conditions:
    - sensor becomes healthy after step 6
    - heartbeat drops in two outage windows
    - reset requests at fixed steps
    """

    def step(self, input: Tick) -> Conditions:
        if input.step_idx is None or input.t_sim is None:
            return Conditions()

        step = int(input.step_idx)
        sensor_ok = step >= 6
        heartbeat_ok = not (8 <= step <= 11 or 16 <= step <= 17)
        reset_requested = step in {9, 14}

        return Conditions(
            step_idx=step,
            t_sim=float(input.t_sim),
            sensor_ok=sensor_ok,
            heartbeat_ok=heartbeat_ok,
            reset_requested=reset_requested,
        )


class ConditionalDeadlineTrigger(Flow[Conditions, TimerEvent]):
    """Fire once at deadline and report whether the condition was met in time."""

    def __init__(self, *, deadline_s: float, event_name: str):
        super().__init__()
        self.deadline_s = float(deadline_s)
        self.event_name = event_name

    def init_config(self) -> dict:
        return {"deadline_s": self.deadline_s, "event_name": self.event_name}

    def reset(self) -> None:
        self._start_t = None
        self._condition_seen = False
        self._fired = False

    def step(self, input: Conditions) -> TimerEvent:
        if input.t_sim is None:
            return TimerEvent()
        t_sim = float(input.t_sim)

        if self._start_t is None:
            self._start_t = t_sim

        if bool(input.sensor_ok):
            self._condition_seen = True

        if self._fired:
            return TimerEvent()

        if t_sim - self._start_t >= self.deadline_s:
            self._fired = True
            status = "condition_met" if self._condition_seen else "condition_missed"
            return TimerEvent(
                event=self.event_name,
                pattern="conditional_deadline",
                status=status,
                t_sim=t_sim,
            )

        return TimerEvent()


class HeartbeatTimeoutTrigger(Flow[Conditions, TimerEvent]):
    """Fire once if heartbeat stays absent longer than timeout."""

    def __init__(self, *, timeout_s: float, event_name: str):
        super().__init__()
        self.timeout_s = float(timeout_s)
        self.event_name = event_name

    def init_config(self) -> dict:
        return {"timeout_s": self.timeout_s, "event_name": self.event_name}

    def reset(self) -> None:
        self._last_heartbeat_ok_t = None
        self._fired = False

    def step(self, input: Conditions) -> TimerEvent:
        if input.t_sim is None:
            return TimerEvent()
        t_sim = float(input.t_sim)

        if self._last_heartbeat_ok_t is None:
            self._last_heartbeat_ok_t = t_sim

        if bool(input.heartbeat_ok):
            self._last_heartbeat_ok_t = t_sim
            return TimerEvent()

        if self._fired:
            return TimerEvent()

        if t_sim - self._last_heartbeat_ok_t >= self.timeout_s:
            self._fired = True
            return TimerEvent(
                event=self.event_name,
                pattern="timeout_watchdog",
                status="timeout_expired",
                t_sim=t_sim,
            )
        return TimerEvent()


class RecurringResetTrigger(Flow[Conditions, TimerEvent]):
    """
    Fire a recurring event every period.
    Explicit reset requests restart the period clock.
    """

    def __init__(self, *, period_s: float, event_name: str):
        super().__init__()
        self.period_s = float(period_s)
        self.event_name = event_name

    def init_config(self) -> dict:
        return {"period_s": self.period_s, "event_name": self.event_name}

    def reset(self) -> None:
        self._anchor_t = None
        self._count = 0

    def step(self, input: Conditions) -> TimerEvent:
        if input.t_sim is None:
            return TimerEvent()
        t_sim = float(input.t_sim)

        if self._anchor_t is None:
            self._anchor_t = t_sim
            return TimerEvent()

        if bool(input.reset_requested):
            self._anchor_t = t_sim
            return TimerEvent(
                event=self.event_name,
                pattern="recurring_reset",
                status="timer_reset",
                t_sim=t_sim,
            )

        if t_sim - self._anchor_t >= self.period_s:
            self._count += 1
            self._anchor_t = t_sim
            return TimerEvent(
                event=f"{self.event_name}_{self._count}",
                pattern="recurring_reset",
                status="timer_fired",
                t_sim=t_sim,
            )

        return TimerEvent()


class EventPrinter(Flow[TimerEvent, None]):
    def __init__(self, *, channel: str):
        super().__init__()
        self.channel = channel

    def init_config(self) -> dict:
        return {"channel": self.channel}

    def step(self, input: TimerEvent) -> None:
        if (
            input.event is None
            or input.pattern is None
            or input.status is None
            or input.t_sim is None
        ):
            return None

        print(
            f"[{self.channel}] t={input.t_sim:4.2f}s "
            f"event={input.event} pattern={input.pattern} status={input.status}"
        )
        return None


def build_pipeline(
    *,
    dt: float,
    conditional_deadline_s: float,
    heartbeat_timeout_s: float,
    recurring_period_s: float,
) -> Pipeline:
    pipe = Pipeline("advanced_time_patterns")
    clock_rate = 1.0 / max(dt, 1e-6)

    clock = SimClock(dt=dt) @ Rate(hz=clock_rate)
    conditions = ConditionScript() @ Trigger("t_sim")

    conditional = ConditionalDeadlineTrigger(
        deadline_s=conditional_deadline_s, event_name="sensor_calibration"
    ) @ Trigger("step_idx")
    timeout = HeartbeatTimeoutTrigger(
        timeout_s=heartbeat_timeout_s, event_name="heartbeat_watchdog"
    ) @ Trigger("step_idx")
    recurring = RecurringResetTrigger(
        period_s=recurring_period_s, event_name="status_report"
    ) @ Trigger("step_idx")

    conditional_sink = EventPrinter(channel="conditional") @ Trigger("event")
    timeout_sink = EventPrinter(channel="timeout") @ Trigger("event")
    recurring_sink = EventPrinter(channel="recurring") @ Trigger("event")

    pipe.connect(clock, conditions, sync=Latest())
    pipe.connect(conditions, conditional, sync=Latest())
    pipe.connect(conditions, timeout, sync=Latest())
    pipe.connect(conditions, recurring, sync=Latest())
    pipe.connect(conditional, conditional_sink, sync=Latest())
    pipe.connect(timeout, timeout_sink, sync=Latest())
    pipe.connect(recurring, recurring_sink, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Advanced time trigger patterns tutorial.")
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--dt", type=float, default=0.2)
    p.add_argument("--conditional-deadline", type=float, default=1.0)
    p.add_argument("--heartbeat-timeout", type=float, default=0.6)
    p.add_argument("--recurring-period", type=float, default=0.8)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(
        dt=args.dt,
        conditional_deadline_s=args.conditional_deadline,
        heartbeat_timeout_s=args.heartbeat_timeout,
        recurring_period_s=args.recurring_period,
    )

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
