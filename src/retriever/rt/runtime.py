"""
Runtime - Entry point for running pipelines with backend selection.

Provides high-level API for executing pipelines using different backends.
"""

import logging
import uuid
from typing import Dict, Any, Union, Optional
from pathlib import Path

from retriever.ir.execution import ExecutionGraph
from retriever.ir import IR
from retriever.rt.backend.factory import get_backend
from retriever.rt.backend.interface import ExecutionEngine
from retriever.rt.logging import LogConfig
from retriever.rt.logging.manager import LogManager

logger = logging.getLogger('retriever')


def _extract_rerun_port(connect_addr: str, default_port: int = 9876) -> int:
    if not connect_addr:
        return default_port
    addr = connect_addr
    if "://" in addr:
        addr = addr.split("://", 1)[1]
    addr = addr.split("/", 1)[0]
    if ":" in addr:
        try:
            return int(addr.rsplit(":", 1)[1])
        except ValueError:
            return default_port
    return default_port


def execute_ir(
    ir: Union[IR, ExecutionGraph, str, Path],
    backend: str = 'multiprocessing',
    duration: Optional[float] = None,
    blocking: bool = True,
    log_config: Optional[LogConfig] = None,
    backend_config: Optional[Dict[str, Any]] = None,
) -> ExecutionEngine:
    """
    Execute pipeline from IR or IR file with backend selection.

    Args:
        ir: Either IR instance or path to IR JSON file
        backend: Backend name ('multiprocessing', 'dora', or 'in-process')
        duration: Optional duration in seconds (None = run indefinitely)
        blocking: If True, wait for completion/duration. If False, return immediately.
        log_config: Logging configuration (optional, uses defaults if None)
        backend_config: Backend-specific configuration (optional)

    Returns:
        ExecutionEngine instance (can be used to stop pipeline)

    Raises:
        FileNotFoundError: If IR file path does not exist
        ValueError: If IR validation fails or invalid JSON
        RTError: If backend errors occur

    Examples:
        # Execute from IRStruct
        execute_ir(ir, backend='multiprocessing', duration=10.0)

        # Execute from file path
        execute_ir('pipeline.json', backend='multiprocessing', duration=10.0)

        # Execute indefinitely (requires Ctrl+C to stop)
        execute_ir(ir, backend='multiprocessing')

        # Start and return (non-blocking)
        # WARNING: Must manually call engine.stop() to avoid orphaned processes
        engine = execute_ir(ir, backend='multiprocessing', blocking=False)
        time.sleep(5)
        engine.stop()
    """
    # Load IR from file if string/Path provided
    if isinstance(ir, (str, Path)):
        filepath = Path(ir)
        try:
            with open(filepath, 'r') as f:
                ir_struct = IR.from_json(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"IR file not found: {filepath}")
        except Exception as e:
            raise ValueError(f"Failed to load IR from {filepath}: {e}") from e
    elif isinstance(ir, ExecutionGraph):
        ir_struct = ir.ir  # Use the underlying IR
    else:
        ir_struct = ir

    in_process_only_nodes = [
        node.id for node in ir_struct.nodes if node.config.get("in_process_only")
    ]
    if in_process_only_nodes and backend != "in-process":
        raise ValueError(
            "This IR contains in-process-only flow wrappers and cannot run on "
            f"backend '{backend}'. Offending nodes: {in_process_only_nodes}"
        )

    if backend == "in-process" and not (backend_config or {}).get("pipeline_instance"):
        raise NotImplementedError(
            "The in-process backend requires a live Pipeline instance via "
            "backend_config['pipeline_instance']. Saved IR / IR-file execution is "
            "currently supported only on multiprocessing or dora."
        )

    # Initialize logging
    log_manager = LogManager()
    config = log_config or LogConfig()
    log_manager.init(config, ir_struct.metadata.name)

    logger.info(f"Executing pipeline: {ir_struct.metadata.name} (backend={backend})")

    # Handle Rerun
    rerun_process = None
    if backend_config and backend_config.get("rerun_config"):
        import rerun as rr
        import os

        # Use defaults if config is just True
        rr_config = backend_config["rerun_config"]
        if isinstance(rr_config, bool):
            rr_config = {"spawn": True}

        # In a real shared setup, we might want to start the Rerun server separately
        # or assume it's running via `rerun` config.
        # For now, we assume the user might have provided a connect addr or we use default.
        connect_addr = rr_config.get("connect_addr", "127.0.0.1:9876")
        
        # Inject into env_overrides
        if "env_overrides" not in backend_config:
            backend_config["env_overrides"] = {}
        
        backend_config["env_overrides"]["RERUN_CONNECT_ADDR"] = connect_addr
        backend_config["env_overrides"]["RERUN_APP_ID"] = ir_struct.metadata.name
        
        recording_id = (
            rr_config.get("recording_id")
            or os.environ.get("RERUN_RECORDING_ID")
            or str(uuid.uuid4())
        )

        # Also set in current process for main thread logic
        os.environ["RERUN_CONNECT_ADDR"] = connect_addr
        os.environ["RERUN_APP_ID"] = ir_struct.metadata.name
        os.environ["RERUN_RECORDING_ID"] = recording_id

        backend_config["env_overrides"]["RERUN_RECORDING_ID"] = recording_id

        # Start Rerun after env is set so SDK picks up the correct address.
        spawn_viewer = rr_config.get("spawn", True)
        rr.init(ir_struct.metadata.name, spawn=False, recording_id=recording_id)
        if spawn_viewer:
            port = _extract_rerun_port(connect_addr)
            rr.spawn(port=port, connect=True)
        else:
            try:
                from retriever.lib.rerun import _connect_rerun
                _connect_rerun(rr, connect_addr)
            except Exception as e:
                logger.warning(f"Failed to connect Rerun at {connect_addr}: {e}")
        logger.info(f"Rerun enabled: {connect_addr}")

    # Get backend factory
    factory_class = get_backend(backend)
    factory = factory_class()

    # Validate backend dependencies
    if not factory.validate_dependencies():
        raise ImportError(f"Backend '{backend}' dependencies not satisfied")

    # Create execution engine
    engine = factory.create_engine(ir_struct, backend_config)
    engine.build()
    engine.start()

    if not blocking:
        logger.warning("Non-blocking mode: engine.stop() must be called manually to cleanup")
        return engine

    try:
        if duration is not None:
            logger.info(f"Running for {duration} seconds")
            engine.wait(timeout=duration)
        else:
            logger.info("Running indefinitely (Ctrl+C to stop)")
            engine.wait()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger.info("Stopping pipeline")
        engine.stop()
        log_manager.shutdown()
        # Rerun shuts down automatically with process usually

    return engine
