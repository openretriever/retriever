---
title: "Refactored Runtime Guide (Canonical)"
---

# Refactored Runtime Guide (Canonical)

This guide documents the **canonical** Retriever runtime workflow:

`Pipeline (or FlowContext) → validate() → IRStruct → (optional) build_execution() → execute_ir()`

It intentionally avoids the legacy `Flow.from_module`/`LocalExecutor` API.

## 1) Quickstart: build + run a tiny pipeline

```py
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Latest, flow_io


@flow_io
@dataclass
class SrcOut:
    value: int


@flow_io
@dataclass
class AddOut:
    value: int


class Source(Flow[None, SrcOut]):
    def run(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def run(self, input: SrcOut) -> AddOut:
        return AddOut(value=input.value + 1)


# Set global default (recommended)
import retriever
retriever.init(default_sync=Latest())

pipe = Pipeline("quickstart")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)
pipe.connect(src, add, sync=Latest())

pipe.run(backend="multiprocessing", duration=1.0)
# Or record to MCAP (uses in-process backend):
# pipe.run(duration=1.0, record="log.mcap")
```

### Async full run (non-blocking)

```py
engine = pipe.run(backend="multiprocessing", blocking=False)
# ... do other work ...
engine.stop()
```

### Single-step debugging (in-process)

`Pipeline.step()` runs the authored pipeline in the current Python process and advances it by one step:

```py
res = pipe.step(dt=0.1)  # advances an internal logical clock by 0.1s
print(res.executed)
pipe.close_stepper()
```

More details: `docs/guides/debugging.md`.

### Record + replay (stepper-first)

For unified full-pipeline recording, prefer `pipe.run(record="log.mcap")`.

For granular control (e.g. recording specific flows during manual stepping), use:

```py
pipe.record_to(camera, "logs/camera_recording.pkl.gz", steps=10, dt=0.05)
pipe.replay(camera, path="logs/camera_recording.pkl.gz")
```

## 2) Core concepts

### `@flow_io` types (ports)

Flows communicate with typed, `@flow_io`-decorated dataclasses. Each field becomes a port.

### `Flow[I, O]` (node logic)

A `Flow` is a node that implements:

- `init()` (optional)
- `run(input: I) -> O`
- `finalize()` (optional)

### Clocks (when a node executes)

Attach a clock using `flow @ clock`:

- `Rate(hz=..., sample=[...])`: periodic execution (`fields=` is a supported alias)
- `Trigger("field")` / `Trigger(on=[...])`: event-driven execution
- `Hybrid(hz=..., trigger=[...], sample=[...])`: mixed mode (`trigger_fields=`/`rate_fields=` also work)

Defaults:
- `Rate(hz=...)` and `Hybrid(..., sample=...)` sample **all inputs** by default (`["..."]`).
- Use `sample=[]` (or `Tick(hz=...)`) for tick-only nodes.

### Wiring (edges)

Connect nodes either:

- inside an active `FlowContext`, or
- by attaching connections to an explicit `Pipeline` (no context manager).

**Option A — FlowContext**

- `a.then(b, sync=Latest(), map={"*": "*"})`
- `a >> b` (shorthand for `.then(...)` with defaults)

`sync` is an Adapter that defines how the downstream samples its input queue.

**Option B — Pipeline**

```py
pipe = Pipeline("my_pipeline")
a = A() @ Rate(hz=10)
b = B() @ Rate(hz=10)
pipe.connect(a, b, sync=Latest())
```

## 3) Execution model

### Validate to IR

`validate(ctx)` turns the `Pipeline`/`FlowContext` graph into an `IRStruct`. This happens automatically during `Pipeline.run(...)`,
but you can call it directly for debugging/inspection.

### Build execution graph (partitioning + placement)

`build_execution(ir)` creates an `ExecutionGraph`, a *physical* graph used to decide:

- which flows should run together (co-location / fusion)
- where a partition should run (placement hints; currently informational)

### Run with a backend

`execute_ir(ir, backend=..., duration=..., blocking=...)` runs the IR on:

- `multiprocessing`: local Python multiprocessing backend
- `dora`: dora-rs backend (requires compatible dora CLI + deps)
- `in-process`: single-process wrapper for debugging/recording

`execute_ir(...)` accepts either an `IRStruct` or an `ExecutionGraph`.

Note: `compile_execution(...)` remains as a compatibility alias for `build_execution(...)`.

### Dora backend config: native node overrides (Tier A.1)

The dora backend can optionally run selected nodes as **native dora nodes** (Rust binaries) rather than Python executors.
This is controlled at execution time (no change to Flow authoring code) via `backend_config["native_overrides"]`:

```py
pipe.run(
    backend="dora",
    backend_config={
        # Match by node.id, "module:Type", or Type (in that order).
        "native_overrides": {
            "CameraSource": "native:retriever-dora-camera",
        }
    },
    duration=10.0,
)
```

Design plan: `docs/temp_notes/2025-12-17_native_acceleration_plan.md`.

### Backend config: buffer engine (Tier B.3)

The runtime hot-path samples timestamped per-port buffers every step. Backends expose a
`buffer_engine` switch so we can later swap in a Rust implementation without changing
user pipelines:

```py
pipe.run(
    backend="dora",
    backend_config={"buffer_engine": "python"},  # default
    duration=10.0,
)
```

`"native"` is reserved for a future `retriever_native` extension.
See `examples/tutorial/015_buffer_engine_demo.py` for a minimal runnable demo.

## 4) Event/time model (FRP vocabulary)

### `EventBuffer`

Each input port maintains a finite **timestamped buffer**:

`EventBuffer[T] = list[tuple[float, T]]`

This is what `Subscriber.get_all()` returns and what Adapters sample.

### `EventStream`

`EventStream[T]` is a conceptual view over an event source. In the runtime:

- each port is an EventStream
- the runtime materializes only a finite `EventBuffer` per port

`EventStream.sample(adapter, now=...)` applies an Adapter to its `EventBuffer`.

### `Behavior`

`Behavior[T]` is a continuous-time sampler: `t -> value`. In this runtime it is usually derived from an
`EventStream` via an Adapter.

High-level combinators (`switch_behavior`, `until_event`) are available in `retriever.flow.frp`.

### Adapters (sampling policy)

Adapters decide how to interpret an `EventBuffer` at time `now`:

- `Latest()`: last value
- `Hold(debounce=...)`: zero-order hold with debounce
- `Window(duration=..., agg=...)`: time window aggregation
- `Events(duration=..., include_timestamps=...)`: return history/window (for “queue manipulation” flows)

## 5) Pipelines registry + plugins

### Register a pipeline factory

Use `retriever.pipeline_registry.register_pipeline` to register a pipeline builder that returns:

- an `IRStruct`, or
- a `Pipeline` / `FlowContext` (it will be validated automatically)

### Plugin discovery

The runtime supports entry-point plugins (`retriever.plugins`) so system packages can register pipelines without
living in the runtime repo.

## 6) Notes

- This guide uses `retriever.flow.Pipeline`. The top-level `retriever.Pipeline` is legacy/FRP-engine code
  and is not part of the refactored runtime surface.
- `retriever.rt.signal.Signal` is an internal per-step helper used by executors (sample → transform → publish).
  It is not an `EventStream`.
