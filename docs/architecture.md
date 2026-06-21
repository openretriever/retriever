---
title: "Retriever Runtime Architecture (Canonical)"
---

# Retriever Runtime Architecture (Canonical)

This document describes the **refactored runtime** architecture:

`Pipeline / TemporalFlow → Pipeline.validate() → IR → Pipeline.build_execution() → ExecutionGraph → execute_ir()`

Older pre-runtime architecture notes are not part of the public release docs in this repo.
Use this page plus `docs/guide_execution.md` for the supported architecture surface.

---

## 1) Layers and responsibilities

### 1.1 Authoring (declarative graph)

Code lives in `retriever/flow/`:

- `Flow[I, O]`: user-defined node logic (`reset()`, `run()`, `finalize()`)
- `@io` classes: typed ports (each field is a port)
- `Pipeline`: explicit graph builder (no context manager)
- `PipelineBuilder`: lower-level validator/builder used by the registry and tooling
- `TemporalFlow`: result of `flow @ clock`, used to connect nodes (`then`, `>>`)
- Clocks: `Rate`, `Tick`, `Trigger`, `Hybrid`
- Adapters: sampling policies for input queues (`Latest`, `Hold`, `Window`, `Events`)

### 1.2 Validation (IR boundary)

Code lives in `retriever/ir/`:

- `Pipeline.validate() -> IR`
- `Pipeline.build_execution() -> ExecutionGraph` (optional, but recommended)

`IR` is the stable logical boundary. It contains:

- nodes (flow class/module identity + clock config + metadata)
- edges (port mappings + queue policy + queue sizes)

`ExecutionGraph` is the physical graph used for deployment decisions. It contains:

- partitions (groups of flows that should run together)
- cross-partition edges
- optional placement hints per partition

### 1.3 Execution (runtime + backends)

Code lives in `retriever/rt/`:

- `execute_ir(ir, backend=..., duration=..., blocking=...)`
- in-process debugging: `Pipeline.step(...)` + record/replay helpers (implemented in `retriever/rt/stepper.py`)
- backend registry: `retriever/rt/backend/factory.py`
- backends:
  - `retriever/rt/backend/multiprocessing/*`
  - `retriever/rt/backend/dora/*`

Backends are responsible for:

- building executors per node
- wiring publishers/subscribers per edge
- scheduling execution (clocks)
- process lifecycle (start/wait/stop)

Note: `execute_ir(...)` accepts either an `IR` (logical graph) or an `ExecutionGraph`
(physical plan). When given an execution graph, it is lowered to a backend-friendly IR for execution.

Backend boundary note:
- Dora integration is the supported external-runtime path. Native acceleration is an extension point for future backend packages rather than part of the current public core.

---

## 2) Execution-step data model (FRP vocabulary)

### 2.1 `TimedBuffer`

Each input port is represented at runtime as a finite timestamped history:

- `retriever.flow.types.TimedBuffer[T] = list[tuple[float, T]]`

For collection/replay/export contracts, `retriever.types.data.EventBuffer` is a separate layer with explicit lineage and nanosecond event time.

This is what `Subscriber.get_all()` returns.

### 2.2 `EventStream` and sampling

`EventStream[T]` is a conceptual wrapper over a source of events. In the runtime, each port can be viewed as an
EventStream whose `events()` returns the current `TimedBuffer`.

- `EventStream.sample(adapter, now=...)` applies an Adapter to the current TimedBuffer.
- A `Behavior[T]` is a “continuous-time” sampler derived from an EventStream + Adapter.

The concrete definitions live in `retriever.flow.types`. `retriever.rt` re-exports `Behavior` and `EventStream` for runtime-facing imports. Higher-level stream operations such as `map`, `filter`, `merge`, `fold`, `snapshot`, `combine_latest`, `flat_map`, `Behavior.select(...)`, and `Behavior.until(...)` are methods on those classes rather than a separate `retriever.flow.frp` module.

### 2.3 Step execution helper

Runtime step execution is implemented in `retriever.rt.step` and `retriever.rt.stepper`. For each executed Flow, the runtime:

- samples per-port `TimedBuffer` histories with the configured Adapter at time `now`
- calls `flow.step(...)`
- publishes output values with the step timestamp

The public debugging surface for this path is `Pipeline.step(...)`.

---

## 3) Clock semantics (sampling vs scheduling)

Clocks decide **when** a node runs and (for input ports) **which fields** should be sampled for that step.

Key defaults:

- `Rate(hz=...)` samples **all connected inputs** on each periodic tick.
- `Tick(hz=...)` is the explicit “tick-only” clock (samples no inputs).
- `Trigger("field", ...)` samples the triggering input fields.
- `Hybrid(hz=..., trigger=[...])` mixes periodic execution with trigger-driven execution.

Backends attach a concrete “execution time” to a step:

- `ScheduleResult.now` (wall-clock time used consistently for sampling and output timestamps)

---

## 4) Registry + plugins

Retriever exposes registry surfaces for flows, pipelines, and shared types:

### 4.1 Pipeline registry (IR-first)

`retriever.registry.pipeline` registers **pipeline factories** that return:

- `IR` (preferred), or
- `PipelineBuilder` / `Pipeline` (validated to IR automatically)

### 4.2 Plugin discovery (entry points)

`retriever.plugins` supports loading entry points so external packages can register pipelines/components.

Entry point group:

- `retriever.plugins`

---

## 5) “What to read next”

- User guide: `docs/guide_runtime.md`
- Installation: `docs/getting_started/install.md`
- Execution build details: `docs/guide_execution.md`
