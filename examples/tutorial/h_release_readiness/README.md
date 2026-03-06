# H Release Readiness

## Tutorials

- `01_run_manifest_and_lineage.py`
- `02_release_readiness_walkthrough.py`
- `03_dataset_manifest_and_lerobot_mapping.py`

## What To Expect

- Generate reproducibility manifests and lineage links.
- Run acceptance-gate walkthrough and emit GO/NO-GO artifacts.
- See dataset manifests and export mappings treated as explicit release artifacts.

## Run

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```
