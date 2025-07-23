# Retriever Flow System: Complete Architecture Guide

**Type-safe composition system for production robotics pipelines**

**Author:** Linfeng  
**Version:** 5.0 - Updated with v2.4 Proposal Insights

---

## What This Guide Covers

This is the **complete technical reference** for Retriever's Flow architecture, updated with the latest design insights from our research proposal. For general development practices, see [Developer Guide](guide_dev.md).

**Documentation Hierarchy:**
- **[README.md](README.md)**: Installation and quick start
- **[guide_dev.md](guide_dev.md)**: Development workflows and contributing
- **This guide**: Complete Flow architecture, patterns, and production deployment

---

## Architecture Philosophy

Retriever's Flow system provides **type-safe composition for robotics pipelines**. Think "PyTorch for robotics" - where instead of neural network layers, you compose perception, planning, and control modules.

**Core Design Principles from v2.4 Research:**
- **Type Safety**: Catch errors at development time, not runtime
- **Composability**: Build complex systems from simple, reusable components
- **Execution Flexibility**: Same code works across sequential, parallel, and distributed backends
- **Declarative Pipelines**: Describe what to compute, not how to execute it
- **Stateful Operations**: Principled state management through the `Eff` monad

## Strategic Vision: PyTorch-Like Abstractions for Robotics

Retriever provides **type-safe composition with flexible execution backends**:

| Component | Role | Focus |
|-----------|------|-------|
| **Flow System** | Type-safe development interface | Composability + Type Safety |
| **LocalExecutor** | Development and testing | Fast iteration, debugging |
| **Distributed Backends** | Production deployment | Performance, distribution (dora-rs, Ray, etc.) |

**Value Proposition:**
- ✅ **Development**: Type safety, testability, rapid iteration
- ✅ **Production**: Flexible backend options for performance and distribution
- ✅ **Migration**: Same Flow code, different executors - no rewrite needed

---

# Part I: Core Architecture

## 1. The Three-Layer Hierarchy

Retriever uses a natural progression that matches how roboticists think about systems:

### Layer 1: Module[I, O] - The Atomic Function

A `Module` is any typed function - the fundamental building block.

```python
from typing import Protocol, TypeVar, Generic

I = TypeVar("I")
O = TypeVar("O")

class Module(Protocol, Generic[I, O]):
    """Single typed callable function."""
    def __call__(self, inp: I) -> O: ...

# Examples: Any function is a Module
def detect_objects(image: RGBImage) -> List[Detection]: ...
def estimate_6dof_pose(detections: List[Detection]) -> List[Pose3D]: ...
def plan_manipulation(poses: List[Pose3D]) -> MotionPlan: ...
def execute_motion(plan: MotionPlan) -> ExecutionResult: ...
```

### Layer 2: Flow[X, Y] - The Composable Step

A `Flow` wraps a Module in our composition system, enabling sequential and parallel operations.

```python
# Lift functions into Flow composition system
object_detection = Flow.from_module(detect_objects)      # Flow[RGBImage, List[Detection]]
pose_estimation = Flow.from_module(estimate_6dof_pose)   # Flow[List[Detection], List[Pose3D]]
motion_planning = Flow.from_module(plan_manipulation)    # Flow[List[Pose3D], MotionPlan]
motion_execution = Flow.from_module(execute_motion)      # Flow[MotionPlan, ExecutionResult]

# Individual Flows represent single processing steps
print(type(object_detection))  # Flow[RGBImage, List[Detection]]
```

### Layer 3: Pipeline - The Complete Workflow

A `Pipeline` connects multiple Flows into end-to-end workflows.

```python
# Compose Flows into complete robotics pipeline using operator syntax
manipulation_pipeline = (
    object_detection           # Step 1: Image → Detections
    >> pose_estimation         # Step 2: Detections → Poses  
    >> motion_planning         # Step 3: Poses → Plan
    >> motion_execution        # Step 4: Plan → Result
)

# Pipeline represents complete end-to-end workflow
print(type(manipulation_pipeline))  # Flow[RGBImage, ExecutionResult]
```

