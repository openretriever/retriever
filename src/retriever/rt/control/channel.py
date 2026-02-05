"""
Control channel for communicating between control plane and data plane.

The ControlChannel provides a backend-agnostic way for control signals
to reach executors and flows during pipeline execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import time
import uuid


class ControlCommand(Enum):
    """Control commands that can be sent to flows/executors."""
    PAUSE = "pause"
    RESUME = "resume"
    RESET = "reset"
    STOP = "stop"
    GET_STATE = "get_state"
    SET_CONFIG = "set_config"
    LOG_OUTPUT = "log_output"  # Flow stdout/stderr output for web UI


@dataclass
class ControlMessage:
    """
    A control message sent through the ControlChannel.

    Attributes:
        command: The control command to execute
        target: Optional target node_id (None = all nodes)
        payload: Optional command-specific data
        timestamp: When the command was issued
        request_id: Unique ID for request/response correlation
    """
    command: ControlCommand
    target: Optional[str] = None  # None means "all flows"
    payload: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=lambda: time.time())
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ControlResponse:
    """Response to a control message."""
    request_id: str
    node_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())


class ControlChannel(ABC):
    """
    Abstract base class for control channels.

    Control channels provide bidirectional communication between:
    - PipelineController (control plane)
    - Executors/Flows (data plane)

    Different backends implement this differently:
    - In-process: Direct method calls or thread-safe queues
    - Multiprocessing: multiprocessing.Queue + shared memory
    - Dora: Dora's built-in control messages or dedicated control node
    """

    @abstractmethod
    def send_command(self, message: ControlMessage) -> None:
        """Send a control command (non-blocking)."""
        pass

    @abstractmethod
    def receive_command(self, timeout: float = 0.0) -> Optional[ControlMessage]:
        """Receive a control command (blocking with timeout)."""
        pass

    @abstractmethod
    def send_response(self, response: ControlResponse) -> None:
        """Send a response back to the controller."""
        pass

    @abstractmethod
    def receive_response(self, timeout: float = 1.0) -> Optional[ControlResponse]:
        """Receive a response from an executor."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the channel and release resources."""
        pass


class MPControlChannel(ControlChannel):
    """
    Multiprocessing-based control channel using Queues.

    Uses two queues:
    - command_queue: Controller -> Executors
    - response_queue: Executors -> Controller

    Each executor polls command_queue in its event loop.

    Note: Queues can only be shared through inheritance (fork), not pickling.
    """

    def __init__(self, command_queue=None, response_queue=None):
        import multiprocessing
        self._command_queue = command_queue or multiprocessing.Queue()
        self._response_queue = response_queue or multiprocessing.Queue()

    @property
    def command_queue(self):
        return self._command_queue

    @property
    def response_queue(self):
        return self._response_queue

    def send_command(self, message: ControlMessage) -> None:
        self._command_queue.put(message, block=False)

    def receive_command(self, timeout: float = 0.0) -> Optional[ControlMessage]:
        try:
            return self._command_queue.get(block=True, timeout=timeout)
        except Exception:
            return None

    def send_response(self, response: ControlResponse) -> None:
        self._response_queue.put(response, block=False)

    def receive_response(self, timeout: float = 1.0) -> Optional[ControlResponse]:
        try:
            return self._response_queue.get(block=True, timeout=timeout)
        except Exception:
            return None

    def close(self) -> None:
        self._command_queue.close()
        self._response_queue.close()


class InProcessControlChannel(ControlChannel):
    """
    In-process control channel for Pipeline.step() debugging.

    Uses simple thread-safe queues since everything runs in one process.
    """

    def __init__(self):
        from queue import Queue
        self._command_queue = Queue()
        self._response_queue = Queue()

    def send_command(self, message: ControlMessage) -> None:
        self._command_queue.put(message)

    def receive_command(self, timeout: float = 0.0) -> Optional[ControlMessage]:
        from queue import Empty
        try:
            return self._command_queue.get(block=True, timeout=timeout)
        except Empty:
            return None

    def send_response(self, response: ControlResponse) -> None:
        self._response_queue.put(response)

    def receive_response(self, timeout: float = 1.0) -> Optional[ControlResponse]:
        from queue import Empty
        try:
            return self._response_queue.get(block=True, timeout=timeout)
        except Empty:
            return None

    def close(self) -> None:
        pass  # Python queues don't need explicit close
