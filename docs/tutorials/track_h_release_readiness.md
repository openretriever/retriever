---
title: "Track H: Release Readiness"
---

# Track H: Release Readiness

Focus: manifest lineage, acceptance-gate evidence, and go/no-go decisions.

Start here for semantic flow:
- [Core Release Path Walkthrough](walkthrough_core_release_path.md)

## Modules

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

## What To Observe

- Reproducibility contracts between runs.
- Evidence mapping to acceptance gates.
- Deterministic release decision summary (`GO` or `NO-GO`).

## Core Feature Flow

1. Confirm policy backend abstraction contract (`TUT-027`).
2. Pass backend parity hard gate (`TUT-032`).
3. Pass incident replay hard gate (`TUT-033`).
4. Emit `GO/NO-GO` with evidence mapping (`TUT-029`).

## Expected Artifacts (P0)

- `logs/tutorial_manifest/manifests/*.manifest.json`
- `logs/tutorial_release_readiness/tut029_release_checklist.md`
- `logs/tutorial_release_readiness/tut029_release_summary.json`
