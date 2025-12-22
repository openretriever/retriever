---
title: "Retriever Documentation"
---

# Retriever Documentation

These docs are being updated to match the **refactored runtime**.

**Single canonical note:** `docs/handbook.md`

If you only read one page, read `docs/handbook.md` top-to-bottom.

## Start Here

- `docs/handbook.md` — install → author → run → debug → record/replay → `on_lag` → examples

Optional deep dives (may be merged into the handbook over time):
- `docs/install.md`
- `docs/guide_runtime.md`
- `docs/guide_flow.md`
- `docs/guide_time.md`
- `docs/guide_execution.md`
- `docs/guide_debugging.md`

## Quick Start

```bash
# Pixi (recommended)
pixi run demo-dora

# Run targeted tests
pixi run python -m pytest tests/core/test_pipeline_registry_rt.py tests/core/test_frp_merge_rt.py -q
```

## Legacy Docs (may be outdated)

The refactor is ongoing, but some older, pre-refactor docs are preserved for reference:

- `docs/legacy/guide_flow_legacy.md`
- `docs/legacy/API_legacy.md`
- `docs/architecture_legacy.md`

For runtime/core work, prefer `docs/handbook.md`. The other guides are optional references and may lag behind.
