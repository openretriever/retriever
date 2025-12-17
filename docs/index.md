# 🐕 Retriever Framework

**Type-safe, composable framework for production robotics**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever is a type-safe, composable runtime for building robotics dataflow pipelines, with pluggable execution backends.

## Quick Start

```python
from dataclasses import dataclass

from retriever.core.flow import Flow, Pipeline, Rate, Latest, flow_io


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

## 📚 Documentation

### Getting Started
- **[Install](install.md)** - Pixi / uv setup and troubleshooting
- **[Runtime Guide (Canonical)](guide_runtime.md)** - Pipeline → IR → execute_ir, event/time model
- **[Flow Guide](guide_flow.md)** - Legacy guide (pre-refactor; needs update)
- **[Development Guide](guide_dev.md)** - Dev workflow and architecture

### Reference
- **[Architecture](architecture.md)** - Design philosophy and system overview
- **[API](API.md)** - API reference

### Development Guides  
- **[guide_flow.md](guide_flow.md)** - Flow system detailed reference and patterns
- **[guide_dev.md](guide_dev.md)** - Developer guide and contribution workflows
- **[contributing.md](contributing.md)** - How to contribute to the project

### Quick Navigation
- **Getting Started**: [Install](install.md)
- **Canonical Runtime**: [guide_runtime.md](guide_runtime.md)
- **Architecture**: [architecture.md](architecture.md)
- **Examples**: `examples/` directory and `tests/core/`
- **Registry + Plugins**: [architecture.md](architecture.md#4-registry--plugins-pipelines-and-systems)

## 🚀 Key Features

### ✅ Production Ready
- **Type-Safe Composition**: Catch errors at development time, not runtime
- **Multi-Backend Execution**: Sequential, parallel, and distributed backends
- **Registry System**: PyTorch-style component discovery and substitution
- **State Management**: Principled robot state handling with Eff monad
- **Comprehensive Testing**: 50+ tests covering robotics use cases

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
- **Development**: Sequential execution for debugging
- **Testing**: Parallel execution for performance
- **Production**: Distributed execution with dora-rs

### Registry System
```python
# IR-first pipeline registry
from retriever.core.pipeline_registry import register_pipeline, build_ir
from retriever.core.flow import Pipeline

@register_pipeline("my_pipeline", overwrite=True)
def build():
    pipe = Pipeline("my_pipeline")
    ...
    return pipe

ir = build_ir("my_pipeline")
```

---

**Ready to start?** → [README.md](README.md) | **Deep dive** → [architecture.md](architecture.md)
