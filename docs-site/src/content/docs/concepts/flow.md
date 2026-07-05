---
title: Flow
description: "The smallest unit of Retriever computation: a typed Python class with local state and a synchronous step method."
---

A **Flow** is the smallest unit of computation in Retriever. Read it as a normal Python object with typed inputs, typed outputs, local state, and one synchronous `step(...)` method.

Run the smallest example first:

```bash
pixi run demo-basic-flow
```

## The Smallest Shape

```python
from retriever.flow import Flow, io

@io
class NumberInput:
    value: int

@io
class NumberOutput:
    result: int

class DoubleFlow(Flow[NumberInput, NumberOutput]):
    def step(self, inp: NumberInput) -> NumberOutput:
        return NumberOutput(result=inp.value * 2)
```

The important parts are deliberately plain:

| Part | Meaning |
| --- | --- |
| `@io` classes | The public input/output contract. Fields become graph ports and can carry missing/present signal information. |
| `Flow[Input, Output]` | The type boundary checked by Retriever. Inputs and outputs must be `@io` types, or `None` for source/sink flows. |
| `step(...)` | The local computation. It is synchronous, deterministic when its inputs and local state are deterministic, and easy to call in a debugger. |

## Debug It Like Ordinary Python

```python
flow = DoubleFlow()
out = flow.step(NumberInput(value=5))
assert out.result == 10
```

That direct call is intentional. Before a backend, camera, simulator, or robot enters the picture, a Flow should be testable as a local Python object.

## Add Local State With `reset()`

Use `reset()` for runtime-local state that should be initialized when a run starts or when a pipeline is reset.

```python
class Counter(Flow[None, NumberOutput]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _) -> NumberOutput:
        self.count += 1
        return NumberOutput(result=self.count)
```

Keep `__init__()` lightweight and serializable when you want backend execution. If a Flow needs constructor arguments on another backend, expose them through `init_config()`.

## The Same Shape Scales To Robot Policies

A robot policy, VLA, VLM, planner, state estimator, or controller is still just a Flow at the runtime boundary. The heavy model logic can be inside the class; the graph owns timing and data handoff around it.

<details>
<summary>VLA-shaped Flow example</summary>

```python
from retriever.flow import Flow, io

@io
class SkillObs:
    image: CameraFrame
    state: RobotState
    goal: SkillCommand

@io
class ActionChunk:
    actions: list[RobotAction]
    progress: float

class VLAFlow(Flow[SkillObs, ActionChunk]):
    def __init__(self, encoder, policy):
        self.encoder = encoder
        self.policy = policy

    def reset(self) -> None:
        self.last_chunk = None

    def step(self, obs: SkillObs) -> ActionChunk:
        features = self.encoder.encode(obs.image, obs.state, obs.goal)
        actions, progress = self.policy.decode_action_chunk(features)
        chunk = ActionChunk(actions=actions, progress=progress)
        self.last_chunk = chunk
        return chunk
```

The model may be complex, but the Retriever-facing contract stays small: one typed snapshot in, one typed output out.
</details>

## Put Timing In The Pipeline

When timing matters, place the Flow in a `Pipeline` and declare clocks plus edge sync policies there.

```python
from retriever.flow import Latest, Pipeline, Rate, Trigger
from examples.shared.perception_flows import CameraSource, ColorDetector, DisplayFlow

pipe = Pipeline("tutorial.perception")
with pipe:
    camera = CameraSource(use_real_camera=False) @ Rate(hz=30)
    detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
    display = DisplayFlow(display="stdout") @ Rate(hz=3)

    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display, sync=Latest())
```

This separation is the core design choice: a Flow owns local computation; the graph owns when it wakes up and how upstream history is sampled before `step(...)` runs.

## What Not To Hide Inside A Flow

- Do not make every Flow start its own long-running event loop just to handle timing.
- Do not silently read "whatever latest message happened to arrive" from global state.
- Do not mix backend launch, logging, replay, and visualization into the model logic.

Those belong in Pipeline wiring, runtime execution, recording/replay, and graph visualization.

## Continue

<div class="card-grid">
  <a class="info-card" href="/concepts/time-and-sync/"><strong>Add time and sync</strong><span>Learn how clocks and event buffers build the aligned input passed to <code>step(...)</code>.</span></a>
  <a class="info-card" href="/tutorials/examples-and-results/"><strong>Run example outputs</strong><span>Compare the smallest Flow, local stepper, perception graph, HTML graph, and replay output.</span></a>
  <a class="info-card" href="/tutorials/debug-and-visualize/"><strong>Debug a graph</strong><span>Render the graph, step locally, record, and replay before blaming backend scheduling.</span></a>
</div>
