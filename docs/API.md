---
title: "Runtime/Core API (Refactored)"
---

# Runtime/Core API (Refactored)

<!--
NOTE: This file was historically a large “complete API reference” for an older codebase.
The refactored runtime has a smaller public surface, so this page is now a curated map
of the current runtime/core API.
-->

# Runtime/Core API (Refactored)

This page lists the **current runtime/core** API entry points and where they live.

Canonical workflow:

`Pipeline (or FlowContext) → validate() → IRStruct → (optional) build_execution() → execute_ir()`



---

## 1) Public authoring surface (`retriever.flow`)

Import path:

```py
from retriever.flow import (
    Flow, Pipeline, FlowContext, FlowHandle,
    flow_io, is_flow_io,
    Rate, Tick, Trigger, Hybrid,
    Latest, Hold, Window, Events,
    handle_service, call_service,
)
```

Key concepts:
- `Flow[I, O]`: user-defined node logic (`init/run/reset/finalize`)
- `@flow_io` dataclasses: typed ports (each field is a port)
- `flow @ clock`: produces a `FlowHandle` (node instance with execution config)
- `Pipeline`: explicit graph builder (recommended)
- `FlowContext`: context manager graph builder (still supported)
- adapters (`Latest/Hold/Window/Events`): sampling policy for per-port buffers

- clocks (`Rate/Tick/Trigger/Hybrid`): scheduling + field sampling

Guide: `docs/guide_flow.md`.

---

## 2) Unified High-Level API (Recommended)

Import path:
```python
import retriever  # Global namespace
from retriever.lib import Wrapper, from_torch, from_gym
```

- **Pipeline Construction**:
    - `retriever.connect(src, dst, map=None, sync=None)`: Connects two `FlowHandle`s. Implicitly creates/uses a default pipeline.
    - `retriever.lib.Wrapper(obj)`: Factory creating `Flow` instance from `torch.nn.Module` or `gym.Env` factory.

- **Execution**:
    - `retriever.run(backend="dora", duration=10, record="log.mcap")`: Executes pipeline (records if record= set).
    - `retriever.step(dt=0.1)`: Manually steps the default pipeline (in-process debugging).
    - `retriever.reset()`: Resets the default pipeline state.

---

## 2) IR boundary (`retriever.ir`)

Import path:

```py
from retriever.ir import (
    validate,
    IRStruct,
    build_execution, compile_execution,
    ExecutionGraph,
)
```

- `validate(ctx: FlowContext | Pipeline) -> IRStruct`: converts authoring graph into backend-agnostic IR.
- `build_execution(ir: IRStruct) -> ExecutionGraph`: creates a physical execution plan (partitioning + placement hints).
  - `compile_execution` is a compatibility alias.
- `optimize_ir(...)` exists as a legacy name; prefer `build_execution(...)` (see `docs/guide_execution.md`).

Guide: `docs/guide_execution.md`.

---

## 3) Runtime execution (`retriever.rt`)

Import path:

```py
from retriever.rt import execute_ir
```

- `execute_ir(ir_or_graph, backend=..., duration=..., blocking=...)`: runs an `IRStruct` or an `ExecutionGraph` on a backend.

Backends:
- `multiprocessing`: (default)
- `dora`: High-performance, zero-copy (Rust)
- `in-process`: Debugging/recording (determinstic)

Architecture: `docs/architecture.md`.

---

## 4) Debugging / stepping (Pipeline surface)

Preferred entry points:

- `Pipeline.step(now=..., dt=...)` — one in-process debug step
- `Pipeline.reset_stepper()` / `Pipeline.close_stepper()`
- unified recording: `pipe.run(record="file.rrd")` or `pipe.run(record=RecordConfig(path="file.rrd", mirrors=("file.mcap",)))`
- record/replay: `Pipeline.record_to(...)` / `Pipeline.replay(...)` (legacy)

Implementation lives in:
- `retriever/rt/stepper.py`

Guide: `docs/guide_debugging.md`.

---

## 5) Pipelines registry + plugins (`retriever.pipeline_registry`)

Import path:

```py
from retriever.pipeline_registry import (
    register_pipeline,
    list_pipelines,
    build_ir,
    run_pipeline,
)
```

This enables “system packages” (future golden repo) to register pipelines via entry points:
- group: `retriever.plugins`

See: `docs/architecture.md` (“Registry + plugins”).
