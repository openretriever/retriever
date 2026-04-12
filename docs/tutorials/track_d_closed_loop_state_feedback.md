---
title: "Track D: Closed-Loop, State, and Feedback"
---

# Track D: Closed-Loop, State, and Feedback

Focus: stateful control patterns, feedback loops, authority transitions, and intervention semantics.

## Start Here

Run these in order:
- `04_stateful_flow_reset`
- `07_feedback_intro`
- `03_operator_mode_and_authority_fsm`

Use these later, once the runtime/state story is clear:
- `05_belief_updater`
- `12_stateful_replanning`
- `13_deadline_aware_mode_switch`

These are deeper or more domain-specific and should not be your first stop:
- `01_closed_loop_env`
- `02_symbolic_planning`
- `18_advanced_time_patterns`

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
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.13_deadline_aware_mode_switch --steps 16 --deadline-ms 8 --heavy-ms 14 --heavy-every 4 --miss-streak-limit 1
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.14_stateful_counter_basics --steps 6 --dt 0.1
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.15_robot_state_task_script --steps 8 --dt 0.1
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.16_mutable_state_pitfalls
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.17_immutable_state_transitions
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.18_advanced_time_patterns --steps 20 --dt 0.2
```

## What To Observe

- How state enters a flow and how `reset()` defines state boundaries.
- How feedback changes control behavior over time.
- How authority and intervention markers fit into the same typed runtime model.
