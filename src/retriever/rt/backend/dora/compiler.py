"""
Dora Compiler - Compile IRStruct to Dora dataflow YAML.

Converts validated IR graph structure to dora-rs compatible YAML.

Native acceleration support:
- The compiler can optionally override per-node `path` so some nodes are started
  as native dora nodes (Rust binaries) instead of Python "dynamic" nodes.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Union

import yaml
from retriever.flow.clock import Clock, Hybrid, Rate, Trigger
from retriever.ir.struct import IRNode, IRStruct

logger = logging.getLogger(__name__)


@dataclass
class DoraInput:
    """
    Dora input specification.

    Can be either:
    - Simple string (e.g., "dora/timer/millis/1000")
    - Dict with source and queue_size (e.g., {"source": "NodeA/port", "queue_size": 10})
    """
    source: str
    queue_size: int = None

    def to_yaml_value(self) -> Union[str, Dict[str, Any]]:
        """Convert to YAML-compatible value."""
        if self.queue_size is None:
            return self.source
        return {
            'source': self.source,
            'queue_size': self.queue_size
        }


@dataclass
class DoraNode:
    """
    Dora node specification.

    Attributes:
        id: Unique node identifier
        source: Source type (always 'dynamic' for Python processes)
        inputs: Dict mapping input port names to DoraInput
        outputs: List of output port names
    """
    id: str
    source: str
    inputs: Dict[str, DoraInput]
    outputs: List[str]
    deploy: Optional[Dict[str, str]] = None


    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to YAML-compatible dict."""
        d = {
            'id': self.id,
            'path': self.source,
            'inputs': {
                name: inp.to_yaml_value()
                for name, inp in self.inputs.items()
            },
            'outputs': self.outputs
        }
        if self.deploy:
            d['_unstable_deploy'] = self.deploy
        return d


@dataclass
class DoraGraph:
    """
    Dora dataflow graph.

    Attributes:
        nodes: List of DoraNode in the dataflow
    """
    nodes: List[DoraNode]

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to YAML-compatible dict."""
        return {
            'nodes': [node.to_yaml_dict() for node in self.nodes]
        }


def compile_to_yaml(ir: IRStruct) -> str:
    """
    Compile IRStruct to dora dataflow YAML.

    Converts validated IR graph into dora-compatible YAML format:
    - Each IRNode → DoraNode with dynamic source
    - Each IREdge → DoraInput in inputs with queue_size
    - Rate/Hybrid clocks → dora/timer inputs

    Args:
        ir: Validated IRStruct

    Returns:
        YAML string ready to write to file
    """
    logger.info(f"Compiling IR to dora YAML: '{ir.metadata.name}'")

    # Compile IR to DoraGraph
    dora_graph = _compile_graph(ir, node_path_overrides=None)

    # Convert to YAML
    yaml_str = yaml.dump(
        dora_graph.to_yaml_dict(),
        default_flow_style=False,
        sort_keys=False
    )

    # Add header comment
    header = f"""# Dora Dataflow YAML
# Generated from: {ir.metadata.name}
# Nodes: {len(ir.nodes)}, Edges: {len(ir.edges)}

