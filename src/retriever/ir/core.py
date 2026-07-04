"""
Core IR - The validated Intermediate Representation of a Pipeline.

This module consolidates the definition, behavior, and lifecycle of the Logical IR.
It includes:
1. `IR`: The main class (formerly IRStruct).
2. `IRNode`, `IREdge`: Graph components.
3. Analysis, Loading, Fusion, and Compilation logic.
"""

from __future__ import annotations

import json
import logging
import importlib
from copy import deepcopy
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Mapping, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.clock import Clock
    from retriever.flow.adapter import Adapter
    from retriever.ir.execution import ExecutionGraph, Placement
    from retriever.ir.rules import PlacementRule

logger = logging.getLogger(__name__)





# ==============================================================================
# Part 2: IR Data Structures (formerly struct.py)
# ==============================================================================

@dataclass
class IRServiceHandler:
    service_id: str
    method: str

@dataclass
class IRServiceCaller:
    service_id: str
    target_node: str

@dataclass
class IRVizPolicy:
    """Validated, typed visualization policy attached to an IR node."""

    enabled: bool = True
    hz: Optional[float] = None
    fields: Optional[List[str]] = None
    path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.hz is not None and self.hz <= 0:
            raise ValueError(f"IRVizPolicy.hz must be positive, got {self.hz}")
        if self.fields is not None:
            if not isinstance(self.fields, list) or not all(
                isinstance(name, str) and name for name in self.fields
            ):
                raise ValueError("IRVizPolicy.fields must be a list[str] when provided")
        if self.path is not None and not isinstance(self.path, str):
            raise ValueError("IRVizPolicy.path must be a string when provided")

@dataclass
class IRNode:
    id: str
    type: str
    module: str
    init_config: Dict[str, Any]
    config: Dict[str, Any]
    viz_policy: Optional[IRVizPolicy]
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    successors: List[str]
    predecessors: List[str]
    service_handlers: List[IRServiceHandler]
    service_callers: List[IRServiceCaller]

    def instantiate(self) -> Flow:
        """Instantiate the runtime Flow object for this node."""
        from retriever.error import FlowError, ErrCode
        
        if self.type == "FusedFlow":
            from retriever.rt.fused import FusedFlow
            fused = FusedFlow()
            fused.configure(self.config.get('fused_nodes', []), self.config.get('internal_edges', []))
            return fused

        try:
            module = importlib.import_module(self.module)
            cls = getattr(module, self.type)
            cfg = self.init_config or {}
            
            if hasattr(cls, "from_init_config"):
                return cls.from_init_config(cfg) # type: ignore
            return cls(**cfg) if cfg else cls()
            
        except Exception as e:
            raise FlowError(ErrCode.FLOW_INVALID, f"Cannot instantiate {self.type}: {e}", module=self.module, type=self.type)

    @staticmethod
    def instantiate_clock(config_dict: Dict[str, Any]) -> Clock:
        """Instantiate the runtime Clock object from config."""
        from retriever.flow.clock import Rate, Trigger, Hybrid, Synchronized
        from retriever.error import FlowError, ErrCode
        
        try:
            clk_dict = config_dict['clock']
            ctype = next(iter(clk_dict.keys()))
            params = clk_dict[ctype].copy()
            
            if ctype in ('Rate', 'Tick'):
                params.pop("fields", None)
                params.pop("sample", None)
                return Rate(**params)
            elif ctype == 'Trigger':
                fields = params.pop("fields", [])
                if "on" in params: fields.extend(params.pop("on"))
                return Trigger(*fields, **params)
            elif ctype == 'Synchronized':
                fields = params.pop("fields", [])
                return Synchronized(*fields, **params)
            elif ctype == 'Hybrid':
                trig = params.pop("trigger_fields", None)
                params.pop("rate_fields", None)
                if trig: params["trigger"] = trig
                return Hybrid(**params)
            else:
                raise FlowError(ErrCode.FLOW_CLOCK_INVALID, f"Unknown clock: {ctype}")
        except Exception as e:
            raise FlowError(ErrCode.FLOW_CLOCK_INVALID, f"Clock load error: {e}")

@dataclass
class IREdgeSource:
    node: str
    port: str

@dataclass
class IREdgeDestination:
    node: str
    port: str

