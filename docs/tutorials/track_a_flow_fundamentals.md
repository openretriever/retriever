---
title: "Track A: Flow Fundamentals"
---

# Track A: Flow Fundamentals

Focus: typed flow authoring, clocks, adapters, and ergonomic graph composition.

## Modules

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.a_flow_fundamentals.04_full_pipeline
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics
```

## What To Observe

- How `@flow_io` typing catches wiring mistakes early.
- Clock choice impact (`Rate`, `Trigger`, and adapter semantics).
- Equivalent pipeline authoring styles and tradeoffs.
