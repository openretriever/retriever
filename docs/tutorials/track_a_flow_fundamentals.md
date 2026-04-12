---
title: "Track A: Flow Fundamentals"
---

# Track A: Flow Fundamentals

Focus: typed flow authoring, clocks, adapters, and ergonomic graph composition.

## Start Here

Run these in order:
- `01_basic_flow`
- `03_adapter_connection`
- `05_pipeline_ergonomics`

Come back to these after the basics are clear:
- `02_clock_types`
- `04_full_pipeline`

## Modules

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.a_flow_fundamentals.04_full_pipeline
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics
```

## What To Observe

- How `@io` typing catches wiring mistakes early.
- How adapters change sampling and trigger behavior.
- How explicit `Pipeline(...)` authoring and ergonomic helpers map to the same graph.
