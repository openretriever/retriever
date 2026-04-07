"""
DoraExecutor - Dora-based executor for flows.

Wraps a Flow for execution in a separate process using dora.Node for communication.
Flow.step() may yield ServiceCall for async RPC - executor drives the generator.
"""

import time
import uuid
import types
import dora
import multiprocessing
from typing import Dict, List, Optional, Any, Generator

from retriever.flow.base import Flow
from retriever.flow.clock import Clock
from retriever.ir.core import IRNode
from retriever.rt.step import IOStep
from retriever.flow.adapter import Adapter
from retriever.flow.service import ServiceCall, parse_service_id
from retriever.rt.backend.interface import Executor
from retriever.rt.backend.dora.channel import DoraSubscriber, DoraPublisher
from retriever.rt.backend.dora.scheduler import DoraScheduler
from retriever.rt.backend.dora.serde import serialize_arrow, deserialize_arrow
from retriever.error import FlowError, RTError, ErrCode
from retriever.rt.lifecycle import instantiate_flow_from_node, initialize_flow_runtime
from retriever.rt.logging.worker import configure_worker
from retriever.rt.logging.handlers.otel import shutdown_otel

# Control system (optional)
try:
    from retriever.rt.control import Controllable, FlowState
    from retriever.rt.control.channel import ControlCommand, ControlResponse
    CONTROL_AVAILABLE = True
except ImportError:
    CONTROL_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)


