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


from typing import Any, Optional, Union
from retriever.config import RecordConfig, set_global_config

def init(
    name: Optional[str] = None,
    record: Optional[Union[str, RecordConfig]] = None,
    backend: Optional[str] = None,
    default_sync: Optional[Any] = None,
) -> None:
    """
    Initialize the global retriever environment.

    Args:
        name: Session name (useful for logging/recording)
        record: Recording path (str) or configuration (RecordConfig)
        backend: Default backend for run() (e.g. "multiprocessing", "dora")
        default_sync: Default sync adapter for connections (e.g. Latest()).
                      If None, every pipe.connect() must specify sync= explicitly.
    """
    set_global_config(name=name, record=record, backend=backend, default_sync=default_sync)


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
]

