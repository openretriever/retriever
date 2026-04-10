"""
Release readiness walkthrough tutorial.

Covers:
1) Map tutorial evidence to release acceptance gates
2) Run an end-to-end pre-release check sequence
3) Emit go/no-go checklist artifact with pass/fail reasons

Run:
  pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


@dataclass
class GateResult:
    gate_id: str
    name: str
    passed: bool
    reason: str
    evidence: list[str]


@dataclass
class MatrixCheck:
    item: str
    passed: bool
    reason: str
    evidence: list[str]


def bundled_reference_root() -> Path:
    return Path(__file__).resolve().parent / "release_reference_v1"


def find_reference_root(explicit: Path | None) -> Path:
    bundled = bundled_reference_root().resolve()

    if explicit is not None:
        explicit = explicit.resolve()
        candidates = [explicit, explicit / "release_reference_v1"]
        for candidate in candidates:
            if (candidate / "dev_retriever_release").exists():
                return candidate
        raise FileNotFoundError(
            f"Release reference bundle not found from explicit path: {explicit}. "
            "Expected a directory containing dev_retriever_release/."
        )

    if bundled.exists():
        return bundled

    raise FileNotFoundError(
        "Bundled release reference bundle is missing. Pass --reference-root to a directory containing dev_retriever_release/."
    )


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def read_backends_from_csv(path: Path) -> set[str]:
    backends: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            backend = row.get("backend")
            if backend:
                backends.add(backend.strip())
    return backends


def read_blocked_transition_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return int(payload.get("blocked_transition_count", 0))


def render_markdown(
    *,
    generated_at: str,
    reference_root: Path,
    gates: list[GateResult],
    matrix_checks: list[MatrixCheck],
    decision: str,
) -> str:
    lines: list[str] = []
    lines.append("# TUT-029 Release Readiness Checklist")
    lines.append("")
    lines.append(f"- Generated at: {generated_at}")
    lines.append(f"- Reference root: `{reference_root}`")
    lines.append("")

    lines.append("## Acceptance Gates")
    lines.append("")
    for gate in gates:
        box = "x" if gate.passed else " "
        lines.append(f"- [{box}] {gate.gate_id} {gate.name}: {gate.reason}")
        if gate.evidence:
            lines.append(f"  evidence: {', '.join(gate.evidence)}")
    lines.append("")

    lines.append("## Test Matrix Checks")
    lines.append("")
    lines.append("| Item | Status | Reason | Evidence |")
    lines.append("|---|---|---|---|")
    for row in matrix_checks:
        status = "PASS" if row.passed else "FAIL"
        evidence = "; ".join(row.evidence) if row.evidence else "-"
        lines.append(f"| {row.item} | {status} | {row.reason} | {evidence} |")
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{decision}**")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Release-readiness gate walkthrough.")
    p.add_argument(
        "--reference-root",
        "--notes-root",
        dest="reference_root",
        type=Path,
        default=None,
        help="Path to a release reference bundle.",
    )
    p.add_argument("--evidence-dir", type=Path, default=Path("logs/tutorial_release_evidence"))
    p.add_argument(
        "--out",
        type=Path,
        default=Path("logs/tutorial_release_readiness/tut029_release_checklist.md"),
    )
    p.add_argument(
        "--summary-json",
        type=Path,
        default=Path("logs/tutorial_release_readiness/tut029_release_summary.json"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    reference_root = find_reference_root(args.reference_root)

    release_root = reference_root / "dev_retriever_release"
    validation_root = release_root / "validation"
    core_root = release_root / "core_release"
    pipeline_root = release_root / "pipeline_release"
    risk_root = release_root / "risks"

    docs = {
        "acceptance_gates": validation_root / "acceptance_gates.md",
        "test_matrix": validation_root / "test_matrix.md",
        "public_api": core_root / "public_api_changes.md",
        "release_checklist": core_root / "release_checklist.md",
        "pipeline_spec": pipeline_root / "representative_pipeline_spec.md",
        "operator_runbook": pipeline_root / "operator_runbook.md",
        "risk_register": risk_root / "risk_register.md",
        "dependency_licensing": risk_root / "dependency_and_licensing.md",
    }

    trace_report = first_existing(
        [
            Path("logs/tutorial_trace/tut024_trace_report.json"),
            args.evidence_dir / "tut024_trace_report.json",
        ]
    )
    manifest_path = first_existing(
        sorted((Path("logs/tutorial_manifest/manifests").glob("*.manifest.json")), reverse=True)
    )
    if manifest_path is None:
        manifest_path = first_existing([args.evidence_dir / "latest.manifest.json"])

    policy_metrics = first_existing(
        [
            Path("logs/tutorial_policy/tut027_backend_metrics.csv"),
            args.evidence_dir / "tut027_backend_metrics.csv",
        ]
    )
    authority_log = first_existing(
        [
            Path("logs/tutorial_authority/tut028_authority_log.json"),
            args.evidence_dir / "tut028_authority_log.json",
        ]
    )

    missing_docs = [name for name, path in docs.items() if not path.exists()]

    gate_a = GateResult(
        gate_id="Gate A",
        name="Documentation Completeness",
        passed=not missing_docs,
        reason=("all required release docs are present" if not missing_docs else f"missing docs: {', '.join(missing_docs)}"),
        evidence=[str(path) for path in docs.values() if path.exists()],
    )

    public_api_text = docs["public_api"].read_text(encoding="utf-8") if docs["public_api"].exists() else ""
    manifest_ok = False
    manifest_reason = "manifest evidence missing"
    if manifest_path and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_ok = bool(manifest.get("run_id") and manifest.get("artifacts") and manifest.get("replay_command"))
            manifest_reason = "manifest contains run_id/artifacts/replay_command" if manifest_ok else "manifest missing required keys"
        except json.JSONDecodeError:
            manifest_reason = "manifest is not valid JSON"

    gate_b_checks = [
        "Optional extras commitments" in public_api_text,
        "Plugin interface commitments" in public_api_text,
        "Recording and replay contract" in public_api_text,
        manifest_ok,
    ]
    gate_b = GateResult(
        gate_id="Gate B",
        name="Core Contract Readiness",
        passed=all(gate_b_checks),
        reason=(
            "core contract docs present and manifest evidence linked"
            if all(gate_b_checks)
            else f"missing core contract evidence ({manifest_reason})"
        ),
        evidence=[
            str(docs["public_api"]) if docs["public_api"].exists() else "",
            str(docs["release_checklist"]) if docs["release_checklist"].exists() else "",
            str(manifest_path) if manifest_path else "",
        ],
    )

    backend_set: set[str] = set()
    if policy_metrics and policy_metrics.exists():
        backend_set = read_backends_from_csv(policy_metrics)

    blocked_count = read_blocked_transition_count(authority_log) if authority_log and authority_log.exists() else 0

    required_backends = {"openpi_pi05", "lerobot", "mock"}
    missing_backends = sorted(required_backends - backend_set)

    gate_c_checks = [
        docs["pipeline_spec"].exists(),
        docs["operator_runbook"].exists(),
        not missing_backends,
        blocked_count >= 1,
    ]
    gate_c_reason = "representative pipeline checks covered"
    if missing_backends:
        gate_c_reason = f"policy backend evidence missing: {', '.join(missing_backends)}"
    elif blocked_count < 1:
        gate_c_reason = "authority FSM log missing blocked transition evidence"

    gate_c = GateResult(
        gate_id="Gate C",
        name="Representative Pipeline Readiness",
        passed=all(gate_c_checks),
        reason=gate_c_reason,
        evidence=[
            str(docs["pipeline_spec"]),
            str(docs["operator_runbook"]),
            str(policy_metrics) if policy_metrics else "",
            str(authority_log) if authority_log else "",
        ],
    )

    gate_d_checks = [docs["risk_register"].exists(), docs["dependency_licensing"].exists()]
    gate_d = GateResult(
        gate_id="Gate D",
        name="Risk and Compliance Readiness",
        passed=all(gate_d_checks),
        reason=("risk register + dependency/licensing docs present" if all(gate_d_checks) else "risk/compliance docs incomplete"),
        evidence=[
            str(docs["risk_register"]) if docs["risk_register"].exists() else "",
            str(docs["dependency_licensing"]) if docs["dependency_licensing"].exists() else "",
        ],
    )

    prior_gates = [gate_a, gate_b, gate_c, gate_d]
    blocking = [g.gate_id for g in prior_gates if not g.passed]

    gate_e = GateResult(
        gate_id="Gate E",
        name="Go/No-Go",
        passed=not blocking,
        reason=("all prior gates passed" if not blocking else f"blocked by: {', '.join(blocking)}"),
        evidence=[g.gate_id for g in prior_gates if g.passed],
    )

    gates = prior_gates + [gate_e]

    matrix_checks = [
        MatrixCheck(
            item="Core: package install paths",
            passed=docs["release_checklist"].exists(),
            reason="release checklist file available",
            evidence=[str(docs["release_checklist"])],
        ),
        MatrixCheck(
            item="Core: recording write/read/replay",
            passed=manifest_ok,
            reason=manifest_reason,
            evidence=[str(manifest_path)] if manifest_path else [],
        ),
        MatrixCheck(
            item="Core: plugin loading paths",
            passed="Plugin interface commitments" in public_api_text,
            reason="plugin contract documented" if "Plugin interface commitments" in public_api_text else "plugin contract section missing",
            evidence=[str(docs["public_api"])],
        ),
        MatrixCheck(
            item="Representative: policy backends openpi_pi05|lerobot|mock",
            passed=not missing_backends,
            reason=("all required backends present" if not missing_backends else f"missing: {', '.join(missing_backends)}"),
            evidence=[str(policy_metrics)] if policy_metrics else [],
        ),
        MatrixCheck(
            item="Representative: authority intervention semantics",
            passed=blocked_count >= 1,
            reason=(
                "blocked transition evidence captured"
                if blocked_count >= 1
                else "missing blocked invalid-transition evidence"
            ),
            evidence=[str(authority_log)] if authority_log else [],
        ),
    ]

    decision = "GO" if gate_e.passed else "NO-GO"

    markdown = render_markdown(
        generated_at=utc_now_iso(),
        reference_root=reference_root,
        gates=gates,
        matrix_checks=matrix_checks,
        decision=decision,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")

    summary = {
        "schema_version": "retriever.release_readiness.v1",
        "generated_at": utc_now_iso(),
        "notes_root": str(notes_root),
        "decision": decision,
        "gates": [asdict(g) for g in gates],
        "matrix_checks": [asdict(row) for row in matrix_checks],
    }
    write_json(args.summary_json, summary)

    print("\n=== Acceptance Gate Results ===")
    rows = [[g.gate_id, "PASS" if g.passed else "FAIL", g.reason] for g in gates]
    print(format_table(["gate", "status", "reason"], rows))

    print("\n=== Decision ===")
    print(decision)
    print(f"\n[Artifacts] checklist={args.out} summary={args.summary_json}")


if __name__ == "__main__":
    main()
