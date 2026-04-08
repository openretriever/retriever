"""
PipelineBuilder - Graph builder for flow connections.

Context manager that tracks flow connections and builds FlowGraph.
"""

from contextvars import ContextVar
from dataclasses import dataclass, is_dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union

from retriever.error import ErrCode, FlowError
from retriever.flow.graph import PipelineGraph

if TYPE_CHECKING:
    from retriever.flow.adapter import Adapter
    from retriever.flow.config import EdgeConfig
    from retriever.flow.temporal import TemporalFlow

from retriever.ir.core import (
    IR,
    IRNode,
    IREdge,
    IREdgeSource,
    IREdgeDestination,
    IRServiceHandler,
    IRServiceCaller,
    IRMetadata,
    IRTopology,
)
from retriever.error import IRError
from retriever.flow.service import ServiceMethod
from retriever.utils import type_to_str
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


# Thread-safe context storage
_active_context: ContextVar[Optional["PipelineBuilder"]] = ContextVar(
    "flow_context", default=None
)


@dataclass
class Pipe:
    """Record of a single connection registered via then()"""

    src_node_id: str
    dst_node_id: str
    map: Dict[str, str]
    sync: Union["Adapter", Dict[str, "Adapter"]]
    edge_config: Optional[Dict[str, "EdgeConfig"]] = None  # Per-port buffer config
    qsize: int = 10
    on_full: Optional[str] = None


