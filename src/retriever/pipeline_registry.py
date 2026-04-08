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

import keyword
import re
import time
from dataclasses import dataclass, field, make_dataclass, replace
from typing import Any, Callable, Dict, Optional, Union, Iterable, Tuple, Literal, Type

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
    external_name: str = ""


@dataclass(frozen=True)
class PipelineSurface:
    """Flow-like external port surface for a registered pipeline."""

    inputs: Tuple[PipelineSurfacePort, ...] = field(default_factory=tuple)
    outputs: Tuple[PipelineSurfacePort, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PipelineSurfaceBinding:
    """Resolved runtime binding for one surfaced port."""

    surface_port: PipelineSurfacePort
    python_type: Type[Any] | Any = Any


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
            return result.validate(lower_composite_flows=True)

        # Support Pipeline objects (via duck typing or direct import)
        if hasattr(result, "validate") and hasattr(result, "_build_ir"):
            return result.validate(lower_composite_flows=True)

        raise TypeError(
            f"Pipeline factory '{name}' returned unsupported type: {type(result)} "
            "(expected IR, PipelineBuilder, or Pipeline)"
        )

    def build_surface(self, name: str, **kwargs: Any) -> PipelineSurface:
        """Build a flow-like surface from a registered pipeline."""
        info = self.get(name)
        result = info.factory(**kwargs)
        if isinstance(result, IR):
            ir = result
        elif isinstance(result, PipelineBuilder):
            ir = result.validate(lower_composite_flows=False)
        elif hasattr(result, "validate") and hasattr(result, "_build_ir"):
            ir = result.validate(lower_composite_flows=False)
        else:
            raise TypeError(
                f"Pipeline factory '{name}' returned unsupported type: {type(result)} "
                "(expected IR, PipelineBuilder, or Pipeline)"
            )
        return _build_pipeline_surface_from_ir(
            ir,
            surface_policy=info.surface_policy,
            input_selectors=info.input_ports,
            output_selectors=info.output_ports,
        )

    def build_flow(self, name: str, **kwargs: Any):
        """Build an in-process composite Flow wrapper from a registered pipeline."""
        info = self.get(name)
        live_ctx = _build_live_pipeline_context(info, **kwargs)
        ir = live_ctx.validate(lower_composite_flows=False)
        surface = _build_pipeline_surface_from_ir(
            ir,
            surface_policy=info.surface_policy,
            input_selectors=info.input_ports,
            output_selectors=info.output_ports,
        )
        return _build_pipeline_flow_from_surface(name, live_ctx, surface, ir)


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
        / `output_ports`, using `flow_id.port`
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


def build_pipeline_flow(name: str, **kwargs: Any):
    """Build an in-process composite Flow from a registered pipeline surface."""
    return _global_pipeline_registry.build_flow(name, **kwargs)


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
        return _with_external_names(PipelineSurface(
            inputs=tuple(_resolve_surface_selector(ir, selector, direction="input") for selector in input_selectors),
            outputs=tuple(_resolve_surface_selector(ir, selector, direction="output") for selector in output_selectors),
        ))

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
    return _with_external_names(PipelineSurface(inputs=tuple(inputs), outputs=tuple(outputs)))


def _resolve_surface_selector(
    ir: IR,
    selector: str,
    *,
    direction: Literal["input", "output"],
) -> PipelineSurfacePort:
    if "." not in selector:
        raise ValueError(
            f"Invalid pipeline surface selector '{selector}'. "
            "Expected 'flow_id.port'. Named flow selectors like 'camera.image' are preferred; "
            "a bare FlowClass fallback only works when unique."
        )
    node_selector, port = selector.rsplit(".", 1)
    direct_match: PipelineSurfacePort | None = None
    fallback_matches = []
    for node in ir.nodes:
        port_map = node.inputs if direction == "input" else node.outputs
        if port not in port_map:
            continue
        surface_port = PipelineSurfacePort(
            node_id=node.id,
            node_type=node.type,
            port=port,
            type=port_map[port],
            direction=direction,
        )
        if node.id == node_selector:
            direct_match = surface_port
            break
        if node.type == node_selector:
            fallback_matches.append(surface_port)
    if direct_match is not None:
        return direct_match
    if len(fallback_matches) == 1:
        return fallback_matches[0]
    if not fallback_matches:
        available = sorted(node.id for node in ir.nodes)
        raise ValueError(
            f"Pipeline surface selector '{selector}' did not match any {direction} port. "
            f"Available flow ids: {available}"
        )
    raise ValueError(
        f"Pipeline surface selector '{selector}' is ambiguous. "
        f"Matches: {[match.node_id for match in fallback_matches]}. "
        "Use a stable flow id/name in the selector."
    )


def _with_external_names(surface: PipelineSurface) -> PipelineSurface:
    return PipelineSurface(
        inputs=_assign_external_names(surface.inputs),
        outputs=_assign_external_names(surface.outputs),
    )


def _assign_external_names(
    ports: Tuple[PipelineSurfacePort, ...],
) -> Tuple[PipelineSurfacePort, ...]:
    taken: set[str] = set()
    named: list[PipelineSurfacePort] = []

    for port in ports:
        raw = port.port.replace(".", "__")
        candidates = [
            _sanitize_identifier(raw),
            _sanitize_identifier(f"{port.node_id}__{raw}"),
            _sanitize_identifier(f"{port.node_type}__{raw}"),
        ]
        chosen = ""
        for candidate in candidates:
            if candidate and candidate not in taken:
                chosen = candidate
                break
        if not chosen:
            base = candidates[-1] or "port"
            suffix = 2
            chosen = base
            while chosen in taken:
                chosen = f"{base}__{suffix}"
                suffix += 1
        taken.add(chosen)
        named.append(replace(port, external_name=chosen))

    return tuple(named)


def _sanitize_identifier(name: str) -> str:
    candidate = re.sub(r"\W", "_", name)
    if not candidate:
        candidate = "port"
    if candidate[0].isdigit():
        candidate = f"_{candidate}"
    if keyword.iskeyword(candidate):
        candidate = f"{candidate}_"
    return candidate


def _build_live_pipeline_context(info: PipelineInfo, **kwargs: Any):
    result = info.factory(**kwargs)
    if isinstance(result, IR):
        raise TypeError(
            f"Pipeline factory '{info.name}' returned IR only. "
            "build_pipeline_flow(...) requires a live Pipeline or PipelineBuilder."
        )
    if isinstance(result, PipelineBuilder):
        return result
    if (
        hasattr(result, "validate")
        and hasattr(result, "get_handle_for_node")
        and hasattr(result, "get_node_id")
    ):
        return result
    raise TypeError(
        f"Pipeline factory '{info.name}' returned unsupported type for flow wrapping: {type(result)}. "
        "Expected PipelineBuilder or Pipeline-like object."
    )


def _get_builder(ctx: Any) -> PipelineBuilder:
    builder = getattr(ctx, "_builder", ctx)
    if not hasattr(builder, "_extract_ports"):
        raise TypeError("Live pipeline context does not expose builder port extraction.")
    return builder


def _build_surface_bindings(
    ctx: Any,
    surface: PipelineSurface,
) -> Tuple[Tuple[PipelineSurfaceBinding, ...], Tuple[PipelineSurfaceBinding, ...]]:
    builder = _get_builder(ctx)
    input_bindings: list[PipelineSurfaceBinding] = []
    output_bindings: list[PipelineSurfaceBinding] = []

    for port in surface.inputs:
        handle = ctx.get_handle_for_node(port.node_id)
        port_types = builder._extract_ports(handle.flow.input_types)
        input_bindings.append(
            PipelineSurfaceBinding(surface_port=port, python_type=port_types.get(port.port, Any))
        )

    for port in surface.outputs:
        handle = ctx.get_handle_for_node(port.node_id)
        port_types = builder._extract_ports(handle.flow.output_types)
        output_bindings.append(
            PipelineSurfaceBinding(surface_port=port, python_type=port_types.get(port.port, Any))
        )

    return tuple(input_bindings), tuple(output_bindings)


def _build_pipeline_viz_metadata(name: str, ir: IR, surface: PipelineSurface) -> Dict[str, Any]:
    internal_edges = [
        {
            "source": edge.source.node,
            "source_port": IR.get_logical_port(edge.source.port),
            "destination": edge.destination.node,
            "destination_port": IR.get_logical_port(edge.destination.port),
        }
        for edge in ir.edges
        if not IR.get_logical_port(edge.source.port).startswith("_")
        and not IR.get_logical_port(edge.destination.port).startswith("_")
    ]
    return {
        "kind": "pipeline",
        "pipeline_name": name,
        "summary": {
            "node_count": len(ir.nodes),
            "edge_count": len(internal_edges),
        },
        "surface": {
            "inputs": [
                {
                    "external_name": port.external_name,
                    "node_id": port.node_id,
                    "node_type": port.node_type,
                    "port": port.port,
                    "type": port.type,
                }
                for port in surface.inputs
            ],
            "outputs": [
                {
                    "external_name": port.external_name,
                    "node_id": port.node_id,
                    "node_type": port.node_type,
                    "port": port.port,
                    "type": port.type,
                }
                for port in surface.outputs
            ],
        },
        "internal": {
            "nodes": [{"id": node.id, "type": node.type} for node in ir.nodes],
            "edges": internal_edges,
        },
    }


def _make_surface_io_type(
    name: str,
    bindings: Tuple[PipelineSurfaceBinding, ...],
) -> Optional[Type[Any]]:
    if not bindings:
        return None

    from dataclasses import field as dc_field
    from retriever.flow import io

    fields_spec = [
        (binding.surface_port.external_name, binding.python_type, dc_field(default=None))
        for binding in bindings
    ]
    return io(make_dataclass(name, fields_spec))


def _build_pipeline_flow_from_surface(
    name: str,
    ctx: Any,
    surface: PipelineSurface,
    ir: IR,
):
    from retriever.flow import Flow
    from retriever.rt.stepper import PipelineStepper, current_step_time

    input_bindings, output_bindings = _build_surface_bindings(ctx, surface)
    class_stem = _sanitize_identifier(name.title())
    input_type = _make_surface_io_type(f"{class_stem}Input", input_bindings)
    output_type = _make_surface_io_type(f"{class_stem}Output", output_bindings)
    pipeline_viz = _build_pipeline_viz_metadata(name, ir, surface)

    base = Flow[input_type or None, output_type or None]  # type: ignore[misc]
    output_cache_init = {binding.surface_port.external_name: None for binding in output_bindings}

    class _PipelineFlow(base):
        in_process_only = True

        def __init__(self):
            self._pipeline_flow_wrapper = True
            self._pipeline_flow_context = ctx
            self._pipeline_flow_surface = surface
            self._pipeline_flow_input_bindings = input_bindings
            self._pipeline_flow_output_bindings = output_bindings
            self.context = ctx
            self.surface = surface
            self.input_bindings = input_bindings
            self.output_bindings = output_bindings
            self._stepper = None
            self._output_cache = dict(output_cache_init)

        def init_config(self) -> dict:
            # Validation still needs a serializable placeholder when this wrapper is
            # nested inside a larger in-process Pipeline. Backend execution is blocked
            # separately via the `in_process_only` marker in IR node config.
            return {}

        def viz_metadata(self) -> dict:
            return pipeline_viz

        def _ensure_stepper(self) -> PipelineStepper:
            if self._stepper is None:
                self._stepper = PipelineStepper(ctx)
            return self._stepper

        def reset(self) -> None:
            self._output_cache = dict(output_cache_init)
            if self._stepper is not None:
                self._stepper.reset()

        def finalize(self) -> None:
            if self._stepper is not None:
                self._stepper.close()
                self._stepper = None

        def step(self, input):  # type: ignore[override]
            stepper = self._ensure_stepper()
            step_now = current_step_time() or time.time()

            if input is not None:
                injected: Dict[str, Dict[str, Any]] = {}
                for binding in self.input_bindings:
                    ext = binding.surface_port.external_name
                    if input._has_signal(ext):
                        injected.setdefault(binding.surface_port.node_id, {})[
                            binding.surface_port.port
                        ] = input._get_signal(ext)
                if injected:
                    stepper.inject_inputs(injected, timestamp=step_now)

            result = stepper.step(now=step_now)

            for binding in self.output_bindings:
                node_output = result.outputs.get(binding.surface_port.node_id)
                if node_output is None:
                    continue
                if node_output._has_signal(binding.surface_port.port):
                    self._output_cache[binding.surface_port.external_name] = node_output._get_signal(
                        binding.surface_port.port
                    )

            if output_type is None:
                return None

            payload = {
                key: value for key, value in self._output_cache.items() if value is not None
            }
            return output_type(**payload)

    _PipelineFlow.__name__ = f"{class_stem}Flow"
    return _PipelineFlow()
