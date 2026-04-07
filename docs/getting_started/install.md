---
title: "Installation Guide"
---

# Installation Guide

Environment definitions (Pixi tasks/environments) live in `pixi.toml`. Pixi is the recommended path; the conda+uv section below is an alternative if you prefer a pure Python workflow.

Use Python 3.11 for the current runtime stack.

Notes:
- Pixi currently pins Python `3.11.*` for the runtime environment.
- `pyproject.toml` also requires Python `>=3.11`.
- Treat 3.11 as the public, tested baseline for the core runtime docs and examples.

## Supported Python

Use Python 3.10–3.12 for the full stack. The runtime/core is pure-Python, but some optional “system” deps (e.g. Ray) may lag on newer Python versions.

## Pixi vs uv (how they fit together)

- **Pixi** manages the whole dev/runtime environment (conda + PyPI) from `pixi.toml` and stores it under `.pixi/`.
  It uses `uv` internally for resolving/installing the PyPI portion.
- **uv** is great if you want a pure Python workflow (venv/conda + `uv pip install ...` / `uv sync ...`), but avoid
  mixing `uv sync` into a Pixi-managed environment unless you also update `pixi.toml`/`pixi.lock`.

## Quick Start (Pip / Venv)

The documentation build and website are decoupled from `pixi` for simplicity. To build the docs locally:

```sh
# Create a venv (optional)
python -m venv .venv
source .venv/bin/activate

# Install docs dependencies
pip install -r doc_requirements.txt

# Run the build
./scripts/build_site.sh
```

## Runtime Environment (Pixi)

For running the actual Retriever codebase and examples, we use [Pixi](https://pixi.sh).

```sh
# Install pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Run a demo
pixi run demo-dora
```

See `pixi.toml` for available environments and tasks.

## Manual Setup (conda + uv)
...
(Rest of the file remains similar or can be simplified)
