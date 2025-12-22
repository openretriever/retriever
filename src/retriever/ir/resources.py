"""
Resource Management for Flows - Ray-style Resource Annotations

This module provides resource annotations for Flows to specify:
- CPU requirements (number of cores)
- GPU requirements (number of GPUs, GPU memory)
- Memory requirements (RAM in GB)
- Custom resource requirements
- Deployment constraints (host affinity, etc.)

Inspired by Ray's resource model but adapted for robotics workflows.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
from enum import Enum

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
    """Resource specification for a Flow"""
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
    
    # Priority and scheduling
    priority: int = 0  # Higher priority = scheduled first
    preemptible: bool = True  # Can be preempted by higher priority tasks
    
    def __post_init__(self):
        if self.host_affinity is None:
            self.host_affinity = []
        
        # Auto-detect node type based on GPU requirements
        if self.node_type is None:
            if self.gpu > 0:
                self.node_type = "gpu"
            else:
                self.node_type = "cpu"
    
    def requires_gpu(self) -> bool:
        """Check if this spec requires GPU resources"""
        return self.gpu > 0 or self.gpu_memory > 0
    
    def total_memory(self) -> float:
        """Get total memory requirement (RAM + GPU memory)"""
        return self.memory + self.gpu_memory
    
    def merge(self, other: 'ResourceSpec') -> 'ResourceSpec':
        """Merge two resource specs (sum requirements)"""
        merged_custom = {**self.custom, **other.custom}
        for key in self.custom.keys() & other.custom.keys():
            merged_custom[key] = self.custom[key] + other.custom[key]
        
        return ResourceSpec(
            cpu=self.cpu + other.cpu,
            gpu=self.gpu + other.gpu,
            memory=self.memory + other.memory,
            gpu_memory=self.gpu_memory + other.gpu_memory,
            disk=self.disk + other.disk,
            custom=merged_custom,
            priority=max(self.priority, other.priority),
            preemptible=self.preemptible and other.preemptible
        )
    
    def can_run_on(self, available: 'ResourceSpec') -> bool:
        """Check if this spec can run on available resources"""
        if self.cpu > available.cpu:
            return False
        if self.gpu > available.gpu:
            return False
        if self.memory > available.memory:
            return False
        if self.gpu_memory > available.gpu_memory:
            return False
        if self.disk > available.disk:
            return False
        
        # Check custom resources
        for resource, amount in self.custom.items():
            if amount > available.custom.get(resource, 0):
                return False
        
        return True

# Predefined resource specs for common robotics workloads
class ResourcePresets:
    """Predefined resource specifications for common robotics tasks"""
    
    # Basic CPU workloads
    CPU_LIGHT = ResourceSpec(cpu=1, memory=1)  # Sensor reading, basic processing
    CPU_MEDIUM = ResourceSpec(cpu=2, memory=4)  # Path planning, moderate computation
    CPU_HEAVY = ResourceSpec(cpu=4, memory=8)  # Complex algorithms, optimization
    
    # GPU workloads for ML/vision
    GPU_INFERENCE = ResourceSpec(cpu=2, gpu=0.25, memory=4, gpu_memory=2)  # Model inference
    GPU_LIGHT = ResourceSpec(cpu=2, gpu=0.5, memory=8, gpu_memory=4)  # Light ML workloads
    GPU_MEDIUM = ResourceSpec(cpu=4, gpu=1, memory=16, gpu_memory=8)  # Standard vision/ML
    GPU_HEAVY = ResourceSpec(cpu=8, gpu=2, memory=32, gpu_memory=16)  # Heavy ML, training
    
    # Edge computing
    EDGE_SENSOR = ResourceSpec(cpu=0.5, memory=0.5, node_type="edge")  # Edge sensors
    EDGE_COMPUTE = ResourceSpec(cpu=2, memory=2, node_type="edge")  # Edge processing
    
    # Real-time constraints
    REALTIME_CONTROL = ResourceSpec(cpu=1, memory=1, max_runtime=0.01, priority=10)  # 10ms max
    SOFT_REALTIME = ResourceSpec(cpu=2, memory=2, max_runtime=0.1, priority=5)  # 100ms max
    
    # Custom robotics resources
    CAMERA_EXCLUSIVE = ResourceSpec(cpu=1, memory=2, custom={"camera": 1})
    LIDAR_PROCESSING = ResourceSpec(cpu=4, memory=8, custom={"lidar": 1})
    ROBOT_ARM = ResourceSpec(cpu=2, memory=4, custom={"robot_arm": 1})

def resource_spec(
    cpu: float = 1.0,
    gpu: float = 0.0, 
    memory: float = 1.0,
    gpu_memory: float = 0.0,
    disk: float = 0.0,
    custom: Optional[Dict[str, float]] = None,
    node_type: Optional[str] = None,
    host_affinity: Optional[List[str]] = None,
    max_runtime: Optional[float] = None,
    priority: int = 0,
    preemptible: bool = True
) -> ResourceSpec:
    """Convenience function to create ResourceSpec"""
    return ResourceSpec(
        cpu=cpu, gpu=gpu, memory=memory, gpu_memory=gpu_memory, disk=disk,
        custom=custom or {}, node_type=node_type, host_affinity=host_affinity,
        max_runtime=max_runtime, priority=priority, preemptible=preemptible
    )

# Decorator for easy resource annotation
def requires(**kwargs) -> ResourceSpec:
    """Decorator to specify resource requirements for a Flow class
    
    Usage:
        @requires(cpu=2, gpu=1, memory=8)
        class VisionFlow(Flow[RGBImage, List[Detection]]):
            pass
    """
    spec = resource_spec(**kwargs)
    
    def decorator(cls):
        cls._resource_spec = spec
        return cls
    
    return decorator

class ResourceManager:
    """Manages resource allocation and scheduling for Flow execution"""
    
    def __init__(self):
        self.available_resources: Dict[str, ResourceSpec] = {}
        self.allocated_resources: Dict[str, ResourceSpec] = {}
        self.pending_flows: List[tuple] = []  # (flow, spec, callback)
    
    def register_node(self, node_id: str, resources: ResourceSpec):
        """Register available resources for a compute node"""
        self.available_resources[node_id] = resources
        self.allocated_resources[node_id] = ResourceSpec()  # Start with no allocation
    
    def allocate_resources(self, flow_id: str, spec: ResourceSpec) -> Optional[str]:
        """Try to allocate resources for a flow. Returns node_id if successful."""
        
        # Find a node that can accommodate this flow
        for node_id, available in self.available_resources.items():
            allocated = self.allocated_resources[node_id]
            remaining = ResourceSpec(
                cpu=available.cpu - allocated.cpu,
                gpu=available.gpu - allocated.gpu,
                memory=available.memory - allocated.memory,
                gpu_memory=available.gpu_memory - allocated.gpu_memory,
                disk=available.disk - allocated.disk,
                custom={k: available.custom.get(k, 0) - allocated.custom.get(k, 0) 
                       for k in available.custom.keys() | allocated.custom.keys()}
            )
            
            if spec.can_run_on(remaining):
                # Allocate resources
                self.allocated_resources[node_id] = allocated.merge(spec)
                return node_id
        
        return None  # No suitable node found
    
    def deallocate_resources(self, node_id: str, spec: ResourceSpec):
        """Deallocate resources when a flow completes"""
        if node_id in self.allocated_resources:
            allocated = self.allocated_resources[node_id]
            # Subtract the resources (simplified - in practice needs more careful handling)
            self.allocated_resources[node_id] = ResourceSpec(
                cpu=max(0, allocated.cpu - spec.cpu),
                gpu=max(0, allocated.gpu - spec.gpu),
                memory=max(0, allocated.memory - spec.memory),
                gpu_memory=max(0, allocated.gpu_memory - spec.gpu_memory),
                disk=max(0, allocated.disk - spec.disk),
                custom={k: max(0, allocated.custom.get(k, 0) - spec.custom.get(k, 0))
                       for k in allocated.custom.keys() | spec.custom.keys()}
            )
    
    def get_resource_utilization(self) -> Dict[str, Dict[str, float]]:
        """Get current resource utilization across all nodes"""
        utilization = {}
        
        for node_id in self.available_resources:
            available = self.available_resources[node_id]
            allocated = self.allocated_resources[node_id]
            
            utilization[node_id] = {
                "cpu": allocated.cpu / available.cpu if available.cpu > 0 else 0,
                "gpu": allocated.gpu / available.gpu if available.gpu > 0 else 0,
                "memory": allocated.memory / available.memory if available.memory > 0 else 0,
                "gpu_memory": allocated.gpu_memory / available.gpu_memory if available.gpu_memory > 0 else 0,
            }
        
        return utilization

# Global resource manager instance
_global_resource_manager = ResourceManager()

def get_resource_manager() -> ResourceManager:
    """Get the global resource manager"""
    return _global_resource_manager