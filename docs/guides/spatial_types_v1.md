---
title: Spatial Types v1
---

# Spatial Types v1

## Purpose

`retriever.types.spatial` is the mirror-native package for stamped robotics
boundary payloads.

Use it when a flow boundary should explicitly carry:
- frame id,
- timestamp,
- source metadata,
- pose/twist/wrench/joint-state structure.

## Import Surface

Preferred:

```python
from retriever.types.spatial import PoseStamped, SE3Pose, Vector3, Quaternion
```

Pinned path:

```python
from retriever.types.spatial.v1 import PoseStamped
```

Registry lookup:

```python
from retriever import get_type

PoseStamped = get_type("PoseStamped")
```

## Canonical v1 Types

- `Header`
- `Vector3`
- `Quaternion`
- `SE3Pose`
- `PoseStamped`
- `Twist`
- `TwistStamped`
- `Wrench`
- `WrenchStamped`
- `JointState`

Validation helpers:
- `validate_header`
- `validate_quaternion`
- `validate_pose_stamped`
- `validate_joint_state`

## Recommended Usage

Use robotics typing at flow boundaries where frame/time semantics matter.

Typical pattern:

```python
from retriever.flow import Flow, io
from retriever.types.spatial import PoseStamped

@io
class PoseEnvelope:
    pose: PoseStamped | None = None
```

This keeps:
- flow I/O compatibility explicit,
- robotics payload semantics explicit,
- boundary evolution controlled by a stable package.

## Relationship to Flow Typing

`Flow[...]` defines composition shape.
`retriever.types.spatial` defines payload meaning.

Example:
- `Flow[PoseEnvelope, PoseEnvelope]` tells Retriever how to connect nodes
- `PoseStamped` tells operators what the payload represents

## Tutorial Entry Point

Runnable walkthrough:

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
```
