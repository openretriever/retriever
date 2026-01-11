"""
FlowConfig for configuring flow execution parameters.

FlowConfig encapsulates execution metadata for a flow.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple, Literal, Union
from enum import Enum

from retriever.error import FlowError, ErrCode

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.clock import Clock
    from retriever.flow.temporal import TemporalFlow
    from retriever.flow.adapter import Adapter


@dataclass
class EdgeConfig:
    """
    Per-port edge configuration for buffer and sync behavior.
    
    Used in FlowHandle.then() to configure individual input ports:
    - qsize: Buffer size for this port
    - on_full: Policy when buffer is full ("drop" or "block")
    - adapter: Optional sync adapter override for this port
    
    Example:
        cam.then(planner, edge_config={
            "frame": EdgeConfig(qsize=100, on_full="drop"),
            "timestamp": EdgeConfig(qsize=10),
        })
    """
    qsize: int = 10
    on_full: Literal["drop", "block"] = "drop"
    adapter: Optional['Adapter'] = None
    
    def __post_init__(self):
        if self.qsize < 1:
            raise FlowError(
                ErrCode.FLOW_INVALID,
                "EdgeConfig qsize must be >= 1",
                qsize=self.qsize,
            )
        if self.on_full not in ("drop", "block"):
            raise FlowError(
                ErrCode.FLOW_INVALID,
                f"EdgeConfig on_full must be 'drop' or 'block', got '{self.on_full}'",
            )


@dataclass
class FlowRateConfig:
    """
    Rate configuration for a Flow class.
    
    This dataclass defines rate metadata that clocks (DefaultRate, AdaptiveRate)
    can read at wiring time for validation and defaults.
    
    Attributes:
        default_rate: Default execution frequency in Hz
        rate_range: Valid range (min_hz, max_hz) for execution rate
        enforce_default: If True, only DefaultRate() is allowed (no explicit Rate())
        enforce_range: If True, any Rate must be within rate_range
    
    Example:
        class CameraFlow(Flow[In, Out]):
            rate_config = FlowRateConfig(
                default_rate=30.0,
                rate_range=(10.0, 60.0),
                enforce_range=True,
            )
    """
    default_rate: Optional[float] = None
    rate_range: Optional[Tuple[float, float]] = None
    enforce_default: bool = False  # If True, must use DefaultRate()
    enforce_range: bool = False    # If True, must stay within rate_range
    
    def __post_init__(self):
        """Validate configuration."""
        if self.default_rate is not None and self.default_rate <= 0:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "default_rate must be positive",
                default_rate=self.default_rate,
            )
        
        if self.rate_range is not None:
            min_hz, max_hz = self.rate_range
            if min_hz <= 0 or max_hz <= 0:
                raise FlowError(
                    ErrCode.FLOW_CLOCK_INVALID,
                    "rate_range values must be positive",
                    rate_range=self.rate_range,
                )
            if min_hz > max_hz:
                raise FlowError(
                    ErrCode.FLOW_CLOCK_INVALID,
                    "rate_range min must be <= max",
                    rate_range=self.rate_range,
                )
            
            # Validate default_rate is within range if both specified
            if self.default_rate is not None:
                if not (min_hz <= self.default_rate <= max_hz):
                    raise FlowError(
                        ErrCode.FLOW_CLOCK_INVALID,
                        f"default_rate ({self.default_rate}) must be within "
                        f"rate_range ({min_hz}, {max_hz})",
                    )
        
        # enforce_default requires default_rate
        if self.enforce_default and self.default_rate is None:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "enforce_default=True requires default_rate to be set",
            )
        
        # enforce_range requires rate_range
        if self.enforce_range and self.rate_range is None:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "enforce_range=True requires rate_range to be set",
            )


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
        resources: Comprehensive resource specification
    """

    clock: 'Clock'
    resources: Optional[ResourceSpec] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.resources is None:
             self.resources = ResourceSpec()

    def to_dict(self):
        """
        Convert config to dict with clock serialized.

        Returns:
            Dict with clock converted to dict format
        """
        from retriever.utils import as_tagged
        return {
            'clock': as_tagged(self.clock),
            'resources': self.resources.to_dict() if self.resources else None
        }

    def __rmatmul__(self, flow: 'Flow') -> 'TemporalFlow':
        """
        Bind flow to this config using @ operator.

        Args:
            flow: Flow instance to bind

        Returns:
            TemporalFlow with this configuration
        """
        from retriever.flow.temporal import TemporalFlow
        return TemporalFlow(flow=flow, config=self)
