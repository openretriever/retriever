"""
Runtime Execution - Execute IR pipelines

Run pipelines via `Pipeline.run(...)` (recommended).

This example shows:
  - Raw IR execution (`build=False`) -> one executor per node
  - ExecutionGraph execution (`build=True`) -> grouping/co-location via `build_execution`

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution --backend multiprocessing --duration 4
"""

from __future__ import annotations

import argparse
import time

from retriever.flow import Flow, Pipeline, io, Rate, Trigger


@io
class Data:
    value: int


class CounterSource(Flow[None, Data]):
    """Source that generates incrementing numbers"""
    def __init__(self):
        super().__init__()
        self.counter = 0

    def step(self, _):
        self.counter += 1
        result = Data(value=self.counter)
        print(f"  [Source] generated: {result.value}")
        return result


class MultiplyFlow(Flow[Data, Data]):
    """Multiply input by 2"""
    def step(self, input: Data):
        result = Data(value=input.value * 2)
        print(f"  [Multiply] {input.value} × 2 = {result.value}")
        time.sleep(0.1)  # Simulate processing
        return result


class AddFlow(Flow[Data, Data]):
    """Add 10 to input"""
    def step(self, input: Data):
        result = Data(value=input.value + 10)
        print(f"  [Add] {input.value} + 10 = {result.value}")
        time.sleep(0.1)  # Simulate processing
        return result


class PrintSink(Flow[Data, None]):
    """Print final result"""
    def step(self, input: Data):
        print(f"  [Sink] ✓ Final result: {input.value}\n")
        return None


def build_pipeline() -> Pipeline:
    pipe = Pipeline("demo_pipeline")
    with pipe:
        source = CounterSource() @ Rate(hz=1)  # 1 execution per second
        multiply = MultiplyFlow() @ Trigger("value")
        add = AddFlow() @ Trigger("value")
        sink = PrintSink() @ Trigger("value")

        source >> multiply >> add >> sink
    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Runtime execution demo (raw IR vs ExecutionGraph).")
    p.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=4.0)
    p.add_argument("--build", action="store_true", help="Run via ExecutionGraph (grouping/co-location).")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("Building pipeline:")
    print("  Counter @ Rate(1Hz) → Multiply @ Trigger → Add @ Trigger → Print @ Trigger")
    print("  Formula: (counter × 2) + 10\n")

    pipe = build_pipeline()
    pipe.run(backend=args.backend, duration=args.duration, blocking=True, build=bool(args.build))


if __name__ == "__main__":
    main()
