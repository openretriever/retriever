"""
Incident response replay drill (TUT-033).

Covers:
1) Detect an incident from latency/queue symptoms
2) Produce a first-response checklist and root-cause candidate
3) Replay the incident trace and verify diagnosis consistency

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from examples.tutorial._p0_utils import format_table, percentile, utc_now_iso, write_json, write_jsonl


EDGE_OBS_TO_POLICY = "observation_aggregator->policy_backend"
EDGE_POLICY_TO_BUFFER = "policy_backend->action_buffer"
EDGE_BUFFER_TO_CONTROL = "action_buffer->control_dispatch"


@dataclass
class DrillEnvelope:
    schema_version: str
    run_id: str
    event_idx: int
    step_idx: int
    edge_id: str
    source_node: str
    destination_node: str
    timestamp_emit_s: float
    timestamp_consume_s: float
    latency_ms: float
    queue_depth: int
    incident_marker: bool
    metadata: dict[str, Any]


def _edge_nodes(edge_id: str) -> tuple[str, str]:
    src, dst = edge_id.split("->", 1)
    return src, dst


def _mk_env(
    *,
    run_id: str,
    event_idx: int,
    step_idx: int,
    edge_id: str,
    emit_s: float,
    consume_s: float,
    queue_depth: int,
    incident_marker: bool,
    metadata: dict[str, Any],
) -> DrillEnvelope:
    src, dst = _edge_nodes(edge_id)
    return DrillEnvelope(
        schema_version="retriever.incident_trace.v1",
        run_id=run_id,
        event_idx=event_idx,
        step_idx=step_idx,
        edge_id=edge_id,
        source_node=src,
        destination_node=dst,
        timestamp_emit_s=round(emit_s, 6),
        timestamp_consume_s=round(consume_s, 6),
        latency_ms=round((consume_s - emit_s) * 1000.0, 3),
        queue_depth=queue_depth,
        incident_marker=incident_marker,
        metadata=metadata,
    )


def simulate_envelopes(
    *,
    run_id: str,
    duration_s: float,
    obs_hz: float,
    policy_hz: float,
    control_hz: float,
    action_horizon: int,
    lag_step: int | None,
    lag_ms: float,
    base_policy_ms: float,
) -> list[DrillEnvelope]:
    eps = 1e-9

    q_obs: list[float] = []
    q_chunks: list[tuple[float, int]] = []
    active_chunk: dict[str, float | int] | None = None
    envelopes: list[DrillEnvelope] = []

    obs_period = 1.0 / obs_hz
    policy_period = 1.0 / policy_hz
    control_period = 1.0 / control_hz

    next_obs = 0.0
    next_policy = 0.0
    next_control = 0.0
    policy_step = 0
    control_step = 0
    event_idx = 0

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
                depth_before = len(q_obs)
                obs_emit_s = q_obs[-1]
                q_obs.clear()

                policy_ms = base_policy_ms
                lag_injected = lag_step is not None and policy_step == lag_step
                if lag_injected:
                    policy_ms += lag_ms

                policy_consume_s = t + (policy_ms / 1000.0)
                event_idx += 1
                envelopes.append(
                    _mk_env(
                        run_id=run_id,
                        event_idx=event_idx,
                        step_idx=policy_step,
                        edge_id=EDGE_OBS_TO_POLICY,
                        emit_s=obs_emit_s,
                        consume_s=policy_consume_s,
                        queue_depth=depth_before,
                        incident_marker=lag_injected,
                        metadata={
                            "clock_hz": policy_hz,
                            "stage": "policy_infer",
                            "lag_injected": lag_injected,
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
                active_chunk = {"emit_s": chunk_emit_s, "remaining": int(chunk_actions)}
                event_idx += 1
                envelopes.append(
                    _mk_env(
                        run_id=run_id,
                        event_idx=event_idx,
                        step_idx=control_step,
                        edge_id=EDGE_POLICY_TO_BUFFER,
                        emit_s=chunk_emit_s,
                        consume_s=max(t + 0.001, chunk_emit_s),
                        queue_depth=depth_before,
                        incident_marker=False,
                        metadata={"clock_hz": control_hz, "stage": "chunk_ingest"},
                    )
                )

            if active_chunk is not None and int(active_chunk["remaining"]) > 0:
                depth_before = int(active_chunk["remaining"])
                emit_s = t
                event_idx += 1
                envelopes.append(
                    _mk_env(
                        run_id=run_id,
                        event_idx=event_idx,
                        step_idx=control_step,
                        edge_id=EDGE_BUFFER_TO_CONTROL,
                        emit_s=emit_s,
                        consume_s=max(t + 0.002, emit_s),
                        queue_depth=depth_before,
                        incident_marker=False,
                        metadata={"clock_hz": control_hz, "stage": "action_dispatch"},
                    )
                )

                active_chunk["remaining"] = int(active_chunk["remaining"]) - 1
                if int(active_chunk["remaining"]) <= 0:
                    active_chunk = None

            next_control += control_period

    return envelopes


def rows_to_envelopes(rows: list[dict[str, Any]]) -> list[DrillEnvelope]:
    return [DrillEnvelope(**row) for row in rows]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def edge_summary(envelopes: list[DrillEnvelope]) -> list[dict[str, Any]]:
    grouped: dict[str, list[DrillEnvelope]] = defaultdict(list)
    for env in envelopes:
        grouped[env.edge_id].append(env)

    rows: list[dict[str, Any]] = []
    for edge_id, events in grouped.items():
        latencies = [e.latency_ms for e in events]
        queues = [e.queue_depth for e in events]
        rows.append(
            {
                "edge_id": edge_id,
                "count": len(events),
                "latency_mean_ms": round(sum(latencies) / len(latencies), 3),
                "latency_p95_ms": round(percentile(latencies, 95.0), 3),
                "latency_max_ms": round(max(latencies), 3),
                "queue_depth_max": max(queues),
            }
        )
    rows.sort(key=lambda x: x["latency_max_ms"], reverse=True)
    return rows


def first_incident(envelopes: list[DrillEnvelope], *, threshold_ms: float) -> DrillEnvelope | None:
    candidates = [env for env in envelopes if env.latency_ms >= threshold_ms]
    if not candidates:
        return None
    return min(candidates, key=lambda env: (env.timestamp_consume_s, env.event_idx))


def incident_windows(envelopes: list[DrillEnvelope], *, threshold_ms: float) -> list[dict[str, Any]]:
    violating = sorted([env for env in envelopes if env.latency_ms >= threshold_ms], key=lambda env: env.event_idx)
    if not violating:
        return []

    windows: list[dict[str, Any]] = []
    start = violating[0]
    prev = violating[0]
    window_events = [start]

    for current in violating[1:]:
        if current.event_idx == prev.event_idx + 1:
            window_events.append(current)
        else:
            windows.append(
                {
                    "start_event_idx": start.event_idx,
                    "end_event_idx": prev.event_idx,
                    "count": len(window_events),
                    "edges": sorted({e.edge_id for e in window_events}),
                }
            )
            start = current
            window_events = [current]
        prev = current

    windows.append(
        {
            "start_event_idx": start.event_idx,
            "end_event_idx": prev.event_idx,
            "count": len(window_events),
            "edges": sorted({e.edge_id for e in window_events}),
        }
    )
    return windows


def diagnosis_signature(root: DrillEnvelope | None, windows: list[dict[str, Any]]) -> str:
    payload = {
        "root_edge": root.edge_id if root else None,
        "root_step": root.step_idx if root else None,
        "root_latency_ms": round(root.latency_ms, 3) if root else None,
        "window_count": len(windows),
        "window_shapes": [[w["start_event_idx"], w["end_event_idx"], w["count"]] for w in windows],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def render_checklist(
    *,
    generated_at: str,
    threshold_ms: float,
    root: DrillEnvelope | None,
    windows: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# TUT-033 Incident Response Replay Checklist")
    lines.append("")
    lines.append(f"- Generated at: {generated_at}")
    lines.append(f"- Incident threshold: `{threshold_ms}` ms")
    lines.append("")

    lines.append("## Detection")
    lines.append("")
    if root is None:
        lines.append("- Root cause candidate: none detected")
    else:
        lines.append(
            f"- Root cause candidate: `{root.edge_id}` at step `{root.step_idx}` "
            f"(latency `{root.latency_ms}` ms, queue `{root.queue_depth}`)"
        )
    lines.append(f"- Incident windows: `{len(windows)}`")
    lines.append("")

    lines.append("## First Response")
    lines.append("")
    lines.append("1. Stabilize pipeline by switching policy backend to `mock`.")
    lines.append("2. Cap infer latency path and monitor `observation_aggregator->policy_backend`.")
    lines.append("3. Replay incident trace and verify diagnosis signature matches live run.")
    lines.append("")

    lines.append("## Drill Checks")
    lines.append("")
    for check in checks:
        box = "x" if check["pass"] else " "
        lines.append(f"- [{box}] {check['name']}: observed `{check['observed']}` threshold `{check['threshold']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Incident response replay drill (deterministic synthetic scenario).")
    p.add_argument("--duration", type=float, default=4.0)
    p.add_argument("--obs-hz", type=float, default=30.0)
    p.add_argument("--policy-hz", type=float, default=10.0)
    p.add_argument("--control-hz", type=float, default=20.0)
    p.add_argument("--action-horizon", type=int, default=2)
    p.add_argument("--lag-step", type=int, default=8)
    p.add_argument("--lag-ms", type=float, default=220.0)
    p.add_argument("--base-policy-ms", type=float, default=8.0)
    p.add_argument("--threshold-ms", type=float, default=120.0)
    p.add_argument("--fail-on-mismatch", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--out-trace", type=Path, default=Path("logs/tutorial_incident/tut033_incident_trace.jsonl"))
    p.add_argument("--out-replay", type=Path, default=Path("logs/tutorial_incident/tut033_replay_trace.jsonl"))
    p.add_argument("--report", type=Path, default=Path("logs/tutorial_incident/tut033_incident_report.json"))
    p.add_argument("--checklist", type=Path, default=Path("logs/tutorial_incident/tut033_incident_checklist.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    baseline = simulate_envelopes(
        run_id="incident_baseline",
        duration_s=args.duration,
        obs_hz=args.obs_hz,
        policy_hz=args.policy_hz,
        control_hz=args.control_hz,
        action_horizon=args.action_horizon,
        lag_step=None,
        lag_ms=args.lag_ms,
        base_policy_ms=args.base_policy_ms,
    )
    incident = simulate_envelopes(
        run_id="incident_live",
        duration_s=args.duration,
        obs_hz=args.obs_hz,
        policy_hz=args.policy_hz,
        control_hz=args.control_hz,
        action_horizon=args.action_horizon,
        lag_step=args.lag_step,
        lag_ms=args.lag_ms,
        base_policy_ms=args.base_policy_ms,
    )

    write_jsonl(args.out_trace, [asdict(env) for env in incident])
    replay_rows = load_jsonl(args.out_trace)
    write_jsonl(args.out_replay, replay_rows)
    replay = rows_to_envelopes(replay_rows)

    baseline_summary = edge_summary(baseline)
    live_summary = edge_summary(incident)
    replay_summary = edge_summary(replay)

    live_root = first_incident(incident, threshold_ms=args.threshold_ms)
    replay_root = first_incident(replay, threshold_ms=args.threshold_ms)
    live_windows = incident_windows(incident, threshold_ms=args.threshold_ms)
    replay_windows = incident_windows(replay, threshold_ms=args.threshold_ms)

    live_sig = diagnosis_signature(live_root, live_windows)
    replay_sig = diagnosis_signature(replay_root, replay_windows)

    baseline_policy_max = next((r["latency_max_ms"] for r in baseline_summary if r["edge_id"] == EDGE_OBS_TO_POLICY), 0.0)
    live_policy_max = next((r["latency_max_ms"] for r in live_summary if r["edge_id"] == EDGE_OBS_TO_POLICY), 0.0)

    checks = [
        {
            "name": "incident_detected",
            "pass": live_root is not None,
            "observed": "present" if live_root is not None else "missing",
            "threshold": "present",
        },
        {
            "name": "policy_path_flagged",
            "pass": live_root is not None and live_root.edge_id == EDGE_OBS_TO_POLICY,
            "observed": live_root.edge_id if live_root else None,
            "threshold": EDGE_OBS_TO_POLICY,
        },
        {
            "name": "replay_signature_match",
            "pass": live_sig == replay_sig,
            "observed": {"live": live_sig, "replay": replay_sig},
            "threshold": "equal",
        },
        {
            "name": "policy_peak_regression_detected",
            "pass": live_policy_max > baseline_policy_max,
            "observed": {"baseline_max_ms": baseline_policy_max, "live_max_ms": live_policy_max},
            "threshold": "live max > baseline max",
        },
    ]

    result = {
        "schema_version": "retriever.incident_drill.v1",
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
            "threshold_ms": args.threshold_ms,
            "fail_on_mismatch": args.fail_on_mismatch,
        },
        "baseline_summary": baseline_summary,
        "live_summary": live_summary,
        "replay_summary": replay_summary,
        "live_root_cause": asdict(live_root) if live_root else None,
        "replay_root_cause": asdict(replay_root) if replay_root else None,
        "live_windows": live_windows,
        "replay_windows": replay_windows,
        "diagnosis_signature": {"live": live_sig, "replay": replay_sig},
        "checks": checks,
        "overall_pass": all(check["pass"] for check in checks),
    }
    write_json(args.report, result)

    checklist = render_checklist(
        generated_at=utc_now_iso(),
        threshold_ms=args.threshold_ms,
        root=live_root,
        windows=live_windows,
        checks=checks,
    )
    args.checklist.parent.mkdir(parents=True, exist_ok=True)
    args.checklist.write_text(checklist, encoding="utf-8")

    print("=== Incident Drill Summary (Baseline vs Incident vs Replay) ===")
    headers = ["edge_id", "baseline_p95", "incident_p95", "replay_p95", "incident_max"]
    summary_rows: list[list[Any]] = []
    for edge in [EDGE_OBS_TO_POLICY, EDGE_POLICY_TO_BUFFER, EDGE_BUFFER_TO_CONTROL]:
        b = next((r for r in baseline_summary if r["edge_id"] == edge), {})
        l = next((r for r in live_summary if r["edge_id"] == edge), {})
        r = next((r for r in replay_summary if r["edge_id"] == edge), {})
        summary_rows.append(
            [
                edge,
                b.get("latency_p95_ms", 0.0),
                l.get("latency_p95_ms", 0.0),
                r.get("latency_p95_ms", 0.0),
                l.get("latency_max_ms", 0.0),
            ]
        )
    print(format_table(headers, summary_rows))

    print("\n=== Drill Checks ===")
    check_rows = [[c["name"], c["pass"], c["observed"], c["threshold"]] for c in checks]
    print(format_table(["check", "pass", "observed", "threshold"], check_rows))

    print(f"\n[Artifacts] {args.out_trace}")
    print(f"[Artifacts] {args.out_replay}")
    print(f"[Artifacts] {args.report}")
    print(f"[Artifacts] {args.checklist}")

    if args.fail_on_mismatch and not result["overall_pass"]:
        print("\n[Result] FAIL: incident replay drill checks did not pass")
        raise SystemExit(1)

    print("\n[Result] PASS: incident replay drill checks passed")


if __name__ == "__main__":
    main()
