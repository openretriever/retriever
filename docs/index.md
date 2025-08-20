# 🐕 Retriever Framework

**Type-safe, composable framework for production robotics**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever provides PyTorch-like abstractions for robotics development, combining type safety, composability, and execution flexibility for building production robot systems.

## Quick Start

```python
from retriever.core.flow import Flow
from retriever.core.executor import LocalExecutor

# Build a robotics pipeline
perception = (
    Flow.from_module(detect_objects)
    .then(Flow.from_module(estimate_poses))
    .then(Flow.from_module(plan_actions))
)

# Execute
executor = LocalExecutor()
result = executor.execute_sync(perception, sensor_data)
```

## 📚 Documentation

### Core Documentation
- **[README.md](README.md)** - Quick start, installation, and overview
- **[architecture.md](architecture.md)** - Complete technical architecture and design philosophy
- **[api.md](api.md)** - Complete API reference with examples

### Development Guides  
- **[guide_flow.md](guide_flow.md)** - Flow system detailed reference and patterns
- **[guide_dev.md](guide_dev.md)** - Developer guide and contribution workflows
- **[contributing.md](contributing.md)** - How to contribute to the project

### Quick Navigation
- **Getting Started**: [README.md](README.md#quick-start)
- **Architecture**: [architecture.md](architecture.md#core-architecture)
- **Examples**: `examples/` directory and `tests/core/`
- **Registry System**: [architecture.md](architecture.md#registry-ecosystem)

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

### Three-Layer Hierarchy
```python
# Layer 1: Module[I, O] - Atomic functions
def detect_objects(image: RGBImage) -> List[Detection]: ...

# Layer 2: Flow[X, Y] - Composable steps  
detection_flow = Flow.from_module(detect_objects)

# Layer 3: Pipeline - Complete workflows
manipulation_pipeline = camera_flow >> detection_flow >> planning_flow
```

### Multi-Backend Execution
- **Development**: Sequential execution for debugging
- **Testing**: Parallel execution for performance
- **Production**: Distributed execution with dora-rs

### Registry System
```python
# PyTorch-style component access
camera = get_flow("camera")
detector = get_flow("yolo_detector")
pipeline = camera >> detector
```

---

**Ready to start?** → [README.md](README.md) | **Deep dive** → [architecture.md](architecture.md)