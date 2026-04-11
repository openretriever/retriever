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
    io, flow_io, is_flow_io,
    Rate, Tick, Trigger, Hybrid,
    Latest, Hold, Window, Events,
    handle_service, call_service,
)
```

Key concepts:
- `Flow[I, O]`: user-defined node logic (`step/reset/finalize`)
- `@io` classes: typed ports (each field is a port)
- `flow @ clock`: produces a `TemporalFlow` (node instance with execution config)
- `Pipeline`: explicit graph builder (recommended)
- `PipelineBuilder`: lower-level validation builder
- adapters (`Latest/Hold/Window/Events`): sampling policy for per-port buffers
- clocks (`Rate/Tick/Trigger/Hybrid`): scheduling + field sampling

Guide: `docs/guide_flow.md`.

---

## 2) Default-pipeline convenience API

Import path:
```python
import retriever  # Global namespace
from retriever.lib import Wrapper
```

- **When to use this**: REPL/notebook experiments or very small scripts where an implicit default pipeline is acceptable. For library code and checked-in examples, prefer an explicit `Pipeline` and `pipe.run(...)`.

- **Pipeline Construction**:
    - `retriever.connect(src, dst, map=None, sync=None)`: Connects two `TemporalFlow`s and records the edge on the implicit default pipeline.
    - `retriever.lib.Wrapper(obj)`: Factory creating `Flow` instance from `torch.nn.Module` or `gym.Env` factory.

- **Execution**:
    - `retriever.run(backend="multiprocessing", duration=10, record="log.mcap")`: Executes the implicit default pipeline (records if `record=` is set).
    - `retriever.step(dt=0.1)`: Manually steps the default pipeline (in-process debugging).
    - `retriever.reset()`: Resets the default pipeline state.

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
- `in-process` requires a live `Pipeline` instance; it is not a saved-IR loader.

Architecture: `docs/architecture.md`.

---

## 5) Debugging / stepping (Pipeline surface)

Preferred entry points:

- `Pipeline.step(now=..., dt=...)` — one in-process debug step
- `Pipeline.reset_stepper()` / `Pipeline.close_stepper()`
- unified recording: `pipe.run(record="file.rrd")` or `pipe.run(record=RecordConfig(path="file.rrd", mirrors=("file.mcap",)))`
- session recording/replay: `Pipeline.record(...)`, `Pipeline.view(...)` (local Rerun viewer when available), and `Pipeline.replay(...)`
- legacy recording aliases remain available for older code, but new examples should prefer `Pipeline.record(handle, path, ...)`

Implementation lives in:
- `retriever/rt/stepper.py`

Guide: `docs/guides/debugging.md`.

---

## 6) Pipelines registry + plugins (`retriever.pipeline_registry`)

Import path:

```py
from retriever.pipeline_registry import (
    register_pipeline,
    list_pipelines,
    build_ir,
    run_pipeline,
)
```

This enables external packages to register pipelines via entry points:
- group: `retriever.plugins`

See: `docs/architecture.md` (“Registry + plugins”).
