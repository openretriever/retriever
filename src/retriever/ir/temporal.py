"""
Core Temporal Primitives for Retriever Flow v2.7

This module provides general-purpose timing and coordination utilities that serve
as the foundation for time-aware execution. These primitives are application-agnostic
and focus on measurement, constraint checking, and rate limiting.

Design Principles:
- General-purpose, not specialized for specific application patterns
- Minimal dependencies and simple interfaces
- Thread-safe for multi-rate execution
- Focus on measurement and constraint validation
"""

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TypeVar
from abc import ABC, abstractmethod

T = TypeVar('T')


@dataclass
class TimeConstraint:
    """Declarative timing constraint specification."""
    max_duration: float  # Maximum allowed execution time in seconds
    target_hz: Optional[float] = None  # Target frequency if applicable
    timeout_behavior: str = "abort"  # abort, continue, retry


@dataclass
class TimingViolation:
    """Record of a timing constraint violation."""
    component: str
    expected_duration: float
    actual_duration: float
    timestamp: float
    severity: str = "warning"  # warning, error, critical


@dataclass
class ExecutionMetrics:
    """Performance metrics for execution monitoring."""
    total_executions: int = 0
    successful_executions: int = 0
    average_duration: float = 0.0
    max_duration: float = 0.0
    min_duration: float = float('inf')
    violations: List[TimingViolation] = field(default_factory=list)
    
    def update(self, duration: float, success: bool = True):
        """Update metrics with new execution result."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        
        # Update duration statistics
        self.max_duration = max(self.max_duration, duration)
        if self.min_duration == float('inf'):
            self.min_duration = duration
        else:
            self.min_duration = min(self.min_duration, duration)
        
        # Update running average with exponential smoothing
        alpha = 0.1  # Smoothing factor
        if self.average_duration == 0.0:
            self.average_duration = duration
        else:
            self.average_duration = (1 - alpha) * self.average_duration + alpha * duration


class ExecutionTimer:
    """Core timing utility for measuring and monitoring execution performance."""
    
    def __init__(self, target_hz: Optional[float] = None, name: str = "timer"):
        """Initialize timer with optional target frequency and name."""
        self.target_hz = target_hz
        self.name = name
        self.metrics = ExecutionMetrics()
        self._start_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def now(self) -> float:
        """Get current time as float timestamp."""
        return time.time()
    
    def start(self) -> float:
        """Start timing measurement and return start time."""
        self._start_time = self.now()
        return self._start_time
    
    def elapsed_since(self, start_time: float) -> float:
        """Get elapsed time since given start time."""
        return self.now() - start_time
    
    def elapsed(self) -> float:
        """Get elapsed time since start() was called."""
        if self._start_time is None:
            raise RuntimeError("Timer not started - call start() first")
        return self.elapsed_since(self._start_time)
    
    @contextmanager
    def execution_context(self):
        """Context manager for automatic timing and metrics collection."""
        start_time = self.start()
        success = True
        try:
            yield self
        except Exception:
            success = False
            raise
        finally:
            duration = self.elapsed_since(start_time)
            with self._lock:
                self.metrics.update(duration, success)
    
    @contextmanager
    def timeout_context(self, timeout_seconds: float):
        """Context manager that raises TimeoutError if execution exceeds timeout."""
        start_time = self.start()
        
        try:
            yield self
            # Check if execution exceeded timeout
            elapsed = self.elapsed_since(start_time)
            if elapsed > timeout_seconds:
                raise TimeoutError(f"Execution exceeded {timeout_seconds}s timeout (took {elapsed:.3f}s)")
        finally:
            pass
    
    def log_timing_violation(self, component: str, actual_duration: float, 
                           expected_duration: Optional[float] = None):
        """Log a timing constraint violation."""
        if expected_duration is None and self.target_hz is not None:
            expected_duration = 1.0 / self.target_hz
        
        if expected_duration is not None:
            violation = TimingViolation(
                component=component,
                expected_duration=expected_duration,
                actual_duration=actual_duration,
                timestamp=self.now(),
                severity="warning" if actual_duration < expected_duration * 1.5 else "error"
            )
            
            with self._lock:
                self.metrics.violations.append(violation)
    
    def log_execution(self, component: str, duration: float, success: bool = True):
        """Log execution completion with automatic violation detection."""
        with self._lock:
            self.metrics.update(duration, success)
        
        # Check for timing violations if target frequency is set
        if self.target_hz is not None:
            expected_duration = 1.0 / self.target_hz
            if duration > expected_duration:
                self.log_timing_violation(component, duration, expected_duration)
    
    def log_timeout(self, component: str, timeout_duration: float):
        """Log a timeout occurrence."""
        violation = TimingViolation(
            component=component,
            expected_duration=timeout_duration,
            actual_duration=timeout_duration,
            timestamp=self.now(),
            severity="critical"
        )
        
        with self._lock:
            self.metrics.violations.append(violation)
    
    def print_performance_summary(self):
        """Print comprehensive performance summary."""
        with self._lock:
            m = self.metrics
            success_rate = (m.successful_executions / max(m.total_executions, 1)) * 100
            
            print(f"\n=== Timer Performance: {self.name} ===")
            print(f"Executions: {m.total_executions} | Success: {success_rate:.1f}%")
            print(f"Duration: avg={m.average_duration:.3f}s, min={m.min_duration:.3f}s, max={m.max_duration:.3f}s")
            
            if self.target_hz:
                target_duration = 1.0 / self.target_hz
                print(f"Target: {target_duration:.3f}s ({self.target_hz:.1f}Hz) | Violations: {len(m.violations)}")
                
                # Show recent violations
                if m.violations:
                    print("Recent violations:")
                    for violation in m.violations[-3:]:  # Show last 3
                        print(f"  {violation.component}: {violation.actual_duration:.3f}s "
                              f"(expected {violation.expected_duration:.3f}s) [{violation.severity}]")


class RateLimiter:
    """Rate limiting utility for maintaining consistent execution frequency."""
    
    def __init__(self, target_hz: float):
        """Initialize rate limiter with target frequency in Hz."""
        self.target_hz = target_hz
        self.target_period = 1.0 / target_hz
        self.last_execution = 0.0
        self._lock = threading.Lock()
    
    def wait_for_next_cycle(self):
        """Wait until it's time for the next execution cycle."""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_execution
            
            if time_since_last < self.target_period:
                sleep_time = self.target_period - time_since_last
                time.sleep(sleep_time)
            
            self.last_execution = time.time()
    
    @contextmanager
    def rate_limited_execution(self):
        """Context manager for rate-limited execution."""
        try:
            yield
        finally:
            self.wait_for_next_cycle()


