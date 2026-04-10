---
title: "Quickstart"
---

# Quickstart

This page is the shortest path to the core Retriever runtime ideas.

If you only want the essentials, learn these five things:

1. `@io` defines typed message envelopes.
2. `Flow[I, O]` defines node logic.
3. `flow @ clock` decides when a node runs.
4. `Pipeline.connect(..., sync=...)` wires nodes and declares sampling behavior.
5. `pipe.run(...)` is for backend execution; `pipe.step(...)` is for in-process debugging.

## Minimal Runnable Example

```python
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class Number:
    value: int


@io
class Doubled:
    value: int


class Source(Flow[None, Number]):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return Number(value=self.count)


class Double(Flow[Number, Doubled]):
    def step(self, input: Number) -> Doubled:
        return Doubled(value=input.value * 2)


pipe = Pipeline("quickstart")
source = Source() @ Rate(hz=2)
double = Double() @ Trigger("value")
pipe.connect(source, double, sync=Latest())

pipe.run(backend="multiprocessing", duration=1.0)
```

## What This Example Means

- `@io` turns a simple annotated class into a runtime envelope with typed ports.
- `Flow[None, Number]` means the source emits `Number` and does not consume a typed input.
- `Rate(hz=2)` means the source runs periodically at 2 Hz.
- `Trigger("value")` means the downstream flow runs when a new `value` arrives.
- `sync=Latest()` means the downstream reads the newest available event from its input buffer.

## The Two Execution Modes

### Full execution

Use `run(...)` when you want real backend behavior:

```python
pipe.run(backend="multiprocessing", duration=1.0)
# Use backend="dora" when you explicitly want the dora runtime.
```

### Debugging

Use `step(...)` when you want breakpoints inside `Flow.step(...)`:

```python
result = pipe.step(dt=0.5)
print(result.executed)
pipe.close_stepper()
```

`step(...)` runs in the current Python process. Start here before debugging a multiprocessing or dora run.

## First Live Camera + Recording Workflow

Once the minimal example makes sense, use the tutorial perception path:

```bash
pixi run demo-webcam-stepper
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
pixi run demo-webcam-replay-mcap
```

What to expect:

- If a real webcam is available, Retriever captures from it.
- If no webcam is available, the tutorial camera source falls back to mock frames so the record/replay path still works.
- `stdout` replay is the documented default across macOS, Linux, and Windows.
- Use `--show-window` or `--visualize rerun` only on local desktop sessions where GUI viewers are available.
- If camera index `0` is not the right device, run the underlying module with `--camera-index N`.

This is the shortest public path that exercises:

- live perception with `Pipeline.step(...)`
- persisted `.rrd` recording
- mirrored `.mcap` recording
- deterministic replay from either artifact

## Next Reusable-Surface Example

When you want to package a pipeline and reuse it as a stage in a larger graph:

```bash
pixi run demo-composable-pipelines
```

See [Track G: Operations and Interfaces](tutorials/track_g_operations_interfaces.md) after the quickstart.

## The Three Rules That Matter Most

1. Always define public flow inputs and outputs with `@io`.
2. Always provide `sync=...` on `pipe.connect(...)`, or set a global default with `retriever.init(default_sync=Latest())`.
3. Start with `Rate` and `Trigger`; reach for more advanced clocks or adapters only when you have a concrete need.

## What To Read Next

- [Install](getting_started/install.md)
- [Flow Guide](guide_flow.md)
- [Runtime Guide](guide_runtime.md)
- [Debugging](guides/debugging.md)
- [Tutorial Tracks](getting_started/tutorials.md)
