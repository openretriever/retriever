"""
PipelineController - Central control API for managing pipeline execution.

Provides pause/resume/reset for individual flows or entire pipeline.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set
import threading
import time

from retriever.rt.control.channel import (
    ControlChannel, ControlCommand, ControlMessage, ControlResponse
)
from retriever.rt.control.controllable import FlowStatus, FlowState


@dataclass
class PipelineStatus:
    """Aggregate status of the entire pipeline."""
    name: str
    state: str  # "running", "paused", "stopped", "partial" (some paused)
    node_count: int
    nodes: Dict[str, FlowStatus]
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "node_count": self.node_count,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "timestamp": self.timestamp,
        }


class PipelineController:
    """
    Central control API for managing pipeline execution.

    Provides:
    - pause()/resume()/reset() for individual flows or entire pipeline
    - get_state() for status inspection
    - Event callbacks for state changes

    Works with any backend by using the ControlChannel abstraction.

    Usage:
        # During pipeline setup
        controller = PipelineController(pipeline, control_channel)

        # During execution
        controller.pause()          # Pause all flows
        controller.pause("camera")  # Pause specific flow
        controller.resume()         # Resume all

        status = controller.get_state()
        print(status.nodes["planner"].step_count)
    """

    def __init__(
        self,
        pipeline: "Pipeline",
        channel: ControlChannel,
        *,
        timeout: float = 5.0,
    ):
        """
        Initialize controller.

        Args:
            pipeline: The Pipeline instance being controlled
            channel: ControlChannel for communication with executors
            timeout: Default timeout for control commands
        """
        self._pipeline = pipeline
        self._channel = channel
        self._timeout = timeout
        self._name = pipeline.get_name()

        # Track known node IDs
        self._node_ids: Set[str] = set()
        for handle in pipeline.get_handles():
            self._node_ids.add(pipeline.get_node_id(handle))

        # State cache (updated by callbacks)
        self._state_cache: Dict[str, FlowStatus] = {}
        self._state_lock = threading.Lock()

        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "on_pause": [],
            "on_resume": [],
            "on_reset": [],
            "on_state_change": [],
            "on_error": [],
        }

    # =========================================================================
    # Control Commands
    # =========================================================================

    def pause(self, target: Optional[str] = None) -> bool:
        """
        Pause flow(s).

        Args:
            target: Node ID to pause, or None for all flows.

        Returns:
            True if command was acknowledged by all targets.
        """
        return self._send_command(ControlCommand.PAUSE, target)

    def resume(self, target: Optional[str] = None) -> bool:
        """
        Resume flow(s).

        Args:
            target: Node ID to resume, or None for all flows.
        """
        return self._send_command(ControlCommand.RESUME, target)

    def reset(self, target: Optional[str] = None) -> bool:
        """
        Reset flow state(s).

        Flows should be paused before reset for safety.

        Args:
            target: Node ID to reset, or None for all flows.
        """
        return self._send_command(ControlCommand.RESET, target)

    def stop(self, target: Optional[str] = None) -> bool:
        """
        Stop flow(s) gracefully.

        Args:
            target: Node ID to stop, or None for all flows.
        """
        return self._send_command(ControlCommand.STOP, target)

    # =========================================================================
    # State Inspection
    # =========================================================================

    def get_state(self, target: Optional[str] = None) -> PipelineStatus:
        """
        Get current state of the pipeline or specific flow.

        Args:
            target: Node ID for specific flow, or None for entire pipeline.

        Returns:
            PipelineStatus with state of all requested flows.
        """
        message = ControlMessage(
            command=ControlCommand.GET_STATE,
            target=target,
        )

        self._channel.send_command(message)

        # Collect responses
        expected = {target} if target else self._node_ids.copy()
        responses: Dict[str, FlowStatus] = {}
        deadline = time.time() + self._timeout

        while expected and time.time() < deadline:
            response = self._channel.receive_response(timeout=0.1)
            if response and response.request_id == message.request_id:
                if response.success and response.data:
                    status = FlowStatus(**response.data)
                    responses[response.node_id] = status
                    expected.discard(response.node_id)

        # Update cache
        with self._state_lock:
            self._state_cache.update(responses)

        # Determine aggregate state
        states = {s.state for s in responses.values()}
        if len(states) == 1:
            aggregate = list(states)[0].value
        elif FlowState.ERROR in states:
            aggregate = "error"
        elif FlowState.PAUSED in states and FlowState.RUNNING in states:
            aggregate = "partial"
        else:
            aggregate = "unknown"

        return PipelineStatus(
            name=self._name,
            state=aggregate,
            node_count=len(self._node_ids),
            nodes=responses,
        )

    def get_cached_state(self) -> PipelineStatus:
        """Get last known state without querying executors."""
        with self._state_lock:
            return PipelineStatus(
                name=self._name,
                state="cached",
                node_count=len(self._node_ids),
                nodes=self._state_cache.copy(),
            )

    # =========================================================================
    # Event Callbacks
    # =========================================================================

    def on(self, event: str, callback: Callable) -> None:
        """
        Register callback for control events.

        Events:
            - on_pause: Called when flow(s) are paused
            - on_resume: Called when flow(s) are resumed
            - on_reset: Called when flow(s) are reset
            - on_state_change: Called on any state change
            - on_error: Called when an error occurs
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, *args) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception:
                pass  # Don't let callback errors break control flow

    # =========================================================================
    # Internal
    # =========================================================================

    def _send_command(
        self,
        command: ControlCommand,
        target: Optional[str],
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send command and wait for acknowledgment."""
        message = ControlMessage(
            command=command,
            target=target,
            payload=payload,
        )

        self._channel.send_command(message)

        # Wait for acknowledgments
        expected = {target} if target else self._node_ids.copy()
        deadline = time.time() + self._timeout

        while expected and time.time() < deadline:
            response = self._channel.receive_response(timeout=0.1)
            if response and response.request_id == message.request_id:
                if response.success:
                    expected.discard(response.node_id)
                else:
                    self._emit("on_error", response.node_id, response.error)

        # Emit appropriate event
        event_map = {
            ControlCommand.PAUSE: "on_pause",
            ControlCommand.RESUME: "on_resume",
            ControlCommand.RESET: "on_reset",
        }
        if command in event_map:
            self._emit(event_map[command], target)

        return len(expected) == 0
