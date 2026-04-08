"""
Stateful counter flow (no Eff).

Run:
  pixi run python -m examples.tutorial.d_closed_loop_state_feedback.90_legacy_eff_basics --steps 6 --dt 0.1
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class StepIn:
    step: int | None = None


@io
class CounterOut:
    step: int | None = None
    value: int | None = None
    note: str | None = None


class StepSource(Flow[None, StepIn]):
    def init(self) -> None:
        self.step = 0

    def reset(self) -> None:
        self.step = 0

    def run(self, _):  # type: ignore[override]
        self.step += 1
        return StepIn(step=self.step)


class EffCounter(Flow[StepIn, CounterOut]):
    """Stateful counter that adjusts its increment by step parity."""

    def init(self) -> None:
        self.value = 0

    def reset(self) -> None:
        self.value = 0

    def run(self, input: StepIn) -> CounterOut:
        if input.step is None:
            return CounterOut()

        add_amount = 2 if input.step % 2 == 0 else 1
        self.value += 1 + add_amount
        note = f"applied +{1 + add_amount}, value={self.value}"
        return CounterOut(step=input.step, value=self.value, note=note)


class Printer(Flow[CounterOut, None]):
    def run(self, input: CounterOut) -> None:
        if input.step is None or input.value is None or input.note is None:
            return None
        print(f"[step {input.step}] value={input.value} ({input.note})")
        return None


def build_pipeline(hz: float) -> Pipeline:
    pipe = Pipeline("eff_basics")
    clock = Rate(hz=hz)

    with pipe:
        src = StepSource() @ clock
        counter = EffCounter() @ clock
        printer = Printer() @ clock
        pipe.connect(src, counter, sync=Latest())
        pipe.connect(counter, printer, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Eff basics inside a Flow.")
    p.add_argument("--steps", type=int, default=6)
    p.add_argument("--dt", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    hz = 1.0 / max(args.dt, 1e-6)
    pipe = build_pipeline(hz=hz)

    for _ in range(args.steps):
        pipe.step(dt=args.dt)

    pipe.close_stepper()


if __name__ == "__main__":
    main()
