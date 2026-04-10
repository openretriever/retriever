# C Debug and Replay

## Tutorials

- `01_debug_stepper.py`
- `02_debug_perception_stepper.py`
- `03_debug_perception_stepper_real_camera.py`
- `04_record_replay_perception.py`
- `05_buffer_engine_demo.py`
- `06_trace_contract_basics.py`
- `07_incident_response_replay_drill.py`
- `08_mcap_session_inspection.py`

## What To Expect

- Use stepper workflows to isolate failures.
- Record one session to `.rrd` plus a mirrored `.mcap`, then replay either artifact.
- Run an incident-response replay drill and verify diagnosis consistency.
- Inspect an MCAP session as a compact step/table artifact for later analysis. Use the module form with `--recording ...` only when you want a non-default file.

## Run

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run demo-record-replay
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run demo-trace-contract
pixi run demo-incident-replay
pixi run demo-mcap-session-inspection
```
