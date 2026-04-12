---
title: "Retriever Runtime Developer Guide"
---

# Retriever Runtime Developer Guide

**Comprehensive guide for contributing to the core Retriever runtime**

> **New Contributors**: Start with [contributing.md](../contributing.md) for setup and workflow basics, then return here for advanced development topics.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Architecture Overview](#architecture-overview)
4. [Development Workflow](#development-workflow)
5. [Core Framework Components](#core-framework-components)
6. [Testing & Quality Assurance](#testing--quality-assurance)
7. [Contributing Guidelines](#contributing-guidelines)
8. [Advanced Development](#advanced-development)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- **Python 3.11** (current pinned runtime baseline)
- **Pixi** (recommended) or **uv**/**pip** for dependency management
- **VS Code** (recommended) with Python extension
- **Git** with pre-commit hooks

### Quick Setup

```bash
# Clone and install
git clone <repository-url>
cd <repo-root>

# Option A: Pixi (quick demo env defined in pixi.toml)
pixi run demo-webcam-detection
pixi run demo-webcam-detection-mp-rerun
pixi run python -m pip install -e '.[dev]'   # dev tooling inside Pixi env

# Option B: uv (in your own venv/conda env)
# uv pip install -e '.[dev]'

# Verify installation
pixi run python -m pytest tests/core -q  # Pixi
# python -m pytest tests/core -q         # uv/pip (after activating your env)
```

### Command Conventions

Command conventions:
- Prefer Pixi: `pixi run <command>` (uses the Pixi environment)
- Or run tools directly after activating your env:
  - Tests: `python -m pytest`
  - Lint: `ruff check .`
  - Format: `black .`
  - Types: `mypy src/retriever`

### Development Dependencies

```bash
# Core development tools (inside Pixi env)
pixi run python -m pip install -e '.[dev]'

# Additional system-level repos may carry their own environment templates.
# This repository documents only the runtime/core development surface.
```

## Development Environment

### VS Code Configuration

Launch configurations in `.vscode/launch.json` target the maintained tutorial modules directly:

- `examples.tutorial.c_debug_and_replay.01_debug_stepper`
- `examples.tutorial.c_debug_and_replay.02_debug_perception_stepper`
- `examples.tutorial.c_debug_and_replay.03_debug_perception_stepper_real_camera`
- `examples.tutorial.c_debug_and_replay.04_record_replay_perception`

### Pre-commit Setup

```bash
# Install pre-commit hooks
pixi run pre-commit install

# Run manually
pixi run pre-commit run --all-files

# Common QA commands
pixi run ruff check .
pixi run black .
pixi run mypy src/retriever
pixi run python -m pytest
```

### Documentation

Public docs are authored as markdown under `docs/` with tutorial track pages in `docs/tutorials/`.

Current repo note:
- A checked-in `mkdocs.yml` is not present right now.
- Use repo markdown files directly as the source of truth.

### Environment Variables

```bash
# Development configuration
export RETRIEVER_ENV=development
export RETRIEVER_LOG_LEVEL=DEBUG
export RETRIEVER_BACKEND=multiprocessing  # multiprocessing, dora, in-process

# Testing configuration
export RETRIEVER_TEST_DATA=/path/to/test/data
export RETRIEVER_SKIP_SLOW_TESTS=true
```

## Architecture Overview

Retriever runtime follows a **type-safe, composable architecture** for typed dataflow execution:

### Core Design Principles

1. **Type Safety First**: Catch errors at development time, not runtime
2. **Composable Modules**: Build complex systems from simple, reusable components  
3. **Execution Flexibility**: Same code works across different backends
4. **Declarative Pipelines**: Describe what to do, not how to execute it

### Runtime Authoring Hierarchy

```python
from retriever.flow import Flow, Pipeline, Rate, Trigger, io


@io
class CameraFrame:
    image: "np.ndarray"


@io
class Detections:
    boxes: list


class DetectionFlow(Flow[CameraFrame, Detections]):
    def step(self, image: CameraFrame) -> Detections:
        return Detections(boxes=[])


pipe = Pipeline("perception")
with pipe:
    camera = CameraSource() @ Rate(hz=20)
    detect = DetectionFlow() @ Trigger("image")
    camera >> detect

```

### Framework Components

- **`src/retriever/flow/`**: authoring surface, clocks, adapters, pipeline wiring
- **`src/retriever/ir/`**: logical IR and execution graph structures
- **`src/retriever/rt/`**: runtime execution, stepper, multiprocessing, dora
- **`src/retriever/types/data/`**: explicit dataset/event/export contracts
- **`src/retriever/types/spatial/`**: typed spatial boundary payloads
- **`examples/tutorial/`**: public runnable examples for the runtime release

## Development Workflow

### Feature Development Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-capability-YYYY-MM-DD
   ```

2. **Implement with TDD**
   ```bash
   # Write tests first
   touch tests/test_new_capability.py
   
   # Implement feature
   touch src/retriever/new_module.py
   
   # Run tests continuously
   pixi run python -m pytest --maxfail=1 --lf
   ```

3. **Quality Assurance**
   ```bash
   # Common checks
   pixi run ruff check .
   pixi run black .
   pixi run mypy src/retriever
   pixi run python -m pytest
   ```

4. **Documentation**
   ```bash
   # Update relevant documentation
   # Add docstrings with examples
   # Update guide if significant changes
   ```

5. **Submit for Review**
   ```bash
   git push origin feature/new-capability-YYYY-MM-DD
   # Create pull request with clear description
   ```

### Code Quality Standards

**Type Annotations Required**:
```python
from retriever.flow import Flow

class MyFlow(Flow[InputType, OutputType]):
    def step(self, input_data: InputType) -> OutputType:
        return output
```

**Testing Standards**:
```python
def test_component_basic_functionality():
    """Test core functionality with realistic inputs."""
    component = MyComponent()
    result = component(test_input)
    assert result == expected_output

def test_component_edge_cases():
    """Test error conditions and edge cases."""
    component = MyComponent()
    with pytest.raises(ValueError):
        component(invalid_input)
```

**Documentation Standards**:
```python
def process_sensor_data(data: SensorData) -> ProcessedData:
    """Process raw sensor data into structured format.
    
    Args:
        data: Raw sensor readings from robot sensors
        
    Returns:
        Processed data ready for perception pipeline
        
    Example:
        >>> sensor_data = capture_sensors()
        >>> processed = process_sensor_data(sensor_data)
        >>> assert processed.timestamp == sensor_data.timestamp
    """
```

## Core Framework Components

### Flow System

The canonical runtime loop is:

1. define typed envelopes with `@io`
2. implement `Flow[I, O]`
3. wire a `Pipeline`
4. run with `pipe.run(...)` or debug with `pipe.step(...)`

```python
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@io
class Observation:
    value: float


@io
class Command:
    action: float


class Controller(Flow[Observation, Command]):
    def step(self, input: Observation) -> Command:
        return Command(action=input.value * 0.1)


pipe = Pipeline("control")
sensor = SensorFlow() @ Rate(hz=50)
controller = Controller() @ Trigger("value")
pipe.connect(sensor, controller, sync=Latest())
pipe.run(backend="multiprocessing", duration=2.0)
```

### Stateful Flows

For public runtime examples, keep state either:

- inside the `Flow` instance (`self.counter`, cached models, controller state), or
- explicit in typed input/output envelopes when state must cross node boundaries.

Historical Eff-style examples still exist in the repo for migration context, but they are not the canonical runtime API.

### Multi-Backend Execution

Use the same authored pipeline across the supported execution surfaces:

```python
pipe.run(backend="multiprocessing", duration=2.0)
pipe.run(backend="dora", duration=2.0)

# In-process debugging
pipe.step(dt=0.1)
pipe.close_stepper()
```

## Testing & Quality Assurance

### Test Organization

```
tests/
├── core/                  # Runtime-facing regression tests (default pytest target)
├── examples/              # Tutorial/example checks
├── flow/                  # Flow composition and ergonomics tests
├── integration/           # End-to-end runtime checks
├── ir/                    # IR analysis / lowering / visualization checks
├── planning/              # Planning-oriented tests
└── images/                # Static image fixtures used by tests
```

### Writing Effective Tests

**Unit Tests for Components**:
```python
def test_flow_composition():
    """Test basic flow composition and type safety."""
    pipe = build_demo_pipeline()
    step = pipe.step(dt=0.1)
    assert "AddOne" in step.executed
    pipe.close_stepper()
```

**Integration Tests**:
```python
@pytest.mark.integration
def test_complete_manipulation_pipeline():
    """Test a real pipeline on the multiprocessing backend."""
    pipe = build_demo_pipeline()
    engine = pipe.run(backend="multiprocessing", duration=0.5, blocking=False)
    engine.stop()
```

**Focused Runtime Regression Tests**:
```python
def test_pipeline_runtime_regression():
    """Keep the default runtime surface stable."""
    pipe = build_demo_pipeline()
    step = pipe.step(dt=0.02)
    assert step.now is not None
    pipe.close_stepper()
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install pixi
        run: curl -fsSL https://pixi.sh/install.sh | bash
      - name: Install environment
        run: pixi install
      - name: Run quality checks
        run: |
          pixi run ruff check .
          pixi run black .
          pixi run mypy src/retriever
          pixi run python -m pytest
      - name: Run focused runtime sweep
        run: pixi run python -m pytest tests/core/test_public_surface_rt.py tests/core/test_pipeline_step_rt.py
```

## Contributing Guidelines

> **Quick Start**: See [contributing.md](../contributing.md) for complete contribution workflow, setup, and standards.

### Adding New Components

1. **Follow the public runtime surface**:
   ```python
   from retriever.flow import Flow, io

   @io
   class Input:
       value: float

   @io
   class Output:
       result: float

   class NewComponent(Flow[Input, Output]):
       def step(self, input_data: Input) -> Output:
           return Output(result=input_data.value)
   ```

2. **Add Comprehensive Tests**:
   ```python
   def test_new_component():
       component = NewComponent()
       result = component(test_input)
       assert result == expected_output
   ```

3. **Update Documentation**:
   - Add docstrings with examples
   - Update relevant README files
   - Add to developer guide if significant

4. **Ensure Type Safety**:
   ```bash
   pixi run mypy src/retriever  # Must pass mypy
   ```

### Adding Robot Integrations

System-level robot integrations belong in external robot-integration packages.
This runtime repository should only keep runtime-agnostic interfaces, typed payloads, adapters, clocks, builders, and backend hooks.

A good extension boundary is:
1. define typed payloads and registry metadata here only if they are runtime-generic
2. wrap the external SDK or robot API in normal `Flow` classes outside this repo
3. keep hardware-, simulator-, and model-stack code out of this repository

### Adding Execution Backends

1. **Implement Executor Function**:
   ```python
   def execute_my_backend(ir: IR, **kwargs):
       # Compile IR to backend-specific graph
       graph = compile_to_my_backend(ir)
       # Execute
       graph.run()
   ```

2. **Add Performance Benchmarks**:
   ```python
   def benchmark_new_executor():
       # Compare against multiprocessing / dora baselines
       pass
   ```

3. **Update Documentation**: Add to execution backend guide

## Advanced Development

### Performance Optimization

**Profiling Pipelines**:
```python
import cProfile
import pstats

def profile_pipeline():
    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(100):
        pipe.step(dt=0.02)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(20)
```

**Memory Usage Analysis**:
```bash
# This repo does not currently ship a blessed memray workflow.
# Prefer cProfile for checked-in examples, or add a local profiler in your own environment.
```

### Extending the Runtime

For core runtime work, prefer explicit extension points over monkey-patching:

- add adapters in `src/retriever/flow/adapter.py`
- add clocks in `src/retriever/flow/clock.py`
- add builder/validation behavior in `src/retriever/flow/builder.py`
- add runtime backends under `src/retriever/rt/backend/`

External systems such as Ray, hardware SDKs, or model-serving stacks should usually live in external packages and integrate with the runtime through normal `Flow` wrappers and typed `@io` envelopes.

## Troubleshooting

### Common Development Issues

**Import Errors**:
```bash
# Ensure proper installation
pixi run python -m pip install -e .

# Check Python path
export PYTHONPATH=/path/to/Retriever/src:$PYTHONPATH

# Verify installation
python -c "import retriever; print(retriever.__version__)"
```

**Type Checking Failures**:
```python
# Common mypy issues and fixes

# Issue: Type mismatch in flow composition
# Flow[Image, Detection] -> Flow[String, Result]  # ERROR

# Fix: Ensure output type matches input type
# Flow[Image, Detection] -> Flow[Detection, Result]  # OK

# Use explicit IO envelopes and Flow type parameters
# class Detect(Flow[Image, Detection]): ...
```

**Performance Issues**:
```bash
# Profile execution
pixi run python -m examples.tutorial.b_ir_and_execution.09_backend_parity_benchmark

# Or run a focused test module under the debugger / profiler of your choice
pixi run python -m pytest tests/core/test_pipeline_step_rt.py -v
```

**Testing Failures**:
```bash
# Run specific test module
pixi run python -m pytest tests/core/test_pipeline_step_rt.py

# Run with verbose output
pixi run python -m pytest -v

# Run with debugging
pixi run python -m pytest --pdb
```

### Debug Mode

Enable detailed logging and debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Component-specific logging
logger = logging.getLogger("retriever.flow")
logger.setLevel(logging.DEBUG)
```

### Getting Help

1. **Check Documentation**: Start with relevant guide sections
2. **Search Issues**: Look through GitHub issues for similar problems
3. **Run Diagnostics**: Try `ruff check .`, `mypy src/retriever`, and `python -m pytest`
4. **Check Examples**: Look at working examples in `examples/` directory
5. **Ask for Help**: Create detailed GitHub issue with reproduction steps

## Resources

### Documentation
- [Flow System Guide](../guide_flow.md) - Complete Flow architecture reference
- [Runtime Guide](../guide_runtime.md) - End-to-end runtime workflow
- [Architecture Guide](../architecture.md) - Complete technical architecture
- [API Reference](../API.md) - Complete API documentation
- [Handbook](../handbook.md) - Single canonical runtime note

### Examples
- `examples/tutorial/a_flow_fundamentals/01_basic_flow.py` - Basic flow composition
- `examples/tutorial/b_ir_and_execution/03_execution_build.py` - IR and execution graph build
- `examples/tutorial/c_debug_and_replay/01_debug_stepper.py` - In-process debugging

### External Resources
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Pre-commit Hooks](https://pre-commit.com/)

## Next Steps

After reading this guide:

1. **Set up your environment**: follow `docs/getting_started/install.md`
2. **Run the test suite**: `python -m pytest`
3. **Try the examples**: start with `examples/tutorial/a_flow_fundamentals/01_basic_flow.py`
4. **Read the architecture guide**: [architecture.md](../architecture.md) for technical details
5. **Start contributing**: Pick an issue and follow the contribution workflow
