---
title: "Track H: Release Readiness"
---

# Track H: Release Readiness

Focus: manifest lineage, acceptance-gate evidence, and go/no-go decisions.

## Modules

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

## What To Observe

- Reproducibility contracts between runs.
- Evidence mapping to acceptance gates.
- Deterministic release decision summary (`GO` or `NO-GO`).

## Expected Artifacts (P0)

- `logs/tutorial_manifest/manifests/*.manifest.json`
- `logs/tutorial_release_readiness/tut029_release_checklist.md`
- `logs/tutorial_release_readiness/tut029_release_summary.json`
