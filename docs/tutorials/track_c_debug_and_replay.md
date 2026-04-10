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
pixi run demo-record-replay
pixi run python -m examples.tutorial.c_debug_and_replay.05_buffer_engine_demo
pixi run demo-trace-contract
pixi run demo-incident-replay
pixi run demo-mcap-session-inspection
```

## What To Observe

- How to debug node-by-node with `pipe.step(...)`.
- How `.rrd` and `.mcap` artifacts fit the record/replay workflow.
- How to detect a latency incident and confirm the same diagnosis on replay.
- How to inspect a recorded MCAP session as a compact step/table artifact.
