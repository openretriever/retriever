"""
Trace contract basics for release-readiness instrumentation.

Covers:
1) Trace envelope fields
2) Per-edge latency + queue-depth snapshots
3) First-bottleneck diagnosis in a synthetic multi-rate graph

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
"""

from __future__ import annotations

import argparse
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from examples.tutorial._p0_utils import format_table, percentile, utc_now_iso, write_json, write_jsonl


EDGE_OBS_TO_POLICY = "observation_aggregator->policy_backend"
EDGE_POLICY_TO_BUFFER = "policy_backend->action_buffer"
EDGE_BUFFER_TO_CONTROL = "action_buffer->control_dispatch"


@dataclass
class TraceEnvelope:
    schema_version: str
    run_id: str
    step_idx: int
    edge_id: str
    source_node: str
    destination_node: str
    timestamp_emit_s: float
    timestamp_consume_s: float
    latency_ms: float
    queue_depth: int
    metadata: dict[str, Any]


def _edge_nodes(edge_id: str) -> tuple[str, str]:
    src, dst = edge_id.split("->", 1)
    return src, dst


def _trace_envelope(
    *,
    run_id: str,
    step_idx: int,
    edge_id: str,
    emit_s: float,
    consume_s: float,
    queue_depth: int,
    metadata: dict[str, Any],
) -> TraceEnvelope:
    src, dst = _edge_nodes(edge_id)
    return TraceEnvelope(
        schema_version="retriever.trace_envelope.v1",
        run_id=run_id,
        step_idx=step_idx,
        edge_id=edge_id,
        source_node=src,
        destination_node=dst,
        timestamp_emit_s=round(emit_s, 6),
        timestamp_consume_s=round(consume_s, 6),
        latency_ms=round((consume_s - emit_s) * 1000.0, 3),
        queue_depth=queue_depth,
        metadata=metadata,
    )


def simulate_trace(
    *,
    duration_s: float,
    obs_hz: float,
    policy_hz: float,
    control_hz: float,
    action_horizon: int,
    lag_step: int,
    lag_ms: float,
    base_policy_ms: float,
) -> tuple[str, list[TraceEnvelope]]:
    """
    Simulate a fixed topology with intentional lag in the policy stage.

    Topology:
      observation_aggregator -> policy_backend -> action_buffer -> control_dispatch
    """
    run_id = f"trace_{uuid.uuid4().hex[:8]}"
    eps = 1e-9

    q_obs: list[float] = []
    q_chunks: list[tuple[float, int]] = []
    active_chunk: dict[str, float | int] | None = None

    envelopes: list[TraceEnvelope] = []

    obs_period = 1.0 / obs_hz
    policy_period = 1.0 / policy_hz
    control_period = 1.0 / control_hz

    next_obs = 0.0
    next_policy = 0.0
    next_control = 0.0

    policy_step = 0
    control_step = 0

    while True:
        t = min(next_obs, next_policy, next_control)
        if t > duration_s + eps:
            break

        if abs(t - next_obs) <= eps:
            q_obs.append(t)
            next_obs += obs_period

        if abs(t - next_policy) <= eps:
            policy_step += 1

            if q_obs:
                # Latest-style sampling keeps latency reasoning focused on true bottlenecks
                # instead of unbounded backlog in this synthetic example.
                depth_before = len(q_obs)
                obs_emit_s = q_obs[-1]
                q_obs.clear()

                policy_ms = base_policy_ms
                lag_injected = policy_step == lag_step
                if lag_injected:
                    policy_ms += lag_ms

                policy_consume_s = t + (policy_ms / 1000.0)

                envelopes.append(
                    _trace_envelope(
                        run_id=run_id,
                        step_idx=policy_step,
                        edge_id=EDGE_OBS_TO_POLICY,
                        emit_s=obs_emit_s,
                        consume_s=policy_consume_s,
                        queue_depth=depth_before,
                        metadata={
                            "clock_hz": policy_hz,
                            "lag_injected": lag_injected,
                            "stage": "policy_infer",
                        },
                    )
                )

                q_chunks.append((policy_consume_s, action_horizon))

            next_policy += policy_period

        if abs(t - next_control) <= eps:
            control_step += 1

            if active_chunk is None and q_chunks:
                depth_before = len(q_chunks)
                chunk_emit_s, chunk_actions = q_chunks.pop(0)
                active_chunk = {
                    "emit_s": chunk_emit_s,
                    "remaining": int(chunk_actions),
                }

                envelopes.append(
                    _trace_envelope(
                        run_id=run_id,
                        step_idx=control_step,
                        edge_id=EDGE_POLICY_TO_BUFFER,
                        emit_s=chunk_emit_s,
                        consume_s=max(t + 0.001, chunk_emit_s),
                        queue_depth=depth_before,
                        metadata={
                            "clock_hz": control_hz,
                            "stage": "chunk_ingest",
                        },
                    )
                )

            if active_chunk is not None and int(active_chunk["remaining"]) > 0:
                depth_before = int(active_chunk["remaining"])
                emit_s = t

                envelopes.append(
                    _trace_envelope(
                        run_id=run_id,
                        step_idx=control_step,
                        edge_id=EDGE_BUFFER_TO_CONTROL,
                        emit_s=emit_s,
                        consume_s=max(t + 0.002, emit_s),
                        queue_depth=depth_before,
                        metadata={
                            "clock_hz": control_hz,
                            "stage": "action_dispatch",
                        },
                    )
                )

                active_chunk["remaining"] = int(active_chunk["remaining"]) - 1
                if int(active_chunk["remaining"]) <= 0:
                    active_chunk = None

            next_control += control_period

    return run_id, envelopes


