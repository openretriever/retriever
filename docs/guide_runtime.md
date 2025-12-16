# Refactored Runtime Guide (Canonical)

This guide documents the **canonical** Retriever runtime workflow:

`FlowContext → validate() → IRStruct → execute_ir()`

It intentionally avoids the legacy `Flow.from_module`/`LocalExecutor` API.

## 1) Quickstart: build + run a tiny pipeline

```py
from dataclasses import dataclass

from retriever.core.flow import Flow, FlowContext, Rate, Latest, flow_io
from retriever.core.ir import validate
from retriever.core.rt import execute_ir


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


with FlowContext("quickstart") as ctx:
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    src.then(add, sync=Latest())

ir = validate(ctx)
execute_ir(ir, backend="multiprocessing", duration=1.0)
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

- `Rate(hz=..., fields=[...])`: periodic execution
- `Trigger(fields=[...])`: event-driven execution
- `Hybrid(hz=..., trigger_fields=[...], rate_fields=[...])`: mixed mode

Defaults:
- `Rate(hz=...)` and `Hybrid(..., rate_fields=...)` sample **all inputs** by default (`["..."]`).
- Use `fields=[]` (or `Tick(hz=...)`) for tick-only nodes.

### Wiring (edges)

Connect nodes inside an active `FlowContext`:

- `a.then(b, sync=Latest(), map={"*": "*"})`
- `a >> b` (shorthand for `.then(...)` with defaults)

`sync` is an Adapter that defines how the downstream samples its input queue.

## 3) Execution model

### Validate to IR

`validate(ctx)` turns the `FlowContext` graph into an `IRStruct`. This is the stable boundary for backends.

### Run with a backend

`execute_ir(ir, backend=..., duration=..., blocking=...)` runs the IR on:

- `multiprocessing`: local Python multiprocessing backend
- `dora`: dora-rs backend (requires compatible dora CLI + deps)

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

### Adapters (sampling policy)

Adapters decide how to interpret an `EventBuffer` at time `now`:

- `Latest()`: last value
- `Hold(debounce=...)`: zero-order hold with debounce
- `Window(duration=..., agg=...)`: time window aggregation
- `Events(duration=..., include_timestamps=...)`: return history/window (for “queue manipulation” flows)

## 5) Pipelines registry + plugins

### Register a pipeline factory

Use `retriever.core.pipeline_registry.register_pipeline` to register a pipeline builder that returns:

- an `IRStruct`, or
- a `FlowContext` (it will be validated automatically)

### Plugin discovery

The runtime supports entry-point plugins (`retriever.plugins`) so system packages can register pipelines without
living in the runtime repo.

## 6) Notes

- `retriever.core.rt.signal.Signal` is an internal per-step helper used by executors (sample → transform → publish).
  It is not an `EventStream`.
