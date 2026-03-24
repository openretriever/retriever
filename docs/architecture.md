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

- `Flow[I, O]`: user-defined node logic (`init()`, `run()`, `finalize()`)
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
- Dora integration + Rust migration candidates: `docs/temp_notes/2025-12-17_dora_rust_boundary.md`
- Native acceleration plan (Tier A/B): `docs/temp_notes/2025-12-17_native_acceleration_plan.md`

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

These live in `retriever/rt/frp.py`.
High-level user combinators (switch, until_event) live in `retriever/flow/frp.py`.

### 2.3 `Signal` (internal step helper)

`retriever/rt/signal.py` defines `Signal`, which is **not** an EventStream.

It is the executor’s per-step helper:

- sample (read per-port EventBuffers and apply Adapters at time `now`)
- transform (call `flow.run(...)`)
- publish (emit output values with the step timestamp)

To avoid duplicating event-stream logic, `Signal` delegates per-port sampling to `EventStream`.

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

## 4) Registry + plugins (pipelines and systems)

To support “system packages” (and the future split into runtime vs golden system repos), the runtime has:

### 4.1 Pipeline registry (IR-first)

`retriever/pipeline_registry.py` registers **pipeline factories** that return:

- `IR` (preferred), or
- `PipelineBuilder` / `Pipeline` (validated to IR automatically)

### 4.2 Plugin discovery (entry points)

`retriever/plugins.py` supports loading entry points so external packages can register pipelines/components.

Entry point group:

- `retriever.plugins`

---

## 5) “What to read next”

- User guide: `docs/guide_runtime.md`
- Installation: `docs/getting_started/install.md`
- Execution build details: `docs/guide_execution.md`
