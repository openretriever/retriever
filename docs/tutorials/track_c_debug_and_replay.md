---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: stepper-first debugging, deterministic replay, and trace diagnostics.

## Start Here

Run these in order:
- `01_debug_stepper`
- `04_record_replay_perception`
- `07_incident_response_replay_drill`

Use these when you want deeper local inspection:
- `02_debug_perception_stepper`
- `03_debug_perception_stepper_real_camera`
- `08_mcap_session_inspection`

If you want one longer story instead of small modules, start with:
- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)

## Modules

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize stdout
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
pixi run python -m examples.tutorial.c_debug_and_replay.08_mcap_session_inspection --recording logs/perception.mcap
```

## Generate An HTML View

Run this from the repository root. The snippet imports a repo-local helper from
`examples/shared/`, so `examples/` needs to be on the default Python path.

```bash
pixi run env PYTHONPATH=src:. python - <<'PY'
from support.perception_runtime import build_tutorial_perception_pipeline

path = build_tutorial_perception_pipeline(
    use_real_camera=False,
    show_window=False,
).visualize("/tmp/tutorial_perception.html")

print(path)
PY
```

## What To Observe

- In-process stepping vs backend execution.
- Recording one sensor or mock session, then replaying it deterministically.
- Using replay artifacts to isolate regressions instead of guessing at live state.
