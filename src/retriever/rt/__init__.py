"""
RT Layer - Runtime execution system for dataflow pipelines.

Provides backend-agnostic execution of validated IR (Intermediate Representation)
with pluggable backend support:

- multiprocessing: Local execution with Python multiprocessing
- dora: Distributed execution with dora-rs runtime

Main entry point:
- execute_ir(ir, backend='multiprocessing', duration=None, blocking=True)
  Execute IRStruct or load from file path, returns ExecutionEngine instance

Components:
- runtime: High-level execution API (execute_ir)
- backend: Pluggable execution backends (multiprocessing, dora)
- executor: Per-node process execution logic
- signal: FRP-style data pipeline (sample → transform → publish)
- loader: IR deserialization utilities
"""

from retriever.rt.runtime import execute_ir
from retriever.rt.frp import Behavior, EventStream

__all__ = [
    "execute_ir",
    "Behavior",
    "EventStream",
]
