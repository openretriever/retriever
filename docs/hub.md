---
title: "Ecosystem"
---

# Retriever Ecosystem

Retriever has three connected public layers:

- **Runtime core**: the Python package in this repo. It defines Flow, Clock, Sync Policy, Pipeline, stepping, replay, IR, and backend execution.
- **Retriever Hub**: reusable Flows, typed payload packs, transforms, and composed pipelines that can be shared across projects.
- **GoldenRetriever applied examples**: the applied robotics reference catalog and current manifest-declared type pack.

<div class="rt-doc-map">
  <a href="/ecosystem/modules/"><strong>Hub Packs and Modules</strong><span>What a reusable Retriever export surface can declare and how users import it.</span></a>
  <a href="/ecosystem/composable_pipelines/"><strong>Composable Pipelines</strong><span>How to reuse a whole pipeline as an inspectable graph or one Flow stage.</span></a>
  <a href="/ecosystem/publishing/"><strong>Publishing</strong><span>Packaging conventions, import-safe modules, and index metadata.</span></a>
  <a href="https://retriever-space.pages.dev/"><strong>Golden reference layer</strong><span>Applied robotics examples and Retriever Hub pack candidates for perception, memory, language, notebooks, and robotics.</span></a>
</div>

## API In A Nutshell

```python
from retriever import hub
from retriever.flow import Pipeline, Rate, Latest

# Share one flow.
LidarSlam = hub.use("your-org/lidar-slam:LidarSlamFlow")
slam = LidarSlam(resolution=0.05) @ Rate(hz=10)

# Share a live pipeline factory that downstream code can inspect or extend.
build_slam = hub.use("your-org/lidar-slam:BuildSlamPipeline")
pipe = build_slam()
frontend = pipe.select_flow("frontend")

# Share a pipeline-flow factory for hierarchical composition.
build_stage = hub.use("your-org/lidar-slam:BuildSlamPipelineFlow")
stage = build_stage(resolution=0.05) @ Rate(hz=10)
```

## When To Use Hub

Use Hub packs/modules when a component is reusable across robot stacks:

- typed boundary payloads such as poses, detections, task commands, and action chunks
- perception, localization, planning, policy, or control Flows
- representation transforms between common robotics/data formats
- pipeline factories that expose a stable public surface while keeping internals replaceable

Keep one-off tutorial code in the examples tree until the public boundary is stable.

## Continue

- [Hub Packs and Modules](ecosystem/modules.md)
- [Composable Pipelines](ecosystem/composable_pipelines.md)
- [Publishing Hub Packs](ecosystem/publishing.md)
