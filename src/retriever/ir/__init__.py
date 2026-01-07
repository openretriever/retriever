"""
Retriever Intermediate Representation (IR).

The IR Layer is split into:
1. `retriever.ir.core`: The Logical Representation (`IR`).
2. `retriever.ir.execution`: The Physical Execution Plan (`ExecutionGraph`).

This module exports the high-level classes needed by users and backends.
"""

from retriever.ir.core import (
    IR,
    IRNode,
    IREdge,
    IRAnalysis,
)
from retriever.ir.execution import (
    ExecutionGraph,
    ExecutionPartition,
    ExecutionEdge,
    Placement,
)
from retriever.ir.rules import PlacementRule

__all__ = [
    "IR",
    "IRNode",
    "IREdge",
    "IRAnalysis",
    "ExecutionGraph",
    "ExecutionPartition",
    "ExecutionEdge",
    "Placement",
    "PlacementRule",
]
