---
title: "Track A: Flow Fundamentals"
---

# Track A: Flow Fundamentals

Focus: canonical examples from `examples/tutorial/a_flow_fundamentals/`.

## Modules

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.a_flow_fundamentals.04_full_pipeline
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics
```

## What To Observe

- How typed `@io` envelopes map to `Flow[I, O]` signatures.
- When to use `Rate`, `Tick`, and `Trigger` clocks.
- How adapter choices change sampling semantics at the pipeline boundary.
- Why `pipe.step(...)` is the fastest way to understand a new graph.
