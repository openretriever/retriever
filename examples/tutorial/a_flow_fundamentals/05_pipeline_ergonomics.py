"""
Pipeline ergonomics demo (canonical authoring surface).

This example shows three equivalent ways to build the same graph:

  Source @ Rate -> Double @ Trigger -> Sink @ Rate

Modes:
  1) explicit:      `pipe.connect(a, b)`
  2) context:       `with pipe: a >> b` (then keep chaining outside the context)
  3) functional:    `retriever.connect(a, b)` (thread-local default pipeline)

Run:
  pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode context --exec step
  pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode functional --exec step
  pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode explicit --exec mp --duration 2
"""

from __future__ import annotations

import argparse

import retriever
from retriever.flow import Flow, Pipeline, Rate, Trigger, io


@io
class Value:
    value: int


class Source(Flow[None, Value]):
    def init(self) -> None:
        self.i = 0

    def run(self, _):  # type: ignore[override]
        self.i += 1
        return Value(value=self.i)


class Double(Flow[Value, Value]):
    def run(self, input: Value) -> Value:
        return Value(value=input.value * 2)


class Sink(Flow[Value, None]):
    def run(self, input: Value) -> None:
        print(f"[Sink] got value={input.value}")
        return None


def build_explicit() -> Pipeline:
    pipe = Pipeline("explicit")
    a = Source() @ Rate(hz=10)
    b = Double() @ Trigger("value")
    c = Sink() @ Rate(hz=10)

    pipe.connect(a, b)
    pipe.connect(b, c)
    return pipe


def build_context() -> Pipeline:
    pipe = Pipeline("context")
    with pipe:
        a = Source() @ Rate(hz=10)
        b = Double() @ Trigger("value")
        a >> b

    # Handles are tagged with `handle.pipeline = pipe`, so wiring can continue later.
    c = Sink() @ Rate(hz=10)
    b >> c
    return pipe


def build_functional() -> Pipeline:
    # Reset default pipeline
    from retriever.flow.pipeline import reset_default_pipeline
    reset_default_pipeline()

    a = Source() @ Rate(hz=10)
    b = Double() @ Trigger("value")
    c = Sink() @ Rate(hz=10)

    retriever.connect(a, b)
    retriever.connect(b, c)
    return retriever.default_pipeline()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline ergonomics demo.")
    p.add_argument("--mode", default="context", choices=["explicit", "context", "functional"])
    p.add_argument("--exec", default="step", choices=["step", "mp", "dora"])
    p.add_argument("--steps", type=int, default=5, help="Stepper iterations (when --exec step)")
    p.add_argument("--dt", type=float, default=0.1, help="Logical dt per step (when --exec step)")
    p.add_argument("--duration", type=float, default=2.0, help="Run duration seconds (when --exec mp/dora)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "explicit":
        pipe = build_explicit()
    elif args.mode == "context":
        pipe = build_context()
    elif args.mode == "functional":
        pipe = build_functional()
    else:
        raise SystemExit(f"Unknown mode: {args.mode}")

    # Always validate once so users see failures early (and to demonstrate that all modes
    # produce equivalent IR).
    ir = pipe.validate()
    print(f"[IR] nodes={len(ir.nodes)} edges={len(ir.edges)} name={ir.metadata.name!r}")

    if args.exec == "step":
        try:
            for i in range(args.steps):
                print(f"\n=== step {i} ===")
                pipe.step(dt=args.dt)
        finally:
            pipe.close_stepper()
        return

    backend = "multiprocessing" if args.exec == "mp" else "dora"
    pipe.run(backend=backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()

