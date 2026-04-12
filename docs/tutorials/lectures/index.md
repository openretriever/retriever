---
title: "Lecture Packs L01-L11"
---

# Lecture Packs L01-L11

These are runnable mini-lecture notes for Retriever foundations and reliability workflows.

## Group L1 Foundations (L01-L06)

- [L01 Retriever Mental Model](l01_retriever_mental_model.md)
- [L02 Typed IO and Adapter Semantics](l02_typed_io_and_adapter_semantics.md)
- [L03 Clocking Model and Multirate Intuition](l03_clocking_and_multirate_intuition.md)
- [L04 Building and Validating IR](l04_building_and_validating_ir.md)
- [L05 Runtime Backends and Execution Lifecycle](l05_runtime_backends_and_execution_lifecycle.md)
- [L06 Pipeline Ergonomics and Composition Antipatterns](l06_pipeline_ergonomics_and_composition_antipatterns.md)

## Group L2 Debug and Reliability (L07-L11)

- [L07 Stepper-First Debugging](l07_stepper_first_debugging.md)
- [L08 Record/Replay Workflows and Determinism](l08_record_replay_and_determinism.md)
- [L09 Synchronization and Fan-In/Fan-Out Behavior](l09_synchronization_and_fan_in_fan_out.md)
- [L10 Stateful Flows and Reset Contracts](l10_stateful_flows_and_reset_contracts.md)
- [L11 Monitoring and Feedback Loops](l11_monitoring_and_feedback_loops.md)

## Baseline Run Pack (L1)

Run from repository root:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
pixi run python -m examples.tutorial.b_ir_and_execution.03_execution_build
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution --backend multiprocessing --duration 2
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode context --exec step --steps 3
```

## Baseline Run Pack (L2)

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 4
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 4 --visualize stdout
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window --backend multiprocessing --duration 2
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset --steps 5 --dt 0.1
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro --backend multiprocessing --duration 2
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.09_execution_monitoring --backend multiprocessing --duration 2
```
