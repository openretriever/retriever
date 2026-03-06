---
title: "🐕 Retriever Framework"
---

# 🐕 Retriever Framework

**Building Modular Robot Agents with Causal Functional Composition**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever is a type-safe, composable runtime for building robotics dataflow pipelines, with pluggable execution backends.

## Quick Start

```python
from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Latest, flow_io


@flow_io
@dataclass
class SrcOut:
    value: int


@flow_io
@dataclass
class AddOut:
    value: int


class Source(Flow[None, SrcOut]):
    def run(self, _):  # type: ignore[override]
        return SrcOut(value=1)


class AddOne(Flow[SrcOut, AddOut]):
    def run(self, input: SrcOut) -> AddOut:
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
- **[Install](getting_started/install.md)** - Pixi / uv setup and troubleshooting
- **[Tutorial Tracks](tutorials/index.md)** - Runnable tutorial curriculum (Tracks A-H)
- **[Runtime Guide (Canonical)](guide_runtime.md)** - Pipeline → IR → execute_ir, event/time model
    - See also: **[Execution Build](guide_execution.md)** (IR optimization details)
- **[Debugging](guides/debugging.md)** - `Pipeline.step(...)` (in-process) vs `Pipeline.run(...)` (backend)
- **[Flow Typing Contract](guides/flow_typing_standard.md)** - tuple signatures, collision semantics, lifecycle ordering
- **[Robotics Typing v1](guides/robotics_typing.md)** - stamped robotics boundary payloads and registry lookup
- **[Data Spec and EventStream v1](guides/data_spec_eventstream.md)** - deterministic event records, joins, manifests, and export helpers
- **[Flow Guide](guide_flow.md)** - Authoring flows, clocks, adapters, and pipelines
    - See also: **[Temporal Model](guide_temporal.md)** (Clocks & Adapters deep dive)
- **[Development Guide](guides/development.md)** - Dev workflow and architecture

### Reference
- **[Architecture](architecture.md)** - Design philosophy and system overview
- **[API](API.md)** - API reference

### Quick Navigation
- **Getting Started**: [Install](getting_started/install.md)
- **Tutorial Curriculum**: [tutorials/index.md](tutorials/index.md)
- **Canonical Runtime**: [guide_runtime.md](guide_runtime.md)
- **Architecture**: [architecture.md](architecture.md)
- **Deep Dives**: [Temporal](guide_temporal.md), [Execution](guide_execution.md)
- **Typing + Data**: [Flow Typing Contract](guides/flow_typing_standard.md), [Robotics Typing v1](guides/robotics_typing.md), [Data Spec v1](guides/data_spec_eventstream.md)
- **Examples**: `examples/` directory and `tests/core/`
- **Registry + Plugins**: [architecture.md](architecture.md#4-registry--plugins-pipelines-and-systems)

## 🚀 Key Features

### ✅ Production Ready
- **Type-Safe Composition**: Catch errors at development time, not runtime
- **Multi-Backend Execution**: Local multiprocessing + dora-rs backend
- **Registry + Plugins**: Entry-point based pipeline discovery (`retriever.plugins`)
- **Debugging Surface**: `Pipeline.step(...)` for VS Code breakpoints inside `Flow.run(...)`
- **Record/Replay**: Stepper-first “rosbag-like” debug workflow

### 🎯 Framework Benefits
- **"PyTorch for Robotics"**: Simple, composable abstractions
- **Execution Flexibility**: Same code works from development to production
- **Component Reusability**: Share and discover robotics components
- **Production Path**: Direct migration from prototype to deployed system

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
- **Production-ish**: dora-rs backend (multi-process, coordinator + message passing)

### Registry System
```python
# IR-first pipeline registry
from retriever.pipeline_registry import register_pipeline, build_ir
from retriever.flow import Pipeline

@register_pipeline("my_pipeline", overwrite=True)
def build():
    pipe = Pipeline("my_pipeline")
    ...
    return pipe

ir = build_ir("my_pipeline")
```

---

**Ready to start?** → [README.md](README.md) | **Deep dive** → [architecture.md](architecture.md)
