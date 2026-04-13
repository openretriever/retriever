# Expected Output: TUT-027 Closed-Loop Policy Backend Abstraction

## Run
```bash
pixi run demo-policy-backends
```

## Expected Console Highlights
- Prints a contract line showing that backend selection happens by config.
- Prints a first-step action preview table.
- Prints one backend comparison table with rows for:
  - `openpi_pi05`
  - `lerobot`
  - `mock`
- Demonstrates the same policy interface across all backends.

## Optional Artifacts
- `logs/tutorial_policy/tut027_backend_metrics.csv`
- `logs/tutorial_policy/tut027_backend_metrics.json`

The console tables are the primary output. The CSV and JSON files are secondary evidence for later release-readiness checks.
