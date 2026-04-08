"""
Multi-rate "robot system" demo (sensing → localization → planning → control).

This is a runtime-aligned rewrite of the legacy FRP coordination example.

What it demonstrates:
  - Multiple rates in one pipeline:
      Sensors 30Hz → Localization 10Hz → Planning 1Hz → Control 20Hz → Print 2Hz
  - Coordination is expressed via:
      - node clocks (`Rate(hz=...)`)
      - edge adapters (`Latest()` by default)
      - explicit field mapping into multi-input flows

Run (multiprocessing):
  pixi run python -m examples.tutorial.e_resource_and_sync.03_multirate_robot_system --backend multiprocessing --duration 5

Run (dora):
  pixi run python -m examples.tutorial.e_resource_and_sync.03_multirate_robot_system --backend dora --duration 5
"""

from __future__ import annotations

import argparse
import math
import time

from retriever.flow import Flow, Pipeline, Rate, io


@io
class SensorsOut:
    encoder: float
    gyro_z: float
    t: float


@io
class PoseOut:
    x: float
    theta: float
    uncertainty: float
    t: float


@io
class PlanOut:
    target_x: float
    confidence: float


@io
class ControlIn:
    x: float
    theta: float
    uncertainty: float
    pose_t: float
    target_x: float
    plan_confidence: float


@io
class CmdOut:
    v: float
    w: float
    err_x: float
    confidence: float


class SensorFlow(Flow[None, SensorsOut]):
    """30Hz sensor source with deterministic pseudo-noise."""

    def reset(self) -> None:
        self.i = 0
        self.t0 = time.time()

    def step(self, _):  # type: ignore[override]
        self.i += 1
        t = time.time() - self.t0
        encoder = 0.1 + 0.02 * math.sin(self.i * 0.3)
        gyro_z = 0.05 * math.sin(self.i * 0.07) + 0.02 * math.sin(self.i * 0.9)
        return SensorsOut(encoder=float(encoder), gyro_z=float(gyro_z), t=float(t))


class LocalizationFlow(Flow[SensorsOut, PoseOut]):
    """10Hz localization: integrate encoder + gyro into a pose estimate."""

    def reset(self) -> None:
        self.x = 0.0
        self.theta = 0.0
        self.uncertainty = 0.1
        self.last_t = None

    def step(self, input: SensorsOut) -> PoseOut:
        if input.encoder is None or input.gyro_z is None or input.t is None:
            return PoseOut()

        t = float(input.t)
        dt = 0.1 if self.last_t is None else max(1e-6, t - self.last_t)
        self.last_t = t

        v = float(input.encoder)
        w = float(input.gyro_z)

        self.theta += w * dt
        self.x += v * dt
        self.uncertainty = min(1.0, self.uncertainty + 0.02 * abs(w) + 0.01 * abs(v))

        return PoseOut(
            x=self.x,
            theta=self.theta,
            uncertainty=self.uncertainty,
            t=t,
        )


class PlanningFlow(Flow[PoseOut, PlanOut]):
    """1Hz planning: fixed goal with confidence based on localization uncertainty."""

    def step(self, input: PoseOut) -> PlanOut:
        if input.x is None or input.uncertainty is None:
            return PlanOut()

        confidence = max(0.2, 1.0 - float(input.uncertainty))
        return PlanOut(target_x=2.0, confidence=confidence)


class ControlFlow(Flow[ControlIn, CmdOut]):
    """20Hz controller: P-control in x and damping in theta."""

    def step(self, input: ControlIn) -> CmdOut:
        missing = (
            input.x is None
            or input.theta is None
            or input.target_x is None
            or input.plan_confidence is None
        )
        if missing:
            return CmdOut()

        x = float(input.x)
        theta = float(input.theta)
        target_x = float(input.target_x)
        confidence = float(input.plan_confidence)

        err_x = target_x - x
        v = max(-1.0, min(1.0, 0.8 * err_x))
        w = max(-2.0, min(2.0, -1.2 * theta))

        # Slow down when we're "less confident" (toy model).
        v *= max(0.2, confidence)

        return CmdOut(v=v, w=w, err_x=err_x, confidence=confidence)


class Printer(Flow[CmdOut, None]):
    """2Hz observer printing control signal and error."""

    def reset(self) -> None:
        self.t0 = time.time()
        self.k = 0

    def step(self, input: CmdOut) -> None:
        if input.v is None or input.w is None or input.err_x is None or input.confidence is None:
            return None
        self.k += 1
        dt = time.time() - self.t0
        print(
            f"[t={dt:4.1f}s] v={input.v:+.2f} w={input.w:+.2f} "
            f"err_x={input.err_x:+.2f} conf={input.confidence:.2f}"
        )
        return None


def build_pipeline() -> Pipeline:
    pipe = Pipeline("multirate_robot_system")

    with pipe:
        sensors = SensorFlow() @ Rate(hz=30)
        loc = LocalizationFlow() @ Rate(hz=10)
        plan = PlanningFlow() @ Rate(hz=1)
        ctrl = ControlFlow() @ Rate(hz=20)
        prn = Printer() @ Rate(hz=2)

        sensors >> loc
        loc >> plan

        # Multi-input wiring into control:
        loc.then(
            ctrl,
            map={
                "x": "x",
                "theta": "theta",
                "uncertainty": "uncertainty",
                "t": "pose_t",
            },
        )
        plan.then(
            ctrl,
            map={
                "target_x": "target_x",
                "confidence": "plan_confidence",
            },
        )

        ctrl >> prn

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-rate robot-system coordination demo.")
    p.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=5.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline()
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()

