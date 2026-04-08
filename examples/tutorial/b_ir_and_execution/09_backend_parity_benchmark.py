"""
Backend parity benchmark tutorial (TUT-032).

Goal:
- Run one representative pipeline on both backends (`multiprocessing`, `dora`)
- Compare behavioral parity (sequence/value signature)
- Compare timing parity (latency/interval deltas)

This tutorial is a hard gate: if either backend fails, or parity checks fail,
this script exits non-zero.

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.09_backend_parity_benchmark
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from examples.tutorial._p0_utils import ensure_parent, format_table, percentile, utc_now_iso, write_json
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class SourceOut:
    sample: "SourceSample | None" = None


@io
class Stage1Out:
    sample: "Stage1Sample | None" = None


@io
class Stage2Out:
    sample: "Stage2Sample | None" = None


@dataclass
class SourceSample:
    seq: int
    source_ts: float
    signal: float


@dataclass
class Stage1Sample:
    seq: int
    source_ts: float
    signal: float


@dataclass
class Stage2Sample:
    seq: int
    source_ts: float
    result: float


class DeterministicSource(Flow[None, SourceOut]):
    def init(self) -> None:
        self.seq = 0

    def run(self, _):  # type: ignore[override]
        self.seq += 1
        source_ts = time.time()
        signal = math.sin(self.seq * 0.17) + math.cos(self.seq * 0.11)
        return SourceOut(sample=SourceSample(seq=self.seq, source_ts=source_ts, signal=round(signal, 6)))


class StageOne(Flow[SourceOut, Stage1Out]):
    def run(self, input: SourceOut) -> Stage1Out:
        if input.sample is None:
            return Stage1Out()
        value = (input.sample.signal * 1.35) + 0.42
        return Stage1Out(
            sample=Stage1Sample(
                seq=input.sample.seq,
                source_ts=input.sample.source_ts,
                signal=round(value, 6),
            )
        )


class StageTwo(Flow[Stage1Out, Stage2Out]):
    def run(self, input: Stage1Out) -> Stage2Out:
        if input.sample is None:
            return Stage2Out()
        value = math.tanh(input.sample.signal) * 2.5
        return Stage2Out(
            sample=Stage2Sample(
                seq=input.sample.seq,
                source_ts=input.sample.source_ts,
                result=round(value, 6),
            )
        )


class MetricsSink(Flow[Stage2Out, None]):
    def init(self) -> None:
        out_jsonl = os.environ.get("TUT032_OUTPUT_JSONL")
        if not out_jsonl:
            raise RuntimeError("TUT032_OUTPUT_JSONL is not set")
        self._out_jsonl = Path(out_jsonl)
        ensure_parent(self._out_jsonl)

    def run(self, input: Stage2Out) -> None:
        if input.sample is None:
            return None
        sink_ts = time.time()
        latency_ms = (sink_ts - float(input.sample.source_ts)) * 1000.0
        row = {
            "seq": int(input.sample.seq),
            "result": round(float(input.sample.result), 6),
            "source_ts": round(float(input.sample.source_ts), 9),
            "sink_ts": round(sink_ts, 9),
            "latency_ms": round(latency_ms, 3),
        }
        with self._out_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        return None


def representative_graph_fingerprint() -> str:
    edges = [
        ["deterministic_source", "stage_one"],
        ["stage_one", "stage_two"],
        ["stage_two", "metrics_sink"],
    ]
    payload = json.dumps(edges, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def build_pipeline(*, name: str, hz: float) -> Pipeline:
    pipe = Pipeline(name)

    with pipe:
        source = DeterministicSource() @ Rate(hz=hz)
        stage1 = StageOne() @ Trigger("sample")
        stage2 = StageTwo() @ Trigger("sample")
        sink = MetricsSink() @ Trigger("sample")

        pipe.connect(source, stage1, sync=Latest())
        pipe.connect(stage1, stage2, sync=Latest())
        pipe.connect(stage2, sink, sync=Latest())

    return pipe


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def hash_sequence(rows: list[dict[str, Any]]) -> str:
    payload = [[int(r["seq"]), float(r["result"])] for r in rows]
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def summarize_backend(backend: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError(f"No rows captured for backend={backend}")

    ordered = sorted(rows, key=lambda r: int(r["seq"]))
    seqs = [int(r["seq"]) for r in ordered]
    latencies = [float(r["latency_ms"]) for r in ordered]
    sink_ts = [float(r["sink_ts"]) for r in ordered]

    contiguous = all(seqs[i] == seqs[0] + i for i in range(len(seqs)))
    intervals = [(sink_ts[i] - sink_ts[i - 1]) * 1000.0 for i in range(1, len(sink_ts))]

    return {
        "backend": backend,
        "count": len(ordered),
        "seq_start": seqs[0],
        "seq_end": seqs[-1],
        "contiguous": contiguous,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 3),
        "p95_latency_ms": round(percentile(latencies, 95.0), 3),
        "max_latency_ms": round(max(latencies), 3),
        "mean_interval_ms": round(sum(intervals) / len(intervals), 3) if intervals else 0.0,
        "signature": hash_sequence(ordered),
        "rows": ordered,
    }


def run_backend(*, backend: str, hz: float, duration: float, out_jsonl: Path) -> dict[str, Any]:
    if out_jsonl.exists():
        out_jsonl.unlink()

    os.environ["TUT032_OUTPUT_JSONL"] = str(out_jsonl)
    pipe = build_pipeline(name=f"tut032_{backend}", hz=hz)
    pipe.run(backend=backend, duration=duration, blocking=True)

    rows = load_rows(out_jsonl)
    return summarize_backend(backend, rows)


def make_check(name: str, passed: bool, observed: Any, threshold: Any) -> dict[str, Any]:
    return {
        "name": name,
        "pass": bool(passed),
        "observed": observed,
        "threshold": threshold,
    }


def parity_report(
    mp: dict[str, Any],
    dora: dict[str, Any],
    *,
    count_ratio_tol: float,
    mean_latency_tol_ms: float,
    p95_latency_tol_ms: float,
) -> dict[str, Any]:
    mp_rows = mp["rows"]
    dora_rows = dora["rows"]

    prefix_n = min(len(mp_rows), len(dora_rows))
    mp_prefix_sig = hash_sequence(mp_rows[:prefix_n]) if prefix_n else ""
    dora_prefix_sig = hash_sequence(dora_rows[:prefix_n]) if prefix_n else ""

    count_ratio = abs(mp["count"] - dora["count"]) / max(mp["count"], dora["count"])
    mean_latency_delta = abs(mp["mean_latency_ms"] - dora["mean_latency_ms"])
    p95_latency_delta = abs(mp["p95_latency_ms"] - dora["p95_latency_ms"])

    checks = [
        make_check("mp_contiguous", mp["contiguous"], mp["contiguous"], True),
        make_check("dora_contiguous", dora["contiguous"], dora["contiguous"], True),
        make_check("prefix_window_non_empty", prefix_n > 0, prefix_n, ">0"),
        make_check("prefix_signature_match", mp_prefix_sig == dora_prefix_sig, {
            "mp": mp_prefix_sig,
            "dora": dora_prefix_sig,
            "prefix_n": prefix_n,
        }, "equal"),
        make_check("count_ratio_within_tol", count_ratio <= count_ratio_tol, round(count_ratio, 4), f"<= {count_ratio_tol}"),
        make_check(
            "mean_latency_delta_within_tol",
            mean_latency_delta <= mean_latency_tol_ms,
            round(mean_latency_delta, 3),
            f"<= {mean_latency_tol_ms}",
        ),
        make_check(
            "p95_latency_delta_within_tol",
            p95_latency_delta <= p95_latency_tol_ms,
            round(p95_latency_delta, 3),
            f"<= {p95_latency_tol_ms}",
        ),
    ]

    overall_pass = all(c["pass"] for c in checks)
    return {
        "overall_pass": overall_pass,
        "prefix_n": prefix_n,
        "checks": checks,
    }


def write_csv(path: Path, mp: dict[str, Any], dora: dict[str, Any], parity: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "backend",
                "count",
                "seq_start",
                "seq_end",
                "contiguous",
                "mean_latency_ms",
                "p95_latency_ms",
                "max_latency_ms",
                "mean_interval_ms",
                "signature",
            ],
        )
        writer.writeheader()
        for row in (mp, dora):
            writer.writerow({k: row[k] for k in writer.fieldnames})

    parity_csv = path.with_name(path.stem + "_checks.csv")
    with parity_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "pass", "observed", "threshold"])
        writer.writeheader()
        for c in parity["checks"]:
            writer.writerow(c)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backend parity benchmark tutorial (hard dora gate).")
    p.add_argument("--duration", type=float, default=2.5, help="Run duration per backend in seconds.")
    p.add_argument("--hz", type=float, default=20.0, help="Source rate used for both backend runs.")
    p.add_argument("--count-ratio-tol", type=float, default=0.50)
    p.add_argument("--mean-latency-tol-ms", type=float, default=900.0)
    p.add_argument("--p95-latency-tol-ms", type=float, default=1500.0)
    p.add_argument("--fail-on-drift", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("logs/tutorial_parity/tut032_backend_parity.json"),
    )
    p.add_argument(
        "--out-csv",
        type=Path,
        default=Path("logs/tutorial_parity/tut032_backend_parity.csv"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    graph_fp = representative_graph_fingerprint()
    print(f"[Contract] graph_fingerprint={graph_fp}")
    print("[Contract] Running parity benchmark on backends: multiprocessing, dora")

    try:
        mp = run_backend(
            backend="multiprocessing",
            hz=args.hz,
            duration=args.duration,
            out_jsonl=args.out_json.with_name("tut032_mp_rows.jsonl"),
        )
        dora = run_backend(
            backend="dora",
            hz=args.hz,
            duration=args.duration,
            out_jsonl=args.out_json.with_name("tut032_dora_rows.jsonl"),
        )
    except Exception as exc:
        print(f"[Backend Error] {exc}")
        raise SystemExit(2) from exc

    parity = parity_report(
        mp,
        dora,
        count_ratio_tol=args.count_ratio_tol,
        mean_latency_tol_ms=args.mean_latency_tol_ms,
        p95_latency_tol_ms=args.p95_latency_tol_ms,
    )

    metric_headers = [
        "backend",
        "count",
        "seq_range",
        "contiguous",
        "mean_latency_ms",
        "p95_latency_ms",
        "max_latency_ms",
        "mean_interval_ms",
        "signature",
    ]
    metric_rows = []
    for row in (mp, dora):
        metric_rows.append(
            [
                row["backend"],
                row["count"],
                f"{row['seq_start']}..{row['seq_end']}",
                row["contiguous"],
                f"{row['mean_latency_ms']:.3f}",
                f"{row['p95_latency_ms']:.3f}",
                f"{row['max_latency_ms']:.3f}",
                f"{row['mean_interval_ms']:.3f}",
                row["signature"],
            ]
        )

    print("\n=== Backend Metrics ===")
    print(format_table(metric_headers, metric_rows))

    check_rows = [[c["name"], c["pass"], c["observed"], c["threshold"]] for c in parity["checks"]]
    print("\n=== Parity Checks ===")
    print(format_table(["check", "pass", "observed", "threshold"], check_rows))

    payload = {
        "schema_version": "retriever.backend_parity.v1",
        "created_at": utc_now_iso(),
        "graph_fingerprint": graph_fp,
        "config": {
            "duration": args.duration,
            "hz": args.hz,
            "count_ratio_tol": args.count_ratio_tol,
            "mean_latency_tol_ms": args.mean_latency_tol_ms,
            "p95_latency_tol_ms": args.p95_latency_tol_ms,
            "fail_on_drift": args.fail_on_drift,
        },
        "metrics": {
            "multiprocessing": {k: v for k, v in mp.items() if k != "rows"},
            "dora": {k: v for k, v in dora.items() if k != "rows"},
        },
        "parity": parity,
    }

    write_json(args.out_json, payload)
    write_csv(args.out_csv, mp, dora, parity)

    print(f"\n[Artifacts] {args.out_json}")
    print(f"[Artifacts] {args.out_csv}")
    print(f"[Artifacts] {args.out_csv.with_name(args.out_csv.stem + '_checks.csv')}")

    if args.fail_on_drift and not parity["overall_pass"]:
        print("\n[Result] FAIL: backend parity checks did not pass")
        raise SystemExit(1)

    print("\n[Result] PASS: backend parity checks passed")


if __name__ == "__main__":
    main()
