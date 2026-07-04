"""
Execution Graph & Placement - Physical execution plan and partitioning.

This module defines:
1. `ExecutionGraph`: The physical graph (partitions + cross-edges) derived from a logical IR.
2. `PlacementRule`: Rules for grouping nodes into partitions (e.g. Rate, Compatibility).
3. `partition_chains`: Algorithms to find co-locatable node groups.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

if TYPE_CHECKING:
    from retriever.ir.core import IR, IRAnalysis
    from retriever.ir.rules import PlacementRule

logger = logging.getLogger(__name__)




# ==============================================================================
# Part 1: Physical Graph Structures (formerly execution.py)
# ==============================================================================

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
    Physical execution graph derived from a logical `IR`.

    Attributes:
        ir: The original logical IR.
        partitions: Execution partitions (nodes in the physical graph).
        edges: Cross-partition edges (edges in the physical graph).
        policy: Policy/provenance used to create grouping partitions.
    """

    ir: IR
    partitions: List[ExecutionPartition]
    edges: List[ExecutionEdge]
    policy: Dict[str, Any]

    @classmethod
    def from_ir(cls, ir: IR, policy: Union[str, Dict[str, Any]] = "aggressive") -> "ExecutionGraph":
        """
        Compile Logical IR into an ExecutionGraph.
        
        Args:
            ir: The logical IR to compile.
            policy: Placement/Partitioning policy name or config.
            
        Returns:
            ExecutionGraph: The physical execution plan.
        """
        from retriever.ir.rules import get_placement_rule, RuleConfig

        # 1. Resolve Policy
        if isinstance(policy, str):
            rule_config = RuleConfig.from_preset(policy)
            policy_dict = {"name": policy}
        elif isinstance(policy, dict):
            rule_config = RuleConfig(name=policy.get("name", "aggressive"))
            policy_dict = policy
        else:
            raise TypeError(f"Invalid policy type: {type(policy)}")

        placement_rule = get_placement_rule(rule_config)
        analysis = ir.analysis

        # 2. Partitioning
        partitioner = ChainPartitioner()
        chains = partitioner.partition(ir, analysis, placement_rule)

        # 3. Build Partitions
        partitions: List[ExecutionPartition] = []
        node_to_partition: Dict[str, str] = {}

        # Grouped partitions
        for i, chain in enumerate(chains):
            pid = f"partition_{i}"
            partitions.append(ExecutionPartition(id=pid, node_ids=chain))
            for nid in chain:
                node_to_partition[nid] = pid

        # Remainder (singleton partitions)
        grouped_nodes = set(node_to_partition.keys())
        for node in ir.nodes:
            if node.id not in grouped_nodes:
                pid = f"partition_{node.id}"
                partitions.append(ExecutionPartition(id=pid, node_ids=[node.id]))
                node_to_partition[node.id] = pid

        # 4. Build Cross-Partition Edges
        exec_edges: List[ExecutionEdge] = []
        
        # Map (src_part, dst_part) -> [ir_edge_ids]
        edge_groups: Dict[Tuple[str, str], List[str]] = {}

        for edge in ir.edges:
            src_p = node_to_partition.get(edge.source.node)
            dst_p = node_to_partition.get(edge.destination.node)

            if src_p and dst_p and src_p != dst_p:
                key = (src_p, dst_p)
                if key not in edge_groups:
                    edge_groups[key] = []
                edge_groups[key].append(edge.id)

        for (src_p, dst_p), edge_ids in edge_groups.items():
            exec_edges.append(ExecutionEdge(
                id=f"{src_p}_to_{dst_p}",
                source=src_p,
                destination=dst_p,
                ir_edge_ids=edge_ids
            ))

        return cls(
            ir=ir,
            partitions=partitions,
            edges=exec_edges,
            policy=policy_dict
        )

    def partition_for_node(self, node_id: str) -> str:
        """Return partition id containing `node_id`."""
        for part in self.partitions:
            if node_id in part.node_ids:
                return part.id
        raise KeyError(f"Node {node_id!r} not present in execution graph")

    def to_execution_ir(self) -> IR:
        """
        Materialize a backend-friendly IR for execution.

        Current backends operate on an `IR` where each node is a runnable
        executor. We implement this by lowering grouped partitions into a single
        `FusedFlow` node (legacy naming).
        """
        fusion_groups = [p.node_ids for p in self.partitions if len(p.node_ids) >= 2]
        if not fusion_groups:
            return self.ir
        return self.ir.fuse(fusion_groups, predicate_config=self.policy)


# ==============================================================================
# Part 3: Partitioning Algorithms
# ==============================================================================

class Partitioner(ABC):
    """Abstract base class for graph partitioning strategies."""
    
    @abstractmethod
    def partition(self, ir: IR, analysis: IRAnalysis, rule: PlacementRule) -> List[List[str]]:
        """
        Partition the IR graph into co-located groups.
        
        Args:
            ir: The logical IR to partition.
            analysis: Cached analysis results.
            rule: The placement rule to determine compatibility.
            
        Returns:
            List of node ID groups (inner lists are groups).
        """
        raise NotImplementedError


class ChainPartitioner(Partitioner):
    """
    Partition the graph into maximal linear chains.
    
    This strategy is useful for simple pipelined execution where compatible
    sequences of nodes are fused into single execution units.
    """
    
    def partition(self, ir: IR, analysis: IRAnalysis, rule: PlacementRule) -> List[List[str]]:
        # Build processing order from topological groups
        processing_order = []
        for group in ir.topology.groups:
            processing_order.extend(group)

        visited: Set[str] = set()
        chains: List[List[str]] = []

        for node_id in processing_order:
            if node_id in visited:
                continue

            chain = [node_id]
            current = ir.get_node(node_id)
            if current is None:
                continue

            chain_seen = {node_id}
            while True:
                # Check for linear continuation
                if len(current.successors) != 1:
                    break

                next_id = current.successors[0]
                # Stop on nodes already chained elsewhere, and on cycles
                # (including self-loops) within the current walk.
                if next_id in visited or next_id in chain_seen:
                    break

                if not rule(ir, current.id, next_id, analysis):
                    break

                chain.append(next_id)
                chain_seen.add(next_id)
                current = ir.get_node(next_id)
                if current is None:
                    break

            if len(chain) >= 2:
                chains.append(chain)
                visited.update(chain)

        return chains

# Backward compatibility / Helper
def partition_chains(ir: IR, analysis: IRAnalysis, rule: PlacementRule) -> List[List[str]]:
    """Legacy helper: Use ChainPartitioner."""
    return ChainPartitioner().partition(ir, analysis, rule)
