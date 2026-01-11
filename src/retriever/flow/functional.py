"""
Functional graph-building helpers (optional ergonomics).

This module provides:
- a thread-local default Pipeline for lightweight experiments
- a `connect(...)` function (PyTorch-ish style)

The explicit `Pipeline(...)` authoring surface remains the recommended default
for larger codebases.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, Optional

from retriever.flow.temporal import TemporalFlow
from retriever.flow.pipeline import Pipeline


_default_pipeline: ContextVar[Optional[Pipeline]] = ContextVar(
    "retriever_default_pipeline",
    default=None,
)


def default_pipeline() -> Pipeline:
    """
    Return the thread-local default Pipeline (creating it if needed).

    This is intended for quick experiments where you don't want to explicitly
    pass a Pipeline around.
    """
    pipe = _default_pipeline.get()
    if pipe is None:
        pipe = Pipeline(name="default")
        _default_pipeline.set(pipe)
    return pipe


def reset_default_pipeline() -> Pipeline:
    """
    Reset the thread-local default Pipeline.

    Useful in notebooks/REPLs to avoid accidentally accumulating nodes/edges
    across experiments.
    """
    pipe = Pipeline(name="default")
    _default_pipeline.set(pipe)
    return pipe


def clear_default_pipeline() -> None:
    """Clear the thread-local default Pipeline (next access will recreate it)."""
    _default_pipeline.set(None)


def connect(
    src: TemporalFlow,
    dst: TemporalFlow,
    *,
    map: Optional[Dict[str, str]] = None,
    sync: Optional[Any] = None,
    edge_config: Optional[Dict[str, Any]] = None,
    pipeline: Optional[Pipeline] = None,
) -> TemporalFlow:
    """
    Connect two handles, optionally using a default Pipeline.

    Precedence:
    1) If `pipeline=` is provided: connect into it.
    2) If a PipelineBuilder/Pipeline context is active: delegate to `src.then(...)`.
    3) If either handle is already Pipeline-owned: delegate to `src.then(...)` (will merge).
    4) Otherwise: connect into the thread-local `default_pipeline()`.
    """
    if pipeline is not None:
        pipeline.connect(src, dst, map=map, sync=sync, edge_config=edge_config)
        return dst

    from retriever.flow.builder import PipelineBuilder

    if PipelineBuilder.active() is not None:
        return src.then(dst, map=map, sync=sync, edge_config=edge_config)

    if src.pipeline is not None or dst.pipeline is not None:
        return src.then(dst, map=map, sync=sync, edge_config=edge_config)

    default_pipeline().connect(src, dst, map=map, sync=sync, edge_config=edge_config)
    return dst

