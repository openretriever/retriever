"""
Tests for Migrated Legacy Modules.

Tests the modules migrated from golden_retriever/core into retriever core:
- retriever.types.skills (SkillSignature, GroundedSkill)
- retriever.types.symbolic (Type, Predicate, Object, Variable, GroundAtom)
- retriever.ir.resources (ResourceSpec, ResourcePresets)
- retriever.ir.temporal (ExecutionTimer, RateLimiter - analysis tools, NOT execution)
- retriever.flow.coordination (EventManager, FRP utilities)
"""

import time
import pytest
import numpy as np


# =============================================================================
# Tests for retriever.types.skills
# =============================================================================

class TestSkillTypes:
    """Tests for SkillSignature and GroundedSkill."""

    def test_skill_signature_creation(self):
        """Test basic SkillSignature creation."""
        from retriever.types.skills import SkillSignature
        
        sig = SkillSignature(
            name="pick_up",
            template="pick up {object} from {location}"
        )
        
        assert sig.name == "pick_up"
        assert sig.parameters == ["object", "location"]
        assert str(sig) == "pick_up(object, location)"

    def test_skill_signature_no_params(self):
        """Test SkillSignature with no parameters."""
        from retriever.types.skills import SkillSignature
        
        sig = SkillSignature(name="stop", template="stop moving")
        assert sig.parameters == []
        assert str(sig) == "stop()"

    def test_grounded_skill_creation(self):
        """Test GroundedSkill creation and validation."""
        from retriever.types.skills import SkillSignature, GroundedSkill
        
        sig = SkillSignature(
            name="put_on",
            template="put {target} on {destination}"
        )
        
        grounded = GroundedSkill(
            signature=sig,
            grounded_params={"target": "red_cup_0", "destination": "table_1"}
        )
        
        assert str(grounded) == "put_on(target=red_cup_0, destination=table_1)"

    def test_grounded_skill_param_mismatch(self):
        """Test that GroundedSkill raises error on param mismatch."""
        from retriever.types.skills import SkillSignature, GroundedSkill
        
        sig = SkillSignature(name="pick", template="pick {object}")
        
        with pytest.raises(ValueError, match="Mismatch between parameters"):
            GroundedSkill(signature=sig, grounded_params={"wrong_param": "obj1"})

    def test_grounded_skill_validate_grounding(self):
        """Test validate_grounding method."""
        from retriever.types.skills import SkillSignature, GroundedSkill
        
        sig = SkillSignature(name="move", template="move to {location}")
        grounded = GroundedSkill(signature=sig, grounded_params={"location": "waypoint_1"})
        
        # Should pass with valid perception
        grounded.validate_grounding({"waypoint_1": "position"})
        
        # Should raise with missing object
        with pytest.raises(ValueError, match="not found"):
            grounded.validate_grounding({"waypoint_2": "position"})


# =============================================================================
# Tests for retriever.types.symbolic
# =============================================================================

class TestSymbolicTypes:
    """Tests for PDDL-style symbolic types."""

    def test_type_creation(self):
        """Test Type creation and hierarchy."""
        from retriever.types.symbolic import Type
        
        thing = Type("thing")
        container = Type("container", parent=thing)
        cup = Type("cup", parent=container)
        
        assert thing.name == "thing"
        assert container.parent == thing
        assert cup.parent == container
        
        # Test ancestor chain
        ancestors = cup.get_ancestors()
        assert thing in ancestors
        assert container in ancestors
        assert cup in ancestors

    def test_object_and_variable(self):
        """Test Object and Variable creation."""
        from retriever.types.symbolic import Type, Object, Variable
        
        cup_type = Type("cup")
        
        # Create object (no ? prefix)
        obj = cup_type("red_cup_0")
        assert isinstance(obj, Object)
        assert obj.name == "red_cup_0"
        assert obj.type == cup_type
        
        # Create variable (? prefix)
        var = cup_type("?x")
        assert isinstance(var, Variable)
        assert var.name == "?x"

    def test_predicate_and_atom(self):
        """Test Predicate and Atom creation."""
        from retriever.types.symbolic import Type, Predicate, State, GroundAtom
        
        cup_type = Type("cup")
        table_type = Type("table")
        
        # Define predicate
        on_predicate = Predicate(
            name="on",
            types=[cup_type, table_type],
            _classifier=lambda state, objs: True  # Simplified
        )
        
        assert on_predicate.arity == 2
        
        # Create ground atom
        cup = cup_type("cup_0")
        table = table_type("table_0")
        atom = on_predicate([cup, table])
        
        assert isinstance(atom, GroundAtom)
        assert str(atom) == "on(cup_0:cup, table_0:table)"

    def test_state_and_predicate_holds(self):
        """Test State and predicate evaluation."""
        from retriever.types.symbolic import Type, Predicate, State, Object
        
        obj_type = Type("object", feature_names=["x", "y"])
        
        def is_at_origin(state: State, objects):
            obj = objects[0]
            features = state[obj]
            return features[0] == 0 and features[1] == 0
        
        at_origin = Predicate(
            name="at_origin",
            types=[obj_type],
            _classifier=is_at_origin
        )
        
        obj = obj_type("test_obj")
        state = State(data={obj: np.array([0.0, 0.0])})
        
        assert at_origin.holds(state, [obj])


