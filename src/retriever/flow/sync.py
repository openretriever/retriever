"""
Synchronization primitives for aligning multiple data streams.
"""

from dataclasses import dataclass, fields, is_dataclass
from typing import TypeVar, Generic, Dict, Optional, List, Any, Union
import time

from retriever.flow.base import Flow
from retriever.error import FlowError, ErrCode

In = TypeVar("In")
Out = TypeVar("Out")

class Synchronizer(Flow[In, Out]):
    """
    Base class for synchronizing multiple input streams by timestamp.
    
    It buffers incoming messages from the Input dataclass (which must have Optional fields)
    and emits the Output dataclass ONLY when a complete set of matching timestamps is found.
    
    Usage:
        class MySync(Synchronizer[MyInput, MyOutput]):
            pass
            
        # Or with custom policy args if we added __init__ params later
    """
    
    def __init__(self, stream_fields: Optional[List[str]] = None, tolerance: float = 0.0):
        """
        Args:
            stream_fields: List of field names in `In` to synchronize. 
                           If None, will try to sync ALL fields found in `In`.
            tolerance: Max time difference to consider "approximate match". 
                       0.0 means Exact Match (using float equality).
        """
        self.stream_fields = stream_fields
        self.tolerance = tolerance
        
    def reset(self):
        # field_name -> {timestamp: value}
        self.buffers: Dict[str, Dict[float, Any]] = {}
        
        # Identify fields to sync if not provided
        if self.stream_fields is None:
            if not is_dataclass(self.input_type):
                 raise FlowError(ErrCode.FLOW_TYPE_NOT_COMPATIBLE, "Input type must be a dataclass")
            
            # We assume all fields in the Input dataclass are potential streams
            self.stream_fields = [f.name for f in fields(self.input_type)]

        for f in self.stream_fields:
            self.buffers[f] = {}
            
    def _get_timestamp(self, value: Any) -> Optional[float]:
        """Extract timestamp from an object. Defaults to .timestamp field."""
        if hasattr(value, "timestamp"):
            return float(value.timestamp)
        return None

    def step(self, input: In) -> Optional[Out]:
        # 1. Ingest
        for field in self.stream_fields:
            val = getattr(input, field, None)
            if val is not None:
                ts = self._get_timestamp(val)
                if ts is not None:
                    self.buffers[field][ts] = val
        
        # 2. Find Intersection (Exact Match for now)
        # We look for a timestamp that exists in ALL buffers
        
        # Optimization: Start with keys from the first buffer
        first_field = self.stream_fields[0]
        candidates = set(self.buffers[first_field].keys())
        
        for field in self.stream_fields[1:]:
            candidates &= self.buffers[field].keys()
            
        if not candidates:
            return None
            
        # Found match(es). Process the oldest one first or latest? 
        # Usually we want to emit in order.
        match_ts = min(candidates)
        
        # 3. Construct Output
        # We assume Output has the same field names!
        kwargs = {}
        for field in self.stream_fields:
            kwargs[field] = self.buffers[field].pop(match_ts)
            
        # Optional: Set timestamp on output if it has one
        # If Out is a dataclass, we can check its content
        if is_dataclass(self.output_type):
             # Check if output has a 'timestamp' field
             out_fields = {f.name for f in fields(self.output_type)}
             if "timestamp" in out_fields:
                 kwargs["timestamp"] = match_ts
        
        # Pruning: Remove older timestamps to prevent memory leaks?
        # For strict exact sync, if we executed T, we can remove T.
        # But should we remove T-1? Only if we assume monotonic arrival and we won't go back.
        # Let's keep it simple: We popped the match. 
        # Pruning logic for "stuck" frames is complex (timeout based), skipping for MVP.
        
        return self.output_type(**kwargs)