"""

    logger.info(f"Compiled {len(dora_graph.nodes)} nodes to YAML")
    return header + yaml_str


def resolve_node_path(
    node: IRNode,
    node_path_overrides: Optional[Mapping[str, Any]],
) -> str:
    """
    Resolve the dora `path` for an IR node.

    Default: "dynamic" (Python executor started externally).

    Overrides are matched by (in priority order):
      1) node.id
      2) "{module}:{type}"
      3) type

    Override values can be:
      - a string path
      - a dict with a `path` field
    """
    if not node_path_overrides:
        return "dynamic"

    keys = (
        node.id,
        f"{node.module}:{node.type}",
        node.type,
    )
    for key in keys:
        if key not in node_path_overrides:
            continue
        spec = node_path_overrides[key]
        if isinstance(spec, str):
            return spec
        if isinstance(spec, dict):
            path = spec.get("path")
            if not isinstance(path, str) or not path:
                raise ValueError(f"Invalid native override for {key!r}: missing string `path`")
            return path
        raise TypeError(f"Invalid native override for {key!r}: expected str or dict, got {type(spec)}")

    return "dynamic"


def get_node_paths(
    ir: IRStruct,
    *,
    node_path_overrides: Optional[Mapping[str, Any]],
) -> Dict[str, str]:
    """Return a node_id -> dora path mapping for this IR."""
    return {node.id: resolve_node_path(node, node_path_overrides) for node in ir.nodes}


def _compile_graph(
    ir: IRStruct, 
    *, 
    node_path_overrides: Optional[Mapping[str, Any]],
    deployment_overrides: Optional[Mapping[str, str]] = None
) -> DoraGraph:
    """
    Compile IRStruct to DoraGraph.

    Args:
        ir: Validated IRStruct

    Returns:
        DoraGraph with all nodes compiled
    """
    dora_nodes = []
    for node in ir.nodes:
        dora_node = _compile_node(
            node, 
            ir, 
            node_path_overrides=node_path_overrides,
            deployment_overrides=deployment_overrides
        )
        dora_nodes.append(dora_node)

    return DoraGraph(nodes=dora_nodes)


def _compile_node(
    node: IRNode, 
    ir: IRStruct, 
    *, 
    node_path_overrides: Optional[Mapping[str, Any]] = None,
    deployment_overrides: Optional[Mapping[str, str]] = None
) -> DoraNode:
    """
    Compile IRNode to DoraNode.


    Args:
        node: IR node to compile
        ir: Full IR structure (for edge lookup)

    Returns:
        DoraNode with inputs, outputs, and queue sizes
    """
    inputs = {}

    # Add clock-based inputs (timer)
    clock = _extract_clock(node.config)
    if clock:
        _add_clock_inputs(inputs, clock)

    # Add edge-based inputs with queue_size
    for edge in ir.get_incoming_edges(node.id):
        port_name = edge.destination.port
        source_spec = f"{edge.source.node}/{edge.source.port}"
        inputs[port_name] = DoraInput(
            source=source_spec,
            queue_size=edge.qsize
        )

    # Get outputs
    outputs = list(node.outputs.keys())


    path = resolve_node_path(node, node_path_overrides)

    # Resolve deployment
    # Priority:
    # 1. Runtime override (deployment_overrides)
    # 2. Compile-time affinity (ResourceSpec.host_affinity)
    
    deploy = None
    
    # Check overrides first
    if deployment_overrides and node.id in deployment_overrides:
        deploy = {'machine': deployment_overrides[node.id]}
    # Check affinity second
    elif node.config.get('resources'):

        # ResourceSpec is dict in IRNode.config
        resources = node.config['resources']
        # Check host_affinity
        affinity = resources.get('host_affinity')
        if affinity and isinstance(affinity, list) and len(affinity) > 0:
            # Map first affinity host to machine
            deploy = {'machine': affinity[0]}

    dora_node = DoraNode(
        id=node.id,
        source=path,
        inputs=inputs,
        outputs=outputs,
        deploy=deploy
    )

    logger.debug(
        f"Compiled node {node.id}: "
        f"{len(inputs)} inputs, {len(outputs)} outputs"
    )

    return dora_node


def _extract_clock(config: Dict[str, Any]) -> Clock:
    """Extract Clock object from node config."""
    from retriever.ir.loader import IRLoader

    try:
        return IRLoader.load_clock(config)
    except Exception as e:
        logger.warning(f"Failed to load clock from config: {e}")
        return None


def _add_clock_inputs(inputs: Dict[str, DoraInput], clock: Clock) -> None:
    """
    Add clock-based timer inputs.

    For Rate/Hybrid clocks, adds dora timer input (no queue_size needed).

    Args:
        inputs: Node inputs dict (modified in place)
        clock: Clock configuration
    """
    if isinstance(clock, Rate):
        interval_ms = int(1000 / clock.hz)
        inputs['tick'] = DoraInput(
            source=f"dora/timer/millis/{interval_ms}",
            queue_size=None  # Timer inputs don't need queue_size
        )
        logger.debug(f"Added Rate timer: {clock.hz} Hz -> {interval_ms} ms")

    elif isinstance(clock, Hybrid):
        interval_ms = int(1000 / clock.hz)
        inputs['tick'] = DoraInput(
            source=f"dora/timer/millis/{interval_ms}",
            queue_size=None
        )
        logger.debug(f"Added Hybrid timer: {clock.hz} Hz -> {interval_ms} ms")

    elif isinstance(clock, Trigger):
        # Trigger-only: no timer needed
        logger.debug("Trigger clock: no timer input")

    else:
        logger.warning(f"Unknown clock type: {type(clock)}")


def _validate_yaml(yaml_str: str) -> bool:
    """
    Validate generated YAML can be parsed.

    Args:
        yaml_str: YAML string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = yaml.safe_load(yaml_str)

        # Basic validation
        if 'nodes' not in parsed:
            logger.error("YAML missing 'nodes' field")
            return False

        if not isinstance(parsed['nodes'], list):
            logger.error("YAML 'nodes' must be a list")
            return False

        # Validate each node has required fields
        for i, node in enumerate(parsed['nodes']):
            if 'id' not in node:
                logger.error(f"Node {i} missing 'id' field")
                return False

            if 'path' not in node:
                logger.error(f"Node {node['id']} missing 'path' field")
                return False

        logger.debug("YAML validation passed")
        return True

    except yaml.YAMLError as e:
        logger.error(f"YAML parse error: {e}")
        return False


def compile_and_validate(
    ir: IRStruct, 
    *, 
    node_path_overrides: Optional[Mapping[str, Any]] = None,
    deployment_overrides: Optional[Mapping[str, str]] = None
) -> str:

    """
    Compile IR to YAML and validate it.

    Args:
        ir: IRStruct to compile

    Returns:
        Validated YAML string

    Raises:
        ValueError: If YAML compilation or validation fails
    """
    # Compile IR to DoraGraph with optional node path overrides
    dora_graph = _compile_graph(
        ir, 
        node_path_overrides=node_path_overrides, 
        deployment_overrides=deployment_overrides
    )


    # Convert to YAML
    yaml_str = yaml.dump(
        dora_graph.to_yaml_dict(),
        default_flow_style=False,
        sort_keys=False
    )

    # Add header comment
    header = f"""# Dora Dataflow YAML
# Generated from: {ir.metadata.name}
# Nodes: {len(ir.nodes)}, Edges: {len(ir.edges)}

"""

    yaml_str = header + yaml_str

    if not _validate_yaml(yaml_str):
        raise ValueError("Generated YAML failed validation")

    return yaml_str
