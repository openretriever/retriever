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
pixi run demo-dora
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

# Full system stack (models/robots/training/Ray) is being split into a separate
# Golden Retriever repository. Templates live in:
# - pixi-golden.toml
# - pyproject-golden.toml
```

## Development Environment

### VS Code Configuration

Launch configurations for common development tasks:

- **Run: [Flow] Demo Pipeline** - Basic flow demonstration
- **Run: [Planning] Oracle Example** - Complete planning example
- **Test: [Core] Flow System** - Core framework tests
- **Debug: [Integration] Full Pipeline** - End-to-end debugging

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

### Documentation (MkDocs)

MkDocs config lives in `mkdocs.yml`, with pages under `docs/`.

```bash
# Install mkdocs tooling (in your active env)
python -m pip install mkdocs mkdocs-material mkdocs-git-revision-date-localized-plugin mkdocs-minify-plugin

# Serve docs locally
mkdocs serve

# Build static site
mkdocs build
```

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
- **`src/retriever/types/`**: shared typed payloads, schema helpers, and registry surface
- **`src/retriever/recording.py`**: persisted `.mcap` / `.rrd` recording and replay helpers
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
# Use backend="dora" explicitly for dora deployment/parity.

# In-process debugging
pipe.step(dt=0.1)
pipe.close_stepper()
```

## Testing & Quality Assurance

### Test Organization

```
tests/
├── core/                  # Core framework tests
│   ├── test_flow.py      # Flow composition tests
│   ├── test_executor.py  # Execution engine tests
│   └── test_types.py     # Type system tests
├── perception/            # Perception system tests
├── planning/              # Planning system tests
├── integration/           # End-to-end integration tests
├── performance/           # Performance and benchmark tests
└── fixtures/              # Shared test data and utilities
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

**Performance Tests**:
```python
@pytest.mark.performance
def test_pipeline_throughput():
    """Test system performance under load."""
    pipe = build_demo_pipeline()
    for _ in range(100):
        pipe.step(dt=0.02)
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
      - name: Run performance tests
        run: pixi run python -m pytest --performance
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

System-layer robot integrations belong under `src/golden_retriever/` or in an external package.
Only runtime-agnostic interfaces and backend hooks should live in the core runtime repo.

1. **Create Robot Package**: `src/golden_retriever/robots/new_robot/`
2. **Implement Robot Interface**:
   ```python
   class NewRobotInterface:
       def move_to(self, pose: Pose3D) -> bool:
           # Implementation
           pass
       
       def get_state(self) -> RobotState:
           # Implementation
           pass
   ```
3. **Add Skills**: `src/golden_retriever/skills/new_robot/`
4. **Create Tests**: `src/golden_retriever/tests/test_new_robot.py`
5. **Update Configuration**: Add to robot registry

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
# Monitor memory during execution
pixi run python -m pytest --memray

# Memory profiling for specific components
python -m memray run --live examples/memory_test.py
```

### Extending the Runtime

For core runtime work, prefer explicit extension points over monkey-patching:

- add adapters in `src/retriever/flow/adapter.py`
- add clocks in `src/retriever/flow/clock.py`
- add builder/validation behavior in `src/retriever/flow/builder.py`
- add runtime backends under `src/retriever/rt/backend/`

External systems such as Ray, hardware SDKs, or model-serving stacks should usually live in
`src/golden_retriever/` or external packages and integrate with the runtime through normal `Flow`
wrappers and typed `@io` envelopes.

## Troubleshooting

### Common Development Issues

**Import Errors**:
```bash
# Ensure proper installation
pixi run python -m pip install -e .

# Check Python path
export PYTHONPATH=/path/to/Retriever:$PYTHONPATH

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
pixi run python -m pytest --profile

# Check for memory leaks
pixi run python -m pytest --memray

# Benchmark against baseline
pixi run python -m pytest --benchmark
```

**Testing Failures**:
```bash
# Run specific test module
pixi run python -m pytest tests/core/test_flow.py

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

1. **Set up your environment**: follow `docs/install.md`
2. **Run the test suite**: `python -m pytest`
3. **Try the examples**: start with `examples/tutorial/a_flow_fundamentals/01_basic_flow.py`
4. **Read the architecture guide**: [architecture.md](../architecture.md) for technical details
5. **Start contributing**: Pick an issue and follow the contribution workflow
