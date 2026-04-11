---
title: Robotics Typing Carry-Back Status
---

# Robotics Typing Carry-Back Status

## Purpose

Track the mirror-native rollout of:
- `retriever.robotics_typing`
- `retriever.data_spec`
- the flow typing contract carry-back that these packages rely on

This page is implementation-status oriented. For user-facing usage, read:
- `docs/guides/robotics_typing.md`
- `docs/guides/data_spec_eventstream.md`
- `docs/guides/flow_typing_standard.md`

## Current State

The mirror carry-back now targets the modern tutorial/runtime branch line and includes:

1. flow typing contract support for tuple-literal and tuple-output signatures,
2. mirror-native robotics typing package,
3. mirror-native data-spec package,
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
- `src/retriever/robotics_typing/__init__.py`
- `src/retriever/robotics_typing/v1.py`
- bootstrap via `src/retriever/__init__.py`
- registry via `src/retriever/types_registry.py`

Data spec:
- `src/retriever/data_spec/__init__.py`
- `src/retriever/data_spec/v1.py`
- `src/retriever/data_spec/buffer.py`
- `src/retriever/data_spec/join.py`
- `src/retriever/data_spec/window.py`
- `src/retriever/data_spec/dataset_manifest.py`
- `src/retriever/data_spec/lerobot_bridge.py`
- `src/retriever/data_spec/interop_flow_types.py`

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
PYTHONPATH=src python -m examples.tutorial.g_operations_interfaces.05_robotics_typing_boundaries
PYTHONPATH=src python -m examples.tutorial.e_resource_and_sync.07_data_spec_multistream_join
PYTHONPATH=src python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```

## Tutorial Entry Points

- `examples/tutorial/g_operations_interfaces/05_robotics_typing_boundaries.py`
- `examples/tutorial/e_resource_and_sync/07_data_spec_multistream_join.py`
- `examples/tutorial/h_release_readiness/03_dataset_manifest_and_lerobot_mapping.py`

## Stale Assumptions Removed

This carry-back does not use:
- the old nested registry path layout
- Golden-only import paths
- old public `v2` naming

Mirror-native public naming is:
- `retriever.robotics_typing.v1`
- `retriever.data_spec.v1`
