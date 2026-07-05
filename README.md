<div align="center">
  <a href="https://openretriever.org/"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg" alt="Retriever logo"></a>
</div>

# 🐕 <span style="background: linear-gradient(45deg, #e96443 0%, #904e95 25%, #e65c00 50%, #f9d423 75%, #fc00ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: bold; font-size: 1.1em;">**Retriever**</span>

## **Building Modular Closed-loop Robot Agents with Explicit Time**

<div align="center">

<p>A programming framework for building closed-loop robot systems whose perception, reasoning, and control can run together easily.</p>

<p>
  <a href="https://openretriever-docs.pages.dev/"><img alt="Docs" src="https://img.shields.io/badge/Docs-open-0f766e?style=for-the-badge"></a>
  <a href="https://openretriever.org/"><img alt="Website" src="https://img.shields.io/badge/Website-openretriever.org-111827?style=for-the-badge"></a>
  <a href="https://github.com/openretriever/retriever"><img alt="Runtime source" src="https://img.shields.io/badge/Source-GitHub-111827?style=for-the-badge&logo=github"></a>
  <a href="https://retriever-space.pages.dev/"><img alt="Golden examples" src="https://img.shields.io/badge/Golden-Examples-f97316?style=for-the-badge"></a>
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

System-level robot integrations, simulator stacks, and heavier model packages belong in the applied examples layer: [GoldenRetriever](https://retriever-space.pages.dev/) and Retriever Hub packs. This repository stays focused on the runtime core.

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

The current working path is source checkout plus Pixi because the examples and visualization assets live in the repository:

```bash
git clone https://github.com/openretriever/retriever
cd retriever
pixi install
pixi run demo-webcam-detection-mock
```

The public PyPI distribution target is `retriever-core`; the Python import package is `retriever`. After `retriever-core==0.0.1` resolves from PyPI, the minimal runtime install is:

```bash
python -m pip install retriever-core
```

For repository demos, use Pixi because it includes example files and optional visualization dependencies. Start with the deterministic color-detection smoke, then run the live webcam visual demo:

```bash
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
pixi run demo-webcam-detection-mock
pixi run demo-webcam-detection
```

`demo-webcam-detection-mock` runs `camera -> color detector -> display` with
synthetic frames and stdout, so it works on headless machines and in agent
runs. `demo-webcam-detection` requests a real webcam and uses `--visualize auto`
so Rerun is used when available and stdout is used otherwise. Hold red or blue
paper/objects in front of the camera to see detections.

Useful follow-up commands:

```bash
pixi run demo-basic-flow
pixi run demo-rt-execution
pixi run demo-stepper
pixi run demo-webcam-record
```

## Documentation Path

The hosted Starlight docs are the public docs front door:

- [Overview](https://openretriever-docs.pages.dev/) — recommended path.
- [Install](https://openretriever-docs.pages.dev/getting-started/install/) — package target and source-checkout commands.
- [Visual Quickstart](https://openretriever-docs.pages.dev/getting-started/visual-quickstart/) — mock smoke, webcam color detection, and Rerun.
- [Examples and Results](https://openretriever-docs.pages.dev/tutorials/examples-and-results/) — commands paired with expected output.
- [Debug and Visualize](https://openretriever-docs.pages.dev/tutorials/debug-and-visualize/) — graph render, stepper, record, and replay.
- [Golden Examples](https://retriever-space.pages.dev/) — maintained robot-facing examples, type packs, simulator/visualization lanes, and Hub-pack candidates after the core quickstart.
- [Golden Example Catalog](https://retriever-space.pages.dev/examples/) — applied perception, memory, language, composition, simulation, visualization, and typing guides.

The repository `docs/` tree remains available for deeper source-local reference
and release maintenance.

Source code lives at [github.com/openretriever/retriever](https://github.com/openretriever/retriever). GoldenRetriever source lives at [github.com/openretriever/golden-retriever](https://github.com/openretriever/golden-retriever), but most users should start from the hosted [Golden docs](https://retriever-space.pages.dev/).

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
- **Golden examples**: [GoldenRetriever](https://retriever-space.pages.dev/) for robot-facing examples and pack candidates.
- **Project website**: [openretriever.org](https://openretriever.org/).

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

Final external launch check before a public release announcement:

```bash
pixi run public-surface-check
```

See [docs/contributing.md](docs/contributing.md) for development workflow and QA details.

## License

Retriever is licensed under the Apache License 2.0 (`Apache-2.0`). See [LICENSE](LICENSE) for the full license text and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for bundled third-party JavaScript notices.
