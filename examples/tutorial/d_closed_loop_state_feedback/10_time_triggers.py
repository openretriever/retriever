"""
06 Feedback Loops — One-shot time trigger (deterministic)

Key idea: model time-based events as a normal flow that only publishes a signal
when the timer fires. Downstream `Trigger("event")` then runs exactly once.

This is a runtime-aligned extraction of the legacy idea in:
`examples/legacy/06_feedback_loops/10_one_shot_time_triggers.py`.

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.10_time_triggers --steps 12 --dt 0.1 --delay 0.6
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class ClockOut:
    t_sim: float | None = None
    step: int | None = None


@io
class TimerEvent:
    event: str | None = None
    t_sim: float | None = None


@io
class ActionOut:
    action: str | None = None
    t_sim: float | None = None


class SimClock(Flow[None, ClockOut]):
    """Deterministic sim-time clock driven by the stepper."""

    def __init__(self, *, dt: float):
        super().__init__()
        self.dt = float(dt)

    def init_config(self) -> dict:
        return {"dt": self.dt}

    def init(self) -> None:
        self.t = 0.0
        self.step_idx = 0

    def reset(self) -> None:
        self.t = 0.0
        self.step_idx = 0

    def run(self, _):  # type: ignore[override]
        self.step_idx += 1
        self.t += self.dt
        return ClockOut(t_sim=self.t, step=self.step_idx)


class OneShotTimer(Flow[ClockOut, TimerEvent]):
    """Fire exactly once after `delay_s` since the first tick."""

    def __init__(self, *, delay_s: float, event_name: str):
        super().__init__()
        self.delay_s = float(delay_s)
        self.event_name = str(event_name)

    def init_config(self) -> dict:
        return {"delay_s": self.delay_s, "event_name": self.event_name}

    def init(self) -> None:
        self._start = None
        self._fired = False

    def reset(self) -> None:
        self._start = None
        self._fired = False

    def run(self, input: ClockOut) -> TimerEvent:
        if input.t_sim is None:
            return TimerEvent()

        t_sim = float(input.t_sim)
        if self._start is None:
            self._start = t_sim
            return TimerEvent()

        if self._fired:
            return TimerEvent()

        if t_sim - self._start >= self.delay_s:
            self._fired = True
            return TimerEvent(event=self.event_name, t_sim=t_sim)

        return TimerEvent()


class DelayedAction(Flow[TimerEvent, ActionOut]):
    """Convert a timer event into a one-shot action."""

    def run(self, input: TimerEvent) -> ActionOut:
        if input.event is None or input.t_sim is None:
            return ActionOut()
        return ActionOut(
            action=f"triggered:{input.event}",
            t_sim=float(input.t_sim),
        )


class Printer(Flow[ActionOut, None]):
    def run(self, input: ActionOut) -> None:
        if input.action is None or input.t_sim is None:
            return None
        print(f"[action] t={input.t_sim:4.2f}s {input.action}")
        return None


def build_pipeline(*, dt: float, delay_s: float, event_name: str) -> Pipeline:
    pipe = Pipeline("time_triggers_one_shot")
    clock_rate = 1.0 / max(dt, 1e-6)

    clock = SimClock(dt=dt) @ Rate(hz=clock_rate)
    timer = OneShotTimer(delay_s=delay_s, event_name=event_name) @ Trigger("t_sim")
    action = DelayedAction() @ Trigger("event")
    printer = Printer() @ Trigger("action")

    pipe.connect(clock, timer, sync=Latest())
    pipe.connect(timer, action, sync=Latest())
    pipe.connect(action, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="One-shot time trigger demo.")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--dt", type=float, default=0.1)
    p.add_argument("--delay", type=float, default=0.6)
    p.add_argument("--event", default="safety_check")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(dt=args.dt, delay_s=args.delay, event_name=args.event)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
