# Retriever Documentation

These docs are being updated to match the **refactored runtime**.

The canonical workflow is:

`FlowContext → validate() → IRStruct → build_execution() → ExecutionGraph → execute_ir()`

## Start Here

- Handbook (overview): `handbook.md`
- Install: `install.md`
- Canonical runtime guide: `guide_runtime.md`
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

Some pages still reference the older `Flow.from_module`/`LocalExecutor` API and will be rewritten:

- `guide_flow.md`
- `API.md`
- `architecture_legacy.md`

For now, treat `guide_runtime.md` as the source of truth.