class PipelineBuilder:
    """
    Context manager for building flow graphs.

    Registers connections and builds FlowGraph structure.
    Validation is deferred to IR layer.

    Usage:
        with PipelineBuilder() as ctx:
            camera = CameraFlow() @ Rate(hz=30)
            detector = DetectorFlow() @ Rate(hz=30)
            camera.then(detector, map={'image': 'image'})

            graph = ctx.build_graph()
    """

    def __init__(self, name: str = "pipeline"):
        """Initialize empty context."""
        self._name: str = name
        self._context_token = None

        # Track handles: node_id → handle
        self._handles: Dict[str, "TemporalFlow"] = {}

        # Optional owner (e.g. Pipeline)
        self.owner: Any = None

        # Track connections
        self._connections: List[Pipe] = []

        # Built graph
        self._graph: Optional[PipelineGraph] = None

    # ========================================================================
    # Context Management
    # ========================================================================

    def __enter__(self) -> "PipelineBuilder":
        """Activate this context for the current thread"""
        self._context_token = _active_context.set(self)
        logger.debug(f"PipelineBuilder '{self._name}' activated")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Deactivate context"""
        if self._context_token is not None:
            _active_context.reset(self._context_token)
            self._context_token = None
        logger.debug(f"PipelineBuilder '{self._name}' deactivated")
        return False

    @staticmethod
    def active() -> Optional["PipelineBuilder"]:
        """Get currently active PipelineBuilder for this thread"""
        return _active_context.get()

    @staticmethod
    def require_active() -> "PipelineBuilder":
        """Get active context or raise FlowError if none active."""
        ctx = PipelineBuilder.active()
        if not ctx:
            import inspect

            frame = inspect.currentframe()
            if frame and frame.f_back:
                method_name = frame.f_back.f_code.co_name
                msg = f"{method_name}() must be called inside PipelineBuilder"
            else:
                msg = "Operation must be called inside PipelineBuilder"
            raise FlowError(ErrCode.FLOW_CONTEXT_INACTIVE, msg)
        return ctx

    # ========================================================================
    # Connection Registration
    # ========================================================================

    def register_connection(
        self,
        src: "TemporalFlow",
        dst: "TemporalFlow",
        map: Dict[str, str],
        sync: Union["Adapter", Dict[str, "Adapter"]],
        edge_config: Optional[Dict[str, "EdgeConfig"]] = None,
        qsize: int = 10,
        on_full: Optional[str] = None,
    ) -> None:
        """Register connection from FlowHandle.then() with basic validation."""
        # Invalidate any previously-built graph cache.
        self._graph = None

        # Basic parameter validation
        if not map:
            raise FlowError(
                ErrCode.FLOW_CONNECTION_INVALID,
                "Map parameter cannot be empty",
                src=src.flow.__class__.__name__,
                dst=dst.flow.__class__.__name__,
            )

        # Register handles and get node IDs
        src_node_id = self._register_handle(src)
        dst_node_id = self._register_handle(dst)

        # Record connection
        self._connections.append(
            Pipe(
                src_node_id=src_node_id,
                dst_node_id=dst_node_id,
                map=map,
                sync=sync,
                edge_config=edge_config,
                qsize=qsize,
                on_full=on_full,
            )
        )

        # Propagate pipeline ownership if this context is part of a Pipeline
        if self.owner:
            src.pipeline = self.owner
            dst.pipeline = self.owner

        logger.debug(
            f"Registered connection: {src.flow.__class__.__name__} -> "
            f"{dst.flow.__class__.__name__} (map={map})"
        )

    def _register_handle(self, handle: "TemporalFlow") -> str:
        """Register handle if not already registered, return node_id"""
        for node_id, existing in self._handles.items():
            if existing is handle:
                return node_id

        node_id = self._create_node_id(handle)
        if node_id not in self._handles:
            self._handles[node_id] = handle
            logger.debug(
                f"Registered handle: {handle.flow.__class__.__name__} as {node_id}"
            )
        return node_id

    def _create_node_id(self, handle: "TemporalFlow") -> str:
        """Create a stable, human-addressable node ID for a handle."""
        explicit = getattr(handle, "name", None)
        if explicit:
            existing = self._handles.get(explicit)
            if existing is not None and existing is not handle:
                raise FlowError(
                    ErrCode.FLOW_CONNECTION_INVALID,
                    f"Flow name '{explicit}' is already in use in pipeline '{self._name}'. "
                    "Use unique TemporalFlow.named(...) selectors for composable pipelines.",
                    flow_name=explicit,
                )
            return explicit

        flow = handle.flow
        base = flow.__class__.__name__
        if base not in self._handles:
            return base

        suffix = 2
        while f"{base}__{suffix}" in self._handles:
            suffix += 1
        return f"{base}__{suffix}"

    # ========================================================================
    # Graph Building
    # ========================================================================

    @property
    def graph(self) -> PipelineGraph:
        """Get the FlowGraph (builds if not already built)."""
        if self._graph is not None:
            return self._graph
        return self._build_graph()

    def _build_graph(self) -> PipelineGraph:
        """Internal: Build FlowGraph from registered connections (validation deferred to IR)."""
        logger.debug(f"Building graph for '{self._name}'")

        graph = PipelineGraph()

        # Step 1: Add all nodes
        for node_id, handle in self._handles.items():
            # Extract ports from @io types (Composite aware)
            input_ports = self._extract_ports(handle.flow.input_types)
            output_ports = self._extract_ports(handle.flow.output_types)

            graph.add_node(node_id, input_ports, output_ports)
            logger.debug(
                f"Added node: {node_id} "
                f"(inputs={list(input_ports.keys())}, "
                f"outputs={list(output_ports.keys())})"
            )

        # Step 2: Add all edges
        for conn in self._connections:
            self._create_edges(graph, conn.src_node_id, conn.dst_node_id, conn)

        self._graph = graph
        logger.info(
            f"Graph built: {graph.get_node_count()} nodes, "
            f"{graph.get_edge_count()} edges"
        )
        return graph

    def _extract_ports(
        self, io_types: Union[Type, Tuple[Type, ...]]
    ) -> Dict[str, Type]:
        """Extract port info from @io types (Composite aware)."""
        from retriever.flow.io import is_flow_io
        from retriever.rt.step import IOView

        if not io_types:
            return {}

        # Normalize to tuple/list
        types_list = list(io_types) if isinstance(io_types, tuple) else [io_types]

        # Use IOView's static method for port resolution
        port_map = IOView.resolve_ports(types_list)

        # Build dict of {port_name: field_type} using OO pattern
        final_ports = {}

        # Cache field types using classmethod (with fallback for older types)
        alias_type_map = IOView.resolve_alias_types(types_list)
        type_cache = {}
        for t in types_list:
            if t is not type(None) and is_flow_io(t):
                # Use _field_types if available, otherwise fall back to dataclass fields
                if hasattr(t, "_field_types") and callable(t._field_types):
                    type_cache[t] = t._field_types()
                elif is_dataclass(t):
                    from dataclasses import fields as dc_fields

                    type_cache[t] = {f.name: f.type for f in dc_fields(t)}
                else:
                    type_cache[t] = {}

        for port_name, (alias_name, field_name) in port_map.items():
            typ = alias_type_map.get(alias_name)
            if typ in type_cache:
                final_ports[port_name] = type_cache[typ].get(field_name, Any)

        return final_ports

    def _create_edges(
        self, graph: PipelineGraph, src_id: str, dst_id: str, conn: Pipe
    ) -> None:
        """Create edges for connection with adapter and qsize metadata."""
        from retriever.utils import as_tagged

        def resolve_port_config(port: str):
            """Resolve qsize, on_full, and adapter for a specific port."""
            # Start with defaults from connection
            qsize = conn.qsize
            on_full = conn.on_full
            adapter = conn.sync

            # Check edge_config for per-port overrides
            if conn.edge_config and "*" in conn.edge_config:
                # "*" acts as edge-level defaults for all ports.
                cfg = conn.edge_config["*"]
                qsize = cfg.qsize
                on_full = cfg.on_full or on_full
                if cfg.adapter is not None:
                    adapter = cfg.adapter

            if conn.edge_config and port in conn.edge_config:
                # Port-specific config overrides "*" defaults.
                cfg = conn.edge_config[port]
                qsize = cfg.qsize
                on_full = cfg.on_full or on_full
                # Use adapter from edge_config if specified
                if cfg.adapter is not None:
                    adapter = cfg.adapter

            # Resolve sync dict -> specific adapter
            if isinstance(adapter, dict):
                adapter = adapter.get(port) or adapter.get("*")
                if adapter is None:
                    from retriever.error import FlowError, ErrCode

                    raise FlowError(
                        ErrCode.FLOW_CONNECTION_INVALID,
                        f"Missing sync adapter for port '{port}' in dict sync",
                    )

            return qsize, on_full, adapter

        # Atomic connection: connect all matching fields by name
        if conn.map == {"*": "*"}:
            src_node = graph.get_node(src_id)
            dst_node = graph.get_node(dst_id)

            src_ports = src_node.get_output_port_names()
            dst_ports = dst_node.get_input_port_names()

            for src_port in src_ports:
                if src_port in dst_ports:
                    qsize, on_full, adapter = resolve_port_config(src_port)
                    graph.connect(
                        src_id,
                        src_port,
                        dst_id,
                        src_port,
                        {
                            "adapter": as_tagged(adapter),
                            "qsize": qsize,
                            "on_full": on_full,
                        },
                    )
                    logger.debug(
                        f"Created atomic edge: {src_id}.{src_port} -> "
                        f"{dst_id}.{src_port} (qsize={qsize})"
                    )

        # Composite connection: edge per field mapping
        else:
            for src_field, dst_field in conn.map.items():
                qsize, on_full, adapter = resolve_port_config(dst_field)
                graph.connect(
                    src_id,
                    src_field,
                    dst_id,
                    dst_field,
                    {"adapter": as_tagged(adapter), "qsize": qsize, "on_full": on_full},
                )
                logger.debug(
                    f"Created composite edge: {src_id}.{src_field} -> "
                    f"{dst_id}.{dst_field} (qsize={qsize})"
                )

    # ========================================================================
    # Accessors
    # ========================================================================

    def get_graph(self) -> PipelineGraph:
        """Get the FlowGraph (builds if not already built)."""
        return self.graph

    def get_connections(self) -> List[Pipe]:
        """Get all registered connections."""
        return self._connections.copy()

    def get_handles(self) -> List["TemporalFlow"]:
        """Get all registered handles."""
        return list(self._handles.values())

    def get_flow_dict(self) -> Dict[str, "TemporalFlow"]:
        """Get the registered flow handles keyed by stable node id."""
        return dict(self._handles)

    def get_name(self) -> str:
        """Get pipeline name"""
        return self._name

    def get_handle_for_node(self, node_id: str) -> "TemporalFlow":
        """Get TemporalFlow for a node ID."""
        if node_id not in self._handles:
            raise FlowError(
                ErrCode.FLOW_CONTEXT_NODE_NOT_FOUND,
                f"Node '{node_id}' not found in context. "
                f"Available: {list(self._handles.keys())}",
                node_id=node_id,
            )

        return self._handles[node_id]

    def get_node_id(self, handle: "TemporalFlow") -> str:
        """Get node_id for a TemporalFlow registered in this context."""
        for node_id, h in self._handles.items():
            if h is handle:
                return node_id
        raise FlowError(
            ErrCode.FLOW_CONTEXT_NODE_NOT_FOUND,
            "Handle not found in context. Connect it into the Pipeline/PipelineBuilder first.",
            handle=handle.flow.__class__.__name__,
        )

    def select_flow(self, selector: str) -> "TemporalFlow":
        """
        Resolve a flow by explicit node id/name or by unique Flow class name.

        Exact node ids are preferred. As a fallback, a bare Flow class name is
        accepted when it uniquely matches one registered handle.
        """
        if selector in self._handles:
            return self._handles[selector]

        matches = [
            (node_id, handle)
            for node_id, handle in self._handles.items()
            if handle.matches(selector)
        ]
        if len(matches) == 1:
            return matches[0][1]
        if not matches:
            raise FlowError(
                ErrCode.FLOW_CONTEXT_NODE_NOT_FOUND,
                f"Flow selector '{selector}' not found. Available: {list(self._handles.keys())}",
                selector=selector,
            )
        raise FlowError(
            ErrCode.FLOW_CONNECTION_INVALID,
            f"Flow selector '{selector}' is ambiguous. Matches: {[node_id for node_id, _ in matches]}",
            selector=selector,
            matches=[node_id for node_id, _ in matches],
        )

    # ========================================================================
    # Validation Entry Point (delegates to IR layer)
    # ========================================================================

    def validate(self):
        """Validate the flow graph (delegates to IR layer)."""
        # Ensure graph is built
        _ = self.graph

        # Delegate to IR validator

    def build_ir(self) -> "IR":
        """
        Compile pipeline construction context into pure IR.

        Validates that all edge connections have matching types on
        source output port and destination input port.

        Returns:
            Validated IR ready for runtime compilation

        Raises:
            FlowError: If validation fails (type mismatch, etc.)
        """
        # Pipeline may provide late-bound defaults (e.g. on_lag policy).
        apply_defaults = getattr(self, "_apply_clock_defaults", None)
        if callable(apply_defaults):
            apply_defaults()

        flow_graph = self.get_graph()
        pipeline_name = self.get_name()

        logger.info(f"Compiling flow graph '{pipeline_name}' to IR")

        # Build IR nodes
        ir_nodes = self._build_nodes(flow_graph)

        # Build IR edges with type validation
        ir_edges = self._build_edges(flow_graph)

        # Resolve service connection
        self._add_service_ports(ir_nodes)
        service_edges = self._build_service_edges(ir_nodes)
        ir_edges.extend(service_edges)

        # Build topology with all fields
        topology = self._build_topology(flow_graph)

        # Create metadata
        metadata = IRMetadata(
            name=pipeline_name, created_at=datetime.now().isoformat(), validated=True
        )

        logger.info(
            f"Compilation complete: {len(ir_nodes)} nodes, "
            f"{len(ir_edges)} edges, "
            f"{len(topology.groups)} groups"
        )

        return IR(
            version="1.0.0",
            metadata=metadata,
            nodes=ir_nodes,
            edges=ir_edges,
            topology=topology,
        )

    def validate(self) -> "IR":
        """Alias for build_ir."""
        return self.build_ir()

    # ========================================================================
    # IR Compilation Helpers (formerly compiler.py)
    # ========================================================================

    def _build_nodes(self, flow_graph: PipelineGraph) -> List[IRNode]:
        """Build IR nodes from FlowGraph nodes."""
        ir_nodes = []
        callers_map: Dict[str, List[ServiceMethod]] = {}

        # First pass: build nodes with handlers
        for node_id, node in flow_graph.nodes.items():
            handle = self.get_handle_for_node(node_id)
            flow_class = handle.flow.__class__

            init_config = handle.flow.init_config()
            if init_config is None:
                init_config = {}
            if not isinstance(init_config, dict):
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    "Flow.init_config() must return a dict",
                    node=node_id,
                    type=flow_class.__name__,
                    got_type=type(init_config).__name__,
                )

            # Extract service metadata
            service_handlers = self._extract_service_handlers(flow_class)
            callers_map[node_id] = self._extract_service_methods(flow_class)
            config = handle.config.to_dict()
            if getattr(handle.flow, "in_process_only", False):
                config["in_process_only"] = True

            ir_node = IRNode(
                id=node_id,
                type=flow_class.__name__,
                module=flow_class.__module__,
                init_config=init_config,
                config=config,
                inputs={
                    name: type_to_str(typ) for name, typ in node.input_ports.items()
                },
                outputs={
                    name: type_to_str(typ) for name, typ in node.output_ports.items()
                },
                successors=flow_graph.get_successors(node_id),
                predecessors=flow_graph.get_predecessors(node_id),
                service_handlers=service_handlers,
                service_callers=[],  # Resolved in second pass
            )
            ir_nodes.append(ir_node)

        # Second pass: resolve callers
        handlers = self._build_handler_index(ir_nodes)
        for ir_node in ir_nodes:
            ir_node.service_callers = self._resolve_service_callers(
                ir_node.id, callers_map[ir_node.id], handlers
            )

        return ir_nodes

    def _build_edges(self, flow_graph: PipelineGraph) -> List[IREdge]:
        """Build IR edges from FlowGraph edges with port type validation."""
        # First pass: group edges by (dst_node, dst_port) to detect fan-in
        edges_by_dst: Dict[tuple, list] = {}
        for edge in flow_graph.edges:
            key = (edge.dst_node, edge.dst_port)
            if key not in edges_by_dst:
                edges_by_dst[key] = []
            edges_by_dst[key].append(edge)

        # Validate fan-in: same type and same adapter required
        fan_in_ports = set()
        for (dst_node, dst_port), edges in edges_by_dst.items():
            if len(edges) > 1:
                fan_in_ports.add((dst_node, dst_port))
                self._validate_fan_in(flow_graph, dst_node, dst_port, edges)

        # Second pass: build IR edges with fan-in port renaming
        ir_edges = []
        for edge in flow_graph.edges:
            src_node = flow_graph.nodes[edge.src_node]
            dst_node = flow_graph.nodes[edge.dst_node]

            # Get port types
            src_port_type = src_node.output_ports.get(edge.src_port)
            dst_port_type = dst_node.input_ports.get(edge.dst_port)

            if src_port_type is None:
                raise IRError(
                    ErrCode.IR_VAL_PORT_NOT_FOUND,
                    f"Source port '{edge.src_port}' missing",
                    node=edge.src_node,
                )
            if dst_port_type is None:
                raise IRError(
                    ErrCode.IR_VAL_PORT_NOT_FOUND,
                    f"Dest port '{edge.dst_port}' missing",
                    node=edge.dst_node,
                )

            if src_port_type != dst_port_type:
                raise IRError(
                    ErrCode.IR_VAL_TYPE_MISMATCH,
                    f"Type mismatch: {edge.src_node}.{edge.src_port}({type_to_str(src_port_type)}) -> "
                    f"{edge.dst_node}.{edge.dst_port}({type_to_str(dst_port_type)})",
                )

            # Determine destination port name (rename for fan-in)
            dst_port_key = (edge.dst_node, edge.dst_port)
            if dst_port_key in fan_in_ports:
                ir_dst_port = IR.make_fan_in_port(edge.src_node, edge.dst_port)
            else:
                ir_dst_port = edge.dst_port

            ir_edges.append(
                IREdge(
                    id=repr(edge),
                    type=type_to_str(src_port_type),
                    source=IREdgeSource(node=edge.src_node, port=edge.src_port),
                    destination=IREdgeDestination(node=edge.dst_node, port=ir_dst_port),
                    adapter=edge.metadata.get("adapter", {}),
                    qsize=edge.metadata.get("qsize", 10),
                    on_full=edge.metadata.get("on_full"),
                )
            )

        return ir_edges

    def _validate_fan_in(
        self, flow_graph: PipelineGraph, dst_node: str, dst_port: str, edges: list
    ) -> None:
        """Validate fan-in consistency."""
        if len(edges) < 2:
            return
        ref_edge = edges[0]
        ref_src = flow_graph.nodes[ref_edge.src_node]
        ref_type = ref_src.output_ports.get(ref_edge.src_port)
        ref_adapter = ref_edge.metadata.get("adapter", {})

        for edge in edges[1:]:
            src_node = flow_graph.nodes[edge.src_node]
            edge_type = src_node.output_ports.get(edge.src_port)
            edge_adapter = edge.metadata.get("adapter", {})

            if edge_type != ref_type:
                raise IRError(
                    ErrCode.IR_VAL_TYPE_MISMATCH,
                    f"Fan-in type mismatch on {dst_node}.{dst_port}",
                )
            if edge_adapter != ref_adapter:
                raise IRError(
                    ErrCode.IR_VAL_INVALID,
                    f"Fan-in adapter mismatch on {dst_node}.{dst_port}",
                )

    def _build_service_edges(self, ir_nodes: List[IRNode]) -> List[IREdge]:
        """Build service request/response edges."""
        edges = []
        for node in ir_nodes:
            for caller in node.service_callers:
                adapter = {"latest": {"buffer_size": 1}}
                # Request
                edges.append(
                    IREdge(
                        id=f"{node.id}._request_out->{caller.target_node}._request_in/{node.id}",
                        type="bytes",
                        source=IREdgeSource(node=node.id, port="_request_out"),
                        destination=IREdgeDestination(
                            node=caller.target_node, port=f"_request_in/{node.id}"
                        ),
                        adapter=adapter,
                        qsize=10,
                    )
                )
                # Response
                edges.append(
                    IREdge(
                        id=f"{caller.target_node}._response_out->{node.id}._response_in/{caller.target_node}",
                        type="bytes",
                        source=IREdgeSource(
                            node=caller.target_node, port="_response_out"
                        ),
                        destination=IREdgeDestination(
                            node=node.id, port=f"_response_in/{caller.target_node}"
                        ),
                        adapter=adapter,
                        qsize=10,
                    )
                )
        return edges

    def _build_topology(self, flow_graph: PipelineGraph) -> IRTopology:
        """Build IRTopology."""
        return IRTopology(
            sources=flow_graph.find_sources(),
            sinks=flow_graph.find_sinks(),
            groups=flow_graph.get_topological_groups(),
            node_count=flow_graph.get_node_count(),
            edge_count=flow_graph.get_edge_count(),
            has_cycle=flow_graph.has_cycles(),
            is_connected=flow_graph.is_connected(),
        )

    def _add_service_ports(self, ir_nodes: List[IRNode]) -> None:
        """Mutate nodes to add service ports."""
        handler_callers = {}
        for node in ir_nodes:
            for caller in node.service_callers:
                handler_callers.setdefault(caller.target_node, []).append(node.id)

        for node in ir_nodes:
            if node.service_callers:
                node.outputs["_request_out"] = "bytes"
                for caller in node.service_callers:
                    node.inputs[f"_response_in/{caller.target_node}"] = "bytes"
            if node.service_handlers:
                node.outputs["_response_out"] = "bytes"
                for caller_id in handler_callers.get(node.id, []):
                    node.inputs[f"_request_in/{caller_id}"] = "bytes"

    # --- Static Extraction Helpers ---

    @staticmethod
    def _extract_service_handlers(flow_class: type) -> List[IRServiceHandler]:
        handlers = getattr(flow_class, "__flow_service_handlers__", [])
        return [
            IRServiceHandler(
                service_id=h.descriptor.service_id, method=h.descriptor.method_name
            )
            for h in handlers
        ]

    @staticmethod
    def _extract_service_methods(flow_class: type) -> List[ServiceMethod]:
        return getattr(flow_class, "__flow_service_callers__", [])

    @staticmethod
    def _build_handler_index(ir_nodes: List[IRNode]) -> Dict[str, str]:
        handlers = {}
        for node in ir_nodes:
            for h in node.service_handlers:
                if h.service_id in handlers:
                    raise IRError(
                        ErrCode.IR_VAL_DUPLICATE_SERVICE,
                        f"Duplicate service: {h.service_id}",
                    )
                handlers[h.service_id] = node.id
        return handlers

    @staticmethod
    def _resolve_service_callers(
        node_id: str, methods: List[ServiceMethod], handlers: Dict[str, str]
    ) -> List[IRServiceCaller]:
        callers = []
        for m in methods:
            sid = m.descriptor.service_id
            if sid not in handlers:
                raise IRError(
                    ErrCode.IR_VAL_SERVICE_NOT_FOUND, f"Unknown service: {sid}"
                )
            callers.append(IRServiceCaller(service_id=sid, target_node=handlers[sid]))
        return callers

    def __repr__(self) -> str:
        return (
            f"PipelineBuilder(name='{self._name}', "
            f"handles={len(self._handles)}, "
            f"connections={len(self._connections)})"
        )
