# Flow Authoring Guide (Runtime/Core)

This guide describes the **refactored** Flow authoring surface used by the runtime/core:

`Pipeline (or FlowContext) → validate() → IRStruct → (optional) build_execution() → execute_ir()`

If you’re looking for the older “Flow.from_module / LocalExecutor / Eff monad” material, it lives in:
- `docs/legacy/guide_flow_legacy.md`

---

## 1) Define typed ports with `@flow_io`

Flows communicate using dataclasses decorated with `@flow_io`. Each field becomes a **port**.

```py
from dataclasses import dataclass
from retriever.core.flow import flow_io


@flow_io
@dataclass
class CameraOut:
    image: "np.ndarray"


@flow_io
@dataclass
class DetectionsOut:
    detections: list
```

Notes:
- `@flow_io` makes all fields `Optional[...]` with default `None`. The runtime sets only the fields present for a step.
- Inside `Flow.run(...)`, use `input._signals` to see which fields are present.

---

## 2) Implement a `Flow[I, O]`

A `Flow` is a typed node. Implement `run(...)` and optionally lifecycle hooks:

- `init()` / `finalize()` for resources (models, cameras, sockets)
- `reset()` for “gym-like” stateful flows (optional; mostly a hook for the future)

```py
from dataclasses import dataclass
from retriever.core.flow import Flow, flow_io


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
```

Ergonomics:
- `Flow.step(...)` and `Flow.forward(...)` are aliases for `run(...)`. This keeps the word “run” available for backend execution (`Pipeline.run`).

---

## 3) Attach clocks: `flow @ clock`

Attach a clock to a flow instance to create a runnable node handle:

```py
from retriever.core.flow import Rate, Trigger, Tick

src = Source() @ Rate(hz=10)           # periodic, samples all inputs (default)
tick_only = Source() @ Tick(hz=10)     # periodic, samples no inputs
event_driven = AddOne() @ Trigger("value")
```

### Field sampling (`Rate.sample=...`)

Clocks control both scheduling and input sampling:
- `Rate(hz=..., sample=...)` (alias: `fields=`) selects which input fields are read on a tick.
  - default: sample all inputs (`sample="all"` / `"*"` / `...`)
  - `sample=[]`: sample no inputs (tick-only)
- `Trigger(...)` runs on arrivals of specified fields
- `Hybrid(...)` combines both (see `retriever/core/flow/clock.py`)

See also: `docs/guide_time.md`.

---

## 4) Connect nodes (edges)

### Option A (recommended): explicit `Pipeline`

`Pipeline` is the preferred authoring surface when you don’t want a global context manager.

```py
from retriever.core.flow import Pipeline, Rate, Latest

pipe = Pipeline("demo")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)

pipe.connect(src, add, sync=Latest())  # default adapter is Latest()
```

### Option B: `FlowContext` (still supported)

`FlowContext` collects connections made via `then(...)` / `>>` inside a `with` block.

```py
from retriever.core.flow import FlowContext, Rate
from retriever.core.rt import execute_ir

with FlowContext("demo") as ctx:
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    src >> add

ir = ctx.validate()
execute_ir(ir, backend="multiprocessing", duration=1.0)
```

### `then(...)` and `>>`

`FlowHandle.then(...)` and the `>>` operator connect nodes:

```py
src.then(add, sync=Latest(), qsize=10)
src >> add
```

Important: you **cannot mix** an active `FlowContext` with `Pipeline`-owned handles. Pick one style per graph.

### Port mapping (`map=...`)

Edges are port-level. By default (`map={"*": "*"}`), Retriever auto-connects fields by **matching names**.

For explicit wiring:

```py
src.then(add, map={"value": "value"})     # src.value -> add.value
```

### Adapters (`sync=...`)

Adapters define how a downstream samples its input **buffer**:

- `Latest()` (default)
- `Hold(debounce=...)`
- `Window(duration=..., agg=..., buffer_size=...)`
- `Events(duration=..., include_timestamps=..., buffer_size=...)`

Adapters live in `retriever/core/flow/adapter.py`. The underlying buffer type is:

`EventBuffer[T] = list[(timestamp: float, value: T)]`

See: `docs/guide_time.md`.

---

## 5) Run vs debug

### Full execution on a backend

```py
pipe.run(backend="multiprocessing", duration=1.0)
pipe.run(backend="dora", duration=10.0)
```

### In-process single-step debugging

`Pipeline.step(...)` runs the pipeline in the current Python process so you can use the VS Code debugger
inside `Flow.run(...)`:

```py
pipe.step(dt=0.1)
pipe.close_stepper()
```

See: `docs/guide_debugging.md`.

---

## 6) Service RPC flows (advanced)

Retriever supports request/response “RPC edges” using generator-based flows via decorators:

- `@handle_service` (service provider methods)
- `@call_service(...)` (service client flow that `yield`s `ServiceCall`)

Example: `examples/00_refact/010_request_response.py`.

Notes:
- Service flows currently require a backend that supports the RPC wiring (the dora backend does).
- `Pipeline.step(...)` is a debug tool and currently does **not** support generator-based flows.

