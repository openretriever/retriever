---
title: "Track E: Resource and Synchronization"
---

# Track E: Resource and Synchronization

Focus: canonical examples from `examples/tutorial/e_resource_and_sync/`.

## Modules

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window
pixi run python -m examples.tutorial.e_resource_and_sync.02_synchronization
pixi run python -m examples.tutorial.e_resource_and_sync.03_multirate_robot_system
pixi run python -m examples.tutorial.e_resource_and_sync.04_strict_resource_fusion
pixi run python -m examples.tutorial.e_resource_and_sync.05_resource_hints
pixi run python -m examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout
```

## What To Observe

- How multi-rate graphs stay coherent with explicit sync policies.
- What strict synchronization vs windowed aggregation changes downstream.
- Where resource hints belong and how they stay separate from logic.
- How fan-in / fan-out composition behaves under nontrivial timing.
