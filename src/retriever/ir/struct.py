"""
IR Structures - Intermediate Representation Data Structures

Validated graph structure ready for runtime compilation.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import json


@dataclass
class IRServiceHandler:
    """
    Service this node provides.

    Attributes:
        service_id: Unique service identifier
        method: Method name
    """
    service_id: str
    method: str


@dataclass
class IRServiceCaller:
    """
    Service this node calls.

    Attributes:
        service_id: Unique service identifier
        target_node: Resolved handler node_id
    """
    service_id: str
    target_node: str


@dataclass
class IRNode:
    """
    IR node representing a validated Flow.

    Attributes:
        id: Unique node identifier (e.g., "ClassName_12345")
        type: Flow class name
        module: Module path for import
        config: FlowConfig as dict (contains clock)
        inputs: Input port name → type string mapping
        outputs: Output port name → type string mapping
        successors: List of successor node IDs
        predecessors: List of predecessor node IDs
        service_handlers: Services this node provides
        service_callers: Services this node calls
    """
    id: str
    type: str
    module: str
    config: Dict[str, Any]
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    successors: List[str]
    predecessors: List[str]
    service_handlers: List[IRServiceHandler]
    service_callers: List[IRServiceCaller]


@dataclass
class IREdgeSource:
    """Source end of an edge"""
    node: str
    port: str


@dataclass
class IREdgeDestination:
    """Destination end of an edge"""
    node: str
    port: str


@dataclass
class IREdge:
    """
    IR edge representing a validated port connection.

    Attributes:
        id: Unique edge identifier (format: source.node.port->dest.node.port)
        type: Data type flowing through edge (as string)
        source: Source node and port
        destination: Destination node and port
        adapter: Adapter configuration {adapter_name: params}
        qsize: Queue size for message passing
    """
    id: str
    type: str
    source: IREdgeSource
    destination: IREdgeDestination
    adapter: Dict[str, Any]
    qsize: int


@dataclass
class IRTopology:
    """
    Graph topology metadata.

    Attributes:
        sources: Source node IDs (no inputs)
        sinks: Sink node IDs (no outputs)
        groups: Topological groups (SCCs in topological order)
                Single-element lists = nodes not in cycles
                Multi-element lists = nodes in same cycle
        node_count: Number of nodes in graph
        edge_count: Number of edges in graph
        has_cycle: True if graph contains cycles
        is_connected: True if graph is weakly connected
    """
    sources: List[str]
    sinks: List[str]
    groups: List[List[str]]
    node_count: int
    edge_count: int
    has_cycle: bool
    is_connected: bool


@dataclass
class IRMetadata:
    """
    IR metadata.

    Attributes:
        name: Pipeline name
        created_at: ISO timestamp
        validated: Validation status
        optimized: Whether the graph has been lowered for execution (legacy name)
    """
    name: str
    created_at: str
    validated: bool
    optimized: bool = False


@dataclass
class IROptimization:
    """
    Execution-lowering provenance (legacy name).

    Tracks what lowering/grouping was applied to produce an executable graph.

    Attributes:
        predicate: Predicate configuration as dict
        fusion_map: Maps fused node ID → list of original node IDs
                    Example: {"Fused_ABC_123": ["FlowA_1", "FlowB_2", "FlowC_3"]}
    """
    predicate: Dict[str, Any]
    fusion_map: Dict[str, List[str]]


@dataclass
class IRStruct:
    """
    Intermediate Representation Structure.

    Validated graph structure with all metadata needed for runtime compilation.

    Attributes:
        version: IR format version
        metadata: Pipeline metadata
        nodes: List of validated IR nodes
        edges: List of validated IR edges
        topology: Graph topology information
        optimization: Lowering provenance (None if not lowered)
    """
    version: str
    metadata: IRMetadata
    nodes: List[IRNode]
    edges: List[IREdge]
    topology: IRTopology
    optimization: Optional[IROptimization] = None

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), indent=indent)

    @staticmethod
    def from_json(json_str: str) -> 'IRStruct':
        """Load from JSON string"""
        data = json.loads(json_str)

        # Reconstruct nested dataclasses
        metadata = IRMetadata(**data['metadata'])
        topology = IRTopology(**data['topology'])

        nodes = [
            IRNode(
                id=n['id'],
                type=n['type'],
                module=n['module'],
                config=n['config'],
                inputs=n['inputs'],
                outputs=n['outputs'],
                successors=n['successors'],
                predecessors=n['predecessors'],
                service_handlers=[IRServiceHandler(**h) for h in n.get('service_handlers', [])],
                service_callers=[IRServiceCaller(**c) for c in n.get('service_callers', [])]
            )
            for n in data['nodes']
        ]

        edges = [
            IREdge(
                id=e['id'],
                type=e['type'],
                source=IREdgeSource(**e['source']),
                destination=IREdgeDestination(**e['destination']),
                adapter=e['adapter'],
                qsize=e['qsize']
            )
            for e in data['edges']
        ]

        # Reconstruct optimization if present
        optimization = None
        if data.get('optimization') is not None:
            optimization = IROptimization(**data['optimization'])

        return IRStruct(
            version=data['version'],
            metadata=metadata,
            nodes=nodes,
            edges=edges,
            topology=topology,
            optimization=optimization
        )

    # Graph query helpers
    def get_node(self, node_id: str) -> Optional[IRNode]:
        """Get node by ID"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edge(self, edge_id: str) -> Optional[IREdge]:
        """Get edge by ID"""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def get_outgoing_edges(self, node_id: str) -> List[IREdge]:
        """Get all edges originating from a node"""
        return [e for e in self.edges if e.source.node == node_id]

    def get_incoming_edges(self, node_id: str) -> List[IREdge]:
        """Get all edges terminating at a node"""
        return [e for e in self.edges if e.destination.node == node_id]
