# data

Standalone incubation package for collaborator-facing data read/write testing.

This package is intentionally independent from `retriever.*`.

## Files

- `types.py` — minimal typed contracts
- `read_tool.py` — inspect portable dataset artifacts
- `mock_write_tool.py` — generate deterministic test artifacts

## Quickstart

Generate a mock artifact:

```bash
python -m tools.data.mock_write_tool /tmp/data_demo --dataset-name demo
```

Inspect it:

```bash
python -m tools.data.read_tool /tmp/data_demo
```
