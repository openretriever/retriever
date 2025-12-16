# Retriever Runtime Architecture (Canonical)

This document describes the **refactored runtime** architecture:

`FlowContext → validate() → IRStruct → execute_ir()`

If you are looking for the older “Flow.from_module / LocalExecutor / ExecutionEngine” material, see
`docs/architecture_legacy.md`.

---

## 1) Layers and responsibilities

### 1.1 Authoring (declarative graph)

Code lives in `retriever/core/flow/`:

- `Flow[I, O]`: user-defined node logic (`init()`, `run()`, `finalize()`)
- `@flow_io` dataclasses: typed ports (each field is a port)
- `FlowContext`: context manager that collects nodes + edges
- `FlowHandle`: result of `flow @ clock`, used to connect nodes (`then`, `>>`)
- Clocks: `Rate`, `Tick`, `Trigger`, `Hybrid`
- Adapters: sampling policies for input queues (`Latest`, `Hold`, `Window`, `Events`)

### 1.2 Validation (IR boundary)

Code lives in `retriever/core/ir/`:

- `validate(ctx: FlowContext) -> IRStruct`

`IRStruct` is the stable boundary for backends. It contains:

- nodes (flow class/module identity + clock config + metadata)
- edges (port mappings + queue policy + queue sizes)

### 1.3 Execution (runtime + backends)

Code lives in `retriever/core/rt/`:

- `execute_ir(ir, backend=..., duration=..., blocking=...)`
- backend registry: `retriever/core/rt/backend/factory.py`
- backends:
  - `retriever/core/rt/backend/multiprocessing/*`
  - `retriever/core/rt/backend/dora/*`

Backends are responsible for:

- building executors per node
- wiring publishers/subscribers per edge
- scheduling execution (clocks)
- process lifecycle (start/wait/stop)

---

## 2) Execution-step data model (FRP vocabulary)

### 2.1 `EventBuffer`

Each input port is represented at runtime as a finite timestamped history:

- `EventBuffer[T] = list[tuple[float, T]]`

This is what `Subscriber.get_all()` returns.

### 2.2 `EventStream` and sampling

`EventStream[T]` is a conceptual wrapper over a source of events. In the runtime, each port can be viewed as an
EventStream whose `events()` returns the current `EventBuffer`.

- `EventStream.sample(adapter, now=...)` applies an Adapter to the current EventBuffer.
- A `Behavior[T]` is a “continuous-time” sampler derived from an EventStream + Adapter.

These live in `retriever/core/rt/frp.py`.

### 2.3 `Signal` (internal step helper)

`retriever/core/rt/signal.py` defines `Signal`, which is **not** an EventStream.

It is the executor’s per-step helper:

- sample (read per-port EventBuffers and apply Adapters at time `now`)
- transform (call `flow.run(...)`)
- publish (emit output values with the step timestamp)

To avoid duplicating event-stream logic, `Signal` delegates per-port sampling to `EventStream`.

---

## 3) Clock semantics (sampling vs scheduling)

Clocks decide **when** a node runs and (for input ports) **which fields** should be sampled for that step.

Key defaults:

- `Rate(hz=...)` samples **all input fields** by default.
- `Tick(hz=...)` is the explicit “tick-only” clock (samples no inputs).
- `Trigger(fields=[...])` samples only the triggering fields.
- `Hybrid(..., rate_fields=[...], trigger_fields=[...])` mixes both behaviors.

Backends attach a concrete “execution time” to a step:

- `ScheduleResult.now` (wall-clock time used consistently for sampling and output timestamps)

---

## 4) Registry + plugins (pipelines and systems)

To support “system packages” (and the future split into runtime vs golden system repos), the runtime has:

### 4.1 Pipeline registry (IR-first)

`retriever/core/pipeline_registry.py` registers **pipeline factories** that return:

- `IRStruct` (preferred), or
- `FlowContext` (validated to IRStruct automatically)

### 4.2 Plugin discovery (entry points)

`retriever/core/plugins.py` supports loading entry points so external packages can register pipelines/components.

Entry point group:

- `retriever.plugins`

---

## 5) “What to read next”

- User guide: `docs/guide_runtime.md`
- Installation: `docs/install.md`
- Legacy architecture reference: `docs/architecture_legacy.md`

