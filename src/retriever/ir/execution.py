"""
Execution graph types (logical IR → physical execution graph).

Retriever distinguishes between:

- Logical graph: `IRStruct` (validated FRP graph: flows + ports + edges)
- Physical graph: `ExecutionGraph` (partitions + placement + cross-partition edges)

Today, the physical graph is primarily used to:
1) group/co-locate flows into fewer runtime executors (legacy: "fusion")
2) attach placement metadata (where a partition should run)

Backends may still consume `IRStruct` directly. `ExecutionGraph.to_execution_ir()`
materializes a backend-friendly `IRStruct` by lowering grouped partitions into
`FusedFlow` nodes (implementation detail).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from retriever.core.ir.struct import IRStruct


@dataclass
class Placement:
    """
    Placement hint for a partition.

    `target` is an opaque label for now (e.g. "local", "robot", "cloud", "gpu-box").
    Backends may ignore it until multi-node deployment is implemented.
    """

    target: str = "local"
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPartition:
    """
    A partition is a physical execution unit.

    For now, partitions are linear chains produced by the current partitioner
    (or singletons for nodes not grouped).
    """

    id: str
    node_ids: List[str]
    placement: Placement = field(default_factory=Placement)


@dataclass
class ExecutionEdge:
    """
    Edge between partitions (physical graph edge).

    `ir_edge_ids` are the logical IR edges that cross this partition boundary.
    """

    id: str
    source: str
    destination: str
    ir_edge_ids: List[str]


@dataclass
class ExecutionGraph:
    """
    Physical execution graph derived from a logical `IRStruct`.

    Attributes:
        ir: The original logical IR.
        partitions: Execution partitions (nodes in the physical graph).
        edges: Cross-partition edges (edges in the physical graph).
        policy: Policy/provenance used to create grouping partitions.
    """

    ir: IRStruct
    partitions: List[ExecutionPartition]
    edges: List[ExecutionEdge]
    policy: Dict[str, Any]

    def partition_for_node(self, node_id: str) -> str:
        """Return partition id containing `node_id`."""
        for part in self.partitions:
            if node_id in part.node_ids:
                return part.id
        raise KeyError(f"Node {node_id!r} not present in execution graph")

    def to_execution_ir(self) -> IRStruct:
        """
        Materialize a backend-friendly IRStruct for execution.

        Current backends operate on an `IRStruct` where each node is a runnable
        executor. We implement this by lowering grouped partitions into a single
        `FusedFlow` node (legacy naming).
        """
        from retriever.core.ir.fusion import apply_fusion

        fusion_groups = [p.node_ids for p in self.partitions if len(p.node_ids) >= 2]
        if not fusion_groups:
            return self.ir
        return apply_fusion(self.ir, fusion_groups, predicate_config=self.policy)
