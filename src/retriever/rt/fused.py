"""
FusedFlow - Execute multiple flows in sequence without IPC overhead

Created by IR optimizer when fusion is applied.
Chains sub-flows with direct method calls and port mapping.
"""

import importlib
from typing import Any, List, Dict, Tuple
from retriever.flow.base import Flow
from retriever.flow.io import io
from retriever.error import FlowError, ErrCode

import logging
logger = logging.getLogger(__name__)


@io
class FusedAny:
    """Dynamic type placeholder for FusedFlow"""
    pass


class FusedFlow(Flow[FusedAny, FusedAny]):
    """
    Wrapper that chains multiple flows for zero-copy execution.

    Executes sub-flows in sequence with port mapping based on internal edges.
    """

    def __init__(self):
        self.sub_flows: List[Flow] = []
        self.node_ids: List[str] = []
        self.node_id_to_idx: Dict[str, int] = {}
        self.port_mappings: List[List[Tuple[str, str]]] = []

    def configure(self, fused_nodes_config: List[Dict[str, Any]],
                  internal_edges: List[Dict[str, str]]):
        """
        Load and configure sub-flows from fused node metadata.

        Args:
            fused_nodes_config: List of original node metadata
            internal_edges: List of internal edge mappings
        """
        for idx, node_data in enumerate(fused_nodes_config):
            try:
                module = importlib.import_module(node_data['module'])
                flow_class = getattr(module, node_data['type'])
                init_cfg = node_data.get("init_config", {}) or {}
                if hasattr(flow_class, "from_init_config"):
                    flow_instance = flow_class.from_init_config(init_cfg)  # type: ignore[attr-defined]
                else:
                    flow_instance = flow_class(**init_cfg) if init_cfg else flow_class()

                self.sub_flows.append(flow_instance)
                self.node_ids.append(node_data['id'])
                self.node_id_to_idx[node_data['id']] = idx

                logger.debug(f"Loaded sub-flow [{idx}]: {node_data['id']} ({node_data['type']})")

            except Exception as e:
                raise FlowError(
                    ErrCode.FLOW_INVALID,
                    f"Failed to load fused sub-flow {node_data['id']}: {e}",
                    node_id=node_data['id'],
                    module=node_data['module'],
                    type=node_data['type']
                )

        self._build_port_mappings(internal_edges)

        # Set input/output types from first/last sub-flows
        # This enables proper type checking and Signal.sample() to work correctly
        if self.sub_flows:
            self._input_type = self.sub_flows[0].input_type
            self._output_type = self.sub_flows[-1].output_type
            logger.debug(
                f"FusedFlow types: input={self._input_type}, output={self._output_type}"
            )

    def _build_port_mappings(self, internal_edges: List[Dict[str, str]]):
        """
        Build port mappings from internal edges.

        Creates a list where port_mappings[i] contains mappings from flow i to flow i+1.
        """
        num_flows = len(self.sub_flows)
        self.port_mappings = [[] for _ in range(num_flows - 1)]

        for edge in internal_edges:
            src_idx = self.node_id_to_idx[edge['src_node']]
            dst_idx = self.node_id_to_idx[edge['dst_node']]

            if dst_idx != src_idx + 1:
                raise FlowError(
                    ErrCode.FLOW_INVALID,
                    f"Non-sequential fusion: {edge['src_node']} -> {edge['dst_node']}",
                    src_node=edge['src_node'],
                    dst_node=edge['dst_node']
                )

            self.port_mappings[src_idx].append((edge['src_port'], edge['dst_port']))

            logger.debug(
                f"Port mapping [{src_idx}→{dst_idx}]: "
                f"{edge['src_port']} → {edge['dst_port']}"
            )

    def init(self):
        """Initialize all sub-flows in order"""
        for i, flow in enumerate(self.sub_flows):
            try:
                flow.init()
                logger.debug(f"Initialized sub-flow [{i}]: {self.node_ids[i]}")
            except Exception as e:
                raise FlowError(
                    ErrCode.FLOW_INIT_FAILED,
                    f"Sub-flow {self.node_ids[i]} init failed: {e}",
                    node_id=self.node_ids[i],
                    index=i
                )

    def run(self, input: Any) -> Any:
        """
        Chain execution through all sub-flows with port mapping.

        Args:
            input: Input from external sources (or None for source flows)

        Returns:
            Output from last sub-flow
        """
        try:
            data = self.sub_flows[0].run(input)
        except Exception as e:
            raise FlowError(
                ErrCode.FLOW_EXECUTION_FAILED,
                f"Sub-flow {self.node_ids[0]} execution failed: {e}",
                node_id=self.node_ids[0],
                index=0
            )

        for i in range(1, len(self.sub_flows)):
            port_mapping = self.port_mappings[i - 1]

            next_input = self._create_input_instance(
                data,
                self.sub_flows[i].input_type,
                port_mapping,
                i
            )

            try:
                data = self.sub_flows[i].run(next_input)
            except Exception as e:
                raise FlowError(
                    ErrCode.FLOW_EXECUTION_FAILED,
                    f"Sub-flow {self.node_ids[i]} execution failed: {e}",
                    node_id=self.node_ids[i],
                    index=i
                )

        return data

    def _create_input_instance(self, output_instance: Any, input_type: type,
                               port_mapping: List[Tuple[str, str]], flow_idx: int) -> Any:
        """
        Create input instance by mapping ports from output instance.

        Args:
            output_instance: Previous flow's output
            input_type: Type of next flow's input
            port_mapping: List of (src_port, dst_port) tuples
            flow_idx: Index of target flow (for error reporting)

        Returns:
            Input instance for next flow
        """
        if input_type is None:
            return None

        try:
            next_input = input_type()

            for src_port, dst_port in port_mapping:
                if hasattr(output_instance, src_port):
                    value = getattr(output_instance, src_port)
                    next_input._set_signal(dst_port, value)
                else:
                    raise FlowError(
                        ErrCode.FLOW_EXECUTION_FAILED,
                        f"Output port '{src_port}' not found in previous flow output",
                        src_port=src_port,
                        node_id=self.node_ids[flow_idx - 1]
                    )

            return next_input

        except Exception as e:
            raise FlowError(
                ErrCode.FLOW_EXECUTION_FAILED,
                f"Failed to map ports for flow {self.node_ids[flow_idx]}: {e}",
                node_id=self.node_ids[flow_idx],
                index=flow_idx
            )

    def finalize(self):
        """Finalize all sub-flows in reverse order"""
        for i, flow in reversed(list(enumerate(self.sub_flows))):
            try:
                flow.finalize()
                logger.debug(f"Finalized sub-flow [{i}]: {self.node_ids[i]}")
            except Exception as e:
                logger.warning(
                    f"Sub-flow {self.node_ids[i]} finalize failed: {e}",
                    exc_info=True
                )
