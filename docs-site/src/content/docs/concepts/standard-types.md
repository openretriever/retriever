---
title: Standard Types
description: The canonical payload types in retriever.types — one class per standard type across the runtime, hub modules, and GoldenRetriever.
---

There is one canonical home for standard payload types: **`retriever.types`**,
shipped with the runtime. Anything that runs Retriever — examples, hub
modules, GoldenRetriever lanes — can refer to these classes directly, and
two components that both say `PoseStamped` mean the *same class*.

## The canonical modules

| Module | What lives there |
| --- | --- |
| `retriever.types.spatial` | `Header`, `Vector3`, `Quaternion`, `SE3Pose`, `PoseStamped`, `Twist(Stamped)`, `Wrench(Stamped)`, `JointState` + `validate_*` helpers |
| `retriever.types.perception` | `Image2D`, `CompressedImage2D`, `CameraIntrinsics`, `PointCloud3D`, `BBox2D`, `Detection2D`, `DetectionBatch`, `SegmentationMask2D`, `PointTarget2D` |
| `retriever.types.language` | `Caption`, `ReferringExpression`, `GroundedPhrase`, plan-text payloads |
| `retriever.types.symbolic` | objects, skills, grounded-skill payloads |
| `retriever.types.data` | data-spec / event-stream contracts |
| `retriever.types.schema` | `SchemaRef`, `StreamId`, `ClockDomain` |

All payload classes are `@io`-ready: use them directly as Flow port types.

These are generic standards, not the whole robotics ontology. Applied payloads
such as `WorldState`, `BeliefGraph`, `Skill`, `Plan`, and `Trajectory` belong
in GoldenRetriever or other Hub payload packs so they can evolve with examples and
domain semantics without expanding the core runtime API.

```python
from retriever.flow import Flow, Trigger
from retriever.types.perception import Image2D, DetectionBatch

class Detector(Flow[Image2D, DetectionBatch]):
    def step(self, image: Image2D) -> DetectionBatch: ...
```

## How the ecosystem refers to them

- **Hub modules**: depend on `retriever-core` (they already do) and import
  `retriever.types.*` in their port contracts. Do not vendor copies — a
  copied class with the same name is a different type at runtime.
- **Golden packs**: import canonical runtime types directly, delegate to the
  runtime registry, and add what the runtime should not own directly: Arrow
  conversions plus higher-level robotics/planning payloads exported as a
  Hub-loadable applied type pack.
- **Extension packs**: domain-specific type sets that do not belong in the
  runtime can be published as hub modules and loaded with
  `hub.use("org/types-pack:SomeType")` — built on top of, never instead of,
  the standard modules.

## Rules of thumb

1. Need a common robotics payload? Import it from `retriever.types.*`.
2. Adding a broadly useful payload? Contribute it to `retriever.types`
   (versioned, `@io`-decorated, with validators where invariants exist).
3. Adding a niche or heavy payload? Keep it in your module/repo, typed with
   standard fields (`Header`, `SchemaRef`) so it composes.
4. Never redefine a standard type locally, even with identical fields —
   type identity is the contract.

For Hub-distributed applied types, the cross-version contract is the registered
schema and serialization behavior, not Python class identity across unrelated
versions. Pin one Hub ref per application; compose runtime standard types rather
than redefining them.
