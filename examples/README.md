# Examples

This repo is focused on the **Retriever runtime/core**.

The **canonical, maintained** examples live in:

- `examples/tutorial/` (matches `docs/handbook.md`; see `examples/tutorial/README.md` for the tutorial index)

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
pixi run python -m examples.tutorial.017_pipeline_ergonomics --mode context --exec step
```

## About legacy/system examples

Legacy/system-level examples are kept under `examples/legacy/` for reference while we finish the runtime split.
They may not run on the current runtime and are expected to move to the future **golden-retriever** (system) repo.
