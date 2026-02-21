"""
06 Feedback Loops — Stateful replanning (internal planner memory)

Key idea: the replanner keeps *internal* state (current plan + failure count),
but only emits a plan update when a new obstacle is detected or cleared.

This is a runtime-aligned extraction of the legacy idea in:
`examples/legacy/06_feedback_loops/04_stateful_replanning.py`.

Graph:
  ReplanScenario @ Rate ──▶ StatefulReplanner @ Rate ──▶ PlanPrinter @ Trigger("plan")

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.12_stateful_replanning --steps 10 --dt 0.2
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class WorldState:
    t_sim: float | None = None
    obstacle: bool | None = None


@io
class PlanEvent:
    plan: str | None = None
    reason: str | None = None
    failure_count: int | None = None
    t_sim: float | None = None


class ReplanScenario(Flow[None, WorldState]):
    """Deterministic obstacle schedule to trigger replanning events."""

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

        # Inject two obstacle events (rising edges).
        obstacle = self._step in (3, 7)
        return WorldState(t_sim=t_sim, obstacle=obstacle)


class StatefulReplanner(Flow[WorldState, PlanEvent]):
    """Replanner with internal state; emits only when the plan changes."""

    def init(self) -> None:
        self._current_plan = "direct_v0"
        self._failure_count = 0
        self._last_obstacle = False
        self._started = False

    def reset(self) -> None:
        self.init()

    def run(self, input: WorldState) -> PlanEvent:
        if input.obstacle is None or input.t_sim is None:
            return PlanEvent()

        obstacle = bool(input.obstacle)
        t_sim = float(input.t_sim)

        # Emit an initial plan on the first tick.
        if not self._started:
            self._started = True
            return PlanEvent(
                plan=self._current_plan,
                reason="initial",
                failure_count=self._failure_count,
                t_sim=t_sim,
            )

        # Rising edge: obstacle detected -> replan and increment failure count.
        if obstacle and not self._last_obstacle:
            self._failure_count += 1
            self._current_plan = f"detour_v{self._failure_count}"
            self._last_obstacle = True
            return PlanEvent(
                plan=self._current_plan,
                reason="obstacle_detected",
                failure_count=self._failure_count,
                t_sim=t_sim,
            )

        # Falling edge: obstacle cleared -> go back to direct plan.
        if not obstacle and self._last_obstacle:
            self._current_plan = f"direct_v{self._failure_count}"
            self._last_obstacle = False
            return PlanEvent(
                plan=self._current_plan,
                reason="obstacle_cleared",
                failure_count=self._failure_count,
                t_sim=t_sim,
            )

        return PlanEvent()


class PlanPrinter(Flow[PlanEvent, None]):
    def run(self, input: PlanEvent) -> None:
        if input.plan is None or input.t_sim is None:
            return None
        print(
            "[replan]"
            f" t={input.t_sim:4.2f}s"
            f" plan={input.plan}"
            f" reason={input.reason}"
            f" failures={input.failure_count}"
        )
        return None


def build_pipeline(*, dt: float) -> Pipeline:
    pipe = Pipeline("stateful_replanning")
    hz = 1.0 / max(dt, 1e-6)

    scenario = ReplanScenario(dt=dt) @ Rate(hz=hz)
    replanner = StatefulReplanner() @ Rate(hz=hz)
    printer = PlanPrinter() @ Trigger("plan")

    pipe.connect(scenario, replanner, sync=Latest())
    pipe.connect(replanner, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stateful replanning demo (event-driven plan updates).")
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--dt", type=float, default=0.2)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(dt=args.dt)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
