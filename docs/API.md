# API Reference

## Core Classes

### Flow[X, Y]
```python
class Flow(Generic[X, Y]):
    """Composable wrapper around a Module."""
    
    @classmethod
    def from_module(cls, module: Module[X, Y]) -> Flow[X, Y]:
        """Create Flow from any callable function."""
    
    def then(self, next_flow: Flow[Y, Z]) -> Flow[X, Z]:
        """Sequential composition: X → Y → Z"""
    
    def fanout(self, parallel_flow: Flow[X, Z]) -> Flow[X, Tuple[Y, Z]]:
        """Parallel composition: X → (Y, Z)"""
    
    # Operator overloading
    def __rshift__(self, other): return self.then(other)      # >>
    def __and__(self, other): return self.fanout(other)       # &
```

### LocalExecutor
```python
class LocalExecutor:
    """Simple, synchronous executor for development."""
    
    def run(self, flow: Flow[X, Y], input_data: X) -> Y:
        """Execute Flow synchronously."""
    
    def run_eff(self, flow: Flow[X, Eff[S, A]], input_data: X, state: S) -> Tuple[A, S]:
        """Execute stateful Flow with state threading."""
    
    async def run_async(self, flow: Flow[X, Y], input_data: X) -> Y:
        """Execute Flow asynchronously (for fanout parallelism)."""
```

### Eff[S, A] (State Monad)
```python
class Eff(Generic[S, A]):
    """Effectful computation with state."""
    
    def __init__(self, run_fn: Callable[[S], Tuple[A, S]]):
        """run_fn takes state, returns (result, new_state)"""
        self.run = run_fn
```

### Module[I, O] (Protocol)
```python
class Module(Protocol, Generic[I, O]):
    """Any callable function with typed input/output."""
    def __call__(self, inp: I) -> O: ...
```

## Configuration

### Config Loading
```python
from retriever.config import load_config

config = load_config(
    config_name="my_config.yaml",
    overrides=["planner.temperature=0.5"]
)
```

### Planning
```python
from retriever.main import create_planner_from_config

planner = create_planner_from_config(config)
plan = planner.plan("Pick up the red cup")
```

## CLI Commands
```bash
python -m retriever.main demo                    # Interactive demo
python -m retriever.main run                     # Run with default config
python -m retriever.main --help                  # Show all options
```

## Type System

### Basic Types
```python
# Input/Output types for common robotics operations
RGBImage = np.ndarray                    # Shape: (H, W, 3)
DepthImage = np.ndarray                  # Shape: (H, W)
PointCloud = np.ndarray                  # Shape: (N, 3)

@dataclass
class Detection:
    object_id: str
    confidence: float
    bbox: Tuple[int, int, int, int]     # (x, y, w, h)

@dataclass  
class Pose3D:
    x: float
    y: float  
    z: float
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
```

### Robotics State Types
```python
@dataclass
class RobotState:
    position: Pose3D
    battery_level: float
    objects_held: List[str]
    
@dataclass
class WorldState:
    object_locations: Dict[str, Pose3D]
    explored_areas: List[Tuple[float, float]]
```

## Common Patterns

### Perception Pipeline
```python
perception = (
    Flow.from_module(capture_image)      # → RGBImage
    .then(Flow.from_module(detect_objects))    # → List[Detection]
    .then(Flow.from_module(estimate_poses))    # → List[Pose3D]
)
```

### Stereo Vision
```python
stereo = (
    left_camera.fanout(right_camera)     # → (left_img, right_img)
    .then(Flow.from_module(stereo_depth))      # → DepthImage
)
```

### Robot Control
```python
def move_robot_eff(target: Pose3D) -> Eff[RobotState, bool]:
    def run(state: RobotState) -> Tuple[bool, RobotState]:
        # Move robot, update state
        new_state = replace(state, position=target, battery=state.battery-0.1)
        return True, new_state
    return Eff(run)

mission = Flow.from_module(move_robot_eff)
success, final_state = executor.run_eff(mission, target, initial_state)
```

### Error Handling
```python
def safe_detection(image: RGBImage) -> List[Detection]:
    try:
        return yolo_model(image)
    except Exception as e:
        logger.warning(f"Detection failed: {e}")
        return []  # Return empty list on failure

robust_flow = Flow.from_module(safe_detection)
```

### Conditional Processing
```python
def adaptive_processing(data):
    if is_complex_scene(data):
        return advanced_algorithm(data)
    else:
        return simple_algorithm(data)

adaptive_flow = Flow.from_module(adaptive_processing)
```

## Testing Utilities

### Mock Modules
```python
# Create mock functions for testing
def mock_detector(image): return [Detection("cup", 0.9, (10, 10, 50, 50))]
def mock_planner(poses): return "pick_cup"

test_pipeline = (
    Flow.from_module(mock_detector)
    .then(Flow.from_module(mock_planner))
)

result = executor.run(test_pipeline, test_image)
assert result == "pick_cup"
```

### Performance Testing
```python
import time

def benchmark_pipeline(pipeline, test_data, iterations=100):
    start = time.time()
    for _ in range(iterations):
        result = executor.run(pipeline, test_data)
    duration = time.time() - start
    return duration / iterations  # Average time per iteration
```

---

**Note**: For complete examples, see `tests/core/test_flow_executor.py` 