### Why This Hierarchy Works

**Natural Language Mapping:**
- ✅ "This **module** detects objects" (single function)
- ✅ "This **flow** processes camera data" (single step in pipeline)  
- ✅ "This **pipeline** performs autonomous manipulation" (complete workflow)

**Technical Benefits:**
- **Module**: Testable, pure functions with clear interfaces
- **Flow**: Type-safe composition with automatic type checking
- **Pipeline**: Complete workflows that can be executed, deployed, optimized

---

## 2. Composition Operations

### Sequential Composition: `>>` and `.then()`

Chain operations where the output of the first becomes the input of the second.

```python
# Operator syntax (concise, mathematical)
perception_to_action = camera_flow >> detection_flow >> planning_flow >> control_flow

# Method syntax (explicit, IDE-friendly)
perception_to_action = (
    camera_flow
    .then(detection_flow)      # Clear sequential composition
    .then(planning_flow)       # Easy to read and debug
    .then(control_flow)        # Excellent IDE support
)

# Type checking ensures compatibility
# This would be a compile-time error:
# camera_flow >> control_flow  # Type mismatch: RGBImage ≠ MotionPlan
```

### Parallel Composition: `&` and `.fanout()`

Process the same input through multiple paths, combining results as tuples.

```python
# Operator syntax - parallel processing
stereo_pipeline = (left_camera_flow & right_camera_flow) >> fusion_flow

# Method syntax - explicit parallel composition
stereo_pipeline = (
    left_camera_flow
    .fanout(right_camera_flow)  # Clear parallel intent  
    .then(fusion_flow)          # Then sequential processing
)

# Complex compositions with mixed patterns
advanced_pipeline = (
    (sensor_a_flow & sensor_b_flow & sensor_c_flow)  # Triple parallel sensing
    >> fusion_flow                                    # Sensor fusion
    >> (planning_flow & backup_planning_flow)        # Parallel planning
    >> selection_flow                                 # Select best plan
)
```

### When to Use Each Syntax Style

**Use Method Syntax For:**
- Teams new to functional programming
- Code reviews and documentation  
- Maximum IDE support and autocomplete
- Teaching and onboarding

**Use Operator Syntax For:**
- Teams with functional programming background
- Complex pipeline compositions
- Mathematical/research-oriented code
- Concise prototyping

---

# Part II: Stateful Operations with `Eff`

## 3. The `Eff` Monad for Robot State Management

Robot operations inherently involve state—robot poses, sensor data, mission progress. The `Eff[S, A]` monad provides **principled state management** for robotics.

### How `Eff` Works

- **Definition**: `Eff[S, A]` represents a computation that takes state `S`, produces output `A`, and returns updated state `S`
- **Core Principle**: Modules return *descriptions* of state transitions rather than directly modifying state
- **Automatic Threading**: State flows automatically through `>>` composition without manual passing

```python
from retriever.core.types import Eff
from dataclasses import dataclass

@dataclass(frozen=True)
class RobotState:
    position: Pose3D
    battery_level: float
    objects_held: List[str]
    last_error: Optional[str] = None

def move_robot_eff(target: Pose3D) -> Eff[RobotState, bool]:
    def run(state: RobotState) -> tuple[bool, RobotState]:
        # Check preconditions
        if state.battery_level < 0.1:
            return False, state._replace(last_error="Low battery")
        
        # Execute movement (describe the change)
        success = robot_controller.move_to(target)
        new_state = state._replace(
            position=target if success else state.position,
            battery_level=max(0, state.battery_level - 0.1),
            last_error=None if success else "Movement failed"
        )
        return success, new_state
    return Eff(run)

def pick_object_eff(object_id: str) -> Eff[RobotState, bool]:
    def run(state: RobotState) -> tuple[bool, RobotState]:
        # Check capacity
        if len(state.objects_held) >= 2:
            return False, state._replace(last_error="Gripper full")
        
        # Execute pick
        success = gripper_controller.pick(object_id)
        new_objects = state.objects_held + [object_id] if success else state.objects_held
        new_state = state._replace(
            objects_held=new_objects,
            last_error=None if success else f"Failed to pick {object_id}"
        )
        return success, new_state
    return Eff(run)
```

