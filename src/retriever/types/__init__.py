"""Retriever type umbrella: shared primitives plus canonical domain packages.

`retriever.types` intentionally stays small:
- shared schema/stream identity primitives: `ClockDomain`, `SchemaRef`, `StreamId`
- lightweight effect/module primitives: `Eff`, `pure`, `Module`
- canonical domain packages:
  - `retriever.types.data`
  - `retriever.types.spatial`
  - `retriever.types.symbolic`

Registry operations live under `retriever.registry.types` and are re-exported
from top-level `retriever`, not from this package.
"""

from .core import Eff, pure, Module
from .schema import ClockDomain, SchemaRef, StreamId
from . import data, spatial, symbolic

__all__ = [
    "ClockDomain",
    "Eff",
    "Module",
    "SchemaRef",
    "StreamId",
    "data",
    "pure",
    "spatial",
    "symbolic",
]
