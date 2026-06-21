"""Retriever type umbrella: shared primitives plus lazy domain packages.

`retriever.types` intentionally keeps the import path light:
- shared schema/stream identity primitives: `ClockDomain`, `SchemaRef`, `StreamId`
- lightweight effect/module primitives: `Eff`, `pure`, `Module`
- canonical domain packages loaded on first access:
  - `retriever.types.data`
  - `retriever.types.language`
  - `retriever.types.perception`
  - `retriever.types.spatial`
  - `retriever.types.symbolic`

Registry operations live under `retriever.registry.types` and are re-exported
from top-level `retriever`, not from this package.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

from .core import Eff, Module, pure
from .schema import ClockDomain, SchemaRef, StreamId

_DOMAIN_PACKAGES = {"data", "language", "perception", "spatial", "symbolic"}


def __getattr__(name: str) -> ModuleType:
    """Load optional domain packages only when callers ask for them."""

    if name in _DOMAIN_PACKAGES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ClockDomain",
    "Eff",
    "Module",
    "SchemaRef",
    "StreamId",
    "data",
    "language",
    "perception",
    "pure",
    "spatial",
    "symbolic",
]
