<div align="center">
  <a href="https://github.com/linfeng-z/Retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg"></a>
</div>



# 🐕 <span style="background: linear-gradient(45deg, #e96443 0%, #904e95 25%, #e65c00 50%, #f9d423 75%, #fc00ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: bold; font-size: 1.1em;">**Retriever**</span>

## **Building Modular Closed-loop Robot Agents with Causal Functional Composition**

<!-- **Retriever: a type-safe runtime for robotics dataflow pipelines** -->

This repository is evolving to focus on the **Retriever core/runtime**:

- Author pipelines as a typed graph (`Pipeline`)
- Verify/compile to a backend-agnostic IR (done automatically at runtime)
- Execute on a backend (`Pipeline.run(...)`): local multiprocessing or dora-rs
- Debug step-by-step in-process (`Pipeline.step(...)`)

System-level pipelines, integrations (robots/sim), and heavy model stacks will live in a separate **Golden Retriever** (reference system) repository as part of an ongoing split.

---


## Canonical Runtime Workflow

Critical ideas:

- `@io` defines typed message envelopes.
- `Flow[I, O]` defines node logic.
- `flow @ clock` decides when a node runs.
- `Pipeline.connect(..., sync=...)` wires nodes and declares sampling behavior.
- `pipe.run(...)` is for backend execution; `pipe.step(...)` is for in-process debugging.

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

    def run(self, _):  # type: ignore[override]
        self.count += 1
        return Number(value=self.count)


class Double(Flow[Number, Doubled]):
    def run(self, input: Number) -> Doubled:
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

Short docs path:

- Quickstart: `docs/quickstart.md`
- Handbook: `docs/handbook.md`
- Runtime guide: `docs/guide_runtime.md`

## Setup (overview)

Use Python 3.11 for the pinned runtime environment in this repo.

Quick start with [Pixi](https://pixi.sh):

```sh
curl -fsSL https://pixi.sh/install.sh | bash
pixi run demo-dora
```

`pixi.lock` is multi-platform (osx-arm64, linux-64). Commit it for reproducible installs; other platforms can re-lock after adding the platform to `pixi.toml` and running `pixi install`.

Pixi manages its own env. If you prefer `uv`/`pip`, use a separate conda/venv to avoid mixing managers. Pixi installs the PyPI portion using `uv` internally; you usually don't need to run `uv` yourself when using Pixi.

Full installation (Pixi/conda/uv), dora CLI notes, and troubleshooting: `docs/install.md`.

Golden/system split prep:

- Runtime/core manifests: `pyproject.toml`, `pixi.toml`
- Golden/system templates (to be moved to a separate repo): `pyproject-golden.toml`, `pixi-golden.toml`

## Development

- Development workflow, pre-commit hooks, and QA steps: `docs/contributing.md`

## Documentation

Docs live in `docs/` (served via MkDocs):

- Runtime handbook (canonical): `docs/handbook.md`
- Quickstart: `docs/quickstart.md`
- Architecture: `docs/architecture.md`
- Install: `docs/install.md`
- Advanced Examples: `examples/advanced/`
  - **Skill Switching**: Dynamic behavior switching pattern with **Fan-in** support (`examples/advanced/skill_switching/`)
  - **Native Controller**: Rust/C++ native extension bindings (`examples/advanced/native_controller/`)
  - **TWIST2 Simulation**: MuJoCo humanoid robot at 1000Hz physics + 50Hz policy (`examples/advanced/twist2_simulation/`)

## Roadmap

Recent features:
- **Main Thread Flow** (`@gui_flow`): Run flows in main thread for native GUI support (MuJoCo viewers, Qt, etc.)
  - See: `examples/advanced/twist2_simulation/` for usage example
