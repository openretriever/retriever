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
from retriever.lib import Wrapper
```

- **Pipeline Construction**:
    - `retriever.connect(src, dst, map=None, sync=None)`: Connects two `TemporalFlow`s. Implicitly creates or uses a default pipeline.
    - `retriever.lib.Wrapper(obj)`: Factory creating `Flow` instance from `torch.nn.Module` or `gym.Env` factory.

- **Execution**:
    - `retriever.run(...)`: Executes the thread-local default-pipeline convenience surface.
    - `retriever.step(dt=0.1)`: Manually steps the default pipeline (in-process debugging).
    - `retriever.reset()`: Resets the default pipeline state.

Use this surface for notebooks and lightweight experiments. For scripts and shared
examples, prefer `pipe.run(...)`, `pipe.step(...)`, and `pipe.reset_stepper()`.

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
- unified recording: `pipe.run(record="file.mcap")` (preferred)
- explicit stepper recording: `Pipeline.record(...)` / `Pipeline.replay(...)`

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
    run_pipeline,
)
```

This enables external packages to register pipelines via entry points:
- group: `retriever.plugins`

See: `docs/architecture.md` (“Registry + plugins”).
