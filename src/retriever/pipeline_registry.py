"""
Pipeline registry (IR-first).

This registry is designed for the refactored runtime:
  FlowContext -> validate(...) -> IR -> execute_ir(...)

It registers *pipeline factories* (callables) that return either:
  - IR (preferred), or
  - FlowContext (will be validated to IR).

This enables:
  - Discoverable pipelines (for a future `retriever` CLI)
  - Plugin-based extensibility via entry points (see `retriever.plugins`)
  - Flow-like pipeline surfaces inferred from unused external ports
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union, Iterable, Tuple, Literal

from retriever.flow.builder import PipelineBuilder
from retriever.ir import IR
from retriever.utils import load_plugins

PipelineFactory = Callable[..., Union[IR, PipelineBuilder]]


def _ensure_plugins_loaded() -> None:
    # Best-effort plugin loading: enables external packages to register pipelines.
    try:
        load_plugins()
    except Exception:
        # Plugins are optional and should not prevent using local code.
        pass


@dataclass(frozen=True)
class PipelineInfo:
    """Metadata for a registered pipeline."""

    name: str
    factory: PipelineFactory
    category: str = "general"
    description: str = ""
    tags: Tuple[str, ...] = field(default_factory=tuple)
    surface_policy: Literal["auto_unused", "explicit", "none"] = "auto_unused"
    input_ports: Tuple[str, ...] = field(default_factory=tuple)
    output_ports: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PipelineSurfacePort:
    """One externally visible port on a registered pipeline surface."""

    node_id: str
    node_type: str
    port: str
    type: str
    direction: Literal["input", "output"]


@dataclass(frozen=True)
class PipelineSurface:
    """Flow-like external port surface for a registered pipeline."""

    inputs: Tuple[PipelineSurfacePort, ...] = field(default_factory=tuple)
    outputs: Tuple[PipelineSurfacePort, ...] = field(default_factory=tuple)


class PipelineRegistry:
    """Global registry of pipeline factories."""

    def __init__(self) -> None:
        self._pipelines: Dict[str, PipelineInfo] = {}

    def register(
        self,
        name: str,
        factory: PipelineFactory,
        *,
        category: str = "general",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
        surface_policy: Literal["auto_unused", "explicit", "none"] = "auto_unused",
        input_ports: Optional[Iterable[str]] = None,
        output_ports: Optional[Iterable[str]] = None,
        overwrite: bool = False,
    ) -> None:
        if name in self._pipelines and not overwrite:
            raise ValueError(f"Pipeline '{name}' already registered (set overwrite=True to replace)")

        info = PipelineInfo(
            name=name,
            factory=factory,
            category=category,
            description=description,
            tags=tuple(tags or ()),
            surface_policy=surface_policy,
            input_ports=tuple(input_ports or ()),
            output_ports=tuple(output_ports or ()),
        )
        self._pipelines[name] = info

    def get(self, name: str) -> PipelineInfo:
        _ensure_plugins_loaded()
        try:
            return self._pipelines[name]
        except KeyError:
            available = sorted(self._pipelines.keys())
            raise ValueError(f"Pipeline '{name}' not found. Available: {available}") from None

    def list(self, *, category: Optional[str] = None) -> Dict[str, PipelineInfo]:
        _ensure_plugins_loaded()
        if category is None:
            return dict(self._pipelines)
        return {name: info for name, info in self._pipelines.items() if info.category == category}

    def build_ir(self, name: str, **kwargs: Any) -> IR:
        """Build an IR for a registered pipeline."""
        info = self.get(name)
        result = info.factory(**kwargs)

        if isinstance(result, IR):
            return result
        if isinstance(result, PipelineBuilder):
            return result.validate()
        
        # Support Pipeline objects (via duck typing or direct import)
        if hasattr(result, "validate") and hasattr(result, "_build_ir"):
             return result.validate()

        raise TypeError(
            f"Pipeline factory '{name}' returned unsupported type: {type(result)} "
            "(expected IR, PipelineBuilder, or Pipeline)"
        )

    def build_surface(self, name: str, **kwargs: Any) -> PipelineSurface:
        """Build a flow-like surface from a registered pipeline."""
        info = self.get(name)
        ir = self.build_ir(name, **kwargs)
        return _build_pipeline_surface_from_ir(
            ir,
            surface_policy=info.surface_policy,
            input_selectors=info.input_ports,
            output_selectors=info.output_ports,
        )


_global_pipeline_registry = PipelineRegistry()


def register_pipeline(
    name: str,
    *,
    category: str = "general",
    description: str = "",
    tags: Optional[Iterable[str]] = None,
    surface_policy: Literal["auto_unused", "explicit", "none"] = "auto_unused",
    input_ports: Optional[Iterable[str]] = None,
    output_ports: Optional[Iterable[str]] = None,
    overwrite: bool = False,
) -> Callable[[PipelineFactory], PipelineFactory]:
    """
    Decorator to register a pipeline factory.

    Surface controls:
      - `surface_policy="auto_unused"`: expose unconnected non-internal ports
      - `surface_policy="explicit"`: expose only selectors from `input_ports`
        / `output_ports`, using `FlowClass.port`
      - `surface_policy="none"`: do not expose a flow-like surface

    Example:
        @register_pipeline("perception_demo", category="examples")
        def build() -> IR:
            with FlowContext("perception_demo") as ctx:
                ...
                return validate(ctx)
    """

    def decorator(factory: PipelineFactory) -> PipelineFactory:
        _global_pipeline_registry.register(
            name,
            factory,
            category=category,
            description=description,
            tags=tags,
            surface_policy=surface_policy,
            input_ports=input_ports,
            output_ports=output_ports,
            overwrite=overwrite,
        )
        return factory

    return decorator


def get_pipeline_info(name: str) -> PipelineInfo:
    """Return pipeline metadata for a registered pipeline."""
    return _global_pipeline_registry.get(name)


def list_pipelines(category: Optional[str] = None) -> Dict[str, PipelineInfo]:
    """List registered pipelines."""
    return _global_pipeline_registry.list(category=category)


def build_ir(name: str, **kwargs: Any) -> IR:
    """Build a pipeline IR by name."""
    return _global_pipeline_registry.build_ir(name, **kwargs)


def build_pipeline_surface(name: str, **kwargs: Any) -> PipelineSurface:
    """Infer the external flow-like surface for a registered pipeline."""
    return _global_pipeline_registry.build_surface(name, **kwargs)


def get_pipeline(name: str, **kwargs: Any) -> IR:
    """
    Backward-compatible alias for `build_ir`.

    Historically, `get_pipeline(...)` returned a "pipeline instance" in an older
    API. In the refactored runtime, pipelines are built as `IR`.
    """
    return build_ir(name, **kwargs)


def get_pipeline_factory(name: str) -> PipelineFactory:
    """Return the underlying pipeline factory callable."""
    return _global_pipeline_registry.get(name).factory


def find_pipelines(
    *,
    category: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
) -> Dict[str, PipelineInfo]:
    """Find pipelines by simple metadata filters."""
    pipelines = list_pipelines(category=category)
    if not tags:
        return pipelines

    wanted = set(tags)
    return {name: info for name, info in pipelines.items() if wanted.issubset(set(info.tags))}


def run_pipeline(
    name: str,
    *,
    backend: str = "dora",
    duration: Optional[float] = None,
    blocking: bool = True,
    backend_config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
):
    """Convenience helper: build IR then execute it."""
    from retriever.rt.runtime import execute_ir

    ir = build_ir(name, **kwargs)
    return execute_ir(
        ir,
        backend=backend,
        duration=duration,
        blocking=blocking,
        backend_config=backend_config,
    )


def get_global_pipeline_registry() -> PipelineRegistry:
    return _global_pipeline_registry


def _build_pipeline_surface_from_ir(
    ir: IR,
    *,
    surface_policy: Literal["auto_unused", "explicit", "none"],
    input_selectors: Tuple[str, ...],
    output_selectors: Tuple[str, ...],
) -> PipelineSurface:
    if surface_policy == "none":
        return PipelineSurface()

    if surface_policy == "explicit":
        return PipelineSurface(
            inputs=tuple(_resolve_surface_selector(ir, selector, direction="input") for selector in input_selectors),
            outputs=tuple(_resolve_surface_selector(ir, selector, direction="output") for selector in output_selectors),
        )

    incoming = {
        (edge.destination.node, IR.get_logical_port(edge.destination.port))
        for edge in ir.edges
        if not IR.get_logical_port(edge.destination.port).startswith("_")
    }
    outgoing = {
        (edge.source.node, IR.get_logical_port(edge.source.port))
        for edge in ir.edges
        if not IR.get_logical_port(edge.source.port).startswith("_")
    }

    inputs: list[PipelineSurfacePort] = []
    outputs: list[PipelineSurfacePort] = []
    for node in ir.nodes:
        for port, port_type in node.inputs.items():
            if port.startswith("_"):
                continue
            if (node.id, port) not in incoming:
                inputs.append(
                    PipelineSurfacePort(
                        node_id=node.id,
                        node_type=node.type,
                        port=port,
                        type=port_type,
                        direction="input",
                    )
                )
        for port, port_type in node.outputs.items():
            if port.startswith("_"):
                continue
            if (node.id, port) not in outgoing:
                outputs.append(
                    PipelineSurfacePort(
                        node_id=node.id,
                        node_type=node.type,
                        port=port,
                        type=port_type,
                        direction="output",
                    )
                )
    return PipelineSurface(inputs=tuple(inputs), outputs=tuple(outputs))


def _resolve_surface_selector(
    ir: IR,
    selector: str,
    *,
    direction: Literal["input", "output"],
) -> PipelineSurfacePort:
    if "." not in selector:
        raise ValueError(
            f"Invalid pipeline surface selector '{selector}'. "
            "Expected 'FlowClass.port'."
        )
    node_type, port = selector.split(".", 1)
    matches = []
    for node in ir.nodes:
        port_map = node.inputs if direction == "input" else node.outputs
        if node.type == node_type and port in port_map:
            matches.append(
                PipelineSurfacePort(
                    node_id=node.id,
                    node_type=node.type,
                    port=port,
                    type=port_map[port],
                    direction=direction,
                )
            )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"Pipeline surface selector '{selector}' did not match any {direction} port.")
    raise ValueError(
        f"Pipeline surface selector '{selector}' is ambiguous. "
        f"Matches: {[match.node_id for match in matches]}"
    )
