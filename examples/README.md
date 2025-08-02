# Retriever Examples - Progressive Learning Path

This folder contains examples organized from basic to advanced, demonstrating the unified Pipeline architecture with >> operators and FRP integration.

## 📚 Learning Path: Easy → Hard

### 01_basic_flows/ - Start Here!
**Goal**: Understand Flow[I,O] interface and basic execution
- `01_hello_flow.py` - Your first Flow class
- `02_typed_pipeline.py` - Type-safe Flow composition  
- `03_simple_vision.py` - Camera → Detection pipeline
- **Time**: 5-10 minutes each
- **Concepts**: Flow interface, type safety, basic execution

### 02_pipeline_composition/ 
**Goal**: Master >> and & operators
- `01_sequential_composition.py` - Using >> operator
- `02_parallel_composition.py` - Using & operator with precedence
- `03_complex_composition.py` - Mixed >> and & patterns
- **Time**: 10-15 minutes each  
- **Concepts**: Mathematical composition, operator precedence, type matching

### 03_backend_execution/
**Goal**: Understand execution strategies
- `01_backend_selection.py` - Sequential vs Threading vs Dora
- `02_performance_comparison.py` - Benchmark different backends
- `03_dora_generation.py` - Inspect generated Dora YAML/operators
- **Time**: 15-20 minutes each
- **Concepts**: Backend selection, performance scaling, Dora generation

### 04_time_aware_frp/
**Goal**: Add time awareness and reactivity  
- `01_basic_timing.py` - @flow(rate="30hz") decorator
- `02_multi_rate.py` - Different flows at different rates
- `03_events_triggers.py` - Event-driven behaviors
- `04_feedback_loops.py` - Closed-loop reactive systems
- **Time**: 20-30 minutes each
- **Concepts**: FRP annotations, multi-rate coordination, reactive programming

### 05_hardware_integration/
**Goal**: Real robot integration patterns
- `01_simulation_mock.py` - Mock robot for testing
- `02_spot_integration.py` - Boston Dynamics Spot flows
- `03_ur5_integration.py` - Universal Robots UR5 flows  
- `04_hardware_abstraction.py` - Same pipeline, different robots
- **Time**: 30-45 minutes each
- **Concepts**: Hardware abstraction, robot-specific implementations, sim-to-real

### 06_advanced_patterns/
**Goal**: Production-ready robotics systems
- `01_safety_monitoring.py` - Production safety patterns
- `02_fleet_coordination.py` - Multi-robot coordination
- `03_adaptive_learning.py` - Online skill learning
- `04_production_deployment.py` - Full production system
- **Time**: 45-60 minutes each
- **Concepts**: Safety systems, fleet coordination, learning, production deployment

## 🗄️ Archive

### archive_old_examples/
Contains previous examples before unified architecture:
- Original examples using old interfaces
- Legacy demos and test files
- Historical reference only

---

## 🚀 Quick Start

1. **Start with 01_basic_flows/01_hello_flow.py**
2. **Progress through folders in order**
3. **Each example builds on previous concepts**
4. **Run examples to see implementation working**

## 🎯 What You'll Learn

By the end, you'll understand:
- ✅ Flow[I,O] interface and type safety
- ✅ Pipeline composition with >> and & operators  
- ✅ Backend execution (sequential → threading → dora)
- ✅ FRP time-aware reactive programming
- ✅ Hardware integration and abstraction
- ✅ Production robotics patterns

---

## 📋 Legacy Examples (for reference)

### Quick Start with uv

The examples are designed to work with minimal dependencies using `uv` for dependency management:

```bash
# Install minimal dependencies for examples
uv pip install -e .

# Run the simple oracle flow example
uv run demo-flow

# Or run directly
uv run python examples/simple_oracle_flow.py
```

### Available Legacy Examples

#### `simple_oracle_flow.py`
A minimal example demonstrating the core Flow framework without heavy dependencies:
- Flow composition with `.then()` and `.fanout()`
- Module protocol implementation  
- Type-safe pipeline construction
- Eff monad for stateful operations

**Dependencies**: Only `numpy` (minimal)

#### `end_to_end_demo.py`
Complete end-to-end demonstration of the Retriever framework capabilities:
- Core Flow/Module/Eff architecture
- Models system integration with fallbacks
- Perception pipeline with object detection and grounding
- Task planning and execution with skills
- Stateful robot operations and error handling
- Advanced framework features (parallel processing, state management)

**Dependencies**: Core framework only (uses mock models for demonstration)

#### `ravens_flow_demo.py`
Ravens environment integration demonstrating Flow framework with real simulation:
- Flow-based pipeline with Ravens physics simulation
- Integration with actual robotics environment
- LangSAM vision model integration (when available)
- Real manipulation tasks (stack-blocks, etc.)
- Graceful fallback to mock environment if dependencies missing

**Dependencies**: Full Ravens simulation stack (optional - uses fallbacks if missing)

### Using uv Scripts

The project includes convenient uv scripts defined in `pyproject.toml`:

```bash
# Development workflow
uv run format          # Format code with black
uv run lint            # Lint and fix with ruff  
uv run typecheck       # Type check with mypy
uv run test            # Run tests with pytest
uv run qa              # Run full quality assurance pipeline

# Examples and demos
uv run demo-flow       # Simple flow example
uv run end-to-end-demo # Complete end-to-end demo  
uv run ravens-flow-demo # Ravens simulation integration
uv run demo-oracle     # Full oracle example

# Dora integration
uv run dora-test       # Test dora benchmarking infrastructure
uv run dora-bench      # Run performance benchmarks
uv run dora-bench-quick # Quick benchmark run

# Setup
uv run install-dev     # Install development dependencies
uv run install-dora    # Install dora integration dependencies
uv run install-all     # Install all optional dependencies
```

**Start with folder 01, progress through 06, and you'll master the unified Retriever architecture!** 🚀