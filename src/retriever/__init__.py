"""Top-level convenience surface for Retriever.

`retriever` re-exports the most common runtime/core entry points so notebooks and
small scripts can stay terse. The preferred explicit surfaces still live in:

- `retriever.flow` for authoring `Flow` and `Pipeline`
- `retriever.rt` for backend execution
- `retriever.registry` for discoverable flows, pipelines, and types
- `retriever.types` for shared payload and contract definitions
"""

from importlib.metadata import PackageNotFoundError, version as _package_version

try:
    __version__ = _package_version("retriever")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

from retriever.flow import Flow, Rate, Clock
from retriever.flow.adapter import Latest
from retriever.flow.pipeline import (
    Pipeline,
    connect,
    default_pipeline,
    reset_default_pipeline,
    run,
    step,
    reset,
    view,
)
from retriever.flow.functional import clear_default_pipeline
from retriever.flow import io, TemporalFlow, PipelineBuilder


from typing import Any, Optional, Union
from retriever.config import RecordConfig, VizConfig, set_global_config

def init(
    name: Optional[str] = None,
    record: Optional[Union[str, RecordConfig]] = None,
    backend: Optional[str] = None,
    backend_config: Optional[dict] = None,
    default_sync: Optional[Any] = None,
    default_viz: Optional[VizConfig] = None,
) -> None:
    """
    Set process-wide default configuration for convenience helpers.

    `retriever.init(...)` only updates global defaults used by the thread-local
    default pipeline and by `Pipeline.connect(...)` when `sync=` is omitted.
    It does not build, reset, or run a pipeline by itself. For scripts and shared
    examples, prefer an explicit `Pipeline(...)` object and pass runtime settings
    directly to `pipe.run(...)`.

    Args:
        name: Session name (useful for logging/recording)
        record: Recording path (str) or configuration (RecordConfig)
        backend: Default backend for `pipe.run()` / `retriever.run()`
                 (e.g. "multiprocessing", "dora")
        backend_config: Default backend configuration dict. Values are merged
                        with (and overridden by) `pipe.run(backend_config=...)`.
        default_sync: Default sync adapter for connections (e.g. Latest()).
                      If None, every pipe.connect() must specify sync= explicitly.
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
from retriever import hub  # noqa: F401
# Import built-in domain typing packages so registry lookups are stable after plain `import retriever`.
from retriever.types import data as _data  # noqa: F401
from retriever.types import spatial as _spatial  # noqa: F401

__all__ = [
    "Flow",
    "Rate",
    "Clock",
    "Latest",
    "Pipeline",
    "connect",
    "default_pipeline",
    "clear_default_pipeline",
    "run",
    "step",
    "reset",
    "view",
    "init",
    "RecordConfig",
    "VizConfig",
    "io",
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
