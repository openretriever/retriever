"""
Pipeline registry (IR-first).

This registry is designed for the refactored runtime:
  FlowContext -> validate(...) -> IRStruct -> execute_ir(...)

It registers *pipeline factories* (callables) that return either:
  - IRStruct (preferred), or
  - FlowContext (will be validated to IRStruct).

This enables:
  - Discoverable pipelines (for a future `retriever` CLI)
  - Plugin-based extensibility via entry points (see `retriever.core.plugins`)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union, Iterable, Tuple

from retriever.core.flow.context import FlowContext
from retriever.core.ir.struct import IRStruct
from retriever.core.utils import load_plugins

PipelineFactory = Callable[..., Union[IRStruct, FlowContext]]


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

    def build_ir(self, name: str, **kwargs: Any) -> IRStruct:
        """Build an IRStruct for a registered pipeline."""
        info = self.get(name)
        result = info.factory(**kwargs)

        if isinstance(result, IRStruct):
            return result
        if isinstance(result, FlowContext):
            return result.validate()

        raise TypeError(
            f"Pipeline factory '{name}' returned unsupported type: {type(result)} "
            "(expected IRStruct or FlowContext)"
        )


_global_pipeline_registry = PipelineRegistry()


def register_pipeline(
    name: str,
    *,
    category: str = "general",
    description: str = "",
    tags: Optional[Iterable[str]] = None,
    overwrite: bool = False,
) -> Callable[[PipelineFactory], PipelineFactory]:
    """
    Decorator to register a pipeline factory.

    Example:
        @register_pipeline("perception_demo", category="examples")
        def build() -> IRStruct:
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


def build_ir(name: str, **kwargs: Any) -> IRStruct:
    """Build a pipeline IRStruct by name."""
    return _global_pipeline_registry.build_ir(name, **kwargs)


def get_pipeline(name: str, **kwargs: Any) -> IRStruct:
    """
    Backward-compatible alias for `build_ir`.

    Historically, `get_pipeline(...)` returned a "pipeline instance" in an older
    API. In the refactored runtime, pipelines are built as `IRStruct`.
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
    backend: str = "multiprocessing",
    duration: Optional[float] = None,
    blocking: bool = True,
    backend_config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
):
    """Convenience helper: build IR then execute it."""
    from retriever.core.rt.runtime import execute_ir

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
