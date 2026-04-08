"""
Pipeline - Functional graph builder without a global FlowContext.

`Pipeline` is the preferred authoring surface when you don't want an ambient
context manager. It reuses the same underlying graph/IR machinery as
`FlowContext`, but the graph lives on the Pipeline instance.
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from retriever.flow.builder import PipelineBuilder
from retriever.flow.temporal import TemporalFlow


class Pipeline:
    """
    A FlowContext-compatible graph builder with an explicit owner object.

    `Pipeline` intentionally provides a small ergonomic surface:
    - connect flows with `handle.then(...)` (outside of FlowContext)
    - or connect explicitly with `pipeline.connect(a, b, ...)`
    - build artifacts: `pipeline.validate()`, `pipeline.build_execution()`
    - run on a backend: `pipeline.run(...)`
    """

    def __init__(self, name: str = "pipeline", *, on_lag: Optional[str] = None):
        self._builder = PipelineBuilder(name=name)
        self._builder.owner = self
        self._name = name
        self._context_token = None
        self._stepper = None
        self._default_on_lag = on_lag

        # Control support (opt-in)
        self._controller: Optional[Any] = None
        self._control_channel: Optional[Any] = None
        self._web_dashboard: Optional[Any] = None
        self._keyboard_controller: Optional[Any] = None

    def set_on_lag(self, on_lag: Optional[str]) -> "Pipeline":
        """
        Set a pipeline-level default for Rate/Hybrid lag handling.

        The default is applied at `validate()` time to any node whose clock is still
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

    def validate(self):
        """Validate the pipeline (applies pipeline-level defaults first)."""
        self._apply_clock_defaults()
        return self._builder.validate()

    def visualize(
        self,
        path: str | Path = "pipeline_viz.html",
        *,
        open_browser: bool = False,
    ) -> Path:
        """
        Generate an interactive HTML visualization of the pipeline.

        Args:
            path: Output file path for the HTML visualization.
            open_browser: If True, open the visualization in the default browser.

        Returns:
            Path: The absolute path to the generated HTML file.

        Example:
            pipe.visualize("my_pipeline.html")
            pipe.visualize("debug.html", open_browser=True)
        """
        ir = self.validate()
        ir.visualize(str(path), open_browser=False)

        if open_browser:
            import webbrowser
            webbrowser.open(f"file://{Path(path).resolve()}")

        return Path(path).resolve()

    # ========================================================================
    # Delegate Context / Builder Methods
    # ========================================================================

    def __enter__(self) -> "Pipeline":
        # Set Pipeline as active context (not the inner builder)
        # This ensures isinstance(ctx, Pipeline) works in TemporalFlow.then()
        from retriever.flow.builder import _active_context
        self._context_token = _active_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        from retriever.flow.builder import _active_context
        if self._context_token is not None:
            _active_context.reset(self._context_token)
            self._context_token = None
        return False

    def register_connection(self, *args, **kwargs):
        return self._builder.register_connection(*args, **kwargs)

    def get_handles(self) -> List[TemporalFlow]:
        return self._builder.get_handles()

    def get_flow_dict(self) -> Dict[str, TemporalFlow]:
        return self._builder.get_flow_dict()

    def select_flow(self, selector: str) -> TemporalFlow:
        return self._builder.select_flow(selector)

    def get_connections(self) -> List[Any]:
        return self._builder.get_connections()

    def get_handle_for_node(self, node_id: str) -> TemporalFlow:
        return self._builder.get_handle_for_node(node_id)

    def get_node_id(self, handle: TemporalFlow) -> str:
        return self._builder.get_node_id(handle)

    def get_name(self) -> str:
        return self._builder.get_name()

    def get_graph(self):
        """Get the underlying PipelineGraph (physical structure). Alias for graph()."""
        return self._builder.graph

    def graph(self):
        """Get the underlying PipelineGraph (physical structure)."""
        return self._builder.graph

    def connect(
        self,
        src: TemporalFlow,
        dst: TemporalFlow,
        *,
        map: Optional[Dict[str, str]] = None,
        sync: Optional[Union[Any, Dict[str, Any]]] = None,
        edge_config: Optional[Dict[str, Any]] = None,
        qsize: int = 10,
        on_full: Optional[str] = None,
    ) -> "Pipeline":
        """Connect two handles inside this pipeline.

        Args:
            src: Source TemporalFlow.
            dst: Destination TemporalFlow.
            map: Port mapping (e.g., {"a": "b"}). Default {"*": "*"} auto-matches.
            sync: Sync adapter(s). Can be:
                  - Single adapter: applied to all edges (e.g., `Latest()`)
                  - Dict[str, Adapter]: per-port adapters (e.g., `{"a": Hold(), "b": Latest()}`)
                  If None, uses `retriever.set_global_config(default_sync=...)`.
                  If no global default, raises FlowError.
            edge_config: Optional per-port queue/adapter overrides.
            qsize: Queue size for buffering.
            on_full: Optional queue-full policy for edges from this connection.

        Raises:
            FlowError: If sync is None and no global default_sync is configured.
        """
        from retriever.config import get_global_config
        from retriever.error import FlowError, ErrCode

        # Resolve sync: explicit > global default > error
        if sync is None:
            sync = get_global_config().get("default_sync")
            if sync is None:
                raise FlowError(
                    ErrCode.FLOW_CONNECTION_INVALID,
                    "sync= is required. Set globally via retriever.set_global_config(default_sync=...) "
                    "or pass sync= to each connect() call.",
                    src=src.flow.__class__.__name__,
                    dst=dst.flow.__class__.__name__,
                )

        self._builder.register_connection(
            src=src,
            dst=dst,
            map=map or {"*": "*"},
            sync=sync,
            edge_config=edge_config,
            qsize=qsize,
            on_full=on_full,
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
            self._builder.register_connection(
                src=src,
                dst=dst,
                map=conn.map,
                sync=conn.sync,
                edge_config=conn.edge_config,
                qsize=conn.qsize,
                on_full=conn.on_full,
            )

        for handle in other.get_handles():
            handle.pipeline = self

        self._stepper = None
        return self

    def replace(
        self,
        old: TemporalFlow,
        new: TemporalFlow,
        *,
        keep_id: bool = True,
    ) -> "Pipeline":
        """
        Replace a node handle inside this pipeline.

        This is primarily intended for debugging workflows, e.g. swapping a real
        camera source for a replay source while keeping the rest of the pipeline.
        """
        from retriever.error import FlowError, ErrCode

        if old is new:
            return self
        if new.pipeline is not None and new.pipeline is not self:
            raise FlowError(
                ErrCode.FLOW_CONNECTION_INVALID,
                "Cannot replace with a handle that already belongs to a different Pipeline.",
            )

        old_id = self.get_node_id(old)
        existing_id = None
        for node_id, handle in self._builder._handles.items():  # type: ignore[attr-defined]
            if handle is new:
                existing_id = node_id
                break
        if existing_id is not None and existing_id != old_id:
            raise FlowError(
                ErrCode.FLOW_CONNECTION_INVALID,
                f"Replacement handle is already registered as '{existing_id}' in this pipeline.",
                node_id=existing_id,
            )

        if keep_id:
            new_id = old_id
            new.name = old_id
        else:
            new_id = existing_id or self._builder._register_handle(new)  # type: ignore[attr-defined]

            # Rewrite connections when the node id changes.
            for conn in self._builder._connections:  # type: ignore[attr-defined]
                if conn.src_node_id == old_id:
                    conn.src_node_id = new_id
                if conn.dst_node_id == old_id:
                    conn.dst_node_id = new_id

        # Swap handle table
        self._builder._handles.pop(old_id, None)  # type: ignore[attr-defined]
        self._builder._handles[new_id] = new  # type: ignore[attr-defined]

        # Update pipeline owner pointers
        old.pipeline = None
        new.pipeline = self

        # Invalidate caches
        self._builder._graph = None  # type: ignore[attr-defined]
        self._stepper = None
        return self

    def inject_input(
        self,
        node_id: str,
        port: str,
        value: Any,
        *,
        timestamp: Optional[float] = None,
    ) -> "Pipeline":
        """Inject one external input into the in-process stepper."""
        from retriever.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)
        self._stepper.inject_input(node_id, port, value, timestamp=timestamp)
        return self

    def inject_inputs(
        self,
        values: Dict[str, Dict[str, Any]],
        *,
        timestamp: Optional[float] = None,
    ) -> "Pipeline":
        """Inject a batch of external inputs into the in-process stepper."""
        from retriever.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)
        self._stepper.inject_inputs(values, timestamp=timestamp)
        return self

    def _build_ir(self):
        """Validate and return an IR (Internal)."""
        return self.validate()

    def build_execution(self, *, policy: Any = "aggressive", **kwargs: Any):
        """Build an ExecutionGraph from this pipeline's IR."""
        ir = self._build_ir()
        return ir.compile(policy=policy, **kwargs)

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

    def inject_input(
        self,
        node: Union[str, TemporalFlow],
        port: str,
        value: Any,
        *,
        timestamp: Optional[float] = None,
    ) -> "Pipeline":
        """
        Inject one external input value into a node for the next in-process step.

        This is intended for composite/debugging workflows where a pipeline has
        surfaced but unconnected input ports.
        """
        from retriever.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)

        node_id = node if isinstance(node, str) else self.get_node_id(node)
        self._stepper.inject_input(node_id, port, value, timestamp=timestamp)
        return self

    def inject_inputs(
        self,
        values: Dict[str, Dict[str, Any]],
        *,
        timestamp: Optional[float] = None,
    ) -> "Pipeline":
        """Inject a batch of external input values into surfaced pipeline ports."""
        from retriever.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)

        self._stepper.inject_inputs(values, timestamp=timestamp)
        return self

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
    # Control System
    # ==================================================================================

    def _enable_control_from_config(self, config: Any) -> Any:
        """Internal: Enable control from ControlConfig."""
        try:
            from retriever.rt.control.channel import MPControlChannel
            from retriever.rt.control.controller import PipelineController
        except ImportError:
            raise ImportError(
                "Control system not available. Ensure retriever.rt.control is installed."
            )

        self._control_channel = MPControlChannel()
        self._controller = PipelineController(self, self._control_channel)

        if config.web_port:
            try:
                from retriever.rt.control.web import WebDashboard
                config_info = {
                    "Pipeline": self._name or "Unnamed",
                    "Control Features": "Web Dashboard + Individual Flow Control",
                }
                if config.keyboard:
                    config_info["Keyboard Controls"] = "Enabled"
                self._web_dashboard = WebDashboard(
                    self._controller,
                    port=config.web_port,
                    config_info=config_info
                )
            except ImportError:
                print(f"Web dashboard requires FastAPI: pip install fastapi uvicorn")

        if config.keyboard:
            try:
                from retriever.rt.control.keyboard import GlobalKeyboardController
                self._keyboard_controller = GlobalKeyboardController(self._controller)
            except ImportError:
                print(f"Keyboard control requires pynput: pip install pynput")

        return self._controller

    @property
    def controller(self) -> Optional[Any]:
        """Get the controller if control is enabled."""
        return self._controller

    # ==================================================================================
    # Stepper-first Record / Replay helpers
    # ==================================================================================

    def _create_recorder(self, handle: TemporalFlow, *, name: str = "stream"):
        """
        Create an in-process recorder bound to this pipeline and handle.

        This is a thin convenience wrapper around `retriever.rt.stepper.EventStreamRecorder`.
        Internal method - use `record()` for the main recording API.
        """
        from retriever.rt.stepper import EventStreamRecorder

        return EventStreamRecorder(self, handle, name=name)

    def record(
        self,
        arg1: TemporalFlow | str | Path | Any,
        arg2: Optional[str | Path] = None,
        *,
        steps: int,
        dt: Optional[float] = None,
        sleep_s: float = 0.0,
        name: str = "stream",
        visualize: bool = False,
    ):
        """
        Record `steps` iterations via `Pipeline.step()` and save to one or more artifacts.

        The format is auto-detected from the file extension:
        - `.mcap`: Records ALL pipeline outputs (session recording, replayable).
        - `.rrd`: Records ALL pipeline outputs as a native Rerun recording (inspectable and replayable).
        - `.pkl.gz`: Records ONLY the specified handle (stream recording).

        Usage:
            # Record entire session to MCAP (recommended)
            pipe.record("session.mcap", steps=50)

            # Record entire session to Rerun recording
            pipe.record("session.rrd", steps=50)

            # Record both artifacts from one run
            pipe.record(RecordConfig(path="session.rrd", mirrors=("session.mcap",)), steps=50)

            # Legacy: Record specific stream to pickle
            pipe.record(camera, "stream.pkl.gz", steps=50)

        Args:
            arg1: Output Path (for session) OR TemporalFlow (for single stream)
            arg2: Output Path (if arg1 is handle)
            steps: Number of step iterations
            dt: Logical dt per step (seconds)
            sleep_s: Sleep seconds between steps
            name: Name for the recorded stream
            visualize: Stream to Rerun live viewer during recording (default False)
        """
        import time as _time
        from retriever.flow.temporal import TemporalFlow
        from retriever.config import RecordConfig
        from retriever.recording import build_recording_sink, detect_recording_format

        # Parse arguments to support both signatures
        handle: Optional[TemporalFlow] = None
        path: Path
        record_cfg: Optional[RecordConfig] = None

        if isinstance(arg1, TemporalFlow):
            # pipe.record(handle, path, ...)
            handle = arg1
            if arg2 is None:
                raise ValueError("When passing a handle, you must also provide a path.")
            path = Path(arg2)
        elif isinstance(arg1, RecordConfig):
            if arg2 is not None:
                raise ValueError("RecordConfig already supplies the output path; do not pass a second path.")
            record_cfg = arg1
            path = Path(record_cfg.path)
        else:
            # pipe.record(path, ...)
            path = Path(arg1)  # type: ignore

        path = Path(path)
        session_format = detect_recording_format(path)
        use_session_recording = session_format is not None

        if not use_session_recording and handle is None:
            raise ValueError("Legacy recording (.pkl.gz) requires a specific TemporalFlow argument.")

        if record_cfg and record_cfg.visualize and not visualize:
            visualize = True

        # Setup Rerun streaming if enabled
        rerun_manager = None
        if visualize:
            from retriever.lib.rerun import RerunConfig, RerunManager

            config = RerunConfig(mode="spawn")
            rerun_manager = RerunManager(config, app_id=self._name)
            rerun_manager.init()

        recording_sink = None
        if use_session_recording:
            record_cfg = record_cfg or RecordConfig(path=path)
            recording_sink = build_recording_sink(record_cfg, app_id=self._name)
            recording_sink.open()

        # Run steps and record
        # For legacy pickle recording, we need the recorder wrapper around the specific handle
        rec = self._create_recorder(handle, name=name) if not use_session_recording else None
        try:
            for i in range(steps):
                result = self.step(dt=dt)

                if recording_sink:
                    recording_sink.write_step(result, i)

                if rerun_manager:
                    rerun_manager.log_step_result(result, i)

                if sleep_s > 0:
                    _time.sleep(sleep_s)

                if rec:
                    node_id = self.get_node_id(handle)
                    out = result.outputs.get(node_id)
                    if out is None:
                        out = rec.output_type()
                    rec.buffer.append((result.now, out))
        finally:
            if recording_sink:
                recording_sink.close()

            if rec:
                rec.save(path)

            if rerun_manager:
                rerun_manager.cleanup()

        return None if use_session_recording else rec.buffer

    # Alias for backwards compatibility
    def record_to(self, *args, stream_rerun: bool = False, **kwargs):
        """Alias for record(). Use record() instead."""
        return self.record(*args, visualize=stream_rerun, **kwargs)

    def view(self, path: str | Path) -> None:
        """
        Open a persisted recording artifact in Rerun.

        Args:
            path: Path to .mcap or .rrd file

        Example:
            pipe.record(camera, "session.mcap", steps=50)
            pipe.view("session.mcap")  # Opens Rerun viewer
        """
        from retriever.recording import view_recording

        view_recording(path)

    def replay(
        self,
        handle: TemporalFlow,
        *,
        buffer: Optional[Any] = None,
        path: str | Path | None = None,
        clock: Optional[Any] = None,
        output_type: Optional[Type] = None,
    ) -> TemporalFlow:
        """
        Replace `handle` with an in-process replay source and return the new handle.

        Provide exactly one of:
        - `buffer`: an `EventBuffer[T] = list[(ts, value)]`
        - `path`: path to a recording (.mcap, .rrd, or .pkl.gz)

        The format is auto-detected from the file extension.
        `.mcap` and `.rrd` are replayable when they contain Retriever replay payloads.
        By default, the replay node reuses the replaced handle's clock and output type.
        """
        from retriever.rt.stepper import load_event_buffer, replay_flow

        if (buffer is None) == (path is None):
            raise ValueError("Provide exactly one of `buffer=` or `path=`.")

        if clock is None:
            clock = handle.config.clock

        if output_type is None:
            output_type = handle.flow.output_type
            if output_type is None:
                raise TypeError(
                    "Handle output type is not available; add Flow type parameters [I, O]."
                )

        if buffer is None:
            path = Path(path)  # type: ignore[arg-type]
            node_id = self.get_node_id(handle)
            suffix = path.suffix.lower()
            if suffix in {".mcap", ".rrd"}:
                from retriever.recording import read_node_stream_from_recording

                buffer = read_node_stream_from_recording(path, node_id, output_type=output_type)
            else:
                buffer = load_event_buffer(path)

        replay = replay_flow(buffer, output_type=output_type) @ clock  # type: ignore[arg-type]
        self.replace(handle, replay)
        return replay

    def replay_from(self, path: str | Path, inputs: List[TemporalFlow]) -> None:
        """
        Systematic Replay: Configure multiple inputs to replay from a recording.

        This is a convenience wrapper that calls `replay()` for each handle in `inputs`.

        Args:
            path: Path to the recording (.mcap or .rrd)
            inputs: List of source handles to replace with recorded data

        Example:
            pipe.replay_from("session.rrd", inputs=[camera, lidar])
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
        backend: Optional[str] = None,
        duration: Optional[float] = None,
        blocking: bool = True,
        log_config: Optional[Any] = None,
        backend_config: Optional[Dict[str, Any]] = None,
        policy: Any = "aggressive",
        deploy: Optional[Dict[Any, str]] = None,
        build: bool = False,

        visualize: Optional[str] = None,
        record: Optional[Union[str, Any]] = None, # RecordConfig
        control: Optional[Any] = None,  # ControlConfig
        **kwargs: Any,
    ):
        """
        Execute this pipeline on a runtime backend.

        Args:
            backend: Backend name ("multiprocessing", "dora", "in-process").
                     Defaults to "multiprocessing" usually, unless recording.
            duration: Optional duration in seconds (None = run indefinitely).
            blocking: If True, wait for completion.
            log_config: Optional LogConfig.
            visualize: "rerun" for live streaming.
            record: Path (str) or RecordConfig to enable recording.
                    Forces backend="in-process" currently.
            control: ControlConfig for pause/resume/reset control.
                     Example: control=ControlConfig(web_port=8080, keyboard=True)
            deploy: Dict mapping TemporalFlow or node_id (str) to machine name.
            **kwargs: Extra arguments.
        """

        from retriever.rt.runtime import execute_ir
        from retriever.config import RecordConfig, get_global_config

        # Resolve global config defaults
        glob = get_global_config()
        if backend is None:
            backend = glob.get("backend", "multiprocessing")

        # Resolve control config: arg > global
        control_cfg = control or glob.get("control")
        if control_cfg and control_cfg.enabled:
            # Enable control if not already enabled
            if not self._controller:
                self._enable_control_from_config(control_cfg)

        # Resolve recording config
        # hierarchy: arg > global
        record_cfg = None
        if record is not None:
             if isinstance(record, str):
                 record_cfg = RecordConfig(path=record)
             else:
                 record_cfg = record
        elif glob.get("record"):
             # Global default
             record_cfg = glob["record"]

        # Handling "in-process" enforcement for recording
        if record_cfg and backend != "in-process":
            # Unified persisted recording is currently stepper/in-process first.
            import logging
            logging.getLogger("retriever").info(
                f"Recording enabled ({record_cfg.path}); switching backend to 'in-process'."
            )
            backend = "in-process"

        # Prepare backend config: merge global defaults with local overrides
        global_backend_config = glob.get("backend_config", {})
        local_backend_config = backend_config or {}
        backend_config = {**global_backend_config, **local_backend_config}

        # Inject control channel if enabled
        if self._control_channel:
            backend_config["control_channel"] = self._control_channel
        
        # Handle deployment overrides
        if deploy:
            overrides = {}
            for target, machine in deploy.items():
                if hasattr(target, 'flow'): # Is TemporalFlow
                    # We need the node ID. The handle doesn't strictly know its ID 
                    # until pipeline validation, but we can look it up if registered.
                    node_id = self.get_node_id(target)
                    overrides[node_id] = machine
                elif isinstance(target, str):
                    overrides[target] = machine
                else:
                    raise ValueError(f"Invalid deploy target: {target} (expected TemporalFlow or str ID)")
            
            backend_config["deployment_overrides"] = overrides



        # Inject live pipeline instance for in-process backend optimization
        if backend == "in-process":
             backend_config["pipeline_instance"] = self
             # Pass record config explicitly if we possess it (engine will assume it)
             if record_cfg:
                 backend_config["record"] = record_cfg

        # Start web dashboard if enabled
        if self._web_dashboard:
            # Update config info with execution details
            self._web_dashboard.config_info.update({
                "Backend": backend,
                "Duration": f"{duration}s" if duration else "Unlimited",
            })
            self._web_dashboard.start(blocking=False)

        # Enable visualization if requested
        if record_cfg and getattr(record_cfg, "visualize", False) and visualize is None:
            visualize = "rerun"

        if visualize == "rerun" or visualize is True:
            import retriever.lib.rerun
            retriever.lib.rerun.enable_rerun_logging(self) # Still init process for safety/pre-checks

            # Ensure backend knows to use Rerun
            if "rerun_config" not in backend_config:
                 backend_config["rerun_config"] = {"mode": "spawn"}

        ir = self._build_ir() if not build else None
        # Note: 'build=True' path in original code calls build_execution.
        # But for in-process, we mostly use IR or live instance.
        # Standard execute_ir handles 'ir' being ExecutionGraph if passed.

        
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
    src: TemporalFlow,
    dst: TemporalFlow,
    *,
    map: Optional[Dict[str, str]] = None,
    sync: Optional[Any] = None,
    edge_config: Optional[Dict[str, Any]] = None,
    qsize: int = 10,
    on_full: Optional[str] = None,
) -> Pipeline | PipelineBuilder:
    """
    Connect two flows in the active context (or default pipeline).

    1. If a PipelineBuilder is active (via `with Pipeline():` or `with PipelineBuilder():`), use it.
    2. Otherwise, use `retriever.default_pipeline()`.
    """
    # Fallback for raw PipelineBuilder (manual defaults)
    from retriever.flow.adapter import Latest

    if sync is None:
        sync = Latest()

    # Check for active context
    ctx = PipelineBuilder.active()

    if ctx is None:
        # Fallback to default pipeline
        ctx = default_pipeline()

    # Reuse Pipeline.connect logic if available (handles defaults)
    if isinstance(ctx, Pipeline):
        return ctx.connect(
            src,
            dst,
            map=map,
            sync=sync,
            edge_config=edge_config,
            qsize=qsize,
            on_full=on_full,
        )

    # Check if context belongs to a pipeline (Composition support)
    if getattr(ctx, "owner", None) and isinstance(ctx.owner, Pipeline):
        return ctx.owner.connect(
            src,
            dst,
            map=map,
            sync=sync,
            edge_config=edge_config,
            qsize=qsize,
            on_full=on_full,
        )

    ctx.register_connection(
        src,
        dst,
        map=map or {"*": "*"},
        sync=sync,
        edge_config=edge_config,
        qsize=qsize,
        on_full=on_full,
    )
    
    # Try to set pipeline pointer if possible
    pipeline_ref = getattr(ctx, "owner", None) if isinstance(getattr(ctx, "owner", None), Pipeline) else None
    src.pipeline = pipeline_ref
    dst.pipeline = pipeline_ref
    return ctx


def run(
    *,
    backend: str = "dora",
    duration: Optional[float] = None,
    blocking: bool = True,
    log_config: Optional[Any] = None,
    backend_config: Optional[Dict[str, Any]] = None,
    policy: Any = "aggressive",
    deploy: Optional[Dict[Any, str]] = None,
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
        deploy=deploy,
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
    Open a persisted recording artifact in Rerun.

    Args:
        path: Path to .mcap or .rrd file

    Example:
        import retriever

        # Record a session
        pipe.record(camera, "session.mcap", steps=50)

        # View it later
        retriever.view("session.mcap")
    """
    from retriever.recording import view_recording

    view_recording(path)


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
