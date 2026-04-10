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

macOS / Linux:

```sh
curl -fsSL https://pixi.sh/install.sh | bash
pixi install
pixi run demo-stepper
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
pixi install
pixi run demo-stepper
```

Once the runtime is installed, the first live-camera-or-mock follow-up is:

```sh
pixi run demo-webcam-stepper
```

If no webcam is available, the tutorial camera source falls back to mock frames so the command still exercises the perception path.

See `pixi.toml` for available environments and tasks.

## Manual Setup (conda/venv + uv)

If you prefer a pure Python workflow without Pixi:

macOS / Linux:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e '.[dev]'
```
