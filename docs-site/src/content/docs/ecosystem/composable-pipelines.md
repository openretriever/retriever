---
title: Composable Pipelines
---

# Composable Pipelines

A reusable pipeline can be loaded in two modes:

- **Inspectable graph**: downstream users can validate, visualize, and extend the internal pipeline.
- **Pipeline-as-Flow**: downstream users treat the pipeline as one typed stage inside a larger graph.

```python
build_slam = hub.use("your-org/lidar-slam:BuildSlamPipeline")
pipe = build_slam()
frontend = pipe.select_flow("frontend")

build_stage = hub.use("your-org/lidar-slam:BuildSlamPipelineFlow")
stage = build_stage(resolution=0.05) @ Rate(hz=10)
```

Use the graph form when debugging and extension matter. Use the Flow form when you want a clean boundary inside a larger robot agent.
