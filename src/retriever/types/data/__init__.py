"""Canonical data/event type surface.

Keep the package root narrow:
- import core contracts from `retriever.types.data`
- import operators/helpers from explicit submodules:
  - `retriever.types.data.streams`
  - `retriever.types.data.dataset`
  - `retriever.types.data.interop`

This keeps the public front door type-first instead of turning it into a mixed
bag of contracts, operators, and export helpers.
"""

from __future__ import annotations

from . import dataset, interop, streams, v1
from .v1 import (
    DataSpec,
    DatasetManifest,
    EpisodeManifest,
    Event,
    EventBuffer,
    EventRef,
    FieldSpec,
    JoinMode,
    JoinPolicy,
    LineageRef,
    MultiStreamBuffer,
    StreamSpec,
    WatermarkPolicy,
    WindowAgg,
    WindowPolicy,
)

__all__ = [
    "DataSpec",
    "DatasetManifest",
    "EpisodeManifest",
    "Event",
    "EventBuffer",
    "EventRef",
    "FieldSpec",
    "JoinMode",
    "JoinPolicy",
    "LineageRef",
    "MultiStreamBuffer",
    "StreamSpec",
    "WatermarkPolicy",
    "WindowAgg",
    "WindowPolicy",
    "dataset",
    "interop",
    "streams",
    "v1",
]