### Composing Stateful Operations

State flows automatically through composition:

```python
# Compose stateful robot operations - state threads automatically
move_flow = Flow.from_module(lambda target: move_robot_eff(target))
pick_flow = Flow.from_module(lambda obj_id: pick_object_eff(obj_id))

# Sequential robot mission using operator syntax
fetch_mission = move_flow >> pick_flow

# Execute with state tracking
initial_state = RobotState(
    position=Pose3D(0, 0, 0), 
    battery_level=1.0, 
    objects_held=[]
)

executor = LocalExecutor()
success, final_state = executor.execute_eff(
    fetch_mission, 
    (target_pose, "red_cup"), 
    initial_state
)

if success:
    print(f"Mission complete! Robot now holds: {final_state.objects_held}")
else:
    print(f"Mission failed: {final_state.last_error}")
```

### Key Benefits of `Eff` for Robotics

1. **Type Safety**: State mismatches caught at compile time, not during robot operation
2. **Testability**: State transitions verified without physical hardware
3. **Modularity**: Reusable stateful components that compose cleanly
4. **Rollback Safety**: Failed operations don't corrupt robot state
5. **Execution Flexibility**: Same state logic works across different execution backends

---

# Part III: Multi-Backend Execution

## 4. Execution Architecture

Following PyTorch's design philosophy, computation graphs are completely separate from execution backends.

### Backend Selection Strategy

```python
import retriever

# Development: Pure Python sequential execution (BDAI predicators compatible)
retriever.init(backend="sequential")  # Default, excellent for debugging

# Testing: Parallel execution on single machine  
retriever.init(backend="local_parallel")

# Production: Distributed execution with resource management
retriever.init(backend="dora", config="cluster_config.yaml")
```

### LocalExecutor - Development and Testing

**Use for:** Development, prototyping, testing, debugging

```python
from retriever.core.executor import LocalExecutor

executor = LocalExecutor()

# Synchronous execution (most common)
perception_pipeline = camera_flow >> detection_flow >> pose_estimation_flow
poses = executor.execute_sync(perception_pipeline, initial_input)

# Asynchronous execution (CPU-intensive parallel work)
stereo_pipeline = (left_camera_flow & right_camera_flow) >> stereo_fusion_flow
depth_map = await executor.execute_async(stereo_pipeline, timestamp)

# Effectful execution (stateful robot operations)
manipulation_mission = move_flow >> pick_flow >> place_flow
success, final_state = executor.execute_eff(manipulation_mission, mission_data, initial_state)
```

### Production Backends

**Distributed Execution with Ray-Like Configuration**:

```python
# Production deployment with resource annotations
@retriever.module(host="robot_edge", rate=30.0)
class PerceptionModule(Module[None, RGBDImage]):
    def __call__(self, _: None) -> RGBDImage:
        return self.camera.capture()

@retriever.module(host="gpu_server", rate=5.0)
class PlanningModule(Module[List[Detection], MotionPlan]):
    def __call__(self, detections: List[Detection]) -> MotionPlan:
        return self.planner.plan(detections)

# Same Flow code, different execution
pipeline = perception_flow >> planning_flow >> execution_flow
result = pipeline.execute_distributed()  # Automatic resource management
```

### Backend Compatibility Matrix

| Backend | Use Case | Eff Support | Distribution | Debugging |
|---------|----------|-------------|--------------|-----------|
| **Sequential** | Development, testing | ✅ Full | Single machine | ✅ Excellent |
| **Local Parallel** | Single-machine optimization | ✅ Full | Single machine | ✅ Good |
| **Dora Distributed** | Production robotics | ✅ Limited* | Multi-machine | ⚠️ Complex |

*Custom objects (locks, connections) handled by execution layer abstractions.

---

# Part IV: Real-World Robotics Examples

