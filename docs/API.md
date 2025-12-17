# Retriever Framework API Reference

**Complete API documentation for the Retriever robotics framework**

---

> Note (2025-12): The canonical runtime is now **FlowContext → validate() → IRStruct → build_execution() → ExecutionGraph → execute_ir()**.
> Some sections of this API reference still describe the legacy `Flow.from_module` surface and will be updated.
> See `docs/guide_runtime.md` for the up-to-date runtime workflow.

## Table of Contents

1. [Core System](#core-system)
2. [Flow System](#flow-system) 
3. [Registry System](#registry-system)
4. [Execution Backends](#execution-backends)
5. [Type System](#type-system)
6. [State Management](#state-management)
7. [Configuration](#configuration)
8. [Utilities and Testing](#utilities-and-testing)

---

## Core System

### Module Protocol

```python
from typing import Protocol, TypeVar, Generic

I = TypeVar("I")
O = TypeVar("O")

class Module(Protocol[I, O]):
    """Base protocol for all components in the framework.
    
    Any typed callable function automatically implements this protocol.
    """
    def __call__(self, inp: I) -> O:
        """Process input and return output."""
        ...

# Examples
def detect_objects(image: RGBImage) -> List[Detection]: ...
def plan_motion(poses: List[Pose3D]) -> MotionPlan: ...

# Both functions automatically implement Module protocol
```

## Flow System

### Flow[X, Y] - Core Flow Class

```python
from typing import Generic, TypeVar, Callable, Tuple, Union
from retriever.core.flow import Flow

X = TypeVar("X")
Y = TypeVar("Y")
Z = TypeVar("Z")

class Flow(Generic[X, Y]):
    """Type-safe composable wrapper around Module components.
    
    Provides composition operations and execution capabilities.
    """
    
    @classmethod
    def from_module(cls, module: Module[X, Y]) -> "Flow[X, Y]":
        """Create Flow from any callable function.
        
        Args:
            module: Any callable with signature (X) -> Y
            
        Returns:
            Flow wrapper that enables composition
            
        Example:
            >>> def double(x: int) -> int: return x * 2
            >>> flow = Flow.from_module(double)
            >>> # flow is now Flow[int, int]
        """
    
    def then(self, next_flow: "Flow[Y, Z]") -> "Flow[X, Z]":
        """Sequential composition: X → Y → Z
        
        Args:
            next_flow: Flow to execute after this one
            
        Returns:
            Combined flow that executes both in sequence
            
        Example:
            >>> double = Flow.from_module(lambda x: x * 2)
            >>> add_one = Flow.from_module(lambda x: x + 1)
            >>> pipeline = double.then(add_one)  # (x * 2) + 1
        """
    
    def fanout(self, parallel_flow: "Flow[X, Z]") -> "Flow[X, Tuple[Y, Z]]":
        """Parallel composition: X → (Y, Z)
        
        Both flows receive the same input, outputs are combined as tuple.
        
        Args:
            parallel_flow: Flow to execute in parallel
            
        Returns:
            Combined flow that outputs tuple of both results
            
        Example:
            >>> left_camera = Flow.from_module(capture_left)
            >>> right_camera = Flow.from_module(capture_right)
            >>> stereo = left_camera.fanout(right_camera)  # -> (left, right)
        """
    
    # Operator overloading for mathematical syntax
    def __rshift__(self, other: "Flow[Y, Z]") -> "Flow[X, Z]":
        """Sequential composition operator: >>
        
        Example:
            >>> pipeline = flow_a >> flow_b >> flow_c
        """
        return self.then(other)
        
    def __and__(self, other: "Flow[X, Z]") -> "Flow[X, Tuple[Y, Z]]":
        """Parallel composition operator: &
        
        Example:
            >>> parallel = flow_a & flow_b & flow_c
        """
        return self.fanout(other)
    
    def run(self, input_data: X) -> Y:
        """Execute this flow with input data.
        
        Args:
            input_data: Input matching flow's input type
            
        Returns:
            Output matching flow's output type
        """
        
    def deploy(self, rate: Union[str, float], **kwargs) -> "Flow[X, Y]":
        """Deploy flow with rate annotation for temporal execution.
        
        Args:
            rate: Execution rate ("30hz", 30.0, etc.)
            **kwargs: Additional deployment parameters
            
        Returns:
            Rate-annotated flow for FRP execution
            
        Example:
            >>> camera_flow = camera.deploy(rate="30hz")
            >>> planner_flow = planner.deploy(rate="1hz")
        """
```

### Flow Decorators

```python
from typing import Optional, Union

def flow(rate: Optional[Union[str, float]] = None,
         resources: Optional[dict] = None,
         **kwargs) -> Callable:
    """Class decorator for Flow components with metadata.
    
    Args:
        rate: Execution rate annotation ("30hz", 10.0, etc.)
        resources: Resource requirements {"cpu": 2, "gpu": 1}
        **kwargs: Additional metadata
        
    Example:
        >>> @flow(rate="30hz", resources={"cpu": 2})
        >>> class CameraFlow(Flow[None, RGBImage]):
        ...     def run(self, _: None) -> RGBImage:
        ...         return self.camera.capture()
    """
```

## Registry System

### Flow Registry

```python
from retriever import register_flow, get_flow, list_flows, find_flows
from typing import Optional, Dict, List, Type, Any

def register_flow(name: str, 
                 category: str = "general",
                 description: str = "",
                 tags: Optional[List[str]] = None) -> Callable:
    """Register a Flow class for discovery and substitution.
    
    Args:
        name: Unique identifier for the flow
        category: Category for organization ("vision", "control", etc.)
        description: Human-readable description
        tags: Tags for filtering and search
        
    Example:
        >>> @register_flow("yolo_detector", category="vision", 
        ...                description="YOLO object detection",
        ...                tags=["detection", "ml"])
        >>> class YOLODetector(Flow[RGBImage, List[Detection]]):
        ...     def run(self, image): return self.model.predict(image)
    """

def get_flow(name: str, **kwargs) -> Flow:
    """Get registered flow by name with configuration.
    
    Args:
        name: Registered flow name
        **kwargs: Configuration parameters passed to flow constructor
        
    Returns:
        Configured flow instance
        
    Example:
        >>> detector = get_flow("yolo_detector", confidence=0.8)
        >>> camera = get_flow("webcam", device_id=0)
    """

def list_flows(category: Optional[str] = None) -> Dict[str, Any]:
    """List all registered flows, optionally filtered by category.
    
    Args:
        category: Filter by category ("vision", "control", etc.)
        
    Returns:
        Dictionary mapping flow names to FlowInfo objects
        
    Example:
        >>> vision_flows = list_flows(category="vision")
        >>> all_flows = list_flows()
    """

def find_flows(input_type: Optional[Type] = None,
              output_type: Optional[Type] = None,
              tags: Optional[List[str]] = None,
              category: Optional[str] = None) -> Dict[str, Any]:
    """Find flows matching type signatures and metadata.
    
    Args:
        input_type: Required input type
        output_type: Required output type
        tags: Required tags (all must match)
        category: Required category
        
    Returns:
        Dictionary of matching flows
        
    Example:
        >>> # Find all flows that output RGBImage
        >>> cameras = find_flows(output_type=RGBImage)
        
        >>> # Find vision flows with ML tag
        >>> ml_vision = find_flows(category="vision", tags=["ml"])
    """
```

### Type Registry

```python
from retriever import register_type, get_type, list_types

def register_type(name: str,
                 category: str = "general", 
                 description: str = "",
                 tags: Optional[List[str]] = None,
                 **kwargs) -> Callable:
    """Register a type class for discovery and substitution.
    
    Args:
        name: Unique identifier for the type
        category: Category ("geometry", "robotics", "vision", etc.)
        description: Human-readable description
        tags: Tags for filtering
        
    Example:
        >>> @register_type("pose_3d", category="geometry",
        ...                description="3D pose with position and orientation")
        >>> @dataclass
        >>> class Pose3D:
        ...     x: float = 0.0
        ...     y: float = 0.0
        ...     z: float = 0.0
    """

def get_type(name: str) -> Type:
    """Get registered type by name.
    
    Args:
        name: Registered type name
        
    Returns:
        Type class for instantiation
        
    Example:
        >>> pose_type = get_type("pose_3d")
        >>> pose = pose_type(x=1.0, y=2.0, z=3.0)
    """

def list_types(category: Optional[str] = None) -> Dict[str, Any]:
    """List all registered types, optionally filtered by category.
    
    Example:
        >>> geometry_types = list_types(category="geometry")
    """
```

### Pipeline Registry

```python
from retriever import register_pipeline, get_pipeline, list_pipelines

def register_pipeline(name: str,
                     category: str = "general",
                     description: str = "",
                     tags: Optional[List[str]] = None) -> Callable:
    """Register a complete pipeline workflow.
    
    Example:
        >>> @register_pipeline("manipulation", category="robotics")
        >>> class ManipulationPipeline:
        ...     def __init__(self):
        ...         self.camera = get_flow("camera")
        ...         self.detector = get_flow("yolo_detector")
        ...         self.planner = get_flow("motion_planner")
    """

def get_pipeline(name: str, **kwargs) -> Any:
    """Get registered pipeline by name with configuration."""

def list_pipelines(category: Optional[str] = None) -> Dict[str, Any]:
    """List all registered pipelines."""
```

## Execution Backends

### ExecutionEngine

```python
from retriever.core.executor import ExecutionEngine, ExecutionConfig, ExecutionBackend
from enum import Enum

class ExecutionBackend(Enum):
    """Available execution backends."""
    SEQUENTIAL = "sequential"      # Single-threaded Python execution
    THREADING = "threading"        # Multi-threaded parallel execution
    DORA = "dora"                 # Distributed execution with dora-rs

@dataclass
class ExecutionConfig:
    """Configuration for execution engines."""
    backend: ExecutionBackend = ExecutionBackend.SEQUENTIAL
    max_workers: Optional[int] = None
    timeout: Optional[float] = None
    enable_profiling: bool = False
    **kwargs: Any

class ExecutionEngine:
    """Unified execution engine supporting multiple backends."""
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize execution engine with configuration."""
    
    def execute_sync(self, flow: Flow[I, O], input_data: I) -> O:
        """Execute flow synchronously.
        
        Args:
            flow: Flow to execute
            input_data: Input matching flow's input type
            
        Returns:
            Output matching flow's output type
            
        Example:
            >>> engine = ExecutionEngine()
            >>> result = engine.execute_sync(pipeline, test_data)
        """
    
    async def execute_async(self, flow: Flow[I, O], input_data: I) -> O:
        """Execute flow asynchronously.
        
        Useful for I/O-bound operations and parallel fanout execution.
        """
    
    def execute_eff(self, flow: Flow[I, Eff[S, A]], input_data: I, state: S) -> Tuple[A, S]:
        """Execute stateful flow with state threading.
        
        Args:
            flow: Flow that returns Eff monad
            input_data: Input data
            state: Initial state
            
        Returns:
            Tuple of (result, final_state)
            
        Example:
            >>> success, final_state = engine.execute_eff(
            ...     move_robot_flow, target_pose, initial_state)
        """
    
    def compile_to_dora(self, flow: Flow[I, O], output_path: str = "./dataflow") -> bool:
        """Compile flow to Dora distributed execution.
        
        Args:
            flow: Flow to compile
            output_path: Directory for generated Dora files
            
        Returns:
            True if compilation successful
            
        Example:
            >>> success = engine.compile_to_dora(production_pipeline)
            >>> # Generates dataflow.yml and operator files
        """
```

### LocalExecutor (Legacy)

```python
class LocalExecutor:
    """Simple, synchronous executor for development.
    
    Note: Use ExecutionEngine(ExecutionConfig(backend=SEQUENTIAL)) for new code.
    """
    
    def execute_sync(self, flow: Flow[X, Y], input_data: X) -> Y:
        """Execute Flow synchronously."""
    
    def execute_eff(self, flow: Flow[X, Eff[S, A]], input_data: X, state: S) -> Tuple[A, S]:
        """Execute stateful Flow with state threading."""
    
    async def execute_async(self, flow: Flow[X, Y], input_data: X) -> Y:
        """Execute Flow asynchronously (for fanout parallelism)."""
```

## Type System

### Core Vision Types

```python
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

@dataclass
class RGBImage:
    """RGB image data with metadata."""
    data: np.ndarray  # Shape: (height, width, 3), dtype: uint8
    timestamp: Optional[float] = None
    camera_id: str = "default"
    
    def to_arrow(self) -> dict:
        """Convert to Arrow-compatible format for distributed execution."""
    
    @classmethod
    def from_arrow(cls, arrow_data: dict) -> 'RGBImage':
        """Convert from Arrow format."""

@dataclass
class Detection:
    """Object detection result."""
    label: str
    confidence: float
    bbox: 'BoundingBox'
    mask: Optional[np.ndarray] = None
    
@dataclass
class BoundingBox:
    """2D bounding box representation."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center coordinates."""
        return (self.x + self.width / 2, self.y + self.height / 2)
```

### Spatial Types

```python
@dataclass
class Pose3:
    """3D pose with position and orientation."""
    position: np.ndarray  # Shape: (3,), XYZ coordinates
    orientation: np.ndarray  # Shape: (4,), quaternion (w, x, y, z)
    frame_id: str = "world"
    
@dataclass
class Transform3:
    """3D transformation matrix."""
    matrix: np.ndarray  # Shape: (4, 4), homogeneous transformation
    from_frame: str = "world"
    to_frame: str = "base"
    
@dataclass
class PointCloud:
    """3D point cloud data."""
    points: np.ndarray  # Shape: (N, 3), XYZ coordinates
    colors: Optional[np.ndarray] = None  # Shape: (N, 3), RGB values
    normals: Optional[np.ndarray] = None  # Shape: (N, 3), normal vectors
```

### Action Types

```python
@dataclass
class Action:
    """Generic robot action."""
    type: str  # "move", "grasp", "release", etc.
    parameters: Dict[str, Any]
    timestamp: Optional[float] = None
    priority: int = 0
    
@dataclass
class MotionPlan:
    """Robot motion plan."""
    waypoints: List[Pose3]
    joint_trajectories: Optional[List[np.ndarray]] = None
    execution_time: Optional[float] = None
    
@dataclass
class ExecutionResult:
    """Result of action execution."""
    success: bool
    message: str = ""
    execution_time: Optional[float] = None
    final_state: Optional[Any] = None
```

### Robot State Types

```python
@dataclass(frozen=True)
class RobotState:
    """Immutable robot state for Eff monad."""
    position: Pose3
    battery_level: float
    objects_held: List[str]
    joint_positions: Optional[np.ndarray] = None
    
    def _replace(self, **kwargs) -> 'RobotState':
        """Create new state with updated fields."""
        
@dataclass
class WorldState:
    """World model state."""
    object_locations: Dict[str, Pose3]
    explored_areas: List[Tuple[float, float]]
    timestamp: float
```

## State Management

### Eff Monad

```python
from typing import Callable, Tuple, Generic, TypeVar

S = TypeVar("S")  # State type
A = TypeVar("A")  # Result type

class Eff(Generic[S, A]):
    """Effectful computation with state threading.
    
    Represents a computation that takes state S, produces result A,
    and returns updated state S.
    """
    
    def __init__(self, run_fn: Callable[[S], Tuple[A, S]]):
        """Create effectful computation.
        
        Args:
            run_fn: Function that takes state and returns (result, new_state)
            
        Example:
            >>> def increment_counter(state: int) -> Tuple[int, int]:
            ...     return state, state + 1
            >>> counter_eff = Eff(increment_counter)
        """
        self.run = run_fn
    
    def map(self, f: Callable[[A], B]) -> 'Eff[S, B]':
        """Transform the result value.
        
        Args:
            f: Function to transform result
            
        Returns:
            New Eff with transformed result
        """
    
    def flat_map(self, f: Callable[[A], 'Eff[S, B]']) -> 'Eff[S, B]':
        """Monadic bind operation for sequencing effects.
        
        Args:
            f: Function that takes result and returns new Eff
            
        Returns:
            Sequenced effectful computation
        """
    
    @classmethod
    def pure(cls, value: A) -> 'Eff[S, A]':
        """Create Eff that returns value without changing state.
        
        Args:
            value: Value to return
            
        Returns:
            Eff that returns value with unchanged state
        """

# Helper functions for common state operations
def get_state() -> Eff[S, S]:
    """Get current state as result."""
    
def put_state(new_state: S) -> Eff[S, None]:
    """Set new state."""
    
def modify_state(f: Callable[[S], S]) -> Eff[S, None]:
    """Modify state with function."""
```

### State Helper Functions

```python
def move_robot_eff(target: Pose3) -> Eff[RobotState, bool]:
    """Move robot to target pose.
    
    Example:
        >>> target = Pose3(position=np.array([1, 2, 3]))
        >>> move_eff = move_robot_eff(target)
        >>> success, new_state = move_eff.run(initial_state)
    """
    
def pick_object_eff(object_id: str) -> Eff[RobotState, bool]:
    """Pick up object with given ID."""
    
def place_object_eff(location: Pose3) -> Eff[RobotState, bool]:
    """Place held object at location."""
    
# Composition of stateful operations
fetch_mission = move_robot_eff >> pick_object_eff >> place_object_eff
```

### Module[I, O] (Protocol)
```python
class Module(Protocol, Generic[I, O]):
    """Any callable function with typed input/output."""
    def __call__(self, inp: I) -> O: ...
```

## Configuration

### Configuration System

```python
from retriever.config import load_config, Config
from omegaconf import OmegaConf
from typing import Optional, Dict, Any

def load_config(config_name: str = "default.yaml",
               config_path: Optional[str] = None,
               overrides: Optional[List[str]] = None) -> Config:
    """Load configuration with overrides.
    
    Args:
        config_name: Configuration file name
        config_path: Custom config directory path
        overrides: List of override strings ("key=value")
        
    Returns:
        Loaded and validated configuration
        
    Example:
        >>> config = load_config(
        ...     config_name="production.yaml",
        ...     overrides=["planner.temperature=0.1", "robot.name=spot_01"]
        ... )
    """

@dataclass
class Config:
    """Main configuration structure."""
    robot: RobotConfig
    planner: PlannerConfig
    execution: ExecutionConfig
    logging: LoggingConfig
    
@dataclass
class RobotConfig:
    """Robot-specific configuration."""
    type: str = "mock"  # "spot", "ur5", "mock"
    name: str = "default_robot"
    connection_params: Dict[str, Any] = None
    
@dataclass
class PlannerConfig:
    """Planning system configuration."""
    client_type: str = "mock"  # "openai", "gemini", "mock"
    model_name: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 1000
```

### Planning Integration

```python
from retriever.planning import create_planner_from_config, Planner
from typing import List

def create_planner_from_config(config: Config) -> Planner:
    """Create planner from configuration.
    
    Args:
        config: Loaded configuration
        
    Returns:
        Configured planner instance
        
    Example:
        >>> config = load_config("my_config.yaml")
        >>> planner = create_planner_from_config(config)
        >>> plan = planner.plan("Pick up the red cup")
    """

class Planner:
    """Abstract base planner interface."""
    
    def plan(self, instruction: str, context: Optional[Dict] = None) -> List[str]:
        """Generate plan from natural language instruction.
        
        Args:
            instruction: Natural language task description
            context: Optional context information
            
        Returns:
            List of skill steps
            
        Example:
            >>> plan = planner.plan("Navigate to the kitchen and pick up the red cup")
            >>> print(plan)
            ['navigate(kitchen)', 'detect_objects()', 'pick(red_cup)']
        """
```

### Environment Variables

```python
# Development configuration
RETRIEVER_ENV = "development"  # "development", "testing", "production"
RETRIEVER_LOG_LEVEL = "DEBUG"  # "DEBUG", "INFO", "WARNING", "ERROR"
RETRIEVER_BACKEND = "sequential"  # "sequential", "threading", "dora"

# API keys
OPENAI_API_KEY = "your_openai_key"
GEMINI_API_KEY = "your_gemini_key"

# Testing
RETRIEVER_TEST_DATA = "/path/to/test/data"
RETRIEVER_SKIP_SLOW_TESTS = "true"
```

### CLI Interface

```bash
# Basic commands
python -m retriever.main demo                    # Interactive demo
python -m retriever.main run                     # Run with default config
python -m retriever.main --help                  # Show all options

# Configuration override
python -m retriever.main run --config-name production.yaml
python -m retriever.main demo planner.client_type=openai robot.type=spot

# Development commands
python -m retriever.main test-flow               # Test flow system
python -m retriever.main benchmark               # Performance benchmarks
python -m retriever.main validate-config my_config.yaml  # Validate configuration
```

## Utilities and Testing

### Testing Utilities

```python
from retriever.testing import MockFlow, TestExecutor, create_test_data
from typing import Any

class MockFlow(Flow[Any, Any]):
    """Mock flow for testing.
    
    Returns predefined output regardless of input.
    """
    
    def __init__(self, output: Any, delay: float = 0.0):
        """Create mock flow.
        
        Args:
            output: Output to return
            delay: Artificial delay in seconds
        """
        
class TestExecutor:
    """Test-specific executor with additional debugging."""
    
    def execute_with_trace(self, flow: Flow[I, O], input_data: I) -> Tuple[O, List[str]]:
        """Execute flow and return result with execution trace.
        
        Returns:
            Tuple of (result, trace_log)
        """

def create_test_data(data_type: str, **kwargs) -> Any:
    """Create test data of specified type.
    
    Args:
        data_type: Type of test data ("rgb_image", "detection", etc.)
        **kwargs: Parameters for data generation
        
    Returns:
        Generated test data
        
    Example:
        >>> test_image = create_test_data("rgb_image", width=640, height=480)
        >>> test_detection = create_test_data("detection", label="cup", confidence=0.9)
    """
```

### Performance Testing

```python
from retriever.benchmarking import benchmark_flow, ProfileResult
import time
from typing import List

def benchmark_flow(flow: Flow[I, O], 
                  test_data: I,
                  iterations: int = 100,
                  warmup_iterations: int = 10) -> ProfileResult:
    """Benchmark flow execution performance.
    
    Args:
        flow: Flow to benchmark
        test_data: Input data for testing
        iterations: Number of iterations to run
        warmup_iterations: Number of warmup iterations
        
    Returns:
        Performance profile with timing statistics
        
    Example:
        >>> pipeline = build_perception_pipeline()
        >>> result = benchmark_flow(pipeline, test_image, iterations=100)
        >>> print(f"Average: {result.avg_time:.3f}s, Throughput: {result.throughput:.1f} Hz")
    """

@dataclass
class ProfileResult:
    """Benchmarking result."""
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    throughput: float  # Hz
    total_iterations: int
    
def profile_memory_usage(flow: Flow[I, O], input_data: I) -> Dict[str, float]:
    """Profile memory usage during flow execution.
    
    Returns:
        Dictionary with memory statistics in MB
    """
```

### Debugging Tools

```python
from retriever.debugging import enable_flow_tracing, FlowTrace
import logging

def enable_flow_tracing(level: str = "DEBUG"):
    """Enable detailed flow execution tracing.
    
    Args:
        level: Logging level for traces
    """

class FlowTrace:
    """Flow execution trace for debugging."""
    
    def __init__(self, flow: Flow[I, O]):
        self.flow = flow
        self.traces: List[str] = []
        
    def execute_with_trace(self, input_data: I) -> Tuple[O, List[str]]:
        """Execute flow with detailed tracing."""

# Logging configuration
def setup_logging(level: str = "INFO", 
                 format_string: Optional[str] = None,
                 log_file: Optional[str] = None):
    """Set up framework logging.
    
    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR")
        format_string: Custom log format
        log_file: Optional file to write logs
    """
```

## Common Usage Patterns

### Basic Flow Composition

```python
# Simple sequential pipeline
perception_pipeline = (
    Flow.from_module(capture_image)           # None → RGBImage
    .then(Flow.from_module(detect_objects))   # RGBImage → List[Detection]
    .then(Flow.from_module(estimate_poses))   # List[Detection] → List[Pose3D]
)

# Using operator syntax
perception_pipeline = (
    capture_flow >> detection_flow >> pose_estimation_flow
)

# Execute pipeline
executor = ExecutionEngine()
result = executor.execute_sync(perception_pipeline, None)
```

### Parallel Processing

```python
# Stereo vision processing
stereo_pipeline = (
    left_camera_flow.fanout(right_camera_flow)  # timestamp → (left_img, right_img)
    .then(Flow.from_module(stereo_depth))       # (left, right) → DepthImage
)

# Multi-sensor fusion
sensor_fusion = (
    (lidar_flow & camera_flow & imu_flow)       # → (lidar, camera, imu)
    >> Flow.from_module(fusion_algorithm)       # → FusedSensorData
)
```

### Registry-Based Component Substitution

```python
# Register multiple detector implementations
@register_flow("yolo_detector", category="vision")
class YOLODetector(Flow[RGBImage, List[Detection]]):
    def run(self, image): return yolo_model.predict(image)

@register_flow("rcnn_detector", category="vision")
class RCNNDetector(Flow[RGBImage, List[Detection]]):
    def run(self, image): return rcnn_model.predict(image)

# Easy algorithm swapping
for detector_name in ["yolo_detector", "rcnn_detector"]:
    detector = get_flow(detector_name)
    pipeline = camera_flow >> detector >> planning_flow
    results = evaluate_pipeline(pipeline, test_data)
```

### Stateful Robot Operations

```python
# Define stateful operations
def move_robot_eff(target: Pose3) -> Eff[RobotState, bool]:
    def run(state: RobotState) -> Tuple[bool, RobotState]:
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

# Compose stateful mission
mission = (
    Flow.from_module(lambda target: move_robot_eff(target))
    >> Flow.from_module(lambda _: pick_object_eff("cup"))
    >> Flow.from_module(lambda _: place_object_eff(table_pose))
)

# Execute with state tracking
initial_state = RobotState(position=home_pose, battery_level=1.0, objects_held=[])
success, final_state = executor.execute_eff(mission, target_pose, initial_state)
```

### Error Handling and Robustness

```python
# Safe operation with fallback
def safe_detection(image: RGBImage) -> List[Detection]:
    try:
        return primary_detector.predict(image)
    except Exception as e:
        logger.warning(f"Primary detection failed: {e}, using fallback")
        try:
            return fallback_detector.predict(image)
        except Exception:
            logger.error("All detectors failed")
            return []  # Return empty list on complete failure

# Robust pipeline with error handling
robust_pipeline = (
    Flow.from_module(capture_image_with_retry)
    >> Flow.from_module(safe_detection)
    >> Flow.from_module(filter_low_confidence_detections)
)
```

### Conditional and Adaptive Processing

```python
# Adaptive processing based on scene complexity
def adaptive_processing(image: RGBImage) -> List[Detection]:
    complexity = analyze_scene_complexity(image)
    
    if complexity > 0.8:
        # High complexity: use advanced model
        return advanced_detector.predict(image)
    elif complexity > 0.3:
        # Medium complexity: use standard model
        return standard_detector.predict(image)
    else:
        # Low complexity: use fast model
        return fast_detector.predict(image)

# Conditional flow based on input
def conditional_flow(condition_func: Callable[[I], bool],
                    true_flow: Flow[I, O],
                    false_flow: Flow[I, O]) -> Flow[I, O]:
    def conditional_module(input_data: I) -> O:
        if condition_func(input_data):
            return true_flow.run(input_data)
        else:
            return false_flow.run(input_data)
    
    return Flow.from_module(conditional_module)

# Usage
adaptive_detector = conditional_flow(
    lambda img: is_outdoor_scene(img),
    get_flow("outdoor_detector"),
    get_flow("indoor_detector")
)
```

### Multi-Backend Deployment

```python
# Development: Sequential execution
dev_engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.SEQUENTIAL))
result = dev_engine.execute_sync(pipeline, test_data)

# Testing: Parallel execution
test_engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.THREADING))
result = test_engine.execute_sync(pipeline, test_data)

# Production: Distributed execution
prod_engine = ExecutionEngine(ExecutionConfig(backend=ExecutionBackend.DORA))
success = prod_engine.compile_to_dora(pipeline, "./production_dataflow")

# Same pipeline code works across all backends
```

### Testing Patterns

```python
# Unit testing individual flows
def test_object_detector():
    detector = YOLODetector()
    test_image = create_test_data("rgb_image", width=640, height=480)
    detections = detector.run(test_image)
    
    assert len(detections) > 0
    assert all(d.confidence > 0.5 for d in detections)
    assert all(isinstance(d.label, str) for d in detections)

# Integration testing with mock components
def test_perception_pipeline():
    # Create mock components
    mock_camera = MockFlow(create_test_data("rgb_image"))
    mock_detector = MockFlow([create_test_data("detection")])
    
    # Build test pipeline
    test_pipeline = mock_camera >> mock_detector
    
    # Execute and verify
    executor = TestExecutor()
    result, trace = executor.execute_with_trace(test_pipeline, None)
    assert len(result) == 1
    assert "detection" in trace

# Performance benchmarking
def test_pipeline_performance():
    pipeline = build_production_pipeline()
    test_data = create_test_data("rgb_image")
    
    # Benchmark execution
    profile = benchmark_flow(pipeline, test_data, iterations=100)
    
    # Assert performance requirements
    assert profile.throughput >= 30.0  # 30 Hz minimum
    assert profile.avg_time <= 0.033   # 33ms maximum latency
    
# Memory usage testing
def test_memory_usage():
    pipeline = build_vision_pipeline()
    memory_stats = profile_memory_usage(pipeline, test_image)
    
    assert memory_stats["peak_mb"] < 1000  # Less than 1GB peak
    assert memory_stats["leak_mb"] < 10    # Less than 10MB leak
```

---

## Quick Reference

### Essential Imports

```python
# Core framework
from retriever.core.flow import Flow
from retriever.core.executor import ExecutionEngine, ExecutionConfig, ExecutionBackend
from retriever.core.types import Eff

# Registry system
from retriever import register_flow, get_flow, list_flows, find_flows
from retriever import register_type, get_type, list_types
from retriever import register_pipeline, get_pipeline, list_pipelines

# Configuration
from retriever.config import load_config
from retriever.planning import create_planner_from_config

# Testing
from retriever.testing import MockFlow, TestExecutor, create_test_data
from retriever.benchmarking import benchmark_flow, profile_memory_usage
```

### Common Flow Patterns

```python
# Sequential: A → B → C
pipeline = flow_a >> flow_b >> flow_c
pipeline = flow_a.then(flow_b).then(flow_c)

# Parallel: A → (B, C)
parallel = flow_a & flow_b
parallel = flow_a.fanout(flow_b)

# Mixed: A → (B, C) → D
complex = (flow_a & flow_b) >> flow_c
```

### Execution Examples

```python
# Synchronous execution
result = engine.execute_sync(pipeline, input_data)

# Asynchronous execution
result = await engine.execute_async(pipeline, input_data)

# Stateful execution
success, final_state = engine.execute_eff(stateful_flow, input_data, initial_state)

# Distributed compilation
success = engine.compile_to_dora(pipeline, "./dataflow")
```

---

**For complete examples and tutorials, see:**
- [architecture.md](architecture.md) - Complete technical architecture
- [guide_flow.md](guide_flow.md) - Flow system detailed guide
- [guide_dev.md](guide_dev.md) - Developer guide and workflows
- `examples/` directory - Working code examples
- `tests/core/` directory - Comprehensive test suite 
