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

    def run(self, _):  # type: ignore[override]
        self.count += 1
        return Number(value=self.count)


class Double(Flow[Number, Doubled]):
    def run(self, input: Number) -> Doubled:
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
pipe.run(backend="dora", duration=1.0)
```

### Debugging

Use `step(...)` when you want breakpoints inside `Flow.run(...)`:

```python
result = pipe.step(dt=0.5)
print(result.executed)
pipe.close_stepper()
```

`step(...)` runs in the current Python process. Start here before debugging a multiprocessing or dora run.

## The Three Rules That Matter Most

1. Always define public flow inputs and outputs with `@io`.
2. Always provide `sync=...` on `pipe.connect(...)`, or set a global default with `retriever.init(default_sync=Latest())`.
3. Start with `Rate` and `Trigger`; reach for more advanced clocks or adapters only when you have a concrete need.

## Try The Camera Path

If you want something visual right away, use the perception tutorial series.

### 1. Run the Dora camera demo

```bash
pixi run demo-webcam-detection
```

This runs `camera -> detector -> display` with a real camera when available and falls back to a mock pattern otherwise.

If Dora reports a stale coordinator or schema/version mismatch, restart Dora and retry:

```bash
pkill -9 dora || true
pixi run demo-webcam-detection
```

### 2. Debug the same workflow in-process

Use this when you want breakpoints inside `Flow.run(...)` without Dora or multiprocessing getting in the way:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera --steps 20 --sleep 0.05
```

Add `--show-window` if you want the OpenCV display window.

### 3. Record and replay a short session

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
```

This is the shortest path from live sensing to deterministic replay.

## What To Read Next

- [Install](getting_started/install.md)
- [Flow Guide](guide_flow.md)
- [Runtime Guide](guide_runtime.md)
- [Debugging](guides/debugging.md)
- [Track A: Flow Fundamentals](tutorials/track_a_flow_fundamentals.md)
