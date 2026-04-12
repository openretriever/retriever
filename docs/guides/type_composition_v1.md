---
title: Type Composition v1
---

# Type Composition v1

## Goal

Keep Retriever's type story small and reusable.

The preferred pattern is:
- shared payload types for meaning,
- `Flow[...]` and surfaced ports for structure,
- one small `@io` envelope only when named boundary ports are actually needed.

## The Four Shared Type Families

Use these packages as the default vocabulary:

- `retriever.types.schema`
  - `StreamId`, `SchemaRef`, `ClockDomain`
- `retriever.types.spatial`
  - stamped robotics boundary payloads
- `retriever.types.data`
  - event/data/export contracts
- `retriever.types.symbolic`
  - object-centric planning contracts

## Composition Rules

### 1. Prefer shared payloads

Good:

```python
from retriever.types.spatial import PoseStamped, JointState

Flow[tuple[PoseStamped, JointState], PoseStamped]
```

### 2. Prefer plain Python for local products

Before inventing a new dataclass, prefer:
- `tuple[A, B]`
- `T | None`
- plain scalars

### 3. Use `@io` for structural boundaries

`@io` is still useful when a flow needs named ports or explicit field mapping.

```python
from retriever.flow import Flow, io
from retriever.types.spatial import PoseStamped

@io
class PoseEnvelope:
    pose: PoseStamped | None = None
```

The key point is that `PoseStamped` is still the real reusable payload.
The envelope is only the transport shape.

### 4. Keep pipeline adaptation structural

If a composite pipeline needs a different external surface, use:
- surfaced ports
- mapping
- `select_flow(...)`
- `replace(...)`
- `build_pipeline_flow(...)`

Do not create a new payload type just to adapt one pipeline to another.

## `retriever.types.data` Rule

Keep the root import narrow:

```python
from retriever.types.data import Event, EventBuffer, DataSpec
```

Use explicit submodules for helpers:

```python
from retriever.types.data.streams import align_exact, hold, latest, window_agg
from retriever.types.data.dataset import build_dataset_manifest, build_episode_manifest
from retriever.types.data.interop import from_runtime_event_buffer, to_lerobot_records
```

## `retriever.types.symbolic` Rule

Keep the symbolic layer object-centric and compact:
- `objects`
- `options`
- `skills`

Do not let it absorb perception, backend, or recording concerns.

## Tutorial Rule of Thumb

- Intro tutorials may still use tiny `@io` envelopes because they are teaching flow structure.
- Later tutorials should stop inventing one-off payload classes when a shared type, tuple, scalar, or optional value would be clearer.
