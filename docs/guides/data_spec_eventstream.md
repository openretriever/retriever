---
title: Data Spec and EventStream v1
---

# Data Spec and EventStream v1

## Purpose

`retriever.data_spec` defines the mirror-native contract for:
- deterministic event records,
- multi-stream joins,
- lineage,
- dataset manifests,
- export profiles such as LeRobot mapping.

This package is for collection/replay/export semantics, not for changing the
runtime executor internals.

## Import Surface

Preferred:

```python
from retriever.data_spec import Event, EventBuffer, DataSpec
```

Pinned path:

```python
from retriever.data_spec.v1 import Event, StreamId
```

## Two EventBuffer Layers

Retriever now has two distinct event-buffer concepts.

### Runtime EventBuffer

```python
retriever.flow.types.EventBuffer
```

- current runtime abstraction
- shape: `list[(timestamp_seconds: float, value)]`
- used by adapters and executors

### Data Spec EventBuffer

```python
retriever.data_spec.EventBuffer
```

- typed event/data/export abstraction
- uses explicit event metadata
- uses integer nanosecond event time
- carries lineage/schema/frame/unit metadata

Chosen compatibility rule:
- the runtime buffer stays unchanged
- conversions are explicit via:
  - `from_runtime_event_buffer(...)`
  - `to_runtime_event_buffer(...)`

## Core Contracts

- `Event[T]`
- `EventRef`
- `LineageRef`
- `StreamId`
- `ClockDomain`
- `SchemaRef`
- `EventBuffer[T]`
- `MultiStreamBuffer`
- `JoinPolicy`
- `WindowPolicy`
- `DataSpec`
- `EpisodeManifest`
- `DatasetManifest`

## Join and Sampling Profiles

Event-time operators:
- `align_exact`
- `align_latest_before`
- `align_window`
- `join_with_policy`

Processing-time helpers:
- `latest`
- `hold`
- `window_agg`

## Dataset and Export Layer

For dataset/export work, `retriever.data_spec` also provides:
- `build_episode_manifest(...)`
- `build_dataset_manifest(...)`
- `event_table_rows(...)`
- `to_lerobot_records(...)`
- `from_lerobot_records(...)`
- `validate_lerobot_mapping(...)`

These helpers are dependency-light mapping utilities. They do not add a hard
LeRobot runtime dependency.

## Tutorial Entry Points

Multistream join walkthrough:

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.07_data_spec_multistream_join
```

Manifest/export walkthrough:

```bash
pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```
