<div align="center">

<a href="https://openretriever.org/"><img width="200" height="auto" src="assets/retriever-illustrative.jpeg" alt="Retriever logo"></a>

<br>

<a href="https://openretriever.org/"><img src="assets/retriever-wordmark.svg" alt="Retriever" width="300"></a>

### Building Modular Closed-loop Robot Agents with Explicit Time

<p>A Python runtime for building closed-loop robot systems whose perception, reasoning, and control can run together with explicit time, typed handoff, graph inspection, and replay.</p>

<p>
  <a href="https://retriever.build/"><img alt="Docs" src="https://img.shields.io/badge/Docs-open-0f766e?style=for-the-badge"></a>
  <a href="https://openretriever.org/"><img alt="Website" src="https://img.shields.io/badge/Website-openretriever.org-111827?style=for-the-badge"></a>
  <a href="https://github.com/openretriever/retriever"><img alt="Source" src="https://img.shields.io/badge/Source-GitHub-111827?style=for-the-badge&logo=github"></a>
  <br>
  <a href="https://golden.retriever.build/examples/"><img alt="GoldenRetriever examples" src="https://img.shields.io/badge/GoldenRetriever-examples-f97316?style=for-the-badge"></a>
  <a href="https://golden.retriever.build/hub/"><img alt="Hub packs" src="https://img.shields.io/badge/Hub-packs-9333ea?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-3b82f6?style=for-the-badge"></a>
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

System-level robot integrations, simulator stacks, and heavier model packages belong in the maintained reference examples layer: [GoldenRetriever](https://golden.retriever.build/examples/) and Retriever Hub packs. This repository stays focused on the runtime core.

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

The public package target is `retriever-core`; the Python import package and executable command are both `retriever`:

```bash
python -m pip install retriever-core
retriever --version
retriever init my-retriever-app --bootstrap-pixi
cd my-retriever-app
retriever run hello
```

For repository demos, clone the source checkout because the example files, graph renderers, and visualization assets live in the repository. With `retriever-core` installed, run everything through the `retriever` command:

```bash
git clone https://github.com/openretriever/retriever
cd retriever
retriever install --bootstrap-pixi
retriever run webcam-mock
retriever run webcam
```

`retriever run webcam-mock` runs `camera -> color detector -> display` with
synthetic frames and stdout, so it works on headless machines and in agent
runs. `retriever run webcam` requests a real webcam and uses `--visualize auto`
so Rerun is used when available and stdout is used otherwise. Hold red or blue
paper/objects in front of the camera to see detections.

Useful follow-up commands from the source checkout:

```bash
retriever run basic-flow
retriever run rt-execution
retriever run stepper
retriever run record
retriever tasks
```

`retriever run <name>` is the stable command surface for examples and diagnostics. Curated names (`webcam-mock`, `stepper`, `record`, …) are the public path; raw repository task names still work with `retriever run <task>` as a source-checkout escape hatch.

## Step And Checkpoint Graphs

Checkpointable graph debugging is a Python API, not a separate CLI namespace. Define the graph in Python, inspect or render its IR, then step it in-process with normal breakpoints and your own checkpoint artifact:

```python
import json
from pathlib import Path

pipe.validate()

for i in range(10):
    result = pipe.step(dt=0.1)
    checkpoint = {"now": result.now, "executed": result.executed}
    Path(f"checkpoint-{i:03d}.json").write_text(json.dumps(checkpoint, indent=2))

pipe.close_stepper()
```

Python is the executable source of truth. Saved IR/HTML is the portable graph description for inspection and reproducibility; executing directly from saved IR should remain a future, versioned contract rather than the default promise.

## Retriever Hub

Hub refs are ordinary strings: `{org}/{name}[:Export][@version]`. Use the CLI to validate the ref shape offline, inspect a module through the same loader as `hub.use(...)`, and locate the local cache:

```bash
retriever hub parse openretriever/hello-world:HelloFlow
retriever hub inspect openretriever/hello-world --json
retriever hub cache-dir
```

`hub inspect` may fetch from the Hub index and GitHub unless the module is already cached. Use `retriever --dry-run hub inspect <ref>` when you only want to check the ref shape without network access. In Python, load the same export with `from retriever import hub; hub.use("openretriever/hello-world:HelloFlow")`.

## Documentation Path

The hosted Starlight docs are the public docs front door:

- [Overview](https://retriever.build/) — recommended path.
- [Install](https://retriever.build/getting-started/install/) — package target and source-checkout commands.
- [Visual Quickstart](https://retriever.build/getting-started/visual-quickstart/) — mock smoke, webcam color detection, and Rerun.
- [Examples and Results](https://retriever.build/tutorials/examples-and-results/) — commands paired with expected output.
- [Debug and Visualize](https://retriever.build/tutorials/debug-and-visualize/) — graph render, stepper, record, and replay.
- [GoldenRetriever Overview](https://golden.retriever.build/) — GoldenRetriever as the applied examples and reference-pack layer.
- [GoldenRetriever Example Catalog](https://golden.retriever.build/examples/) — applied perception, memory, language, composition, simulation, visualization, and typing guides.

The repository `docs/` tree remains available for deeper source-local reference
and release maintenance.

Source code lives at [github.com/openretriever/retriever](https://github.com/openretriever/retriever). GoldenRetriever source lives at [github.com/openretriever/golden-retriever](https://github.com/openretriever/golden-retriever), but most users should start from the hosted [GoldenRetriever example catalog](https://golden.retriever.build/examples/).

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
- **GoldenRetriever examples**: [GoldenRetriever](https://golden.retriever.build/examples/) for robot-facing examples and pack candidates.
- **Project website**: [openretriever.org](https://openretriever.org/).

## Development

Contributor tasks run through the same `retriever` command from a source
checkout:

```bash
retriever install                     # set up the environment
retriever run test                    # full test suite
retriever run p0-release-readiness
retriever run public-surface-check    # external launch check before announcing
```

The source checkout uses [Pixi](https://pixi.sh) as its environment and task
backend, and `retriever run <task>` wraps it. For focused test subsets, run
pytest in the environment directly:

```bash
pixi run python -m pytest tests/core/test_public_surface_rt.py -q
pixi run python -m pytest tests/core/test_hub_ref_rt.py tests/core/test_hub_check_rt.py tests/core/test_hub_loader_rt.py tests/core/test_hub_use_rt.py -q
```

See [docs/contributing.md](docs/contributing.md) for the full development workflow.

## Clone and Stay in Sync

```bash
git clone https://github.com/openretriever/retriever
cd retriever
git pull   # normal pulls fast-forward
```

`main` is the canonical branch; a fresh clone and ordinary `git pull` are all you need.

## License

Retriever is licensed under the Apache License 2.0 (`Apache-2.0`). See [LICENSE](LICENSE) for the full license text and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for bundled third-party JavaScript notices.
