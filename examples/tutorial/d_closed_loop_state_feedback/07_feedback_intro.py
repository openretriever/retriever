"""
06 Feedback Loops — Minimal Closed-Loop Intro

Goal: show the essential feedback loop pattern with the refactored runtime:

  Plant @ Rate  ──obs──▶  Controller @ Trigger  ──action──▶  Plant
       └───────────────────────────────(cycle)───────────────────────────────┘

This is a runtime-aligned extraction of the idea in legacy:
`examples/legacy/06_feedback_loops/00_simple_feedback_intro.py`.

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro --backend multiprocessing --duration 3
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro --backend dora --on-lag panic --duration 3
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
@dataclass
class Action:
    action: float | None = None


@dataclass
class Transition:
    x: float
    u: float
    error: float
    reward: float
    done: bool


@io
@dataclass
class Observation:
    transition: Transition


class IntegratorPlant(Flow[Action, Observation]):
    """
    A tiny "env.step"-like plant:

      x_{t+1} = x_t + dt * u_t
      reward = -error^2
    """

    TARGET = 1.0
    U_MAX = 2.0
    DONE_TOL = 0.05
    ENV_DELAY_S = 0.0

    def init(self) -> None:
        self.x = 0.0
        self.step_count = 0

    def run(self, input: Action) -> Observation:
        if self.ENV_DELAY_S > 0:
            time.sleep(self.ENV_DELAY_S)

        self.step_count += 1

        u = 0.0 if input.action is None else float(input.action)
        u = max(-self.U_MAX, min(self.U_MAX, u))

        # Discrete-time "plant": keep this independent of wall-clock dt so the demo
        # stays easy to reason about even when the backend can't hit the target Hz.
        self.x = float(self.x + u)
        err = float(self.TARGET - self.x)
        reward = float(-(err * err))
        done = abs(err) <= self.DONE_TOL

        return Observation(transition=Transition(x=self.x, u=u, error=err, reward=reward, done=done))


class PController(Flow[Observation, Action]):
    """u = k_p * error, with optional controller delay."""

    K_P = 1.5
    CTRL_DELAY_S = 0.0

    def run(self, input: Observation) -> Action:
        if self.CTRL_DELAY_S > 0:
            time.sleep(self.CTRL_DELAY_S)

        tr = input.transition
        u = self.K_P * float(tr.error)
        u = max(-IntegratorPlant.U_MAX, min(IntegratorPlant.U_MAX, u))
        return Action(action=u)


class PrintStep(Flow[Observation, None]):
    def init(self) -> None:
        self._i = 0

    def run(self, input: Observation) -> None:
        self._i += 1
        tr = input.transition
        print(
            f"[step {self._i:03d}] x={tr.x:+.3f} u={tr.u:+.3f} err={tr.error:+.3f} "
            f"reward={tr.reward:+.3f} done={tr.done}"
        )
        return None


def build_pipeline(
    *,
    hz: float,
    on_lag: str,
) -> Pipeline:
    pipe = Pipeline("feedback_intro")

    plant = IntegratorPlant() @ Rate(hz=hz, on_lag=on_lag)
    controller = PController() @ Trigger("transition")
    printer = PrintStep() @ Trigger("transition")

    # Closed-loop wiring:
    #   plant -> controller (obs)
    #   controller -> plant (action)
    pipe.connect(plant, controller, sync=Latest())
    pipe.connect(controller, plant, sync=Latest())
    pipe.connect(plant, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Minimal closed-loop feedback demo (P-controller).")
    ap.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--hz", type=float, default=10.0, help="Plant tick rate (Hz)")
    ap.add_argument(
        "--on-lag",
        default="warn",
        choices=["drop", "warn", "error", "panic", "catch_up"],
        help="Rate lag policy (panic is an alias for error)",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    args.on_lag = Rate._normalize_on_lag(args.on_lag)

    print(
        f"[config] backend={args.backend} hz={args.hz:g} on_lag={args.on_lag} "
        f"(target={IntegratorPlant.TARGET:g} k_p={PController.K_P:g} "
        f"env_delay={IntegratorPlant.ENV_DELAY_S:.2f}s ctrl_delay={PController.CTRL_DELAY_S:.2f}s)"
    )

    pipe = build_pipeline(
        hz=args.hz,
        on_lag=args.on_lag,
    )
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()
