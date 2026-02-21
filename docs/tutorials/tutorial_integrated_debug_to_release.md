---
title: "Integrated Tutorial: Debug to Release"
---

# Integrated Tutorial: Debug to Release

This is the single end-to-end tutorial for the core Retriever workflow:
- stepper debugging
- debugger usage inside stepping
- MCAP recording/replay
- backend abstraction and parity checks
- incident replay validation
- final `GO/NO-GO` release check

## What You Will Achieve
By the end, you can answer:
1. Is my flow logic correct in-process?
2. Can I reproduce behavior deterministically from recorded data?
3. Are runtime backends still within parity tolerance?
4. Does replay confirm my incident diagnosis?
5. Is release readiness `GO` or `NO-GO` with evidence?

## Prerequisites
- Run from `retriever/`.
- Use `pixi` environment.
- For MCAP recording step: real camera/source available (optional if you already have a recording).

## Phase A: Stepper-First Debugging

### A1) Step deterministic logic
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

Expected:
- deterministic step outputs
- easy breakpoint behavior

### A2) Force a controlled failure and inspect
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5 --fail-at 3
```

Expected:
- failure at the configured step
- clear location for debugging

### A3) Debug inside `Flow.run()`
Put a breakpoint in the tutorial flow implementation, then rerun A1/A2.

Purpose:
- inspect typed input/output at each step
- confirm state transitions before backend runtime complexity

## Phase B: Record and Replay with MCAP

### B1) Record real session to MCAP
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
```

Artifact:
- `logs/perception.mcap`

### B2) Replay the same session
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
```

Expected:
- stable, repeatable output
- hardware-independent debugging loop

## Phase C: Backend Contract + Parity

### C1) Verify policy backend abstraction contract (`TUT-027`)
```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

Check:
- includes `openpi_pi05`, `lerobot`, `mock`
- graph contract remains backend-invariant

Artifact:
- `logs/tutorial_policy/tut027_backend_metrics.csv`

### C2) Verify backend parity hard gate (`TUT-032`)
```bash
pixi run verify-backend-parity
```

Check:
- command exits successfully
- parity checks pass

Artifacts:
- `logs/tutorial_parity/tut032_backend_parity.json`
- `logs/tutorial_parity/tut032_backend_parity_checks.csv`

## Phase D: Incident Drill + Replay Consistency (`TUT-033`)

```bash
pixi run verify-incident-replay
```

Check:
- incident root cause candidate exists
- live/replay diagnosis signatures match

Artifacts:
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`

## Phase E: Release Readiness Decision (`TUT-029`)

```bash
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

Check:
- acceptance gates printed
- explicit final `GO` or `NO-GO`

Artifacts:
- `logs/tutorial_release_readiness/tut029_release_checklist.md`
- `logs/tutorial_release_readiness/tut029_release_summary.json`

## One-Block Core Run

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
pixi run verify-backend-parity
pixi run verify-incident-replay
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

## Fast Failure Triage
- Fails in Phase A: fix flow logic/state handling first.
- Fails in Phase B: fix recording/replay path or input assumptions.
- Fails in Phase C: fix backend contract/parity drift.
- Fails in Phase D: fix incident diagnosis/replay consistency.
- Fails in Phase E: fix evidence linkage and acceptance-gate prerequisites.

## Done Criteria
- All phases run successfully.
- Required artifacts are present.
- Release walkthrough outputs `GO` with evidence-backed checks.
