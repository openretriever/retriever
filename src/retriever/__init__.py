"""Top-level convenience surface for Retriever.

`retriever` re-exports the most common runtime/core entry points so notebooks and
small scripts can stay terse. The preferred explicit surfaces still live in:

- `retriever.flow` for authoring `Flow` and `Pipeline`
- `retriever.rt` for backend execution
- `retriever.registry` for discoverable flows, pipelines, and types
- `retriever.types` for shared payload and contract definitions
"""

from importlib import import_module
from importlib.metadata import (
    PackageNotFoundError,
    packages_distributions as _packages_distributions,
    version as _package_version,
)
from types import ModuleType


def _resolve_version() -> str:
    # The `retriever` import package may be shipped by more than one
    # distribution (the canonical `retriever-core`, or the interim
    # `debug-retriever` used before the core package is published). Resolve the
    # version from whichever distribution actually installed this package rather
    # than assuming one dist name, so `retriever.__version__` is correct either
    # way. Fall back to a source-tree marker when running uninstalled.
    candidates: list[str] = []
    try:
        candidates = list(_packages_distributions().get("retriever", []))
    except Exception:
        candidates = []
    for dist in [*candidates, "retriever-core"]:
        try:
            return _package_version(dist)
        except PackageNotFoundError:
            continue
    return "0.0.0+local"


__version__ = _resolve_version()

from retriever.flow import Flow, Rate, Clock, Trigger, Hybrid, Tick
from retriever.flow.adapter import Latest, Hold, Window, Events
from retriever.flow.pipeline import (
    Pipeline,
    clear_default_pipeline,
    connect,
    default_pipeline,
    reset_default_pipeline,
    run,
    step,
    reset,
    view,
)
from retriever.flow import io, TemporalFlow, PipelineBuilder, compose, select


from typing import Any, Optional, Union
from retriever.config import RecordConfig, VizConfig, _UNSET as _CONFIG_UNSET, set_global_config

def init(
    name: Optional[str] | object = _CONFIG_UNSET,
    record: Optional[Union[str, RecordConfig]] | object = _CONFIG_UNSET,
    backend: Optional[str] | object = _CONFIG_UNSET,
    backend_config: Optional[dict] | object = _CONFIG_UNSET,
    default_sync: Optional[Any] | object = _CONFIG_UNSET,
    default_viz: Optional[VizConfig] | object = _CONFIG_UNSET,
) -> None:
    """
    Set process-wide default configuration for convenience helpers.

    `retriever.init(...)` only updates global defaults used by the thread-local
    default pipeline and by `Pipeline.connect(...)` when `sync=` is omitted.
    Pass `None` explicitly to clear optional defaults like `record`,
    `default_sync`, or `default_viz`. It does not build, reset, or run a
    pipeline by itself. For scripts and shared examples, prefer an explicit
    `Pipeline(...)` object and pass runtime settings directly to `pipe.run(...)`.

    Args:
        name: Session name (useful for logging/recording)
        record: Recording path (str) or configuration (RecordConfig)
        backend: Default backend for `pipe.run()` / `retriever.run()`
                 (e.g. "multiprocessing", "dora")
        backend_config: Default backend configuration dict. Values are merged
                        with (and overridden by) `pipe.run(backend_config=...)`.
        default_sync: Default sync adapter for connections (e.g. Latest()).
                      Pass None explicitly to clear it so every explicit connection
                      must specify sync=.
        default_viz: Default visualization policy for all output ports that do not
                     have an explicit viz= on their .then() connection.
                     Example: retriever.init(default_viz=VizConfig(hz=5.0))
                     enables lightweight visualization across the whole pipeline.
    """
    set_global_config(
        name=name,
        record=record,
        backend=backend,
        backend_config=backend_config,
        default_sync=default_sync,
        default_viz=default_viz,
    )



# Registry Exports
from retriever.registry import (
    register_flow,
    get_flow,
    get_flow_class,
    list_flows,
    find_flows,
    register_pipeline,
    get_pipeline,
    get_pipeline_factory,
    list_pipelines,
    find_pipelines,
    build_ir,
    build_pipeline_flow,
    build_pipeline_surface,
    get_type_info,
    get_registered_types,
    register_type,
    get_type,
    list_types,
    find_types,
    get_type_name,
    resolve_schema_ref,
)

# Import built-in shared schema types so registry lookups are stable after plain `import retriever`.
from retriever.types import ClockDomain as _ClockDomain, SchemaRef as _SchemaRef, StreamId as _StreamId  # noqa: F401
# Import built-in domain typing packages so registry lookups are stable after plain `import retriever`.
from retriever.types import data as _data  # noqa: F401
from retriever.types import spatial as _spatial  # noqa: F401


def __getattr__(name: str) -> ModuleType:
    """Load optional top-level convenience modules on first access."""

    if name == "hub":
        module = import_module("retriever.hub")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Flow",
    "Rate",
    "Clock",
    "Trigger",
    "Hybrid",
    "Tick",
    "Latest",
    "Hold",
    "Window",
    "Events",
    "Pipeline",
    "connect",
    "default_pipeline",
    "reset_default_pipeline",
    "clear_default_pipeline",
    "run",
    "step",
    "reset",
    "view",
    "init",
    "RecordConfig",
    "VizConfig",
    "io",
    "compose",
    "select",
    "TemporalFlow",
    "PipelineBuilder",
    # Registry
    "register_flow",
    "get_flow",
    "get_flow_class",
    "list_flows",
    "find_flows",
    "register_pipeline",
    "get_pipeline",
    "get_pipeline_factory",
    "list_pipelines",
    "find_pipelines",
    "build_ir",
    "build_pipeline_flow",
    "build_pipeline_surface",
    "register_type",
    "get_type",
    "get_type_info",
    "get_registered_types",
    "get_type_name",
    "list_types",
    "find_types",
    "resolve_schema_ref",
    "hub",
]
