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

# Run a tutorial demo (auto-resolves env, streams to Rerun)
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

Then run tutorials directly:

```bash
python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend multiprocessing
```

## Dora Notes

If `dora` reports stale coordinator/state errors, kill stale processes and retry:

```bash
pkill -9 dora || true
pixi run demo-webcam-detection
```

## Where To Go Next

- Tutorial index: `docs/tutorials/index.md`
- Runtime handbook: `docs/handbook.md`
- Debugging guide: `docs/guides/debugging.md`
