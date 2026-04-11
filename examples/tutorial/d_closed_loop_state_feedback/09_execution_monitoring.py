"""
06 Feedback Loops — Execution Monitoring (minimal)

Key idea: a monitor can run continuously (or on every state update) and only emit
an *event* when something goes wrong.

This is the canonical minimal execution-monitoring tutorial.

Graph:
  RobotSim @ Rate ──▶ ExecutionMonitor @ Rate ──▶ PrintAlert @ Trigger("alert")

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.09_execution_monitoring --backend multiprocessing --duration 3
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.09_execution_monitoring --backend dora --duration 3
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
@dataclass
class RobotState:
    position: float
    goal: float
    velocity: float
    goal_reached: bool


@io
@dataclass
class MonitorEvent:
    alert: str


class RobotSim(Flow[None, RobotState]):
    """
    Deterministic "execution" simulator.

    Produces a short sequence with one stuck interval (velocity ~ 0 while far from goal),
    then recovers and reaches the goal.
    """

    GOAL = 5.0
    STUCK_AT_STEP = 5
    STUCK_STEPS = 3

    def reset(self) -> None:
        self._step = 0
        self._pos = 1.0

    def step(self, _):  # type: ignore[override]
        self._step += 1

        # Default: move forward.
        vel = 1.0

        # Inject a "stuck" period.
        if self.STUCK_AT_STEP <= self._step < self.STUCK_AT_STEP + self.STUCK_STEPS:
            vel = 0.05
        else:
            self._pos += 0.5

        goal_reached = abs(self.GOAL - self._pos) <= 0.05
        return RobotState(position=self._pos, goal=self.GOAL, velocity=vel, goal_reached=goal_reached)


class ExecutionMonitor(Flow[RobotState, MonitorEvent]):
    """
    Continuous monitor: emit an alert when the system looks "stuck".

    Event-driven output: returns `MonitorEvent()` with no signals when OK.
    """

    STUCK_VEL = 0.1
    FAR_DIST = 0.5

    def reset(self) -> None:
        self._alerts = 0

    def step(self, input: RobotState) -> MonitorEvent:
        # On multi-process backends, periodic (Rate) nodes may execute before any upstream
        # data has arrived. Treat missing signals as "no event".
        if (
            input.goal is None
            or input.position is None
            or input.velocity is None
            or input.goal_reached is None
        ):
            return MonitorEvent()

        if input.goal_reached:
            return MonitorEvent()

        far = abs(float(input.goal) - float(input.position)) > self.FAR_DIST
        stuck = float(input.velocity) < self.STUCK_VEL
        if stuck and far:
            self._alerts += 1
            return MonitorEvent(alert=f"STUCK alert={self._alerts} pos={input.position:.2f} vel={input.velocity:.2f}")

        return MonitorEvent()


class PrintAlert(Flow[MonitorEvent, None]):
    def step(self, input: MonitorEvent) -> None:
        print(f"[monitor] {input.alert}")
        return None


def build_pipeline(*, hz: float) -> Pipeline:
    pipe = Pipeline("execution_monitoring")

    sim = RobotSim() @ Rate(hz=hz)
    # Monitoring is *continuous* (periodic). It samples the latest RobotState and only emits
    # an event when execution looks unhealthy.
    monitor = ExecutionMonitor() @ Rate(hz=hz)
    printer = PrintAlert() @ Trigger("alert")

    pipe.connect(sim, monitor, sync=Latest())
    pipe.connect(monitor, printer, sync=Latest())

    return pipe


def main() -> None:
    ap = argparse.ArgumentParser(description="Execution monitoring demo (event-driven alerts).")
    ap.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--duration", type=float, default=3.0)
    args = ap.parse_args()

    pipe = build_pipeline(hz=args.hz)
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()