# =============================================================================
# Tests for retriever.ir.resources
# =============================================================================

class TestResourceSpec:
    """Tests for ResourceSpec and resource management."""

    def test_resource_spec_creation(self):
        """Test basic ResourceSpec creation."""
        from retriever.ir.resources import ResourceSpec
        
        spec = ResourceSpec(cpu=2, gpu=1, memory=8)
        
        assert spec.cpu == 2
        assert spec.gpu == 1
        assert spec.memory == 8
        assert spec.requires_gpu() is True
        assert spec.node_type == "gpu"  # Auto-detected

    def test_resource_presets(self):
        """Test predefined ResourcePresets."""
        from retriever.ir.resources import ResourcePresets
        
        assert ResourcePresets.CPU_LIGHT.cpu == 1
        assert ResourcePresets.GPU_MEDIUM.gpu == 1
        assert ResourcePresets.REALTIME_CONTROL.max_runtime == 0.01

    def test_resource_spec_merge(self):
        """Test merging two ResourceSpecs."""
        from retriever.ir.resources import ResourceSpec
        
        spec1 = ResourceSpec(cpu=2, memory=4)
        spec2 = ResourceSpec(cpu=1, memory=2, gpu=0.5)
        
        merged = spec1.merge(spec2)
        
        assert merged.cpu == 3
        assert merged.memory == 6
        assert merged.gpu == 0.5

    def test_resource_spec_can_run_on(self):
        """Test can_run_on allocation check."""
        from retriever.ir.resources import ResourceSpec
        
        available = ResourceSpec(cpu=4, gpu=2, memory=16)
        small_task = ResourceSpec(cpu=1, gpu=0.5, memory=4)
        large_task = ResourceSpec(cpu=8, gpu=1, memory=32)
        
        assert small_task.can_run_on(available) is True
        assert large_task.can_run_on(available) is False


# =============================================================================
# Tests for retriever.ir.temporal (Analysis Tools)
# =============================================================================

class TestTemporalAnalysis:
    """Tests for temporal analysis utilities (NOT execution scheduling)."""

    def test_execution_timer_basic(self):
        """Test ExecutionTimer basic timing."""
        from retriever.ir.temporal import ExecutionTimer
        
        timer = ExecutionTimer(name="test_timer")
        
        start = timer.start()
        time.sleep(0.05)
        elapsed = timer.elapsed()
        
        assert elapsed >= 0.05
        assert elapsed < 0.15  # Should be close to 50ms (with margin)

    def test_execution_timer_context(self):
        """Test ExecutionTimer context manager for metrics collection."""
        from retriever.ir.temporal import ExecutionTimer
        
        timer = ExecutionTimer(target_hz=10, name="context_timer")
        
        with timer.execution_context():
            time.sleep(0.02)
        
        assert timer.metrics.total_executions == 1
        assert timer.metrics.successful_executions == 1

    def test_execution_metrics(self):
        """Test ExecutionMetrics tracking."""
        from retriever.ir.temporal import ExecutionMetrics
        
        metrics = ExecutionMetrics()
        
        metrics.update(0.01, success=True)
        metrics.update(0.02, success=True)
        metrics.update(0.03, success=False)
        
        assert metrics.total_executions == 3
        assert metrics.successful_executions == 2
        assert metrics.min_duration == 0.01
        assert metrics.max_duration == 0.03

    def test_time_constraint(self):
        """Test TimeConstraint data structure."""
        from retriever.ir.temporal import TimeConstraint
        
        constraint = TimeConstraint(
            max_duration=0.1,
            target_hz=30.0,
            timeout_behavior="abort"
        )
        
        assert constraint.max_duration == 0.1
        assert constraint.target_hz == 30.0


# =============================================================================
# Tests for retriever.flow.coordination (FRP Utilities)
# =============================================================================

class TestFRPUtilities:
    """Tests for FRP utility functions."""

    def test_constant_behavior(self):
        """Test constant_behavior creates a constant value behavior."""
        from retriever.flow.coordination import constant_behavior
        
        behavior = constant_behavior(42)
        
        assert behavior.at_time(0.0) == 42
        assert behavior.at_time(100.0) == 42

    def test_time_behavior(self):
        """Test time_behavior returns the requested time."""
        from retriever.flow.coordination import time_behavior
        
        behavior = time_behavior()
        
        assert behavior.at_time(1.0) == 1.0
        assert behavior.at_time(99.5) == 99.5

    def test_empty_event_stream(self):
        """Test empty_event_stream creates empty stream."""
        from retriever.flow.coordination import empty_event_stream
        
        stream = empty_event_stream()
        events = stream.events()
        
        assert events == []

    def test_single_event(self):
        """Test single_event creates stream with one event."""
        from retriever.flow.coordination import single_event
        
        stream = single_event(1.5, "test_value")
        events = stream.events()
        
        assert len(events) == 1
        assert events[0] == (1.5, "test_value")

    def test_event_manager_handler_registration(self):
        """Test EventManager handler registration."""
        from retriever.flow.coordination import EventManager
        
        manager = EventManager()
        handled_events = []
        
        def handler(value, timestamp):
            handled_events.append((value, timestamp))
        
        manager.add_event_handler("obstacle_detected", handler)
        
        assert "obstacle_detected" in manager.event_handlers
        assert len(manager.event_handlers["obstacle_detected"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