@dataclass
class IREdge:
    id: str
    type: str
    source: IREdgeSource
    destination: IREdgeDestination
    adapter: Dict[str, Any]
    qsize: int
    on_full: Optional[str] = None

    def instantiate_adapter(self) -> Adapter:
        """Instantiate the runtime Adapter object for this edge."""
        from retriever.flow.adapter import get_adapter
        from retriever.error import FlowError, ErrCode
        try:
            if not self.adapter:
                # Default fallback if needed, or raise? Usually adapter is set.
                # Just returning None implies no adapter or handled elsewhere?
                # Existing loader logic assumed it existed or raised if dict access failed.
                # But here we check 'adapter'.
                raise ValueError("No adapter config")
                
            name = next(iter(self.adapter.keys()))
            params = self.adapter[name]
            cls = get_adapter(name.lower())
            clean = {k: v for k, v in params.items() if not k.startswith('_')}
            return cls(**clean)
        except Exception as e:
            raise FlowError(ErrCode.FLOW_ADAPTER_INVALID, f"Adapter load error: {e}")

@dataclass
class IRTopology:
    sources: List[str]
    sinks: List[str]
    groups: List[List[str]]
    node_count: int
    edge_count: int
    has_cycle: bool
    is_connected: bool

@dataclass
class IRMetadata:
    name: str
    created_at: str
    validated: bool
    optimized: bool = False

@dataclass
class IROptimization:
    predicate: Dict[str, Any]
    fusion_map: Dict[str, List[str]]

@dataclass
class IRAnalysis:
    """Analysis results/metadata from IR graph."""
    effective_rates: Dict[str, Optional[float]]
    rate_sources: Dict[str, str]
    clock_types: Dict[str, str]
    adapter_types: Dict[Tuple[str, str], str]
    in_cycle: Dict[str, bool]


