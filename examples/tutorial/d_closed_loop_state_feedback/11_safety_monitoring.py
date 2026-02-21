"""
06 Feedback Loops — Safety monitoring (event-driven)

Key idea: run a fast safety monitor continuously, but only emit an action when
the safety status changes. This keeps safety logic simple and deterministic.

This is a runtime-aligned extraction of the legacy idea in:
`examples/legacy/06_feedback_loops/03_safety_monitoring.py`.

Graph:
  SafetyScenario @ Rate ──▶ SafetyMonitor @ Rate ──▶ SafetyAction @ Trigger("level")

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.11_safety_monitoring --steps 12 --dt 0.1
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class SafetySample:
    t_sim: float | None = None
    velocity: float | None = None
    force: float | None = None


@io
class SafetyEvent:
    level: str | None = None
    message: str | None = None
    t_sim: float | None = None


@io
class SafetyAction:
    action: str | None = None
    t_sim: float | None = None


class SafetyScenario(Flow[None, SafetySample]):
    """Deterministic safety scenario with one warning and one emergency spike."""

    def __init__(self, *, dt: float):
        super().__init__()
        self.dt = float(dt)

    def init_config(self) -> dict:
        return {"dt": self.dt}

    def init(self) -> None:
        self._step = 0

    def reset(self) -> None:
        self._step = 0

    def run(self, _):  # type: ignore[override]
        self._step += 1
        t_sim = self._step * self.dt

        # Base "safe" values.
        velocity = 1.0
        force = 25.0

        # Inject a speed warning, then a force emergency.
        if 4 <= self._step <= 5:
            velocity = 2.6
        if self._step == 9:
            force = 92.0

        return SafetySample(t_sim=t_sim, velocity=velocity, force=force)


class SafetyMonitor(Flow[SafetySample, SafetyEvent]):
    """Continuous safety checks; emits only on status change."""

    FORCE_LIMIT = 80.0
    SPEED_LIMIT = 2.0

    def init(self) -> None:
        self._last_level: str | None = None

    def reset(self) -> None:
        self._last_level = None

    def run(self, input: SafetySample) -> SafetyEvent:
        # Rate flows can run before upstream data arrives; treat missing fields as no-op.
        if input.velocity is None or input.force is None or input.t_sim is None:
            return SafetyEvent()

        level = "SAFE"
        message = "Safe"
        if float(input.force) > self.FORCE_LIMIT:
            level = "EMERGENCY"
            message = "High force detected"
        elif float(input.velocity) > self.SPEED_LIMIT:
            level = "WARNING"
            message = "Overspeed detected"

        # Only emit when the safety level changes.
        if level == self._last_level:
            return SafetyEvent()

        self._last_level = level
        return SafetyEvent(level=level, message=message, t_sim=float(input.t_sim))


class SafetyActionMapper(Flow[SafetyEvent, SafetyAction]):
    """Map a safety event to an action command."""

    def run(self, input: SafetyEvent) -> SafetyAction:
        if input.level is None or input.t_sim is None:
            return SafetyAction()

        if input.level == "EMERGENCY":
            action = "STOP"
        elif input.level == "WARNING":
            action = "SLOW_DOWN"
        else:
            action = "CONTINUE"

        return SafetyAction(action=action, t_sim=float(input.t_sim))


class ActionPrinter(Flow[SafetyAction, None]):
    def run(self, input: SafetyAction) -> None:
        if input.action is None or input.t_sim is None:
            return None
        print(f"[safety] t={input.t_sim:4.2f}s action={input.action}")
        return None


def build_pipeline(*, dt: float) -> Pipeline:
    pipe = Pipeline("safety_monitoring")
    hz = 1.0 / max(dt, 1e-6)

    scenario = SafetyScenario(dt=dt) @ Rate(hz=hz)
    monitor = SafetyMonitor() @ Rate(hz=hz)
    mapper = SafetyActionMapper() @ Trigger("level")
    printer = ActionPrinter() @ Trigger("action")

    pipe.connect(scenario, monitor, sync=Latest())
    pipe.connect(monitor, mapper, sync=Latest())
    pipe.connect(mapper, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Safety monitoring demo (event-driven actions).")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(dt=args.dt)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
