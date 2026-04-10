
import time
import logging
from typing import Dict, Any, Optional

from retriever.rt.backend.interface import BackendFactory, ExecutionEngine
from retriever.rt.backend.factory import register_backend
from retriever.ir import IR
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
    
    def __init__(self, ir: IR, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.ir = ir
        self.config = config or {}
        self._pipeline: Optional[Pipeline] = None
        self._stepper = None
        self._running = False
        
        # Extract pipeline instance if provided (fast path)
        if config and "pipeline_instance" in config:
            self._pipeline = config["pipeline_instance"]
            
        if self._pipeline is None:
            raise ValueError(
                "The in-process backend is a live-Pipeline debug/recording surface. "
                "Pass backend_config['pipeline_instance'] or use Pipeline.step(), "
                "pipe.run(record=...), or execute the saved IR on multiprocessing or dora."
            )

        # Setup recording
        self._recorder = None
        self._recording_sink = None
        self._record_config: Optional[RecordConfig] = None
        self._rerun_manager = None
        self._pending_rerun_config = config.get("rerun_config") if config else None
        
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

        # Setup live Rerun when not also recording through the unified sink.
        if self._pending_rerun_config and not self._record_config:
            try:
                from retriever.lib.rerun import RerunManager, RerunConfig
                rr_cfg_data = self._pending_rerun_config
                if isinstance(rr_cfg_data, bool):
                     rr_cfg = RerunConfig(spawn=True)
                elif isinstance(rr_cfg_data, dict):
                     rr_cfg = RerunConfig(**rr_cfg_data)
                else:
                     rr_cfg = rr_cfg_data

                app_id = self.ir.metadata.name
                self._rerun_manager = RerunManager(rr_cfg, app_id=app_id)
                self._rerun_manager.init()
            except ImportError as e:
                logger.warning(f"Rerun logging enabled but failed to init: {e}")

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

        from retriever.recording import build_recording_sink

        self._recording_sink = build_recording_sink(
            self._record_config,
            app_id=self.ir.metadata.name,
        )
        self._recording_sink.open()

        if self._pending_rerun_config and self._rerun_manager is None:
            from retriever.lib.rerun import RerunManager, RerunConfig

            rr_cfg_data = self._pending_rerun_config
            if isinstance(rr_cfg_data, bool):
                rr_cfg = RerunConfig(spawn=True)
            elif isinstance(rr_cfg_data, dict):
                rr_cfg = RerunConfig(**rr_cfg_data)
            else:
                rr_cfg = rr_cfg_data
            self._rerun_manager = RerunManager(rr_cfg, app_id=self.ir.metadata.name)
            self._rerun_manager.init()

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
                if self._recording_sink:
                    self._recording_sink.write_step(result, step_idx)

                # Rerun
                if self._rerun_manager:
                    self._rerun_manager.log_step_result(result, step_idx)
                
                step_idx += 1
                
                # TODO: Sleep to match wall clock if desired? 
                # For now, run as fast as possible (simulation mode).
                
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self._recording_sink:
            self._recording_sink.close()
            self._recording_sink = None
            logger.info("Recording saved.")
             
        if self._rerun_manager:
            self._rerun_manager.cleanup()
            
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

    def create_engine(self, ir: IR, config: Optional[Dict[str, Any]] = None) -> ExecutionEngine:
        return InProcessEngine(ir, config)
