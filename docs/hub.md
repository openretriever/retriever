# Retriever Hub

## API in a nutshell

```python
from retriever import hub
from retriever.flow import Pipeline, Rate, Latest

# Share one flow
LidarSlam = hub.use("company-abc/lidar-slam:LidarSlamFlow")
slam = LidarSlam(resolution=0.05) @ Rate(hz=10)

# Share a live pipeline factory you can still extend
build_slam = hub.use("company-abc/lidar-slam:BuildSlamPipeline")
pipe = build_slam()
pipe.select_flow("frontend")

# Share a pipeline-flow factory for hierarchical in-process composition
build_slam_stage = hub.use("company-abc/lidar-slam:BuildSlamPipelineFlow")
slam_stage = build_slam_stage(resolution=0.05) @ Rate(hz=10)

# Share a type or a representation transform
SE3Pose = hub.use("company-abc/lidar-slam:SE3Pose")
pose_to_matrix = hub.use("company-abc/lidar-slam:pose_to_matrix")
```

Module reference format:

```plaintext
{org}/{module-name}[:{attribute}][@{version}]
```

Examples:

```python
hub.use("company-abc/lidar-slam")
hub.use("company-abc/lidar-slam:LidarSlamFlow")
hub.use("company-abc/lidar-slam:BuildSlamPipeline@0.1.0")
```

## Loading semantics

- `hub.use("org/name:Export")` returns the actual exported class/function/value, not a wrapper.
- `hub.use("org/name")` returns a `ModuleProxy` over the declared export table, not the raw Python module.
- Different versions of the same hub module are isolated by commit-scoped internal namespaces, so `@0.9.0` and `@1.0.0` do not alias each other in one process.
- Backend/runtime re-import can recover hub-loaded flow classes from the local hub cache when a fresh process needs to reconstruct nodes from IR.

Current boundary:

- a serialized IR from hub-loaded code is still not a self-contained artifact across machines by itself; the target machine must have the corresponding hub cache content available, or load the module through Hub first.

## What a module can export

Hub exports are normal Python attributes. A module may export:

- flow classes or flow factories
- live pipeline factories
- pipeline-flow factories for in-process hierarchical composition
- shared `@io` envelope types for flow boundaries
- shared domain / representation types
- representation transforms and serialization helpers

Recommended public split:

- `types.py`: shared envelope types and domain types
  Use `@io` only for flow-boundary envelopes. Keep canonical domain types plain when
  they should not gain optional-field signal semantics.
- `transforms.py`: pure representation conversion helpers
- `pipeline.py`: graph assembly and composition helpers

## Packaging a module

Example directory structure:

```plaintext
lidar-slam/
├── pyproject.toml
└── lidar_slam/
    ├── flow.py
    ├── pipeline.py
    ├── transforms.py
    └── types.py
```

`pyproject.toml`:

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

The Hub loader reads `[tool.retriever.module]`, then imports the declared module and returns the requested export.
That means module top-level code must be import-safe: do not open cameras, sockets,
SDK clients, or other local resources during import.

## Composable pipelines

Two export patterns matter for reusable pipelines:

### 1. Export a live pipeline factory

Use this when downstream code wants to inspect or extend the imported graph.

```python
pipe = hub.use("company-abc/lidar-slam:BuildSlamPipeline")()
frontend = pipe.select_flow("frontend")
pipe.replace(frontend, ReplayFrontend() @ Rate(hz=10))
```

### 2. Export a pipeline-flow factory

Use this when downstream code wants to treat the whole sub-pipeline as one flow stage.

```python
slam_stage = hub.use("company-abc/lidar-slam:BuildSlamPipelineFlow")() @ Rate(hz=10)
camera.then(slam_stage, sync=Latest())
```

Direct `flow.step(...)` on this wrapper is still local/in-process.
When you nest it inside a larger `Pipeline` and build or run that pipeline,
Retriever lowers the wrapper into flat IR so `multiprocessing` and `dora`
backends can execute the inner nodes normally.

Shared types and transforms compose with these factories the same way:

```python
SE3Pose = hub.use("company-abc/lidar-slam:SE3Pose")
pose_to_threshold = hub.use("company-abc/lidar-slam:pose_to_threshold")
build_slam = hub.use("company-abc/lidar-slam:BuildSlamPipeline")

pipe = build_slam()  # `SE3Pose` can be a plain shared representation type
threshold = pose_to_threshold(SE3Pose(x=1.0, y=2.0, z=3.0))
pipe.inject_input("frontend", "threshold", threshold, timestamp=0.0)
```

## Surface grammar

Explicit pipeline surfaces use:

```plaintext
flow_id.port
```

Resolution order:

1. exact flow id / node id
2. unique flow class name fallback

Recommendation:

- Name internal handles with `.named("camera")`, `.named("frontend")`, `.named("planner")`
- Use those stable ids in `input_ports=[...]` and `output_ports=[...]`

Example:

```python
source = (Camera() @ Rate(hz=10)).named("camera")
frontend = (Frontend() @ Rate(hz=10)).named("frontend")
```

Then:

```python
@register_pipeline(
    "slam_stage",
    surface_policy="explicit",
    input_ports=["frontend.threshold"],
    output_ports=["camera.image", "frontend.pose"],
)
```

Helper APIs:

- `handle.named("camera")`
- `pipe.get_flow_dict()`
- `pipe.select_flow("camera")`
- `pipe.replace(old, new)` keeps the old flow id by default
- `build_pipeline_surface(...)`
- `build_pipeline_flow(...)`

Pipeline ports still belong to concrete internal flow nodes, even when the whole pipeline is reused hierarchically.

## Visualizing composed pipelines

`Pipeline.visualize(...)` and `IR.visualize(...)` now preserve wrapped-pipeline context for
`build_pipeline_flow(...)` stages. In HTML and ASCII views, a nested pipeline stage is rendered
as a grouped pipeline box around the lowered inner flows, with:

- the wrapped pipeline name
- surfaced input/output bindings
- a summary of the internal flow graph

This keeps the outer graph readable while still showing that a set of lowered nodes belongs to one
reusable pipeline stage, not a flat unrelated subgraph.

## Flow instantiation and local resources

Keep the authoring surface as ordinary Python construction:

```python
camera = Camera(device_id="front")
```

Do not introduce a separate `.remote()` authoring mode unless Retriever also changes its backend/placement model. Today the runtime boundary already exists:

- authoring code creates flow objects eagerly
- `Pipeline.step()` runs those same instances in-process
- backends reconstruct flows lazily from IR in the runtime process

Guidelines:

- module top-level: import-safe only
- `__init__`: store lightweight, serializable configuration only
- `init_config()`: return serializable reconstruction data only
- `__lazy_init__()` / `init()`: acquire runtime-local resources

Local resources include:

- camera handles
- sockets
- SDK clients
- GPU contexts
- file handles

Preferred pattern:

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

    def init(self) -> None:
        self._camera = open_camera(self.device_id)
```

## Hub index

Retriever Hub uses an index repository with entries under:

```plaintext
modules/{org}/{name}.toml
```

Example:

```toml
[module]
repo = "https://github.com/company-abc/lidar-slam"
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
