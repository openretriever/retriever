"""
Pipeline - Functional graph builder without a global FlowContext.

`Pipeline` is the preferred authoring surface when you don't want an ambient
context manager. It reuses the same underlying graph/IR machinery as
`FlowContext`, but the graph lives on the Pipeline instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from retriever.flow.context import FlowContext
from retriever.flow.handle import FlowHandle

from contextvars import ContextVar


class Pipeline(FlowContext):
    """
    A FlowContext-compatible graph builder with an explicit owner object.

    `Pipeline` intentionally provides a small ergonomic surface:
    - connect flows with `handle.then(...)` (outside of FlowContext)
    - or connect explicitly with `pipeline.connect(a, b, ...)`
    - build artifacts: `pipeline.build_ir()`, `pipeline.build_execution()`
    - run on a backend: `pipeline.run(...)`
    """

    def __init__(self, name: str = "pipeline", *, on_lag: Optional[str] = None):
        super().__init__(name=name)
        self._stepper = None
        self._default_on_lag = on_lag

    def set_on_lag(self, on_lag: Optional[str]) -> "Pipeline":
        """
        Set a pipeline-level default for Rate/Hybrid lag handling.

        The default is applied at `build_ir()` time to any node whose clock is still
        using the library default (`on_lag="warn"`).

        Per-node overrides are still possible by explicitly setting `Rate(on_lag=...)`
        or `Hybrid(on_lag=...)`.
        """
        self._default_on_lag = on_lag
        return self

    def _apply_clock_defaults(self) -> None:
        """
        Apply pipeline-level defaults to clocks, if configured.

        This is intentionally late-bound (at build time) so you can configure a pipeline
        after authoring and before running.
        """
        if self._default_on_lag is None:
            return

        from retriever.flow.clock import Rate, Hybrid
        from retriever.error import FlowError, ErrCode

        desired = Rate._normalize_on_lag(self._default_on_lag)
        allowed = {"drop", "warn", "error", "catch_up"}
        if desired not in allowed:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Invalid pipeline on_lag policy",
                on_lag=self._default_on_lag,
                normalized=desired,
                allowed=sorted(allowed),
            )

        default_policy = "warn"

        for handle in self.get_handles():
            clock = handle.config.clock
            if (
                isinstance(clock, (Rate, Hybrid))
                and getattr(clock, "on_lag", default_policy) == default_policy
            ):
                clock.on_lag = desired

    def validate(self):  # type: ignore[override]
        """Validate the pipeline (applies pipeline-level defaults first)."""
        self._apply_clock_defaults()
        return super().validate()

    def connect(
        self,
        src: FlowHandle,
        dst: FlowHandle,
        *,
        map: Optional[Dict[str, str]] = None,
        sync: Optional[Any] = None,
        qsize: int = 10,
    ) -> "Pipeline":
        """Connect two handles inside this pipeline."""
        from retriever.flow.adapter import Latest

        if sync is None:
            sync = Latest()

        self.register_connection(
            src=src, dst=dst, map=map or {"*": "*"}, sync=sync, qsize=qsize
        )
        src.pipeline = self
        dst.pipeline = self
        self._stepper = None
        return self

    def merge(self, other: "Pipeline") -> "Pipeline":
        """
        Merge another Pipeline into this one.

        This is primarily used when two independently-built handle chains are
        connected together. After merging, all handles from `other` will point
        to `self`.
        """
        if other is self:
            return self

        for conn in other.get_connections():
            src = other.get_handle_for_node(conn.src_node_id)
            dst = other.get_handle_for_node(conn.dst_node_id)
            self.register_connection(
                src=src,
                dst=dst,
                map=conn.map,
                sync=conn.sync,
                qsize=conn.qsize,
            )

        for handle in other.get_handles():
            handle.pipeline = self

        self._stepper = None
        return self

    def replace(self, old: FlowHandle, new: FlowHandle) -> "Pipeline":
        """
        Replace a node handle inside this pipeline.

        This is primarily intended for debugging workflows, e.g. swapping a real
        camera source for a replay source while keeping the rest of the pipeline.
        """
        old_id = self.get_node_id(old)
        new_id = self._register_handle(new)  # type: ignore[attr-defined]

        # Rewrite connections
        for conn in self._connections:  # type: ignore[attr-defined]
            if conn.src_node_id == old_id:
                conn.src_node_id = new_id
            if conn.dst_node_id == old_id:
                conn.dst_node_id = new_id

        # Swap handle table
        self._handles.pop(old_id, None)  # type: ignore[attr-defined]
        self._handles[new_id] = new  # type: ignore[attr-defined]

        # Update pipeline owner pointers
        old.pipeline = None
        new.pipeline = self

        # Invalidate caches
        self._graph = None  # type: ignore[attr-defined]
        self._stepper = None
        return self

    def build_ir(self):
        """Validate and return an IRStruct."""
        return self.validate()

    def build_execution(self, *, policy: Any = "aggressive", **kwargs: Any):
        """Build an ExecutionGraph from this pipeline's IRStruct."""
        from retriever.ir import build_execution

        ir = self.build_ir()
        return build_execution(ir, policy=policy, **kwargs)

    def step(self, *, now: Optional[float] = None, dt: Optional[float] = None):
        """
        Execute one discrete debugging step in-process.

        This is intended for interactive debugging and unit tests.
        For full execution on backends, use `run(...)`.

        Args:
            now: Optional wall-clock timestamp to associate with this step.
            dt: Optional logical time delta (seconds) to advance an internal clock.

        Returns:
            `StepResult` (see `retriever.rt.stepper.StepResult`)
        """
        from retriever.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)

        return self._stepper.step(now=now, dt=dt)

    def reset(self) -> None:
        """
        Reset in-process execution state (debugging).

        - If a stepper exists, calls `PipelineStepper.reset()` (clears buffers + calls `Flow.reset()`).
        - If no stepper exists yet, calls `Flow.reset()` on all handles (best-effort).

        This is intended to feel like a lightweight gym-style `env.reset()` for
        debugging and record/replay workflows.
        """
        if self._stepper is not None:
            self._stepper.reset()
            return

        for handle in self.get_handles():
            try:
                handle.flow.reset()
            except Exception:
                pass

    def close_stepper(self) -> None:
        """
        Finalize all flows created for in-process stepping and drop the stepper.

        Use this when your pipeline uses hardware resources (camera, sockets, etc.)
        and you want to ensure `Flow.finalize()` is invoked.
        """
        if self._stepper is None:
            return
        self._stepper.close()
        self._stepper = None

    # ==================================================================================
    # Stepper-first Record / Replay helpers
    # ==================================================================================

    def _create_recorder(self, handle: FlowHandle, *, name: str = "stream"):
        """
        Create an in-process recorder bound to this pipeline and handle.

        This is a thin convenience wrapper around `retriever.rt.stepper.EventStreamRecorder`.
        Internal method - use `record()` for the main recording API.
        """
        from retriever.rt.stepper import EventStreamRecorder

        return EventStreamRecorder(self, handle, name=name)

    def record(
        self,
        arg1: FlowHandle | str | Path,
        arg2: Optional[str | Path] = None,
        *,
        steps: int,
        dt: Optional[float] = None,
        sleep_s: float = 0.0,
        name: str = "stream",
        visualize: bool = False,
    ):
        """
        Record `steps` iterations via `Pipeline.step()` and save to `path`.

        The format is auto-detected from the file extension:
        - `.mcap`: Records ALL pipeline outputs (session recording). Handle is ignored.
        - `.pkl.gz`: Records ONLY the specified handle (stream recording).

        Usage:
            # Record entire session to MCAP (recommended)
            pipe.record("session.mcap", steps=50)

            # Legacy: Record specific stream to pickle
            pipe.record(camera, "stream.pkl.gz", steps=50)

        Args:
            arg1: Output Path (for session) OR FlowHandle (for single stream)
            arg2: Output Path (if arg1 is handle)
            steps: Number of step iterations
            dt: Logical dt per step (seconds)
            sleep_s: Sleep seconds between steps
            name: Name for the recorded stream
            visualize: Stream to Rerun live viewer during recording (default False)
        """
        import time as _time
        from retriever.flow.handle import FlowHandle

        # Parse arguments to support both signatures
        handle: Optional[FlowHandle] = None
        path: Path

        if isinstance(arg1, FlowHandle):
            # pipe.record(handle, path, ...)
            handle = arg1
            if arg2 is None:
                raise ValueError("When passing a handle, you must also provide a path.")
            path = Path(arg2)
        else:
            # pipe.record(path, ...)
            path = Path(arg1)  # type: ignore
            handle = None

        path = Path(path)
        use_mcap = path.suffix.lower() == ".mcap"

        if not use_mcap and handle is None:
            raise ValueError("Legacy recording (.pkl.gz) requires a specific FlowHandle argument.")

        # Setup MCAP writer if using MCAP format
        mcap_writer = None
        if use_mcap:
            from retriever.lib.mcap import MCAPWriter

            mcap_writer = MCAPWriter(path)
            mcap_writer.__enter__()

        # Setup Rerun streaming if enabled
        rerun_manager = None
        if visualize:
            from retriever.lib.rerun import RerunConfig, RerunManager

            config = RerunConfig(mode="spawn")
            rerun_manager = RerunManager(config, app_id=self._name)
            rerun_manager.init()

        # Run steps and record
        # For legacy pickle recording, we need the recorder wrapper around the specific handle
        rec = self._create_recorder(handle, name=name) if not use_mcap else None
        for i in range(steps):
            result = self.step(dt=dt)

            # Write to MCAP
            if mcap_writer:
                mcap_writer.write_step(result, i)

            # Stream to Rerun if enabled
            if rerun_manager:
                rerun_manager.log_step_result(result, i)

            if sleep_s > 0:
                _time.sleep(sleep_s)

        # Finalize
        if mcap_writer:
            mcap_writer.__exit__(None, None, None)
            print(f"[MCAP] Recording saved to: {path}")

        if rec:
            rec.save(path)

        if rerun_manager:
            rerun_manager.cleanup()

        return None if use_mcap else rec.buffer

    # Alias for backwards compatibility
    def record_to(self, *args, stream_rerun: bool = False, **kwargs):
        """Alias for record(). Use record() instead."""
        return self.record(*args, visualize=stream_rerun, **kwargs)

    def view(self, path: str | Path) -> None:
        """
        Open an MCAP recording in Rerun viewer.

        Args:
            path: Path to .mcap file

        Example:
            pipe.record(camera, "session.mcap", steps=50)
            pipe.view("session.mcap")  # Opens Rerun viewer
        """
        from retriever.lib.mcap import view_in_rerun

        view_in_rerun(path)

    def replay(
        self,
        handle: FlowHandle,
        *,
        buffer: Optional[Any] = None,
        path: str | Path | None = None,
        clock: Optional[Any] = None,
        output_type: Optional[Type] = None,
    ) -> FlowHandle:
        """
        Replace `handle` with an in-process replay source and return the new handle.

        Provide exactly one of:
        - `buffer`: an `EventBuffer[T] = list[(ts, value)]`
        - `path`: path to a recording (.mcap or .pkl.gz)

        The format is auto-detected from the file extension.
        By default, the replay node reuses the replaced handle's clock and output type.
        """
        from retriever.rt.stepper import load_event_buffer, replay_flow

        if (buffer is None) == (path is None):
            raise ValueError("Provide exactly one of `buffer=` or `path=`.")

        if buffer is None:
            path = Path(path)  # type: ignore[arg-type]
            if path.suffix.lower() == ".mcap":
                # Load from MCAP format
                from retriever.lib.mcap import MCAPReader

                # Use systematic node_id lookup
                node_id = self.get_node_id(handle)
                with MCAPReader(path) as reader:
                    buffer = reader.read_node_stream(node_id)
            else:
                buffer = load_event_buffer(path)

        if clock is None:
            clock = handle.config.clock

        if output_type is None:
            output_type = handle.flow.output_type
            if output_type is None:
                raise TypeError(
                    "Handle output type is not available; add Flow type parameters [I, O]."
                )

        replay = replay_flow(buffer, output_type=output_type) @ clock  # type: ignore[arg-type]
        self.replace(handle, replay)
        return replay

    def replay_from(self, path: str | Path, inputs: List[FlowHandle]) -> None:
        """
        Systematic Replay: Configure multiple inputs to replay from a recording.

        This is a convenience wrapper that calls `replay()` for each handle in `inputs`.

        Args:
            path: Path to the recording (.mcap)
            inputs: List of source handles to replace with recorded data

        Example:
            pipe.replay_from("session.mcap", inputs=[camera, lidar])
        """
        for handle in inputs:
            self.replay(handle, path=path)

    def reset_stepper(self) -> None:
        """Reset in-process stepper state (buffers + Flow.reset)."""
        if self._stepper is not None:
            self._stepper.reset()

    def run(
        self,
        *,
        backend: str = "dora",
        duration: Optional[float] = None,
        blocking: bool = True,
        log_config: Optional[Any] = None,
        backend_config: Optional[Dict[str, Any]] = None,
        policy: Any = "aggressive",
        build: bool = False,
        visualize: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Execute this pipeline on a runtime backend.

        Args:
            backend: Backend name ('multiprocessing' or 'dora')
            duration: Optional duration in seconds (None = run indefinitely)
            blocking: If True, wait for completion/duration. If False, return immediately.
            log_config: Optional LogConfig for runtime logging.
            backend_config: Backend-specific configuration.
            policy: Execution build policy (passed to build_execution).
            build: If True, run via ExecutionGraph (grouping/placement). If False, run raw IRStruct.
            visualize: Visualization backend. Pass "rerun" to enable Rerun streaming.
            **kwargs: Extra kwargs forwarded to build_execution.
        """
        from retriever.rt.runtime import execute_ir

        # Enable visualization if requested
        if visualize == "rerun" or visualize is True:
            import retriever.lib.rerun
            retriever.lib.rerun.enable_rerun_logging(self)

        if build:
            graph = self.build_execution(policy=policy, **kwargs)
            return execute_ir(
                graph,
                backend=backend,
                duration=duration,
                blocking=blocking,
                log_config=log_config,
                backend_config=backend_config,
            )

        ir = self.build_ir()
        return execute_ir(
            ir,
            backend=backend,
            duration=duration,
            blocking=blocking,
            log_config=log_config,
            backend_config=backend_config,
        )


# ==================================================================================
# Default Pipeline Ergonomics (Global / Thread-local)
# ==================================================================================

_default_pipeline_var: ContextVar[Optional[Pipeline]] = ContextVar(
    "default_pipeline", default=None
)


def reset_default_pipeline() -> Pipeline:
    """
    Reset and return a fresh default pipeline.

    Useful for interactive sessions (notebooks) to clear state.
    """
    pipe = Pipeline("default")
    _default_pipeline_var.set(pipe)
    return pipe


def default_pipeline() -> Pipeline:
    """
    Get the current default pipeline (creating one if needed).
    """
    pipe = _default_pipeline_var.get()
    if pipe is None:
        pipe = Pipeline("default")
        _default_pipeline_var.set(pipe)
    return pipe


def connect(
    src: FlowHandle,
    dst: FlowHandle,
    *,
    map: Optional[Dict[str, str]] = None,
    sync: Optional[Any] = None,
    qsize: int = 10,
) -> Pipeline | FlowContext:
    """
    Connect two flows in the active context (or default pipeline).

    1. If a FlowContext is active (via `with Pipeline():` or `with FlowContext():`), use it.
    2. Otherwise, use `retriever.default_pipeline()`.
    """
    # Check for active context
    ctx = FlowContext.active()

    if ctx is None:
        # Fallback to default pipeline
        ctx = default_pipeline()

    # Reuse Pipeline.connect logic if available (handles defaults)
    if isinstance(ctx, Pipeline):
        return ctx.connect(src, dst, map=map, sync=sync, qsize=qsize)

    # Fallback for raw FlowContext (manual defaults)
    from retriever.flow.adapter import Latest

    if sync is None:
        sync = Latest()

    ctx.register_connection(src, dst, map=map or {"*": "*"}, sync=sync, qsize=qsize)
    src.pipeline = ctx if isinstance(ctx, Pipeline) else None
    dst.pipeline = ctx if isinstance(ctx, Pipeline) else None
    return ctx


def run(
    *,
    backend: str = "dora",
    duration: Optional[float] = None,
    blocking: bool = True,
    log_config: Optional[Any] = None,
    backend_config: Optional[Dict[str, Any]] = None,
    policy: Any = "aggressive",
    build: bool = False,
    **kwargs: Any,
):
    """
    Run the default pipeline.

    Equivalent to:
        retriever.default_pipeline().run(...)
    """
    return default_pipeline().run(
        backend=backend,
        duration=duration,
        blocking=blocking,
        log_config=log_config,
        backend_config=backend_config,
        policy=policy,
        build=build,
        **kwargs,
    )


def step(*, now: Optional[float] = None, dt: Optional[float] = None):
    """
    Execute one discrete debugging step on the default pipeline.

    Equivalent to:
        retriever.default_pipeline().step(...)
    """
    return default_pipeline().step(now=now, dt=dt)


def reset() -> None:
    """
    Reset execution state of the default pipeline (buffers, flows).

    Equivalent to:
        retriever.default_pipeline().reset()
    """
    return default_pipeline().reset()


def view(path: str | Path) -> None:
    """
    Open an MCAP recording in Rerun viewer.

    This is a convenience function that opens the Rerun viewer
    and loads the recorded data from an MCAP file.

    Args:
        path: Path to .mcap file

    Example:
        import retriever

        # Record a session
        pipe.record(camera, "session.mcap", steps=50)

        # View it later
        retriever.view("session.mcap")
    """
    from retriever.lib.mcap import view_in_rerun

    view_in_rerun(path)


__all__ = [
    "Pipeline",
    "reset_default_pipeline",
    "default_pipeline",
    "connect",
    "run",
    "step",
    "reset",
    "view",
]

