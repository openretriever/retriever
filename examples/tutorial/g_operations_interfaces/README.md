# G Operations and Interfaces

## Tutorials

- `01_registry_basics.py`
- `02_registry_ecosystem.py`
- `03_unified_wrapper.py`
- `04_peripheral.py`
- `05_spatial_type_boundaries.py`
- `06_composable_pipelines.py`

## What To Expect

- `03_unified_wrapper.py` shows an alternate ergonomic wrapper surface. Keep explicit `Pipeline(...)` authoring as the default mental model for the rest of the tutorials.
- Use registries and wrappers to operate pipelines.
- Understand extension points and runtime control surfaces.
- See canonical spatial types used at typed flow boundaries.
- Compose registered pipelines as reusable stages and still extend live graphs.

## Run

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.01_registry_basics
pixi run python -m examples.tutorial.g_operations_interfaces.02_registry_ecosystem
pixi run python -m examples.tutorial.g_operations_interfaces.03_unified_wrapper
pixi run python -m examples.tutorial.g_operations_interfaces.04_peripheral
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
pixi run python -m examples.tutorial.g_operations_interfaces.06_composable_pipelines
```
