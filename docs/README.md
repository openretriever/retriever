# Retriever Documentation

These docs are being updated to match the **refactored runtime**.

The canonical workflow is:

`Pipeline (or FlowContext) → validate() → IRStruct → build_execution() → ExecutionGraph → execute_ir()`

## Start Here

- Handbook (overview): `handbook.md`
- Install: `install.md`
- Canonical runtime guide: `guide_runtime.md`
- Debugging (`Pipeline.step`): `guide_debugging.md`
- Execution compilation: `guide_execution.md`
- Time/FRP model: `guide_time.md`

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

For runtime/core work, treat these pages as canonical:

- `docs/guide_runtime.md`
- `docs/guide_flow.md`
- `docs/guide_debugging.md`
- `docs/guide_time.md`
