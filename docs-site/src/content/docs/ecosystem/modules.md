---
title: Hub Packs and Modules
---

# Hub Packs and Modules

A Retriever Hub pack or module is a normal Python package with a declared export table. Users load the exported class, function, type, or value directly; they do not import private source paths or depend on an in-repo layout.

## Hub reference format

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
- `hub.use("org/name")` returns a proxy over the declared export table, not the raw Python module.
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

Types are a first-class use case. Runtime-wide standards live in `retriever.types.*`; domain-specific applied types can live in Hub packs so they evolve with the examples or product integration that owns them.

Recommended public split:

| File | Purpose |
| --- | --- |
| `types.py` | Shared envelope types and domain types. Use `@io` only for Flow-boundary envelopes. |
| `transforms.py` | Pure representation conversion helpers. |
| `flow.py` | Flow classes and lightweight factories. |
| `pipeline.py` | Graph assembly and composition helpers. |

## Applied reference catalog

GoldenRetriever is the reference catalog for this release. Its current manifest-declared Hub surface exports robot-facing payloads such as `WorldState`, `BeliefGraph`, `Skill`, `Plan`, and `Trajectory` through the same ref shape:

```python
from retriever import hub

WorldState = hub.use("openretriever/golden-retriever:WorldState")
```

Open [Golden Examples](/ecosystem/golden-packs/) for the local manifest proof path, then continue to [Golden examples](https://retriever-space.pages.dev/examples/) for applied perception, memory, language, simulator, visualization, and robot type-pack lanes.
