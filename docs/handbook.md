---
title: "Retriever Runtime Handbook (Canonical)"
---

# Retriever Runtime Handbook (Canonical)

This is the **single canonical note** for using the **Retriever runtime/core**.

If you only read one document, read this one.

If you want the shorter version first, start with `docs/quickstart.md`.

---

## 0) Quick Start (Pixi)

Supported Python: **3.11+**. Pixi pins `3.11.*` as the tested baseline in this repo.

```bash
# Install pixi (if needed)
# macOS / Linux
curl -fsSL https://pixi.sh/install.sh | bash

# Start with the local multiprocessing baseline
pixi run demo-stepper
pixi run demo-webcam-record
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
pixi install
pixi run demo-stepper
```

If you want the live camera path after that, run:

```bash
pixi run demo-webcam-stepper
pixi run demo-webcam-record
```

Pixi vs uv (how they fit together):

- **Pixi** manages a full environment from `pixi.toml` and installs the PyPI portion via `uv` internally.
- If you prefer **uv-only** workflows, use a separate venv/conda env and `uv pip install -e ".[demo,dora]"`.
- Avoid mixing `uv sync` into a Pixi env unless you also update `pixi.toml`/`pixi.lock`.

---

## 1) Mental model (what user is building)

Retriever runtime is a **typed dataflow runtime**:

1) You author a graph of typed nodes (**Flows**) connected by typed edges (**ports**).
2) Retriever validates the graph into a backend-agnostic IR.
3) Retriever optionally builds an **ExecutionGraph** (partitioning/co-location).
4) Retriever executes the graph on a backend (`multiprocessing` or `dora`).

Two execution surfaces exist on purpose:

- `Pipeline.run(...)`: production-ish execution on a backend (separate processes).
- `Pipeline.step(...)`: in-process stepper (single-step debugging with VS Code breakpoints).

Canonical workflow:

`Pipeline / TemporalFlow → Pipeline.validate() → IR → (optional) Pipeline.build_execution() → execute_ir()`

But **user code should usually just call**:

- `pipe.run(...)` (full run), or
- `pipe.step(...)` (debug).

---

## 2) Authoring: define ports and flows

### 2.1 Define typed ports with `@io`

Flows communicate using `@io` classes. Each annotated field becomes a **port**.

```py
from retriever.flow import io


@io
class SrcOut:
    value: int


@io
class AddOut:
    value: int
```

Notes:
- `@io` makes fields `Optional[...]` and adds runtime metadata (signals).

### 2.2 Implement a `Flow[I, O]`

```py
from retriever.flow import Flow


class Source(Flow[None, SrcOut]):
    def step(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def step(self, input: SrcOut) -> AddOut:
        return AddOut(value=input.value + 1)
```

Lifecycle hooks:
- `reset()` / `finalize()` (optional) for resources and gym-like state
- `init()` remains available only as a deprecated compatibility alias

---

## 3) Authoring: clocks and connections

### 3.1 Attach clocks: `flow @ clock`

```py
from retriever.flow import Rate, Tick, Trigger

src = Source() @ Rate(hz=10)        # periodic; samples inputs (default: all)
tick_only = Source() @ Tick(hz=10)  # periodic; samples no inputs
event_driven = AddOne() @ Trigger("value")
```

Clock cheat-sheet:
- `Rate(hz=...)`: periodic, sampling all connected inputs.
- `Tick(hz=...)`: periodic tick-only.
- `Trigger("field")`: runs when a new arrival happens on that input field.
- `Hybrid(hz=..., trigger=[...])`: periodic + event-driven combined.

### 3.2 Connect nodes with a `Pipeline` (recommended)

```py
from retriever.flow import Pipeline, Latest

pipe = Pipeline("demo")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)
pipe.connect(src, add, sync=Latest())
```

Notes:
- `sync=...` is **required** unless you set a global default: `retriever.init(default_sync=Latest())`.
- `map={"*": "*"}` is the default port mapping.

You can also use a `Pipeline` as a context manager to enable `then(...)` / `>>` wiring:

```py
pipe = Pipeline("demo")
with pipe:
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    src >> add

# Handles are tagged with `handle.pipeline = pipe`, so you can keep wiring later:
more = AddOne() @ Rate(hz=10)
add >> more
```

