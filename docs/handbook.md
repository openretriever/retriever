# Retriever Runtime Handbook

This handbook is the **entry point** for the refactored Retriever runtime/core.

Retriever is being split into:

- **Runtime/Core (this repo)**: typed Flow graphs → IR → backend execution
- **Golden/System (future repo)**: canonical system pipelines + heavy deps (models/robots/sim/training/Ray)

If you’re new: read this page top-to-bottom once, then use the linked guides as references.

---

## 1) Quick Start

- Install / environment setup: `docs/install.md`
- Canonical runtime workflow and examples: `docs/guide_runtime.md`
- Time / FRP vocabulary (EventBuffer, EventStream, Behavior, adapters): `docs/guide_time.md`

Key demos (Pixi):

```sh
pixi run demo-dora
pixi run demo-request-dora
```

---

## 2) What Retriever *is* (and is not)

Retriever runtime is a **type-safe dataflow runtime** for robotics-like pipelines:

1) Author a pipeline as a typed graph (`FlowContext`)
2) Validate/compile to backend-agnostic IR (`validate() → IRStruct`)
3) Execute the IR on a backend (`execute_ir()`):
   - local multiprocessing
   - dora-rs

Retriever runtime is **not** the place for:

- robot drivers / sim glue
- foundation-model stacks
- training pipelines / evaluation suites

Those belong in the future **Golden Retriever** system repo.

---

## 3) Core concepts (the minimum you need)

### 3.1 Flow graph

- `Flow[I, O]` is a node with typed I/O (dataclasses decorated by `@flow_io`)
- `FlowContext` builds a graph of node instances and edges

See: `docs/guide_runtime.md`

### 3.2 IR boundary

- `validate(ctx)` produces `IRStruct`
- Backends consume `IRStruct` (not `FlowContext`)

See: `docs/architecture.md`

### 3.3 Time model

At runtime, every port is a timestamped stream:

- `EventBuffer[T] = list[(ts, value)]`
- Adapters sample buffers at a specific step time `now`
- Clocks decide **when** to execute, and **which fields** to sample

See: `docs/guide_time.md`

---

## 4) Runtime surfaces (where to extend)

### 4.1 Clocks and adapters

- Clocks: `retriever/core/flow/clock.py`
  - `Rate`, `Tick`, `Trigger`, `Hybrid`
- Adapters: `retriever/core/flow/adapter.py`
  - `Latest`, `Hold`, `Window`, `Events`

### 4.2 Backends

- MP backend: `retriever/core/rt/backend/multiprocessing/*`
- Dora backend: `retriever/core/rt/backend/dora/*`

---

## 5) Project structure (runtime vs legacy)

Runtime/core “source of truth” paths:

- `retriever/core/flow/*` — typed graph authoring
- `retriever/core/ir/*` — validation + IR structs
- `retriever/core/rt/*` — execution, backends, runtime FRP helpers

Legacy/system folders still present (expected to move to golden repo):

- `retriever/models`, `retriever/robots`, `retriever/envs`, `retriever/mappers`, `retriever/skills`, etc.

---

## 6) Development workflow

- Contributing / QA: `docs/contributing.md`
- Developer guide: `docs/guide_dev.md`

Recommended validation loop:

```sh
pixi run python -m pytest -q
pixi run demo-request-dora
```

---

## 7) Roadmap (near-term)

- Finish repo split into runtime vs golden/system
- Migrate legacy FRP engine code and heavy deps into golden repo
- Keep runtime install minimal and backends consistent

