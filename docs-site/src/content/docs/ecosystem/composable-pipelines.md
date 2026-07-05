---
title: Composable Pipelines
---
Reusable robot subsystems often need two surfaces: a live graph that downstream users can inspect and modify, and a single-stage wrapper that fits inside a larger graph.

## 1. Export a live pipeline factory

Use this when downstream code wants to inspect, replace, or rewire internal Flows.

```python
from retriever import hub
from retriever.flow import Rate

pipe = hub.use("your-org/lidar-slam:BuildSlamPipeline")()
frontend = pipe.select_flow("frontend")
pipe.replace(frontend, ReplayFrontend() @ Rate(hz=10))
```

## 2. Export a Pipeline-as-Flow factory

Use this when downstream code wants to treat the whole sub-pipeline as one reusable stage.

```python
from retriever import hub
from retriever.flow import Latest, Rate

slam_stage = hub.use("your-org/lidar-slam:BuildSlamPipelineFlow")() @ Rate(hz=10)
camera.then(slam_stage, sync=Latest())
```

Important boundary:

- direct `flow.step(...)` on this wrapper is local/in-process
- the wrapper itself is not the backend artifact
- when nested inside a larger `Pipeline`, Retriever lowers the wrapper into flat IR so multiprocessing and dora backends can execute the inner nodes normally

## Surface grammar

Explicit pipeline surfaces use:

```text
flow_id.port
```

Resolution order:

1. exact flow id / node id
2. unique flow class name fallback

Recommendation:

- name internal handles with `.named("camera")`, `.named("frontend")`, `.named("planner")`
- use stable ids in `input_ports=[...]` and `output_ports=[...]`

```python
source = (Camera() @ Rate(hz=10)).named("camera")
frontend = (Frontend() @ Rate(hz=10)).named("frontend")
```

Then publish the stable surface:

```python
@register_pipeline(
    "slam_stage",
    surface_policy="explicit",
    input_ports=["frontend.threshold"],
    output_ports=["camera.image", "frontend.pose"],
)
def build_slam_stage():
    ...
```

## Visualizing composition

`Pipeline.visualize(...)` and `IR.visualize(...)` preserve wrapped-pipeline context for `build_pipeline_flow(...)` stages. In HTML and ASCII views, a nested pipeline stage is rendered as a grouped pipeline box around the lowered inner Flows, with:

- the wrapped pipeline name
- surfaced input/output bindings
- a summary of the internal Flow graph

Run the core composition demo:

```bash
pixi run demo-composable-pipelines
pixi run docs-tutorial-composable-html
```

For applied composition examples, start with the [first Golden proof](https://retriever-space.pages.dev/examples/golden-hub-proof/), then browse GoldenRetriever examples.
