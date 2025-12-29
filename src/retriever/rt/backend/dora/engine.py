"""
DoraEngine - Dora-based execution engine.

Orchestrates dora dataflow lifecycle:
1. Generate YAML from IR
2. Start dora coordinator and dataflow
3. Spawn DoraExecutor processes
4. Manage shutdown
"""

import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from retriever.ir.loader import IRLoader
from retriever.ir.struct import IRStruct
from retriever.ir.loader import IRLoader
from retriever.ir.fanin import is_fan_in_port, get_logical_port
from retriever.rt.backend.dora.compiler import compile_and_validate, get_node_paths
from retriever.rt.backend.dora.executor import DoraExecutor
from retriever.rt.backend.interface import ExecutionEngine
from retriever.rt.logging.manager import LogManager

logger = logging.getLogger(__name__)


class DoraEngine(ExecutionEngine):
    """
    Dora-based execution engine.

    Generates dora YAML from IR and manages dataflow lifecycle.

    Lifecycle:
    1. build(): Generate YAML and create executors
    2. start(): Start dora dataflow and spawn executor processes
    3. wait(): Wait for execution (with optional timeout)
    4. stop(): Graceful shutdown
    """

    def __init__(self, ir: IRStruct, config: Dict[str, Any] = None):
        """
        Initialize engine from IR.

        Args:
            ir: Validated IRStruct
            config: Backend-specific configuration:
                - 'keep_yaml': Don't delete YAML after stop (default: False)
                - 'yaml_dir': Custom directory for YAML (default: tempdir)
                - 'dora_timeout': Timeout for dora commands (default: 10s)
                - 'dora_destroy': Destroy dora runtime on stop (default: False)
                - 'init_delay': Delay after dora start (default: 1.0s)
                - 'buffer_engine': Buffer engine kind for per-port sampling ('python' | 'native', default: 'python')
        """
        self.ir = ir
        self.config = config or {}
        self.executors: List[DoraExecutor] = []
        self.main_thread_runners: List = []  # For @gui_flow nodes
        self._main_thread_nodes: List = []  # Node IDs that are main-thread
        self._running = False
        self._temp_dir: Optional[Path] = None
        self._yaml_path: Optional[Path] = None
        self._dora_started = False

    def build(self) -> None:
        """
        Build runtime from IR.

        Validates dora availability, generates YAML, and creates executors.
        """
        logger.info(f"Building dora runtime for '{self.ir.metadata.name}'")

        # # Validate dora is available
        # if not validate_dora_available():
        #     raise ImportError(
        #         "Dora backend requires 'dora-rs' and 'pyarrow'. "
        #         "Install with: pip install dora-rs pyarrow"
        #     )

        # Create temp directory for YAML
        yaml_dir = self.config.get("yaml_dir")
        if yaml_dir:
            self._temp_dir = Path(yaml_dir)
            self._temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="dora_retriever_"))

        logger.debug(f"YAML directory: {self._temp_dir}")

        # Resolve optional native node overrides (Tier A.1)
        node_path_overrides = None
        if "native_overrides" in self.config:
            node_path_overrides = self.config.get("native_overrides")

        # Resolve deployment overrides (Tier A.2)
        deployment_overrides = None
        if "deployment_overrides" in self.config:
            deployment_overrides = self.config.get("deployment_overrides")


        # Compile IR to YAML (with optional per-node path overrides)
        try:
            yaml_content = compile_and_validate(
                self.ir, 
                node_path_overrides=node_path_overrides,
                deployment_overrides=deployment_overrides
            )

            logger.debug(f"Generated YAML:\n{yaml_content}")
        except Exception as e:
            logger.error(f"YAML compilation failed: {e}")
            raise ValueError(f"Failed to compile dora YAML: {e}") from e

        yaml_filename = f"{self.ir.metadata.name}.yaml"
        self._yaml_path = self._temp_dir / yaml_filename
        self._yaml_path.write_text(yaml_content)
        logger.info(f"Generated YAML: {self._yaml_path}")

        # Record node paths so we can decide which nodes are Python vs native.
        self._node_paths = get_node_paths(
            self.ir, node_path_overrides=node_path_overrides
        )

        # Create Python executors only for "dynamic" nodes.
        # Partition into main-thread (run inline) and worker (spawn subprocess).
        for node in self.ir.nodes:
            path = self._node_paths.get(node.id, "dynamic")
            if path != "dynamic":
                logger.info(
                    f"Skipping Python executor for native node: {node.id} (path={path})"
                )
                continue
            executor = self._create_executor(node)

            # Check if flow is marked as main-thread (@gui_flow)
            if getattr(executor.flow, "_main_thread", False):
                self.main_thread_runners.append(executor)
                self._main_thread_nodes.append(node.id)
                logger.info(f"Main-thread flow detected: {node.id}")
            else:
                self.executors.append(executor)

        logger.info(
            f"Runtime built: {len(self.executors)} worker executors, {len(self.main_thread_runners)} main-thread executors"
        )

    def _create_executor(self, node) -> DoraExecutor:
        """Create DoraExecutor for each node."""
        # Load flow instance
        flow = IRLoader.load_flow(node)

        # Load clock from config
        clock = IRLoader.load_clock(node.config)

        # Get data port names (filter out service ports)
        from retriever.flow.service import is_service_port

        output_ports = [p for p in node.outputs.keys() if not is_service_port(p)]

        # Load adapters and build fan-in mapping
        # For fan-in ports (_fanin/source/logical), we:
        # - Map actual_port -> logical_port for event routing
        # - Use logical_port for subscriber creation and adapter lookup
        adapters = {}
        fan_in_map = {}  # actual_port -> logical_port
        logical_ports = set()

        for edge in self.ir.get_incoming_edges(node.id):
            actual_port = edge.destination.port
            if is_service_port(actual_port):
                continue

            logical_port = get_logical_port(actual_port)

            if is_fan_in_port(actual_port):
                # Fan-in port: map actual -> logical for event routing
                fan_in_map[actual_port] = logical_port

            logical_ports.add(logical_port)
            # Only load adapter once per logical port (all fan-in edges have same adapter)
            if logical_port not in adapters:
                adapter = IRLoader.load_adapter(edge.adapter)
                adapters[logical_port] = adapter

        input_ports = list(logical_ports)

        # Warn about unconnected ports from node.inputs
        declared_ports = [p for p in node.inputs.keys() if not is_service_port(p) and not is_fan_in_port(p)]
        for p in declared_ports:
            if p not in adapters:
                logger.warning(
                    f"Node '{node.id}' has unconnected input port: '{p}'. It will not receive data."
                )

        # Create executor with logging params
        log_params = None
        if LogManager.is_initialized():
            log_manager = LogManager()
            log_params = {
                "queue": log_manager.get_queue(),
                "config": log_manager.get_config(),
                "log_dir": log_manager.get_log_dir(),
            }

        executor = DoraExecutor(
            node_id=node.id,
            flow=flow,
            clock=clock,
            input_ports=input_ports,
            output_ports=output_ports,
            adapters=adapters,
            fan_in_map=fan_in_map,
            buffer_engine=self.config.get("buffer_engine", "python"),
            log_params=log_params,
        )

        logger.debug(f"Created executor for {node.id}")
        return executor

    def start(self) -> None:
        """Start dora dataflow and all executors."""
        if self._running:
            logger.warning("Engine already running")
            return

        logger.info("Starting dora runtime")

        timeout = self.config.get("dora_timeout", 10)

        # Start dora runtime
        self._start_dora_runtime(timeout)

        # Start dataflow
        self._start_dataflow(timeout)

        # Give dora time to initialize nodes
        init_delay = self.config.get("init_delay", 1.0)
        logger.debug(f"Waiting {init_delay}s for dora initialization")
        time.sleep(init_delay)

        # Start all worker executors (as subprocesses)
        for executor in self.executors:
            executor.start()
            logger.info(f"Started executor: {executor.name} (PID: {executor.pid})")

        self._running = True

        # Run main-thread executors inline (blocking)
        # This keeps them in the main process for GUI frameworks
        if self.main_thread_runners:
            logger.info(
                f"Running {len(self.main_thread_runners)} main-thread executor(s) inline"
            )
            for runner in self.main_thread_runners:
                # Run in main thread (blocking) - uses dora.Node for communication
                print(f"[MAIN] Starting @gui_flow: {runner.name}")
                logger.info(f"Starting main-thread executor: {runner.name}")
                runner.run()  # This blocks until executor stops

    def _start_dora_runtime(self, timeout: float) -> None:
        """Start dora runtime with 'dora up'."""
        logger.debug("Starting dora runtime")

        try:
            result = subprocess.run(
                ["dora", "up"], capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                logger.info("Dora runtime started")
            else:
                # Runtime may already be running
                logger.warning(
                    f"dora up returned {result.returncode} "
                    f"(may already be running): {result.stderr}"
                )

        # except FileNotFoundError:
        #     raise FileNotFoundError(
        #         "dora CLI not found. Ensure dora-rs-cli is installed: "
        #         "pip install dora-rs-cli"
        #     )

        except subprocess.TimeoutExpired:
            logger.warning(f"dora up timed out after {timeout}s")

    def _start_dataflow(self, timeout: float) -> None:
        """Start dataflow with 'dora start <yaml> --detach'."""
        logger.debug(f"Starting dataflow: {self._yaml_path}")

        try:
            result = subprocess.run(
                ["dora", "start", str(self._yaml_path), "--detach"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._temp_dir,
            )

            if result.returncode != 0:
                err = result.stderr.strip()
                # Friendly guidance for older dora CLI that lacks dynamic nodes
                if "unknown variant `dynamic`" in err:
                    raise RuntimeError(
                        "dora CLI rejected the generated dataflow YAML (unknown variant `dynamic`). "
                        "This usually means your installed `dora` CLI does not support Retriever's "
                        "current dataflow schema. Install a newer dora CLI (latest release or build "
                        "from source), then retry.\n"
                        f"stderr: {err}"
                    )

                raise RuntimeError(
                    f"dora start failed (exit code {result.returncode}):\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )

            self._dora_started = True
            logger.info(f"Dataflow started: {self.ir.metadata.name}")
            logger.debug(f"dora start output: {result.stdout}")

        # except FileNotFoundError:
        #     raise FileNotFoundError(
        #         "dora CLI not found. Ensure dora-rs-cli is installed."
        #     )

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"dora start timed out after {timeout}s")

    def stop(self) -> None:
        """Stop all executors and dora dataflow gracefully."""
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

        # Stop dataflow
        if self._dora_started:
            self._stop_dataflow()

        # Destroy dora runtime (optional, disabled by default)
        if self.config.get("dora_destroy", False):
            self._destroy_dora_runtime()

        # Cleanup temp files
        if not self.config.get("keep_yaml", False):
            self._cleanup_temp_files()

    def _stop_dataflow(self) -> None:
        """Stop dora dataflow with 'dora stop --name <dataflow>'."""
        logger.debug(f"Stopping dataflow: {self.ir.metadata.name}")

        timeout = self.config.get("dora_timeout", 10)

        try:
            result = subprocess.run(
                ["dora", "stop", "--name", self.ir.metadata.name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                logger.info("Dataflow stopped")
            elif "no dataflow with name" in result.stderr:
                logger.debug(f"Dataflow already stopped: {self.ir.metadata.name}")
            else:
                logger.warning(
                    f"dora stop returned {result.returncode}: {result.stderr}"
                )

        except Exception as e:
            logger.warning(f"Failed to stop dataflow: {e}")

    def _destroy_dora_runtime(self) -> None:
        """Destroy dora runtime with 'dora destroy'."""
        logger.debug("Destroying dora runtime")

        timeout = self.config.get("dora_timeout", 10)

        try:
            result = subprocess.run(
                ["dora", "destroy"], capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                logger.info("Dora runtime destroyed")
            else:
                logger.warning(
                    f"dora destroy returned {result.returncode}: {result.stderr}"
                )

        except Exception as e:
            logger.warning(f"Failed to destroy dora runtime: {e}")

    def _cleanup_temp_files(self) -> None:
        """Remove temporary directory and YAML file."""
        if self._temp_dir and self._temp_dir.exists():
            logger.debug(f"Cleaning up temp directory: {self._temp_dir}")

            try:
                import shutil

                shutil.rmtree(self._temp_dir, ignore_errors=True)
                logger.debug("Temp files cleaned up")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")

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

    def get_yaml_path(self) -> Optional[Path]:
        """Get path to generated YAML file."""
        return self._yaml_path
