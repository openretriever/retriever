---
title: Composable Pipelines
---
A pipeline is built by a function, so it distributes like one. A Hub module can export a builder that returns a live `Pipeline` (for downstream code to inspect and rewire) or a builder wrapped as a single Flow stage (to drop inside a larger graph). Both surfaces come from the same registered pipeline.

Prove the mechanics locally first — this runs in the core checkout:

```bash
pixi run demo-composable-pipelines
```

```text
=== Extend Declared Pipeline ===
internal flows: ['counter', 'policy']
policy output after replacement: ProcOut(value=104)

=== Compose Pipeline As Flow ===
[outer] value=5 aux=99
wrapped stage output: Tutorial_Composable_CounterOutput(aux=99, value=5)
```

## 1. Register a pipeline with an explicit surface

`register_pipeline` records a builder under a name and declares the external ports downstream code is allowed to touch. Name internal flows with `.named(...)` so those ports have stable ids.

```python
import retriever
from retriever.flow import Flow, Pipeline, Rate, Latest

@retriever.register_pipeline(
    "tutorial.composable_counter",
    surface_policy="explicit",
    input_ports=["policy.bias"],
    output_ports=["counter.aux", "policy.value"],
    overwrite=True,
)
def build_composable_counter() -> Pipeline:
    pipe = Pipeline("tutorial.composable_counter")
    with pipe:
        counter = (Counter() @ Rate(hz=10)).named("counter")
        policy = (BiasPolicy() @ Rate(hz=10)).named("policy")
        counter.then(policy, map={"value": "value"}, sync=Latest())
    return pipe
```

## 2. Extend a live pipeline

Call the builder to get a real `Pipeline`, then reach in by id and rewire it. This is what a downstream consumer does after `hub.use`-ing the builder:

```python
pipe = build_composable_counter()
print("internal flows:", sorted(pipe.get_flow_dict().keys()))   # ['counter', 'policy']

pipe.replace(pipe.select_flow("policy"), OverridePolicy(delta=100) @ Rate(hz=10))
pipe.inject_input("policy", "bias", 3, timestamp=0.0)
result = pipe.step(now=0.0)
print(result.outputs["policy"])   # ProcOut(value=104)
pipe.close_stepper()
```

## 3. Reuse the whole pipeline as one Flow stage

`build_pipeline_flow(name)` returns the registered pipeline as a Flow you can name, rate, and wire like any other node:

```python
outer = Pipeline("outer.composable_counter")
with outer:
    bias_source = BiasSource(bias=4) @ Rate(hz=10)
    stage = (retriever.build_pipeline_flow("tutorial.composable_counter") @ Rate(hz=10)).named("stage")
    sink = DecisionPrinter() @ Rate(hz=10)
    bias_source.then(stage, sync=Latest())
    stage.then(sink, sync=Latest())

result = outer.step(now=0.0)   # -> [outer] value=5 aux=99
```

Nesting boundary:

- `stage.step(...)` in isolation is local and in-process.
- The wrapper is not itself the backend artifact.
- Inside a larger `Pipeline`, Retriever lowers the wrapper into flat IR, so the multiprocessing and dora backends execute the inner nodes directly.

## Distributing a builder over Hub

Export the two builders from your module's manifest ([Publishing](/ecosystem/publishing/)):

```toml
[tool.retriever.module.exports]
BuildSlamPipeline     = "lidar_slam.pipeline:build_slam_pipeline"
BuildSlamPipelineFlow = "lidar_slam.pipeline:build_slam_pipeline_flow"
```

Then a consumer reuses either surface exactly as above — a live graph to extend, or a stage to nest:

```python
from retriever import hub
from retriever.flow import Latest, Rate

pipe = hub.use("your-org/lidar-slam:BuildSlamPipeline")()
pipe.replace(pipe.select_flow("frontend"), ReplayFrontend() @ Rate(hz=10))

slam_stage = hub.use("your-org/lidar-slam:BuildSlamPipelineFlow")() @ Rate(hz=10)
camera.then(slam_stage, sync=Latest())
```

## Surface grammar

Explicit ports are `flow_id.port`. Selectors resolve by exact flow/node id first, then fall back to a unique flow class name. Prefer stable `.named(...)` handles and declare them in `input_ports=[...]` / `output_ports=[...]` so the public surface does not drift with internal renames.

`Pipeline.visualize(...)` and `IR.visualize(...)` keep wrapped-pipeline context: a nested `build_pipeline_flow(...)` stage renders as a grouped box around its lowered inner flows, with the pipeline name and surfaced port bindings. Render the tutorial graph with `pixi run docs-tutorial-composable-html`.

For applied composition, see the [first Golden proof](https://retriever-space.pages.dev/examples/golden-hub-proof/) and the GoldenRetriever examples.
