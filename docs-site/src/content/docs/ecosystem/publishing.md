---
title: Publishing
---
To make a repository hub-loadable you add one manifest section, keep the module import-safe, and register the repo in the Hub index. After that, `hub.use("your-org/your-module:Export")` resolves for anyone.

## Package layout

The loader supports a flat package or the standard `src/` layout:

```text
lidar-slam/
├── pyproject.toml
└── lidar_slam/          # or src/lidar_slam/
    ├── flow.py
    ├── pipeline.py
    ├── transforms.py
    └── types.py
```

## The `[tool.retriever.module]` manifest

This section is the entire contract the loader reads. `module` names the importable package; the `exports` table maps each public name to a `dotted.module:Attribute` path inside that package.

```toml
[project]
name = "lidar-slam"
version = "1.2.0"
dependencies = ["numpy>=1.24,<2"]

[tool.retriever.module]
module = "lidar_slam"
min_retriever_version = "1.0.0"

[tool.retriever.module.exports]
LidarSlamFlow         = "lidar_slam.flow:LidarSlamFlow"
SE3Pose               = "lidar_slam.types:SE3Pose"
pose_to_matrix        = "lidar_slam.transforms:pose_to_matrix"
BuildSlamPipeline     = "lidar_slam.pipeline:build_slam_pipeline"
BuildSlamPipelineFlow = "lidar_slam.pipeline:build_slam_pipeline_flow"
```

Rules the loader enforces:

- Every export value needs the `:` separator, and the module part must live inside the declared package (`lidar_slam.*`).
- `min_retriever_version` is checked against the consumer's installed `retriever` version.
- `[project].dependencies` are checked as PEP 508 requirements — a missing or version-incompatible dependency raises before your code imports.

An export can be anything importable: a Flow class, a `@io` envelope type, a plain domain type, a transform, or a pipeline builder ([Composable Pipelines](/ecosystem/composable-pipelines/) covers the builder exports).

## Keep modules import-safe

The loader imports your package top-to-bottom. Top-level code must not open cameras, sockets, SDK clients, GPU contexts, or files — importing the module must be free of side effects.

Push all resource acquisition into the Flow lifecycle:

```python
from retriever.flow import Flow, io

@io
class Frame:
    image: bytes

class Camera(Flow[None, Frame]):
    def __init__(self, *, device_id: str):
        self.device_id = device_id      # lightweight config only
        self._camera = None

    def init_config(self) -> dict:
        return {"device_id": self.device_id}  # serializable reconstruction data

    def reset(self) -> None:
        self._camera = open_camera(self.device_id)  # runtime-local resource
```

- module top level: import-safe only
- `__init__`: store lightweight, serializable configuration
- `init_config()`: return serializable reconstruction data
- `reset()` / `__lazy_init__()`: acquire runtime-local resources

## Register in the Hub index

The index is a git repo of TOML entries keyed by `modules/{org}/{name}.toml`. Each entry points at your repo:

```toml
[module]
repo = "https://github.com/your-org/lidar-slam"
description = "LiDAR SLAM pipeline"
author = "Company ABC"
license = "MIT"
tags = ["lidar", "slam", "mapping"]
```

The default index is `openretriever/hub-index`; consumers can point elsewhere with `RETRIEVER_HUB_INDEX_URL`.

## Before you publish

- the repo is reachable (add `RETRIEVER_HUB_TOKEN` support in mind for private repos)
- `pyproject.toml` has a valid `[tool.retriever.module]` section
- at least one semver tag exists — version resolution reads git tags like `v1.0.0`, and a repo with none raises `HUB_NO_SEMVER_TAGS`
- the declared package imports cleanly with no side effects
- the smallest public example runs without private credentials or local-only paths

Run your module's smallest smoke command and confirm every documented import and output still matches before announcing. Keep hosting credentials, DNS, and org-specific release notes out of the public package docs.

## Release boundary

GoldenRetriever is the current applied catalog and the reference for this shape: source examples plus a manifest-declared Hub payload pack. Do not ship a second runtime package to share applied robot payloads — publish them as a Hub module instead. See [Golden Examples](/ecosystem/golden-packs/).
