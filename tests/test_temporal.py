"""
Unit tests for the temporal execution system.

Tests cover:
- ExecutionTimer functionality
- RateLimiter behavior  
- MultiRateCoordinator
- TimedFlow integration
- Performance monitoring
"""

import time
import pytest
import threading
from unittest.mock import MagicMock, patch

from retriever.core.temporal import (
    ExecutionTimer, RateLimiter, MultiRateCoordinator,
    TimeConstraint, TimingViolation, ExecutionMetrics,
    with_timing_constraint, with_rate_limiting
)


class TestExecutionTimer:
    """Test ExecutionTimer functionality."""
    
    def test_basic_timing(self):
        """Test basic timer operations."""
        timer = ExecutionTimer()
        
        start_time = timer.start()
        time.sleep(0.01)  # 10ms
        elapsed = timer.elapsed()
        
        assert elapsed >= 0.01
        assert elapsed < 0.02  # Should be close to 10ms
        assert start_time <= timer.now()
    
    def test_elapsed_since(self):
        """Test elapsed_since method."""
        timer = ExecutionTimer()
        
        start_time = timer.now()
        time.sleep(0.01)
        elapsed = timer.elapsed_since(start_time)
        
        assert elapsed >= 0.01
        assert elapsed < 0.02
    
    def test_execution_context(self):
        """Test execution context manager."""
        timer = ExecutionTimer()
        
        with timer.execution_context():
            time.sleep(0.01)
        
        # Check metrics were updated
        assert timer.metrics.total_executions == 1
        assert timer.metrics.successful_executions == 1
        assert timer.metrics.average_duration >= 0.01
    
    def test_execution_context_with_exception(self):
        """Test execution context with exception."""
        timer = ExecutionTimer()
        
        with pytest.raises(ValueError):
            with timer.execution_context():
                raise ValueError("Test exception")
        
        # Check metrics record the failure
        assert timer.metrics.total_executions == 1
        assert timer.metrics.successful_executions == 0
    
    def test_timeout_context_success(self):
        """Test timeout context with successful execution."""
        timer = ExecutionTimer()
        
        with timer.timeout_context(0.1):  # 100ms timeout
            time.sleep(0.01)  # 10ms execution
        
        # Should complete without timeout
        assert True
    
    def test_timeout_context_timeout(self):
        """Test timeout context with timeout."""
        timer = ExecutionTimer()
        
        with pytest.raises(TimeoutError):
            with timer.timeout_context(0.01):  # 10ms timeout
                time.sleep(0.05)  # 50ms execution
    
    def test_timing_violation_logging(self):
        """Test timing violation logging."""
        timer = ExecutionTimer(target_hz=10.0)  # 100ms expected
        
        timer.log_timing_violation("test_component", 0.2, 0.1)  # 200ms actual, 100ms expected
        
        assert len(timer.metrics.violations) == 1
        violation = timer.metrics.violations[0]
        assert violation.component == "test_component"
        assert violation.actual_duration == 0.2
        assert violation.expected_duration == 0.1
        assert violation.severity == "error"  # 200ms > 150ms (1.5x expected)
    
    def test_execution_logging(self):
        """Test execution logging with automatic violation detection."""
        timer = ExecutionTimer(target_hz=10.0)  # 100ms expected
        
        # Log successful execution within constraint
        timer.log_execution("fast_component", 0.05, True)
        assert len(timer.metrics.violations) == 0
        
        # Log slow execution that violates constraint
        timer.log_execution("slow_component", 0.15, True)
        assert len(timer.metrics.violations) == 1
    
    def test_metrics_update(self):
        """Test metrics updating."""
        metrics = ExecutionMetrics()
        
        # First execution
        metrics.update(0.1, True)
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 1
        assert metrics.average_duration == 0.1
        assert metrics.min_duration == 0.1
        assert metrics.max_duration == 0.1
        
        # Second execution
        metrics.update(0.2, False)
        assert metrics.total_executions == 2
        assert metrics.successful_executions == 1  # Still 1 success
        assert metrics.min_duration == 0.1
        assert metrics.max_duration == 0.2
        # Average should be updated (moving average)
        assert 0.1 < metrics.average_duration < 0.2


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    def test_rate_limiting(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(target_hz=10.0)  # 100ms period
        
        start_time = time.time()
        
        # First execution should be immediate
        with limiter.rate_limited_execution():
            pass
        
        elapsed_first = time.time() - start_time
        assert elapsed_first < 0.01  # Should be very fast
        
        # Second execution should be rate limited
        start_second = time.time()
        with limiter.rate_limited_execution():
            pass
        
        elapsed_second = time.time() - start_second
        assert elapsed_second >= 0.09  # Should wait ~100ms
    
    def test_wait_for_next_cycle(self):
        """Test explicit wait_for_next_cycle."""
        limiter = RateLimiter(target_hz=20.0)  # 50ms period
        
        # First call should not wait
        start_time = time.time()
        limiter.wait_for_next_cycle()
        elapsed = time.time() - start_time
        assert elapsed < 0.01
        
        # Second call should wait
        start_time = time.time()
        limiter.wait_for_next_cycle()
        elapsed = time.time() - start_time
        assert elapsed >= 0.04  # Should wait ~50ms


class TestMultiRateCoordinator:
    """Test MultiRateCoordinator functionality."""
    
    def test_initialization(self):
        """Test coordinator initialization."""
        rates = {"planning": 1.0, "control": 30.0, "sensing": 60.0}
        coordinator = MultiRateCoordinator(rates)
        
        assert coordinator.rate_configs == rates
        assert "planning" in coordinator.timers
        assert "control" in coordinator.timers
        assert "sensing" in coordinator.timers
        assert len(coordinator.timers) == 3
    
    def test_rate_context(self):
        """Test rate context execution."""
        coordinator = MultiRateCoordinator({"test": 10.0})
        
        with coordinator.rate_context("test") as timer:
            assert isinstance(timer, ExecutionTimer)
            time.sleep(0.01)
        
        # Should have recorded execution
        assert coordinator.timers["test"].metrics.total_executions == 1
    
    def test_invalid_rate_context(self):
        """Test error handling for invalid rate names."""
        coordinator = MultiRateCoordinator({"valid": 10.0})
        
        with pytest.raises(ValueError, match="Unknown rate: invalid"):
            with coordinator.rate_context("invalid"):
                pass
    
    def test_shared_state(self):
        """Test shared state management."""
        coordinator = MultiRateCoordinator({"test": 1.0})
        
        # Set and get shared state
        coordinator.set_shared_state("key1", "value1")
        coordinator.set_shared_state("key2", 42)
        
        assert coordinator.get_shared_state("key1") == "value1"
        assert coordinator.get_shared_state("key2") == 42
        assert coordinator.get_shared_state("nonexistent") is None
        assert coordinator.get_shared_state("nonexistent", "default") == "default"
    
    def test_thread_safety(self):
        """Test thread safety of shared state."""
        coordinator = MultiRateCoordinator({"test": 100.0})
        results = {}
        
        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_item_{i}"
                coordinator.set_shared_state(key, f"value_{i}")
                results[key] = coordinator.get_shared_state(key)
        
        # Run multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Check all values were set correctly
        assert len(results) == 30  # 3 workers * 10 items each
        for key, value in results.items():
            expected_value = f"value_{key.split('_')[-1]}"
            assert value == expected_value


class TestTimeConstraint:
    """Test TimeConstraint functionality."""
    
    def test_time_constraint_creation(self):
        """Test TimeConstraint creation and attributes."""
        constraint = TimeConstraint(
            max_duration=0.1,
            target_hz=10.0,
            timeout_behavior="retry"
        )
        
        assert constraint.max_duration == 0.1
        assert constraint.target_hz == 10.0
        assert constraint.timeout_behavior == "retry"


class TestDecorators:
    """Test timing decorators."""
    
    def test_with_timing_constraint(self):
        """Test timing constraint decorator."""
        constraint = TimeConstraint(max_duration=0.05)  # 50ms max
        
        @with_timing_constraint(constraint)
        def fast_function(x):
            time.sleep(0.01)  # 10ms
            return x * 2
        
        result = fast_function(5)
        assert result == 10  # Function should work normally
    
    def test_with_timing_constraint_violation(self):
        """Test timing constraint decorator with violation."""
        constraint = TimeConstraint(max_duration=0.01)  # 10ms max
        
        @with_timing_constraint(constraint)
        def slow_function(x):
            time.sleep(0.05)  # 50ms - violates constraint
            return x * 2
        
        with pytest.raises(TimeoutError):
            slow_function(5)
    
    def test_with_rate_limiting(self):
        """Test rate limiting decorator."""
        @with_rate_limiting(target_hz=20.0)  # 50ms period
        def rate_limited_function(x):
            return x * 2
        
        # First call should be fast
        start_time = time.time()
        result1 = rate_limited_function(5)
        elapsed1 = time.time() - start_time
        assert result1 == 10
        assert elapsed1 < 0.01
        
        # Second call should be rate limited
        start_time = time.time()
        result2 = rate_limited_function(6)
        elapsed2 = time.time() - start_time
        assert result2 == 12
        assert elapsed2 >= 0.04  # Should wait ~50ms


class TestTimingViolation:
    """Test TimingViolation data structure."""
    
    def test_timing_violation_creation(self):
        """Test TimingViolation creation."""
        violation = TimingViolation(
            component="test_component",
            expected_duration=0.1,
            actual_duration=0.2,
            timestamp=time.time(),
            severity="warning"
        )
        
        assert violation.component == "test_component"
        assert violation.expected_duration == 0.1
        assert violation.actual_duration == 0.2
        assert violation.severity == "warning"


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_multi_rate_execution_pattern(self):
        """Test realistic multi-rate execution pattern."""
        coordinator = MultiRateCoordinator({
            "planning": 1.0,    # 1Hz planning
            "control": 10.0,    # 10Hz control  
            "sensing": 20.0     # 20Hz sensing
        })
        
        execution_log = []
        
        # Simulate planning cycle
        with coordinator.rate_context("planning") as timer:
            coordinator.set_shared_state("plan", {"target": "object_A"})
            execution_log.append(("planning", timer.now()))
        
        # Simulate multiple control cycles
        for i in range(3):
            with coordinator.rate_context("control") as timer:
                plan = coordinator.get_shared_state("plan")
                coordinator.set_shared_state("control_output", f"move_towards_{plan['target']}")
                execution_log.append(("control", timer.now()))
        
        # Simulate multiple sensing cycles
        for i in range(5):
            with coordinator.rate_context("sensing") as timer:
                coordinator.set_shared_state("sensor_data", f"reading_{i}")
                execution_log.append(("sensing", timer.now()))
        
        # Verify execution log
        assert len(execution_log) == 9  # 1 planning + 3 control + 5 sensing
        
        # Verify shared state
        assert coordinator.get_shared_state("plan")["target"] == "object_A"
        assert coordinator.get_shared_state("control_output") == "move_towards_object_A"
        assert coordinator.get_shared_state("sensor_data") == "reading_4"
        
        # Verify timing metrics
        coordinator.print_performance_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])