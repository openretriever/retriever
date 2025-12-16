# 🐕 Retriever Framework

**Type-safe, composable framework for production robotics**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever is a type-safe, composable runtime for building robotics dataflow pipelines, with pluggable execution backends.

## Quick Start

```python
from dataclasses import dataclass

from retriever.core.flow import Flow, FlowContext, Rate, Latest, flow_io
from retriever.core.ir import validate
from retriever.core.rt import execute_ir


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


with FlowContext("quickstart") as ctx:
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    src.then(add, sync=Latest())

ir = validate(ctx)
execute_ir(ir, backend="multiprocessing", duration=1.0)
```

## 📚 Documentation

### Getting Started
- **[Install](install.md)** - Pixi / uv setup and troubleshooting
- **[Runtime Guide (Canonical)](guide_runtime.md)** - FlowContext → IR → execute_ir, event/time model
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
with FlowContext("my_pipeline") as ctx:
    ...

# Validate to IR
ir = validate(ctx)

# Execute on a backend
execute_ir(ir, backend="multiprocessing")
```

### Multi-Backend Execution
- **Development**: Sequential execution for debugging
- **Testing**: Parallel execution for performance
- **Production**: Distributed execution with dora-rs

### Registry System
```python
# IR-first pipeline registry
from retriever.core.pipeline_registry import register_pipeline, build_ir
from retriever.core.flow import FlowContext

@register_pipeline("my_pipeline", overwrite=True)
def build():
    with FlowContext("my_pipeline") as ctx:
        ...
        return ctx

ir = build_ir("my_pipeline")
```

---

**Ready to start?** → [README.md](README.md) | **Deep dive** → [architecture.md](architecture.md)
