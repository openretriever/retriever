"""
06 Feedback Loops — Event-Driven Replanning (minimal)

Key idea: in Retriever, "event-driven" can be expressed by only publishing an
output field when an event occurs. Downstream `Trigger("field")` clocks then
only fire on those event messages.

This is the canonical minimal event-driven replanning tutorial.

Graph:
  RobotSim @ Rate ──▶ ObstacleMonitor @ Trigger("obstacle") ──▶ Replanner @ Trigger("reason") ──▶ PrintPlan

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.08_event_driven_replan --backend multiprocessing --duration 2
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.08_event_driven_replan --backend dora --duration 2
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Trigger, io


@io
class RobotState:
    position: float
    goal: float
    obstacle: bool


@io
class ReplanRequest:
    reason: str


@io
class Plan:
    command: str


class RobotSim(Flow[None, RobotState]):
    """Tiny deterministic simulator that injects an obstacle event at a fixed step."""

    GOAL = 10.0
    OBSTACLE_AT_STEP = 5

    def reset(self) -> None:
        self._step = 0
        self._pos = 0.0

    def step(self, _):  # type: ignore[override]
        self._step += 1

        # Move forward unless we are "blocked".
        obstacle = self._step == self.OBSTACLE_AT_STEP
        if not obstacle:
            self._pos += 1.0

        return RobotState(position=self._pos, goal=self.GOAL, obstacle=obstacle)


class ObstacleMonitor(Flow[RobotState, ReplanRequest]):
    """
    Emits a `reason` only when an obstacle is detected.

    When no obstacle is present, returns an empty ReplanRequest (all None fields),
    and therefore publishes *no message* on `reason`.
    """

    def reset(self) -> None:
        self._events = 0

    def step(self, input: RobotState) -> ReplanRequest:
        if input.obstacle:
            self._events += 1
            return ReplanRequest(reason=f"obstacle_detected event={self._events}")
        return ReplanRequest()


class Replanner(Flow[ReplanRequest, Plan]):
    """Build a new plan when asked."""

    def reset(self) -> None:
        self._replans = 0

    def step(self, input: ReplanRequest) -> Plan:
        self._replans += 1
        return Plan(command=f"REPLAN[{self._replans}] because={input.reason}")


class PrintPlan(Flow[Plan, None]):
    def step(self, input: Plan) -> None:
        print(f"[plan] {input.command}")
        return None


def build_pipeline(*, hz: float) -> Pipeline:
    pipe = Pipeline("event_driven_replan")

    sim = RobotSim() @ Rate(hz=hz)
    monitor = ObstacleMonitor() @ Trigger("obstacle")
    replanner = Replanner() @ Trigger("reason")
    printer = PrintPlan() @ Trigger("command")

    pipe.connect(sim, monitor, sync=Latest())      # state -> monitor
    pipe.connect(monitor, replanner, sync=Latest())  # request -> plan (event-driven via publish-on-signal)
    pipe.connect(replanner, printer, sync=Latest())  # plan -> stdout

    return pipe


def main() -> None:
    ap = argparse.ArgumentParser(description="Event-driven replanning demo.")
    ap.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--duration", type=float, default=2.0)
    args = ap.parse_args()

    pipe = build_pipeline(hz=args.hz)
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()
