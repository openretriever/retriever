---
title: "Tutorials"
---

# Tutorials

Use this page if you want the shortest learning path.

The full tutorial front door lives at [../tutorials/index.md](../tutorials/index.md).
That page groups examples by functionality. This page keeps only the minimum path.

Use the minimal path to learn the core runtime loop. Use Track G later for operational surfaces like registries and composable pipelines.

## Minimal Path

Run these in order:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
```

What this path covers:
- typed `Flow` and `Pipeline` authoring
- adapters and execution surfaces
- stepper debugging
- `.rrd` / `.mcap` recording and replay
- primitive-first typed boundaries

## Choose By Functionality

- Build a first pipeline:
  [../tutorials/track_a_flow_fundamentals.md](../tutorials/track_a_flow_fundamentals.md)
- Run and inspect a backend:
  [../tutorials/track_b_ir_and_execution.md](../tutorials/track_b_ir_and_execution.md)
- Debug and replay failures:
  [../tutorials/track_c_debug_and_replay.md](../tutorials/track_c_debug_and_replay.md)
- Learn state and feedback patterns:
  [../tutorials/track_d_closed_loop_state_feedback.md](../tutorials/track_d_closed_loop_state_feedback.md)
- Learn synchronization and event joins:
  [../tutorials/track_e_resource_and_sync.md](../tutorials/track_e_resource_and_sync.md)
- Learn composition, registries, and type boundaries:
  [../tutorials/track_g_operations_interfaces.md](../tutorials/track_g_operations_interfaces.md)
- Learn release artifacts and acceptance gates:
  [../tutorials/track_h_release_readiness.md](../tutorials/track_h_release_readiness.md)

## Deep-Dives

- Integrated walkthrough:
  [../tutorials/tutorial_integrated_debug_to_release.md](../tutorials/tutorial_integrated_debug_to_release.md)
- Lecture pack:
  [../tutorials/lectures/index.md](../tutorials/lectures/index.md)
