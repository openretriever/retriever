---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: stepper-first debugging, deterministic replay, and trace diagnostics.

Start here:
- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)
- `02_debug_perception_stepper` for breakpoint-friendly local stepping.

## Modules

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize cv2
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
pixi run python -m examples.tutorial.c_debug_and_replay.08_mcap_session_inspection --recording logs/perception.mcap
```

## Generate an HTML View

Before stepping or replaying the perception pipeline, generate a static HTML view:

```bash
pixi run env PYTHONPATH=src python - <<'PY'
from retriever.tutorials.perception import build_tutorial_perception_pipeline

path = build_tutorial_perception_pipeline(
    use_real_camera=False,
    show_window=False,
).visualize("/tmp/tutorial_perception.html")

print(path)
PY
```

## What To Observe

- In-process stepper behavior vs backend run behavior.
- Replay workflows that isolate regressions.
- Edge latency + queue depth bottleneck identification.
- Incident triage with replay signature consistency checks.
- MCAP session inspection outputs for notebook-ready analysis.

## Core Feature Flow

1. Step pipeline in-process (`01_debug_stepper`) to debug logic with breakpoints.
2. Record one real sensor session to `.rrd`, with a mirrored `.mcap` artifact for interchange (`04_record_replay_perception record`).
3. Replay the same captured session from `.rrd` or `.mcap` (`04_record_replay_perception replay`) for deterministic debugging.
4. Run incident drill (`07_incident_response_replay_drill`) and verify diagnosis consistency.

## Expected Artifacts

- `logs/perception.rrd`
- `logs/perception.mcap`
- `logs/tutorial_trace/tut024_trace_envelopes.jsonl`
- `logs/tutorial_trace/tut024_trace_report.json`
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`
- `logs/tutorial_mcap/tut036_mcap_session_summary.json`
- `logs/tutorial_mcap/tut036_mcap_step_table.jsonl`

Expected output references:
- `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
- `examples/tutorial/expected_outputs/033_incident_response_replay_drill.md`
- `examples/tutorial/expected_outputs/036_mcap_session_inspection.md`
