# Retriever Framework Developer Guide

**Comprehensive guide for contributing to and developing with Retriever**

> **New Contributors**: Start with [contributing.md](contributing.md) for setup and workflow basics, then return here for advanced development topics.

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

- **Python 3.10–3.12** (avoid 3.14; some deps lack wheels)
- **Pixi** (recommended) or **uv**/**pip** for dependency management
- **VS Code** (recommended) with Python extension
- **Git** with pre-commit hooks

### Quick Setup

```bash
# Clone and install
git clone <repository-url>
cd Retriever

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
  - Types: `mypy retriever`

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
pixi run mypy retriever
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
export RETRIEVER_BACKEND=local  # local, dora, distributed

# Testing configuration
export RETRIEVER_TEST_DATA=/path/to/test/data
export RETRIEVER_SKIP_SLOW_TESTS=true
```

## Architecture Overview

Retriever follows a **type-safe, composable architecture** inspired by PyTorch's success in deep learning:

### Core Design Principles

1. **Type Safety First**: Catch errors at development time, not runtime
2. **Composable Modules**: Build complex systems from simple, reusable components  
3. **Execution Flexibility**: Same code works across different backends
4. **Declarative Pipelines**: Describe what to do, not how to execute it

### Three-Layer Hierarchy

```python
# Layer 1: Module[I, O] - Atomic functions
def detect_objects(image: RGBImage) -> List[Detection]:
    return yolo_model.predict(image)

# Layer 2: Flow[X, Y] - Composable steps
detection_flow = Flow.from_module(detect_objects)

# Layer 3: Pipeline - Complete workflows
manipulation_pipeline = (
    camera_flow >> detection_flow >> planning_flow >> execution_flow
)
```

### Framework Components

- **`retriever/`**: Flow system, execution engines, type system
- **`retriever/perception/`**: Object detection, tracking, grounding
- **`retriever/planning/`**: Task planning, VLM integration, DSPy optimization  
- **`retriever/robots/`**: Platform integrations (Spot, UR5, simulation)
- **`retriever/skills/`**: Reusable robot capabilities and learned behaviors
- **`retriever/integrations/`**: External system integrations (dora, Ray, etc.)

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
   touch retriever/new_module.py
   
   # Run tests continuously
   pixi run python -m pytest --maxfail=1 --lf
   ```

3. **Quality Assurance**
   ```bash
   # Common checks
   pixi run ruff check .
   pixi run black .
   pixi run mypy retriever
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
from typing import List, Dict, Optional, Protocol
from retriever.types import Module, Flow, Eff

class MyComponent(Module[InputType, OutputType]):
    def __call__(self, input_data: InputType) -> OutputType:
        # Implementation with full type coverage
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

The heart of Retriever's composability:

```python
from retriever.flow import Flow
from retriever.executor import LocalExecutor

# Create reusable components
def my_perception_module(image: RGBImage) -> List[Detection]:
    # Implementation
    return detections

# Lift into Flow system
perception_flow = Flow.from_module(my_perception_module)

# Compose with other flows
pipeline = perception_flow >> planning_flow >> execution_flow

# Execute
executor = LocalExecutor()
result = executor.execute_sync(pipeline, input_data)
```

### Stateful Operations with Eff

For robot operations that modify state:

```python
from retriever.types import Eff
from dataclasses import dataclass

@dataclass(frozen=True)
class RobotState:
    position: Pose3D
    battery_level: float
    objects_held: List[str]

def move_robot_eff(target: Pose3D) -> Eff[RobotState, bool]:
    def run(state: RobotState) -> tuple[bool, RobotState]:
        # Check preconditions
        if state.battery_level < 0.1:
            return False, state._replace(last_error="Low battery")
        
        # Execute movement
        success = robot_controller.move_to(target)
        new_state = state._replace(
            position=target if success else state.position,
            battery_level=max(0, state.battery_level - 0.05)
        )
        return success, new_state
    return Eff(run)

# Compose stateful operations
mission = move_robot_eff >> pick_object_eff >> place_object_eff

# Execute with state tracking
initial_state = RobotState(position=home_pose, battery_level=1.0, objects_held=[])
success, final_state = executor.execute_eff(mission, target_data, initial_state)
```

### Multi-Backend Execution

Design for flexibility across execution environments:

```python
# Development: Pure Python sequential execution
retriever.init(backend="sequential")

# Testing: Parallel execution on single machine
retriever.init(backend="local_parallel")

# Production: Distributed execution
retriever.init(backend="dora", config="cluster_config.yaml")

# Same pipeline code works across all backends
result = pipeline.execute(input_data)
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
    double = Flow.from_module(lambda x: x * 2)
    add_one = Flow.from_module(lambda x: x + 1)
    pipeline = double >> add_one  # Using operator syntax
    
    executor = LocalExecutor()
    result = executor.execute_sync(pipeline, 5)
    assert result == 11  # (5 * 2) + 1

def test_stateful_operation():
    """Test Eff monad for stateful operations."""
    initial_state = RobotState(battery_level=0.5, position=Pose3D(0, 0, 0))
    
    move_eff = move_robot_eff(Pose3D(1, 0, 0))
    success, final_state = move_eff.run(initial_state)
    
    assert success == True
    assert final_state.position == Pose3D(1, 0, 0)
    assert final_state.battery_level < initial_state.battery_level
```

**Integration Tests**:
```python
@pytest.mark.integration
def test_complete_manipulation_pipeline():
    """Test end-to-end manipulation pipeline."""
    pipeline = build_manipulation_pipeline()
    executor = LocalExecutor()
    
    # Test with realistic data
    test_image = load_test_image("manipulation_scene.jpg")
    result = executor.execute_sync(pipeline, test_image)
    
    assert isinstance(result, ManipulationResult)
    assert result.success == True
    assert len(result.executed_actions) > 0
```

**Performance Tests**:
```python
@pytest.mark.performance
def test_pipeline_throughput():
    """Test system performance under load."""
    pipeline = build_perception_pipeline()
    executor = LocalExecutor()
    
    start_time = time.time()
    results = []
    
    for i in range(100):
        result = executor.execute_sync(pipeline, test_data)
        results.append(result)
    
    total_time = time.time() - start_time
    throughput = len(results) / total_time
    
    assert throughput >= 10.0, f"Expected ≥10 Hz, got {throughput:.1f} Hz"
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
          pixi run mypy retriever
          pixi run python -m pytest
      - name: Run performance tests
        run: pixi run python -m pytest --performance
```

## Contributing Guidelines

> **Quick Start**: See [contributing.md](contributing.md) for complete contribution workflow, setup, and standards.

### Adding New Components

1. **Follow Module Protocol**:
   ```python
   class NewComponent(Module[InputType, OutputType]):
       def __call__(self, input_data: InputType) -> OutputType:
           # Implementation
           return output
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
   pixi run mypy retriever  # Must pass mypy
   ```

### Adding Robot Integrations

1. **Create Robot Package**: `retriever/robots/new_robot/`
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
3. **Add Skills**: `retriever/skills/new_robot/`
4. **Create Tests**: `tests/robots/test_new_robot.py`
5. **Update Configuration**: Add to robot registry

### Adding Execution Backends

1. **Implement Executor Interface**:
   ```python
   class NewExecutor:
       def execute_sync(self, flow: Flow[I, O], input_data: I) -> O:
           # Implementation
           pass
       
       async def execute_async(self, flow: Flow[I, O], input_data: I) -> O:
           # Implementation  
           pass
   ```

2. **Add Performance Benchmarks**:
   ```python
   def benchmark_new_executor():
       # Compare against LocalExecutor baseline
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
    
    result = executor.execute_sync(pipeline, test_data)
    
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

### Custom Flow Operations

**Creating New Composition Operations**:
```python
def conditional_then(self, condition_func, true_flow, false_flow):
    """Conditional composition based on runtime data."""
    def conditional_module(input_data):
        if condition_func(input_data):
            return true_flow.execute(input_data)
        else:
            return false_flow.execute(input_data)
    
    return Flow.from_module(conditional_module)

# Add to Flow class
Flow.conditional_then = conditional_then
```

### Integration with External Systems

**Ray Integration for Distributed Models**:
```python
import ray
from retriever.integrations.ray import RayModelServer

@ray.remote
class DistributedYOLO:
    def predict(self, image: RGBImage) -> List[Detection]:
        return self.model.predict(image)

# Integrate with Flow system
ray_yolo = RayModelServer(DistributedYOLO)
detection_flow = Flow.from_module(ray_yolo.predict)
```

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
# Flow[Image, Detection].then(Flow[String, Result])  # ERROR

# Fix: Ensure output type matches input type
# Flow[Image, Detection].then(Flow[Detection, Result])  # OK

# Use explicit type annotations
detection_flow: Flow[RGBImage, List[Detection]] = Flow.from_module(detect_objects)
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

# Enable flow execution tracing
from retriever.debug import enable_flow_tracing
enable_flow_tracing()
```

### Getting Help

1. **Check Documentation**: Start with relevant guide sections
2. **Search Issues**: Look through GitHub issues for similar problems
3. **Run Diagnostics**: Try `ruff check .`, `mypy retriever`, and `python -m pytest`
4. **Check Examples**: Look at working examples in `examples/` directory
5. **Ask for Help**: Create detailed GitHub issue with reproduction steps

## Resources

### Documentation
- [Flow System Guide](guide_flow.md) - Complete Flow architecture reference
- [Architecture Guide](architecture.md) - Complete technical architecture
- [API Reference](API.md) - Complete API documentation
- [Spot Setup](robots/spot_setup.md) - Spot configuration

### Examples
- `examples/simple_flow.py` - Basic flow composition
- `examples/stateful_robot.py` - Robot state management
- `examples/distributed_execution.py` - Multi-backend deployment

### External Resources
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Pre-commit Hooks](https://pre-commit.com/)

## Next Steps

After reading this guide:

1. **Set up your environment**: follow `docs/install.md`
2. **Run the test suite**: `python -m pytest`
3. **Try the examples**: Start with `examples/simple_flow.py`
4. **Read the architecture guide**: [architecture.md](architecture.md) for technical details
5. **Start contributing**: Pick an issue and follow the contribution workflow

The Retriever framework is designed to make robotics development faster, safer, and more composable. We welcome contributions from the community! 🤖
