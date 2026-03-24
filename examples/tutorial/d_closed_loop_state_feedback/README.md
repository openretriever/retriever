# D Closed-Loop State and Feedback

## Tutorials

- `01_closed_loop_env.py`
- `02_symbolic_planning.py`
- `03_operator_mode_and_authority_fsm.py`
- `04_stateful_flow_reset.py`
- `05_belief_updater.py`
- `06_stateful_composition.py`
- `07_feedback_intro.py`
- `08_event_driven_replan.py`
- `09_execution_monitoring.py`
- `10_time_triggers.py`
- `11_safety_monitoring.py`
- `12_stateful_replanning.py`
- `13_deadline_aware_mode_switch.py`
- `14_stateful_counter_basics.py`
- `15_robot_state_task_script.py`
- `16_mutable_state_pitfalls.py`
- `17_immutable_state_transitions.py`

## Advanced

- `18_advanced_time_patterns.py`

## What To Expect

- Build closed-loop and authority-aware control patterns.
- Combine state management and feedback-driven replanning.

## Run

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.02_symbolic_planning
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro --backend multiprocessing --duration 3
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.13_deadline_aware_mode_switch --steps 16 --deadline-ms 8 --heavy-ms 14 --heavy-every 4 --miss-streak-limit 1
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.18_advanced_time_patterns --steps 20 --dt 0.2
```
