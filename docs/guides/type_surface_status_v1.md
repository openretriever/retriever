---
title: Type Surface Status v1
---

# Type Surface Status v1

## Purpose

Summarize the current canonical type surfaces and:
- `retriever.types.spatial`
- `retriever.types.data`
- the flow typing contract carry-back that these packages rely on

This page is status-oriented. For day-to-day usage, read:
- `docs/guides/spatial_types_v1.md`
- `docs/guides/data_eventstream_v1.md`
- `docs/guides/flow_typing_standard.md`

## Current State

The mirror carry-back now targets the modern tutorial/runtime branch line and includes:

1. flow typing contract support for tuple-literal and tuple-output signatures,
2. canonical `retriever.types.spatial` package,
3. canonical `retriever.types.data` package,
4. tutorial-track exposure under existing one-level tracks.

## Runtime File Map

Flow typing contract:
- `src/retriever/flow/base.py`
- `src/retriever/rt/step.py`
- `src/retriever/rt/stepper.py`
- `src/retriever/rt/backend/multiprocessing/executor.py`
- `src/retriever/rt/backend/dora/executor.py`
- `src/retriever/rt/lifecycle.py`
- `scripts/validate_flow_typing.py`

Robotics typing:
- `src/retriever/types/spatial/__init__.py`
- `src/retriever/types/spatial/v1.py`
- compatibility shim via `src/retriever/robotics_typing/`
- registry via `src/retriever/types_registry.py`

Data spec:
- `src/retriever/types/data/__init__.py`
- `src/retriever/types/data/v1.py`
- `src/retriever/types/data/buffer.py`
- `src/retriever/types/data/join.py`
- `src/retriever/types/data/window.py`
- `src/retriever/types/data/dataset_manifest.py`
- `src/retriever/types/data/lerobot_bridge.py`
- `src/retriever/types/data/interop_flow_types.py`

## Acceptance Checks

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q \
  tests/core/test_flow_typing_contract_rt.py \
  tests/core/test_flow_typing_validator_script.py \
  tests/flow/test_compositional_io.py \
  tests/core/test_robotics_typing_v1_rt.py \
  tests/core/test_robotics_typing_registry_rt.py \
  tests/core/test_data_spec_event_core_rt.py \
  tests/core/test_data_spec_multistream_event_time_rt.py \
  tests/core/test_data_spec_processing_profile_rt.py \
  tests/core/test_data_spec_manifest_and_lerobot_rt.py \
  tests/core/test_data_spec_eventbuffer_interop_rt.py
```

Tutorial smoke checks:

```bash
PYTHONPATH=src python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
PYTHONPATH=src python -m examples.tutorial.e_resource_and_sync.07_data_multistream_join
PYTHONPATH=src python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```

## Tutorial Entry Points

- `examples/tutorial/g_operations_interfaces/05_spatial_type_boundaries.py`
- `examples/tutorial/e_resource_and_sync/07_data_multistream_join.py`
- `examples/tutorial/h_release_readiness/03_dataset_manifest_and_lerobot_mapping.py`

## Stale Assumptions Removed

This carry-back does not use:
- the old nested registry path layout
- Golden-only import paths
- old public `v2` naming

Canonical public naming is:
- `retriever.types.spatial` / `retriever.types.spatial.v1`
- `retriever.types.data` / `retriever.types.data.v1`
