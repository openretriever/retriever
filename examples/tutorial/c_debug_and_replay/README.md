# C Debug and Replay

Walkthrough first:
- `docs/tutorials/tutorial_integrated_debug_to_release.md`

## Tutorials

- `01_debug_stepper.py`
- `02_debug_perception_stepper.py`
- `03_debug_perception_stepper_real_camera.py`
- `04_record_replay_perception.py`
- `05_buffer_engine_demo.py`
- `06_trace_contract_basics.py`
- `07_incident_response_replay_drill.py`

## What To Expect

- Use stepper workflows to isolate failures.
- Record/replay traces and identify bottlenecks.
- Run incident-response drills and verify replay diagnosis consistency.

## Run

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
```

Expected output reference:
- `examples/tutorial/expected_outputs/033_incident_response_replay_drill.md`
