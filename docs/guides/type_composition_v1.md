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

## The Five Shared Type Families

Use these packages as the default vocabulary:

Registry helpers do not live on `retriever.types`; use top-level `retriever.register_type(...)` or `retriever.registry.types`. Symbolic object-centric types live under `retriever.types.symbolic`, not the umbrella root.

- `retriever.types.schema`
  - `StreamId`, `SchemaRef`, `ClockDomain`
- `retriever.types.spatial`
  - stamped robotics boundary payloads
- `retriever.types.perception`
  - media, detection, mask, point-cloud, and video primitives
- `retriever.types.data`
  - event/data/export contracts
- `retriever.types.language`
  - primitive text, grounding, and plan-text contracts
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

## `retriever.types.perception` Rule

Use `retriever.types.perception` for reusable media/perception payloads such as images, compressed images, encoded video, point clouds, detections, masks, and pointing targets.

```python
from retriever.types.perception import Image2D, DetectionBatch, PointTarget2D

class PointingFlow(Flow[(Image2D, DetectionBatch), PointTarget2D]):
    ...
```

A stream of `Image2D` frames is semantically a video. Keep encoded multi-frame artifacts separate as `EncodedVideo`.

## `retriever.types.data` Rule

Keep the root import narrow:

```python
from retriever.types import SchemaRef, StreamId
from retriever.types.data import Event, EventBuffer, DataSpec
```

Use explicit submodules for helpers:

```python
from retriever.types.data.streams import align_exact, hold, latest, window_agg
from retriever.types.data.dataset import build_dataset_manifest, build_episode_manifest
from retriever.types.data.interop import from_runtime_event_buffer, to_lerobot_records
```

## `retriever.types.language` Rule

Use `retriever.types.language` for primitive text, grounding, and plan-text outputs.

```python
from retriever.types.language import Caption, GroundedPhrase, PlanText, ReferringExpression
from retriever.types.perception import DetectionBatch

Flow[(ReferringExpression, DetectionBatch), GroundedPhrase]
Flow[Caption, PlanText]
```

Keep model-specific request/response packets and larger planner bundles out of core.

## `retriever.types.symbolic` Rule

Keep the symbolic layer object-centric and compact:
- `objects`
- `options`
- `skills`

Do not let it absorb perception, backend, or recording concerns.

## Tutorial Rule of Thumb

- Intro tutorials may still use tiny `@io` envelopes because they are teaching flow structure.
- Later tutorials should stop inventing one-off payload classes when a shared type, tuple, scalar, or optional value would be clearer.
