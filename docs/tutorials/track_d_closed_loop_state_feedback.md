---
title: "Track D: Closed-Loop, State, and Feedback"
---

# Track D: Closed-Loop, State, and Feedback

Focus: stateful control patterns, feedback loops, authority transitions, and intervention semantics.

## Modules

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.02_symbolic_planning
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.05_belief_updater
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.06_stateful_composition
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.08_event_driven_replan
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.09_execution_monitoring
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.10_time_triggers
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.11_safety_monitoring
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.12_stateful_replanning
```

## What To Observe

- Closed-loop dynamics under different scheduler choices.
- State reset and persistence boundaries.
- Valid vs invalid authority-mode transitions.

## Expected Artifacts (P0)

- `logs/tutorial_authority/tut028_authority_log.json`
