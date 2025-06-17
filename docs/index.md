# 🐕 Retriever

**Type-safe robotics pipeline framework with Flow-based composition**

<div align="center">
  <strong>Retriever</strong>
</div>

Retriever is a framework for building type-safe robotics pipelines with composable Flow architecture.

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
result = executor.run(perception, sensor_data)
```

## Documentation

📖 **[Complete Guide](README.md)** - Installation, usage, examples, and architecture  
📚 **[API Reference](API.md)** - Technical reference for classes and methods

### Quick Links
- **Installation**: `git clone ... && pip install -e '.[dev]'`
- **Examples**: `tests/core/test_flow_executor.py` - Real robotics examples
- **Configuration**: YAML + CLI overrides in `configs/`

## Current Status

**✅ Implemented**:
- Core Flow system with comprehensive test suite (32+ tests)
- LocalExecutor for development and testing
- LLM planning integration (OpenAI/Gemini)
- Configuration system with YAML + CLI

**🚧 Next**:
- Perception modules (object detection, pose estimation)
- Robot hardware interfaces (Spot, etc.)
- High-performance executors (dora-rs integration for 10x speedup)

## Architecture

**Hierarchy**: Module → Flow → Pipeline  
**Execution**: LocalExecutor (current) → DoraExecutor (10x speedup) → RayExecutor (massive scale)  
**Focus**: Type-safe development with clear migration to production performance

---

**Get Started**: See [README.md](README.md) for complete documentation