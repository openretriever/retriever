"""
FlowConfig for configuring flow execution parameters.

FlowConfig encapsulates execution metadata for a flow.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, List

from retriever.error import FlowError, ErrCode

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.clock import Clock
    from retriever.flow.handle import FlowHandle


@dataclass
class FlowConfig:
    """
    Configuration for flow execution.

    Attributes:
        clock: Execution clock (Rate, Trigger, or Hybrid)
        priority: Optional execution priority
        cpu_affinity: Optional CPU cores binding
        memory_size: Optional memory limit in MB
    """

    clock: 'Clock'
    priority: Optional[int] = None
    cpu_affinity: Optional[List[int]] = None
    memory_size: Optional[float] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate cpu_affinity values
        if self.cpu_affinity is not None:
            for core in self.cpu_affinity:
                if core < 0:
                    raise FlowError(
                        ErrCode.FLOW_CONFIG_INVALID,
                        f"cpu_affinity must contain non-negative integers",
                        cpu_affinity=self.cpu_affinity
                    )

        # Validate memory_size
        if self.memory_size is not None and self.memory_size < 0:
            raise FlowError(
                ErrCode.FLOW_CONFIG_INVALID,
                "memory_size must be non-negative",
                memory_size=self.memory_size
            )

    def to_dict(self):
        """
        Convert config to dict with clock serialized.

        Returns:
            Dict with clock converted to dict format
        """
        from retriever.utils import as_tagged
        return {
            'clock': as_tagged(self.clock),
            'priority': self.priority,
            'cpu_affinity': self.cpu_affinity,
            'memory_size': self.memory_size
        }

    def __rmatmul__(self, flow: 'Flow') -> 'FlowHandle':
        """
        Bind flow to this config using @ operator.

        Args:
            flow: Flow instance to bind

        Returns:
            FlowHandle with this configuration
        """
        from retriever.flow.handle import FlowHandle
        return FlowHandle(flow=flow, config=self)
