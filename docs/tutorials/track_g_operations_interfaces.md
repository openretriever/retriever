---
title: "Track G: Operations and Interfaces"
---

# Track G: Operations and Interfaces

Focus: registries, reusable pipelines, typed boundaries, and operational control surfaces.

`03_unified_wrapper` is an alternate ergonomic surface. Keep explicit `Pipeline(...)` authoring as the default mental model, and teach direct primitive composition first.

Treat `05_spatial_type_boundaries` and `07_language_grounding_composition` as the canonical primitive-first lessons. `06_composable_pipelines`, `01_registry_basics`, `02_registry_ecosystem`, and `04_peripheral` are later operational examples and still use more explicit wrappers, surfaced selectors, or registry plumbing.

## Start Here

Run these in order:
- `05_spatial_type_boundaries`
- `07_language_grounding_composition`

Use these later:
- `06_composable_pipelines`
- `01_registry_basics`
- `02_registry_ecosystem`
- `03_unified_wrapper` (optional external env: `gymnasium` + `torch`)
- `04_peripheral`

## Modules

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
pixi run python -m examples.tutorial.g_operations_interfaces.07_language_grounding_composition
pixi run python -m examples.tutorial.g_operations_interfaces.06_composable_pipelines
pixi run python -m examples.tutorial.g_operations_interfaces.01_registry_basics
pixi run python -m examples.tutorial.g_operations_interfaces.02_registry_ecosystem
pixi run python -m examples.tutorial.g_operations_interfaces.04_peripheral
```

`03_unified_wrapper` is intentionally not in the default Pixi tutorial surface. It needs `gymnasium` and `torch` in your own environment.

## Generate An HTML View

```bash
pixi run python - <<'PY'
import importlib

mod = importlib.import_module("examples.tutorial.g_operations_interfaces.06_composable_pipelines")
path = mod.build_outer_composable_counter().visualize("outer_composable_counter.html")
print(path)
PY
```

## What To Observe

- How registries expose reusable runtime surfaces.
- How composed pipelines can still be inspected and extended as live graphs.
- How typed boundary payloads carry frame/time/source metadata cleanly.
- How language and perception primitives compose directly in one Flow signature.
- How a text-triggered grounding flow can keep the latest scene snapshot explicitly buffered.