class FrequencyCoordinator:
    """General-purpose coordinator for multiple execution frequencies.
    
    This is a generic utility that can coordinate any number of different
    execution rates. Application-specific coordination patterns
    should be built on top of this primitive.
    """
    
    def __init__(self, frequency_configs: Dict[str, float]):
        """Initialize with frequency configurations.
        
        Args:
            frequency_configs: Dict mapping names to frequencies in Hz
                             e.g., {"planning": 1.0, "control": 30.0, "sensing": 60.0}
        """
        self.frequency_configs = frequency_configs
        self.timers = {}
        self.limiters = {}
        self.shared_state = {}
        self._lock = threading.Lock()
        
        for name, hz in frequency_configs.items():
            self.timers[name] = ExecutionTimer(hz, name)
            self.limiters[name] = RateLimiter(hz)
    
    @contextmanager
    def frequency_context(self, frequency_name: str):
        """Context for execution at specified frequency."""
        if frequency_name not in self.frequency_configs:
            raise ValueError(f"Unknown frequency: {frequency_name}. "
                           f"Available: {list(self.frequency_configs.keys())}")
        
        with self.limiters[frequency_name].rate_limited_execution():
            with self.timers[frequency_name].execution_context():
                yield self.timers[frequency_name]

    # Backward-compatibility alias used in tests
    def rate_context(self, frequency_name: str):
        return self.frequency_context(frequency_name)
    
    def set_shared_state(self, key: str, value: Any):
        """Set shared state between different execution frequencies."""
        with self._lock:
            self.shared_state[key] = value
    
    def get_shared_state(self, key: str, default: Any = None) -> Any:
        """Get shared state between different execution frequencies."""
        with self._lock:
            return self.shared_state.get(key, default)
    
    def print_performance_summary(self):
        """Print performance summary for all frequencies."""
        print(f"\n=== Frequency Coordination Summary ===")
        for name, timer in self.timers.items():
            timer.print_performance_summary()


# Functional helpers for declarative timing constraints
def with_timing_constraint(constraint: TimeConstraint):
    """Decorator to add timing constraint to any function."""
    def decorator(func: Callable[[T], Any]) -> Callable[[T], Any]:
        def wrapped(input_data: T) -> Any:
            timer = ExecutionTimer()
            
            with timer.timeout_context(constraint.max_duration):
                result = func(input_data)
            
            # Check constraint compliance
            execution_time = timer.elapsed()
            if execution_time > constraint.max_duration:
                timer.log_timing_violation("function", execution_time, constraint.max_duration)
            
            return result
        
        return wrapped
    return decorator


def with_rate_limiting(target_hz: float):
    """Decorator to add rate limiting to any function."""
    limiter = RateLimiter(target_hz)
    
    def decorator(func: Callable[[T], Any]) -> Callable[[T], Any]:
        def wrapped(input_data: T) -> Any:
            with limiter.rate_limited_execution():
                return func(input_data)
        
        return wrapped
    return decorator


# Timing validation utilities
def validate_timing_accuracy(target_duration: float, tolerance: float = 0.001) -> bool:
    """Validate timing accuracy of the system."""
    timer = ExecutionTimer()
    start_time = timer.start()
    time.sleep(target_duration)
    actual_duration = timer.elapsed()
    
    error = abs(actual_duration - target_duration)
    return error <= tolerance


def benchmark_execution_overhead() -> float:
    """Benchmark the overhead of timing measurement."""
    iterations = 100
    
    def realistic_workload():
        """Simulate realistic computation work."""
        # Simple computation that takes measurable time
        result = 0
        for i in range(100):
            result += i * i
        return result
    
    # Measure baseline (no timing)
    start_time = time.time()
    for _ in range(iterations):
        realistic_workload()
    baseline_duration = time.time() - start_time
    
    # Measure with timing
    timer = ExecutionTimer()
    start_time = time.time()
    for _ in range(iterations):
        with timer.execution_context():
            realistic_workload()
    timed_duration = time.time() - start_time
    
    # Calculate overhead percentage
    if baseline_duration > 0:
        overhead = ((timed_duration - baseline_duration) / baseline_duration) * 100
    else:
        overhead = 0.0
    
    return max(0.0, overhead)  # Ensure non-negative
