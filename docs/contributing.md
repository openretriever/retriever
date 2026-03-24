---
title: "Contributing"
---

# Contributing

This repo is early-stage and moves fast. Keep PRs small, include tests when it makes sense, and update docs when behavior/setup changes.

## Prerequisites

- Python 3.11 (current tested baseline for the runtime repo)
- Pixi (recommended) or uv/pip
- Git

## Setup

1) Set up an environment by following `docs/install.md`.

2) Install dev tooling (ruff/black/mypy/pytest/pre-commit) inside the Pixi env:

```bash
pixi run python -m pip install -e '.[dev]'

# Optional: if you prefer uv in your own venv/conda env:
# uv pip install -e '.[dev]'
```

3) Enable pre-commit and run a quick check:

```bash
pixi run pre-commit install
pixi run pre-commit run --all-files
pixi run python -m pytest tests/core -q
```

## Workflow

- Branch naming: `<type>/<short-description>-<YYYY-MM-DD>` (e.g. `bugfix/dora-yaml-2025-12-15`)
- Before pushing: run `pixi run ruff check .`, `pixi run black .`, `pixi run mypy src/retriever`, `pixi run python -m pytest`
- Open a PR with: what/why/how-tested, and any follow-ups

## Documentation

- Docs are in `docs/` and served by MkDocs (`mkdocs.yml`).
- Local preview: `mkdocs serve`
