---
title: "Track E: Resource and Synchronization"
---

# Track E: Resource and Synchronization

Focus: fan-in synchronization, multi-rate sampling, strict resource compatibility, and fusion constraints.

## Start Here

Run these in order:
- `02_synchronization`
- `06_functional_fanin_fanout`
- `07_data_multistream_join`

Use these later if you want more backend/resource detail:
- `01_multirate_window`
- `03_multirate_robot_system`
- `04_strict_resource_fusion`
- `05_resource_hints`

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

- Synchronization tradeoffs (`Latest`, windows, and fan-in behavior).
- Resource hints only after the synchronization story is clear.
- Explicit bridges between runtime buffer records and `retriever.types.data` event structures.
