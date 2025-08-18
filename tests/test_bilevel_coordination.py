"""
Unit tests for bilevel coordination application layer.

Tests cover:
- BilevelCoordinator functionality
- BilevelFlow patterns
- Strategic/tactical coordination
- Application-specific patterns
"""

import time
import pytest
from unittest.mock import MagicMock

from retriever.applications.bilevel_coordination import (
    BilevelConfiguration, BilevelCoordinator, BilevelFlow, SimpleBilevelFlow,
    create_bilevel_coordinator, example_bilevel_manipulation
)
from retriever.core.temporal import ExecutionTimer


class TestBilevelConfiguration:
    """Test BilevelConfiguration settings."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = BilevelConfiguration()
        
        assert config.strategic_hz == 1.0
        assert config.tactical_hz == 30.0
        assert config.strategic_timeout == 1.0
        assert config.tactical_timeout == 0.1
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = BilevelConfiguration(
            strategic_hz=2.0,
            tactical_hz=50.0,
            strategic_timeout=0.5,
            tactical_timeout=0.02
        )
        
        assert config.strategic_hz == 2.0
        assert config.tactical_hz == 50.0
        assert config.strategic_timeout == 0.5
        assert config.tactical_timeout == 0.02


class TestBilevelCoordinator:
    """Test BilevelCoordinator functionality."""
    
    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        coordinator = BilevelCoordinator()
        
        assert coordinator.config.strategic_hz == 1.0
        assert coordinator.config.tactical_hz == 30.0
        assert coordinator.coordinator is not None
    
    def test_custom_configuration(self):
        """Test coordinator with custom configuration."""
        config = BilevelConfiguration(strategic_hz=2.0, tactical_hz=10.0)
        coordinator = BilevelCoordinator(config)
        
        assert coordinator.config.strategic_hz == 2.0
        assert coordinator.config.tactical_hz == 10.0
    
    def test_strategic_context(self):
        """Test strategic execution context."""
        coordinator = BilevelCoordinator()
        
        with coordinator.strategic_context() as timer:
            assert isinstance(timer, ExecutionTimer)
            time.sleep(0.001)  # Brief execution
        
        # Should have recorded execution
        strategic_timer = coordinator.coordinator.timers["strategic"]
        assert strategic_timer.metrics.total_executions == 1
    
    def test_tactical_context(self):
        """Test tactical execution context."""
        coordinator = BilevelCoordinator()
        
        with coordinator.tactical_context() as timer:
            assert isinstance(timer, ExecutionTimer)
            time.sleep(0.001)  # Brief execution
        
        # Should have recorded execution
        tactical_timer = coordinator.coordinator.timers["tactical"]
        assert tactical_timer.metrics.total_executions == 1
    
    def test_strategic_state_management(self):
        """Test strategic state management."""
        coordinator = BilevelCoordinator()
        
        # Initially no state
        assert coordinator.get_strategic_state() is None
        
        # Set strategic state
        test_state = {"plan": "grasp_object", "target": "red_cup"}
        coordinator.update_strategic_state(test_state)
        
        # Retrieve strategic state
        retrieved_state = coordinator.get_strategic_state()
        assert retrieved_state == test_state
    
    def test_tactical_commands_management(self):
        """Test tactical commands management."""
        coordinator = BilevelCoordinator()
        
        # Initially no commands
        assert coordinator.get_tactical_commands() == []
        
        # Add tactical commands
        coordinator.add_tactical_command("move_arm")
        coordinator.add_tactical_command("open_gripper")
        
        # Retrieve commands (should clear them)
        commands = coordinator.get_tactical_commands()
        assert commands == ["move_arm", "open_gripper"]
        
        # Commands should be cleared after retrieval
        assert coordinator.get_tactical_commands() == []


class TestBilevelFlow:
    """Test BilevelFlow abstract base class."""
    
    def test_rate_configs(self):
        """Test rate configuration generation."""
        
        class TestBilevelFlow(BilevelFlow):
            def run_strategic(self, input_data, timer):
                return {"plan": "test_plan"}
            
            def run_tactical(self, strategic_state, input_data, timer):
                return True
        
        flow = TestBilevelFlow()
        rate_configs = flow.get_rate_configs()
        
        assert "strategic" in rate_configs
        assert "tactical" in rate_configs
        assert rate_configs["strategic"] == 1.0
        assert rate_configs["tactical"] == 30.0
    
    def test_custom_rate_configs(self):
        """Test custom rate configuration."""
        
        class CustomBilevelFlow(BilevelFlow):
            def __init__(self):
                config = BilevelConfiguration(strategic_hz=2.0, tactical_hz=50.0)
                super().__init__(config)
            
            def run_strategic(self, input_data, timer):
                return {"plan": "custom_plan"}
            
            def run_tactical(self, strategic_state, input_data, timer):
                return strategic_state is not None
        
        flow = CustomBilevelFlow()
        rate_configs = flow.get_rate_configs()
        
        assert rate_configs["strategic"] == 2.0
        assert rate_configs["tactical"] == 50.0
    
    def test_run_at_rate_strategic(self):
        """Test run_at_rate for strategic execution."""
        
        class TestFlow(BilevelFlow):
            def run_strategic(self, input_data, timer):
                return {"plan": f"plan_for_{input_data}"}
            
            def run_tactical(self, strategic_state, input_data, timer):
                return strategic_state["plan"] if strategic_state else "no_plan"
        
        flow = TestFlow()
        timer = ExecutionTimer()
        shared_state = {}
        
        result = flow.run_at_rate("strategic", "test_input", timer, shared_state)
        
        assert result == {"plan": "plan_for_test_input"}
        assert shared_state["strategic_state"] == {"plan": "plan_for_test_input"}
    
    def test_run_at_rate_tactical(self):
        """Test run_at_rate for tactical execution."""
        
        class TestFlow(BilevelFlow):
            def run_strategic(self, input_data, timer):
                return {"plan": "strategic_result"}
            
            def run_tactical(self, strategic_state, input_data, timer):
                return f"tactical_executing_{strategic_state['plan']}"
        
        flow = TestFlow()
        timer = ExecutionTimer()
        shared_state = {"strategic_state": {"plan": "existing_plan"}}
        
        result = flow.run_at_rate("tactical", "test_input", timer, shared_state)
        
        assert result == "tactical_executing_existing_plan"
    
    def test_run_at_rate_invalid_rate(self):
        """Test error handling for invalid rate names."""
        
        class TestFlow(BilevelFlow):
            def run_strategic(self, input_data, timer):
                return {"plan": "test"}
            
            def run_tactical(self, strategic_state, input_data, timer):
                return True
        
        flow = TestFlow()
        timer = ExecutionTimer()
        shared_state = {}
        
        with pytest.raises(ValueError, match="Unknown rate for bilevel flow: invalid"):
            flow.run_at_rate("invalid", "input", timer, shared_state)


class TestSimpleBilevelFlow:
    """Test SimpleBilevelFlow implementation."""
    
    def test_simple_bilevel_flow_creation(self):
        """Test SimpleBilevelFlow creation with function delegates."""
        
        def strategic_fn(input_data, timer):
            return {"plan": f"strategic_{input_data}"}
        
        def tactical_fn(strategic_state, input_data, timer):
            plan = strategic_state["plan"] if strategic_state else "no_plan"
            return f"tactical_{plan}_{input_data}"
        
        flow = SimpleBilevelFlow(strategic_fn, tactical_fn)
        
        assert flow.strategic_fn == strategic_fn
        assert flow.tactical_fn == tactical_fn
    
    def test_simple_bilevel_flow_execution(self):
        """Test SimpleBilevelFlow execution."""
        
        strategic_calls = []
        tactical_calls = []
        
        def strategic_fn(input_data, timer):
            strategic_calls.append(input_data)
            return {"plan": f"plan_for_{input_data}"}
        
        def tactical_fn(strategic_state, input_data, timer):
            tactical_calls.append((strategic_state, input_data))
            return f"executed_{strategic_state['plan']}"
        
        config = BilevelConfiguration(strategic_hz=10.0, tactical_hz=20.0)  # Faster for testing
        flow = SimpleBilevelFlow(strategic_fn, tactical_fn, config)
        
        result = flow.run("test_instruction")
        
        # Verify functions were called
        assert len(strategic_calls) == 1
        assert strategic_calls[0] == "test_instruction"
        
        # Tactical should be called multiple times based on rate ratio
        assert len(tactical_calls) >= 1
        
        # Verify result
        assert "executed_plan_for_test_instruction" in result


class TestBilevelPatterns:
    """Test common bilevel coordination patterns."""
    
    def test_manipulation_pattern(self):
        """Test bilevel manipulation pattern."""
        
        execution_log = []
        
        def strategic_planning(instruction, timer):
            execution_log.append(("strategic", instruction))
            if "grasp" in instruction:
                return {
                    "action": "grasp",
                    "target_object": "red_cup",
                    "approach_vector": [0, 0, -1]
                }
            return {"action": "idle"}
        
        def tactical_execution(strategic_state, instruction, timer):
            execution_log.append(("tactical", strategic_state))
            if strategic_state and strategic_state["action"] == "grasp":
                return {"success": True, "object_grasped": strategic_state["target_object"]}
            return {"success": False}
        
        flow = SimpleBilevelFlow(
            strategic_planning, 
            tactical_execution,
            BilevelConfiguration(strategic_hz=5.0, tactical_hz=10.0)  # Faster for testing
        )
        
        result = flow.run("grasp the red cup")
        
        # Verify execution pattern
        strategic_executions = [log for log in execution_log if log[0] == "strategic"]
        tactical_executions = [log for log in execution_log if log[0] == "tactical"]
        
        assert len(strategic_executions) == 1
        assert len(tactical_executions) >= 1
        
        # Verify strategic planning
        assert strategic_executions[0][1] == "grasp the red cup"
        
        # Verify tactical execution received strategic state
        tactical_state = tactical_executions[0][1]
        assert tactical_state["action"] == "grasp"
        assert tactical_state["target_object"] == "red_cup"
        
        # Verify final result
        assert result["success"] is True
        assert result["object_grasped"] == "red_cup"
    
    def test_early_stopping_pattern(self):
        """Test early stopping in tactical execution."""
        
        class EarlyStoppingFlow(BilevelFlow):
            def __init__(self):
                super().__init__(BilevelConfiguration(strategic_hz=5.0, tactical_hz=20.0))
                self.tactical_executions = 0
            
            def run_strategic(self, input_data, timer):
                return {"target_reached": False, "max_attempts": 3}
            
            def run_tactical(self, strategic_state, input_data, timer):
                self.tactical_executions += 1
                # Simulate success on second attempt
                if self.tactical_executions == 2:
                    return {"success": True, "attempts": self.tactical_executions}
                return {"success": False, "attempts": self.tactical_executions}
            
            def should_stop_tactical_execution(self, tactical_result):
                # Stop when successful
                return tactical_result.get("success", False)
        
        flow = EarlyStoppingFlow()
        result = flow.run("test_input")
        
        # Should stop after 2 tactical executions due to success
        assert flow.tactical_executions == 2
        assert result["success"] is True
        assert result["attempts"] == 2


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_bilevel_coordinator(self):
        """Test create_bilevel_coordinator utility."""
        coordinator = create_bilevel_coordinator(strategic_hz=2.0, tactical_hz=40.0)
        
        assert isinstance(coordinator, BilevelCoordinator)
        assert coordinator.config.strategic_hz == 2.0
        assert coordinator.config.tactical_hz == 40.0
    
    def test_example_bilevel_manipulation(self):
        """Test example bilevel manipulation function."""
        # This should run without errors
        result = example_bilevel_manipulation()
        
        # Should return a boolean result
        assert isinstance(result, bool)


class TestPerformanceMonitoring:
    """Test performance monitoring in bilevel coordination."""
    
    def test_timing_metrics_collection(self):
        """Test that timing metrics are properly collected."""
        
        def strategic_fn(input_data, timer):
            time.sleep(0.001)  # 1ms strategic work
            return {"plan": "test"}
        
        def tactical_fn(strategic_state, input_data, timer):
            time.sleep(0.0005)  # 0.5ms tactical work
            return True
        
        flow = SimpleBilevelFlow(
            strategic_fn, 
            tactical_fn,
            BilevelConfiguration(strategic_hz=20.0, tactical_hz=40.0)  # Fast for testing
        )
        
        # Execute multiple times
        for i in range(3):
            flow.run(f"test_{i}")
        
        # Check that metrics were collected
        strategic_timer = flow.coordinator.coordinator.timers["strategic"]
        tactical_timer = flow.coordinator.coordinator.timers["tactical"]
        
        assert strategic_timer.metrics.total_executions >= 3
        assert tactical_timer.metrics.total_executions >= 3
        
        # Strategic should take longer than tactical
        assert strategic_timer.metrics.average_duration > tactical_timer.metrics.average_duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])