@dataclass
class IR:
    """
    Intermediate Representation.

    The validated logic graph of a Pipeline. This is a "Rich Object" that
    owns its analysis, visualization, and compilation logic.
    """
    version: str
    metadata: IRMetadata
    nodes: List[IRNode]
    edges: List[IREdge]
    topology: IRTopology
    optimization: Optional[IROptimization] = None

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    @staticmethod
    def from_json(json_str: str) -> 'IR':
        data = json.loads(json_str)
        metadata = IRMetadata(**data['metadata'])
        topology = IRTopology(**data['topology'])

        nodes = [
            IRNode(
                id=n['id'],
                type=n['type'],
                module=n['module'],
                init_config=n.get('init_config', {}),
                config={k: v for k, v in n['config'].items() if k != 'viz_policy'},
                viz_policy=IRVizPolicy(**viz_policy_dict) if (
                    (viz_policy_dict := n.get('viz_policy') or n['config'].get('viz_policy'))
                ) is not None else None,
                inputs=n['inputs'],
                outputs=n['outputs'],
                successors=n['successors'],
                predecessors=n['predecessors'],
                service_handlers=[IRServiceHandler(**h) for h in n.get('service_handlers', [])],
                service_callers=[IRServiceCaller(**c) for c in n.get('service_callers', [])]
            ) for n in data['nodes']
        ]

        edges = [
            IREdge(
                id=e['id'],
                type=e['type'],
                source=IREdgeSource(**e['source']),
                destination=IREdgeDestination(**e['destination']),
                adapter=e['adapter'],
                qsize=e['qsize'],
                on_full=e.get('on_full')
            ) for e in data['edges']
        ]

        optimization = None
        if data.get('optimization') is not None:
            optimization = IROptimization(**data['optimization'])

        ir = IR(
            version=data['version'],
            metadata=metadata,
            nodes=nodes,
            edges=edges,
            topology=topology,
            optimization=optimization
        )
        # Loaded IRs are untrusted input: fail here with a named node/edge/port
        # instead of deep inside backend execution.
        ir.validate_structure()
        return ir

    def validate_structure(self) -> 'IR':
        """Check referential integrity of the graph; raise IRError on the
        first inconsistency (duplicate ids, dangling edge/adjacency
        references, unknown ports)."""
        from retriever.error import ErrCode, IRError

        nodes_by_id: Dict[str, IRNode] = {}
        for node in self.nodes:
            if node.id in nodes_by_id:
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    f"Duplicate node id '{node.id}'",
                    node=node.id,
                )
            nodes_by_id[node.id] = node

        expected_successors: Dict[str, Set[str]] = {node.id: set() for node in self.nodes}
        expected_predecessors: Dict[str, Set[str]] = {node.id: set() for node in self.nodes}
        edge_ids: Set[str] = set()

        for edge in self.edges:
            if edge.id in edge_ids:
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    f"Duplicate edge id '{edge.id}'",
                    edge=edge.id,
                )
            edge_ids.add(edge.id)

            for endpoint, role in ((edge.source, 'source'), (edge.destination, 'destination')):
                if endpoint.node not in nodes_by_id:
                    raise IRError(
                        ErrCode.IR_VAL_INVALID,
                        f"Edge '{edge.id}' {role} references unknown node '{endpoint.node}'",
                        edge=edge.id,
                        node=endpoint.node,
                    )
            src_node = nodes_by_id[edge.source.node]
            if edge.source.port not in src_node.outputs:
                raise IRError(
                    ErrCode.IR_VAL_PORT_NOT_FOUND,
                    f"Edge '{edge.id}' source port '{edge.source.port}' "
                    f"not in outputs of node '{src_node.id}'",
                    edge=edge.id,
                    node=src_node.id,
                    port=edge.source.port,
                )
            dst_node = nodes_by_id[edge.destination.node]
            destination_port = edge.destination.port
            if destination_port.startswith(self._FANIN_PREFIX):
                parts = destination_port.split("/")
                if len(parts) != 3 or parts[0] != "_fanin" or not parts[1] or not parts[2]:
                    raise IRError(
                        ErrCode.IR_VAL_INVALID,
                        f"Edge '{edge.id}' destination fan-in port '{destination_port}' "
                        "must be _fanin/<source_node>/<logical_port>",
                        edge=edge.id,
                        node=dst_node.id,
                        port=destination_port,
                    )
                fanin_source, logical_port = parts[1], parts[2]
                if fanin_source != edge.source.node:
                    raise IRError(
                        ErrCode.IR_VAL_INVALID,
                        f"Edge '{edge.id}' destination fan-in source '{fanin_source}' "
                        f"does not match source node '{edge.source.node}'",
                        edge=edge.id,
                        node=edge.source.node,
                        port=destination_port,
                    )
                if logical_port not in dst_node.inputs:
                    raise IRError(
                        ErrCode.IR_VAL_PORT_NOT_FOUND,
                        f"Edge '{edge.id}' destination fan-in logical port '{logical_port}' "
                        f"not in inputs of node '{dst_node.id}'",
                        edge=edge.id,
                        node=dst_node.id,
                        port=logical_port,
                    )
            elif destination_port not in dst_node.inputs:
                raise IRError(
                    ErrCode.IR_VAL_PORT_NOT_FOUND,
                    f"Edge '{edge.id}' destination port '{destination_port}' "
                    f"not in inputs of node '{dst_node.id}'",
                    edge=edge.id,
                    node=dst_node.id,
                    port=destination_port,
                )
            # Node adjacency is defined by topology edges only — internal
            # channels (underscore-prefixed logical ports, e.g. service
            # request/response) are excluded, matching the builder's
            # _is_topology_edge predicate.
            if not (self.get_logical_port(edge.source.port).startswith('_')
                    or self.get_logical_port(edge.destination.port).startswith('_')):
                expected_successors[edge.source.node].add(edge.destination.node)
                expected_predecessors[edge.destination.node].add(edge.source.node)

        for node in self.nodes:
            for kind, neighbors in (('successors', node.successors),
                                    ('predecessors', node.predecessors)):
                if len(neighbors) != len(set(neighbors)):
                    raise IRError(
                        ErrCode.IR_VAL_INVALID,
                        f"Node '{node.id}' contains duplicate {kind}",
                        node=node.id,
                    )
                for neighbor in neighbors:
                    if neighbor not in nodes_by_id:
                        raise IRError(
                            ErrCode.IR_VAL_INVALID,
                            f"Node '{node.id}' lists unknown {kind[:-1]} '{neighbor}'",
                            node=node.id,
                            neighbor=neighbor,
                        )

            actual_successors = set(node.successors)
            if actual_successors != expected_successors[node.id]:
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    f"Node '{node.id}' successors do not match edges: "
                    f"expected {sorted(expected_successors[node.id])}, "
                    f"got {sorted(actual_successors)}",
                    node=node.id,
                )

            actual_predecessors = set(node.predecessors)
            if actual_predecessors != expected_predecessors[node.id]:
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    f"Node '{node.id}' predecessors do not match edges: "
                    f"expected {sorted(expected_predecessors[node.id])}, "
                    f"got {sorted(actual_predecessors)}",
                    node=node.id,
                )
        self._validate_topology_metadata(nodes_by_id)
        return self

    def _validate_topology_metadata(self, nodes_by_id: Mapping[str, IRNode]) -> None:
        """Ensure serialized topology cannot change runtime execution order."""
        from retriever.error import ErrCode, IRError
        from retriever.flow.graph import PipelineGraph

        topo = self.topology
        if topo.node_count != len(self.nodes):
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology node_count mismatch: expected {len(self.nodes)}, got {topo.node_count}",
            )
        if topo.edge_count != len(self.edges):
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology edge_count mismatch: expected {len(self.edges)}, got {topo.edge_count}",
            )

        grouped_nodes: List[str] = [node_id for group in topo.groups for node_id in group]
        grouped_node_set = set(grouped_nodes)
        node_ids = set(nodes_by_id)
        if len(grouped_nodes) != len(grouped_node_set):
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                "Topology groups contain duplicate node ids",
            )
        unknown_grouped = sorted(grouped_node_set - node_ids)
        if unknown_grouped:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology groups reference unknown nodes: {unknown_grouped}",
            )
        missing_grouped = sorted(node_ids - grouped_node_set)
        if missing_grouped:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology groups omit nodes: {missing_grouped}",
            )

        topo_graph = PipelineGraph()
        for node_id in nodes_by_id:
            topo_graph.add_node(node_id, {"_in": object}, {"_out": object})

        seen_pairs: Set[Tuple[str, str]] = set()
        for edge in self.edges:
            if (self.get_logical_port(edge.source.port).startswith('_')
                    or self.get_logical_port(edge.destination.port).startswith('_')):
                continue
            pair = (edge.source.node, edge.destination.node)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            topo_graph.connect(edge.source.node, "_out", edge.destination.node, "_in", {})

        expected_sources = topo_graph.find_sources()
        expected_sinks = topo_graph.find_sinks()
        expected_groups = topo_graph.get_topological_groups()
        expected_has_cycle = topo_graph.has_cycles()
        expected_is_connected = topo_graph.is_connected()

        if topo.sources != expected_sources:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology sources mismatch: expected {expected_sources}, got {topo.sources}",
            )
        if topo.sinks != expected_sinks:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology sinks mismatch: expected {expected_sinks}, got {topo.sinks}",
            )
        if topo.groups != expected_groups:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology groups mismatch: expected {expected_groups}, got {topo.groups}",
            )
        if topo.has_cycle != expected_has_cycle:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology has_cycle mismatch: expected {expected_has_cycle}, got {topo.has_cycle}",
            )
        if topo.is_connected != expected_is_connected:
            raise IRError(
                ErrCode.IR_VAL_INVALID,
                f"Topology is_connected mismatch: expected {expected_is_connected}, got {topo.is_connected}",
            )

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.write_text(self.to_json())

    @classmethod
    def load(cls, path: Union[str, Path]) -> "IR":
        path = Path(path)
        return cls.from_json(path.read_text())

    # ------------------------------------------------------------------------
    # Graph Queries
    # ------------------------------------------------------------------------
    def get_node(self, node_id: str) -> Optional[IRNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edge(self, edge_id: str) -> Optional[IREdge]:
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def get_outgoing_edges(self, node_id: str) -> List[IREdge]:
        return [e for e in self.edges if e.source.node == node_id]

    def get_incoming_edges(self, node_id: str) -> List[IREdge]:
        return [e for e in self.edges if e.destination.node == node_id]

    # ------------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------------
    _cached_analysis: Optional[IRAnalysis] = field(default=None, repr=False, compare=False)

    @property
    def analysis(self) -> IRAnalysis:
        if self._cached_analysis is None:
            object.__setattr__(self, '_cached_analysis', self._analyze())
        return self._cached_analysis  # type: ignore

    # ------------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------------
    def visualize(
        self,
        path: Union[str, Path] = "pipeline_viz.html",
        *,
        open_browser: bool = False,
    ) -> Path:
        from retriever.ir.viz import save_interactive_html
        path_obj = Path(path)
        save_interactive_html(self, str(path_obj))
        if open_browser:
            import webbrowser
            webbrowser.open(f"file://{path_obj.resolve()}")
        return path_obj.resolve()

    def to_ascii(self) -> str:
        from retriever.ir.viz import generate_ascii_graph
        return generate_ascii_graph(self)
    
    # ------------------------------------------------------------------------
    # Optimization (Fusion)
    # ------------------------------------------------------------------------
    def fuse(
        self,
        partitions: List[List[str]],
        predicate_config: Dict[str, Any]
    ) -> 'IR':
        """Apply fusion to IR and return new IR (out-of-place)."""
        new_ir = deepcopy(self)
        fusion_map: Dict[str, List[str]] = {}

        # Fuse groups
        for group in partitions:
            if len(group) < 2: continue
            fused_id = new_ir._fuse_group_inplace(group)
            fusion_map[fused_id] = group

        # Rebuild topology
        new_ir._update_node_adjacency()
        new_ir._rebuild_topology(self.topology.groups, fusion_map)

        new_ir.metadata.optimized = True
        new_ir.optimization = IROptimization(predicate=predicate_config, fusion_map=fusion_map)
        return new_ir

    def _fuse_group_inplace(self, node_ids: List[str]) -> str:
        # Validation
        for nid in node_ids:
            if not self.get_node(nid): raise ValueError(f"Node {nid} missing")
        
        first, last = self.get_node(node_ids[0]), self.get_node(node_ids[-1])
        if not first or not last: raise ValueError("Missing endpoint nodes")
        
        fused_id = f"Fused_{'_'.join(node_ids)}"
        node_set = set(node_ids)
        
        # Internal edges for port mapping
        internal_edges_data = []
        internal_edges = []
        incoming_edges = []
        outgoing_edges = []

        for edge in self.edges:
            src, dst = edge.source.node, edge.destination.node
            if src in node_set and dst in node_set:
                internal_edges_data.append({
                    "src_node": src, "src_port": edge.source.port,
                    "dst_node": dst, "dst_port": edge.destination.port
                })
                internal_edges.append(edge)
            elif dst == node_ids[0]:
                incoming_edges.append(edge)
            elif src == node_ids[-1]:
                outgoing_edges.append(edge)

        # Create Fused Node
        fused_node = IRNode(
            id=fused_id,
            type="FusedFlow",
            module="retriever.rt.fused",
            init_config={},
            config={
                "clock": first.config.get("clock"),
                "priority": first.config.get("priority"),
                "cpu_affinity": first.config.get("cpu_affinity"),
                "memory_size": first.config.get("memory_size"),
                "fused_nodes": [asdict(self.get_node(nid)) for nid in node_ids if self.get_node(nid)],
                "internal_edges": internal_edges_data
            },
            viz_policy=None,
            inputs=first.inputs,
            outputs=last.outputs,
            successors=[], predecessors=[], service_handlers=[], service_callers=[]
        )

        # Remap edges
        self.edges = [e for e in self.edges if e not in internal_edges]
        self.nodes = [n for n in self.nodes if n.id not in node_set]
        
        for edge in self.edges:
            if edge in incoming_edges: edge.destination.node = fused_id
            elif edge in outgoing_edges: edge.source.node = fused_id
        
        self.nodes.append(fused_node)
        return fused_id

    def _update_node_adjacency(self) -> None:
        for node in self.nodes:
            node.successors = []
            node.predecessors = []
        for edge in self.edges:
            src, dst = self.get_node(edge.source.node), self.get_node(edge.destination.node)
            if src and edge.destination.node not in src.successors:
                src.successors.append(edge.destination.node)
            if dst and edge.source.node not in dst.predecessors:
                dst.predecessors.append(edge.source.node)

    def _rebuild_topology(self, original_groups: List[List[str]], fusion_map: Dict[str, List[str]]) -> None:
        # Recompute sources/sinks
        sources = [n.id for n in self.nodes if not n.predecessors]
        sinks = [n.id for n in self.nodes if not n.successors]
        
        # Derive groups
        node_map = {orig: fused for fused, origs in fusion_map.items() for orig in origs}
        new_groups = []
        for group in original_groups:
            if len(group) > 1:
                new_groups.append(group) # Cycles unchanged
            else:
                n = group[0]
                if n in node_map:
                    fused = node_map[n]
                    origs = fusion_map[fused]
                    if n == origs[0]: new_groups.append([fused])
                else:
                    new_groups.append(group)

        self.topology.sources = sources
        self.topology.sinks = sinks
        self.topology.groups = new_groups
        self.topology.node_count = len(self.nodes)
        self.topology.edge_count = len(self.edges)

    # ------------------------------------------------------------------------
    # Fan-in Helpers
    # ------------------------------------------------------------------------
    _FANIN_PREFIX = "_fanin/"

    @classmethod
    def is_fan_in_port(cls, port: str) -> bool:
        return port.startswith(cls._FANIN_PREFIX)

    @classmethod
    def make_fan_in_port(cls, source_node: str, logical_port: str) -> str:
        return f"{cls._FANIN_PREFIX}{source_node}/{logical_port}"

    @classmethod
    def get_logical_port(cls, port: str) -> str:
        """Get logical port name from any port (fan-in or regular)."""
        if not port.startswith(cls._FANIN_PREFIX):
            return port
        parts = port.split("/")
        return parts[2] if len(parts) == 3 else port

    # ------------------------------------------------------------------------
    # Internal Analysis Logic
    # ------------------------------------------------------------------------
    def _analyze(self) -> IRAnalysis:
        """Run all analysis passes (internal)."""
        rates = self._compute_effective_rates()
        clock_types, _ = self._extract_clock_info()
        adapter_types = self._extract_adapter_info()
        in_cycle = self._compute_in_cycle()
        
        return IRAnalysis(
            effective_rates=rates['effective_rates'],
            rate_sources=rates['rate_sources'],
            clock_types=clock_types,
            adapter_types=adapter_types,
            in_cycle=in_cycle
        )

    def _compute_effective_rates(self) -> Dict[str, Any]:
        rates: Dict[str, Optional[float]] = {}
        sources: Dict[str, str] = {}
        
        # Pass 1: explicit
        for node in self.nodes:
            clock = node.config.get('clock', {})
            hz = None
            if 'Rate' in clock: hz = clock['Rate'].get('hz')
            elif 'Hybrid' in clock: hz = clock['Hybrid'].get('hz')
            rates[node.id] = hz
            if hz: sources[node.id] = node.id
            
        # Pass 2: propagate
        for _ in range(len(self.nodes)):
            changed = False
            for edge in self.edges:
                s, d = edge.source.node, edge.destination.node
                if rates.get(d) is not None: continue
                
                d_node = self.get_node(d)
                if not d_node or 'Trigger' not in d_node.config.get('clock', {}): continue
                
                if rates.get(s):
                    rates[d] = rates[s]
                    sources[d] = sources.get(s, s)
                    changed = True
            if not changed: break
            
        return {'effective_rates': rates, 'rate_sources': sources}

    def _extract_clock_info(self) -> Tuple[Dict[str, str], Dict[str, dict]]:
        types, params = {}, {}
        for node in self.nodes:
            clk = node.config.get('clock', {})
            if clk:
                t = next(iter(clk.keys()))
                types[node.id] = t
                params[node.id] = clk[t]
            else:
                types[node.id] = 'Unknown'
        return types, params

    def _extract_adapter_info(self) -> Dict[Tuple[str, str], str]:
        types = {}
        for edge in self.edges:
            key = (edge.source.node, edge.destination.node)
            if edge.adapter: types[key] = next(iter(edge.adapter.keys()))
            else: types[key] = 'Unknown'
        return types

    def _compute_in_cycle(self) -> Dict[str, bool]:
        in_cycle = {}
        for group in self.topology.groups:
            is_cyc = len(group) > 1
            for n in group: in_cycle[n] = is_cyc
        return in_cycle

    # ------------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------------
    def compile(self, policy: Union[str, Dict[str, Any]] = "aggressive", **kwargs) -> 'ExecutionGraph':
        """
        Compile Logical IR into an ExecutionGraph.

        Args:
            policy: Placement/Partitioning policy name (e.g., "aggressive", "conservative")
                    or explicit configuration dict.

        Returns:
            ExecutionGraph: The physical execution plan.
        """
        from retriever.ir.execution import ExecutionGraph
        return ExecutionGraph.from_ir(self, policy)
