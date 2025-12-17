"""
Pipeline - Functional graph builder without a global FlowContext.

`Pipeline` is the preferred authoring surface when you don't want an ambient
context manager. It reuses the same underlying graph/IR machinery as
`FlowContext`, but the graph lives on the Pipeline instance.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

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

        return self

    def build_ir(self):
        """Validate and return an IRStruct."""
        return self.validate()

    def build_execution(self, *, policy: Any = "aggressive", **kwargs: Any):
        """Build an ExecutionGraph from this pipeline's IRStruct."""
        from retriever.core.ir import build_execution

        ir = self.build_ir()
        return build_execution(ir, policy=policy, **kwargs)

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