def summarize_edges(envelopes: list[TraceEnvelope]) -> list[dict[str, Any]]:
    grouped: dict[str, list[TraceEnvelope]] = defaultdict(list)
    for env in envelopes:
        grouped[env.edge_id].append(env)

    rows: list[dict[str, Any]] = []
    for edge_id, events in grouped.items():
        latencies = [e.latency_ms for e in events]
        queue_depths = [e.queue_depth for e in events]

        rows.append(
            {
                "edge_id": edge_id,
                "count": len(events),
                "latency_mean_ms": round(sum(latencies) / len(latencies), 3),
                "latency_p95_ms": round(percentile(latencies, 95.0), 3),
                "latency_max_ms": round(max(latencies), 3),
                "queue_depth_last": queue_depths[-1],
                "queue_depth_max": max(queue_depths),
            }
        )

    rows.sort(key=lambda item: item["latency_max_ms"], reverse=True)
    return rows


def first_bottleneck(
    envelopes: list[TraceEnvelope],
    *,
    latency_threshold_ms: float,
) -> TraceEnvelope | None:
    candidates = [e for e in envelopes if e.latency_ms >= latency_threshold_ms]
    if not candidates:
        return None
    return min(candidates, key=lambda e: e.timestamp_consume_s)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Trace contract basics with synthetic bottleneck diagnostics.")
    p.add_argument("--duration", type=float, default=4.0, help="Simulation duration in seconds.")
    p.add_argument("--obs-hz", type=float, default=30.0, help="Observation source rate.")
    p.add_argument("--policy-hz", type=float, default=10.0, help="Policy loop rate.")
    p.add_argument("--control-hz", type=float, default=20.0, help="Control dispatch rate.")
    p.add_argument("--action-horizon", type=int, default=2, help="Actions emitted per policy chunk.")
    p.add_argument("--lag-step", type=int, default=7, help="Policy step that receives intentional lag.")
    p.add_argument("--lag-ms", type=float, default=180.0, help="Injected lag in milliseconds.")
    p.add_argument("--base-policy-ms", type=float, default=8.0, help="Nominal policy inference time.")
    p.add_argument(
        "--bottleneck-threshold-ms",
        type=float,
        default=120.0,
        help="Latency threshold used to flag the first bottleneck.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("logs/tutorial_trace/tut024_trace_envelopes.jsonl"),
        help="Trace envelope output path (.jsonl).",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=Path("logs/tutorial_trace/tut024_trace_report.json"),
        help="Summary report output path (.json).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    run_id, envelopes = simulate_trace(
        duration_s=args.duration,
        obs_hz=args.obs_hz,
        policy_hz=args.policy_hz,
        control_hz=args.control_hz,
        action_horizon=args.action_horizon,
        lag_step=args.lag_step,
        lag_ms=args.lag_ms,
        base_policy_ms=args.base_policy_ms,
    )

    write_jsonl(args.out, [asdict(env) for env in envelopes])

    top3 = sorted(envelopes, key=lambda env: env.latency_ms, reverse=True)[:3]
    edge_stats = summarize_edges(envelopes)
    bottleneck = first_bottleneck(envelopes, latency_threshold_ms=args.bottleneck_threshold_ms)

    report = {
        "schema_version": "retriever.trace_report.v1",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "config": {
            "duration": args.duration,
            "obs_hz": args.obs_hz,
            "policy_hz": args.policy_hz,
            "control_hz": args.control_hz,
            "action_horizon": args.action_horizon,
            "lag_step": args.lag_step,
            "lag_ms": args.lag_ms,
            "base_policy_ms": args.base_policy_ms,
            "bottleneck_threshold_ms": args.bottleneck_threshold_ms,
        },
        "top3_latency": [asdict(x) for x in top3],
        "edge_stats": edge_stats,
        "first_bottleneck": asdict(bottleneck) if bottleneck else None,
    }
    write_json(args.report, report)

    print("\n=== Trace Envelope Field Sample ===")
    if envelopes:
        sample = asdict(envelopes[min(2, len(envelopes) - 1)])
        for key in [
            "schema_version",
            "run_id",
            "edge_id",
            "step_idx",
            "timestamp_emit_s",
            "timestamp_consume_s",
            "latency_ms",
            "queue_depth",
            "metadata",
        ]:
            print(f"{key}: {sample[key]}")

    print("\n=== Top-3 Latency Edges ===")
    top_rows = [
        [
            env.edge_id,
            env.step_idx,
            f"{env.latency_ms:.1f}",
            env.queue_depth,
            "yes" if env.metadata.get("lag_injected") else "no",
        ]
        for env in top3
    ]
    print(format_table(["edge", "step", "latency_ms", "queue_depth", "lag_injected"], top_rows))

    print("\n=== Per-Edge Latency + Queue Snapshot ===")
    edge_rows = [
        [
            item["edge_id"],
            item["count"],
            f"{item['latency_mean_ms']:.1f}",
            f"{item['latency_p95_ms']:.1f}",
            f"{item['latency_max_ms']:.1f}",
            item["queue_depth_last"],
            item["queue_depth_max"],
        ]
        for item in edge_stats
    ]
    print(
        format_table(
            [
                "edge",
                "n",
                "mean_ms",
                "p95_ms",
                "max_ms",
                "queue_last",
                "queue_max",
            ],
            edge_rows,
        )
    )

    print("\n=== Bottleneck Diagnosis ===")
    if bottleneck is None:
        print(f"No edge exceeded {args.bottleneck_threshold_ms:.1f} ms.")
    else:
        print(
            f"First bottleneck at t={bottleneck.timestamp_consume_s:.3f}s on {bottleneck.edge_id} "
            f"(latency={bottleneck.latency_ms:.1f}ms, queue_depth={bottleneck.queue_depth})."
        )
        if bool(bottleneck.metadata.get("lag_injected")):
            print(
                "Diagnosis: intentional lag injection hit the policy stage; "
                "downstream queue pressure confirms this as the first bottleneck."
            )

    print(f"\n[Artifacts] envelopes={args.out} report={args.report}")


if __name__ == "__main__":
    main()
