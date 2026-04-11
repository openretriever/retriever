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


def read_manifest_status(path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "manifest is not valid JSON"

    ok = bool(payload.get("run_id") and payload.get("artifacts") and payload.get("replay_command"))
    if ok:
        return True, "manifest contains run_id/artifacts/replay_command"
    return False, "manifest missing required keys"


def read_parity_status(path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "parity report is not valid JSON"

    overall_pass = bool(payload.get("parity", {}).get("overall_pass"))
    if overall_pass:
        return True, "backend parity passed"
    return False, "backend parity report indicates drift"


def read_incident_status(path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "incident report is not valid JSON"

    overall = bool(payload.get("overall_pass"))
    live = payload.get("diagnosis_signature", {}).get("live")
    replay = payload.get("diagnosis_signature", {}).get("replay")
    if overall and live is not None and live == replay:
        return True, "incident replay diagnosis signature matched"
    return False, "incident report failed or replay signature mismatch"


def render_markdown(
    *,
    generated_at: str,
    contracts_root: Path,
    expected_root: Path,
    gates: list[GateResult],
    matrix_checks: list[MatrixCheck],
    decision: str,
) -> str:
    lines: list[str] = []
    lines.append("# TUT-029 Release Readiness Checklist")
    lines.append("")
    lines.append(f"- Generated at: {generated_at}")
    lines.append(f"- Contracts root: `{contracts_root}`")
    lines.append(f"- Expected outputs root: `{expected_root}`")
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
        "--contracts-root",
        type=Path,
        default=Path("docs/tutorials"),
        help="Path to tutorial documentation contracts.",
    )
    p.add_argument(
        "--expected-root",
        type=Path,
        default=Path("examples/tutorial/expected_outputs"),
        help="Path to expected output specs used as checklist contracts.",
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

    contracts_root = args.contracts_root.resolve()
    expected_root = args.expected_root.resolve()

    required_docs = {
        "tutorial_index": contracts_root / "index.md",
        "track_h_release_readiness": contracts_root / "track_h_release_readiness.md",
        "integrated_tutorial": contracts_root / "tutorial_integrated_debug_to_release.md",
        "core_release_walkthrough": contracts_root / "walkthrough_core_release_path.md",
        "notebook_ready": contracts_root / "notebook_ready.md",
    }

    expected_specs = {
        "trace_contract": expected_root / "024_trace_contract_basics.md",
        "manifest_lineage": expected_root / "025_run_manifest_and_lineage.md",
        "policy_backends": expected_root / "027_closed_loop_policy_backend_abstraction.md",
        "authority_fsm": expected_root / "028_operator_mode_and_authority_fsm.md",
        "backend_parity": expected_root / "032_backend_parity_benchmark.md",
        "incident_replay": expected_root / "033_incident_response_replay_drill.md",
        "functional_fanin_fanout": expected_root / "034_functional_fanin_fanout.md",
        "deadline_mode_switch": expected_root / "035_deadline_aware_mode_switch.md",
        "mcap_session_inspection": expected_root / "036_mcap_session_inspection.md",
    }

    missing_docs = [name for name, path in required_docs.items() if not path.exists()]
    missing_expected = [name for name, path in expected_specs.items() if not path.exists()]

    gate_a = GateResult(
        gate_id="Gate A",
        name="Documentation Completeness",
        passed=not (missing_docs or missing_expected),
        reason=(
            "tutorial contracts and expected outputs are present"
            if not (missing_docs or missing_expected)
            else f"missing docs/specs: {', '.join(missing_docs + missing_expected)}"
        ),
        evidence=[
            str(path)
            for path in list(required_docs.values()) + list(expected_specs.values())
            if path.exists()
        ],
    )

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

    manifest_ok = False
    manifest_reason = "manifest evidence missing"
    if manifest_path and manifest_path.exists():
        manifest_ok, manifest_reason = read_manifest_status(manifest_path)

    gate_b_checks = [trace_report is not None, manifest_ok]
    gate_b = GateResult(
        gate_id="Gate B",
        name="Core Contract Readiness",
        passed=all(gate_b_checks),
        reason=(
            "trace + manifest evidence present"
            if all(gate_b_checks)
            else f"core evidence incomplete ({manifest_reason})"
        ),
        evidence=[
            str(trace_report) if trace_report else "",
            str(manifest_path) if manifest_path else "",
        ],
    )

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

    backend_set: set[str] = set()
    if policy_metrics and policy_metrics.exists():
        backend_set = read_backends_from_csv(policy_metrics)

    blocked_count = read_blocked_transition_count(authority_log) if authority_log and authority_log.exists() else 0
    required_backends = {"openpi_pi05", "lerobot", "mock"}
    missing_backends = sorted(required_backends - backend_set)

    gate_c_checks = [policy_metrics is not None, not missing_backends, blocked_count >= 1]
    if missing_backends:
        gate_c_reason = f"policy backend evidence missing: {', '.join(missing_backends)}"
    elif blocked_count < 1:
        gate_c_reason = "authority FSM log missing blocked transition evidence"
    elif policy_metrics is None:
        gate_c_reason = "policy backend metrics missing"
    else:
        gate_c_reason = "representative pipeline checks covered"

    gate_c = GateResult(
        gate_id="Gate C",
        name="Representative Pipeline Readiness",
        passed=all(gate_c_checks),
        reason=gate_c_reason,
        evidence=[
            str(policy_metrics) if policy_metrics else "",
            str(authority_log) if authority_log else "",
        ],
    )

    parity_report = first_existing(
        [
            Path("logs/tutorial_parity/tut032_backend_parity.json"),
            args.evidence_dir / "tut032_backend_parity.json",
        ]
    )
    incident_report = first_existing(
        [
            Path("logs/tutorial_incident/tut033_incident_report.json"),
            args.evidence_dir / "tut033_incident_report.json",
        ]
    )

    parity_ok = False
    parity_reason = "backend parity report missing"
    if parity_report and parity_report.exists():
        parity_ok, parity_reason = read_parity_status(parity_report)

    incident_ok = False
    incident_reason = "incident replay report missing"
    if incident_report and incident_report.exists():
        incident_ok, incident_reason = read_incident_status(incident_report)

    gate_d_checks = [parity_ok, incident_ok]
    gate_d = GateResult(
        gate_id="Gate D",
        name="Reliability and Replay Readiness",
        passed=all(gate_d_checks),
        reason=(
            "parity and incident replay reliability checks passed"
            if all(gate_d_checks)
            else f"reliability evidence incomplete ({parity_reason}; {incident_reason})"
        ),
        evidence=[
            str(parity_report) if parity_report else "",
            str(incident_report) if incident_report else "",
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
            item="Docs: tutorial contracts + expected outputs",
            passed=gate_a.passed,
            reason=gate_a.reason,
            evidence=gate_a.evidence,
        ),
        MatrixCheck(
            item="Core: trace report present",
            passed=trace_report is not None,
            reason=("trace report available" if trace_report else "trace report missing"),
            evidence=[str(trace_report)] if trace_report else [],
        ),
        MatrixCheck(
            item="Core: recording write/read/replay manifest",
            passed=manifest_ok,
            reason=manifest_reason,
            evidence=[str(manifest_path)] if manifest_path else [],
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
        MatrixCheck(
            item="Reliability: backend parity",
            passed=parity_ok,
            reason=parity_reason,
            evidence=[str(parity_report)] if parity_report else [],
        ),
        MatrixCheck(
            item="Reliability: incident replay signature consistency",
            passed=incident_ok,
            reason=incident_reason,
            evidence=[str(incident_report)] if incident_report else [],
        ),
    ]

    decision = "GO" if gate_e.passed else "NO-GO"

    markdown = render_markdown(
        generated_at=utc_now_iso(),
        contracts_root=contracts_root,
        expected_root=expected_root,
        gates=gates,
        matrix_checks=matrix_checks,
        decision=decision,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")

    summary = {
        "schema_version": "retriever.release_readiness.v1",
        "generated_at": utc_now_iso(),
        "contracts_root": str(contracts_root),
        "expected_root": str(expected_root),
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
