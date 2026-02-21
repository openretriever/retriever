"""
Run manifest and lineage walkthrough.

Covers:
1) Create machine-readable run metadata bundle
2) Link recording artifact to run_id + config hash
3) Compare two manifests and summarize differences

Run:
  pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, flow_io
from retriever.lib.mcap import MCAPReader, MCAPWriter

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


@flow_io
@dataclass
class CounterOut:
    value: int | None = None


class Counter(Flow[None, CounterOut]):
    def init(self) -> None:
        self.i = 0

    def run(self, _):  # type: ignore[override]
        self.i += 1
        return CounterOut(value=self.i)


class Sink(Flow[CounterOut, None]):
    def run(self, _input: CounterOut) -> None:
        return None


@dataclass
class PolicyRunConfig:
    backend: str = "in-process"
    steps: int = 20
    dt: float = 0.05
    pipeline_name: str = "tut025_manifest_lineage"


@dataclass
class ArtifactRef:
    kind: str
    path: str
    sha256: str
    bytes: int


@dataclass
class ManifestLineage:
    parent_run_ids: list[str] = field(default_factory=list)
    parent_manifests: list[str] = field(default_factory=list)


@dataclass
class RunManifest:
    schema_version: str
    run_id: str
    created_at: str
    config: dict[str, Any]
    config_sha256: str
    artifacts: list[ArtifactRef]
    replay_command: str
    lineage: ManifestLineage
    summary: dict[str, Any]


def build_pipeline(name: str) -> Pipeline:
    pipe = Pipeline(name)
    src = Counter() @ Rate(hz=20)
    sink = Sink() @ Trigger("value")
    pipe.connect(src, sink, sync=Latest())
    return pipe


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def run_and_record(*, config: PolicyRunConfig, recording_path: Path) -> dict[str, Any]:
    pipe = build_pipeline(config.pipeline_name)
    non_null_outputs = 0

    try:
        with MCAPWriter(recording_path) as writer:
            for step_idx in range(config.steps):
                step_result = pipe.step(dt=config.dt)
                writer.write_step(step_result, step_idx=step_idx)
                non_null_outputs += sum(value is not None for value in step_result.outputs.values())
    finally:
        pipe.close_stepper()

    with MCAPReader(recording_path) as reader:
        replay_steps = list(reader)

    return {
        "steps_requested": config.steps,
        "steps_recorded": len(replay_steps),
        "non_null_outputs": non_null_outputs,
        "first_timestamp_s": replay_steps[0]["now"] if replay_steps else None,
        "last_timestamp_s": replay_steps[-1]["now"] if replay_steps else None,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _derive_lineage(parent_manifest: Path | None) -> ManifestLineage:
    if parent_manifest is None:
        return ManifestLineage()

    parent_data = load_manifest(parent_manifest)
    parent_run_id = str(parent_data.get("run_id", "unknown"))
    return ManifestLineage(parent_run_ids=[parent_run_id], parent_manifests=[str(parent_manifest)])


def generate_manifest(
    *,
    out_dir: Path,
    steps: int,
    dt: float,
    run_id: str | None,
    parent_manifest: Path | None,
) -> Path:
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"

    cfg = PolicyRunConfig(steps=steps, dt=dt)
    cfg_dict = {
        "backend": cfg.backend,
        "steps": cfg.steps,
        "dt": cfg.dt,
        "pipeline_name": cfg.pipeline_name,
    }

    recording_path = out_dir / "artifacts" / f"{run_id}.mcap"
    recording_path.parent.mkdir(parents=True, exist_ok=True)

    summary = run_and_record(config=cfg, recording_path=recording_path)

    artifact = ArtifactRef(
        kind="recording.mcap",
        path=str(recording_path),
        sha256=sha256_file(recording_path),
        bytes=recording_path.stat().st_size,
    )

    lineage = _derive_lineage(parent_manifest)

    manifest_path = out_dir / "manifests" / f"{run_id}.manifest.json"
    replay_cmd = (
        "pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage "
        f"replay --manifest {manifest_path}"
    )

    manifest = RunManifest(
        schema_version="retriever.run_manifest.v1",
        run_id=run_id,
        created_at=utc_now_iso(),
        config=cfg_dict,
        config_sha256=config_hash(cfg_dict),
        artifacts=[artifact],
        replay_command=replay_cmd,
        lineage=lineage,
        summary=summary,
    )

    write_json(
        manifest_path,
        {
            "schema_version": manifest.schema_version,
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "config": manifest.config,
            "config_sha256": manifest.config_sha256,
            "artifacts": [artifact.__dict__ for artifact in manifest.artifacts],
            "replay_command": manifest.replay_command,
            "lineage": {
                "parent_run_ids": manifest.lineage.parent_run_ids,
                "parent_manifests": manifest.lineage.parent_manifests,
            },
            "summary": manifest.summary,
        },
    )

    return manifest_path


def replay_manifest(manifest_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    if not manifest.get("artifacts"):
        raise ValueError(f"Manifest has no artifacts: {manifest_path}")

    recording_path = Path(manifest["artifacts"][0]["path"])
    with MCAPReader(recording_path) as reader:
        steps = list(reader)

    print(f"[Replay] manifest={manifest_path}")
    print(f"[Replay] recording={recording_path}")
    print(f"[Replay] steps={len(steps)}")
    if steps:
        print(f"[Replay] first_ts={steps[0]['now']:.3f}s last_ts={steps[-1]['now']:.3f}s")


def compare_manifests(a_path: Path, b_path: Path) -> dict[str, Any]:
    a = load_manifest(a_path)
    b = load_manifest(b_path)

    a_cfg = a.get("config", {})
    b_cfg = b.get("config", {})

    cfg_keys = sorted(set(a_cfg) | set(b_cfg))
    cfg_diffs: list[tuple[str, Any, Any]] = []
    for key in cfg_keys:
        if a_cfg.get(key) != b_cfg.get(key):
            cfg_diffs.append((key, a_cfg.get(key), b_cfg.get(key)))

    a_summary = a.get("summary", {})
    b_summary = b.get("summary", {})

    summary_rows = [
        ("steps_recorded", a_summary.get("steps_recorded"), b_summary.get("steps_recorded")),
        ("non_null_outputs", a_summary.get("non_null_outputs"), b_summary.get("non_null_outputs")),
        ("config_sha256", a.get("config_sha256"), b.get("config_sha256")),
    ]

    print("\n=== Config Differences ===")
    if cfg_diffs:
        print(format_table(["field", "manifest_a", "manifest_b"], cfg_diffs))
    else:
        print("No config differences.")

    print("\n=== Run Summary Differences ===")
    print(format_table(["field", "manifest_a", "manifest_b"], summary_rows))

    result = {
        "a": str(a_path),
        "b": str(b_path),
        "config_differences": [
            {"field": field, "a": old, "b": new}
            for field, old, new in cfg_diffs
        ],
        "summary_differences": [
            {"field": field, "a": old, "b": new}
            for field, old, new in summary_rows
        ],
    }
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run manifest + lineage tutorial.")
    sub = p.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="Generate one run recording and manifest.")
    gen.add_argument("--out-dir", type=Path, default=Path("logs/tutorial_manifest"))
    gen.add_argument("--steps", type=int, default=20)
    gen.add_argument("--dt", type=float, default=0.05)
    gen.add_argument("--run-id", type=str, default=None)
    gen.add_argument("--parent-manifest", type=Path, default=None)

    replay = sub.add_parser("replay", help="Replay metadata from a manifest.")
    replay.add_argument("--manifest", type=Path, required=True)

    cmp_cmd = sub.add_parser("compare", help="Compare two manifests.")
    cmp_cmd.add_argument("--a", type=Path, required=True)
    cmp_cmd.add_argument("--b", type=Path, required=True)
    cmp_cmd.add_argument("--out", type=Path, default=None, help="Optional compare summary JSON.")

    demo = sub.add_parser("demo", help="Create two runs and compare them.")
    demo.add_argument("--out-dir", type=Path, default=Path("logs/tutorial_manifest"))
    demo.add_argument("--steps-a", type=int, default=20)
    demo.add_argument("--steps-b", type=int, default=28)
    demo.add_argument("--dt-a", type=float, default=0.05)
    demo.add_argument("--dt-b", type=float, default=0.08)

    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.cmd == "generate":
        manifest = generate_manifest(
            out_dir=args.out_dir,
            steps=args.steps,
            dt=args.dt,
            run_id=args.run_id,
            parent_manifest=args.parent_manifest,
        )
        print(f"[Manifest] written: {manifest}")
        print(
            "[Replay cmd] pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage "
            f"replay --manifest {manifest}"
        )
        return

    if args.cmd == "replay":
        replay_manifest(args.manifest)
        return

    if args.cmd == "compare":
        result = compare_manifests(args.a, args.b)
        if args.out is not None:
            write_json(args.out, result)
            print(f"[Compare] summary JSON: {args.out}")
        return

    if args.cmd == "demo":
        manifest_a = generate_manifest(
            out_dir=args.out_dir,
            steps=args.steps_a,
            dt=args.dt_a,
            run_id="tut025_baseline",
            parent_manifest=None,
        )
        manifest_b = generate_manifest(
            out_dir=args.out_dir,
            steps=args.steps_b,
            dt=args.dt_b,
            run_id="tut025_candidate",
            parent_manifest=manifest_a,
        )

        print(f"[Demo] baseline_manifest={manifest_a}")
        print(f"[Demo] candidate_manifest={manifest_b}")
        compare = compare_manifests(manifest_a, manifest_b)

        compare_path = args.out_dir / "manifests" / "tut025_demo_compare.json"
        write_json(compare_path, compare)
        print(f"[Demo] compare summary={compare_path}")
        return

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
