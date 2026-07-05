---
title: "Quickstart"
---

# Quickstart

Start with the reliable visual smoke: `pixi run demo-webcam-detection-mock` runs the same color-detection graph with deterministic frames and stdout output. Then use `pixi run demo-webcam-detection` for live webcam input and Rerun/stdout visualization. This page then teaches the same core model with the smallest runnable graph.

<div class="rt-learning-panel">
  <h2>The five ideas</h2>
  <ol>
    <li><code>@io</code> defines typed message envelopes.</li>
    <li><code>Flow[I, O]</code> defines stateful node logic.</li>
    <li><code>flow @ clock</code> declares when a node runs.</li>
    <li><code>Pipeline.connect(..., sync=...)</code> declares how data crosses an edge.</li>
    <li><code>pipe.run(...)</code> executes; <code>pipe.step(...)</code> debugs in-process.</li>
  </ol>
</div>

## Minimal Runnable Graph

```python
from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io


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

Read it as a timed graph: `Source` wakes at 2 Hz, `Double` wakes when a new `value` arrives, and `Latest()` says exactly which upstream event the downstream Flow consumes.

## Step Before You Scale

Use backend execution when you want real scheduling behavior:

```python
pipe.run(backend="multiprocessing", duration=1.0)
pipe.run(backend="dora", duration=1.0)
```

Use the stepper when you want normal Python breakpoints and deterministic inspection:

```python
result = pipe.step(dt=0.5)
print(result.executed)
pipe.close_stepper()
```

This split is intentional: debug the graph in one process first, then move the same graph to a backend.

## First Things To Run

=== "See something"

    ```bash
    pixi run demo-webcam-detection-mock
    pixi run demo-webcam-detection
    ```

    The mock command is the first smoke: no camera permission and no GUI requirement. The live command runs `camera -> color detector -> display` with a real webcam by default. Show red or blue objects to the camera; Rerun opens when available and stdout is the fallback.

=== "Learn the API"

    ```bash
    pixi run demo-basic-flow
    pixi run demo-adapter-connection
    pixi run demo-rt-execution
    pixi run demo-stepper
    ```

=== "Record and replay"

    ```bash
    pixi run demo-webcam-record
    pixi run demo-webcam-replay-rrd
    ```

## Rules Of Thumb

- Define public Flow inputs and outputs with `@io`.
- Keep Flow logic in `step(...)`; put timing in clocks and edge sync policies.
- Start with `Rate`, `Trigger`, and `Latest`; reach for advanced policies only when a concrete robot handoff needs them.
- Use `Pipeline.step(...)` before debugging multiprocessing or dora execution.

## Next Pages

<div class="rt-doc-map">
  <a href="/guide_flow/"><strong>Flow Guide</strong><span>Typed IO, Flow classes, clocks, sync, and wiring.</span></a>
  <a href="/tutorials/"><strong>Tutorial Tracks</strong><span>Ordered runnable lessons.</span></a>
  <a href="/guide_runtime/"><strong>Runtime Guide</strong><span>Validation, IR, execution, and backends.</span></a>
  <a href="/examples/"><strong>Example Gallery</strong><span>Core runtime examples plus the Golden applied examples handoff.</span></a>
</div>

??? note "Backend and visualization variants"
    Use these after the basic path is clear:

    ```bash
    pixi run demo-webcam-detection-mp-rerun
    pixi run demo-webcam-detection-dora-rerun
    pixi run demo-webcam-window
    pixi run demo-webcam-replay-mcap
    ```

    The Dora demo tasks request a fresh runtime by default. If you run Dora manually and hit a stale coordinator or schema/version mismatch, restart Dora and rerun the task.
