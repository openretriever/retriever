# G Operations and Interfaces

## Start Here

Run these first:
- `06_composable_pipelines.py`
- `05_spatial_type_boundaries.py`
- `07_language_grounding_composition.py`
- `01_registry_basics.py`

Use these later:
- `02_registry_ecosystem.py`
- `03_unified_wrapper.py` (requires your own `gymnasium` + `torch` env)
- `04_peripheral.py`

## What To Expect

- `03_unified_wrapper.py` is an alternate ergonomic surface. Keep explicit `Pipeline(...)` authoring as the default mental model.
- `03_unified_wrapper.py` is illustrative, not part of the default Pixi tutorial surface.
- Use registries and reusable pipelines as operational surfaces.
- See spatial type boundaries where frame/time/source metadata matters.
- See language + perception primitives compose without a custom wrapper dataclass.
- `07_language_grounding_composition.py` shows buffered grounding over the latest detection snapshot, not a model-specific request/response envelope.
