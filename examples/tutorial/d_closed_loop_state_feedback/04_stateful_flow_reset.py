"""
Stateful flow + reset demo (breakpoint-friendly).

This is the runtime-aligned replacement for the legacy "state management" demos.
It demonstrates:
  - A flow that holds internal state (a counter).
  - `Flow.reset()` resetting that state.
  - The in-process stepper executing deterministically so VS Code can break inside `Flow.step()`.

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset --steps 5 --dt 0.1
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, io


@io
@dataclass
class CountOut:
    count: int


class Counter(Flow[None, CountOut]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return CountOut(count=self.count)


class Printer(Flow[CountOut, None]):
    def step(self, input: CountOut) -> None:
        print(f"[Printer] count={input.count}")
        return None


def build_pipeline() -> Pipeline:
    pipe = Pipeline("stateful_reset_demo")
    with pipe:
        counter = Counter() @ Rate(hz=1)
        printer = Printer() @ Rate(hz=1)
        counter >> printer
    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stateful flow reset + stepper demo.")
    p.add_argument("--steps", type=int, default=5, help="How many stepper iterations to run.")
    p.add_argument("--dt", type=float, default=0.1, help="Logical time delta per step.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline()

    print("=== run #1 ===")
    for i in range(args.steps):
        print(f"\n--- step {i} ---")
        pipe.step(dt=args.dt)

    print("\n=== reset ===")
    pipe.reset()

    print("\n=== run #2 ===")
    for i in range(args.steps):
        print(f"\n--- step {i} ---")
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
