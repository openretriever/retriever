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
        metadata: Edge metadata dict
    """
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str
    metadata: Dict[str, Any]

    def __repr__(self) -> str:
        return f"{self.src_node}.{self.src_port}->{self.dst_node}.{self.dst_port}"

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
        metadata: Dict[str, Any],
    ) -> FlowEdge:
        """Create port-to-port connection with metadata"""
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
            metadata=metadata,
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

    def get_in_degree(self, node_id: str) -> int:
        """Get number of incoming edges to a node"""
        return len(self.get_predecessors(node_id))

    def get_out_degree(self, node_id: str) -> int:
        """Get number of outgoing edges from a node"""
        return len(self.get_successors(node_id))

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

    def get_cycles(self) -> List[List[str]]:
        """
        Get all cycles in the graph.

        Returns SCCs with more than one node (each represents a cycle).
        """
        sccs = self.find_strongly_connected_components()
        return [scc for scc in sccs if len(scc) > 1]

    def find_strongly_connected_components(self) -> List[List[str]]:
        """
        Find strongly connected components using Tarjan's algorithm.

        Returns list of SCCs, where each SCC is a list of node IDs.
        Single-node SCCs represent nodes not in cycles.
        Multi-node SCCs represent cycles.

        Time complexity: O(V + E)
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []

        def strongconnect(node: str):
            """Tarjan's DFS helper"""
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            on_stack[node] = True
            stack.append(node)

            for successor in self.get_successors(node):
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack.get(successor, False):
                    lowlinks[node] = min(lowlinks[node], index[successor])

            if lowlinks[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == node:
                        break
                sccs.append(scc)

        for node in self.nodes:
            if node not in index:
                strongconnect(node)

        return sccs

    def get_topological_groups(self) -> List[List[str]]:
        """
        Get SCCs in topological order, with nodes ordered within each SCC.

        Returns list where each element is a group (SCC) of node IDs:
        - Single-node list: node not in a cycle
        - Multi-node list: nodes in same cycle, ordered by in-degree + DFS

        Example:
            Graph: A -> B <-> C -> D
            Returns: [['A'], ['B', 'C'], ['D']]

        SCCs are ordered topologically (respects inter-SCC dependencies).
        Nodes within each SCC are ordered starting from minimum in-degree node.

        This preserves cycle structure while maintaining topological ordering,
        useful for partition algorithms and visualization.
        """
        sccs = self.find_strongly_connected_components()

        # Create mapping from node to its SCC index
        node_to_scc = {}
        for scc_idx, scc in enumerate(sccs):
            for node in scc:
                node_to_scc[node] = scc_idx

        # Build condensed graph (edges between SCCs)
        scc_successors = {i: set() for i in range(len(sccs))}
        for edge in self.edges:
            src_scc = node_to_scc[edge.src_node]
            dst_scc = node_to_scc[edge.dst_node]
            if src_scc != dst_scc:
                scc_successors[src_scc].add(dst_scc)

        # Topologically sort SCCs using DFS
        visited_sccs = set()
        scc_order = []

        def dfs_scc(scc_idx: int):
            if scc_idx in visited_sccs:
                return
            visited_sccs.add(scc_idx)
            for succ_scc in scc_successors[scc_idx]:
                dfs_scc(succ_scc)
            scc_order.append(scc_idx)

        # Find SCCs with no predecessors
        scc_has_predecessor = set()
        for succs in scc_successors.values():
            scc_has_predecessor.update(succs)

        for scc_idx in range(len(sccs)):
            if scc_idx not in scc_has_predecessor:
                dfs_scc(scc_idx)

        # Process remaining SCCs (disconnected)
        for scc_idx in range(len(sccs)):
            if scc_idx not in visited_sccs:
                dfs_scc(scc_idx)

        scc_order.reverse()

        # Return SCCs as groups with ordered nodes
        groups = []
        for scc_idx in scc_order:
            scc = sccs[scc_idx]
            if len(scc) == 1:
                groups.append(scc)
            else:
                # Cycle: order nodes within SCC
                groups.append(self._order_nodes_in_scc(scc))

        return groups

    def _order_nodes_in_scc(self, scc: List[str]) -> List[str]:
        """
        Order nodes within a strongly connected component (cycle).

        Uses DFS starting from node with minimum in-degree within the SCC.
        """
        if len(scc) == 1:
            return scc

        scc_set = set(scc)
        in_degree = {node: 0 for node in scc}

        for edge in self.edges:
            if edge.src_node in scc_set and edge.dst_node in scc_set:
                in_degree[edge.dst_node] += 1

        start_node = min(scc, key=lambda n: in_degree[n])

        visited = set()
        order = []

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            for successor in self.get_successors(node):
                if successor in scc_set:
                    dfs(successor)
            order.append(node)

        dfs(start_node)

        return list(reversed(order))

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
              Groups: [['sensor_0'], ['detector_0']]
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
        lines.append(f"  Sinks: {self.find_sinks()}")
        lines.append(f"  Groups: {self.get_topological_groups()}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"FlowGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"

    def __str__(self) -> str:
        return self.visualize()
