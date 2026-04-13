---
title: Type Surface Status v1
---

# Type Surface Status v1

## Purpose

Summarize the current canonical type surfaces and:
- `retriever.types.spatial`
- `retriever.types.perception`
- `retriever.types.language`
- `retriever.types.data`
- the flow typing contract carry-back that these packages rely on

This page is status-oriented. For day-to-day usage, read:
- `docs/guides/spatial_types_v1.md`
- `docs/guides/data_eventstream_v1.md`
- `docs/guides/perception_types_v1.md`
- `docs/guides/language_types_v1.md`
- `docs/guides/type_composition_v1.md`
- `docs/guides/flow_typing_standard.md`

## Current State

The mirror carry-back now targets the modern tutorial/runtime branch line and includes:

1. flow typing contract support for tuple-literal and tuple-output signatures,
2. canonical `retriever.types.spatial` package,
3. canonical `retriever.types.perception` package,
4. canonical `retriever.types.language` package,
5. canonical `retriever.types.data` package,
6. tutorial-track exposure under existing one-level tracks.

## Runtime File Map

Flow typing contract:
- `src/retriever/flow/base.py`
- `src/retriever/rt/step.py`
- `src/retriever/rt/stepper.py`
- `src/retriever/rt/backend/multiprocessing/executor.py`
- `src/retriever/rt/backend/dora/executor.py`
- `src/retriever/rt/lifecycle.py`
- `scripts/validate_flow_typing.py`

Spatial types:
- `src/retriever/types/spatial/__init__.py`
- `src/retriever/types/spatial/v1.py`
- registry via `src/retriever/registry/types.py`

Perception types:
- `src/retriever/types/perception/__init__.py`
- `src/retriever/types/perception/v1.py`

Language types:
- `src/retriever/types/language/__init__.py`
- `src/retriever/types/language/v1.py`

Data layer:
- `src/retriever/types/data/__init__.py`
- `src/retriever/types/data/events.py`
- `src/retriever/types/data/streams.py`
- `src/retriever/types/data/dataset.py`
- `src/retriever/types/data/interop.py`
- `src/retriever/types/data/v1.py`

Canonical rule:
- package root exports core contracts
- explicit submodules export operators and export helpers

## Acceptance Checks

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q \
  tests/core/test_flow_typing_contract_rt.py \
  tests/core/test_flow_typing_validator_script.py \
  tests/flow/test_compositional_io.py \
  tests/core/test_perception_type_surface_rt.py \
  tests/core/test_language_type_surface_rt.py \
  tests/core/test_data_spec_event_core_rt.py \
  tests/core/test_data_spec_multistream_event_time_rt.py \
  tests/core/test_data_spec_processing_profile_rt.py \
  tests/core/test_data_spec_manifest_and_lerobot_rt.py \
  tests/core/test_data_spec_eventbuffer_interop_rt.py \
  tests/core/test_type_registry_schema_rt.py
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
- the removed placeholder package trees that previously duplicated data/spatial imports
- old public `v2` naming

Canonical public naming is:
- `retriever.types` is a narrow umbrella, not the home for symbolic entities or registry helpers
- `retriever.types.spatial` / `retriever.types.spatial.v1`
- `retriever.types.perception` / `retriever.types.perception.v1`
- `retriever.types.language` / `retriever.types.language.v1`
- `retriever.types.data` / `retriever.types.data.v1`
