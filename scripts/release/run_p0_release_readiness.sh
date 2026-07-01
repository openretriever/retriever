#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if command -v pixi >/dev/null 2>&1; then
  RUNNER=(pixi run python)
  RUNNER_LABEL="pixi run python"
else
  RUNNER=(python)
  RUNNER_LABEL="python (PYTHONPATH=src)"
  export PYTHONPATH="${PYTHONPATH:-src}"
fi

STAMP="$(date -u +%Y%m%d_%H%M%S)"
SESSION_DIR="logs/tutorial_release_readiness/p0_run_${STAMP}"
mkdir -p "$SESSION_DIR"

CHECKLIST_MD="$SESSION_DIR/tut029_release_checklist.md"
SUMMARY_JSON="$SESSION_DIR/tut029_release_summary.json"
RUN_SUMMARY_MD="$SESSION_DIR/p0_run_summary.md"

run_step() {
  local step_name="$1"
  shift
  local log_file="$SESSION_DIR/${step_name}.log"
  echo "[run] $step_name"
  echo "[cmd] $*"
  "$@" 2>&1 | tee "$log_file"
}

run_step tut024_trace_contract_basics   "${RUNNER[@]}" -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics

run_step tut025_run_manifest_and_lineage   "${RUNNER[@]}" -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo

run_step tut027_policy_backend_abstraction   "${RUNNER[@]}" -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction

run_step tut028_authority_fsm   "${RUNNER[@]}" -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm

run_step tut029_release_readiness_walkthrough   "${RUNNER[@]}" -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough   --out "$CHECKLIST_MD"   --summary-json "$SUMMARY_JSON"

if [[ ! -f "$SUMMARY_JSON" ]]; then
  echo "[error] missing summary JSON: $SUMMARY_JSON" >&2
  exit 3
fi

DECISION="$("${RUNNER[@]}" - <<'JSONPY' "$SUMMARY_JSON"
import json
import sys
p = sys.argv[1]
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('decision', 'UNKNOWN'))
JSONPY
)"

cat > "$RUN_SUMMARY_MD" <<EOF
# P0 Tutorial Execution Summary

- Timestamp (UTC): ${STAMP}
- Repository: ${ROOT_DIR}
- Runner: ${RUNNER_LABEL}
- Final decision: **${DECISION}**

## Commands Executed

1. \`${RUNNER_LABEL} -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics\`
2. \`${RUNNER_LABEL} -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo\`
3. \`${RUNNER_LABEL} -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction\`
4. \`${RUNNER_LABEL} -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm\`
5. \`${RUNNER_LABEL} -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough --out ${CHECKLIST_MD} --summary-json ${SUMMARY_JSON}\`

## Session Artifacts

- Checklist: \`${CHECKLIST_MD}\`
- Summary JSON: \`${SUMMARY_JSON}\`
- Step logs: \`${SESSION_DIR}/*.log\`
- Tutorial outputs (default locations):
  - \`logs/tutorial_trace/\`
  - \`logs/tutorial_manifest/\`
  - \`logs/tutorial_policy/\`
  - \`logs/tutorial_authority/\`

EOF

echo "[done] decision=${DECISION}"
echo "[done] session_dir=${SESSION_DIR}"
echo "[done] summary=${RUN_SUMMARY_MD}"

if [[ "$DECISION" != "GO" ]]; then
  echo "[warn] Decision is ${DECISION}. Inspect ${CHECKLIST_MD} for blocking gates."
fi
