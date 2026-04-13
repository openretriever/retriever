---
title: "🐕 Retriever Framework"
slug: "intro"
---

# 🐕 Retriever Framework

**Building Modular Robot Agents with Causal Functional Composition**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever is the runtime/core package for typed robotics dataflow pipelines, with pluggable execution backends.
Robot integrations, simulator stacks, and heavier model packages belong in companion repositories or external packages.

## Quick Start

```python
from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class SrcOut:
    value: int


@io
class AddOut:
    value: int


class Source(Flow[None, SrcOut]):
    def step(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def step(self, input: SrcOut) -> AddOut:
        return AddOut(value=input.value + 1)


pipe = Pipeline("quickstart")
src = Source() @ Rate(hz=10)
add = AddOne() @ Rate(hz=10)
pipe.connect(src, add, sync=Latest())

pipe.run(backend="multiprocessing", duration=1.0)
```

### Debugging

```python
# Non-blocking full run
engine = pipe.run(backend="multiprocessing", blocking=False)
engine.stop()

# Single-step in-process execution
pipe.step(dt=0.1)
pipe.close_stepper()
```

## 📚 Documentation

### Getting Started
- **[Quickstart](quickstart.md)** - The shortest path to `@io`, `Flow`, clocks, `connect`, `run`, and `step`
- **[Install](getting_started/install.md)** - Pixi / uv setup and troubleshooting
- **[Tutorial Tracks](tutorials/index.md)** - Runnable tutorial curriculum (Tracks A-H)
- **[Runtime Guide (Canonical)](guide_runtime.md)** - Pipeline → IR → execute_ir, event/time model
    - See also: **[Execution Build](guide_execution.md)** (IR optimization details)
- **[Debugging](guides/debugging.md)** - `Pipeline.step(...)` (in-process) vs `Pipeline.run(...)` (backend)
- **[Flow Typing Contract](guides/flow_typing_standard.md)** - tuple signatures, collision semantics, lifecycle ordering
- **[Spatial Types v1](guides/spatial_types_v1.md)** - stamped robotics boundary payloads and registry lookup
- **[Perception Types v1](guides/perception_types_v1.md)** - canonical images, encoded video artifacts, point clouds, detections, and masks
- **[Language Types v1](guides/language_types_v1.md)** - primitive captions, grounded phrases, prompts, and plan text
- **[Data and EventStream v1](guides/data_eventstream_v1.md)** - canonical event/data contracts plus explicit helper modules
- **[Flow Guide](guide_flow.md)** - Authoring flows, clocks, adapters, and pipelines
    - See also: **[Temporal Model](guide_temporal.md)** (Clocks & Adapters deep dive)
- **[Development Guide](guides/development.md)** - Dev workflow and architecture

### Reference
- **[Architecture](architecture.md)** - Design philosophy and system overview
- **[API](API.md)** - API reference

## 🚀 Key Features

### ✅ Alpha, Runtime-First
- **Type-Safe Composition**: Catch errors at development time, not runtime
- **Multi-Backend Execution**: Local multiprocessing + dora-rs backend
- **Registry + Plugins**: Entry-point based pipeline discovery (`retriever.plugins`)
- **Debugging Surface**: `Pipeline.step(...)` for VS Code breakpoints inside `Flow.step(...)`
- **Record/Replay**: Stepper-first “rosbag-like” debug workflow

### 🎯 Framework Benefits
- **"PyTorch for Robotics"**: Simple, composable abstractions
- **Execution Flexibility**: One authoring model across stepper, multiprocessing, and dora-rs execution
- **Component Reusability**: Share and discover robotics components
- **Runtime Path**: Clear progression from prototype to backend execution and replay/debug workflows

## 🏗️ Architecture Overview

### Canonical Runtime Workflow
```python
# Author pipelines
pipe = Pipeline("my_pipeline")
...

# Run on a backend (validates IR internally)
pipe.run(backend="multiprocessing")
```

### Multi-Backend Execution
- **Development**: In-process stepping (`Pipeline.step`) for debugging
- **Local execution**: Python multiprocessing backend
- **Backend execution**: dora-rs backend (multi-process, coordinator + message passing)

### Registry System
```python
# IR-first pipeline registry
from retriever.registry.pipeline import register_pipeline, build_ir
from retriever.flow import Pipeline

@register_pipeline("my_pipeline", overwrite=True)
def build():
    pipe = Pipeline("my_pipeline")
    ...
    return pipe

ir = build_ir("my_pipeline")
```

---

**Ready to start?** → [Quickstart](quickstart.md) | **Tutorials** → [Tutorial Tracks](tutorials/index.md)
