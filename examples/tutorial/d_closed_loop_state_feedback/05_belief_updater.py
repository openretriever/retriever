"""
Stateful belief updater (implicit state inside a Flow).

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.05_belief_updater --steps 12 --dt 0.1
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class SensorOut:
    t_sim: float | None = None
    reading: float | None = None


@io
class BeliefOut:
    t_sim: float | None = None
    estimate: float | None = None
    confidence: float | None = None


class SensorSim(Flow[None, SensorOut]):
    """Deterministic sensor signal for repeatable debugging."""

    def __init__(self, *, dt: float):
        super().__init__()
        self.dt = float(dt)

    def init_config(self) -> dict:
        return {"dt": self.dt}

    def init(self) -> None:
        self.step = 0
        self.t_sim = 0.0

    def reset(self) -> None:
        self.step = 0
        self.t_sim = 0.0

    def run(self, _):  # type: ignore[override]
        self.step += 1
        self.t_sim += self.dt
        reading = 0.8 + 0.2 * ((self.step % 6) - 3)
        return SensorOut(t_sim=self.t_sim, reading=reading)


class BeliefUpdater(Flow[SensorOut, BeliefOut]):
    """Tracks a belief estimate using internal state (no explicit state passing)."""

    def __init__(self, *, alpha: float):
        super().__init__()
        self.alpha = float(alpha)

    def init_config(self) -> dict:
        return {"alpha": self.alpha}

    def init(self) -> None:
        self.estimate = 0.0
        self.confidence = 0.3

    def reset(self) -> None:
        self.estimate = 0.0
        self.confidence = 0.3

    def run(self, input: SensorOut) -> BeliefOut:
        if input.reading is None or input.t_sim is None:
            return BeliefOut()

        reading = float(input.reading)
        self.estimate = self.alpha * reading + (1.0 - self.alpha) * self.estimate
        self.confidence = min(1.0, self.confidence + 0.05)

        return BeliefOut(
            t_sim=float(input.t_sim),
            estimate=self.estimate,
            confidence=self.confidence,
        )


class Printer(Flow[BeliefOut, None]):
    def run(self, input: BeliefOut) -> None:
        if input.t_sim is None or input.estimate is None or input.confidence is None:
            return None
        print(
            f"[t={input.t_sim:4.1f}s] estimate={input.estimate:+.3f} "
            f"confidence={input.confidence:.2f}"
        )
        return None


def build_pipeline(*, dt: float) -> Pipeline:
    hz = 1.0 / max(dt, 1e-6)
    pipe = Pipeline("belief_updater_internal")

    with pipe:
        sensor = SensorSim(dt=dt) @ Rate(hz=hz)
        belief = BeliefUpdater(alpha=0.4) @ Rate(hz=hz)
        printer = Printer() @ Rate(hz=hz)

        pipe.connect(sensor, belief, sync=Latest())
        pipe.connect(belief, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stateful belief updater demo.")
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(dt=args.dt)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