## 5. Boston Dynamics Spot Mobile Manipulation

Complete mobile manipulation system with coordinated base and arm control:

```python
from retriever.core.flow import Flow
from retriever.core.executor import LocalExecutor
from retriever.robots.spot import SpotInterface

# Spot-specific modules following the Module[I, O] protocol
class SpotCameraModule(Module[None, RGBDImage]):
    def __init__(self, spot_client):
        self.spot = spot_client
    
    def __call__(self, _: None) -> RGBDImage:
        return self.spot.capture_hand_camera()

class SpotManipulationModule(Module[List[Detection], Eff[SpotState, ExecutionResult]]):
    def __init__(self, spot_client):
        self.spot = spot_client
    
    def __call__(self, detections: List[Detection]) -> Eff[SpotState, ExecutionResult]:
        def run(state: SpotState) -> tuple[ExecutionResult, SpotState]:
            if not detections:
                return ExecutionResult(success=False), state
            
            target = detections[0]
            
            # Step 1: Position base optimally
            optimal_base_pose = self.compute_base_position(target, state.base_pose)
            base_success = self.spot.navigate_to(optimal_base_pose)
            
            # Step 2: Execute arm manipulation
            if base_success:
                arm_success = self.spot.manipulate_to_pose(target.pose)
                grasp_success = self.spot.close_gripper() if arm_success else False
            else:
                arm_success = grasp_success = False
            
            # Update robot state
            new_state = SpotState(
                base_pose=optimal_base_pose if base_success else state.base_pose,
                arm_pose=target.pose if arm_success else state.arm_pose,
                gripper_holding=target.class_name if grasp_success else None
            )
            
            result = ExecutionResult(
                success=base_success and arm_success and grasp_success,
                object_grasped=target.class_name if grasp_success else None
            )
            
            return result, new_state
        return Eff(run)

# Compose complete Spot pipeline using operator syntax
spot_pipeline = (
    Flow.from_module(SpotCameraModule(spot_client))
    >> Flow.from_module(detection_module)
    >> Flow.from_module(SpotManipulationModule(spot_client))
)

# Execute with state management
initial_state = SpotState(
    base_pose=current_position,
    arm_pose=stow_position,
    gripper_holding=None
)

executor = LocalExecutor()
success, final_state = executor.execute_eff(spot_pipeline, None, initial_state)

if success:
    print(f"Spot manipulation complete: {final_state.gripper_holding}")
```

## 6. UR5 + External Camera Manipulation

Stationary manipulator with external perception:

```python
# UR5 system with distributed processing
class RealSensePerceptionModule(Module[None, RGBDImage]):
    """External RealSense D435 for workspace monitoring"""
    def __call__(self, _: None) -> RGBDImage:
        return self.realsense.capture_rgbd()

class UR5ExecutionModule(Module[RobotTrajectory, Eff[UR5State, ExecutionResult]]):
    """Force-monitored trajectory execution"""
    def __init__(self, ur5_interface):
        self.ur5 = ur5_interface
    
    def __call__(self, trajectory: RobotTrajectory) -> Eff[UR5State, ExecutionResult]:
        def run(state: UR5State) -> tuple[ExecutionResult, UR5State]:
            # Execute with force monitoring
            success = self.ur5.execute_trajectory_with_monitoring(
                trajectory, 
                force_threshold=10.0,
                position_tolerance=0.001
            )
            
            # Attempt grasp
            grasp_success = self.ur5.close_gripper() if success else False
            
            new_state = UR5State(
                joint_positions=trajectory.end_joints if success else state.joint_positions,
                end_effector_pose=trajectory.end_pose if success else state.end_effector_pose,
                gripper_state="closed" if grasp_success else "open"
            )
            
            return ExecutionResult(success=success and grasp_success), new_state
        return Eff(run)

# UR5 pipeline with parallel processing
ur5_pipeline = (
    Flow.from_module(RealSensePerceptionModule())           # External camera
    >> Flow.from_module(WorkspaceDetectionModule())         # Object detection  
    >> (Flow.from_module(GraspPoseEstimationModule()) & 
        Flow.from_module(CollisionCheckModule()))           # Parallel processing
    >> Flow.from_module(GraspSelectionModule())             # Combine results
    >> Flow.from_module(UR5MotionPlanningModule())          # Motion planning
    >> Flow.from_module(UR5ExecutionModule(ur5_interface))  # Execution
)
```

