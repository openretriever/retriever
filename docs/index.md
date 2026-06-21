---
title: "Retriever Framework"
slug: "intro"
---

# Retriever Framework

Retriever is a programming framework for building closed-loop robot systems whose perception, reasoning, and control can run together easily.

It is designed for robot applications that do not fit cleanly into one global loop: sensors stream, policies run at different rates, planners block, operators intervene, controllers need fresh state, and logs must be replayable. Retriever makes those temporal boundaries explicit while keeping the programming model close to ordinary Python classes.

## The Short Version

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

Read this as: each Flow has local state, each Flow declares when it runs, and each edge declares how upstream events are sampled before the downstream `step(...)` call.

## What To Learn First

1. Run `pixi run demo-basic-flow`.
2. Read `docs/quickstart.md`.
3. Read `docs/handbook.md` for the full runtime path.
4. Use `Pipeline.step(...)` before debugging backend execution.
5. Move to `docs/tutorials/index.md` when you want specific runnable lanes.

## Runtime Model

- `@io`: typed message envelopes.
- `Flow[I, O]`: stateful module logic.
- `Rate`, `Trigger`, `Tick`, `Hybrid`: local clocks for each Flow.
- `Latest` and other sync policies: deterministic edge sampling.
- `Pipeline`: graph authoring and validation.
- `IR`: backend-agnostic representation.
- `Pipeline.run(...)`: backend execution.
- `Pipeline.step(...)`: in-process debugging and replay.

## Why This Matters

A robot stack becomes hard to maintain when timing is hidden inside callbacks, queues, sleeps, and ad hoc threads. Retriever puts timing and data handoff in the graph itself, so the same system can be inspected, replayed, and moved across execution backends.

That is the core adoption story: normal Python authoring, explicit temporal semantics, and an ecosystem path for reusable robot components.

## Documentation Map

- [Quickstart](quickstart.md)
- [Runtime Handbook](handbook.md)
- [Architecture](architecture.md)
- [Tutorial Tracks](tutorials/index.md)
- [Flow Guide](guide_flow.md)
- [Runtime Guide](guide_runtime.md)
- [Hub](hub.md)
- [Website Story](website_story.md)
