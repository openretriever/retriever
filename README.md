<div align="center">
  <a href="https://github.com/openretriever/retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg" alt="Retriever logo"></a>
</div>

# 🐕 <span style="background: linear-gradient(45deg, #e96443 0%, #904e95 25%, #e65c00 50%, #f9d423 75%, #fc00ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: bold; font-size: 1.1em;">**Retriever**</span>

## **Building Modular Closed-loop Robot Agents with Explicit Time**

<div align="center">

<p>A programming framework for building closed-loop robot systems whose perception, reasoning, and control can run together easily.</p>

<p>
  <a href="https://openretriever-docs.pages.dev/"><img alt="Docs" src="https://img.shields.io/badge/Docs-open-0f766e?style=for-the-badge"></a>
  <a href="https://openretriever.org/"><img alt="Website" src="https://img.shields.io/badge/Website-openretriever.org-111827?style=for-the-badge"></a>
  <a href="https://github.com/openretriever/retriever"><img alt="Runtime code" src="https://img.shields.io/badge/Runtime-code-111827?style=for-the-badge&logo=github"></a>
  <a href="https://github.com/openretriever/golden-retriever"><img alt="Examples" src="https://img.shields.io/badge/Examples-Golden-92400e?style=for-the-badge&logo=github"></a>
  <img alt="Paper arXiv coming soon" src="https://img.shields.io/badge/Paper%20%2F%20arXiv-coming%20soon-64748b?style=for-the-badge">
  <img alt="Discord coming soon" src="https://img.shields.io/badge/Discord-coming%20soon-64748b?style=for-the-badge&logo=discord">
</p>

</div>

---

Retriever is the **core/runtime** package for typed, multi-rate robot pipelines. Robot applications rarely run as one neat synchronous loop: cameras, state estimators, planners, VLMs, VLAs, controllers, operators, and logs all update at different rates. Retriever makes those timing boundaries explicit while keeping the authoring model close to normal Python.

Use Retriever when a robot system needs:

- **Closed loops**: perception, memory, planning, control, monitoring, and even environment wrappers can live in one cyclic graph.
- **Explicit timing**: each `Flow` declares when it runs, and each edge declares how data is sampled before `step(...)` executes.
- **Debuggable execution**: run the graph on a backend, or step it in-process with normal Python breakpoints.
- **Portable backends**: author one typed graph, then run it in-process, with multiprocessing, or on a distributed backend.
- **Reusable components**: typed payloads, registries, and Hub surfaces make robot software easier to publish and compose.

System-level robot integrations, simulator stacks, and heavier model packages belong in companion repositories such as [`openretriever/golden-retriever`](https://github.com/openretriever/golden-retriever). This repository stays focused on the runtime core.

## Canonical Runtime Workflow

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

The public PyPI distribution target is `retriever-core`; the Python import package is `retriever`. The planned package install path is:

```bash
python -m pip install retriever-core
```

For demos and development before the release package is finalized, use the Pixi/source-checkout path below.

For local development and demos, use Pixi. The first visual demo is webcam color detection:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
pixi run demo-webcam-detection
```

`demo-webcam-detection` runs `camera -> color detector -> display` in-process, requests a real webcam by default, and uses `--visualize auto` so Rerun is used when available and stdout is used otherwise. Hold red or blue paper/objects in front of the camera to see detections. If a camera is not available, rerun the module directly with `--camera-mode mock`.

Useful follow-up commands:

```bash
pixi run demo-basic-flow
pixi run demo-rt-execution
pixi run demo-stepper
pixi run demo-webcam-record
```

## Documentation Path

Start here:

- [Quickstart](docs/quickstart.md) — the shortest runnable introduction.
- [Handbook](docs/handbook.md) — the canonical runtime handbook.
- [Install Guide](docs/getting_started/install.md) — Pixi, pip/uv, and backend setup notes.
- [Architecture](docs/architecture.md) — runtime layers, IR, clocks, and backends.
- [Tutorials](docs/tutorials/index.md) — runnable tutorial tracks.
- [API Reference](docs/API.md) — public API surface.
- [Release Checklist](RELEASE.md) — launch and package publishing checklist.

The hosted docs target is [openretriever-docs.pages.dev](https://openretriever-docs.pages.dev/).

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

## Ecosystem Boundary

The intended public split is:

- **Core runtime**: this repository, published as `retriever-core` and imported as `retriever`.
- **Examples and integrations**: [`openretriever/golden-retriever`](https://github.com/openretriever/golden-retriever).
- **Project website**: [openretriever.org](https://openretriever.org/).
- **Paper / arXiv**: research writeup, link pending.
- **Community**: Discord or similar community link, planned.

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

See [docs/contributing.md](docs/contributing.md) for development workflow and QA details.

## License

Retriever is licensed under the Apache License 2.0 (`Apache-2.0`). See [LICENSE](LICENSE) for the full license text and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for bundled third-party JavaScript notices.
