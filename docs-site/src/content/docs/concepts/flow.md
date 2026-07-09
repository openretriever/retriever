---
title: Flow
description: "The smallest unit of Retriever computation: a typed Python class with local state and a synchronous step method."
---

**What you'll learn:** how to write, run, and debug a `Flow` — a stateful causal stream function with typed ports and one synchronous `step()` — as plain Python, before any backend, camera, or robot is involved.

## The smallest shape

A Flow subclasses `Flow[Input, Output]` and overrides `step()`. Inputs and outputs are `@io` dataclasses; their fields are the graph ports.

```python
from retriever.flow import Flow, io

@io
class NumberInput:
    value: int

@io
class NumberOutput:
    result: int

class DoubleFlow(Flow[NumberInput, NumberOutput]):
    def step(self, input: NumberInput) -> NumberOutput:
        return NumberOutput(result=input.value * 2)
```

`@io` turns the class into a dataclass whose fields are all `Optional` and carry present/absent signal information. `Flow[NumberInput, NumberOutput]` is the type boundary Retriever checks: both parameters must be `@io` types (or `None` for a source or sink). `step()` is the local computation — synchronous, and deterministic whenever its input and local state are.

## Run it like ordinary Python

A Flow is callable directly. No pipeline, no clock, no event loop:

```python
flow = DoubleFlow()
out = flow.step(NumberInput(value=5))
print(out)
assert out.result == 10
print("ports:", flow.input_type.__name__, "->", flow.output_type.__name__)
```

```text
NumberOutput(result=10)
ports: NumberInput -> NumberOutput
```

That direct call is the point. A Flow should be unit-testable and breakpoint-friendly on its own.

## Ports are optional; `_signals` says what arrived

Because `@io` makes every field `Optional`, a Flow can receive a partial input — some ports present, others not yet. `_signals` lists the fields that are actually set, so `step()` can branch on what it got instead of assuming a full observation.

```python
print("empty  _signals:", NumberInput()._signals)
print("filled _signals:", NumberInput(value=7)._signals)
```

```text
empty  _signals: []
filled _signals: ['value']
```

```python
class SignalAwareFlow(Flow[NumberInput, NumberOutput]):
    def step(self, input: NumberInput) -> NumberOutput:
        match input._signals:
            case ["value"]:
                return NumberOutput(result=input.value * 2)
            case _:
                return NumberOutput()  # nothing to do yet
```

## Local state with `reset()`

Runtime-local state — counters, buffers, model handles — belongs in `reset()`, not `__init__()`. The runtime calls `reset()` once when a run starts and again on `Pipeline.reset()`.

```python
class Counter(Flow[None, NumberOutput]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _) -> NumberOutput:
        self.count += 1
        return NumberOutput(result=self.count)

c = Counter()
c.reset()
print("counter:", [c.step(None).result for _ in range(3)])
```

```text
counter: [1, 2, 3]
```

Keep `__init__()` lightweight and serializable. Backends reconstruct a Flow from its `init_config()`, so put devices, sockets, and SDK clients in `reset()` and expose only plain constructor arguments through `init_config()`.

## Run the shipped example

```bash
retriever run basic-flow
```

This runs `examples/tutorial/a_flow_fundamentals/01_basic_flow.py`, which exercises both `DoubleFlow` and the `_signals` branch and prints each step.

## The same shape scales to robot policies

A VLA, VLM, planner, state estimator, or controller is still one Flow at the runtime boundary: one typed snapshot in, one typed output out. The model can be arbitrarily heavy inside `step()`; the graph owns timing and data handoff around it.

```python
from retriever.flow import Flow, io
from retriever.types.perception import Image2D, DetectionBatch
from retriever.types.language import Caption

@io
class SkillObs:
    image: Image2D
    detections: DetectionBatch
    goal: Caption

@io
class ActionChunk:
    actions: tuple[float, ...]
    progress: float

class VLAFlow(Flow[SkillObs, ActionChunk]):
    def __init__(self, policy):
        self.policy = policy

    def reset(self) -> None:
        self.last_chunk = None

    def step(self, obs: SkillObs) -> ActionChunk:
        actions, progress = self.policy(obs.image, obs.detections, obs.goal)
        self.last_chunk = ActionChunk(actions=tuple(actions), progress=progress)
        return self.last_chunk
```

## Put timing in the Pipeline, not the Flow

A Flow never decides when it runs. That belongs to the graph. You attach a clock with `@` and declare how each edge is sampled with `sync=`:

```python
from retriever.flow import Latest, Pipeline, Rate, Trigger
from examples.shared.perception_flows import CameraSource, ColorDetector, DisplayFlow

pipe = Pipeline("tutorial.perception")
with pipe:
    camera   = CameraSource(use_real_camera=False) @ Rate(hz=30)
    detector = ColorDetector(min_confidence=0.6)    @ Trigger("image")
    display  = DisplayFlow(display="stdout")         @ Rate(hz=3)

    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display, sync=Latest())
```

This split is the whole design: a Flow owns local computation; the graph owns when the Flow wakes up and which upstream record it consumes. Keep out of a Flow anything that belongs to the graph or runtime — do not start a private event loop for timing, do not read "whatever message last arrived" from global state, and do not fold backend launch, logging, or replay into the model logic.

Next: [Time and Sync](/concepts/time-and-sync/) shows how clocks and edge sync policies build the input passed to `step()`.
