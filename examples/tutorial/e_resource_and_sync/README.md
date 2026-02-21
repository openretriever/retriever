# E Resource and Synchronization

## Tutorials

- `01_multirate_window.py`
- `02_synchronization.py`
- `03_multirate_robot_system.py`
- `04_strict_resource_fusion.py`
- `05_resource_hints.py`
- `06_functional_fanin_fanout.py`

## What To Expect

- Tune multi-rate adapters and synchronization behavior.
- Understand strict resource compatibility and fusion policy.

## Run

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window
pixi run python -m examples.tutorial.e_resource_and_sync.02_synchronization
pixi run python -m examples.tutorial.e_resource_and_sync.03_multirate_robot_system --backend dora --duration 5
pixi run python -m examples.tutorial.e_resource_and_sync.04_strict_resource_fusion --case compatible
pixi run python -m examples.tutorial.e_resource_and_sync.05_resource_hints --print-ir
pixi run python -m examples.tutorial.e_resource_and_sync.06_functional_fanin_fanout --steps 6 --dt 0.1
```
