"""
Closed-loop policy backend abstraction tutorial.

Covers:
1) One closed-loop policy contract: infer(example) -> actions
2) Backend switching by config only: openpi_pi05 | lerobot | mock
3) Optional timing/chunk evidence written to CSV/JSON

Run:
  pixi run demo-policy-backends
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from examples.tutorial._p0_utils import format_table, percentile, write_json


BackendName = Literal["openpi_pi05", "lerobot", "mock"]


@dataclass(frozen=True)
class PolicyBackendConfig:
    backend: BackendName
    action_horizon: int = 6
    dt: float = 0.05
    seed: int = 7


class PolicyBackend(Protocol):
    def infer(self, example: dict[str, Any]) -> dict[str, Any]: ...


class SimulatedPolicyBackend:
    """Deterministic stand-in that keeps the same backend-facing contract."""

    def __init__(
        self,
        *,
        name: BackendName,
        config: PolicyBackendConfig,
        base_ms: float,
        jitter_ms: float,
        gain: float,
        seed_offset: int,
    ) -> None:
        self.name = name
        self.config = config
        self.base_ms = base_ms
        self.jitter_ms = jitter_ms
        self.gain = gain
        self.rng = random.Random(config.seed + seed_offset)
        self.step_idx = 0

    def infer(self, example: dict[str, Any]) -> dict[str, Any]:
        phase = float(example["phase"])
        jitter = self.jitter_ms * (0.5 + 0.5 * math.sin(self.step_idx * 0.7))
        latency_ms = self.base_ms + jitter

        actions = []
        for i in range(self.config.action_horizon):
            wave = math.sin(phase + i * 0.35)
            noise = self.rng.uniform(-0.03, 0.03)
            actions.append(round(self.gain * wave + noise, 5))

        self.step_idx += 1
        return {
            "actions": actions,
            "latency_ms": round(latency_ms, 3),
            "backend": self.name,
            "dt": self.config.dt,
            "step": self.step_idx - 1,
        }


_BACKEND_FACTORIES: dict[BackendName, callable] = {
    "openpi_pi05": lambda cfg: SimulatedPolicyBackend(
        name="openpi_pi05", config=cfg, base_ms=18.0, jitter_ms=4.0, gain=1.0, seed_offset=11
    ),
    "lerobot": lambda cfg: SimulatedPolicyBackend(
        name="lerobot", config=cfg, base_ms=11.0, jitter_ms=3.0, gain=0.9, seed_offset=23
    ),
    "mock": lambda cfg: SimulatedPolicyBackend(
        name="mock", config=cfg, base_ms=4.0, jitter_ms=1.0, gain=0.5, seed_offset=37
    ),
}


@dataclass
class BackendMetrics:
    backend: BackendName
    mean_latency_ms: float
    p95_latency_ms: float
    mean_chunk_len: float
    mean_abs_action: float


def make_backend(config: PolicyBackendConfig) -> PolicyBackend:
    return _BACKEND_FACTORIES[config.backend](config)


def example_for_step(step_idx: int, dt: float) -> dict[str, Any]:
    return {
        "timestamp_s": step_idx * dt,
        "phase": step_idx * 0.25,
        "task": "stabilize closed-loop motion",
        "ee_pose": [0.2, -0.1, 0.4],
    }


def benchmark_backend(config: PolicyBackendConfig, *, steps: int) -> tuple[BackendMetrics, dict[str, Any]]:
    backend = make_backend(config)

    latencies: list[float] = []
    chunk_lengths: list[int] = []
    abs_actions: list[float] = []
    first_result: dict[str, Any] | None = None

    for step_idx in range(steps):
        result = backend.infer(example_for_step(step_idx, config.dt))
        if first_result is None:
            first_result = result

        latency_ms = float(result["latency_ms"])
        actions = [float(a) for a in result.get("actions", [])]

        latencies.append(latency_ms)
        chunk_lengths.append(len(actions))
        abs_actions.append((sum(abs(a) for a in actions) / len(actions)) if actions else 0.0)

    metrics = BackendMetrics(
        backend=config.backend,
        mean_latency_ms=round(sum(latencies) / len(latencies), 3),
        p95_latency_ms=round(percentile(latencies, 95.0), 3),
        mean_chunk_len=round(sum(chunk_lengths) / len(chunk_lengths), 3),
        mean_abs_action=round(sum(abs_actions) / len(abs_actions), 5),
    )
    return metrics, (first_result or {"actions": [], "latency_ms": 0.0, "backend": config.backend})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Closed-loop policy backend abstraction tutorial.")
    p.add_argument(
        "--backends",
        nargs="+",
        default=["openpi_pi05", "lerobot", "mock"],
        choices=["openpi_pi05", "lerobot", "mock"],
        help="Backends to run under the same example and policy contract.",
    )
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--action-horizon", type=int, default=6)
    p.add_argument("--dt", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument(
        "--out-csv",
        type=Path,
        default=Path("logs/tutorial_policy/tut027_backend_metrics.csv"),
    )
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("logs/tutorial_policy/tut027_backend_metrics.json"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("[Contract] same policy example, same infer(example)->actions surface, backend selected by config")

    metrics: list[BackendMetrics] = []
    sample_rows: list[list[str]] = []
    for backend_name in args.backends:
        cfg = PolicyBackendConfig(
            backend=backend_name,  # type: ignore[arg-type]
            action_horizon=args.action_horizon,
            dt=args.dt,
            seed=args.seed,
        )
        metric, first_result = benchmark_backend(cfg, steps=args.steps)
        metrics.append(metric)
        preview = ", ".join(f"{v:.3f}" for v in list(first_result["actions"])[:3])
        sample_rows.append([backend_name, f"[{preview}]", f"{float(first_result['latency_ms']):.2f}"])

    print("\n=== First-step Action Preview ===")
    print(format_table(["backend", "actions[:3]", "latency_ms"], sample_rows))

    rows = [
        [
            m.backend,
            f"{m.mean_latency_ms:.2f}",
            f"{m.p95_latency_ms:.2f}",
            f"{m.mean_chunk_len:.2f}",
            f"{m.mean_abs_action:.4f}",
        ]
        for m in metrics
    ]

    print("\n=== Backend Comparison (optional evidence) ===")
    print(format_table(["backend", "mean_ms", "p95_ms", "mean_chunk_len", "mean_|action|"], rows))

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["backend", "mean_ms", "p95_ms", "mean_chunk_len", "mean_abs_action"])
        for m in metrics:
            writer.writerow([m.backend, m.mean_latency_ms, m.p95_latency_ms, m.mean_chunk_len, m.mean_abs_action])

    write_json(
        args.out_json,
        {
            "schema_version": "retriever.policy_backend_metrics.v1",
            "steps": args.steps,
            "action_horizon": args.action_horizon,
            "dt": args.dt,
            "metrics": [m.__dict__ for m in metrics],
        },
    )

    print(f"\n[Artifacts] optional csv={args.out_csv} json={args.out_json}")


if __name__ == "__main__":
    main()
