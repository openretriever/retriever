"""
Backend abstraction interfaces for retriever runtime system.

Defines protocols and abstract base classes for execution backends.
"""

from typing import Tuple, Dict, Any, List, Optional
from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from retriever.ir import IR
from retriever.flow.clock import Clock


# ============================================================================
# Execution Engine Interface
# ============================================================================

class ExecutionEngine(ABC):
    """
    Backend execution engine interface.

    Each backend implements this to orchestrate pipeline execution.
    Manages the complete lifecycle: build → start → run → stop.
    """



    @abstractmethod
    def build(self) -> None:
        """
        Build runtime from IR.

        Creates transport channels, loads flows, creates executors.
        NOTE: Must be called before start().
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start all executors.

        Executors begin their execution loops.
        NOTE: Must call build() first.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop all executors gracefully.

        Sends termination signals and waits for cleanup.
        """
        pass

    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> None:
        """
        Wait while executors are running.

        Blocks until all executors finish or timeout is reached.

        Args:
            timeout: Optional timeout in seconds
        """
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Check if any executor is still alive.

        Returns:
            True if at least one executor is running
        """
        pass

    def __enter__(self):
        """Execution context manager entry."""
        self.build()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Execution context manager exit."""
        self.stop()
        return False


# ============================================================================
# Executor Interface
# ============================================================================

class Executor(ABC):
    """
    Flow executor process interface

    Abstracts the execution context for a single flow.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Executor name (typically node_id).
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start executor.

        Begins execution loop in isolated context.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop executor gracefully.

        Sends termination signal and allows cleanup.
        """
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Check if executor is running.

        Returns:
            True if executor is active
        """
        pass

    @abstractmethod
    def join(self, timeout: Optional[float] = None) -> None:
        """
        Wait for executor to terminate.

        Args:
            timeout: Optional timeout in seconds
        """
        pass


# ============================================================================
# Channel Interfaces
# ============================================================================

@runtime_checkable
class Publisher(Protocol):
    """
    Publisher interface for sending timestamped messages.
    Timestamps created at sender when data is generated.
    """

    def put_one(self, value: Any, timestamp: float, block: bool = True) -> None:
        """
        Publish message with timestamp.

        Args:
            value: Message value
            timestamp: Sender timestamp
            block: Block until space available

        Raises:
            Exception: If buffer full and block=False
        """
        ...


@runtime_checkable
class Subscriber(Protocol):
    """
    Subscriber interface for receiving timestamped messages.
    Non-destructive reads preserve history for adapters.
    """

    def new_arrival(self) -> bool:
        """Check if new data arrived."""
        ...

    def get_all(self) -> List[Tuple[float, Any]]:
        """
        Get all buffered messages without removing them.

        Returns:
            List of (timestamp, value) tuples in chronological order
        """
        ...

    def empty(self) -> bool:
        """Check if buffer is empty."""
        ...

    def clear(self) -> None:
        """Remove all buffered messages."""
        ...


# ============================================================================
# Scheduler Interface
# ============================================================================

@dataclass
class ScheduleResult:
    """
    Result of scheduler next() operation.

    Attributes:
        should_execute: Whether flow should execute now
        fields_to_sample: [] (no), ["..."] (all), or list (specific)
        now: Wall-clock timestamp associated with this execution decision
    """
    should_execute: bool
    fields_to_sample: Optional[List[str]] = None
    now: Optional[float] = None


class Scheduler(ABC):
    """
    Scheduler interface for flow execution timing.

    Determines when flows execute and which fields to sample
    based on clock configuration (Rate/Trigger/Hybrid).
    """

    @abstractmethod
    def __init__(self, clock: Clock):
        """
        Initialize scheduler with clock configuration.

        Args:
            clock: Clock configuration (Rate/Trigger/Hybrid)
        """
        pass

    @abstractmethod
    def next(self, inputs: Dict[str, Subscriber]) -> ScheduleResult:
        """
        Advance to next execution point.

        For blocking backends: blocks until flow should execute.
        For event-driven backends: non-blocking check of current state.

        Args:
            inputs: Dict mapping port name to Subscriber

        Returns:
            ScheduleResult with execution decision and fields to sample
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Reset scheduler timing state.

        Called after flow initialization.
        """
        pass


# ============================================================================
# Backend Factory Interface
# ============================================================================

@runtime_checkable
class BackendFactory(Protocol):
    """
    Backend factory interface.

    Creates backend-specific ExecutionEngine.
    Registered via @register_backend decorator.

    Example:
        @register_backend('multiprocessing')
        class MPBackendFactory:
            @property
            def name(self) -> str:
                return 'multiprocessing'

            @property
            def description(self) -> str:
                return "Python multiprocessing backend"

            def validate_dependencies(self) -> bool:
                return True

            def create_engine(self, ir, config=None):
                return MPEngine(ir, config)
    """

    @property
    def name(self) -> str:
        """
        Backend name (e.g., 'multiprocessing', 'dora').

        Returns:
            Unique backend identifier
        """
        ...

    @property
    def description(self) -> str:
        """
        Backend description.

        Returns:
            Human-readable backend description
        """
        ...

    def validate_dependencies(self) -> bool:
        """
        Validate backend dependencies are available.

        Returns:
            True if all dependencies are met, False otherwise
        """
        ...

    def create_engine(
        self,
        ir: IR,
        config: Optional[Dict[str, Any]] = None,
    ) -> ExecutionEngine:
        """
        Create execution engine for this backend.

        Args:
            ir: Validated IR
            config: Backend-specific configuration

        Returns:
            ExecutionEngine instance for this backend
        """
        ...
