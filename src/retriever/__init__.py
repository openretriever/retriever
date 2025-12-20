"""
Retriever: Robot Decision-Making Runtime with Functional Composition.

Core modules:
- flow: Declarative dataflow computation framework
- ir: Intermediate representation for pipeline graphs
- rt: Runtime execution backends
"""

__version__ = "0.0.0"

from retriever.flow.pipeline import (
    Pipeline,
    connect,
    default_pipeline,
    reset_default_pipeline,
    run,
    step,
    reset,
)

__all__ = [
    "Pipeline",
    "connect",
    "default_pipeline",
    "reset_default_pipeline",
    "run",
]
