# Expected Output: TUT-034 Functional Fan-In and Fan-Out

## Run
```bash
pixi run python -m examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout --steps 6 --dt 0.1
```

## Expected Console Highlights
- `Fan-Out Summary` table appears with two branch columns (`high_branch`, `low_branch`).
- `Fan-In Summary (Window Mean)` appears with mean samples near `20.00`.
- Both `[fan-out]` and `[fan-in]` prefixed log lines are printed.

## Expected Artifact
- `logs/tutorial_wiring/tut034_functional_fanin_fanout.json`