class DoraExecutor(multiprocessing.Process, Executor):
    """
    Generator-driven executor for dora backend.

    Each executor runs one flow in isolation with its own:
    - Scheduler (determines when to execute)
    - Input channels (receives dora events)
    - Output channels (publishes via dora.Node)
    - Adapters (samples input data)
    """

    def __init__(
        self,
        node_id: str,
        clock: Clock,
        input_ports: Optional[List[str]] = None,
        output_ports: Optional[List[str]] = None,
        adapters: Optional[Dict[str, Adapter]] = None,
        flow: Optional[Flow] = None,
        flow_node: Optional[IRNode] = None,
        fan_in_map: Optional[Dict[str, str]] = None,
        buffer_engine: str = "python",
        log_params: Optional[Dict[str, Any]] = None,
        control_channel: Optional[Any] = None,
        control_command_queue: Optional[Any] = None,
        control_response_queue: Optional[Any] = None,
        control_log_queue: Optional[Any] = None,
    ):
        """
        Initialize DoraExecutor.

        Args:
            node_id: Unique node identifier
            clock: Clock for scheduling
            input_ports: List of logical input port names
            output_ports: List of output port names
            adapters: Dict mapping logical port names to Adapters
            flow: Optional pre-instantiated Flow (primarily for tests/compat)
            flow_node: Optional IR node spec for runtime-side instantiation
            fan_in_map: Dict mapping actual fan-in port names to logical port names
            log_params: Logging params (queue, config, log_dir)
            control_channel: Optional ControlChannel (deprecated, use queues instead)
            control_command_queue: Optional multiprocessing.Queue for commands
            control_response_queue: Optional multiprocessing.Queue for responses
            control_log_queue: Optional multiprocessing.Queue for flow log messages
        """
        super().__init__(name=node_id)
        self.node_id = node_id
        self.flow = flow
        self.flow_node = flow_node
        self.clock = clock
        self.input_ports = input_ports or []
        self.output_ports = output_ports or []
        self.adapters = adapters or {}
        self.fan_in_map = fan_in_map or {}
        self.buffer_engine = buffer_engine
        self.log_params = log_params

        # Store queue references (will create channel in run() after fork/spawn)
        self._control_command_queue = control_command_queue
        self._control_response_queue = control_response_queue
        self._control_log_queue = control_log_queue
        self._control_channel = control_channel  # May be set lazily in run() from queues

        self._is_controllable = False
        self._stop_flag = multiprocessing.Event()

        # Process-local resources (created in run())
        self.node: Optional[Any] = None
        self.inputs: Dict[str, DoraSubscriber] = {}
        self.outputs: Dict[str, List[DoraPublisher]] = {}
        self.scheduler: Optional[DoraScheduler] = None

        # Generator state for async service calls
        self._gen: Optional[Generator] = None
        self._srv_uuid: Optional[str] = None
        self._srv_deadline: float = 0

    @property
    def name(self) -> str:
        """Executor name/identifier."""
        return self.node_id

    def _ensure_runtime_flow_initialized(self) -> None:
        if self.flow is None:
            if self.flow_node is None:
                raise RuntimeError(
                    f"[{self.node_id}] No flow instance or flow node spec was provided"
                )
            self.flow = instantiate_flow_from_node(self.flow_node)

        if CONTROL_AVAILABLE:
            self._is_controllable = isinstance(self.flow, Controllable)
        else:
            self._is_controllable = False

        initialize_flow_runtime(self.flow)

    def _handle_control_messages(self) -> bool:
        """
        Check for and handle control messages (pause, resume, reset, etc.).

        Returns:
            False if executor should stop, True otherwise.
        """
        if not self._control_channel or not CONTROL_AVAILABLE:
            return True

        # Non-blocking check for commands
        message = self._control_channel.receive_command(timeout=0)
        if message is None:
            return True

        # Check if message is for this node or all nodes
        if message.target and message.target != self.node_id:
            return True

        # Handle command
        response = self._handle_control_command(message)
        self._control_channel.send_response(response)

        # STOP command returns False
        return message.command != ControlCommand.STOP

    def _handle_control_command(self, message) -> ControlResponse:
        """Handle a specific control command."""
        from retriever.rt.control.channel import ControlCommand

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

                # Clear adapters before resetting flow state
                self._reset_adapters()

                self.flow.reset()

                if was_running:
                    self.flow.resume()
            else:
                # Non-controllable flow: still reset adapters, then reset
                self._reset_adapters()

                if hasattr(self.flow, 'reset'):
                    self.flow.reset()

            return ControlResponse(
                request_id=message.request_id,
                node_id=self.node_id,
                success=True,
            )

        elif message.command == ControlCommand.GET_STATE:
            if self._is_controllable:
                status = self.flow.get_status(self.node_id)
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=True,
                    data=status.__dict__,
                )
            else:
                return ControlResponse(
                    request_id=message.request_id,
                    node_id=self.node_id,
                    success=False,
                    error="Flow is not controllable",
                )

        else:
            return ControlResponse(
                request_id=message.request_id,
                node_id=self.node_id,
                success=False,
                error=f"Unknown command: {message.command}",
            )

    def _should_execute_step(self) -> bool:
        """Check if step should proceed (respecting pause state)."""
        if self._is_controllable:
            return self.flow.control_pre_step()
        return True

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

    def run(self) -> None:
        """
        Main process loop.

        Lifecycle:
        1. Configure logging for this worker
        2. Create dora.Node(node_id)
        3. Initialize flow runtime (flow.reset())
        4. Create subscribers, publishers, scheduler
        5. Main event loop:
           - Route tick events to scheduler
           - Route data inputs to subscribers
           - Route service requests to handler dispatch
           - Route service responses to resume generator
           - Execute flow when triggered, drive generator if yielded
        6. Finalize flow (flow.finalize())
        7. Shutdown OTel
        """
        # Configure logging for this worker process
        if self.log_params:
            flow_type_name = (
                type(self.flow).__name__
                if self.flow is not None
                else (self.flow_node.type if self.flow_node is not None else "UnknownFlow")
            )
            configure_worker(
                self.node_id,
                flow_type_name,
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

        logger.info(f"[{self.node_id}] Starting DoraExecutor")

        # Initialize Rerun if configured (automatic connection)
        self._init_rerun()

        try:
            # Instantiate flow in runtime context and run lazy/init lifecycle.
            self._ensure_runtime_flow_initialized()
            logger.info(f"[{self.node_id}] Flow initialized")

            # Create dora node
            self.node = dora.Node(self.node_id)
            logger.info(f"[{self.node_id}] Created dora.Node")

            # Create input subscribers
            self.inputs = {
                port: DoraSubscriber(
                    buffer_size=self.adapters[port].buffer_size,
                    buffer_engine=self.buffer_engine,  # Tier B.3
                )
                for port in self.input_ports
            }

            # Create output publishers
            self.outputs = {
                port: [
                    DoraPublisher(
                        self._send_output,
                        port,
                        rerun_path=f"flows/{self.node_id}/output/{port}",
                    )
                ]
                for port in self.output_ports
            }

            # Create scheduler
            self.scheduler = DoraScheduler(self.clock)
            self.scheduler.reset()

            # Main event loop
            logger.info(f"[{self.node_id}] Entering event loop")

            while not self._stop_flag.is_set():
                # Check for control messages (non-blocking)
                if not self._handle_control_messages():
                    logger.info(f"[{self.node_id}] Stopping due to control command")
                    break

                event = self._next_event()

                if event is None:
                    self._check_service_timeout()
                    continue

                if event["type"] == "ERROR":
                    # Ignore timeout errors from dora
                    error_msg = event.get("error", "")
                    if "timed out" in error_msg:
                        continue

                    import sys
                    print(f"[{self.flow.name}] DoraExecutor error: {event}", file=sys.stderr)
                    break
                
                self._dispatch_event(event)

        except KeyboardInterrupt:
            logger.info(f"[{self.node_id}] Interrupted by user")

        except Exception as e:
            logger.error(
                f"[{self.node_id}] Fatal error in executor: {e}",
                exc_info=True
            )

        finally:
            if self._gen:
                self._gen.close()
            if self.flow is not None:
                self.flow.finalize()
            logger.info(f"[{self.node_id}] DoraExecutor terminated")
            # Flush OTel before exit only if it was enabled/configured for this worker.
            if self.log_params and getattr(self.log_params.get("config"), "otel_enabled", False):
                shutdown_otel()

    def _next_event(self) -> Optional[Dict[str, Any]]:
        """Get next event from dora node."""
        return self.node.next(timeout=1.0)

    def _dispatch_event(self, event: Dict[str, Any]) -> None:
        """Route event to appropriate handler."""
        event_type = event.get('type')

        if event_type == 'STOP':
            logger.info(f"[{self.node_id}] Received STOP signal")
            self._stop_flag.set()
            return

        if event_type != 'INPUT':
            logger.debug(f"[{self.node_id}] Skipped non-INPUT signal")
            return

        input_name = event.get('id', event.get('name'))
        
        if input_name is None:
            logger.warning(f"[{self.node_id}] Event missing 'id'/'name': {event.keys()}")
            return

        # Route service responses to resume generator
        if input_name.startswith('_response_in/'):
            self._handle_service_response(event)
            return

        # Route service requests to handler
        if input_name.startswith('_request_in/'):
            self._handle_service_request(event)
            return

        # Route tick events to scheduler
        if input_name == 'tick':
            self.scheduler.push_tick_event(event)
            target_port = None

        # Route fan-in inputs to logical port subscriber
        elif input_name in self.fan_in_map:
            target_port = self.fan_in_map[input_name]
            try:
                self.inputs[target_port].add_event(event)
            except Exception as e:
                logger.error(
                    f"[{self.node_id}] Failed to add fan-in event to '{target_port}': {e}",
                    exc_info=True
                )
                return

        # Route regular inputs to subscribers
        elif input_name in self.inputs:
            target_port = input_name
            try:
                self.inputs[input_name].add_event(event)
            except Exception as e:
                logger.error(
                    f"[{self.node_id}] Failed to add event to subscriber '{input_name}': {e}",
                    exc_info=True
                )
                return

        else:
            logger.warning(f"[{self.node_id}] Unknown input port: {input_name}")
            return

        # Check if should execute
        if self._gen is None: # Skip when waiting for service response
            result = self.scheduler.next(self.inputs)
            if result.should_execute:
                self._start_flow(result.fields_to_sample, now=result.now)

    def _start_flow(self, fields_to_sample: Optional[List[str]], *, now: Optional[float]) -> None:
        """Start flow execution, handle generator or direct return."""
        IOStep(
            self.inputs,
            fields_to_sample,
            output_types=self.flow.output_types,
            now=now,
        ) \
            .sample(self.flow.input_types, self.adapters, now=now) \
            .transform(self.flow.step) \
            .fold(on=self._start_generator) \
            .publish(self.outputs)

    def _start_generator(self, gen: Generator) -> None:
        """Start driving a generator from fold."""
        self._gen = gen
        self._drive_generator(None)

    def _drive_generator(self, value: Any) -> None:
        """Send value to generator, handle ServiceCall yield or StopIteration."""
        try:
            yielded = self._gen.send(value)

            if isinstance(yielded, ServiceCall):
                self._send_service_request(yielded)
            else:
                raise RTError(ErrCode.RT_INVALID_YIELD, f"got {type(yielded).__name__}")

        except StopIteration as e:
            IOStep(
                instance=e.value,
                output_types=self.flow.output_types,
                now=time.time(),
            ).publish(self.outputs)
            self._gen = None
            self._srv_uuid = None

        except Exception as e:
            logger.error(f"[{self.node_id}] Error in flow execution: {e}", exc_info=True)
            self._gen = None
            self._srv_uuid = None

    def _throw_to_generator(self, exc: Exception) -> None:
        """Throw exception into generator."""
        if self._gen is None:
            return

        try:
            self._gen.throw(exc)
        except StopIteration as e:
            IOStep(
                instance=e.value,
                output_types=self.flow.output_types,
                now=time.time(),
            ).publish(self.outputs)
        except Exception as e:
            logger.error(f"[{self.node_id}] Exception in generator: {e}", exc_info=True)
        finally:
            self._gen = None
            self._srv_uuid = None

    def _send_service_request(self, call: ServiceCall) -> None:
        """Send service request, set up response tracking."""
        self._srv_uuid = str(uuid.uuid4())
        self._srv_deadline = time.time() + call.timeout

        arrow, meta = serialize_arrow(call.request)
        meta['_srv_uuid'] = self._srv_uuid
        meta['_srv_id'] = call.service_method.descriptor.service_id

        self.node.send_output("_request_out", arrow, metadata=meta)
        logger.debug(f"[{self.node_id}] Sent service request: {meta['_srv_id']}")

    def _handle_service_response(self, event: Dict[str, Any]) -> None:
        """Handle service response, resume generator."""
        meta = event.get("metadata", {})
        srv_uuid = meta.get('_srv_uuid')

        if srv_uuid != self._srv_uuid:
            return

        if '_srv_error' in meta:
            self._throw_to_generator(FlowError(ErrCode.FLOW_SERVICE_ERROR, meta['_srv_error']))
        else:
            response = deserialize_arrow(event.get("value"), meta)
            self._drive_generator(response)

    def _handle_service_request(self, event: Dict[str, Any]) -> None:
        """Dispatch service request to handler method."""
        meta = event.get("metadata", {})
        srv_uuid = meta.get('_srv_uuid')
        srv_id = meta.get('_srv_id')

        try:
            request = deserialize_arrow(event.get("value"), meta)

            _, method_name = parse_service_id(srv_id)
            handler = getattr(self.flow, method_name, None)
            if not handler:
                raise FlowError(ErrCode.FLOW_SERVICE_NOT_FOUND, f"Handler not found: {method_name}")

            response = handler(request)
            arrow, resp_meta = serialize_arrow(response)
            resp_meta['_srv_uuid'] = srv_uuid
            resp_meta['_srv_id'] = srv_id
            self.node.send_output("_response_out", arrow, metadata=resp_meta)

        except Exception as e:
            logger.error(f"[{self.node_id}] Handler {srv_id} error: {e}")
            arrow, resp_meta = serialize_arrow(None)
            resp_meta['_srv_uuid'] = srv_uuid
            resp_meta['_srv_id'] = srv_id
            resp_meta['_srv_error'] = str(e)
            self.node.send_output("_response_out", arrow, metadata=resp_meta)

    def _check_service_timeout(self) -> None:
        """Check if pending service call has timed out."""
        if self._srv_uuid and time.time() > self._srv_deadline:
            self._throw_to_generator(FlowError(ErrCode.FLOW_SERVICE_TIMEOUT, "Service timeout"))

    def _send_output(self, port: str, arrow: Any, metadata: Dict[str, Any]) -> None:
        """Send output via dora node."""
        self.node.send_output(port, arrow, metadata=metadata)

    def stop(self) -> None:
        """Signal executor to stop gracefully."""
        self._stop_flag.set()

    # join() method inherited from multiprocessing.Process
    # is_alive() method inherited from multiprocessing.Process

    def _init_rerun(self) -> None:
        """Initialize Rerun if environment variable is set."""
        import os
        connect_addr = os.environ.get("RERUN_CONNECT_ADDR")
        app_id = os.environ.get("RERUN_APP_ID", "retriever_worker")
        
        if connect_addr:
            try:
                import rerun as rr
                from retriever.lib.rerun import _normalize_rerun_url
                rr.init(app_id)
                if hasattr(rr, "connect"):
                    rr.connect(connect_addr)
                elif hasattr(rr, "connect_grpc"):
                    try:
                        rr.connect_grpc(_normalize_rerun_url(connect_addr))
                    except Exception:
                        rr.connect_grpc()
                else:
                    raise AttributeError("rerun has no connect or connect_grpc")
                logger.info(f"[{self.node_id}] Connected to shared Rerun at {connect_addr} (App: {app_id})")
            except ImportError:
                logger.warning(f"[{self.node_id}] Rerun invalid: module 'rerun' not found")
            except Exception as e:
                logger.warning(f"[{self.node_id}] Failed to connect to Rerun at {connect_addr}: {e}")
