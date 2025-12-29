
import time
import logging
from typing import Dict, Any, Optional

from retriever.rt.backend.interface import BackendFactory, ExecutionEngine
from retriever.rt.backend.factory import register_backend
from retriever.ir.struct import IRStruct
from retriever.flow.pipeline import Pipeline
from retriever.config import RecordConfig, get_global_config

logger = logging.getLogger(__name__)

class InProcessEngine(ExecutionEngine):
    """
    Executes pipeline in the current process using PipelineStepper.
    
    This backend is ideal for:
    - Debugging (breakpoints work, single threaded)
    - Recording (deterministic execution)
    - Simulation (fast execution of logical steps)
    """
    
    def __init__(self, ir: IRStruct, config: Optional[Dict[str, Any]] = None):
        super().__init__(ir, config)
        self._pipeline: Optional[Pipeline] = None
        self._stepper = None
        self._running = False
        
        # Extract pipeline instance if provided (fast path)
        if config and "pipeline_instance" in config:
            self._pipeline = config["pipeline_instance"]
            
        if self._pipeline is None:
            # TODO: Implement hydration from IR for file-based execution
            raise NotImplementedError(
                "In-process backend currently requires a live Pipeline instance. "
                "Run via `pipe.run(backend='in-process')`."
            )

        # Setup recording
        self._recorder = None
        self._mcap_writer = None
        self._record_config: Optional[RecordConfig] = None
        
        # Check explicit config or global config
        if config and "record" in config:
            rc = config["record"]
            if isinstance(rc, str):
                self._record_config = RecordConfig(path=rc)
            elif isinstance(rc, RecordConfig):
                 self._record_config = rc
        else:
             # Fallback to global default
             glob = get_global_config()
             if glob.get("record"):
                 self._record_config = glob["record"]

    def build(self) -> None:
        """Prepare the stepper."""
        # PipelineStepper is created on demand in pipeline.step(), 
        # but we can initialize it explicitly if needed.
        pass

    def start(self) -> None:
        """
        Start execution. 
        For in-process, this signals readiness. 
        Actual loop happens in wait() to block main thread.
        """
        self._running = True
        logger.info("In-process engine ready. Call wait() to execute.")
        
        # Initialize recording if configured
        if self._record_config:
            self._init_recording()

    def _init_recording(self):
        path = self._record_config.path
        fmt = self._record_config.format
        
        logger.info(f"Recording execution to {path} (format={fmt})")
        
        if fmt == "mcap":
            from retriever.lib.mcap import MCAPWriter
            self._mcap_writer = MCAPWriter(path)
            self._mcap_writer.__enter__()
        else:
            # Legacy pickle/native recorder? 
            # Currently Pipeline.record logic for pickle is complex wrapper.
            # We'll stick to MCAP for unified run for now.
            logger.warning("Only MCAP format supported for unified run() recording.")

    def wait(self, timeout: Optional[float] = None) -> None:
        """
        Run the execution loop.
        
        Args:
            timeout: Duration to run in seconds. If None, runs indefinitely.
        """
        if not self._running:
            return

        logger.info("Starting in-process execution loop...")
        
        try:
            start_time = time.time()
            step_idx = 0
            
            # Use small dt for stepping if not specified? 
            # Pipeline.step(dt=None) uses sensible defaults or clock logic.
            # We'll pass dt=0.01 (100Hz) as default "tick" if not driven by inputs?
            # Or just let stepper handle it.
            
            # NOTE: Stepper executes 'one logical step'.
            
            while self._running:
                # Check timeout
                if timeout is not None:
                    if (time.time() - start_time) > timeout:
                        break
                
                # Execute step
                result = self._pipeline.step()
                
                # Record
                if self._mcap_writer:
                    self._mcap_writer.write_step(result, step_idx)
                
                step_idx += 1
                
                # TODO: Sleep to match wall clock if desired? 
                # For now, run as fast as possible (simulation mode).
                
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self._mcap_writer:
            self._mcap_writer.__exit__(None, None, None)
            self._mcap_writer = None
            logger.info("Recording saved.")
            
        if self._pipeline:
            self._pipeline.reset_stepper()

    @property
    def is_alive(self) -> bool:
        return self._running

@register_backend("in-process")
class InProcessBackendFactory(BackendFactory):
    @property
    def name(self) -> str:
        return "in-process"

    def validate_dependencies(self) -> bool:
        return True

    def create_engine(self, ir: IRStruct, config: Optional[Dict[str, Any]] = None) -> ExecutionEngine:
        return InProcessEngine(ir, config)
