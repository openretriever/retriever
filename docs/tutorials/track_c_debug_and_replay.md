---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: stepper-first debugging, deterministic replay, and trace diagnostics.

Start here:
- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)
- [Walkthrough: Stepper, Debugger, and MCAP Replay](walkthrough_stepper_debug_and_replay.md)

## Modules

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run demo-webcam-stepper
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
pixi run demo-webcam-replay-mcap
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
pixi run python -m examples.tutorial.c_debug_and_replay.08_mcap_session_inspection --recording logs/perception.mcap
```

Use `stdout` first. On machines without a webcam, the tutorial source falls back to mock frames so the artifact path still works.

## What To Observe

- In-process stepper behavior vs backend run behavior.
- Replay workflows that isolate regressions.
- Edge latency + queue depth bottleneck identification.
- Incident triage with replay signature consistency checks.
- MCAP session inspection outputs for notebook-ready analysis.

## Core Feature Flow

1. Step pipeline in-process (`01_debug_stepper`) to debug logic with breakpoints.
2. Record one live-or-mock sensor session to `.rrd`, with a mirrored `.mcap` artifact for interchange (`demo-webcam-record`).
3. Replay the same captured session from `.rrd` or `.mcap` (`demo-webcam-replay-rrd` / `demo-webcam-replay-mcap`) for deterministic debugging.
4. Run incident drill (`07_incident_response_replay_drill`) and verify diagnosis consistency.

## Expected Artifacts (P0/P1)

- `logs/tutorial_trace/tut024_trace_envelopes.jsonl`
- `logs/tutorial_trace/tut024_trace_report.json`
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`
- `logs/tutorial_mcap/tut036_mcap_session_summary.json`
- `logs/tutorial_mcap/tut036_mcap_step_table.jsonl`

Expected output reference:
- `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
- `examples/tutorial/expected_outputs/033_incident_response_replay_drill.md`
- `examples/tutorial/expected_outputs/036_mcap_session_inspection.md`
