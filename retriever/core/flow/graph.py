"""
FlowGraph - Directed graph for Flow connections

Port-level connections with explicit field names.
"""

from dataclasses import dataclass
from typing import Dict, List, Type, Optional, Any

from retriever.core.error import ErrCode, FlowError

import logging
logger = logging.getLogger(__name__)


@dataclass
class FlowNode:
    """
    Node representing a Flow in the graph.

    Attributes:
        node_id: Unique identifier for the node
        input_ports: Dict mapping input port names to their types
        output_ports: Dict mapping output port names to their types
    """
    node_id: str
    input_ports: Dict[str, Type]
    output_ports: Dict[str, Type]

    def __repr__(self) -> str:
        return (
            f"FlowNode(node_id='{self.node_id}', "
            f"inputs={list(self.input_ports.keys())}, "
            f"outputs={list(self.output_ports.keys())})"
        )

    def get_input_port_names(self) -> List[str]:
        """Get list of input port names"""
        return list(self.input_ports.keys())

    def get_output_port_names(self) -> List[str]:
        """Get list of output port names"""
        return list(self.output_ports.keys())

    def has_input_port(self, port_name: str) -> bool:
        """Check if node has input port with given name"""
        return port_name in self.input_ports

    def has_output_port(self, port_name: str) -> bool:
        """Check if node has output port with given name"""
        return port_name in self.output_ports


@dataclass
class FlowEdge:
    """
    Edge connecting two node ports in the graph.

    Attributes:
        src_node: Source node ID
        src_port: Source port name
        dst_node: Destination node ID
        dst_port: Destination port name
        adapter: Adapter config as {adapter_name: adapter_dict}
        qsize: Queue size for buffering
    """
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str
    adapter: Dict[str, Any]
    qsize: int

    def __repr__(self) -> str:
        adapter_name = next(iter(self.adapter.keys()))
        return (
            f"{self.src_node}.{self.src_port} → {self.dst_node}.{self.dst_port} "
            f"[{adapter_name}, q={self.qsize}]"
        )

    def __eq__(self, other) -> bool:
        """Check edge equality based on connection"""
        if not isinstance(other, FlowEdge):
            return False
        return (
            self.src_node == other.src_node and
            self.src_port == other.src_port and
            self.dst_node == other.dst_node and
            self.dst_port == other.dst_port
        )

    def __hash__(self) -> int:
        """Compute edge hash based on connection"""
        return hash((self.src_node, self.src_port, self.dst_node, self.dst_port))


