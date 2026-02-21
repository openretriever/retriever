---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: stepper-first debugging, deterministic replay, and trace diagnostics.

## Modules

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
```

## What To Observe

- In-process stepper behavior vs backend run behavior.
- Replay workflows that isolate regressions.
- Edge latency + queue depth bottleneck identification.

## Expected Artifacts (P0)

- `logs/tutorial_trace/tut024_trace_envelopes.jsonl`
- `logs/tutorial_trace/tut024_trace_report.json`
