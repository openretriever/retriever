# H Release Readiness

## Tutorials

- `01_run_manifest_and_lineage.py`
- `02_release_readiness_walkthrough.py`

## What To Expect

- Generate reproducibility manifests and lineage links.
- Run acceptance-gate walkthrough and emit GO/NO-GO artifacts.

## Run

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

The walkthrough uses the bundled public reference pack by default. You can
override it with `--reference-root` if you want to point at a different release
reference bundle.
