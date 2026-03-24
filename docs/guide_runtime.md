---
title: "Refactored Runtime Guide (Canonical)"
---

# Refactored Runtime Guide (Canonical)

This guide documents the **canonical** Retriever runtime workflow:

`Pipeline / TemporalFlow → Pipeline.validate() → IR → (optional) Pipeline.build_execution() → execute_ir()`

It intentionally avoids the legacy `Flow.from_module`/`LocalExecutor` API.

## 1) Quickstart: build + run a tiny pipeline

```py
from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class SrcOut:
    value: int


@io
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

### `@io` types (ports)

Flows communicate with typed `@io` classes. Each annotated field becomes a port.
`@flow_io` remains as a backward-compatible alias, but new docs and examples should prefer `@io`.

### `Flow[I, O]` (node logic)

A `Flow` is a node that implements:

- `init()` (optional)
- `run(input: I) -> O`
- `finalize()` (optional)

### Clocks (when a node executes)

Attach a clock using `flow @ clock`:

- `Rate(hz=...)`: periodic execution, sampling all connected inputs on each tick
- `Tick(hz=...)`: periodic tick-only execution, sampling no inputs
- `Trigger("field", ...)`: event-driven execution on one or more named input fields
- `Hybrid(hz=..., trigger=[...])`: periodic execution plus immediate trigger-driven execution

Defaults:
- `Rate(hz=...)` and the periodic path of `Hybrid(...)` sample all connected inputs.
- `Tick(hz=...)` is the explicit tick-only clock.
- `Trigger(...)` samples only the triggering input fields.

### Wiring (edges)

Connect nodes either with explicit `Pipeline.connect(...)` calls or with `TemporalFlow.then(...)` / `>>`
while a `Pipeline` is active as the owner.

**Option A — explicit `Pipeline.connect(...)`**

```py
pipe = Pipeline("my_pipeline")
a = A() @ Rate(hz=10)
b = B() @ Rate(hz=10)
pipe.connect(a, b, sync=Latest())
```

**Option B — `with pipe:` + handle chaining**

```py
pipe = Pipeline("my_pipeline")
with pipe:
    a = A() @ Rate(hz=10)
    b = B() @ Rate(hz=10)
    a >> b
```

`sync` is an Adapter that defines how the downstream samples its input queue.

## 3) Execution model

### Validate to IR

`pipe.validate()` turns the authored graph into an `IR`. This happens automatically during `Pipeline.run(...)`,
but you can call it directly for debugging or inspection.

### Build execution graph (partitioning + placement)

`pipe.build_execution()` creates an `ExecutionGraph`, a *physical* graph used to decide:

- which flows should run together (co-location / fusion)
- where a partition should run (placement hints; currently informational)

### Run with a backend

`execute_ir(ir, backend=..., duration=..., blocking=...)` runs the IR on:

- `multiprocessing`: local Python multiprocessing backend
- `dora`: dora-rs backend (requires compatible dora CLI + deps)
- `in-process`: single-process wrapper for debugging/recording

`execute_ir(...)` accepts either an `IR` or an `ExecutionGraph`.

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
See `examples/tutorial/c_debug_and_replay/05_buffer_engine_demo.py` for a minimal runnable demo.

## 4) Event/time model (FRP vocabulary)

### `EventBuffer`

Each input port maintains a finite **timestamped buffer**:

`retriever.flow.types.EventBuffer[T] = list[tuple[float, T]]`

This is what `Subscriber.get_all()` returns and what Adapters sample.
For collection/replay/export contracts, use `retriever.data_spec.EventBuffer` instead of the runtime tuple buffer.

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

- an `IR`, or
- a `PipelineBuilder` / `Pipeline` (it will be validated automatically)

### Plugin discovery

The runtime supports entry-point plugins (`retriever.plugins`) so system packages can register pipelines without
living in the runtime repo.

## 6) Notes

- This guide uses `retriever.flow.Pipeline`. The top-level `retriever.Pipeline` re-exports the same class.
- `retriever.rt.signal.Signal` is an internal per-step helper used by executors (sample → transform → publish).
  It is not an `EventStream`.
