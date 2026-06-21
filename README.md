# Retriever

Retriever is a programming framework for building closed-loop robot systems whose perception, reasoning, and control can run together easily.

Robot applications rarely run as one neat synchronous loop. Cameras, state estimators, planners, VLMs, VLAs, controllers, operators, and logs all update at different rates. Retriever makes those timing boundaries explicit while keeping the authoring model close to normal Python: define a `Flow`, connect it in a `Pipeline`, choose how each edge samples data, then run the same graph in-process, with multiprocessing, or on a distributed backend.

## Why Retriever

Retriever is for robot systems that need more than a single `env.step()` loop:

- **Closed-loop by default**: perception, memory, planning, control, monitoring, and the environment can all live in one cyclic graph.
- **Explicit time and handoff**: each Flow has its own clock, and each edge declares how inputs are sampled before `step(...)` runs.
- **Debuggable execution**: run the full graph on a backend, or single-step it in-process with normal Python breakpoints.
- **Portable runtime boundary**: author once as a typed graph, then compile to a backend-agnostic IR for local or distributed execution.
- **Ecosystem-ready components**: shared types, registries, and Hub support make reusable robot components easier to publish and compose.

System-level robot integrations, simulator stacks, and heavier model packages should live in companion repositories. This repository contains the Retriever core/runtime.

## Core Concepts

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

The important pieces are small:

- `@io` defines typed message envelopes.
- `Flow[I, O]` defines node logic.
- `flow @ clock` declares when a node runs.
- `Pipeline.connect(..., sync=...)` declares how data crosses an edge.
- `Pipeline.run(...)` executes on a backend.
- `Pipeline.step(...)` runs in-process for debugging and replay.

## Install

Use Python 3.11 or newer.

```bash
pip install -e .
```

When installed from PyPI, the distribution name is expected to be `openretriever` while the Python package import remains `retriever`.

For the maintained development and demo environment, use Pixi:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
pixi run demo-basic-flow
```

Useful first commands:

```bash
pixi run demo-basic-flow
pixi run demo-rt-execution
pixi run demo-stepper
pixi run demo-webcam-detection
```

`demo-webcam-detection` requests a real camera by default. If a camera is not available, run the module directly with `--camera-mode mock`.

## Documentation Path

Start here:

- [docs/quickstart.md](docs/quickstart.md) — the shortest runnable introduction.
- [docs/handbook.md](docs/handbook.md) — the canonical runtime handbook.
- [docs/architecture.md](docs/architecture.md) — runtime layers, IR, clocks, and backends.
- [docs/tutorials/index.md](docs/tutorials/index.md) — runnable tutorial tracks.
- [docs/website_story.md](docs/website_story.md) — website/blog-ready project narrative and copy blocks.
- [RELEASE.md](RELEASE.md) — launch, docs deployment, and package publishing checklist.

Reference docs:

- `docs/guide_flow.md` — flows, clocks, adapters, and pipelines.
- `docs/guide_runtime.md` — Pipeline to IR to backend execution.
- `docs/guides/data_eventstream_v1.md` — event/data contracts.
- `docs/hub.md` — publishing and loading ecosystem modules.
- `docs/API.md` — API reference.

## Runtime Surfaces

Retriever has two execution modes on purpose:

```python
# Backend execution
pipe.run(backend="multiprocessing", duration=3.0)
pipe.run(backend="dora", duration=3.0)

# In-process debugging
result = pipe.step(dt=0.1)
print(result.executed)
pipe.close_stepper()
```

Backend execution is for realistic scheduling, process boundaries, and deployment behavior. In-process stepping is for debugging logic, replaying incidents, and making timing bugs inspectable with normal Python tools.

## Ecosystem Direction

Retriever is not just a runtime. The long-term goal is an ecosystem for reusable robot software:

- core runtime and typed temporal graph abstractions in this repo;
- examples and tutorials that teach the shortest path first;
- shared schema/type packages for common robot payloads;
- Hub and plugin surfaces for reusable flows and pipelines;
- companion packages for robots, simulators, datasets, and model backends;
- website/blog material that explains the system in public-facing language.

The release default is adoption-oriented: Apache-2.0 licensing, a small required dependency footprint, explicit third-party notices, and docs that avoid private project history.

## Development

```bash
pixi install
pixi run test
pixi run p0-release-readiness
```

Focused public-surface checks:

```bash
pixi run python -m pytest tests/core/test_public_surface_rt.py -q
pixi run python -m pytest tests/core/test_hub_ref_rt.py tests/core/test_hub_check_rt.py tests/core/test_hub_loader_rt.py tests/core/test_hub_use_rt.py -q
```

See `docs/contributing.md` for development workflow and QA details.

## License

Retriever is licensed under the Apache License 2.0 (`Apache-2.0`). See `LICENSE` for the full license text and `THIRD_PARTY_NOTICES.md` for bundled third-party JavaScript notices.
