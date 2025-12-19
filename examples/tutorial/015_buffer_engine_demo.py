"""
015_buffer_engine_demo.py

Minimal demo for Tier B.3 "Buffer Engine" plumbing.

This does NOT change the user authoring surface: it only selects a buffering +
sampling implementation inside runtime backends via `backend_config`.

Run (multiprocessing backend):
  pixi run python -m examples.tutorial.015_buffer_engine_demo

Run (dora backend):
  pixi run python -m examples.tutorial.015_buffer_engine_demo --backend dora
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Trigger, flow_io
from retriever.flow.adapter import Window


@flow_io
@dataclass
class SrcOut:
    x: float


@flow_io
@dataclass
class SinkIn:
    x: float


class Counter(Flow[None, SrcOut]):
    def __init__(self):
        self.i = 0

    def run(self, _):  # type: ignore[override]
        self.i += 1
        return SrcOut(x=float(self.i))


class Printer(Flow[SinkIn, None]):
    def run(self, input: SinkIn) -> None:
        print(f"[Printer] x={input.x}")
        return None


def build_pipeline() -> Pipeline:
    pipe = Pipeline("buffer_engine_demo")
    src = Counter() @ Rate(hz=20)
    # Trigger avoids "empty input" steps: Printer only runs when `x` arrives.
    sink = Printer() @ Trigger("x")
    pipe.connect(src, sink, sync=Window(buffer_size=200, duration=0.5, agg="mean"))
    return pipe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    parser.add_argument("--buffer-engine", default="python", choices=["python", "native"])
    parser.add_argument("--duration", type=float, default=2.0)
    args = parser.parse_args()

    pipe = build_pipeline()
    pipe.run(
        backend=args.backend,
        duration=args.duration,
        backend_config={"buffer_engine": args.buffer_engine},
    )


if __name__ == "__main__":
    main()
