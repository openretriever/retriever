# Retriever

Retriever is the runtime/core library for typed dataflow pipelines.

It provides:
- typed `@io` envelopes
- `Flow[I, O]` nodes with `step()` / `reset()`
- explicit pipeline authoring with `Pipeline`
- validation to IR / execution graphs
- backend execution with `multiprocessing` or explicit `dora`
- in-process stepping, recording, replay, and tutorial-friendly debugging

## Canonical runtime workflow

- author nodes with `Flow.step(...)`
- build graphs with `Pipeline.connect(...)`
- use `pipe.run(backend="multiprocessing", ...)` for normal execution
- use `pipe.step(...)` and `pipe.close_stepper()` for in-process debugging
- use `backend="dora"` explicitly when you want Dora parity or deployment

Minimal example:

```py
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

Debugging:

```py
result = pipe.step(dt=0.5)
print(result.executed)
pipe.close_stepper()
```

## Install

Use Python 3.11 for the pinned runtime environment in this repo.

Quick start with [Pixi](https://pixi.sh):

```sh
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
pixi run demo-stepper
```

Full installation and troubleshooting: `docs/getting_started/install.md`

## Documentation

- Quickstart: `docs/quickstart.md`
- Handbook: `docs/handbook.md`
- Runtime guide: `docs/guide_runtime.md`
- Execution guide: `docs/guide_execution.md`
- Flow guide: `docs/guide_flow.md`
- Tutorials entrypoint: `docs/getting_started/tutorials.md`
- Tutorial tracks + lecture packs: `docs/tutorials/index.md`

## Public examples

The public runnable examples in this repo live under `examples/tutorial/`:

- `a_flow_fundamentals/`
- `b_ir_and_execution/`
- `c_debug_and_replay/`
- `d_closed_loop_state_feedback/`
- `e_resource_and_sync/`
- `f_policy_backends/`
- `g_operations_interfaces/`
- `h_release_readiness/`

Useful launch points:

```sh
pixi run demo-stepper
pixi run demo-functional-fanin-fanout
pixi run demo-record-replay
pixi run demo-release-readiness
```
