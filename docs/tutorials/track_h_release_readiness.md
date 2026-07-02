---
title: "Track H: Evidence and Manifests"
---

# Track H: Evidence and Manifests

Focus: manifest lineage, acceptance-gate evidence, and go/no-go decisions.

This track is for run manifests, dataset lineage, and acceptance evidence after the runtime basics are already familiar.

## Start Here

Run these in order:
- `01_run_manifest_and_lineage demo`
- `02_release_readiness_walkthrough`
- `03_dataset_manifest_and_lerobot_mapping`

If you want one longer narrative first:
- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)

## Modules

```bash
pixi run demo-manifest-lineage
pixi run demo-release-readiness
pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```

## What To Observe

- Reproducibility contracts between runs.
- Evidence mapping to acceptance gates.
- Dataset manifests and export mappings as explicit release artifacts.
