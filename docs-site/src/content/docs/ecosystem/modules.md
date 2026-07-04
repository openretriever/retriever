---
title: Hub Modules
---

# Hub Modules

A Retriever Hub module is a normal Python package with a declared export table. Users load the exported class, function, type, or value directly; they do not import private source paths or depend on an in-repo layout.

## Module reference format

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

## Loading semantics

- `hub.use("org/name:Export")` returns the actual exported class, function, type, or value, not a wrapper.
- `hub.use("org/name")` returns a `ModuleProxy` over the declared export table, not the raw Python module.
- Source-layout packages are supported: a module can keep implementation under `src/` as long as its manifest points to an importable package.
- Different versions of the same module are isolated by commit-scoped internal namespaces, so `@0.9.0` and `@1.0.0` do not alias each other in one process.
- Backend/runtime re-import can recover hub-loaded Flow classes from the local hub cache when a fresh process reconstructs nodes from IR.

> Current boundary: a serialized IR from hub-loaded code is not a self-contained artifact across machines by itself. The target machine must have the corresponding hub cache content available, or load the module through Hub first.

## What a module can export

Hub exports are normal Python attributes. A module may export:

- Flow classes or Flow factories
- live pipeline factories
- pipeline-flow factories for in-process hierarchical composition
- shared `@io` envelope types for Flow boundaries
- shared domain or representation types
- representation transforms and serialization helpers

Types are a first-class use case. Runtime-wide standards live in `retriever.types.*`; domain-specific applied types can live in Hub modules so they evolve with the examples or product integration that owns them.

Recommended public split:

| File | Purpose |
| --- | --- |
| `types.py` | Shared envelope types and domain types. Use `@io` only for Flow-boundary envelopes. |
| `transforms.py` | Pure representation conversion helpers. |
| `flow.py` | Flow classes and lightweight factories. |
| `pipeline.py` | Graph assembly and composition helpers. |

## First applied module

GoldenRetriever is the first applied robotics module for this release. It exports robot-facing payloads such as `WorldState`, `BeliefGraph`, `Skill`, `Plan`, and `Trajectory` through the same Hub path:

```python
from retriever import hub

WorldState = hub.use("openretriever/golden-retriever:WorldState")
```

Open [Golden Packs](/ecosystem/golden-packs/) for the concrete source-checkout proof path, then continue to the [GoldenRetriever examples site](https://retriever-space.pages.dev/) for applied perception, memory, language, simulator, and visualization lanes.
