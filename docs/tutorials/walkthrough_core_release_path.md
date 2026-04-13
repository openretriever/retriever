---
title: "Walkthrough: Core Release Path"
---

# Walkthrough: Core Release Path

This is the shortest operator path to release confidence.

## Goal
Confirm four things, in order:
1. policy backend evidence is available for representative policy pipelines
2. backend behavior stays within parity tolerance
3. incident diagnosis is replay-consistent
4. acceptance-gate summary gives a defensible `GO`/`NO-GO`

## Core Command Chain

Run from `retriever/`:

```bash
pixi run demo-policy-backends
pixi run verify-backend-parity
pixi run verify-incident-replay
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

Task-oriented equivalent:

```bash
pixi run demo-policy-backends
pixi run verify-backend-parity
pixi run verify-incident-replay
pixi run demo-release-readiness
```

## What Each Step Proves

### Step 1: Policy Backend Evidence (`TUT-027`, specialized)
Command:
```bash
pixi run demo-policy-backends
```

Proves:
- backends `openpi_pi05|lerobot|mock` are selected by config/interface
- the same policy example and `infer(example)->actions` contract run across all three backends

Artifact:
- `logs/tutorial_policy/tut027_backend_metrics.csv`

This step is specialized evidence for policy-driven pipelines, not a universal prerequisite for every Retriever deployment.

### Step 2: Backend Parity Gate (`TUT-032`)
Command:
```bash
pixi run verify-backend-parity
```

Proves:
- multiprocessing and dora both run
- parity checks pass under configured tolerances

Artifacts:
- `logs/tutorial_parity/tut032_backend_parity.json`
- `logs/tutorial_parity/tut032_backend_parity_checks.csv`

### Step 3: Incident Replay Gate (`TUT-033`)
Command:
```bash
pixi run verify-incident-replay
```

Proves:
- incident root-cause candidate is detected
- replay diagnosis signature matches live diagnosis

Artifacts:
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`

### Step 4: Release Walkthrough (`TUT-029`)
Command:
```bash
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

Proves:
- evidence maps to acceptance gates
- final decision is explicit (`GO` or `NO-GO`) with reasons

Artifacts:
- `logs/tutorial_release_readiness/tut029_release_checklist.md`
- `logs/tutorial_release_readiness/tut029_release_summary.json`

## Decision Rule
- `GO`: all gate checks pass and no required artifact is missing.
- `NO-GO`: any parity/incident/acceptance gate check fails.

## Fast Triage If It Fails
- fails at Step 2: fix backend runtime/parity contract first
- fails at Step 3: fix replay determinism or diagnosis logic
- fails at Step 4: fix missing evidence/docs linkage and re-run
