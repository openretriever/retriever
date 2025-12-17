"""
Pipeline - Functional graph builder without a global FlowContext.

`Pipeline` is the preferred authoring surface when you don't want an ambient
context manager. It reuses the same underlying graph/IR machinery as
`FlowContext`, but the graph lives on the Pipeline instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Type

from retriever.core.flow.context import FlowContext
from retriever.core.flow.handle import FlowHandle


class Pipeline(FlowContext):
    """
    A FlowContext-compatible graph builder with an explicit owner object.

    `Pipeline` intentionally provides a small ergonomic surface:
    - connect flows with `handle.then(...)` (outside of FlowContext)
    - or connect explicitly with `pipeline.connect(a, b, ...)`
    - build artifacts: `pipeline.build_ir()`, `pipeline.build_execution()`
    - run on a backend: `pipeline.run(...)`
    """

    def __init__(self, name: str = "pipeline"):
        super().__init__(name=name)
        self._stepper = None

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
        from retriever.core.flow.adapter import Latest

        if sync is None:
            sync = Latest()

        self.register_connection(src=src, dst=dst, map=map or {"*": "*"}, sync=sync, qsize=qsize)
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
        from retriever.core.ir import build_execution

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
            `StepResult` (see `retriever.core.rt.stepper.StepResult`)
        """
        from retriever.core.rt.stepper import PipelineStepper

        if self._stepper is None:
            self._stepper = PipelineStepper(self)

        return self._stepper.step(now=now, dt=dt)

    # ==================================================================================
    # Stepper-first Record / Replay helpers
    # ==================================================================================

    def record(self, handle: FlowHandle, *, name: str = "stream"):
        """
        Create an in-process recorder bound to this pipeline and handle.

        This is a thin convenience wrapper around `retriever.core.rt.stepper.EventStreamRecorder`.
        """
        from retriever.core.rt.stepper import EventStreamRecorder

        return EventStreamRecorder(self, handle, name=name)

    def record_to(
        self,
        handle: FlowHandle,
        path: str | Path,
        *,
        steps: int,
        dt: Optional[float] = None,
        sleep_s: float = 0.0,
        name: str = "stream",
    ):
        """
        Record `steps` iterations via `Pipeline.step()` and save to `path`.

        Notes:
        - This does not call `close_stepper()`; keep a `try/finally` in user code for hardware resources.
        - Storage format is gzip+pickle (debug artifact).
        """
        rec = self.record(handle, name=name)
        rec.run(steps=steps, dt=dt, sleep_s=sleep_s)
        rec.save(path)
        return rec.buffer

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
        - `path`: path to a buffer saved via `record_to(...)` / `save_event_buffer(...)`

        By default, the replay node reuses the replaced handle's clock and output type.
        """
        from retriever.core.rt.stepper import load_event_buffer, replay_flow

        if (buffer is None) == (path is None):
            raise ValueError("Provide exactly one of `buffer=` or `path=`.")

        if buffer is None:
            buffer = load_event_buffer(path)  # type: ignore[arg-type]

        if clock is None:
            clock = handle.config.clock

        if output_type is None:
            output_type = handle.flow.output_type
            if output_type is None:
                raise TypeError("Handle output type is not available; add Flow type parameters [I, O].")

        replay = replay_flow(buffer, output_type=output_type) @ clock  # type: ignore[arg-type]
        self.replace(handle, replay)
        return replay

    def reset_stepper(self) -> None:
        """Reset in-process stepper state (buffers + Flow.reset)."""
        if self._stepper is not None:
            self._stepper.reset()

    def close_stepper(self) -> None:
        """Finalize flows used by the in-process stepper and drop stepper state."""
        if self._stepper is not None:
            self._stepper.close()
            self._stepper = None

    def run(
        self,
        *,
        backend: str = "multiprocessing",
        duration: Optional[float] = None,
        blocking: bool = True,
        log_config: Optional[Any] = None,
        backend_config: Optional[Dict[str, Any]] = None,
        policy: Any = "aggressive",
        build: bool = False,
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
            **kwargs: Extra kwargs forwarded to build_execution.
        """
        from retriever.core.rt.runtime import execute_ir

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


__all__ = ["Pipeline"]
