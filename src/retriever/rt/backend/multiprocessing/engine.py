"""
MPEngine - Multiprocessing-based execution engine.

Orchestrates pipeline execution using Python's multiprocessing module.
"""

import time
import sys
from typing import Dict, List, Any, Optional
from multiprocessing import Queue
import multiprocessing

from retriever.ir.core import IR, IRNode, IREdge
from retriever.rt.backend.interface import ExecutionEngine
from retriever.rt.backend.multiprocessing.channel import MPChannel
from retriever.rt.backend.multiprocessing.executor import MPExecutor
from retriever.rt.logging.manager import LogManager

import logging
logger = logging.getLogger(__name__)

# Configure multiprocessing start method for compatibility
# Fork is faster and allows queue sharing; spawn requires full pickling
if sys.platform != 'win32':
    try:
        multiprocessing.set_start_method('fork', force=True)
    except RuntimeError:
        # Start method already set
        pass


class MPEngine(ExecutionEngine):
    """
    Multiprocessing-based execution engine.

    Creates MPChannel for each edge and MPExecutor for each node.

    Lifecycle:
    1. build(): Create channels and executors from IR
    2. start(): Start all executors
    3. wait(): Wait for execution (with optional timeout)
    4. stop(): Graceful shutdown
    """

    def __init__(self, ir: IR, config: Dict[str, Any] = None):
        """
        Initialize engine from IR.

        Args:
            ir: Validated IR
            config: Backend-specific configuration
        """
        self.ir = ir
        self.config = config or {}
        self.executors: List[MPExecutor] = []
        self.channels: Dict[str, MPChannel] = {}
        self._running = False

    def build(self):
        """
        Build runtime from IR.

        Creates MPChannel for each edge and MPExecutor for each node.
        """
        logger.info(f"Building multiprocessing runtime for '{self.ir.metadata.name}'")

        # Step 1: Create channels for each edge
        self._create_channels()

        # Step 2: Create executors for each node
        self._create_executors()

        logger.info(
            f"Runtime built: "
            f"{len(self.executors)} executors, "
            f"{len(self.channels)} channels"
        )

    def _create_channels(self):
        """Create MPChannel for each edge."""
        buffer_engine = self.config.get("buffer_engine", "python")
        for edge in self.ir.edges:
            queue = Queue(maxsize=edge.qsize)
            adapter = edge.instantiate_adapter()
            self.channels[edge.id] = MPChannel(
                queue,
                adapter.buffer_size,
                buffer_engine=buffer_engine,
                on_full=edge.on_full
            )
            logger.debug(f"Created channel {edge.id} "
                         f"(queue_size={edge.qsize}, buffer_size={adapter.buffer_size})")

    def _create_executors(self):
        """Create MPExecutor for each node."""
        for node in self.ir.nodes:
            # Load clock from config
            clock = IRNode.instantiate_clock(node.config)

            # Build input channels mapping
            inputs = {}
            adapters = {}

            for edge in self.ir.edges:
                if edge.destination.node == node.id:
                    actual_port = edge.destination.port
                    logical_port = IR.get_logical_port(actual_port)

                    if IR.is_fan_in_port(actual_port):
                        # Fan-in: one channel with multiple queues
                        if logical_port in inputs:
                            inputs[logical_port].add_queue(self.channels[edge.id].queue)
                        else:
                            inputs[logical_port] = self.channels[edge.id]
                    else:
                        inputs[logical_port] = self.channels[edge.id]

                    # Load adapter once per logical port (fan-in edges have same adapter)
                    if logical_port not in adapters:
                        adapter = edge.instantiate_adapter()
                        adapters[logical_port] = adapter

            # Build output channels mapping
            outputs = {}

            for edge in self.ir.edges:
                if edge.source.node == node.id:
                    port_name = edge.source.port

                    # Support broadcasting
                    if port_name not in outputs:
                        outputs[port_name] = []
                    outputs[port_name].append(self.channels[edge.id])

            # Create executor with logging params
            log_params = None
            if LogManager.is_initialized():
                log_manager = LogManager()
                log_params = {
                    'queue': log_manager.get_queue(),
                    'config': log_manager.get_config(),
                    'log_dir': log_manager.get_log_dir(),
                }

            # Extract control queue references (not the channel object itself)
            # Queues must be inherited, not pickled
            control_cmd_queue = None
            control_resp_queue = None
            control_log_queue = None
            if "control_channel" in self.config:
                ctrl_chan = self.config["control_channel"]
                if hasattr(ctrl_chan, 'register_node'):
                    # Per-node queue channel: register this node and get its queue
                    ctrl_chan.register_node(node.id)
                    control_cmd_queue = ctrl_chan.get_node_command_queue(node.id)
                    control_resp_queue = ctrl_chan.response_queue
                    if hasattr(ctrl_chan, "log_queue"):
                        control_log_queue = ctrl_chan.log_queue
                elif hasattr(ctrl_chan, 'command_queue') and hasattr(ctrl_chan, 'response_queue'):
                    # Legacy shared queue channel
                    control_cmd_queue = ctrl_chan.command_queue
                    control_resp_queue = ctrl_chan.response_queue
                    if hasattr(ctrl_chan, "log_queue"):
                        control_log_queue = ctrl_chan.log_queue

            executor = MPExecutor(
                node_id=node.id,
                flow_node=node,
                clock=clock,
                inputs=inputs,
                outputs=outputs,
                adapters=adapters,
                log_params=log_params,
                control_command_queue=control_cmd_queue,
                control_response_queue=control_resp_queue,
                control_log_queue=control_log_queue,
            )

            self.executors.append(executor)
            logger.debug(f"Created executor for {node.id}")

    def start(self):
        """Start all executors."""
        if self._running:
            logger.warning("Engine already running")
            return

        logger.info("Starting all executors")

        for executor in self.executors:
            executor.start()
            logger.info(f"Started executor: {executor.name} (PID: {executor.pid})")

        self._running = True

    def stop(self):
        """Stop all executors gracefully."""
        if not self._running:
            return

        logger.info("Stopping all executors")

        # Signal all executors to stop
        for executor in self.executors:
            if executor.is_alive():
                executor.stop()

        # Wait for executors to terminate
        for executor in self.executors:
            executor.join(timeout=5.0)
            if executor.is_alive():
                logger.warning(f"Force terminating executor: {executor.name}")
                executor.terminate()
                executor.join()

        self._running = False
        logger.info("All executors stopped")

    def wait(self, timeout: Optional[float] = None) -> None:
        """
        Wait while executors are running.

        Blocks until all executors finish or timeout is reached.

        Args:
            timeout: Optional timeout in seconds
        """
        if not self._running:
            logger.warning("Engine not running")
            return

        logger.info("Waiting for execution")

        start_time = time.time()

        while self.is_alive():
            if timeout and (time.time() - start_time) >= timeout:
                logger.warning("Wait timeout reached")
                return
            time.sleep(0.1)

    def is_alive(self) -> bool:
        """Check if any executor is still alive."""
        return any(e.is_alive() for e in self.executors)