## 7. Multi-Modal Sensor Fusion

Process multiple sensor streams in parallel:

```python
# Individual sensor processing flows
lidar_flow = Flow.from_module(lambda scan: process_lidar_scan(scan))
camera_flow = Flow.from_module(lambda img: process_camera_image(img))
imu_flow = Flow.from_module(lambda imu: process_imu_data(imu))

# Parallel sensor processing using operator syntax
sensor_fusion_pipeline = (
    (lidar_flow & camera_flow & imu_flow)    # Triple parallel processing
    >> Flow.from_module(fuse_sensor_outputs) # Kalman filter, particle filter, etc.
    >> Flow.from_module(update_world_model)  # Update robot's world understanding
)

# Execute at sensor frequency (e.g., 30 Hz)
async def sensor_fusion_loop():
    executor = LocalExecutor()  # or alternative backend
    
    async for sensor_data in sensor_stream():
        fused_state = await executor.execute_async(sensor_fusion_pipeline, sensor_data)
        await publish_robot_state(fused_state)
```

---

# Part V: Testing and Production

## 8. Testing Flow Compositions

### Unit Testing Individual Flows

```python
import pytest
from retriever.core.flow import Flow
from retriever.core.executor import LocalExecutor

def test_object_detection_flow():
    """Test individual Flow components in isolation."""
    detector = Flow.from_module(yolo_detect)
    executor = LocalExecutor()
    
    test_image = load_test_image("cup_on_table.jpg")
    detections = executor.execute_sync(detector, test_image)
    
    assert len(detections) > 0
    assert any(d.class_name == "cup" for d in detections)
    assert all(d.confidence > 0.5 for d in detections)

def test_stateful_operation():
    """Test Eff monad state transitions."""
    initial_state = RobotState(objects_held=[], gripper_state="open")
    
    pick_eff = pick_object_eff("cup")
    success, final_state = pick_eff.run(initial_state)
    
    assert success == True
    assert "cup" in final_state.objects_held
    assert final_state.gripper_state == "closed"
```

### Integration Testing Complete Pipelines

```python
@pytest.mark.integration
def test_manipulation_pipeline():
    """Test complete pipeline with realistic data."""
    pipeline = build_manipulation_pipeline()
    executor = LocalExecutor()
    
    test_rgbd = load_test_rgbd("manipulation_scene.h5")
    result = executor.execute_sync(pipeline, test_rgbd)
    
    assert isinstance(result, ManipulationResult)
    assert result.success == True
    assert len(result.executed_actions) > 0

@pytest.mark.performance
def test_pipeline_throughput():
    """Test system performance under load."""
    pipeline = build_perception_pipeline()
    executor = LocalExecutor()
    
    start_time = time.time()
    results = [executor.execute_sync(pipeline, test_data) for _ in range(100)]
    total_time = time.time() - start_time
    
    throughput = len(results) / total_time
    assert throughput >= 10.0, f"Expected ≥10 Hz, got {throughput:.1f} Hz"
```

## 9. Production Deployment Patterns

### Modular Development Pattern

Following PyTorch's approach, create separate Python files for individual flows:

```python
# flows/perception.py
from retriever import Module, Flow

class ObjectDetectionModule(Module[RGBDImage, List[Detection]]):
    def __call__(self, rgbd: RGBDImage) -> List[Detection]:
        return self.yolo.predict(rgbd.rgb)

detection_flow = Flow.from_module(ObjectDetectionModule())

# flows/planning.py  
class MotionPlanningModule(Module[List[Pose3D], MotionPlan]):
    def __call__(self, poses: List[Pose3D]) -> MotionPlan:
        return self.planner.plan(poses[0])  # Use first pose
    
planning_flow = Flow.from_module(MotionPlanningModule())

# main_pipeline.py - Compose the complete system
from flows.perception import detection_flow
from flows.planning import planning_flow
from flows.control import control_flow

# Clean composition using operator syntax
manipulation_pipeline = camera_flow >> detection_flow >> planning_flow >> control_flow
```

