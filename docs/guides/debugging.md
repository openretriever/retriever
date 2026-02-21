---
title: "Debugging Pipelines: `Pipeline.run()` vs `Pipeline.step()`"
---

# Debugging Pipelines: `Pipeline.run()` vs `Pipeline.step()`

Retriever intentionally exposes **two** execution surfaces:

- `Pipeline.run(...)`: execute a validated pipeline on a runtime backend (multiprocessing / dora).
- `Pipeline.step(...)`: execute a pipeline **in-process**, one discrete step at a time, for debugging.

This note explains the design, semantics, and limitations so the behavior is predictable.

---

## 1) `Pipeline.run(...)` (backend execution)

`Pipeline.run(...)` is the production-facing API:

- validates the authored graph to `IRStruct` internally (no explicit `validate(...)` needed in user code)
- starts a backend `ExecutionEngine`

### Blocking run

```py
pipe.run(backend="multiprocessing", duration=10.0, blocking=True)
```

### Async/non-blocking run

```py
engine = pipe.run(backend="multiprocessing", blocking=False)
# ... do other work ...
engine.stop()
```

Notes:
- `blocking=False` returns immediately; you **must** stop the engine manually to avoid orphan processes.
- `build=True` runs via an `ExecutionGraph` (grouping/placement) before execution; the default is `build=False`.

---

## 2) `Pipeline.step(...)` (in-process debugging)

`Pipeline.step(...)` is a **debug tool**, not a backend:

- runs the pipeline inside the current Python process
- advances one discrete step of the runtime semantics: `sample → run → publish`
- returns a `StepResult` with what executed and snapshots of inputs/outputs

```py
res = pipe.step(dt=0.1)
print(res.executed)   # list of node_ids executed in this step
pipe.close_stepper()
```

### What the stepper actually builds

The in-process stepper:

1. Validates the pipeline to `IRStruct` (same validator as `Pipeline.run`).
2. Builds **in-memory channels** for each data edge.
3. Loads per-edge adapters from IR (so buffer sizes match runtime).
4. Uses the **same Flow instances** you authored (no re-import/re-instantiation).

Implementation lives in:

- `retriever/rt/stepper.py`
- `retriever/flow/pipeline.py` (`Pipeline.step/reset_stepper/close_stepper`)

### Flow lifecycle in the stepper

- The stepper calls `Flow.init()` lazily on the first `step()`.
- `Pipeline.reset_stepper()` calls `Flow.reset()` and clears all buffers.
- `Pipeline.close_stepper()` calls `Flow.finalize()` and drops the stepper.

Use `close_stepper()` when you’re done to release resources (e.g., camera handles).

---

## 3) Clock semantics in `Pipeline.step(...)`

`Pipeline.step()` is **not real-time**. It’s “one debug tick”.

For each node:

### `Rate(hz=...)` / `Tick(hz=...)`

- executes once per `step()`
- samples the configured `Rate.fields` (default: `["..."]` = sample all inputs)

### `Trigger(...)`

- executes **only if** a new arrival is observed on one of its trigger fields
- if multiple trigger fields have new arrivals, the first one in `Trigger.fields` wins for that step

### `Hybrid(hz=..., trigger=..., sample=...)`

- if a trigger field has a new arrival: executes as a trigger step (samples that field)
- otherwise executes once per step and samples `rate_fields`

Time parameters:

- `now=...`: pins the step timestamp.
- `dt=...`: advances an internal logical clock (useful for deterministic unit tests).
- if neither is provided, the stepper uses `time.time()`.

---

## 4) Event buffers, adapters, and sampling

Retriever’s runtime model is:

- each port is a discrete-time **EventStream**
- concretely stored as a finite `EventBuffer[T] = list[(timestamp, value)]`
- adapters sample buffers at time `now` to produce a value for the Flow input

In `Pipeline.step(...)`, buffers are in-process and the buffer size is derived from the adapter:

- `Latest(buffer_size=1)` keeps only the last item
- `Window(buffer_size=N, duration=...)` keeps N items and filters by timestamps

---

## 5) Limitations (current)

These are intentional constraints for the first version:

- Generator-based flows / services are **not supported** in `Pipeline.step(...)` yet.
  - The dora executor supports generators for RPC; the stepper currently raises an error if `Flow.run()` yields.
- Service edges (`_request_out`, `_response_in/...`) are ignored by the stepper for now.
- Cycles are executed once per step using the IR’s SCC groups order; this is a debug approximation.

If you need “real execution semantics”, use `Pipeline.run(...)` on a backend.

---

## 6) VS Code debugging workflow (recommended)

Because backend execution runs flows in **separate processes**, the simplest way to use the VS Code debugger
to step through Flow logic is to run **in-process** with `Pipeline.step()`.

### Minimal example

Use: `examples/tutorial/c_debug_and_replay/01_debug_stepper.py`

What to do:

1. Open `examples/tutorial/c_debug_and_replay/01_debug_stepper.py`
2. Set a breakpoint inside `DebugFlow.run()` (or any `Flow.run()` you want to inspect)
3. Start the VS Code debugger (F5) using the provided launch config (see `.vscode/launch.json`)

### Breaking on exceptions

The example can optionally raise an exception when the counter reaches a value:

```sh
python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --fail-at 3
```

In VS Code, enable “Break on exceptions” to stop exactly where the exception is raised inside `Flow.run()`.

### Debugging the perception detector (no camera)

If you want to debug the *real* `ColorDetector` logic from the dora perception demo without starting dora or a camera, use:

- `examples/tutorial/c_debug_and_replay/02_debug_perception_stepper.py`

It generates synthetic red/blue frames in-process and runs:

`SyntheticCamera → ColorDetector → PrintDetections`

Set breakpoints inside `ColorDetector.run()` / `_detect_from_mask()` and run under the debugger.

### Debugging the perception workflow (real camera)

If you want to debug the perception demo with an actual camera (while still staying in-process for VS Code breakpoints), use:

- `examples/tutorial/c_debug_and_replay/03_debug_perception_stepper_real_camera.py`

This runs:

`CameraSource (real) → ColorDetector → DisplayFlow`

Notes:
- By default it prints to stdout without opening an OpenCV window.
- Pass `--show-window` to enable the GUI window.
- Defaults to a short run (10 steps); override with `--steps` / `--sleep`.
- `dt` is optional and only affects timestamps (not scheduling). Pass `--dt` to force a fixed logical step.

### Interpreter note (Pixi)

If you use Pixi, the interpreter usually lives at:

`./.pixi/envs/default/bin/python`

Make sure VS Code is using that interpreter (or run the module via the launch config).

---

## 7) Recording + replay (rosbag-like workflow)

The stepper is useful for “record once, debug many times” workflows:

- record a short input sequence from real hardware
- replay it later in-process so you can set breakpoints inside `Flow.run()`

Library helpers (stepper-first):

- High-level: `Pipeline.record_to(handle, path, ...)` and `Pipeline.replay(handle, path=...)`.
- Low-level: `retriever.rt.stepper.EventStreamRecorder`, `save_event_buffer`/`load_event_buffer`, `replay_flow`.

Perception example:
- `examples/tutorial/c_debug_and_replay/04_record_replay_perception.py`:
  - Record: `python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record ...`
  - Replay: `python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay ...`

These examples store a gzip+pickle file by default at `logs/perception_recording.pkl.gz`.
