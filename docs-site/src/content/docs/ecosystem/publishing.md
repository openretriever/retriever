---
title: Publishing
---

# Publishing

Publish Hub packs or modules only after the boundary is stable, import-safe, and explicit about what it exports.

## Package layout

```text
lidar-slam/
├── pyproject.toml
└── lidar_slam/
    ├── flow.py
    ├── pipeline.py
    ├── transforms.py
    └── types.py
```

## `pyproject.toml`

```toml
[project]
name = "lidar-slam"
version = "1.2.0"
dependencies = ["numpy>=1.24,<2"]

[tool.retriever.module]
module = "lidar_slam"
min_retriever_version = "1.0.0"

[tool.retriever.module.exports]
LidarSlamFlow = "lidar_slam.flow:LidarSlamFlow"
SE3Pose = "lidar_slam.types:SE3Pose"
pose_to_matrix = "lidar_slam.transforms:pose_to_matrix"
BuildSlamPipeline = "lidar_slam.pipeline:build_slam_pipeline"
BuildSlamPipelineFlow = "lidar_slam.pipeline:build_slam_pipeline_flow"
```

The Hub loader reads `[tool.retriever.module]`, imports the declared package surface, and returns the requested export.

## Import-safe modules

Module top-level code must be import-safe. Do not open cameras, sockets, SDK clients, GPU contexts, or files during import.

Preferred Flow resource pattern:

```python
from retriever.flow import Flow, io

@io
class Frame:
    image: bytes

class Camera(Flow[None, Frame]):
    def __init__(self, *, device_id: str):
        self.device_id = device_id
        self._camera = None

    def init_config(self) -> dict:
        return {"device_id": self.device_id}

    def reset(self) -> None:
        self._camera = open_camera(self.device_id)
```

Guidelines:

- module top-level: import-safe only
- `__init__`: store lightweight, serializable configuration only
- `init_config()`: return serializable reconstruction data only
- `__lazy_init__()` / `reset()`: acquire runtime-local resources

## Hub index

Retriever Hub uses an index repository with entries under:

```text
modules/{org}/{name}.toml
```

Example:

```toml
[module]
repo = "https://github.com/your-org/lidar-slam"
description = "LiDAR SLAM pipeline"
author = "Company ABC"
license = "MIT"
tags = ["lidar", "slam", "mapping"]
```

Minimum expectations before publishing:

- the repository is reachable
- `pyproject.toml` contains a valid `[tool.retriever.module]` section
- at least one semver tag exists
- the declared module imports cleanly
- the smallest public example runs without private credentials or local-only paths

## Release boundary

GoldenRetriever is the current applied reference catalog. Keep Golden as applied examples plus a manifest-declared Hub type pack; do not publish a second runtime package just to share applied robot payloads.

## Final public-surface check

After repository visibility, DNS cutover, and TestPyPI/PyPI publication are complete, run the external launch verifier from the core repo root:

```bash
pixi run public-surface-check
```

This check verifies the GitHub default branch, live website URLs, DNS resolution, and `retriever-core` visibility on PyPI/TestPyPI. It is expected to fail before those external launch steps are complete.
