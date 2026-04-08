"""
Functional fan-in + fan-out tutorial (advanced wiring patterns).

Covers:
1) Fan-out: one source feeding two independent branches
2) Fan-in: multiple sources sharing one destination port with Window(mean)
3) Contract-oriented evidence artifact for quick verification

Run:
  pixi run python -m examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout --steps 6 --dt 0.1
"""

from __future__ import annotations

import argparse
from pathlib import Path

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, Window, io

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


@io
class NumericSample:
    source: str | None = None
    value: float | None = None


@io
class BranchOutput:
    branch: str | None = None
    value: float | None = None


@io
class MeanOutput:
    mean: float | None = None


class CounterSource(Flow[None, NumericSample]):
    def __init__(self, *, source: str, start: float, step: float):
        super().__init__()
        self.source = source
        self.start = float(start)
        self.step = float(step)

    def init_config(self) -> dict:
        return {"source": self.source, "start": self.start, "step": self.step}

    def init(self) -> None:
        self._value = self.start

    def reset(self) -> None:
        self._value = self.start

    def run(self, _):  # type: ignore[override]
        out = NumericSample(source=self.source, value=self._value)
        self._value += self.step
        return out


class ConstantSource(Flow[None, NumericSample]):
    def __init__(self, *, source: str, value: float):
        super().__init__()
        self.source = source
        self.value = float(value)

    def init_config(self) -> dict:
        return {"source": self.source, "value": self.value}

    def run(self, _):  # type: ignore[override]
        return NumericSample(source=self.source, value=self.value)


class ScaleBranch(Flow[NumericSample, BranchOutput]):
    def __init__(self, *, branch: str, gain: float):
        super().__init__()
        self.branch = branch
        self.gain = float(gain)

    def init_config(self) -> dict:
        return {"branch": self.branch, "gain": self.gain}

    def run(self, input: NumericSample) -> BranchOutput:
        if input.value is None:
            return BranchOutput()
        return BranchOutput(branch=self.branch, value=float(input.value) * self.gain)


class MeanFusion(Flow[NumericSample, MeanOutput]):
    """
    For fan-in, each source writes into the same logical `value` port.
    With Window(mean), `input.value` is the adapter result over the shared buffer.
    """

    def run(self, input: NumericSample) -> MeanOutput:
        if input.value is None:
            return MeanOutput()
        return MeanOutput(mean=float(input.value))


class BranchPrinter(Flow[BranchOutput, None]):
    def run(self, input: BranchOutput) -> None:
        if input.branch is None or input.value is None:
            return None
        print(f"[fan-out] branch={input.branch:>4} value={input.value:6.2f}")
        return None


class MeanPrinter(Flow[MeanOutput, None]):
    def run(self, input: MeanOutput) -> None:
        if input.mean is None:
            return None
        print(f"[fan-in] shared_window_mean={input.mean:6.2f}")
        return None


def build_fanout_pipeline() -> tuple[Pipeline, dict[str, object]]:
    pipe = Pipeline("tut034_fanout")
    src = CounterSource(source="counter", start=1.0, step=1.0) @ Rate(hz=10)
    high = ScaleBranch(branch="high", gain=2.0) @ Trigger("value")
    low = ScaleBranch(branch="low", gain=0.5) @ Trigger("value")
    high_sink = BranchPrinter() @ Trigger("value")
    low_sink = BranchPrinter() @ Trigger("value")

    pipe.connect(src, high, sync=Latest())
    pipe.connect(src, low, sync=Latest())
    pipe.connect(high, high_sink, sync=Latest())
    pipe.connect(low, low_sink, sync=Latest())

    return pipe, {"high": high, "low": low}


def build_fanin_pipeline() -> tuple[Pipeline, dict[str, object]]:
    pipe = Pipeline("tut034_fanin")
    shared_window = Window(buffer_size=24, duration=1.0, agg="mean")

    src_a = ConstantSource(source="A", value=10.0) @ Rate(hz=10)
    src_b = ConstantSource(source="B", value=20.0) @ Rate(hz=10)
    src_c = ConstantSource(source="C", value=30.0) @ Rate(hz=10)
    fusion = MeanFusion() @ Trigger("value")
    sink = MeanPrinter() @ Trigger("mean")

    pipe.connect(src_a, fusion, map={"value": "value"}, sync=shared_window)
    pipe.connect(src_b, fusion, map={"value": "value"}, sync=shared_window)
    pipe.connect(src_c, fusion, map={"value": "value"}, sync=shared_window)
    pipe.connect(fusion, sink, sync=Latest())

    return pipe, {"fusion": fusion}


def run_fanout(*, steps: int, dt: float) -> dict[str, object]:
    pipe, handles = build_fanout_pipeline()
    high_id = pipe.get_node_id(handles["high"])  # type: ignore[arg-type]
    low_id = pipe.get_node_id(handles["low"])  # type: ignore[arg-type]

    high_vals: list[float] = []
    low_vals: list[float] = []
    try:
        for _ in range(steps):
            result = pipe.step(dt=dt)
            high = result.outputs.get(high_id)
            low = result.outputs.get(low_id)
            if high is not None and getattr(high, "value", None) is not None:
                high_vals.append(float(high.value))
            if low is not None and getattr(low, "value", None) is not None:
                low_vals.append(float(low.value))
    finally:
        pipe.close_stepper()

    rows = [[idx + 1, f"{high_vals[idx]:.2f}", f"{low_vals[idx]:.2f}"] for idx in range(min(len(high_vals), len(low_vals)))]
    print("\n=== Fan-Out Summary ===")
    print(format_table(["step", "high_branch", "low_branch"], rows))

    return {
        "steps": steps,
        "high_values": high_vals,
        "low_values": low_vals,
        "paired_count": min(len(high_vals), len(low_vals)),
    }


def run_fanin(*, steps: int, dt: float) -> dict[str, object]:
    pipe, handles = build_fanin_pipeline()
    fusion_id = pipe.get_node_id(handles["fusion"])  # type: ignore[arg-type]

    means: list[float] = []
    try:
        for _ in range(steps):
            result = pipe.step(dt=dt)
            out = result.outputs.get(fusion_id)
            if out is not None and getattr(out, "mean", None) is not None:
                means.append(float(out.mean))
    finally:
        pipe.close_stepper()

    preview = [[idx + 1, f"{value:.2f}"] for idx, value in enumerate(means[:8])]
    print("\n=== Fan-In Summary (Window Mean) ===")
    print(format_table(["sample", "mean"], preview))

    final_mean = means[-1] if means else None
    return {
        "steps": steps,
        "mean_samples": means,
        "final_mean": final_mean,
        "target_mean_hint": 20.0,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Functional fan-in/fan-out tutorial.")
    p.add_argument("--steps", type=int, default=6, help="Stepper iterations per demo.")
    p.add_argument("--dt", type=float, default=0.1, help="Logical step dt (seconds).")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("logs/tutorial_wiring/tut034_functional_fanin_fanout.json"),
        help="Output summary JSON path.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    fanout = run_fanout(steps=args.steps, dt=args.dt)
    fanin = run_fanin(steps=args.steps, dt=args.dt)

    summary = {
        "schema_version": "retriever.functional_wiring.v1",
        "created_at": utc_now_iso(),
        "config": {"steps": args.steps, "dt": args.dt},
        "fanout": fanout,
        "fanin": fanin,
    }
    write_json(args.out, summary)
    print(f"\n[Artifacts] summary={args.out}")


if __name__ == "__main__":
    main()
