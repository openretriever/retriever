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
)
from retriever.types_registry import (
    register_type,
    get_type,
    list_types,
    find_types,
)

# Import built-in robotics typing so registry lookups are stable after plain `import retriever`.
from retriever import robotics_typing as _robotics_typing  # noqa: F401
from retriever import hub  # noqa: F401

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
    "register_type",
    "get_type",
    "list_types",
    "find_types",
    "hub",
]

