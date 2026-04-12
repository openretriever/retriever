---
title: "Track E: Resource and Synchronization"
---

# Track E: Resource and Synchronization

Focus: fan-in synchronization, multi-rate sampling, strict resource compatibility, and fusion constraints.

## Modules

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window
pixi run python -m examples.tutorial.e_resource_and_sync.02_synchronization
pixi run python -m examples.tutorial.e_resource_and_sync.03_multirate_robot_system
pixi run python -m examples.tutorial.e_resource_and_sync.04_strict_resource_fusion --case compatible
pixi run python -m examples.tutorial.e_resource_and_sync.05_resource_hints --print-ir
pixi run python -m examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout --steps 6 --dt 0.1
pixi run python -m examples.tutorial.e_resource_and_sync.07_data_multistream_join
```

## What To Observe

- Buffer/adaptor behavior under mixed rates.
- Synchronization tradeoffs (`Latest`, windows, event bundles).
- How resource hints affect grouping policy outcomes.
- Functional fan-in/fan-out wiring semantics with evidence artifacts.
- Explicit bridge from runtime `EventBuffer` to `retriever.types.data`.
- Deterministic event-time join behavior across multiple streams.
