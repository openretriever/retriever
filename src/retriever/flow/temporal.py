"""
TemporalFlow for binding flows to clocks and creating connections.

A TemporalFlow represents a flow bound to a clock, forming a node
in the dataflow graph that can be connected to other nodes.
"""

import keyword
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.config import FlowConfig, EdgeConfig
    from retriever.flow.clock import Clock
    from retriever.flow.adapter import Adapter
    from retriever.flow.pipeline import Pipeline


_FLOW_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class TemporalFlow:
    """A flow bound to execution configuration."""

    flow: "Flow"
    config: "FlowConfig"
    pipeline: Optional["Pipeline"] = None
    name: Optional[str] = None

    @property
    def clock(self) -> "Clock":
        """Convenience accessor for the clock."""

    @property
    def input_type(self) -> Optional["type"]:
        """Get the input type I of the bound flow."""
        return self.flow.input_type

    @property
    def output_type(self) -> Optional["type"]:
        """Get the output type O of the bound flow."""
        return self.flow.output_type

    @property
    def display_name(self) -> str:
        """Human-readable selector/debug label for this handle."""
        return self.name or self.flow.__class__.__name__

    def named(self, name: str) -> "TemporalFlow":
        """
        Assign a stable selector/name to this flow within a pipeline.

        Named flows can be addressed later via helpers like
        `pipe.select_flow("camera")` and explicit pipeline surface selectors
        like `"camera.image"`.
        """
        if not _FLOW_NAME_RE.match(name) or keyword.iskeyword(name):
            raise ValueError(
                f"Invalid flow name '{name}'. "
                "Flow names must be valid identifiers like 'camera' or 'planner_main'."
            )
        self.name = name
        return self

    def matches(self, selector: str) -> bool:
        """Return True when `selector` matches this handle's name or flow class."""
        return selector == self.name or selector == self.flow.__class__.__name__

    def __repr__(self) -> str:
        flow_name = self.flow.__class__.__name__
        if self.name:
            return f"<TemporalFlow {self.name}:{flow_name}>"
        return f"<TemporalFlow {flow_name}>"

    def then(
        self,
        next: "TemporalFlow",
        map: Optional[Dict[str, str]] = None,
        sync: Optional["Adapter"] = None,
        qsize: int = 10,
        on_full: Optional[str] = None,
        edge_config: Optional[Dict[str, "EdgeConfig"]] = None,
    ) -> "TemporalFlow":
        """
        Connect this flow to another flow.

        Args:
            next: Destination TemporalFlow
            map: Field mapping (defaults to {'*': '*'})
                - {'*': '*'} for atomic (whole value)
                - {'src_field': 'dst_field'} for field mapping
            sync: Adapter for queue sampling (single adapter or dict per port)
            edge_config: Per-port buffer configuration (EdgeConfig per port)

        Returns:
            Destination TemporalFlow for chaining

        Examples:
            Atomic connection:
                camera.then(detector)

            Field mapping:
                camera.then(fusion, map={'output': 'camera'})

            With adapter:
                camera.then(detector, sync=Hold(0.1), qsize=5)

            Per-port config:
                camera.then(planner, edge_config={
                    "*": EdgeConfig(qsize=32, on_full="drop"),
                    "frame": EdgeConfig(qsize=100, on_full="drop"),
                    "timestamp": EdgeConfig(qsize=10),
                })
        """
        from retriever.flow.adapter import Latest
        from retriever.error import FlowError, ErrCode

        if map is None:
            map = {"*": "*"}

        if sync is None:
            sync = Latest()

        # Legacy shorthand: normalize qsize/on_full into edge-level defaults.
        # This keeps per-edge transport policy in EdgeConfig (wildcard "*"),
        # while preserving existing call sites that still pass qsize/on_full.
        if qsize != 10 or on_full is not None:
            from retriever.flow.config import EdgeConfig

            normalized_edge_config = dict(edge_config or {})
            normalized_edge_config.setdefault("*", EdgeConfig(qsize=qsize, on_full=on_full))
            edge_config = normalized_edge_config
            qsize = 10
            on_full = None

        # Validate adapter conflict: sync and edge_config.adapter for same port
        if edge_config:
            for port, cfg in edge_config.items():
                if cfg.adapter is not None:
                    # Check if sync also specifies adapter for this port
                    if isinstance(sync, dict) and port in sync:
                        raise FlowError(
                            ErrCode.FLOW_CONNECTION_INVALID,
                            f"Adapter for port '{port}' specified in both sync and edge_config. "
                            "Use only one.",
                            port=port,
                        )
                    elif not isinstance(sync, dict) and sync is not None:
                        # Single sync adapter + edge_config.adapter conflict
                        raise FlowError(
                            ErrCode.FLOW_CONNECTION_INVALID,
                            f"Adapter for port '{port}' specified in edge_config, but a global "
                            "sync adapter is also set. Use sync=None or remove edge_config adapter.",
                            port=port,
                        )

        from retriever.flow.builder import PipelineBuilder

        ctx = PipelineBuilder.active()
        if ctx is not None:
            # If the active context is a Pipeline, treat `then`/`>>` as pipeline wiring.
            from retriever.flow.pipeline import Pipeline

            if isinstance(ctx, Pipeline):
                if (self.pipeline is not None and self.pipeline is not ctx) or (
                    next.pipeline is not None and next.pipeline is not ctx
                ):
                    raise FlowError(
                        ErrCode.FLOW_CONNECTION_INVALID,
                        "Cannot connect handles from a different Pipeline inside an active Pipeline context.",
                    )

                ctx.connect(
                    self,
                    next,
                    map=map,
                    sync=sync,
                    qsize=qsize,
                    on_full=on_full,
                    edge_config=edge_config,
                )
                return next

            # Active context is a plain PipelineBuilder: forbid Pipeline-tagged handles to avoid mixing.
            if self.pipeline is not None or next.pipeline is not None:
                raise FlowError(
                    ErrCode.FLOW_CONNECTION_INVALID,
                    "Cannot mix Pipeline-based connections with an active PipelineBuilder. "
                    "Either build the graph inside PipelineBuilder, or connect handles outside "
                    "a context and run via Pipeline.",
                )

            ctx.register_connection(
                src=self,
                dst=next,
                map=map,
                sync=sync,
                qsize=qsize,
                on_full=on_full,
                edge_config=edge_config,
            )
            return next

        from retriever.flow.pipeline import Pipeline

        left = self.pipeline
        right = next.pipeline
        if left is not None and right is not None and left is not right:
            left.merge(right)

        pipeline = left or right or Pipeline()
        pipeline.connect(
            self,
            next,
            map=map,
            sync=sync,
            qsize=qsize,
            on_full=on_full,
            edge_config=edge_config,
        )

        return next

    def __rshift__(self, next) -> "TemporalFlow":
        """
        Syntactic sugar for `then`: `a >> b`.

        Also supports fanout: `a >> (b & c)` connects a to both b and c.
        """
        # Handle Fanout objects created by `&` operator
        if hasattr(next, "handles"):  # It's a Fanout
            for handle in next.handles:
                self.then(handle)
            return self
        return self.then(next)

    def __call__(self, source: "TemporalFlow", **kwargs) -> "TemporalFlow":
        """
        Functional connection syntax: `op(source)` is equivalent to `source.then(op)`.

        Args:
            source: The upstream flow handle.
            **kwargs: Arguments passed to .then() (e.g. map, sync, qsize).

        Returns:
            Self (this handle) for chaining.
        """
        return source.then(self, **kwargs)

    def __and__(self, other: "TemporalFlow") -> "Fanout":
        """
        Create a fanout group: `a & b` means both receive from the same source.

        This enables single-expression graph building:
            source >> (detector & logger)  # source feeds both

        Returns:
            Fanout object that can be further combined or connected to.
        """
        return Fanout(self, other)

    def fanout(self, *destinations: "TemporalFlow") -> "TemporalFlow":
        """
        Connect this flow to multiple destinations (fan-out).

        Args:
            *destinations: TemporalFlows to connect to

        Returns:
            Self for chaining

        Example:
            source.fanout(detector, logger, recorder)
        """
        for dst in destinations:
            self.then(dst)
        return self

    def deploy(self, machine: str) -> "TemporalFlow":
        """
        Specify which machine this flow should run on (Dora backend only).

        Args:
            machine: Name of the machine (must match dora coordinator config)

        Returns:
            Self for chaining
        """
        # Ensure resources object exists
        if self.config.resources is None:
            from retriever.flow.config import ResourceSpec

            self.config.resources = ResourceSpec()

        # Update host affinity
        # We replace the list to prioritize this deployment target
        self.config.resources.host_affinity = [machine]
        return self


class Fanout:
    """
    Represents a fan-out group created by `a & b`.

    This enables FRP-style single-expression graph building:
        source >> (detector & logger)
        source >> (a & b & c)
    """

    def __init__(self, *handles: TemporalFlow):
        self.handles = list(handles)

    def __and__(self, other: TemporalFlow) -> "Fanout":
        """Chain more handles: (a & b) & c"""
        self.handles.append(other)
        return self

    def __rrshift__(self, source: TemporalFlow) -> "Fanout":
        """
        Receive from source: source >> (a & b)

        Connects source to all handles in this fanout group.
        """
        for handle in self.handles:
            source.then(handle)
        return self

    def __iter__(self):
        """Allow iteration over fanout handles."""
        return iter(self.handles)

    def __repr__(self):
        names = [h.flow.__class__.__name__ for h in self.handles]
        return f"Fanout({' & '.join(names)})"
