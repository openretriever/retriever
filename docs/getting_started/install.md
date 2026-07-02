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

# Run the first visual demo (auto-resolves env)
pixi run demo-webcam-detection
```

This uses a live webcam by default and detects red/blue objects. If camera access is unavailable, run the tutorial module directly with `--camera-mode mock`, or use `pixi run demo-basic-flow` for a pure-core API sanity check.

Useful follow-ups:

```bash
# Run tests
pixi run python -m pytest tests -q

# Open an interactive shell in the resolved env
pixi shell
```

## PyPI Distribution

The first public PyPI release target is `pyretriever==0.0.1`. Once that package is published, install the runtime distribution with:

```bash
python -m pip install pyretriever
python -c "import retriever; print(retriever.__file__)"
```

Until then, use Pixi or a source checkout.

## Alternative: source checkout with venv + pip/uv

Use this when you cloned the repository and want to run local examples from the checkout. The PyPI distribution name is `pyretriever`, and it installs the import package `retriever`; tutorial modules under `examples/` are source-checkout material unless you use a separate example bundle.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Optional extras:

```bash
# Local demos, recording, and dora backend support
python -m pip install -e ".[demo,recording,dora]"

# MCP / connector integration
python -m pip install -e ".[mcp]"
```

From a source checkout, run tutorials directly:

```bash
python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
python -m examples.tutorial.b_ir_and_execution.04_rt_execution
```

## Dora Notes

The Dora demo tasks already request a fresh runtime. If `dora` still reports stale coordinator/state errors while you are running Dora manually, restart the Dora runtime, then rerun:

```bash
pixi run demo-webcam-detection-dora-rerun
```

## Where To Go Next

- Tutorial index: [docs/tutorials/index.md](../tutorials/index.md)
- Runtime handbook: [docs/handbook.md](../handbook.md)
- Debugging guide: [docs/guides/debugging.md](../guides/debugging.md)