### Production Backend Configuration

```python
import retriever

# Production initialization
retriever.init(backend="dora", config={
    "nodes": {
        "robot_edge": {"host": "192.168.1.10", "resources": {"cpu": 4}},
        "gpu_server": {"host": "192.168.1.20", "resources": {"gpu": 1, "cpu": 8}},
        "planning_cluster": {"host": "cloud.example.com", "resources": {"cpu": 16}}
    }
})

# Deploy with resource annotations
@retriever.module(host="robot_edge", rate=30.0)
class RobotPerceptionModule(Module[None, RGBDImage]):
    def __call__(self, _: None) -> RGBDImage:
        return self.camera.capture()

@retriever.module(host="gpu_server", rate=5.0)
class AIPlanningModule(Module[List[Detection], MotionPlan]):
    def __call__(self, detections: List[Detection]) -> MotionPlan:
        return self.ai_planner.plan(detections)

# Same pipeline works across backends
production_pipeline = perception_flow >> planning_flow >> execution_flow
result = production_pipeline.execute(input_data)
```

---

# Part VI: Advanced Patterns and Future Directions

## 10. Two-Level Architecture with VLA Integration

Modern robotics requires coordination between strategic planning and tactical execution:

```python
class TwoLevelSystem:
    def __init__(self):
        # Strategic layer - operates at 1 Hz
        self.high_level = HighLevelPlannerFlow()
        
        # Tactical layer - operates at 30 Hz  
        self.low_level = VLAPolicyFlow(model="pi0")
    
    def create_pipeline(self) -> Flow[TaskRequest, ExecutionResult]:
        return (
            self.high_level.deploy(rate=1.0)             # Strategic planning
            & perception_flow.deploy(rate=30.0)          # Parallel perception  
            >> self.low_level.deploy(rate=30.0)          # Tactical execution
        )

# VLA model integration
def vla_policy_eff(instruction: str, observation: dict) -> Eff[RobotState, Action]:
    def run(state: RobotState) -> tuple[Action, RobotState]:
        action = vla_model(instruction, observation, state.memory)
        new_memory = update_memory(state.memory, observation, action)
        new_state = state._replace(memory=new_memory)
        return action, new_state
    return Eff(run)
```

## 11. DSPy Integration for LLM Optimization

Move beyond brittle prompt engineering with systematic LLM optimization:

```python
import dspy

class TaskPlanningSignature(dspy.Signature):
    """Decompose complex tasks into executable subtasks."""
    task_request = dspy.InputField(desc="Natural language task description")
    world_state = dspy.InputField(desc="Current environment state")
    execution_plan = dspy.OutputField(desc="Sequence of subtasks with parameters")

class OptimizedPlanningModule(Module[TaskRequest, ExecutionPlan]):
    def __init__(self):
        self.planner = dspy.ChainOfThought(TaskPlanningSignature)
    
    def __call__(self, request: TaskRequest) -> ExecutionPlan:
        return self.planner(task_request=request.description, world_state=request.context)

# Compile with training examples
planning_examples = [...]
optimized_planner = dspy.compile(OptimizedPlanningModule(), trainset=planning_examples)

# Integration into unified pipeline
intelligent_pipeline = (
    perception_flow 
    >> Flow.from_module(optimized_planner) 
    >> execution_flow
)
```

## 12. Production Performance Optimization

### Backend Evaluation Framework

When considering production deployment:

