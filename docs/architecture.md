# Retriever Framework Architecture

**Complete technical architecture guide for the Retriever robotics framework**

---

## Table of Contents

1. [Overview](#overview)
2. [Core Architecture](#core-architecture)
3. [Flow System Design](#flow-system-design)
4. [Registry Ecosystem](#registry-ecosystem)
5. [Execution Backends](#execution-backends)
6. [Type System](#type-system)
7. [State Management](#state-management)
8. [Production Patterns](#production-patterns)

---

## Overview

Retriever is a **type-safe, composable framework for production robotics** that provides PyTorch-like abstractions for building, testing, and deploying robot systems. The framework bridges the gap between rapid prototyping and production deployment through a unified programming model.

### Design Philosophy

**"PyTorch for Robotics"** - Just as PyTorch revolutionized deep learning with simple, composable abstractions, Retriever provides the same experience for robotics:

- **Type-Safe Composition**: Catch errors at development time, not runtime
- **Execution Flexibility**: Same code works across sequential, parallel, and distributed backends
- **Component Reusability**: Share and discover robotics components like PyTorch models
- **Production Ready**: Direct path from prototype to deployed system

### Core Value Proposition

```python
# Write simple, testable components
class ObjectDetector(Flow[RGBImage, List[Detection]]):
    def run(self, image: RGBImage) -> List[Detection]:
        return self.yolo.predict(image)

# Compose into complex systems
manipulation_pipeline = (
    camera_flow >> detection_flow >> planning_flow >> execution_flow
)

# Execute across different backends
# Development: Sequential execution
result = LocalExecutor().execute_sync(pipeline, input_data)

# Production: Distributed execution  
result = DoraExecutor().execute(pipeline, input_data)
```

---

## Core Architecture

### Three-Layer Hierarchy

Retriever uses a natural progression that matches how roboticists think about systems:

#### Layer 1: Module[I, O] - Atomic Functions
```python
from typing import Protocol, TypeVar

I = TypeVar("I")
O = TypeVar("O")

class Module(Protocol[I, O]):
    """Single typed callable function."""
    def __call__(self, inp: I) -> O: ...

# Any function is a Module
def detect_objects(image: RGBImage) -> List[Detection]: ...
def plan_motion(poses: List[Pose3D]) -> MotionPlan: ...
```

#### Layer 2: Flow[X, Y] - Composable Steps
```python
# Lift functions into composition system
detection_flow = Flow.from_module(detect_objects)
planning_flow = Flow.from_module(plan_motion)

# Individual flows represent processing steps
print(type(detection_flow))  # Flow[RGBImage, List[Detection]]
```

#### Layer 3: Pipeline - Complete Workflows
```python
# Compose flows into end-to-end workflows
manipulation_pipeline = detection_flow >> planning_flow >> execution_flow

# Pipeline represents complete system
print(type(manipulation_pipeline))  # Flow[RGBImage, ExecutionResult]
```

### Composition Operations

#### Sequential Composition: `>>`
Chain operations where output of first becomes input of second:
```python
# Mathematical operator syntax
perception_to_action = camera >> detection >> planning >> control

# Method syntax for clarity
perception_to_action = (
    camera.then(detection)
    .then(planning) 
    .then(control)
)
```

#### Parallel Composition: `&`
Process same input through multiple paths:
```python
# Parallel sensor processing
sensor_fusion = (lidar_flow & camera_flow & imu_flow) >> fusion_flow

# Parallel planning with selection
planning_system = (
    (primary_planner & backup_planner)
    >> selection_flow
)
```

---

## Flow System Design

### Flow Compilation Approach

The framework uses a **compilation approach** rather than exposing FRP primitives directly:

**Simple Interface (What Users Write)**:
```python
@flow(rate="30hz")
class CameraFlow(Flow[None, RGBImage]):
    def run(self, _: None) -> RGBImage:
        return self.camera.capture()
```

**Hidden Complexity (Framework Handles)**:
```python
# Framework automatically creates FRP behaviors
engine = FRPEngine()
camera_behavior = engine.create_behavior(CameraFlow())  # Hidden from users
```

### Rate Annotations and Timing

Flows can specify execution rates for temporal coordination:

```python
@flow(rate="30hz")    # 30 Hz camera capture
class CameraFlow(Flow[None, RGBImage]): ...

@flow(rate="10hz")    # 10 Hz object detection
class DetectionFlow(Flow[RGBImage, List[Detection]]): ...

@flow(rate="1hz")     # 1 Hz high-level planning
class PlanningFlow(Flow[List[Detection], Plan]): ...
```

**Framework Benefits**:
- Automatic rate coordination between components
- Buffering and synchronization handled transparently
- Different execution rates for optimal performance

### Class-Based Flow Design

Flows are implemented as classes for maximum flexibility:

```python
class AdvancedDetector(Flow[RGBImage, List[Detection]]):
    def __init__(self, model_name: str = "yolo", confidence: float = 0.5):
        super().__init__()
        self.model = load_model(model_name)
        self.confidence = confidence
        
    def run(self, image: RGBImage) -> List[Detection]:
        detections = self.model.predict(image)
        return [d for d in detections if d.confidence >= self.confidence]
    
    def cleanup(self):
        self.model.release_resources()
```

**Benefits of Class-Based Design**:
- **Configuration**: Constructor parameters for customization
- **State Management**: Instance variables for component state
- **Resource Management**: Cleanup methods for proper disposal
- **Testing**: Easy to mock and unit test
- **Reusability**: Share configured components across projects

---

## Registry Ecosystem

### Component Discovery System

Inspired by PyTorch's model registries, Retriever provides unified component discovery:

#### Type Registry
```python
from retriever import register_type, get_type, list_types

# Register custom types
@register_type(description="Custom sensor data")
@dataclass
class CustomSensorData:
    readings: np.ndarray
    timestamp: float

# Discover and use types
RGBImage = get_type('RGBImage')
all_types = list_types(category='vision')
```

#### Flow Registry
```python
from retriever import register_flow, get_flow, list_flows

# Register flow components
@register_flow("yolo_detector", category="vision")
class YOLODetector(Flow[RGBImage, List[Detection]]): ...

# Discover and substitute flows
detector = get_flow("yolo_detector")
all_vision_flows = list_flows(category="vision")
```

#### Pipeline Registry
```python
from retriever import register_pipeline, get_pipeline, list_pipelines

# Register complete systems
manipulation_pipeline = camera >> detector >> planner >> executor
register_pipeline("mobile_manipulation", manipulation_pipeline)

# Reuse across projects
pipeline = get_pipeline("mobile_manipulation")
```

### Benefits of Registry System

1. **PyTorch-Style Substitution**: Easy algorithm swapping
2. **Automatic Discovery**: Components register themselves on import
3. **Type-Safe Access**: Registries respect Flow[I, O] signatures
4. **Clean Imports**: No namespace pollution with `import *`
5. **Categorized Organization**: Logical grouping by domain

---

## Execution Backends

### Multi-Backend Architecture

Following PyTorch's design, computation graphs are separate from execution:

```python
# Same pipeline, different backends
pipeline = camera >> detector >> planner

# Development: Sequential execution
engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.SEQUENTIAL))
result = engine.execute_sync(pipeline, input_data)

# Testing: Parallel execution
engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.THREADING))
result = engine.execute_sync(pipeline, input_data)

# Production: Distributed execution
engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.DORA))
result = engine.compile_to_dora(pipeline)
```

### Backend Capabilities

| Backend | Use Case | Distribution | Debugging | Performance |
|---------|----------|--------------|-----------|-------------|
| **Sequential** | Development, testing | Single machine | ✅ Excellent | Baseline |
| **Threading** | Single-machine optimization | Single machine | ✅ Good | 2-4x speedup |
| **Dora** | Production robotics | Multi-machine | ⚠️ Complex | 10-17x speedup |

### Dora Integration

Complete Flow→Dora translation for production deployment:

**Automatic Operator Generation**:
```python
# Your Flow class
@flow(rate="30hz")
class CameraFlow(Flow[None, RGBImage]):
    def run(self, _: None) -> RGBImage:
        return self.camera.capture()

# Framework generates Dora operator
class CameraOperator:
    def __init__(self):
        self.flow = CameraFlow()  # Embedded Flow instance
    
    def on_event(self, dora_event, send_output):
        result = self.flow.run(input_data)  # Execute real Flow.run()
        output_data, metadata = serialize_output(result)
        send_output("output", output_data, metadata)
        return DoraStatus.CONTINUE
```

**Generated Dora Configuration**:
```yaml
# dataflow.yml - Generated automatically
nodes:
  - id: cameraflow
    operator:
      python: cameraflow_op.py
      inputs:
        tick: dora/timer/millis/33  # 30hz → 33ms
      outputs:
        - output
```

---

## Type System

### Core Data Types

Retriever provides comprehensive type definitions for robotics:

#### Vision Types
```python
@dataclass
class RGBImage:
    data: np.ndarray  # Shape: (H, W, 3)
    timestamp: Optional[float] = None
    camera_id: str = "default"

@dataclass  
class Detection:
    label: str
    confidence: float
    bbox: BoundingBox
    mask: Optional[np.ndarray] = None
```

#### Spatial Types
```python
@dataclass
class Pose3:
    position: np.ndarray  # Shape: (3,), XYZ coordinates
    orientation: np.ndarray  # Shape: (4,), quaternion (w, x, y, z)
    frame_id: str = "world"

@dataclass
class Transform3:
    matrix: np.ndarray  # Shape: (4, 4), homogeneous transformation
    from_frame: str = "world"
    to_frame: str = "base"
```

#### Action Types
```python
@dataclass
class Action:
    type: str  # "move", "grasp", "release"
    parameters: dict
    timestamp: Optional[float] = None
    priority: int = 0
```

### Arrow Serialization

All types support zero-copy serialization for distributed execution:

```python
@dataclass
class RGBImage:
    # ... fields ...
    
    def to_arrow(self) -> dict:
        """Convert to Arrow-compatible format."""
        import pyarrow as pa
        return {
            "data": pa.array(self.data.flatten()),
            "shape": self.data.shape,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id
        }
    
    @classmethod
    def from_arrow(cls, arrow_data: dict) -> 'RGBImage':
        """Convert from Arrow format."""
        import numpy as np
        data = np.array(arrow_data["data"]).reshape(arrow_data["shape"])
        return cls(
            data=data,
            timestamp=arrow_data.get("timestamp"),
            camera_id=arrow_data.get("camera_id", "default")
        )
```

---

## State Management

### Eff Monad for Robot State

Robot operations inherently involve state. The `Eff[S, A]` monad provides principled state management:

```python
from retriever.core.types import Eff

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
```

### State Composition

State flows automatically through composition:

```python
# Compose stateful operations
fetch_mission = move_robot_eff >> pick_object_eff >> place_object_eff

# Execute with state tracking
initial_state = RobotState(position=home_pose, battery_level=1.0, objects_held=[])
success, final_state = executor.execute_eff(fetch_mission, mission_data, initial_state)
```

### Benefits of Eff

1. **Type Safety**: State mismatches caught at compile time
2. **Testability**: Verify state transitions without hardware
3. **Modularity**: Reusable stateful components
4. **Rollback Safety**: Failed operations don't corrupt state
5. **Backend Flexibility**: Same state logic across execution backends

---

## Production Patterns

### Modular Development

Structure code for maximum reusability:

```python
# flows/perception.py
@register_flow("object_detection", category="vision")
class ObjectDetector(Flow[RGBImage, List[Detection]]):
    def run(self, image: RGBImage) -> List[Detection]:
        return self.yolo.predict(image)

# flows/planning.py
@register_flow("motion_planning", category="planning") 
class MotionPlanner(Flow[List[Pose3D], MotionPlan]):
    def run(self, poses: List[Pose3D]) -> MotionPlan:
        return self.planner.plan(poses[0])

# main_system.py
from flows.perception import ObjectDetector
from flows.planning import MotionPlanner

# Or use registry for runtime substitution
detector = get_flow("object_detection")
planner = get_flow("motion_planning")

# Compose complete system
system = camera_flow >> detector >> planner >> execution_flow
```

### Testing Strategy

#### Unit Testing
```python
def test_object_detector():
    """Test individual flow components."""
    detector = ObjectDetector()
    test_image = load_test_image("test.jpg")
    detections = detector.run(test_image)
    
    assert len(detections) > 0
    assert all(d.confidence > 0.5 for d in detections)
```

#### Integration Testing
```python
@pytest.mark.integration
def test_complete_pipeline():
    """Test end-to-end system."""
    pipeline = build_manipulation_pipeline()
    executor = LocalExecutor()
    
    result = executor.execute_sync(pipeline, test_data)
    assert isinstance(result, ManipulationResult)
    assert result.success == True
```

#### Performance Testing
```python
@pytest.mark.performance
def test_throughput():
    """Test system performance."""
    pipeline = build_perception_pipeline()
    executor = LocalExecutor()
    
    start_time = time.time()
    for _ in range(100):
        executor.execute_sync(pipeline, test_data)
    
    throughput = 100 / (time.time() - start_time)
    assert throughput >= 10.0  # 10 Hz minimum
```

### Deployment Architecture

#### Resource Annotations
```python
@flow(rate="30hz", resources={"cpu": 2})
class CameraFlow(Flow[None, RGBImage]):
    def run(self, _: None) -> RGBImage:
        return self.camera.capture()

@flow(rate="5hz", resources={"gpu": 1})
class AIPlanner(Flow[List[Detection], Plan]):
    def run(self, detections: List[Detection]) -> Plan:
        return self.ai_model.plan(detections)
```

#### Distributed Configuration
```python
# Production deployment configuration
production_config = ExecutionConfig(
    backend=ExecutionBackend.DORA,
    nodes={
        "robot_edge": {"host": "192.168.1.10", "resources": {"cpu": 4}},
        "gpu_server": {"host": "192.168.1.20", "resources": {"gpu": 1}},
        "cloud": {"host": "cloud.example.com", "resources": {"cpu": 16}}
    }
)

# Deploy with automatic resource allocation
engine = ExecutionEngine(production_config)
success = engine.compile_to_dora(production_pipeline)
```

---

## Advanced Features

### VLA Integration

Support for Vision-Language-Action models:

```python
class VLAPolicyFlow(Flow[Tuple[str, RGBImage], Action]):
    def __init__(self, model_name: str = "pi0"):
        super().__init__()
        self.vla_model = load_vla_model(model_name)
    
    def run(self, instruction_and_image: Tuple[str, RGBImage]) -> Action:
        instruction, image = instruction_and_image
        return self.vla_model.predict(instruction, image)

# Two-level architecture
high_level_planner = PlanningFlow()  # 1 Hz strategic planning
vla_policy = VLAPolicyFlow()         # 30 Hz tactical execution

two_level_system = (
    high_level_planner.deploy(rate="1hz") 
    & perception_flow.deploy(rate="30hz")
    >> vla_policy.deploy(rate="30hz")
)
```

### DSPy Integration

Systematic LLM optimization for planning:

```python
import dspy

class TaskPlanningSignature(dspy.Signature):
    """Decompose complex tasks into executable subtasks."""
    task_request = dspy.InputField(desc="Natural language task")
    world_state = dspy.InputField(desc="Current environment state")
    execution_plan = dspy.OutputField(desc="Sequence of subtasks")

class OptimizedPlanner(Flow[TaskRequest, ExecutionPlan]):
    def __init__(self):
        self.planner = dspy.ChainOfThought(TaskPlanningSignature)
    
    def run(self, request: TaskRequest) -> ExecutionPlan:
        return self.planner(
            task_request=request.description,
            world_state=request.context
        )

# Compile with training examples
optimized_planner = dspy.compile(OptimizedPlanner(), trainset=examples)
```

---

## Summary

Retriever provides a **comprehensive, production-ready architecture** for robotics development that combines:

1. **Simple Interfaces**: PyTorch-like abstractions that are easy to learn and use
2. **Type Safety**: Catch errors at development time, not during robot operation
3. **Composability**: Build complex systems from simple, reusable components
4. **Execution Flexibility**: Same code works across development and production backends
5. **Production Ready**: Complete path from prototype to deployed system

The framework bridges the gap between rapid prototyping and production deployment, making robotics development **faster, safer, and more scalable**.

### Next Steps

1. **Start with Examples**: Try the examples in `examples/` directory
2. **Read Flow Guide**: [guide_flow.md](guide_flow.md) for detailed Flow system
3. **Check Developer Guide**: [guide_dev.md](guide_dev.md) for contribution workflows
4. **Explore Registry**: Use `list_flows()`, `list_types()` to discover components
5. **Build Your System**: Create your own robotics capabilities with Retriever

**Happy building!** 🤖