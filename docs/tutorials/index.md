---
title: "Tutorial Tracks"
---

# Tutorial Tracks

Retriever tutorials are organized by functionality.
Each lane below points to the smallest set of runnable modules that teaches one concept clearly.

## 1. Build A First Pipeline

Start here if you are new to Retriever.

Run this first:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
```

Then:
- `examples.tutorial.a_flow_fundamentals.03_adapter_connection`
- `examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics`

Track page:
- [Track A: Flow Fundamentals](track_a_flow_fundamentals.md)

## 2. Execute A Pipeline On A Backend

Run this first:

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
```

Then:
- `examples.tutorial.b_ir_and_execution.02_ir_validation`
- `examples.tutorial.b_ir_and_execution.03_execution_build`

Track page:
- [Track B: IR and Execution](track_b_ir_and_execution.md)

## 3. Debug And Replay A Failure

Run this first:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
```

Then:
- `examples.tutorial.c_debug_and_replay.04_record_replay_perception`
- `examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill`

Track page:
- [Track C: Debug and Replay](track_c_debug_and_replay.md)

## 4. Build Stateful And Feedback Logic

Run this first:

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset
```

Then:
- `examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro`
- `examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm`

Track page:
- [Track D: Closed-Loop, State, and Feedback](track_d_closed_loop_state_feedback.md)

## 5. Learn Synchronization And Event Joins

Run this first:

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.02_synchronization
```

Then:
- `examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout`
- `examples.tutorial.e_resource_and_sync.07_data_multistream_join`

Track page:
- [Track E: Resource and Synchronization](track_e_resource_and_sync.md)

## 6. Learn Composition, Registries, And Type Boundaries

Run this first:

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.06_composable_pipelines
```

Then:
- `examples.tutorial.g_operations_interfaces.01_registry_basics`
- `examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries`

Track page:
- [Track G: Operations and Interfaces](track_g_operations_interfaces.md)

## Specialized Lanes

- Backend abstraction:
  [Track F: Policy Backends](track_f_policy_backends.md)
- Release artifacts and acceptance gates:
  [Track H: Release Readiness](track_h_release_readiness.md)

## Deep-Dives

- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)
- [Stepper, Debugger, and MCAP Replay](walkthrough_stepper_debug_and_replay.md)
- [Core Release Path](walkthrough_core_release_path.md)
- [Lecture Packs L01-L11](lectures/index.md)
