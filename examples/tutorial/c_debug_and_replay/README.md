# C Debug and Replay

## Tutorials

- `01_debug_stepper.py`
- `02_debug_perception_stepper.py`
- `03_debug_perception_stepper_real_camera.py`
- `04_record_replay_perception.py`
- `05_buffer_engine_demo.py`
- `06_trace_contract_basics.py`

## What To Expect

- Use stepper workflows to isolate failures.
- Record one session to `.rrd` plus a mirrored `.mcap`, then replay either artifact.
- Identify bottlenecks and verify replay behavior without live hardware.

## Run

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
```
