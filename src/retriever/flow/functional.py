"""Optional functional wrappers around the default Pipeline convenience surface.

This module intentionally delegates to :mod:`retriever.flow.pipeline` so the
thread-local default pipeline has exactly one implementation.
"""

from __future__ import annotations

from retriever.flow.pipeline import (
    clear_default_pipeline,
    connect,
    default_pipeline,
    reset_default_pipeline,
)

__all__ = [
    "connect",
    "default_pipeline",
    "reset_default_pipeline",
    "clear_default_pipeline",
]
