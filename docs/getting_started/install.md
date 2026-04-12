---
title: "Installation Guide"
---

# Installation Guide

Use Python 3.11 for the current runtime stack.

Notes:
- Pixi currently pins Python `3.11.*` for the runtime environment.
- `pyproject.toml` also requires Python `>=3.11`.
- Treat 3.11 as the public, tested baseline for the core runtime docs and examples.

## Recommended: Pixi

Pixi is the default environment manager for this repo.

```bash
# Install pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Run a tutorial demo (auto-resolves env)
pixi run demo-webcam-detection
```

Useful follow-ups:

```bash
# Run tests
pixi run python -m pytest tests -q

# Open an interactive shell in the resolved env
pixi shell
```

## Alternative: venv + pip/uv

If you prefer a plain Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[demo,dora,recording]"
```

Optional extras:

```bash
# MCP / connector integration
python -m pip install -e ".[mcp]"
```

Then run tutorials directly:

```bash
python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend in-process --camera-mode real
```

## Dora Notes

The Dora demo tasks already request a fresh runtime. If `dora` still reports stale coordinator/state errors while you are running Dora manually, kill stale processes and retry:

```bash
pkill -9 dora || true
pixi run demo-webcam-detection-dora-rerun
```

## Where To Go Next

- Tutorial index: `docs/tutorials/index.md`
- Runtime handbook: `docs/handbook.md`
- Debugging guide: `docs/guides/debugging.md`