```python
# Decision framework for backend selection
def evaluate_backend(pipeline, test_data, backend_config):
    """Evaluate backend performance for production deployment."""
    
    # 1. Start with LocalExecutor baseline
    local_executor = LocalExecutor()
    local_time = benchmark_execution(local_executor, pipeline, test_data)
    
    # 2. Evaluate requirements
    performance_needs = analyze_performance_requirements(pipeline)
    distribution_needs = analyze_distribution_requirements(pipeline)
    
    # 3. Prototype alternatives
    if performance_needs.requires_distribution:
        dora_executor = DoraExecutor(backend_config)
        dora_time = benchmark_execution(dora_executor, pipeline, test_data)
        return compare_performance(local_time, dora_time)
    
    # 4. Gradual migration with same Flow code
    return migration_plan(pipeline, backend_config)
```

### Performance Monitoring

```python
@pytest.mark.performance
def test_production_performance():
    """Monitor production system performance."""
    pipeline = build_production_pipeline()
    
    # Test different backend configurations
    backends = ["local", "local_parallel", "dora"]
    results = {}
    
    for backend in backends:
        executor = create_executor(backend)
        start_time = time.time()
        
        for _ in range(100):
            result = executor.execute_sync(pipeline, test_data)
            
        execution_time = time.time() - start_time
        results[backend] = {
            "throughput": 100 / execution_time,
            "avg_latency": execution_time / 100
        }
    
    # Assert performance requirements
    assert results["dora"]["throughput"] >= 30.0  # 30 Hz requirement
    assert results["dora"]["avg_latency"] <= 0.033  # <33ms latency
```

---

# Summary and Best Practices

## Key Architectural Benefits

1. **Clear Conceptual Hierarchy**: Module → Flow → Pipeline progression that's intuitive
2. **Type Safety**: Catch composition errors at development time, not runtime  
3. **Execution Flexibility**: Choose backends based on requirements, not architectural constraints
4. **Stateful Operations**: Principled state management through the `Eff` monad
5. **Production Ready**: Comprehensive testing, error handling, and real-world examples

## Development Best Practices

### 1. Start Simple, Scale Up
```python
# Begin with LocalExecutor for development
executor = LocalExecutor()
result = executor.execute_sync(simple_pipeline, test_data)

# Scale to production when needed
production_executor = DoraExecutor(config)
result = production_executor.execute(same_pipeline, real_data)
```

### 2. Leverage Type Safety
```python
# Let the type system catch errors early
detection_flow: Flow[RGBImage, List[Detection]] = Flow.from_module(yolo_detect)
planning_flow: Flow[List[Detection], MotionPlan] = Flow.from_module(motion_planner)

# This composition is type-checked at development time
safe_pipeline = detection_flow >> planning_flow
```

### 3. Test State Logic Independently
```python
def test_robot_state_transitions():
    """Test state logic without physical robot."""
    initial_state = RobotState(battery_level=1.0, objects_held=[])
    
    pick_eff = pick_object_eff("cup")
    success, final_state = pick_eff.run(initial_state)
    
    # Verify state changes without robot hardware
    assert success == True
    assert "cup" in final_state.objects_held
```

### 4. Design for Backend Flexibility
```python
# Write backend-agnostic code
@retriever.module  # Works with any backend
class MyRobotModule(Module[Input, Output]):
    def __call__(self, input_data: Input) -> Output:
        # Implementation independent of execution backend
        return self.process(input_data)
```

## Migration Path

- **Now**: Develop with LocalExecutor, proven and reliable
- **Future**: Evaluate production backends based on actual requirements and performance needs
- **Always**: Same Flow code, different executors - no rewrite needed

The Flow architecture provides a clear foundation for robotics development with **type safety**, **composability**, and **execution flexibility** as core principles. This system bridges the gap between **type-safe development** and **flexible production** execution, making it the ideal choice for robotics applications that need both correctness and adaptability.

## Next Steps

1. **Explore Examples**: Start with `examples/simple_flow.py`
2. **Read Developer Guide**: [guide_dev.md](guide_dev.md) for contribution workflows
3. **Try Stateful Operations**: Experiment with the `Eff` monad for robot state
4. **Build Your Pipeline**: Create your own robotics capabilities
5. **Scale to Production**: Evaluate backend options based on your requirements

Happy building! 🤖