"""
Runtime - Entry point for running pipelines with backend selection.

Provides high-level API for executing pipelines using different backends.
"""

import logging
from typing import Dict, Any, Union, Optional
from pathlib import Path

from retriever.ir.execution import ExecutionGraph
from retriever.ir.struct import IRStruct
from retriever.rt.backend.factory import get_backend
from retriever.rt.backend.interface import ExecutionEngine
from retriever.rt.logging import LogConfig
from retriever.rt.logging.manager import LogManager

logger = logging.getLogger('retriever')


def execute_ir(
    ir: Union[IRStruct, ExecutionGraph, str, Path],
    backend: str = 'multiprocessing',
    duration: Optional[float] = None,
    blocking: bool = True,
    log_config: Optional[LogConfig] = None,
    backend_config: Optional[Dict[str, Any]] = None,
) -> ExecutionEngine:
    """
    Execute pipeline from IR or IR file with backend selection.

    Args:
        ir: Either IRStruct instance or path to IR JSON file
        backend: Backend name ('multiprocessing' or 'dora')
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
        execute_ir('pipeline.json', backend='dora', duration=10.0)

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
                ir_struct = IRStruct.from_json(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"IR file not found: {filepath}")
        except Exception as e:
            raise ValueError(f"Failed to load IR from {filepath}: {e}") from e
    elif isinstance(ir, ExecutionGraph):
        ir_struct = ir.to_execution_ir()
    else:
        ir_struct = ir

    # Initialize logging
    log_manager = LogManager()
    config = log_config or LogConfig()
    log_manager.init(config, ir_struct.metadata.name)

    logger.info(f"Executing pipeline: {ir_struct.metadata.name} (backend={backend})")

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

    return engine
