# Expected Output: TUT-027 Closed-Loop Policy Backend Abstraction

## Run
```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

## Expected Console Highlights
- Prints backend-invariant graph fingerprint.
- Prints timing + chunk-behavior table with rows for:
  - `openpi_pi05`
  - `lerobot`
  - `mock`
- Demonstrates backend switch without graph changes.

## Expected Artifacts
- `logs/tutorial_policy/tut027_backend_metrics.csv`
- `logs/tutorial_policy/tut027_backend_metrics.json`
