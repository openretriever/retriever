---
title: "Hub Packs and Modules"
---

# Hub Packs and Modules

A Retriever Hub pack or module is a normal Python package with a declared export table. Users import the exported class, function, type, or value directly.

## Hub Reference Format

```text
{org}/{module-name}[:{attribute}][@{version}]
```

Examples:

```python
from retriever import hub

module = hub.use("your-org/lidar-slam")
LidarSlamFlow = hub.use("your-org/lidar-slam:LidarSlamFlow")
BuildSlamPipeline = hub.use("your-org/lidar-slam:BuildSlamPipeline@0.1.0")
```

## Loading Semantics

- `hub.use("org/name:Export")` returns the actual exported class/function/value, not a wrapper.
- `hub.use("org/name")` returns a `ModuleProxy` over the declared export table, not the raw Python module.
- Different versions of the same module are isolated by commit-scoped internal namespaces, so `@0.9.0` and `@1.0.0` do not alias each other in one process.
- Backend/runtime re-import can recover hub-loaded Flow classes from the local hub cache when a fresh process reconstructs nodes from IR.

!!! note "Current boundary"
    A serialized IR from hub-loaded code is not a self-contained artifact across machines by itself. The target machine must have the corresponding hub cache content available, or load the module through Hub first.

## What A Module Can Export

Hub exports are normal Python attributes. A module may export:

- Flow classes or Flow factories
- live pipeline factories
- pipeline-flow factories for in-process hierarchical composition
- shared `@io` envelope types for Flow boundaries
- shared domain / representation types
- representation transforms and serialization helpers

Recommended public split:

| File | Purpose |
| --- | --- |
| `types.py` | Shared envelope types and domain types. Use `@io` only for Flow-boundary envelopes. |
| `transforms.py` | Pure representation conversion helpers. |
| `flow.py` | Flow classes and lightweight factories. |
| `pipeline.py` | Graph assembly and composition helpers. |

## Examples In This Repo

- `examples/hub/hello-world.py`: whole-module import through `ModuleProxy`, then use exported Flow/type symbols.
- `examples/hub/hello-world-explicit.py`: explicit `hub.use("org/name:Export")` imports against a live module.
- `examples/hub/detection-window.py`: import Flows/types from Hub and compose them into a local pipeline.
- `examples/hub/_composable_pipeline_template.py`: template for imported live pipelines, pipeline-flow wrappers, and shared transforms.
