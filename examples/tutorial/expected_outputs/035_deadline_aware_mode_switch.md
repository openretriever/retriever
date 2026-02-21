# Expected Output: TUT-035 Deadline-Aware Mode Switch

## Run
```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.13_deadline_aware_mode_switch --steps 16 --deadline-ms 8 --heavy-ms 14 --heavy-every 4 --miss-streak-limit 1
```

## Expected Console Highlights
- Repeated `[deadline]` lines show per-step `mode` and chosen `action`.
- `Deadline Timeline` table appears with `miss_streak`, `miss_total`, and mode transitions.
- At least one `NOMINAL -> SAFE` and one `SAFE -> NOMINAL` transition appears.

## Expected Artifact
- `logs/tutorial_deadline/tut035_deadline_mode_switch.json`

