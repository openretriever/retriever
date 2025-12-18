"""
Minimal in-process debugging demo for Retriever.

Why this exists:
  - Backends like `multiprocessing` and `dora` run each Flow in a separate process.
    VS Code breakpoints inside `Flow.run()` won't hit in your main Python process.
  - `Pipeline.step()` executes the pipeline **in-process** (sample → run → publish),
    so you can set breakpoints directly inside Flow logic and step through.

How to use:
  1) Set a breakpoint inside `DebugFlow.run()` (or enable "break on exception").
  2) Run this file under the VS Code debugger (F5), or:
     pixi run python -m examples.00_refact.011_debug_stepper --fail-at 3
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, flow_io


@flow_io
@dataclass
class Value:
    value: int


class Counter(Flow[None, Value]):
    def init(self) -> None:
        self.count = 0

    def run(self, _):  # type: ignore[override]
        self.count += 1
        return Value(value=self.count)


class DebugFlow(Flow[Value, Value]):
    def __init__(self, *, fail_at: int = 0):
        super().__init__()
        self.fail_at = fail_at

    def run(self, input: Value) -> Value:
        x = input.value  # put a breakpoint here
        if self.fail_at and x == self.fail_at:
            raise RuntimeError(f"Debug demo: value reached {self.fail_at}")
        return Value(value=x * 2)


class Sink(Flow[Value, None]):
    def run(self, input: Value) -> None:
        print(f"[Sink] got value={input.value}")
        return None


def build_pipeline(*, fail_at: int) -> Pipeline:
    pipe = Pipeline("debug_stepper")

    src = Counter() @ Rate(hz=10)
    dbg = DebugFlow(fail_at=fail_at) @ Trigger("value")
    sink = Sink() @ Rate(hz=10)

    pipe.connect(src, dbg, sync=Latest())
    pipe.connect(dbg, sink, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal Pipeline.step() debugger demo.")
    p.add_argument("--fail-at", type=int, default=0, help="Raise an exception when the counter reaches this value.")
    p.add_argument("--steps", type=int, default=5, help="Number of step iterations.")
    p.add_argument("--dt", type=float, default=0.1, help="Logical dt per step (seconds).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(fail_at=args.fail_at)

    try:
        for i in range(args.steps):
            print(f"\n=== step {i} ===")
            pipe.step(dt=args.dt)
    finally:
        pipe.close_stepper()


if __name__ == "__main__":
    main()
