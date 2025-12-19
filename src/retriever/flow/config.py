"""
FlowConfig for configuring flow execution parameters.

FlowConfig encapsulates execution metadata for a flow.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from enum import Enum

from retriever.error import FlowError, ErrCode

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.clock import Clock
    from retriever.flow.handle import FlowHandle


class ResourceType(Enum):
    """Standard resource types"""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    GPU_MEMORY = "gpu_memory"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class ResourceSpec:
    """
    Resource specification for a Flow.
    
    Ported from legacy core to provide comprehensive resource management.
    """
    cpu: float = 1.0  # Number of CPU cores (can be fractional)
    gpu: float = 0.0  # Number of GPUs (can be fractional for sharing)
    memory: float = 1.0  # Memory in GB
    gpu_memory: float = 0.0  # GPU memory in GB
    disk: float = 0.0  # Disk space in GB
    
    # Custom resources (e.g., custom hardware, licenses)
    custom: Dict[str, float] = field(default_factory=dict)
    
    # Deployment constraints
    node_type: Optional[str] = None  # "cpu", "gpu", "edge", "cloud"
    host_affinity: Optional[List[str]] = None  # Preferred hosts
    max_runtime: Optional[float] = None  # Maximum runtime in seconds
    priority: int = 0
    preemptible: bool = True

    def __post_init__(self):
        if self.host_affinity is None:
            self.host_affinity = []
        
        # Auto-detect node type only if not set
        if self.node_type is None:
            if self.gpu > 0:
                self.node_type = "gpu"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu": self.cpu,
            "gpu": self.gpu,
            "memory": self.memory,
            "gpu_memory": self.gpu_memory,
            "disk": self.disk,
            "custom": self.custom,
            "node_type": self.node_type,
            "host_affinity": self.host_affinity,
            "max_runtime": self.max_runtime,
            "priority": self.priority,
            "preemptible": self.preemptible,
        }


@dataclass
class FlowConfig:
    """
    Configuration for flow execution.

    Attributes:
        clock: Execution clock (Rate, Trigger, or Hybrid)
        priority: Optional execution priority (deprecated, use resources.priority)
        cpu_affinity: Optional CPU cores binding (deprecated, use resources)
        memory_size: Optional memory limit in MB (deprecated, use resources.memory in GB)
        resources: Comprehensive resource specification
    """

    clock: 'Clock'
    priority: Optional[int] = None
    cpu_affinity: Optional[List[int]] = None
    memory_size: Optional[float] = None
    resources: Optional[ResourceSpec] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        # Initialize resources if not present but legacy fields are used
        if self.resources is None:
            # Default fallback if no resources specified
            self.resources = ResourceSpec()
            
            # Map legacy fields to new ResourceSpec if provided
            if self.priority is not None:
                self.resources.priority = self.priority
            
            if self.memory_size is not None:
                # Legacy memory_size is MB, ResourceSpec is GB
                self.resources.memory = self.memory_size / 1024.0

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
            'memory_size': self.memory_size,
            'resources': self.resources.to_dict() if self.resources else None
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
