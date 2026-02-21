# Expected Output: TUT-032 Backend Parity Benchmark

## Run
```bash
pixi run python -m examples.tutorial.b_ir_and_execution.09_backend_parity_benchmark
```

## Expected Console Highlights
- Prints backend-invariant graph fingerprint.
- Prints backend metrics table with rows for:
  - `multiprocessing`
  - `dora`
- Prints parity checks table with pass/fail per check.
- Prints final `PASS` or `FAIL` parity result.

## Expected Artifacts
- `logs/tutorial_parity/tut032_backend_parity.json`
- `logs/tutorial_parity/tut032_backend_parity.csv`
- `logs/tutorial_parity/tut032_backend_parity_checks.csv`
- `logs/tutorial_parity/tut032_mp_rows.jsonl`
- `logs/tutorial_parity/tut032_dora_rows.jsonl`

## Pass Criteria
- Both backends run successfully (hard gate).
- Prefix output signature matches between backends.
- Count ratio drift and latency deltas are within configured tolerances.
