---
title: "Flow Authoring Guide (Runtime/Core)"
---

# Flow Authoring Guide (Runtime/Core)

This guide describes the **refactored** Flow authoring surface used by the runtime/core:

`Pipeline / TemporalFlow → Pipeline.validate() → IR → (optional) Pipeline.build_execution() → execute_ir()`

Older pre-runtime-authoring material is not part of the public release docs in this repo.
Use the tutorial tracks and `docs/handbook.md` as the supported source of truth.

---

## 1) Define typed ports with `@io`

Flows communicate using `@io` classes. Each annotated field becomes a **port**.

```py
from retriever.flow import io


@io
class CameraOut:
    image: "np.ndarray"


@io
class DetectionsOut:
    detections: list
```

Notes:
- `@io` makes all fields `Optional[...]` with default `None`. The runtime sets only the fields present for a step.
- `@io` is standalone. Do not stack it with `@dataclass`.
- Inside `Flow.step(...)`, use `input._signals` to see which fields are present.

---

## 2) Implement a `Flow[I, O]`

A `Flow` is a typed node. Implement `step(...)` and optionally lifecycle hooks:

- `__lazy_init__()` / `reset()` / `finalize()` for resources and runtime-local state
- `run()` / `init()` only as deprecated compatibility aliases for older flows

Keep module top-level code and `__init__()` import-safe and lightweight. Acquire
runtime-local resources in `__lazy_init__()` / `reset()`.

```py
from retriever.flow import Flow, io


@io
class SrcOut:
    value: int


@io
class AddOut:
    value: int


class Source(Flow[None, SrcOut]):
    def step(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def step(self, input: SrcOut) -> AddOut:
        return AddOut(value=input.value + 1)
```


- `Flow.run(...)` and `Flow.forward(...)` are compatibility aliases for `step(...)`. Backend execution stays on `Pipeline.run(...)`.

## 2.1) Wrapper Factory (Torch/Gym)

For standard libraries, use `retriever.lib.Wrapper` instead of writing custom classes:

```python
from retriever.lib import Wrapper

# PyTorch Module
model = Wrapper(MyModule())

# Gym Environment (pass instance or factory)
env = Wrapper(lambda: gym.make("CartPole-v1"))
```

---

## 3) Attach clocks: `flow @ clock`

Attach a clock to a flow instance to create a runnable node handle:

```py
from retriever.flow import Rate, Trigger, Tick

src = Source() @ Rate(hz=10)           # periodic, samples all inputs (default)
tick_only = Source() @ Tick(hz=10)     # periodic, samples no inputs
event_driven = AddOne() @ Trigger("value")
```

### Scheduling vs sampling

Clocks decide when a node runs; adapters decide how each connected input buffer is sampled.

- `Rate(hz=...)` runs periodically and samples all connected inputs on each tick.
- `Tick(hz=...)` is the explicit tick-only clock and samples no inputs.
- `Trigger("field", ...)` runs on arrivals of the specified input fields.
- `Hybrid(hz=..., trigger=[...])` combines periodic execution with immediate trigger-driven runs.

For per-edge buffering and sampling behavior, configure adapters with `sync=...` and edge policies with `edge_config=...`.

### Lag handling (`Rate.on_lag=...`)

If a node cannot keep up with its configured `Rate(hz=...)` (e.g. a large model is too slow),
Retriever needs an explicit policy for “missed ticks”.

`Rate(..., on_lag=...)` (and `Hybrid(..., on_lag=...)` for its periodic path) supports:

- `on_lag="warn"` (default): skip missed ticks + emit throttled warnings (keeps latency bounded, but visible)
- `on_lag="drop"`: same as warn, but without warnings (quiet best-effort)
- `on_lag="error"`: raise if lagging by ≥ 1 tick (aliases: `"panic"`, `"raise"`, `"strict"`)
- `on_lag="catch_up"`: execute every tick eventually (simulation-style; latency can grow)

See: `docs/handbook.md` (Rate lag policy section).

Quick demo (Dora, using the `panic` alias):

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env --env toy --backend dora --hz 50 --duration 2 --on-lag panic
```

Pipeline-wide default:

- `Pipeline("name", on_lag="error")` or `pipe.set_on_lag("error")` applies a default to any node still using the library default (`on_lag="warn"`).

### Global Defaults

You can set a global default adapter at startup:

```python
import retriever
from retriever.flow import Latest

