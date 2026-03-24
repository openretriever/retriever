"""
Multi-rate coordination demo (FRP-ish) using `Rate` + `Window`.

This is a runtime-aligned replacement for the legacy FRP coordination demos.
It shows that you can:
  - produce data at a high rate (30Hz),
  - consume it at a lower rate (10Hz) with a time-window aggregation, and
  - observe it at an even lower rate (1Hz).

Key idea:
  - Adapters live on edges and define how downstream nodes sample buffered history.
  - `Window(duration=..., agg=...)` turns a fast event stream into a smoothed signal.

Run (multiprocessing):
  pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window --backend multiprocessing --duration 3

Run (dora):
  pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window --backend dora --duration 3
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Window, io


@io
@dataclass
class SensorOut:
    x: float


@io
@dataclass
class SmoothedOut:
    x_mean: float


class Sensor(Flow[None, SensorOut]):
    """Fast 30Hz source producing a noisy-ish sinusoid."""

    def init(self) -> None:
        self.i = 0

    def run(self, _):  # type: ignore[override]
        self.i += 1
        # Deterministic "noise" so the example is stable.
        base = math.sin(self.i * 0.2)
        noise = 0.2 * math.sin(self.i * 2.7)
        return SensorOut(x=base + noise)


class Smoother(Flow[SensorOut, SmoothedOut]):
    """10Hz consumer that samples a 0.5s window mean from the upstream buffer."""

    def run(self, input: SensorOut) -> SmoothedOut:
        if input.x is None:
            return SmoothedOut()
        return SmoothedOut(x_mean=float(input.x))


class Printer(Flow[SmoothedOut, None]):
    """1Hz observer that prints the current smoothed value."""

    def init(self) -> None:
        self.t0 = time.time()
        self.k = 0

    def run(self, input: SmoothedOut) -> None:
        if input.x_mean is None:
            return None
        self.k += 1
        dt = time.time() - self.t0
        print(f"[t={dt:4.1f}s] x_mean={input.x_mean:+.3f}")
        return None


def build_pipeline() -> Pipeline:
    pipe = Pipeline("multirate_window")

    with pipe:
        sensor = Sensor() @ Rate(hz=30)
        smoother = Smoother() @ Rate(hz=10)
        printer = Printer() @ Rate(hz=1)

        # Downsample + smooth: sample the last 0.5s of `x` and take mean.
        # buffer_size must cover at least hz*window; 50 covers 30Hz * 0.5s = 15 samples.
        sensor.then(smoother, sync=Window(buffer_size=50, duration=0.5, agg="mean"))
        smoother.then(printer)  # default adapter is Latest()

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-rate window smoothing demo.")
    p.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=3.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline()
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()

