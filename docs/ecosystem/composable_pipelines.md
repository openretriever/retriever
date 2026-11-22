---
title: "Composable Pipelines"
---

# Composable Pipelines

Reusable robot subsystems often need two surfaces: a live graph that downstream users can inspect and modify, and a single-stage wrapper that fits inside a larger graph.

## 1. Export A Live Pipeline Factory

Use this when downstream code wants to inspect, replace, or rewire internal Flows.

```python
from retriever import hub
from retriever.flow import Rate

pipe = hub.use("your-org/lidar-slam:BuildSlamPipeline")()
frontend = pipe.select_flow("frontend")
pipe.replace(frontend, ReplayFrontend() @ Rate(hz=10))
```

## 2. Export A Pipeline-Flow Factory

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

Timing of a nested wrapper:

- the inner Flows keep their own clocks; the clock attached to the wrapper (`@ Rate(hz=10)` above) does not gate them, on any backend
- in `Pipeline.step()`, the wrapper runs on every step, passes in only inputs that received a new event, and emits only outputs that an inner Flow produced in that step, so a stepped nested pipeline behaves like the same Flows inlined
- an output with no new value carries no event; use `sync=Latest()` downstream to keep the previous value

The group as one Flow (covering clock):

- a group of Flows behaves as one Flow on its covering clock: the union of the inner `Rate`, `Tick` and `Hybrid` clocks and the events of the boundary inputs that inner `Trigger`, `Synchronized` and `Hybrid` clocks read; the covering clock may tick when no inner Flow runs, and the group then emits no event
- the wrapper exposes it as `wrapper.covering_clock` (for example `Cover[Rate(20 Hz) ∪ Rate(30 Hz) ∪ events(go)]`) and in `viz_metadata()["covering_clock"]`, for grouping and for views of large graphs; execution still runs each inner Flow on its own clock
- `same_instant_cycles(ir)` lists groups with a **same-tick trigger cycle**: each edge can wake its consumer. A `Prev()` edge never wakes its consumer. Changing a trigger to a rate can break a trigger cycle without breaking the underlying **same-tick data cycle**.
- Validation checks data cycles, which include trigger cycles. The default warns once per offending group and preserves the legacy stepping order; `Pipeline(cycles="strict")` rejects it. See [closed loops](../guide_flow.md#7-closed-loops-cycles).

```python
from retriever.ir.clock_algebra import covering_clock, same_instant_cycles

ir = pipe.validate()
covering_clock(ir).ticks(0.0, 1.0)   # Rate ticks of the group in [0, 1)
# pass boundary={"go": ("gate", "go")} to also list boundary trigger inputs
same_instant_cycles(ir)              # [] when the group is admissible
```

## Surface Grammar

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

## Visualizing Composition

`Pipeline.visualize(...)` and `IR.visualize(...)` preserve wrapped-pipeline context for `build_pipeline_flow(...)` stages. In HTML and ASCII views, a nested pipeline stage is rendered as a grouped pipeline box around the lowered inner Flows, with:

- the wrapped pipeline name
- surfaced input/output bindings
- a summary of the internal Flow graph

Run the core composition demo:

```bash
pixi run demo-composable-pipelines
pixi run docs-tutorial-composable-html
```
