---
title: "Installation Guide"
---

# Installation Guide

Environment definitions (Pixi tasks/environments) live in `pixi.toml`. Pixi is the recommended path; the conda+uv section below is an alternative if you prefer a pure Python workflow.

## Supported Python

Python **3.11+** is required. Pixi pins `3.11.*` for the runtime environment; `pyproject.toml` declares `>=3.11`.

## Pixi vs uv (how they fit together)

- **Pixi** manages the whole dev/runtime environment (conda + PyPI) from `pixi.toml` and stores it under `.pixi/`.
  It uses `uv` internally for resolving/installing the PyPI portion.
- **uv** is great if you want a pure Python workflow (venv/conda + `uv pip install ...` / `uv sync ...`), but avoid
  mixing `uv sync` into a Pixi-managed environment unless you also update `pixi.toml`/`pixi.lock`.

## Runtime Environment (Pixi)

For running the actual Retriever codebase and examples, we use [Pixi](https://pixi.sh).

```sh
# Install pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Run a demo
pixi run demo-dora-simple
```

See `pixi.toml` for available environments and tasks.

## Manual Setup (conda + uv)

If you prefer a pure Python workflow without Pixi:

```sh
# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install the package with dev extras
pip install -e '.[dev]'
```