`Pipeline` is the canonical public authoring surface. Use `pipe.connect(...)` or `with pipe:` when chaining `a.then(b)` / `a >> b`.

---

## 4) Running: full execution (`Pipeline.run`)

### 4.1 Local multiprocessing

```py
pipe.run(backend="multiprocessing", duration=3.0, blocking=True)
```

### 4.2 Dora backend

```py
pipe.run(backend="dora", duration=10.0, blocking=True)
```

Notes:
- Dora requires `dora-rs`, `dora-rs-cli`, `pyarrow` (handled by Pixi in `demo-webcam-detection-dora`).
- If you see schema mismatch errors while using Dora, restart Dora and rerun the same Dora task.

### 4.3 Non-blocking run

```py
engine = pipe.run(backend="multiprocessing", blocking=False)
# ... do other work ...
engine.stop()
```

---

## 5) Debugging: single-step execution (`Pipeline.step`)

`Pipeline.step()` runs the pipeline **in the current Python process** and advances one discrete step.
This is the recommended way to use the VS Code debugger inside `Flow.step()` logic.

```py
res = pipe.step(dt=0.1)
print(res.executed)
pipe.close_stepper()
```

Key semantics:
- `dt` advances an internal logical clock used for timestamps.
- `Trigger(...)` nodes only execute when a new arrival is observed.
- `Rate(...)` nodes execute once per `step()` call.

Recommended examples:

- Minimal debug + exception trace: `examples/tutorial/c_debug_and_replay/01_debug_stepper.py`
- Perception debug (synthetic frames): `examples/tutorial/c_debug_and_replay/02_debug_perception_stepper.py`
- Perception debug (real camera): `examples/tutorial/c_debug_and_replay/03_debug_perception_stepper_real_camera.py`

Topic-focused tutorials (legacy extractions):

- Windowed vision stats: `examples/tutorial/b_ir_and_execution/08_detection_window_stats.py`
- Closed-loop feedback intro: `examples/tutorial/d_closed_loop_state_feedback/07_feedback_intro.py`
- Event-driven replanning: `examples/tutorial/d_closed_loop_state_feedback/08_event_driven_replan.py`
- Execution monitoring: `examples/tutorial/d_closed_loop_state_feedback/09_execution_monitoring.py`

---

## 5.5 Optional ergonomics: `retriever.connect(...)` (default pipeline)

For lightweight experiments (REPL/notebooks), you can build a graph without explicitly passing a `Pipeline` around.
Retriever maintains a thread-local **default pipeline**:

```py
import retriever
from retriever.flow import Rate

# Start a fresh pipeline
# (For scripts, we recommend 'with Pipeline():' instead of global state)
retriever.clear_default_pipeline()

a = Source() @ Rate(hz=10)
b = AddOne() @ Rate(hz=10)

retriever.connect(a, b)

# Run the accumulated default pipeline
retriever.default_pipeline().run(backend="multiprocessing", duration=1.0)
```

Notes:
- `retriever.connect(...)` respects an active `with Pipeline(...):` context.
- Canonical demo: `examples/tutorial/a_flow_fundamentals/05_pipeline_ergonomics.py`

---

## 6) Unified Execution & Recording

Retriever supports a unified API to run and debug pipelines.

### 6.1 Recording execution
You can record any execution to a Rerun `.rrd` file (optionally mirrored to `.mcap`) by passing `record=...`.
This automatically switches to the **in-process** backend to ensure deterministic recording.

```py
pipe.run(
    duration=5.0,
    record="session.rrd",
    visualize="rerun"  # Optional: stream to viewer live
)
```

This generates `session.rrd` containing all flow I/O. If you also want an interchange artifact, mirror to `.mcap`:

```py
from retriever import RecordConfig

pipe.run(
    duration=5.0,
    record=RecordConfig(path="session.rrd", mirrors=("session.mcap",)),
)
```

### 6.2 Replay
To replay data into a pipeline (e.g. replacing a camera source), use `replay()`:

```py
# Inject recorded data into 'camera' flow
pipe.replay(camera, path="session.rrd")  # `.mcap` works too
pipe.step(dt=0.1)
pipe.close_stepper()
```

