---
title: Standard Types
description: The canonical payload types in retriever.types — one class per standard type across the runtime, hub modules, and GoldenRetriever.
---

**What you'll learn:** where the shared robot payload types live (`retriever.types.*`), that each is already an `@io` type you can drop straight onto a Flow port, and why type *identity* — not just field shape — is the contract.

There is one canonical home for standard payloads: **`retriever.types`**, shipped with the runtime. Anything that runs Retriever — examples, Hub modules, GoldenRetriever — imports these classes directly, so two components that both say `PoseStamped` mean the *same class*, not two look-alikes.

## The canonical modules

| Module | Types it exports |
| --- | --- |
| `retriever.types.spatial` | `Header`, `Vector3`, `Quaternion`, `SE3Pose`, `PoseStamped`, `Twist`/`TwistStamped`, `Wrench`/`WrenchStamped`, `JointState` (+ `validate_*`) |
| `retriever.types.perception` | `Image2D`, `CompressedImage2D`, `EncodedVideo`, `CameraIntrinsics`, `PointCloud3D`, `BBox2D`, `Detection2D`, `DetectionBatch`, `SegmentationMask2D`, `PointTarget2D` (+ `validate_*`) |
| `retriever.types.language` | `TextSpan`, `Caption`, `Prompt`, `ReferringExpression`, `GroundedPhrase`, `PlanStepText`, `PlanText` (+ `validate_*`) |
| `retriever.types.symbolic` | `Object`, `ObjectType`, `Variable`, `Predicate`, `LiftedAtom`, `GroundAtom`, `State`, `Action`, `Option`, `ParameterizedOption`, `Task`, `SkillSignature`, `GroundedSkill` |
| `retriever.types.data` | `Event`, `EventBuffer`, `MultiStreamBuffer`, `DataSpec`, `StreamSpec`, `JoinPolicy`, `WindowPolicy`, `DatasetManifest`, `EpisodeManifest`, `LineageRef` |
| `retriever.types` (root) | `StreamId`, `SchemaRef`, `ClockDomain` — stream identity and schema primitives |

## Use them directly as Flow ports

Every payload class is already `@io`-decorated, so it can be a Flow input or output with no wrapping:

```python
from retriever.flow import Flow, Trigger
from retriever.flow.io import is_flow_io
from retriever.types.spatial import Header, Vector3, Quaternion, SE3Pose, PoseStamped
from retriever.types.perception import BBox2D, Detection2D, DetectionBatch
from retriever.types.language import Caption

pose = PoseStamped(
    header=Header(stamp_ns=1_000_000, frame_id="base_link"),
    pose=SE3Pose(
        position=Vector3(x=0.4, y=0.0, z=0.2),
        orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
    ),
)
batch = DetectionBatch(
    detections=(Detection2D(label="cup", bbox=BBox2D(x=12, y=30, width=40, height=55), confidence=0.91),),
    frame_index=7,
)

print("PoseStamped @io? ", is_flow_io(PoseStamped))
print("DetectionBatch @io?", is_flow_io(DetectionBatch))
print("Caption @io?       ", is_flow_io(Caption))
print("pose frame:", pose.header.frame_id, "x=", pose.pose.position.x)
print("detections:", [(d.label, d.confidence) for d in batch.detections])
print("caption:", Caption(text="a red cup on the table").text, "| lang:", Caption(text="").language)

class Detector(Flow[DetectionBatch, Caption]):   # standard types as ports, no wrapping
    def step(self, batch: DetectionBatch) -> Caption:
        return Caption(text="saw: " + ", ".join(d.label for d in batch.detections))

det = Detector() @ Trigger("detections")
print("Flow input port type: ", Detector().input_type.__name__)
print("Flow output port type:", Detector().output_type.__name__)
```

```text
PoseStamped @io?  True
DetectionBatch @io? True
Caption @io?        True
pose frame: base_link x= 0.4
detections: [('cup', 0.91)]
caption: a red cup on the table | lang: en
Flow input port type:  DetectionBatch
Flow output port type: Caption
```

`SE3Pose`, `PoseStamped`, `Twist`, and `Wrench` are composed from `Vector3`/`Quaternion`/`Header`, so nested access (`pose.pose.position.x`) works as written. Where an invariant exists, a matching `validate_*` helper enforces it — e.g. `validate_quaternion` checks unit norm.

## How the ecosystem refers to them

- **Hub modules** depend on `retriever-core` and import `retriever.types.*` in their port contracts. Never vendor a copy — a copied class with the same name is a different type at runtime.
- **GoldenRetriever** imports the canonical runtime types directly and adds what the runtime should not own: Arrow conversions and higher-level robotics/planning payloads, published as a Hub-loadable applied pack.
- **Extension packs** publish domain-specific type sets as Hub modules loaded with `hub.use("org/types-pack:SomeType")` — built on top of the standard modules, never instead of them.

Applied payloads such as `WorldState`, `BeliefGraph`, `Skill`, `Plan`, and `Trajectory` deliberately live in GoldenRetriever or other Hub packs, so they can evolve with domain semantics without expanding the core runtime API.

## Rules of thumb

1. Need a common robotics payload? Import it from `retriever.types.*`.
2. Adding a broadly useful payload? Contribute it to `retriever.types` — versioned, `@io`-decorated, with validators where invariants exist.
3. Adding a niche or heavy payload? Keep it in your own module, typed with standard fields (`Header`, `SchemaRef`) so it composes.
4. Never redefine a standard type locally, even with identical fields — type identity is the contract.

For Hub-distributed applied types, the cross-version contract is the registered schema and serialization behavior, not Python class identity across unrelated versions. Pin one Hub ref per application, and compose runtime standard types rather than redefining them.
