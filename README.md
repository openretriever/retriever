<div align="center">
  <a href="https://github.com/linfeng-z/Retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg"></a>
</div>



# 🐕 Retriever

**Retriever: a type-safe runtime for robotics dataflow pipelines**

This repository is evolving to focus on the **Retriever core/runtime**:

- Author pipelines as a typed graph (`FlowContext`)
- Compile to a backend-agnostic IR (`validate() → IRStruct`)
- Execute on a backend (`execute_ir()`): local multiprocessing or dora-rs

System-level pipelines, integrations (robots/sim), and heavy model stacks will live in a separate **Golden Retriever** (reference system) repository as part of an ongoing split.

> Tracking/docs: Notion page (internal) — https://www.notion.so/retriever-dev/Retriever-Dev-Homepage-bfd5d802e1f346ac81a1ea773f6418e9?pvs=4

---

## Canonical Runtime Workflow

`FlowContext → validate() → IRStruct → execute_ir()`

Minimal example:

```py
from dataclasses import dataclass
from retriever.core.flow import Flow, FlowContext, Rate, Latest, flow_io
from retriever.core.ir import validate
from retriever.core.rt import execute_ir

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

with FlowContext("demo") as ctx:
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    src.then(add, sync=Latest())

ir = validate(ctx)
execute_ir(ir, backend="multiprocessing", duration=1.0)
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

## Development

- Development workflow, pre-commit hooks, and QA steps: `docs/contributing.md`

## Documentation

Docs live in `docs/` (served via MkDocs):

- Runtime user guide: `docs/guide_runtime.md`
- Architecture: `docs/architecture.md`
- Install: `docs/install.md`
