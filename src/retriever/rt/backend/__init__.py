"""
Backend abstraction layer for retriever runtime system.

Provides pluggable execution backends for dataflow pipelines:
- multiprocessing: Local execution with Python multiprocessing and Queue-based IPC
- dora: Distributed execution with dora-rs runtime and Apache Arrow zero-copy IPC

Architecture:
- ExecutionEngine: Manages backend lifecycle (build, start, stop, wait)
- Executor: Per-node process that runs flow logic in isolation
- Publisher/Subscriber: IPC abstractions for inter-node communication
- Scheduler: Determines execution timing (Rate/Trigger/Hybrid)
- BackendFactory: Creates backend-specific engine instances
"""

from retriever.rt.backend.interface import (
    ExecutionEngine,
    Executor,
    Publisher,
    Subscriber,
    Scheduler,
    ScheduleResult,
    BackendFactory,
)
from retriever.rt.backend.factory import (
    register_backend,
    get_backend,
    list_backends,
)

__all__ = [
    # Core interfaces
    'ExecutionEngine',
    'Executor',
    'Publisher',
    'Subscriber',
    'Scheduler',
    'ScheduleResult',
    'BackendFactory',
    # Factory functions
    'register_backend',
    'get_backend',
    'list_backends',
]
