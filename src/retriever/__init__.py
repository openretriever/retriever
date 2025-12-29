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


from typing import Optional, Union
from retriever.config import RecordConfig, set_global_config

def init(
    name: Optional[str] = None,
    record: Optional[Union[str, RecordConfig]] = None,
    backend: Optional[str] = None,
) -> None:
    """
    Initialize the global retriever environment.
    
    Args:
        name: Session name (useful for logging/recording)
        record: Recording path (str) or configuration (RecordConfig)
        backend: Default backend for run() (e.g. "multiprocessing", "in-process")
    """
    set_global_config(name=name, record=record, backend=backend)

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

