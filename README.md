<div align="center">
  <a href="https://github.com/linfeng-z/Retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg"></a>
</div>



# 🐕 <span style="background: linear-gradient(45deg, #e96443 0%, #904e95 25%, #e65c00 50%, #f9d423 75%, #fc00ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: bold; font-size: 1.1em;">**Retriever**</span>: *Robot Decision-Making Runtime with Functional Composition*

<!-- **Retriever: a type-safe runtime for robotics dataflow pipelines** -->

This repository is evolving to focus on the **Retriever core/runtime**:

- Author pipelines as a typed graph (`Pipeline` / `FlowContext`)
- Verify/compile to a backend-agnostic IR (done automatically at runtime)
- Execute on a backend (`Pipeline.run(...)`): local multiprocessing or dora-rs
- Debug step-by-step in-process (`Pipeline.step(...)`)

System-level pipelines, integrations (robots/sim), and heavy model stacks will live in a separate **Golden Retriever** (reference system) repository as part of an ongoing split.

---

## Canonical Runtime Workflow

`Pipeline (or FlowContext) → validate() → IRStruct → (optional) build_execution() → execute_ir()`

Minimal example:

```py
from dataclasses import dataclass
from retriever.core.flow import Flow, Pipeline, Rate, Latest, flow_io
@flow_io
@dataclass
class SrcOut:
    value: int


@flow_io
@dataclass
class AddOut:
    value: int


class Source(Flow[None, SrcOut]):
    def run(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def run(self, input: SrcOut) -> AddOut:
        return AddOut(value=input.value + 1)

pipe = Pipeline("demo")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)
pipe.connect(src, add, sync=Latest())

pipe.run(backend="multiprocessing", duration=1.0)
```

More details: `docs/guide_runtime.md`

## Setup (overview)

Use Python 3.10–3.12 (avoid 3.14; some deps lack wheels).

Quick start with [Pixi](https://pixi.sh):

```sh
curl -fsSL https://pixi.sh/install.sh | bash
pixi run demo-dora
```

If `dora` complains about version/schema, kill stale processes:

```sh
pkill -9 dora && pixi run demo-dora
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

- Runtime user guide: `docs/guide_runtime.md`
- Architecture: `docs/architecture.md`
- Install: `docs/install.md`
