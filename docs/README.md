# 🐕 Retriever Documentation

**Type-safe robotics pipeline framework with Flow-based composition**

## Quick Start

### Installation
```bash
git clone https://github.com/linfeng-z/Retriever.git
cd Retriever
pip install -e '.[dev]'

# Verify
python -c "from retriever.core.flow import Flow; print('✅ Ready!')"
python -m pytest tests/core/ -v
```

### Your First Pipeline
```python
from retriever.core.flow import Flow
from retriever.core.executor import LocalExecutor

# Build a robotics pipeline
def detect_objects(image): return ["cup", "bottle"]
def plan_action(objects): return f"pick_{objects[0]}"

pipeline = (
    Flow.from_module(detect_objects)
    .then(Flow.from_module(plan_action))
)

# Execute
executor = LocalExecutor()
result = executor.run(pipeline, "camera_image")  # "pick_cup"
```

## Architecture: Module → Flow → Pipeline

### 1. Module: Basic Building Block
```python
# Any typed function is a Module
def yolo_detect(image: np.ndarray) -> List[Detection]: ...
def estimate_pose(detections: List[Detection]) -> List[Pose3D]: ...
```

### 2. Flow: Composable Step
```python
# Wrap functions for composition
detection_flow = Flow.from_module(yolo_detect)      # Single step
pose_flow = Flow.from_module(estimate_pose)         # Single step
```

### 3. Pipeline: Complete Workflow
```python
# Compose into complete pipeline
perception_pipeline = (
    detection_flow           # Image → Detections
    .then(pose_flow)         # Detections → Poses  
    .then(planning_flow)     # Poses → Plan
)
```

## Core Operations

### Sequential Composition (`.then()`)
```python
# Chain operations: A → B → C
pipeline = flow_a.then(flow_b).then(flow_c)

# Operator syntax (optional)
pipeline = flow_a >> flow_b >> flow_c
```

### Parallel Composition (`.fanout()`)
```python
# Same input to both: A → (B, C)
parallel = flow_a.fanout(flow_b)

# Operator syntax (optional)  
parallel = flow_a & flow_b

# Stereo vision example
stereo = (
    left_camera.fanout(right_camera)    # timestamp → (left, right)
    .then(stereo_fusion)                # (left, right) → depth
)
```

## State Management

For robot control with state tracking:

```python
from retriever.core.types import Eff

def move_robot(target):
    def run(robot_state):
        # Update robot position, battery, etc.
        new_state = robot_state.copy()
        new_state.position = target
        new_state.battery -= 0.1
        return True, new_state  # success, new_state
    return Eff(run)

# Use stateful execution
move_flow = Flow.from_module(move_robot)
executor = LocalExecutor()
success, final_state = executor.run_eff(move_flow, target, initial_state)
```

## Configuration

### Basic Config
```yaml
# configs/my_config.yaml
planner:
  client_type: "mock"  # "openai", "gemini", "mock"
  model_name: "gpt-4"
  temperature: 0.1

robot:
  type: "spot"
  name: "my_robot"
```

### Environment Variables
```bash
# Optional: LLM API keys
export OPENAI_API_KEY=your_key
export GEMINI_API_KEY=your_key
```

### CLI Usage
```bash
# Run demo
python -m retriever.main demo

# With configuration
python -m retriever.main run --config-name my_config.yaml

# Override settings
python -m retriever.main demo planner.client_type=mock
```

## LLM Planning

```python
from retriever.config import load_config
from retriever.main import create_planner_from_config

# Set up planner
config = load_config("configs/retriever.yaml")
planner = create_planner_from_config(config)

# Plan from natural language
plan = planner.plan("Pick up the red cup")
print(plan)  # List of skill steps
```

## Examples and Testing

### Development Commands
```bash
# Tests
python -m pytest tests/core/test_flow.py -v              # Flow composition
python -m pytest tests/core/test_flow_executor.py -v     # Robotics examples
python -m pytest tests/core/test_effectful_executor.py -v # State management

# Type checking
mypy retriever/core/

# Code formatting
black retriever/ tests/
```

### Example Files
- `tests/core/test_flow_executor.py` - Robotics pipeline examples
- `tests/core/test_effectful_executor.py` - State management examples
- `tests/core/test_flow.py` - Basic composition patterns

## Current Implementation Status

### ✅ What Works Now
- **Flow System**: Type-safe composition (`retriever/core/flow.py`)
- **LocalExecutor**: Sync/async/effectful execution (`retriever/core/executor.py`)
- **State Management**: Eff monad for robot state (`retriever/core/types.py`)
- **LLM Planning**: OpenAI/Gemini integration (`retriever/planning/`)
- **Configuration**: YAML + CLI overrides (`retriever/config.py`)
- **CLI Interface**: Commands and demos (`retriever/main.py`)
- **Test Suite**: 32+ tests covering robotics use cases

### 🚧 Next Development Priorities
1. **Perception Modules**: Object detection, pose estimation
2. **Robot Interfaces**: Hardware integration (Spot, etc.)
3. **High-Performance Executors**: dora-rs integration for 10x speedup

## File Structure
```
retriever/
├── core/
│   ├── flow.py               # Main Flow composition system
│   ├── executor.py           # LocalExecutor implementation  
│   ├── types.py              # Module protocol, Eff monad
│   └── symbolic_structs.py   # Robot state/planning types
├── config.py                 # Configuration system
├── main.py                   # CLI interface
└── planning/
    └── llm_planner.py        # LLM-based planning

tests/core/                   # Comprehensive test suite
configs/                      # Configuration examples
```

## Troubleshooting

**Import errors**: `pip install -e . --force-reinstall`  
**Test failures**: Check `python -m pytest tests/core/test_flow.py -v`  
**Type errors**: Run `mypy retriever/core/` to check types  
**Configuration issues**: Verify config files in `configs/` directory

## Future: High-Performance Execution

### Planned: DoraExecutor (Phase 2.6)
```python
# Same Flow, 10x faster execution
from retriever.integrations.dora import DoraExecutor

executor = DoraExecutor("robotics_cluster.yaml")
result = await executor.run(perception_pipeline, sensor_data)  # 10-17x speedup
```

**Benefits**: Zero-copy Apache Arrow messages, distributed execution, production robotics performance

### Planned: RayExecutor (Phase 2.7)  
```python
# Same Flow, massive scale
from retriever.integrations.ray import RayExecutor

executor = RayExecutor("ray://cluster:10001")
results = await executor.run_parallel(robot_missions, fleet_configs)
```

**Benefits**: Cloud-scale execution, multi-robot coordination, fault tolerance

## Migration Path
1. **Development**: LocalExecutor (current) - simple and reliable
2. **Production**: DoraExecutor (Phase 2.6) - 10x performance, same API
3. **Scale**: RayExecutor (Phase 2.7) - massive parallelism

---

**Focus**: Production-ready development framework. Simple, reliable, type-safe.

**Current Status**: Core Flow system complete and tested. Ready for perception and robot interface development. 