---

## 7) Time + FRP vocabulary (runtime model)

At runtime, each port behaves like an event stream:

- `EventBuffer[T] = list[(timestamp, value)]` (finite history)
- Adapters sample buffers at time `now` to produce a value for the `Flow` input.

Important distinction:

- **Clock policy** decides *when* a node runs.
- **Adapter policy** decides *what* data a node sees when it runs.

Adapters (sampling policies):
- `Latest()` (default)
- `Hold(...)`
- `Window(duration=..., agg=...)`
- `Events(...)`

---

## 8) What happens if a node can’t meet its target Hz? (`Rate.on_lag`)

If a node is configured with `Rate(hz=...)` but is too slow, Retriever must decide what to do with missed ticks.

Supported policies:

- `on_lag="warn"` *(default)*: drop missed ticks + emit throttled warnings (bounded latency)
- `on_lag="drop"`: drop missed ticks quietly (bounded latency)
- `on_lag="error"`: raise when lagging by ≥ 1 tick (aliases: `"panic"`, `"raise"`, `"strict"`)
- `on_lag="catch_up"`: execute every tick eventually (simulation-style; latency can grow)

Pipeline-wide default:

```py
pipe = Pipeline("my_pipe", on_lag="panic")  # alias for "error"
# or:
pipe.set_on_lag("warn")
```

Quick checks (Dora):

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env --env toy --backend dora --hz 50 --duration 2 --on-lag warn
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env --env toy --backend dora --hz 50 --duration 2 --on-lag panic
```

Why this matters on Dora:
- slow nodes can cause tick events to accumulate
- without an explicit policy, the node may “replay” stale ticks and run in bursts with stale inputs

---

## 9) Canonical examples (run these first)

### 9.1 Pipeline authoring ergonomics (017)

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode context --exec step
```

Module: `examples/tutorial/a_flow_fundamentals/05_pipeline_ergonomics.py`

### 9.2 Webcam stepper + record/replay

```bash
pixi run demo-webcam-stepper
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
pixi run demo-webcam-replay-mcap
```

Modules:

- `examples/tutorial/c_debug_and_replay/03_debug_perception_stepper_real_camera.py`
- `examples/tutorial/c_debug_and_replay/04_record_replay_perception.py`

### 9.3 Request/response demo (010)

```bash
pixi run demo-request-response
```

Module: `examples/tutorial/b_ir_and_execution/07_request_response.py`

### 9.4 Closed-loop env + MPC demo (016)

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env --env toy --backend multiprocessing --hz 10 --duration 3
```

Optional (Pendulum, requires gymnasium/gym):

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.01_closed_loop_env --env pendulum --backend dora --hz 10 --duration 5
```

---

## 10) Project structure

Runtime/core “source of truth”:

- `src/retriever/flow/*` — typed graph authoring
- `src/retriever/ir/*` — validation + IR structs
- `src/retriever/rt/*` — execution, backends, stepper/debugging helpers
- `src/retriever/types/*` — shared typed payloads and registry-backed type helpers

System integrations, robot SDK wrappers, and heavier application stacks should
live in separate packages that build on top of the runtime/core surface.

---

## 11) Where to look in code

- Pipeline authoring: `src/retriever/flow/pipeline.py`
- Clocks: `src/retriever/flow/clock.py`
- Adapters: `src/retriever/flow/adapter.py`
- Builder/validation: `src/retriever/flow/builder.py`
- MP backend: `src/retriever/rt/backend/multiprocessing/*`
- Dora backend: `src/retriever/rt/backend/dora/*`
- Stepper/debugger: `src/retriever/rt/stepper.py`

---

## 12) Troubleshooting (common)

- Dora schema/version mismatch: `pkill -9 dora` then rerun.
- Python 3.14: avoid until optional deps ship wheels.
- If using Pixi: don’t install random pip deps into `.pixi/envs/default` outside of Pixi tasks.

---

## 13) Development (optional)

- Contributing / QA: `docs/contributing.md`
- Developer guide: `docs/guides/development.md`

Recommended validation loop:

```bash
pixi run python -m pytest -q
pixi run demo-request-response
```
