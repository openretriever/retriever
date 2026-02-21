"""
Closed-loop policy backend abstraction tutorial.

Covers:
1) Common PolicyBackend interface
2) Backend switching by config only: openpi_pi05 | lerobot | mock
3) Timing + chunk-behavior comparison table

Run:
  pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from examples.tutorial._p0_utils import format_table, percentile, write_json


BackendName = Literal["openpi_pi05", "lerobot", "mock"]


@dataclass
class PolicyBackendConfig:
    backend: BackendName
    model_id: str
    device: str
    action_horizon: int
    dt: float
    cache_dir: str | None
    policy_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyChunk:
    actions: dict[str, Any]
    timestamp_obs: float
    timestamp_infer_start: float
    timestamp_infer_end: float
    dt: float
    metadata: dict[str, Any]


class PolicyBackend(Protocol):
    def init(self, config: PolicyBackendConfig) -> None: ...
    def warmup(self) -> None: ...
    def infer(self, observation: dict[str, Any], context: dict[str, Any]) -> PolicyChunk: ...
    def close(self) -> None: ...


class SimulatedPolicyBackend:
    """Deterministic backend simulator that obeys the PolicyBackend contract."""

    def __init__(self, *, name: BackendName, base_ms: float, jitter_ms: float, gain: float, seed_offset: int):
        self.name = name
        self.base_ms = base_ms
        self.jitter_ms = jitter_ms
        self.gain = gain
        self.seed_offset = seed_offset
        self.cfg: PolicyBackendConfig | None = None
        self.rng: random.Random | None = None
        self.step_idx = 0

    def init(self, config: PolicyBackendConfig) -> None:
        self.cfg = config
        seed = int(config.policy_kwargs.get("seed", 7)) + self.seed_offset
        self.rng = random.Random(seed)
        self.step_idx = 0

    def warmup(self) -> None:
        if self.cfg is None:
            raise RuntimeError("init() must be called before warmup().")

    def infer(self, observation: dict[str, Any], context: dict[str, Any]) -> PolicyChunk:
        if self.cfg is None or self.rng is None:
            raise RuntimeError("Backend not initialized.")

        clock_s = float(context["clock_s"])
        phase = float(observation["phase"])

        # Deterministic latency model with bounded jitter.
        jitter = self.jitter_ms * (0.5 + 0.5 * math.sin(self.step_idx * 0.7))
        latency_ms = self.base_ms + jitter
        t0 = clock_s
        t1 = t0 + (latency_ms / 1000.0)

        actions = []
        for i in range(self.cfg.action_horizon):
            wave = math.sin(phase + i * 0.35)
            noise = self.rng.uniform(-0.03, 0.03)
            actions.append(round(self.gain * wave + noise, 5))

        chunk = PolicyChunk(
            actions={"joint_delta": actions},
            timestamp_obs=float(observation["timestamp"]),
            timestamp_infer_start=t0,
            timestamp_infer_end=t1,
            dt=self.cfg.dt,
            metadata={
                "backend": self.name,
                "step": self.step_idx,
                "action_horizon": self.cfg.action_horizon,
            },
        )
        self.step_idx += 1
        return chunk

    def close(self) -> None:
        return None


_BACKEND_FACTORIES: dict[BackendName, callable] = {
    "openpi_pi05": lambda: SimulatedPolicyBackend(
        name="openpi_pi05", base_ms=18.0, jitter_ms=4.0, gain=1.0, seed_offset=11
    ),
    "lerobot": lambda: SimulatedPolicyBackend(
        name="lerobot", base_ms=11.0, jitter_ms=3.0, gain=0.9, seed_offset=23
    ),
    "mock": lambda: SimulatedPolicyBackend(
        name="mock", base_ms=4.0, jitter_ms=1.0, gain=0.5, seed_offset=37
    ),
}


@dataclass
class BackendMetrics:
    backend: BackendName
    mean_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    mean_chunk_len: float
    mean_abs_action: float


def make_backend(name: BackendName) -> PolicyBackend:
    return _BACKEND_FACTORIES[name]()


def representative_graph_fingerprint() -> str:
    edges = [
        ["observation_aggregator", "policy_backend"],
        ["policy_backend", "action_buffer"],
        ["action_buffer", "control_dispatch"],
    ]
    payload = json.dumps(edges, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def benchmark_backend(config: PolicyBackendConfig, *, steps: int) -> BackendMetrics:
    backend = make_backend(config.backend)
    backend.init(config)
    backend.warmup()

    latencies: list[float] = []
    chunk_lengths: list[int] = []
    abs_actions: list[float] = []

    clock_s = 0.0
    for step_idx in range(steps):
        observation = {
            "timestamp": clock_s,
            "phase": step_idx * 0.25,
            "ee_pose": [0.2, -0.1, 0.4],
        }
        chunk = backend.infer(observation, {"clock_s": clock_s, "step_idx": step_idx})

        latency_ms = (chunk.timestamp_infer_end - chunk.timestamp_infer_start) * 1000.0
        latencies.append(latency_ms)

        actions = list(chunk.actions.get("joint_delta", []))
        chunk_lengths.append(len(actions))
        if actions:
            abs_actions.append(sum(abs(a) for a in actions) / len(actions))
        else:
            abs_actions.append(0.0)

        clock_s += config.dt

    backend.close()

    return BackendMetrics(
        backend=config.backend,
        mean_latency_ms=round(sum(latencies) / len(latencies), 3),
        p95_latency_ms=round(percentile(latencies, 95.0), 3),
        max_latency_ms=round(max(latencies), 3),
        mean_chunk_len=round(sum(chunk_lengths) / len(chunk_lengths), 3),
        mean_abs_action=round(sum(abs_actions) / len(abs_actions), 5),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Policy backend abstraction benchmark tutorial.")
    p.add_argument(
        "--backends",
        nargs="+",
        default=["openpi_pi05", "lerobot", "mock"],
        choices=["openpi_pi05", "lerobot", "mock"],
        help="Backends to benchmark with unchanged graph topology.",
    )
    p.add_argument("--steps", type=int, default=40)
    p.add_argument("--action-horizon", type=int, default=6)
    p.add_argument("--dt", type=float, default=0.05)
    p.add_argument("--model-id", type=str, default="tutorial-policy")
    p.add_argument("--device", type=str, default="cpu")
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

    graph_fp = representative_graph_fingerprint()
    print(f"[Contract] graph_fingerprint={graph_fp}")
    print("[Contract] pipeline graph is backend-invariant; only backend factory selection changes.")

    metrics: list[BackendMetrics] = []
    for backend_name in args.backends:
        cfg = PolicyBackendConfig(
            backend=backend_name,  # type: ignore[arg-type]
            model_id=args.model_id,
            device=args.device,
            action_horizon=args.action_horizon,
            dt=args.dt,
            cache_dir=None,
            policy_kwargs={"seed": args.seed},
        )
        metrics.append(benchmark_backend(cfg, steps=args.steps))

    rows = [
        [
            m.backend,
            f"{m.mean_latency_ms:.2f}",
            f"{m.p95_latency_ms:.2f}",
            f"{m.max_latency_ms:.2f}",
            f"{m.mean_chunk_len:.2f}",
            f"{m.mean_abs_action:.4f}",
        ]
        for m in metrics
    ]

    print("\n=== Backend Comparison (timing + chunk behavior) ===")
    print(
        format_table(
            ["backend", "mean_ms", "p95_ms", "max_ms", "mean_chunk_len", "mean_|action|"],
            rows,
        )
    )

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["backend", "mean_ms", "p95_ms", "max_ms", "mean_chunk_len", "mean_abs_action"])
        for m in metrics:
            writer.writerow(
                [m.backend, m.mean_latency_ms, m.p95_latency_ms, m.max_latency_ms, m.mean_chunk_len, m.mean_abs_action]
            )

    write_json(
        args.out_json,
        {
            "schema_version": "retriever.policy_backend_metrics.v1",
            "graph_fingerprint": graph_fp,
            "steps": args.steps,
            "action_horizon": args.action_horizon,
            "dt": args.dt,
            "metrics": [m.__dict__ for m in metrics],
        },
    )

    print(f"\n[Artifacts] csv={args.out_csv} json={args.out_json}")


if __name__ == "__main__":
    main()
