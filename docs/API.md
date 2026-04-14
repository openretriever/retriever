---
title: "Runtime/Core API (Refactored)"
---

# Runtime/Core API (Refactored)

<!--
NOTE: This file was historically a large “complete API reference” for an older codebase.
The refactored runtime has a smaller public surface, so this page is now a curated map
of the current runtime/core API.
-->

This page lists the **current runtime/core** API entry points and where they live.

Canonical workflow:

`Pipeline / TemporalFlow → Pipeline.validate() → IR → (optional) Pipeline.build_execution() → execute_ir()`



---

## 1) Public authoring surface (`retriever.flow`)

Import path:

```py
from retriever.flow import (
    Flow, Pipeline, PipelineBuilder, TemporalFlow,
    io,
    Rate, Tick, Trigger, Hybrid,
    Latest, Hold, Window, Events,
    EdgeConfig,
    handle_service, call_service,
)
```

Key concepts:
- `Flow[I, O]`: user-defined node logic (`step/reset/finalize`, with `run` and `init` as compatibility aliases)
- `@io` classes: typed ports (each field is a port; use `@io` directly, not with `@dataclass`)
- `flow @ clock`: produces a `TemporalFlow` (node instance with execution config)
- `Pipeline`: explicit graph builder (recommended)
- `PipelineBuilder`: lower-level validation builder
- adapters (`Latest/Hold/Window/Events`): sampling policy for per-port buffers
- clocks (`Rate/Tick/Trigger/Hybrid`): scheduling + field sampling

Guide: `docs/guide_flow.md`.

---

## 2) Default-pipeline convenience API (Optional)

Import path:
```python
import retriever  # Global namespace
```

This is a notebook/REPL convenience layer, not the primary shared-example surface.
Use it when you want a temporary thread-local graph without naming a `Pipeline`.

- `retriever.connect(src, dst, map=None, sync=None)`: connects two `TemporalFlow`s on the thread-local default pipeline
- `retriever.default_pipeline()`: returns the current thread-local pipeline, creating one lazily if needed
- `retriever.clear_default_pipeline()`: drops the current thread-local handle
- `retriever.reset_default_pipeline()`: eagerly creates a fresh empty default pipeline
- `retriever.run(...)`: runs the thread-local default pipeline
- `retriever.step(dt=0.1)`: manually steps the default pipeline in-process
- `retriever.reset()`: resets the default pipeline state

For scripts and shared examples, prefer explicit `Pipeline(...)` plus `pipe.run(...)`,
`pipe.step(...)`, and `pipe.reset_stepper()`.

If you need a clean slate before wiring new notebook cells, prefer `retriever.reset_default_pipeline()`.
If you only want to drop the current thread-local handle and let Retriever recreate it later, use `retriever.clear_default_pipeline()`.

---

## 3) IR boundary (`retriever.ir`)

Import path:

```py
from retriever.ir import IR, ExecutionGraph
```

- `Pipeline.validate() -> IR`: converts an authored graph into backend-agnostic IR.
- `Pipeline.build_execution() -> ExecutionGraph`: creates a physical execution plan (partitioning + placement hints).

Guide: `docs/guide_execution.md`.

---

## 4) Runtime execution (`retriever.rt`)

Import path:

```py
from retriever.rt import execute_ir
```

- `execute_ir(ir_or_graph, backend=..., duration=..., blocking=...)`: runs an `IR` or an `ExecutionGraph` on a backend.

Backends:
- `multiprocessing`: (default)
- `dora`: High-performance, zero-copy (Rust)
- `in-process`: Debugging/recording (deterministic)

Architecture: `docs/architecture.md`.

---

## 5) Debugging / stepping (Pipeline surface)

Preferred entry points:

- `Pipeline.step(now=..., dt=...)` — one in-process debug step
- `Pipeline.reset_stepper()` / `Pipeline.close_stepper()`
- explicit stepper recording: `Pipeline.record(...)` / `Pipeline.replay(...)`
- `pipe.run(backend="in-process", record="file.mcap")` remains available when
  you want a wall-clock-bounded in-process run that also persists artifacts

Implementation lives in:
- `retriever/rt/stepper.py`

Guide: `docs/guides/debugging.md`.

---

## 6) Pipelines registry + plugins (`retriever.registry.pipeline`)

Import path:

```py
from retriever.registry.pipeline import (
    register_pipeline,
    list_pipelines,
    build_ir,
)
```

This enables external packages to register pipelines via entry points:
- group: `retriever.plugins`

Use `build_ir(...)` as the explicit execution-adjacent registry surface.
`run_pipeline(...)` still exists for compatibility, but it is not the primary
surface taught in these docs.

See: `docs/architecture.md` (“Registry + plugins”).
