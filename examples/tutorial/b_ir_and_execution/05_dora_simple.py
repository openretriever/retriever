"""
Dora Backend - Execute pipeline with dora-rs backend

Demonstrates using the dora backend for zero-copy IPC execution.

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple --backend dora --duration 3
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, io, Rate, Trigger


@io
@dataclass
class CounterOutput:
    count: int


@dataclass
class Result:
    original: int
    doubled: int


@io
@dataclass
class ProcessedOutput:
    result: Result


class CounterSource(Flow[None, CounterOutput]):
    """Source that generates incrementing counter"""
    def __init__(self):
        super().__init__()
        self.counter = 0

    def run(self, _):
        self.counter += 1
        result = CounterOutput(count=self.counter)
        print(f"  [Counter] Generated: {result.count}")
        return result


class DoublerFlow(Flow[CounterOutput, ProcessedOutput]):
    """Double the input value"""
    def run(self, input: CounterOutput):
        result = Result(original=input.count, doubled=input.count * 2)
        output = ProcessedOutput(result=result)
        print(f"  [Doubler] {input.count} → {result.doubled}")
        return output


class PrinterSink(Flow[ProcessedOutput, None]):
    """Print the final result"""
    def run(self, input: ProcessedOutput):
        r = input.result
        print(f"  [Printer] Result: {r.original} × 2 = {r.doubled}\n")
        return None


def build_pipeline() -> Pipeline:
    """Build simple pipeline: Counter → Doubler → Printer"""
    pipe = Pipeline("dora_demo")
    with pipe:
        counter = CounterSource() @ Rate(hz=2)
        doubler = DoublerFlow() @ Trigger("count")
        printer = PrinterSink() @ Trigger("result")
        counter >> doubler >> printer
    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal Dora backend demo.")
    p.add_argument("--backend", default="dora", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=3.0)
    p.add_argument("--print-ir", action="store_true", help="Print built IR (optional).")
    p.add_argument(
        "--fresh-dora",
        dest="fresh_dora",
        action="store_true",
        default=True,
        help="Destroy/restart the dora runtime before launch (default for this demo).",
    )
    p.add_argument(
        "--no-fresh-dora",
        dest="fresh_dora",
        action="store_false",
        help="Reuse an existing dora runtime instead of forcing a clean one.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("Building pipeline:")
    print("  Counter @ Rate(2Hz) → Doubler @ Trigger → Printer @ Trigger\n")

    pipe = build_pipeline()

    if args.print_ir:
        ir = pipe.validate()
        print(ir.to_json())
        print(f"✓ IR created: {len(ir.nodes)} nodes, {len(ir.edges)} edges\n")

    backend_config = {"dora_fresh": True} if args.backend == "dora" and args.fresh_dora else None
    pipe.run(
        backend=args.backend,
        duration=args.duration,
        blocking=True,
        backend_config=backend_config,
    )


if __name__ == "__main__":
    main()
