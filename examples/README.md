# Retriever Framework Examples

Complete examples demonstrating the core capabilities of the Retriever robotics framework.

## 📁 **Example Categories**

```
examples/
├── 01_core_concepts/              # Essential Flow patterns 
├── 02_vision_processing/          # ⭐ Camera + detection (START HERE)
├── 03_state_management/           # State & Eff patterns  
├── 04_backend_execution/          # Dora FRP backend execution
├── 05_frp_coordination/           # Multi-rate and timing coordination
├── 06_feedback_loops/             # 🔄 Closed-loop robotics systems
└── 07_resource_management/        # ⚡ Ray-style resource allocation
```

## 🎯 **Quick Start**

```bash
# Complete working camera demo in 2 minutes
python examples/02_vision_processing/01_simple_camera_demo.py  
```

## 📚 **Learning Progression** (10-15 minutes total)

### ⭐ **Start Here**: `02_vision_processing/01_simple_camera_demo.py`
- **One file** showing everything: camera → detection → live OpenCV window
- **Works immediately** (real MacBook camera with 'q' to quit)
- **All key concepts**: Class-based Flows, @flow decorators, >> composition
- **Time**: 2 minutes

### **Step 1**: `01_core_concepts/` (Essential patterns)
- `01_hello_flow.py` - Flow[I,O] basics + class patterns  
- `02_pipeline_composition.py` - >> operator and type safety
- `03_clean_class_flows.py` - PyTorch-like Flow modules (no boilerplate!)
- **Time**: 5 minutes

### **Step 2**: `02_vision_processing/` (Robotics vision)
- `02_camera_detection_window.py` - Real camera + matplotlib  
- `03_class_based_flows.py` - Vision modules like PyTorch
- **Time**: 5 minutes

### **Step 3**: `03_state_management/` (Robotics state)
- Complete tutorial: mutable problems → Eff monad → robotics patterns
- **Simplified patterns** (no confusing nested functions!)  
- **Clear explanations** of what `Eff[State, Result]` means
- **Time**: 5 minutes

### **Advanced**: `04_backend_execution/` (Production robotics)
- `02_dora_backend.py` - True Dora FRP backend with subprocess execution
- Real YAML generation and Dora operator compilation  
- Multi-rate coordination (30Hz → 10Hz via FRP timers)

### **🔄 NEW: Feedback Loops** (`06_feedback_loops/`)
Complete closed-loop robotics systems with adaptive behavior:

- **`01_event_driven_replanning.py`**: Event-triggered replanning with obstacle detection, battery monitoring, tactical and strategic planning
- **`02_sensor_fusion_feedback.py`**: Multi-sensor fusion with quality monitoring, sensor failure detection, and adaptive weighting  
- **`03_learning_adaptation_feedback.py`**: Online parameter learning with performance-based skill optimization

**Key Features**: Real-time event detection, multi-level feedback (strategic + tactical), sensor quality monitoring, online learning from task outcomes, state management with Eff monads.

### **⚡ NEW: Resource Management** (`07_resource_management/`)
Ray-style resource annotations and management for robotics flows:

- **`01_basic_resource_annotations.py`**: @requires decorator, ResourcePresets, custom resources (camera, robot_arm, lidar)
- **`02_flow_resource_integration.py`**: Resource-aware execution with automatic allocation, parallel scheduling, constraint handling
- **`03_multi_robot_resource_coordination.py`**: Fleet-wide resource management across heterogeneous robots
- **`04_simple_dora_integration.py`**: Resource-aware Dora YAML generation

**Key Features**: `@requires(cpu=2, gpu=1, memory=8)` decorator, automatic resource allocation and scheduling, multi-robot fleet coordination, real-time resource utilization monitoring.

## 💡 **Framework Features Demonstrated**

✅ **Flow composition** with >> and & operators  
✅ **PyTorch-style** class-based modules for robotics  
✅ **State management** with Eff monads  
✅ **Feedback loops** for adaptive robot behavior  
✅ **Resource management** with automatic allocation  
✅ **Multi-robot coordination** across distributed systems  
✅ **FRP integration** with time-aware execution  

## 🚀 **Getting Started**

```bash
# Setup environment
conda create -n retriever python=3.10
conda activate retriever  
pip install -e .

# Quick start - working camera demo
python examples/02_vision_processing/01_simple_camera_demo.py

# Try feedback loops
python examples/06_feedback_loops/01_event_driven_replanning.py

# Test resource management  
python examples/07_resource_management/01_basic_resource_annotations.py
```

## 📚 **Learning Progression**

1. **Start with core concepts** (01_core_concepts/) - Learn Flow basics
2. **Explore vision processing** (02_vision_processing/) - Computer vision pipelines  
3. **Understand state management** (03_state_management/) - Eff monads and robot state
4. **Try feedback loops** (06_feedback_loops/) - Closed-loop robotics systems
5. **Add resource management** (07_resource_management/) - Production-ready resource allocation

**All examples are tested and working** - ready for real robotics applications! 🤖