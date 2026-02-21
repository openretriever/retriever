# Expected Output: TUT-028 Operator Mode and Authority FSM

## Run
```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
```

## Expected Console Highlights
- `Authority Transition Log` table with timestamped transitions.
- At least one blocked invalid transition appears:
  - `autonomy -> teleop` (blocked)
- `Intervention Intervals` table appears with start/end/duration.

## Expected Artifacts
- `logs/tutorial_authority/tut028_authority_log.json`
