---
title: "Track H: Release Readiness"
---

# Track H: Release Readiness

Focus: manifest lineage, acceptance-gate evidence, and go/no-go decisions.

Start here:
- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)

## Modules

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```

## What To Observe

- Reproducibility contracts between runs.
- Evidence mapping to acceptance gates.
- Deterministic release decision summary (`GO` or `NO-GO`).
- Dataset manifests and export contracts as explicit release artifacts.
- LeRobot-compatible mapping without changing core runtime transport.
