"""
Retriever: Robot Decision-Making Runtime with Functional Composition.

Core modules:
- flow: Declarative dataflow computation framework
- ir: Intermediate representation for pipeline graphs
- rt: Runtime execution backends
"""

__version__ = "0.0.0"

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
from retriever.flow import io, TemporalFlow, PipelineBuilder


from typing import Any, Optional, Union
from retriever.config import RecordConfig, set_global_config

def init(
    name: Optional[str] = None,
    record: Optional[Union[str, RecordConfig]] = None,
    backend: Optional[str] = None,
    backend_config: Optional[dict] = None,
    default_sync: Optional[Any] = None,
) -> None:
    """
    Initialize the global retriever environment.

    Args:
        name: Session name (useful for logging/recording)
        record: Recording path (str) or configuration (RecordConfig)
        backend: Default backend for run() (e.g. "multiprocessing", "dora")
        backend_config: Default backend configuration dict. Values are merged
                        with (and overridden by) `pipe.run(backend_config=...)`.
        default_sync: Default sync adapter for connections (e.g. Latest()).
                      If None, every pipe.connect() must specify sync= explicitly.
    """
    set_global_config(name=name, record=record, backend=backend, backend_config=backend_config, default_sync=default_sync)



# Registry Exports
from retriever.flow_registry import (
    register_flow,
    get_flow,
    get_flow_class,
    list_flows,
    find_flows,
)
from retriever.pipeline_registry import (
    register_pipeline,
    get_pipeline,
    get_pipeline_factory,
    list_pipelines,
    find_pipelines,
    build_ir,
    build_pipeline_surface,
)
from retriever.types_registry import (
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

__all__ = [
    "Flow",
    "Rate",
    "Clock",
    "Latest",
    "Pipeline",
    "connect",
    "default_pipeline",
    "run",
    "step",
    "reset",
    "view",
    "init",
    "RecordConfig",
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
    "build_pipeline_surface",
    "register_type",
    "get_type",
    "get_type_info",
    "get_registered_types",
    "get_type_name",
    "list_types",
    "find_types",
    "resolve_schema_ref",
]
