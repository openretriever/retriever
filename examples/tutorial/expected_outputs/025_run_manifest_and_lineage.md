# Expected Output: TUT-025 Run Manifest and Lineage

## Run
```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
```

## Expected Console Highlights
- Baseline and candidate manifest paths are printed.
- `Config Differences` table appears.
- `Run Summary Differences` table appears.
- Replay command is printed in generated manifests.

## Expected Artifacts
- `logs/tutorial_manifest/artifacts/tut025_baseline.mcap`
- `logs/tutorial_manifest/artifacts/tut025_candidate.mcap`
- `logs/tutorial_manifest/manifests/tut025_baseline.manifest.json`
- `logs/tutorial_manifest/manifests/tut025_candidate.manifest.json`
- `logs/tutorial_manifest/manifests/tut025_demo_compare.json`
