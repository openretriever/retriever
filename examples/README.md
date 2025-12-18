# Examples

This repo is focused on the **Retriever runtime/core**.

The **canonical, maintained** examples live in:

- `examples/00_refact/` (matches `docs/handbook.md`; see `examples/00_refact/README.md` for the tutorial index)

## Quick start (Pixi)

```bash
# Dora perception demo (camera → detection → display)
pixi run demo-dora

# Service request/response demo (Dora recommended)
pixi run demo-request-dora
```

## Start here

```bash
# Pipeline ergonomics: explicit vs `with pipe:` vs `retriever.connect(...)`
pixi run python -m examples.00_refact.017_pipeline_ergonomics --mode context --exec step
```

## About the other folders

The other folders under `examples/` are **older and/or system-level experiments** from before the runtime refactor
(planning, robot I/O, large “system” demos, etc.).

They are expected to move to the future **golden-retriever** (system) repo and may not run on the current runtime.
Treat them as reference material until the split is complete.
