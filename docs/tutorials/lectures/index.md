---
title: "Lecture Pack L01-L06"
---

# Lecture Pack L01-L06

These are runnable mini-lecture notes for foundational Retriever concepts.

## Lectures

- [L01 Retriever Mental Model](l01_retriever_mental_model.md)
- [L02 Typed IO and Adapter Semantics](l02_typed_io_and_adapter_semantics.md)
- [L03 Clocking Model and Multirate Intuition](l03_clocking_and_multirate_intuition.md)
- [L04 Building and Validating IR](l04_building_and_validating_ir.md)
- [L05 Runtime Backends and Execution Lifecycle](l05_runtime_backends_and_execution_lifecycle.md)
- [L06 Pipeline Ergonomics and Composition Antipatterns](l06_pipeline_ergonomics_and_composition_antipatterns.md)

## Baseline Run Pack

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
