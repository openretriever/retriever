"""
Rerun integration for Retriever pipelines.

This module provides utilities for visualizing and debugging retriever pipelines
using Rerun (https://rerun.io). It supports:

- Automatic visualization of RerunLoggable types
- Recording sessions for later replay
- Integration with Pipeline.step() for debugging
- Timestamp jumping for inspecting specific moments

Usage:
    from retriever.lib.rerun import (
        RerunConfig,
        enable_rerun_logging,
        record_session,
    )

    # Enable logging for a pipeline
    p = Pipeline("my_pipeline")
    enable_rerun_logging(p, config=RerunConfig(spawn=True))

    # Record a debugging session
    with record_session(stepper, "debug.rrd"):
        for _ in range(100):
            stepper.step()
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Dict,
    Literal,
    Optional,
    Protocol,
    runtime_checkable,
)

# Lazy import rerun to keep it optional
rr = None


def _ensure_rerun():
    """Lazily import rerun-sdk"""
    global rr
    if rr is None:
        try:
            import rerun as _rr

            rr = _rr
        except ImportError:
            raise ImportError(
                "rerun-sdk not installed. Install with: pip install rerun-sdk"
            ) from None
    return rr


# =============================================================================
# Protocol for Loggable Types
# =============================================================================


@runtime_checkable
class RerunLoggable(Protocol):
    """
    Protocol for types that can log themselves to Rerun.

    Implement this in your data types to enable automatic visualization:

        @dataclass
        class MyDetection(RerunLoggable):
            boxes: np.ndarray

            def log_to_rerun(self, path: str) -> None:
                import rerun as rr
                rr.log(f"{path}/boxes", rr.Boxes2D(self.boxes))
    """

    def log_to_rerun(self, path: str) -> None:
        """Log this value at the given Rerun entity path"""
        ...


def rerun_loggable(field_loggers: Dict[str, str] = None):
    """
    Decorator to make a @flow_io dataclass automatically log to Rerun.

    Works with multi-port @flow_io types by logging each field separately.

    Args:
        field_loggers: Optional mapping of field_name -> rerun_archetype.
                       Supported: "Image", "Scalar", "Text", "Tensor", "Boxes2D"
                       If not specified, auto-detects based on type hints.

    Usage:
        @rerun_loggable({"image": "Image", "reward": "Scalar"})
        @flow_io
        @dataclass
        class MyOutput:
            image: np.ndarray
            reward: float
            labels: List[str]  # Auto-detects as Text

    For multi-port flows, each field is logged at:
        {base_path}/{field_name}
    """

    def decorator(cls):
        field_loggers_dict = field_loggers or {}

        def log_to_rerun(self, path: str) -> None:
            rr = _ensure_rerun()

            for field_name in self.__dataclass_fields__:
                value = getattr(self, field_name, None)
                if value is None:
                    continue

                field_path = f"{path}/{field_name}"

                # Check explicit mapping first
                if field_name in field_loggers_dict:
                    archetype = field_loggers_dict[field_name]
                    _log_with_archetype(rr, field_path, value, archetype)
                else:
                    # Auto-detect based on value type
                    _log_auto_detect(rr, field_path, value)

        cls.log_to_rerun = log_to_rerun
        return cls

    return decorator


def _log_with_archetype(rr, path: str, value: Any, archetype: str) -> None:
    """Log value with specified Rerun archetype."""
    if archetype == "Image":
        rr.log(path, rr.Image(value))
    elif archetype == "Scalar":
        from rerun.archetypes import Scalars
        rr.log(path, Scalars(value))
    elif archetype == "TimeSeries":
        # Log list of values as individual scalar time-series
        import numpy as np
        from rerun.archetypes import Scalars
        if isinstance(value, (list, tuple, np.ndarray)):
            for i, val in enumerate(value):
                rr.log(f"{path}/{i}", Scalars(val))
    elif archetype == "Text":
        rr.log(path, rr.TextLog(str(value)))
    elif archetype == "Tensor":
        rr.log(path, rr.Tensor(value))
    elif archetype == "Boxes2D":
        rr.log(path, rr.Boxes2D(value))
    elif archetype == "Points2D":
        rr.log(path, rr.Points2D(value))
    elif archetype == "BarChart":
        rr.log(path, rr.BarChart(value))
    else:
        # Fallback to auto-detect
        _log_auto_detect(rr, path, value)


def _log_auto_detect(rr, path: str, value: Any) -> None:
    """Auto-detect value type and log appropriately."""
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            if value.ndim == 3 and value.shape[2] in (3, 4):  # HWC image
                rr.log(path, rr.Image(value))
            elif value.ndim == 2 and value.shape[0] > 10 and value.shape[1] > 10:
                rr.log(path, rr.Image(value))
            else:
                rr.log(path, rr.Tensor(value))
            return
    except ImportError:
        pass

    if isinstance(value, (int, float)):
        from rerun.archetypes import Scalars
        rr.log(path, Scalars(value))
    elif isinstance(value, str):
        rr.log(path, rr.TextLog(value))
    elif isinstance(value, (list, tuple)):
        if len(value) > 0 and all(isinstance(x, (int, float)) for x in value):
            rr.log(path, rr.BarChart(value))
        else:
            rr.log(path, rr.TextLog(str(value)))


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class RerunConfig:
    """Configuration for Rerun integration."""

    enabled: bool = True
    """Whether Rerun logging is enabled."""

    mode: Literal["spawn", "connect", "record"] = "spawn"
    """
    - spawn: Start a new Rerun viewer (default)
    - connect: Connect to an existing viewer at `address`
    - record: Save to .rrd file without opening viewer
    """

    address: str = "127.0.0.1:9876"
    """Address for connecting to existing viewer (mode='connect')."""

    recording_path: Optional[str] = None
    """Path to save .rrd recording (mode='record' or auto-saved on exit)."""

    app_id: Optional[str] = None
    """Application ID for Rerun. Defaults to pipeline name."""

    auto_open_on_exit: bool = True
    """Automatically open Rerun viewer when recording ends."""

    log_inputs: bool = True
    """Log flow inputs (memory intensive, disable for large data)."""

    log_outputs: bool = True
    """Log flow outputs."""


# =============================================================================
# Rerun Manager
# =============================================================================


class RerunManager:
    """
    Manages Rerun lifecycle for a pipeline.

    Handles initialization, logging, and cleanup across processes.
    """

    def __init__(self, config: RerunConfig, app_id: str = "retriever"):
        self.config = config
        self.app_id = config.app_id or app_id
        self._initialized = False
        self._recording_path: Optional[Path] = None
        self._step_count = 0

    def init(self) -> None:
        """Initialize Rerun in the current process."""
        if not self.config.enabled or self._initialized:
            return

        rr = _ensure_rerun()

        if self.config.mode == "spawn":
            rr.init(self.app_id, spawn=True)
        elif self.config.mode == "connect":
            rr.init(self.app_id)
            rr.connect(self.config.address)
        elif self.config.mode == "record":
            if self.config.recording_path:
                self._recording_path = Path(self.config.recording_path)
                rr.init(self.app_id)
                rr.save(str(self._recording_path))
            else:
                raise ValueError("recording_path required for mode='record'")

        self._initialized = True

    def init_worker(self) -> None:
        """Initialize Rerun in a worker process (connects to main viewer)."""
        if not self.config.enabled:
            return

        rr = _ensure_rerun()
        rr.init(self.app_id)
        rr.connect(self.config.address)

    def log(self, path: str, value: Any, time_seconds: Optional[float] = None) -> None:
        """
        Log a value to Rerun.

        If value implements RerunLoggable, calls value.log_to_rerun().
        Otherwise attempts auto-detection for common types.
        """
        if not self.config.enabled or not self._initialized:
            return

        rr = _ensure_rerun()

        if time_seconds is not None:
            rr.set_time_seconds("retriever_time", time_seconds)

        # Use protocol if available
        if isinstance(value, RerunLoggable):
            value.log_to_rerun(path)
            return

        # Fallback: try common types
        self._log_auto(path, value)

    def _log_auto(self, path: str, value: Any) -> None:
        """Auto-detect and log common types."""
        rr = _ensure_rerun()

        # numpy array -> Image or Tensor
        try:
            import numpy as np

            if isinstance(value, np.ndarray):
                if value.ndim == 3 and value.shape[2] in (3, 4):  # HWC image
                    rr.log(path, rr.Image(value))
                elif (
                    value.ndim == 2 and value.shape[0] > 10 and value.shape[1] > 10
                ):  # Likely image
                    rr.log(path, rr.Image(value))
                else:
                    rr.log(path, rr.Tensor(value))
                return
        except ImportError:
            pass

        # Scalar types
        if isinstance(value, (int, float)):
            rr.log(path, rr.Scalar(value))
            return

        # String -> TextLog
        if isinstance(value, str):
            rr.log(path, rr.TextLog(value))
            return

        # List of scalars -> bar chart or time series
        if isinstance(value, (list, tuple)) and len(value) > 0:
            if all(isinstance(x, (int, float)) for x in value):
                rr.log(path, rr.BarChart(value))
                return

        # Dict -> log each key
        if isinstance(value, dict):
            for k, v in value.items():
                self._log_auto(f"{path}/{k}", v)
            return

    def log_step_result(self, result: Any, step_idx: int) -> None:
        """
        Log a StepResult from Pipeline.step().

        Args:
            result: StepResult from stepper.step()
            step_idx: Step index for timeline
        """
        if not self.config.enabled or not self._initialized:
            return

        rr = _ensure_rerun()

        # Set time for this step
        rr.set_time_sequence("step", step_idx)
        if hasattr(result, "now") and result.now is not None:
            rr.set_time_seconds("retriever_time", result.now)

        # Log executed flows
        if hasattr(result, "executed") and result.executed:
            rr.log("step/executed", rr.TextLog(", ".join(result.executed)))

        # Log inputs
        if self.config.log_inputs and hasattr(result, "inputs"):
            for node_id, value in result.inputs.items():
                self.log(f"flows/{node_id}/input", value)

        # Log outputs
        if self.config.log_outputs and hasattr(result, "outputs"):
            for node_id, value in result.outputs.items():
                self.log(f"flows/{node_id}/output", value)

        self._step_count += 1

    def set_time(self, time_seconds: float, step: Optional[int] = None) -> None:
        """Set the current time for subsequent logs."""
        if not self.config.enabled or not self._initialized:
            return

        rr = _ensure_rerun()
        rr.set_time_seconds("retriever_time", time_seconds)
        if step is not None:
            rr.set_time_sequence("step", step)

    def cleanup(self, open_recording: bool = True) -> None:
        """
        Cleanup and optionally open recording.

        Args:
            open_recording: If True and mode='record', opens the .rrd file
        """
        if not self._initialized:
            return

        if (
            self.config.mode == "record"
            and self._recording_path
            and open_recording
            and self.config.auto_open_on_exit
        ):
            self._open_rrd(self._recording_path)

    def _open_rrd(self, path: Path) -> None:
        """Open an .rrd file in the Rerun viewer."""
        try:
            subprocess.Popen(["rerun", str(path)])
        except FileNotFoundError:
            print(f"[Rerun] Recording saved to: {path}")
            print("[Rerun] Install rerun CLI to auto-open: pip install rerun-sdk[cli]")

    @staticmethod
    def cleanup_cache() -> None:
        """Remove Rerun cache (platform-aware)."""
        system = platform.system()
        if system == "Darwin":  # macOS
            cache_path = Path.home() / "Library/Application Support/rerun"
        else:  # Linux
            cache_path = Path.home() / ".cache/rerun"

        if cache_path.exists():
            print(f"[Rerun] Clearing cache at {cache_path}")
            for item in cache_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()


# =============================================================================
# High-Level API
# =============================================================================


def enable_rerun_logging(
    pipeline_or_stepper: Any,
    config: Optional[RerunConfig] = None,
) -> RerunManager:
    """
    Enable Rerun logging for a pipeline or stepper.

    Args:
        pipeline_or_stepper: Pipeline or PipelineStepper instance
        config: Rerun configuration (defaults to spawn mode)

    Returns:
        RerunManager instance for manual control
    """
    config = config or RerunConfig()

    # Get name from pipeline
    name = getattr(pipeline_or_stepper, "name", "retriever")
    if hasattr(pipeline_or_stepper, "_pipeline"):
        name = pipeline_or_stepper._pipeline.name

    manager = RerunManager(config, app_id=name)
    manager.init()

    return manager


@contextmanager
def record_session(
    stepper: Any,
    rrd_path: str = "session.rrd",
    inputs_path: Optional[str] = None,
    auto_open: bool = True,
):
    """
    Context manager for recording a debugging session.

    Records all step() calls to an .rrd file for later replay.
    Optionally saves raw inputs for re-execution.

    Args:
        stepper: PipelineStepper instance
        rrd_path: Path to save Rerun recording
        inputs_path: Optional path to save inputs for replay
        auto_open: Open Rerun viewer when done

    Usage:
        with record_session(stepper, "debug.rrd"):
            for _ in range(100):
                stepper.step()
        # Viewer opens automatically with recording
    """
    import pickle

    # Setup recording
    config = RerunConfig(
        mode="record",
        recording_path=rrd_path,
        auto_open_on_exit=auto_open,
    )

    # Get pipeline name
    if hasattr(stepper, "_ctx"):  # Pipeline object
        name = stepper._ctx._name
    elif hasattr(stepper, "name"):
        name = stepper.name
    else:
        name = "debug"
    manager = RerunManager(config, app_id=name)
    manager.init()

    # Wrap stepper.step to auto-log
    original_step = stepper.step
    step_count = 0
    inputs_log = [] if inputs_path else None

    def wrapped_step(*args, **kwargs):
        nonlocal step_count
        result = original_step(*args, **kwargs)
        manager.log_step_result(result, step_count)

        if inputs_log is not None and hasattr(result, "inputs"):
            inputs_log.append((step_count, result.inputs))

        step_count += 1
        return result

    stepper.step = wrapped_step

    try:
        yield manager
    finally:
        stepper.step = original_step

        # Save inputs if requested
        if inputs_path and inputs_log:
            with open(inputs_path, "wb") as f:
                pickle.dump(inputs_log, f)
            print(f"[Rerun] Saved inputs to: {inputs_path}")

        manager.cleanup()
        print(f"[Rerun] Recording saved to: {rrd_path}")


def jump_to_step(step: int) -> None:
    """
    Jump Rerun viewer to a specific step.

    Note: This requires Rerun viewer to be connected.
    """
    rr = _ensure_rerun()
    rr.set_time_sequence("step", step)
    # TODO: Rerun doesn't have direct "jump to time" API yet
    # This sets the time for next log, which implicitly moves the timeline


def jump_to_time(time_seconds: float) -> None:
    """
    Jump Rerun viewer to a specific timestamp.
    """
    rr = _ensure_rerun()
    rr.set_time_seconds("retriever_time", time_seconds)