class FlowGraph:
    """
    Directed graph with port-level connections.

    Built incrementally by FlowContext during Flow connections.

    Structure:
        - nodes: Dict[node_id, FlowNode]
        - edges: List[FlowEdge]
    """

    def __init__(self):
        """Initialize empty graph"""
        self.nodes: Dict[str, FlowNode] = {}
        self.edges: List[FlowEdge] = []

    # ========================================================================
    # Graph Construction
    # ========================================================================

    def add_node(
        self,
        node_id: str,
        input_ports: Dict[str, Type],
        output_ports: Dict[str, Type],
    ) -> FlowNode:
        """Add a flow node to the graph"""
        # Check for duplicate node
        if node_id in self.nodes:
            logger.warning(f"Skipped node '{node_id}' already exists in graph")
            return self.nodes[node_id]

        node = FlowNode(
            node_id=node_id,
            input_ports=input_ports,
            output_ports=output_ports,
        )

        self.nodes[node_id] = node
        return node

    def connect(
        self,
        src_node: str,
        src_port: str,
        dst_node: str,
        dst_port: str,
        adapter: Dict[str, Any],
        qsize: int,
    ) -> FlowEdge:
        """Create port-to-port connection"""
        # Validate nodes exist
        if src_node not in self.nodes:
            raise FlowError(
                ErrCode.FLOW_GRAPH_NODE_NOT_FOUND,
                f"Source node '{src_node}' not found"
            )
        if dst_node not in self.nodes:
            raise FlowError(
                ErrCode.FLOW_GRAPH_NODE_NOT_FOUND,
                f"Destination node '{dst_node}' not found"
            )

        src = self.nodes[src_node]
        dst = self.nodes[dst_node]

        # Validate ports exist
        if not src.has_output_port(src_port):
            raise FlowError(
                ErrCode.FLOW_GRAPH_PORT_NOT_FOUND,
                f"Port '{src_port}' not in outputs of {src_node}. "
                f"Available: {src.get_output_port_names()}"
            )
        if not dst.has_input_port(dst_port):
            raise FlowError(
                ErrCode.FLOW_GRAPH_PORT_NOT_FOUND,
                f"Port '{dst_port}' not in inputs of {dst_node}. "
                f"Available: {dst.get_input_port_names()}"
            )

        # Create edge
        edge = FlowEdge(
            src_node=src_node,
            src_port=src_port,
            dst_node=dst_node,
            dst_port=dst_port,
            adapter=adapter,
            qsize=qsize,
        )

        # Check for duplicate edge
        if edge in self.edges:
            logger.warning(f"Skipped edge '{edge!r}' already exists in graph")
            return edge

        self.edges.append(edge)
        return edge

    # ========================================================================
    # Graph Queries
    # ========================================================================

    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node exists in graph"""
        return node_id in self.nodes

    def get_node_count(self) -> int:
        """Get number of nodes"""
        return len(self.nodes)

    def get_edge_count(self) -> int:
        """Get number of edges"""
        return len(self.edges)

    def get_outgoing_edges(self, node_id: str) -> List[FlowEdge]:
        """Get all edges going out from a node"""
        return [edge for edge in self.edges if edge.src_node == node_id]

    def get_incoming_edges(self, node_id: str) -> List[FlowEdge]:
        """Get all edges coming into a node"""
        return [edge for edge in self.edges if edge.dst_node == node_id]

    def get_successors(self, node_id: str) -> List[str]:
        """Get all nodes directly connected from this node"""
        successors = []
        for edge in self.edges:
            if edge.src_node == node_id and edge.dst_node not in successors:
                successors.append(edge.dst_node)
        return successors

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get all nodes directly connected to this node"""
        predecessors = []
        for edge in self.edges:
            if edge.dst_node == node_id and edge.src_node not in predecessors:
                predecessors.append(edge.src_node)
        return predecessors

    # ========================================================================
    # Topology Analysis
    # ========================================================================

    def find_sources(self) -> List[str]:
        """Find all source nodes (no incoming edges)"""
        has_incoming = {edge.dst_node for edge in self.edges}
        return [nid for nid in self.nodes if nid not in has_incoming]

    def find_sinks(self) -> List[str]:
        """Find all sink nodes (no outgoing edges)"""
        has_outgoing = {edge.src_node for edge in self.edges}
        return [nid for nid in self.nodes if nid not in has_outgoing]

    def is_empty(self) -> bool:
        """Check if graph has no nodes"""
        return len(self.nodes) == 0

    def is_connected(self) -> bool:
        """Check if graph is weakly connected"""
        if self.is_empty():
            return True

        # Start from arbitrary node
        start = next(iter(self.nodes))
        visited = set()
        stack = [start]

        # Traverse bidirectionally
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self.get_successors(node))
            stack.extend(self.get_predecessors(node))

        return len(visited) == len(self.nodes)

    def has_cycles(self) -> bool:
        """Check if graph contains cycles"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self.nodes}

        def dfs(node: str) -> bool:
            """DFS helper - returns True if cycle found"""
            color[node] = GRAY

            for successor in self.get_successors(node):
                if color[successor] == GRAY:
                    return True  # cycle detected
                if color[successor] == WHITE:
                    if dfs(successor):
                        return True

            color[node] = BLACK
            return False

        # Check all components
        for node in self.nodes:
            if color[node] == WHITE:
                if dfs(node):
                    return True

        return False

    # ========================================================================
    # Visualization
    # ========================================================================

    def visualize(self) -> str:
        """
        Create text visualization of the graph.

        All fields are Optional in the new @flow_io design.

        Example output:
            FlowGraph:

              Nodes (2):
                sensor_0
                  inputs: []
                  outputs: ['image', 'depth']
                detector_0
                  inputs: ['camera']
                  outputs: ['detection']

              Edges (1):
                sensor_0.image → detector_0.camera

              Sources: ['sensor_0']

              Sinks: ['detector_0']
        """
        lines = ["FlowGraph:"]

        # Nodes
        lines.append(f"\n  Nodes ({len(self.nodes)}):")
        for node_id, node in self.nodes.items():
            inputs = node.get_input_port_names()
            outputs = node.get_output_port_names()

            lines.append(f"    {node_id}")
            lines.append(f"      inputs: {inputs}")
            lines.append(f"      outputs: {outputs}")

        # Edges
        lines.append(f"\n  Edges ({len(self.edges)}):")
        for edge in self.edges:
            lines.append(f"    {edge}")

        # Topology
        lines.append(f"\n  Sources: {self.find_sources()}")
        lines.append(f"\n  Sinks: {self.find_sinks()}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"FlowGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"

    def __str__(self) -> str:
        return self.visualize()
