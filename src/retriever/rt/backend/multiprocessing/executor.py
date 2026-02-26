"""
MPExecutor - Process-based executor for multiprocessing backend.

Wraps a Flow for execution in a separate process using multiprocessing.Process.
"""

import multiprocessing
from contextlib import nullcontext
from typing import Dict, List, Optional, Any
from retriever.flow.base import Flow
from retriever.flow.clock import Clock
from retriever.flow.adapter import Adapter
from retriever.rt.backend.interface import Executor, Subscriber, Publisher
from retriever.rt.backend.multiprocessing.scheduler import MPScheduler
from retriever.rt.step import IOStep
from retriever.rt.logging.worker import configure_worker
from retriever.rt.logging.handlers.otel import shutdown_otel

import logging
logger = logging.getLogger(__name__)

# Control support (optional)
try:
    from retriever.rt.control.channel import ControlChannel, ControlCommand, ControlMessage, ControlResponse
    from retriever.rt.control.controllable import Controllable, FlowState
    CONTROL_AVAILABLE = True
except ImportError:
    CONTROL_AVAILABLE = False


class MPExecutor(multiprocessing.Process, Executor):
    """
    Process-based executor for multiprocessing backend.

    Each executor runs one flow in isolation with its own:
    - Scheduler (determines when to execute)
    - Input channels (receives data)
    - Output channels (publishes results)
    - Adapters (samples input data)
    """

    def __init__(
        self,
        node_id: str,
        flow: Flow,
        clock: Clock,
        inputs: Dict[str, Subscriber],
        outputs: Dict[str, List[Publisher]],
        adapters: Dict[str, Adapter],
        log_params: Optional[Dict[str, Any]] = None,
        control_channel: Optional[Any] = None,
        control_command_queue: Optional[Any] = None,
        control_response_queue: Optional[Any] = None,
        control_log_queue: Optional[Any] = None,
    ):
        """
        Initialize MPExecutor.

        Args:
            node_id: Unique node identifier
            flow: Flow instance to execute
            clock: Clock for scheduling
            inputs: Dict mapping input port names to Subscribers
            outputs: Dict mapping output port names to List[Publishers]
            adapters: Dict mapping input port names to Adapters
            log_params: Logging params (queue, config, log_dir)
            control_channel: Optional ControlChannel (deprecated, use queues instead)
            control_command_queue: Optional multiprocessing.Queue for commands
            control_response_queue: Optional multiprocessing.Queue for responses
            control_log_queue: Optional multiprocessing.Queue for flow log messages
        """
        super().__init__(name=node_id)
        self.node_id = node_id
        self.flow = flow
        self.clock = clock
        self.inputs = inputs
        self.outputs = outputs
        self.adapters = adapters
        self.log_params = log_params
        self.scheduler = MPScheduler(clock)
        self._stop_flag = multiprocessing.Event()

        # Store queue references (will create channel in run() after fork/spawn)
        self._control_command_queue = control_command_queue
        self._control_response_queue = control_response_queue
        self._control_log_queue = control_log_queue
        self._control_channel = control_channel  # May be set lazily in run() from queues

        self._is_controllable = CONTROL_AVAILABLE and isinstance(flow, Controllable) if CONTROL_AVAILABLE else False

    @property
    def name(self) -> str:
        """Executor name/identifier."""
        return self.node_id

    def _process_control_commands(self) -> bool:
        """
        Process any pending control commands.

        Returns:
            False if executor should stop, True otherwise.
        """
        if not self._control_channel or not CONTROL_AVAILABLE:
            return True

        # Non-blocking check for commands
        message = self._control_channel.receive_command(timeout=0)
        if message is None:
            return True

        # Check if this command targets us (with per-node queues, this should always match)
        if message.target is not None and message.target != self.node_id:
            return True

        # Handle command
        response = self._handle_control_command(message)
        self._control_channel.send_response(response)

        # STOP command returns False
        if message.command == ControlCommand.STOP:
            return False

        return True

    def _handle_control_command(self, message: ControlMessage) -> ControlResponse:
        """Handle a single control command."""
        if not CONTROL_AVAILABLE:
            return ControlResponse(
                request_id=message.request_id,
                node_id=self.node_id,
                success=False,
                error="Control not available",
            )

        try:
            if message.command == ControlCommand.PAUSE:
                if self._is_controllable:
                    self.flow.pause()
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                )

            elif message.command == ControlCommand.RESUME:
                if self._is_controllable:
                    self.flow.resume()
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                )

            elif message.command == ControlCommand.RESET:
                # Ensure paused before reset
                if self._is_controllable:
                    was_running = self.flow.control_state == FlowState.RUNNING
                    if was_running:
                        self.flow.pause()

                    # Clear queues and adapters before resetting flow state
                    self._clear_input_queues()
                    self._reset_adapters()

                    self.flow.reset()

                    if was_running:
                        self.flow.resume()
                else:
                    # Non-controllable flow: still clear queues/adapters, then reset
                    self._clear_input_queues()
                    self._reset_adapters()

                    if hasattr(self.flow, 'reset'):
                        self.flow.reset()

                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                )

            elif message.command == ControlCommand.STOP:
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                )

            elif message.command == ControlCommand.GET_STATE:
                if self._is_controllable:
                    status = self.flow.get_status(self.node_id)
                    data = status.to_dict()
                else:
                    # Non-controllable: basic info only
                    data = {
                        "node_id": self.node_id,
                        "flow_class": self.flow.__class__.__name__,
                        "state": "running",
                        "step_count": 0,
                        "custom_state": {},
                    }

                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                    data=data,
                )

            else:
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=False,
                    error=f"Unknown command: {message.command}",
                )

        except Exception as e:
            return ControlResponse(
                request_id=message.request_id,
                node_id=self.node_id,
                success=False,
                error=str(e),
            )

    def _should_execute_step(self) -> bool:
        """Check if step should proceed (respecting pause state)."""
        if self._is_controllable:
            return self.flow.control_pre_step()
        return True

    def _clear_input_queues(self) -> None:
        """
        Drain all input queues to remove stale messages.

        Called during reset to ensure downstream flows don't process
        messages from before the reset point.
        """
        from queue import Empty

        for port_name, subscriber in self.inputs.items():
            count = 0
            try:
                while not subscriber.empty():
                    subscriber.get_nowait()
                    count += 1
            except Empty:
                pass

            if count > 0:
                logger.info(f"[{self.node_id}] Cleared {count} stale messages from '{port_name}'")

    def _reset_adapters(self) -> None:
        """
        Reset all adapters to clear their internal state.

        Adapters like Hold maintain state (last value, timestamps)
        that should be cleared during pipeline reset.
        """
        for port_name, adapter in self.adapters.items():
            if hasattr(adapter, 'reset'):
                adapter.reset()
                logger.debug(f"[{self.node_id}] Reset adapter for '{port_name}'")

    def run(self):
        """
        Main process loop.

        Lifecycle:
        1. Configure logging for this worker
        2. Initialize flow (flow.init())
        3. Reset scheduler
        4. Main execution loop:
           - Advance to next execution point (scheduler.next)
           - Sample inputs using adapters (Signal.sample)
           - Transform via flow.run() (Signal.transform)
           - Publish outputs (Signal.publish)
        5. Finalize flow (flow.finalize())
        6. Shutdown OTel
        """
        # Configure logging for this worker process
        if self.log_params:
            configure_worker(
                self.node_id,
                type(self.flow).__name__,
                self.log_params['queue'],
                self.log_params['config'],
                self.log_params['log_dir'],
            )

        # Create control channel from queues (now that we're in the child process)
        if self._control_channel is None and self._control_command_queue is not None and self._control_response_queue is not None:
            from retriever.rt.control.channel import MPControlChannel
            self._control_channel = MPControlChannel(
                self._control_command_queue,
                self._control_response_queue,
                self._control_log_queue,
            )

        # Wrap stdout/stderr for output capture (if control enabled)
        if self._control_channel and CONTROL_AVAILABLE:
            try:
                import sys
                from retriever.rt.control.output_capture import FlowOutputCapture
                sys.stdout = FlowOutputCapture(self.node_id, self._control_channel, "stdout")
                sys.stderr = FlowOutputCapture(self.node_id, self._control_channel, "stderr")
            except Exception as e:
                logger.warning(f"[{self.node_id}] Failed to enable output capture: {e}")

        tracer = None
        try:
            from opentelemetry import trace  # type: ignore
            tracer = trace.get_tracer('retriever.runtime')
        except Exception:
            tracer = None

        logger.info(f"[{self.node_id}] Starting MPExecutor")

        try:
            # Initialize flow
            self.flow.init()
            if self._is_controllable:
                self.flow.control_init()
            logger.info(f"[{self.node_id}] Flow initialized")

            # Reset scheduler
            self.scheduler.reset()

            # Main execution loop
            while not self._stop_flag.is_set():
                # Check for control commands
                if not self._process_control_commands():
                    break

                # Check if paused
                if not self._should_execute_step():
                    import time
                    time.sleep(0.01)  # Avoid busy loop when paused
                    continue

                # Advance to next execution point (scheduler handles drain)
                result = self.scheduler.next(self.inputs)

                if not result.should_execute:
                    continue

                # FRP Signal pipeline: sample → transform → publish
                span_cm = (
                    tracer.start_as_current_span('signal-function')
                    if tracer is not None
                    else nullcontext()
                )
                with span_cm as signal_span:
                    if signal_span is not None and hasattr(signal_span, "set_attributes"):
                        signal_span.set_attributes({
                            'node_id': self.node_id,
                            'fields': result.fields_to_sample,
                        })
                    IOStep(
                        self.inputs,
                        result.fields_to_sample,
                        output_types=self.flow.output_types,
                        now=result.now,
                    ) \
                        .sample(self.flow.input_types, self.adapters, now=result.now) \
                        .transform(self.flow.run) \
                        .publish(self.outputs)

                if self._is_controllable:
                    self.flow.control_post_step()

        except KeyboardInterrupt:
            logger.info(f"[{self.node_id}] Interrupted")
        except Exception as e:
            logger.error(f"[{self.node_id}] Error: {e}", exc_info=True)
            if self._is_controllable:
                self.flow.control_error(e)
        finally:
            # Finalize flow
            if self._is_controllable:
                self.flow.control_finalize()
            self.flow.finalize()
            logger.info(f"[{self.node_id}] MPExecutor terminated")
            # Flush OTel before exit only if it was enabled/configured for this worker.
            if self.log_params and getattr(self.log_params.get("config"), "otel_enabled", False):
                shutdown_otel()

    def stop(self):
        """Signal executor to stop gracefully."""
        self._stop_flag.set()

    # join() method inherited from multiprocessing.Process
    # is_alive() method inherited from multiprocessing.Process
