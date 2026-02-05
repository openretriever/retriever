"""
Controllable mixin for flows that support external control.

Adds pause/resume/reset capabilities and state reporting to flows.
"""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import threading
import time


class FlowState(Enum):
    """Execution state of a flow."""
    UNINITIALIZED = "uninitialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class FlowStatus:
    """
    Complete status snapshot of a flow.

    This is what gets reported back when get_state() is called.
    """
    node_id: str
    flow_class: str
    state: FlowState

    # Timing info
    init_time: Optional[float] = None
    last_step_time: Optional[float] = None
    step_count: int = 0

    # Custom state from flow (opt-in)
    custom_state: Dict[str, Any] = field(default_factory=dict)

    # Error info (if state == ERROR)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "flow_class": self.flow_class,
            "state": self.state.value,
            "init_time": self.init_time,
            "last_step_time": self.last_step_time,
            "step_count": self.step_count,
            "custom_state": self.custom_state,
            "error_message": self.error_message,
        }


class Controllable(ABC):
    """
    Mixin for flows that support external control.

    Adds pause/resume/reset capabilities and state reporting.
    Flows that inherit from this can be controlled via PipelineController.

    Usage:
        class MyFlow(Controllable, Flow[Input, Output]):
            def reset(self) -> None:
                super().reset()  # Reset control counters
                # Reset your internal state
                self.counter = 0
                self.buffer.clear()

            def get_custom_state(self) -> Dict[str, Any]:
                # Report custom state for inspection
                return {"counter": self.counter, "buffer_size": len(self.buffer)}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._control_state = FlowState.UNINITIALIZED
        self._control_lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._step_count = 0
        self._init_time: Optional[float] = None
        self._last_step_time: Optional[float] = None
        self._error_message: Optional[str] = None

    # =========================================================================
    # State Management
    # =========================================================================

    @property
    def control_state(self) -> FlowState:
        """Current control state of the flow."""
        with self._control_lock:
            return self._control_state

    def _set_state(self, state: FlowState) -> None:
        """Internal: Set control state."""
        with self._control_lock:
            self._control_state = state

    # =========================================================================
    # Control Hooks (called by executor)
    # =========================================================================

    def control_init(self) -> None:
        """Called by executor after flow.init()."""
        self._init_time = time.time()
        self._set_state(FlowState.RUNNING)

    def control_pre_step(self) -> bool:
        """
        Called by executor before each step.

        Returns:
            True if step should proceed, False if paused.
        """
        # Wait if paused (with timeout to allow checking stop flag)
        if not self._pause_event.wait(timeout=0.1):
            return False

        if self._control_state in (FlowState.STOPPED, FlowState.ERROR):
            return False

        return True

    def control_post_step(self) -> None:
        """Called by executor after each step."""
        with self._control_lock:
            self._step_count += 1
            self._last_step_time = time.time()

    def control_finalize(self) -> None:
        """Called by executor before flow.finalize()."""
        self._set_state(FlowState.STOPPED)

    def control_error(self, error: Exception) -> None:
        """Called by executor when an error occurs."""
        self._set_state(FlowState.ERROR)
        self._error_message = str(error)

    # =========================================================================
    # Control Commands
    # =========================================================================

    def pause(self) -> None:
        """
        Pause the flow.

        The flow will complete its current step, then wait until resume() is called.
        """
        self._pause_event.clear()
        self._set_state(FlowState.PAUSED)

    def resume(self) -> None:
        """Resume the flow after being paused."""
        self._pause_event.set()
        if self._control_state == FlowState.PAUSED:
            self._set_state(FlowState.RUNNING)

    def reset(self) -> None:
        """
        Reset internal state.

        MUST be overridden by subclasses to reset their specific state.
        This is called while the flow is paused.

        Default implementation resets control counters only.
        """
        with self._control_lock:
            self._step_count = 0
            self._last_step_time = None
            self._error_message = None

    def __getstate__(self):
        """
        Exclude threading primitives when pickling.

        This allows Controllable flows to be pickled for multiprocessing.
        Threading locks and events cannot be pickled and must be recreated
        in the child process.
        """
        state = self.__dict__.copy()
        # Remove unpicklable threading objects
        state.pop('_control_lock', None)
        state.pop('_pause_event', None)
        return state

    def __setstate__(self, state):
        """
        Recreate threading primitives after unpickling.

        Called in the child process after pickling to restore the flow state.
        """
        self.__dict__.update(state)
        # Recreate threading objects
        import threading
        self._control_lock = threading.Lock()
        self._pause_event = threading.Event()
        # Restore pause state based on control state
        if self._control_state == FlowState.RUNNING:
            self._pause_event.set()  # Not paused
        else:
            self._pause_event.clear()  # Paused

    # =========================================================================
    # State Reporting
    # =========================================================================

    def get_custom_state(self) -> Dict[str, Any]:
        """
        Override to report custom state for inspection.

        Returns:
            Dict of custom state that will be included in FlowStatus.
        """
        return {}

    def get_status(self, node_id: str) -> FlowStatus:
        """Get complete status snapshot."""
        return FlowStatus(
            node_id=node_id,
            flow_class=self.__class__.__name__,
            state=self.control_state,
            init_time=self._init_time,
            last_step_time=self._last_step_time,
            step_count=self._step_count,
            custom_state=self.get_custom_state(),
            error_message=self._error_message,
        )