retriever.init(
    default_sync=Latest(),
)
```

Use `Pipeline(..., on_lag=...)` or `pipe.set_on_lag(...)` to set lag policy defaults for a graph.

See also: `docs/guide_temporal.md`.

---

## 4) Connect nodes (edges)

### Fan-in (Many-to-One)

You can connect multiple outputs to the same input port ("fan-in"). They share a single underlying buffer.

```python
# A, B, and C all feed into monitor's 'data' port
a.then(monitor, sync=Latest())
b.then(monitor, sync=Latest())
c.then(monitor, sync=Latest())
```

- With `Latest()`: The monitor runs whenever *any* of the sources emits a value (interleaved execution).
- With `Window(agg="mean")`: The monitor runs on the aggregated buffer of all inputs.

### explicit `Pipeline` (recommended)

`Pipeline` is the preferred authoring surface when you don’t want a global context manager.

```py
from retriever.flow import Pipeline, Rate, Latest

pipe = Pipeline("demo")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)

pipe.connect(src, add, sync=Latest())  # default adapter is Latest()
```

### `then(...)` and `>>`

`TemporalFlow.then(...)` and the `>>` operator connect nodes:

```py
src.then(add, sync=Latest(), qsize=10)
src >> add
```

Important: handles must belong to the same `Pipeline`. The easiest way to guarantee that is to use either
explicit `pipe.connect(...)` calls or `with pipe:` when using `>>`.

### Port mapping (`map=...`)

Edges are port-level. By default (`map={"*": "*"}`), Retriever auto-connects fields by **matching names**.

For explicit wiring:

```py
src.then(add, map={"value": "value"})     # src.value -> add.value
```

### Adapters (`sync=...`)

Adapters define how a downstream samples its input **buffer**:

- `Latest()` (default if configured globally)
- `Hold(debounce=...)`
- `Window(duration=..., agg=..., buffer_size=...)`
- `Events(duration=..., include_timestamps=..., buffer_size=...)`
- `Chunking(dt=...)`
- `Linear()`

Adapters live in `retriever/flow/adapter.py`. The underlying buffer type is:

`EventBuffer[T] = list[(timestamp: float, value: T)]`

See: `docs/guide_temporal.md`.

---

## 5) Run vs debug

### Full execution on a backend

```py
pipe.run(backend="multiprocessing", duration=1.0)
# Use backend="dora" explicitly for dora deployments or parity checks.

# Record to file (uses in-process backend)
pipe.run(duration=5.0, record="session.mcap")
```

### In-process single-step debugging

`Pipeline.step(...)` runs the pipeline in the current Python process so you can use the VS Code debugger
inside `Flow.step(...)`:

```py
pipe.step(dt=0.1)
pipe.close_stepper()
```

See: `docs/guides/debugging.md`.

---

## 6) Service RPC flows (advanced)

Retriever supports request/response “RPC edges” using generator-based flows via decorators:

- `@handle_service` (service provider methods)
- `@call_service(...)` (service client flow that `yield`s `ServiceCall`)

Example: `examples/tutorial/b_ir_and_execution/07_request_response.py`.

Notes:
- Service flows currently require a backend that supports the RPC wiring (the dora backend does).
- `Pipeline.step(...)` is a debug tool and currently does **not** support generator-based flows.

---

## 7) Closed loops (cycles)

Retriever allows **feedback edges** (cycles). Cycles are represented as SCC groups in `IR.topology.groups`.

Practical guidance:

- Avoid a “Trigger-only” cycle (`Trigger(...)` on every node): it may deadlock with no initial event.
- Prefer a **clocked plant/env** and an **event-driven controller**:
  - env: `Rate(hz=...)` (steps periodically, samples latest action)
  - controller: `Trigger("obs")` (runs when a new observation arrives)

This yields a stable distributed closed-loop where the env tick uses the most recent action.

Example:
- `examples/tutorial/d_closed_loop_state_feedback/01_closed_loop_env.py`
  - `--env toy` (no extra deps)
  - `--env pendulum` (requires `gymnasium` or `gym`, MPC balancing loop)

Gym-style env wrapper notes:
- A Gym env is typically stateful and imperative; in Retriever you wrap it in a `Flow`:
  - `init()` creates the env
  - `run(Action)` performs `env.step(action)` and returns `Observation`
  - the flow can internally decide when to `reset()` (e.g. on `done=True`)
- The closed-loop becomes a normal pipeline cycle (env↔controller), which can run on
  multiprocessing or Dora without changing user code.
