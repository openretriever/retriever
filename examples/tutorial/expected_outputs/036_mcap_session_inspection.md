# Expected Output: TUT-036 MCAP Session Inspection

## Run
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.08_mcap_session_inspection --recording logs/perception.mcap
```

## Expected Console Highlights
- `Session Summary` table appears with step and duration metrics.
- `Output Stream Coverage` table appears with per-node output counts.
- `Step Preview` table appears with executed/output counts per step.

## Expected Artifacts
- `logs/tutorial_mcap/tut036_mcap_session_summary.json`
- `logs/tutorial_mcap/tut036_mcap_step_table.jsonl`

