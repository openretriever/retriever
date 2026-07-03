---
title: Flow
---

# Flow

A Flow is the unit of robot computation in Retriever. The easiest way to read it is as an ordinary Python class with a synchronous `step(...)` method.

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
    def __init__(self, model):
        self.model = model
        self.last_chunk = None

    def step(self, obs: SkillObs) -> ActionChunk:
        chunk = self.model.plan(obs.image, obs.state, obs.goal)
        self.last_chunk = chunk
        return chunk
```

The runtime can call this Flow directly while debugging, or place it inside a Pipeline when you need clocks, stream synchronization, visualization, replay, and backend execution.

```python
chunk = vla_flow.step(obs)
# or, when using the callable convenience:
chunk = vla_flow(obs)
```

## Why it stays synchronous

Retriever does not ask every user module to become an async actor. User code implements the local computation. The graph declares the timing around it: when this Flow runs, what input snapshot it consumes, and what output stream it emits.
