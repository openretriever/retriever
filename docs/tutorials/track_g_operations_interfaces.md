---
title: "Track G: Operations and Interfaces"
---

# Track G: Operations and Interfaces

Focus: registries, wrapper abstractions, and operational interaction surfaces.

`03_unified_wrapper` is an alternate ergonomic surface; the rest of the track keeps explicit `Pipeline(...)` authoring primary.

Start here:
- `06_composable_pipelines` if you want reusable pipelines that can still be extended.

## Modules

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.01_registry_basics
pixi run python -m examples.tutorial.g_operations_interfaces.02_registry_ecosystem
pixi run python -m examples.tutorial.g_operations_interfaces.03_unified_wrapper
pixi run python -m examples.tutorial.g_operations_interfaces.04_peripheral
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
pixi run python -m examples.tutorial.g_operations_interfaces.06_composable_pipelines
```

## Generate an HTML View

```bash
pixi run python - <<'PY'
import importlib

mod = importlib.import_module("examples.tutorial.g_operations_interfaces.06_composable_pipelines")
path = mod.build_outer_composable_counter().visualize("/tmp/outer_composable_counter.html")
print(path)
PY
```

## What To Observe

- Registry extension patterns.
- Unified wrapper patterns and operator-facing workflows.
- Canonical spatial type imports and registry lookup parity.
- Typed boundary payloads carrying frame/time/source metadata.
- Registered pipelines used both as live graphs and as reusable flow stages.
- Nested pipeline stages rendered as boxed nodes with surfaced ports and inner-flow summaries.
