---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: canonical examples from `examples/tutorial/c_debug_and_replay/`.

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

- How to debug node-by-node with `pipe.step(...)`.
- How `.rrd` and `.mcap` artifacts fit the record/replay workflow.
- What event buffers look like when you inspect them directly.
- How to capture trace-contract evidence for release checks.
