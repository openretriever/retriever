"""
Adapter module for buffer sampling strategies.

Adapters determine how messages are sampled from input buffers
for temporal alignment between cross-clock flow connections.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Any, Iterable
from typing import Type, List, Dict, Literal
from retriever.error import FlowError, ErrCode
from retriever.flow.types import Behavior, EventBuffer, EventStream
# Forward references
T = TypeVar('T')
U = TypeVar('U')

# Backward-compat alias (older code/docs/tests may still refer to TBuffer).
TBuffer = EventBuffer

# Global adapter registry
_adapter_registry: Dict[str, Type['Adapter']] = {}


@dataclass
class Adapter(ABC, Generic[T]):
    """
    Abstract base class for buffer sampling strategies.

    All adapters must specify buffer_size to control history depth.
    """
    buffer_size: int

    def __post_init__(self):
        if self.buffer_size < 1:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "buffer_size must be >= 1",
                buffer_size=self.buffer_size
            )

    @abstractmethod
    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> Any:
        """
        Apply sampling strategy to the buffer.
        
        Args:
            buffer: List of (timestamp, value) tuples
            now: Optional wall-clock timestamp associated with this sampling
            **kwargs: Future-proofing for additional execution context
            
        Returns:
            Sampled value(s) from the buffer
        """
        pass

    def sample(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> Any:
        """
        Alias for __call__ to support explicit naming.
        """
        return self(buffer, now=now, **kwargs)


# ============================================================================
# Adapter Registration
# ============================================================================

def register_adapter(name: Optional[str] = None):
    """
    Register an adapter class in the global registry.

    Args:
        name: Adapter name (defaults to class name)

    Usage:
        @register_adapter("latest")
        @dataclass
        class Latest(Adapter[T]):
            ...
    """
    def decorator(cls: Type[Adapter]) -> Type[Adapter]:
        # Validate it's an Adapter subclass
        if not issubclass(cls, Adapter):
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                f"{cls.__name__} must inherit from Adapter"
            )

        # Determine adapter name
        adapter_name = name if name is not None else cls.__name__

        # Check for name collision
        if adapter_name in _adapter_registry:
            existing = _adapter_registry[adapter_name]
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                f"Adapter '{adapter_name}' already registered to {existing.__name__}"
            )

        # Register adapter
        _adapter_registry[adapter_name] = cls
        cls.__adapter_name__ = adapter_name

        return cls

    return decorator


def get_adapter(name: str) -> Type[Adapter]:
    """Get adapter class by name."""
    if name not in _adapter_registry:
        raise FlowError(
            ErrCode.FLOW_ADAPTER_INVALID,
            f"Adapter '{name}' not found in registry. "
            f"Available adapters: {list(_adapter_registry.keys())}"
        )
    return _adapter_registry[name]


def list_adapters() -> List[str]:
    """Get all registered adapter names."""
    return list(_adapter_registry.keys())


def is_adapter(cls) -> bool:
    """Check if class is a registered adapter."""
    return hasattr(cls, '__adapter_name__')


# ============================================================================
# Built-in Adapters
# ============================================================================

@register_adapter("latest")
@dataclass
class Latest(Adapter[T]):
    """Samples the most recent value from the buffer."""
    buffer_size: int = 1

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> T:
        if not buffer:
            raise IndexError("list index out of range")
        # Use declarative method (mypy: latest can return None if empty, guarded above)
        return buffer.latest()  # type: ignore[return-value]


@register_adapter("hold")
@dataclass
class Hold(Adapter[T]):
    """
    Zero-Order Hold (ZOH) with optional debounce logic.

    **Zero-Order Hold**:
    In signal processing, a ZOH takes a discrete stream of values and reconstructs
    a continuous signal by "holding" the most recent value constant until the next
    update arrives. In this adapter, it simply means we return the latest sampled value.

    **Debounce**:
    If `debounce > 0`, this adapter implements a rate-limiting filter (or "leading edge" debounce).
    It ignores any updates that occur within `debounce` seconds of the *last accepted* update.
    This is useful for noisy streams or preventing rapid-fire triggers.

    **Logic**:
    1. New event arrives with `timestamp`.
    2. Calculate `elapsed = timestamp - last_accepted_time`.
    3. If `elapsed < debounce`: Ignore new event, return `last_accepted_value`.
    4. Else: Accept new event, update `last_accepted_time = timestamp`, return `value`.

    **WARNING: Stateful Adapter**
    This adapter maintains internal state (`_last_value`, `_last_time`).
    Do NOT reuse a single `Hold` instance across multiple different event streams (ports).
    Each connection should have its own `Hold` instance to track state correctly.
    """
    buffer_size: int = 1
    debounce: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if self.debounce < 0:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "Hold debounce must be non-negative",
                debounce=self.debounce
            )

        # Runtime state (not serde)
        self._last_value: Optional[T] = None
        self._last_time: float = 0.0

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> T:

        # Safe access to latest event using EventBuffer API
        timestamp, value = buffer[-1]

        # Fast-path: if no debounce, just return latest
        if self.debounce <= 0:
            self._last_value = value
            self._last_time = timestamp
            return value

        # Debounce logic
        if self._last_value is not None:
            elapsed = timestamp - self._last_time
            if elapsed < self.debounce:
                # Too soon; return the held value
                return self._last_value

        # Accept new value
        self._last_value = value
        self._last_time = timestamp

        return value


@register_adapter("window")
@dataclass
class Window(Adapter[T]):
    """
    Collects samples from [t-W, t] and applies aggregation.

    Aggregation functions:
    - "first": First value in window
    - "last": Last value in window
    - "max": Maximum value in window
    - "min": Minimum value in window
    - "mean": Average of values in window
    """
    buffer_size: int
    duration: float
    agg: Literal["first", "last", "max", "min", "mean"] = "last"

    def __post_init__(self):
        super().__post_init__()
        if self.duration <= 0:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "Window duration must be positive",
                duration=self.duration
            )

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> T:
        current_time = time.time() if now is None else now

        # Declarative selection of relevant events
        # Note: within() includes start and end boundaries and enforces ts <= now
        relevant_events = buffer.within(duration=self.duration, now=current_time)

        if not relevant_events:  # falls back to latest in buffer (even if outside window?)
            # Original logic: "if not window_values: falls back to latest"
            # Maintain this fallback behavior
            if not buffer:
                 raise IndexError("Window adapter needs data")
            return buffer.latest() # type: ignore

        window_values = [v for _, v in relevant_events]

        # Apply aggregation function based on string name
        if self.agg == "first":
            return window_values[0]
        elif self.agg == "last":
            return window_values[-1]
        elif self.agg == "max":
            return max(window_values)
        elif self.agg == "min":
            return min(window_values)
        elif self.agg == "mean":
            return sum(window_values) / len(window_values)
        else:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                f"Unknown aggregation function: {self.agg}",
                agg=self.agg
            )


@register_adapter("events")
@dataclass
class Events(Adapter[T]):
    """
    Returns a (possibly filtered) slice of the underlying timestamped buffer.

    This is useful for "event stream" style flows that need to reason over
    recent history rather than a single sampled value.

    Notes:
      - `buffer_size` controls how much history is retained by subscribers.
      - When `duration` is set, the window is computed relative to `now` if
        provided (otherwise wall-clock time).
    """

    buffer_size: int
    duration: Optional[float] = None
    include_timestamps: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.duration is not None and self.duration <= 0:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "Events duration must be positive",
                duration=self.duration,
            )

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> Any:
        events: EventBuffer[T]
        if self.duration is None:
            # Return full buffer
            events = EventBuffer(buffer)
        else:
            current_time = time.time() if now is None else now
            # Use declarative within()
            events = buffer.within(duration=self.duration, now=current_time)

        if self.include_timestamps:
            return events
        return [value for _, value in events]


@register_adapter("exact")
@dataclass
class Exact(Adapter[T]):
    """
    Samples value with the exact matching timestamp.

    Requires `now` to be provided (usually by Synchronized clock).
    """
    buffer_size: int = 10
    tolerance: float = 1e-6

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs) -> T:
        if now is None:
            # Fallback to latest if no time requested
            if not buffer:
                 raise IndexError("Exact adapter needs data")
            return buffer.latest() # type: ignore

        # Find match within tolerance
        for ts, value in reversed(buffer):
            if abs(ts - now) <= self.tolerance:
                return value

        raise FlowError(
            ErrCode.FLOW_ADAPTER_INVALID,
            f"No value found for timestamp {now} (tol={self.tolerance})",
            buffer_range=(buffer[0][0], buffer[-1][0]) if buffer else "empty"
        )


@register_adapter("linear")
@dataclass
class Linear(Adapter[float]):
    """
    Linearly interpolates between the two closest values to `now`.
    
    Assumes values are floats (or support arithmetic operations).
    Uses the two closest points in time, one before and one after `now`.
    
    If `now` is outside the range of buffer events:
    - If after latest: returns latest (0-order hold / clamping).
    - If before earliest: returns earliest.
    
    Attributes:
        buffer_size: sufficient size to likely contain the two needed points.
    """
    buffer_size: int = 10
    
    def __call__(self, buffer: EventBuffer[float], now: Optional[float] = None, **kwargs) -> float:
        if not buffer:
            raise IndexError("Linear adapter needs data")
            
        if now is None:
            # Fallback to latest
            return buffer[-1][1]
            
        # 1. Check bounds
        if now >= buffer[-1][0]:
            return buffer[-1][1]
        if now <= buffer[0][0]:
            return buffer[0][1]
            
        # 2. Find bracket [t_prev, t_next] such that t_prev <= now <= t_next
        # We search backwards since we assume `now` is near the end
        prev_pt = None
        next_pt = None
        
        for i in range(len(buffer) - 1, -1, -1):
            pt = buffer[i]
            if pt[0] >= now:
                next_pt = pt
            else:
                prev_pt = pt
                break  # Found the bracket
                
        if prev_pt is None or next_pt is None:
            # Should be unreachable given bounds checks, unless buffer is weirdly unsorted 
            # (which EventBuffer guarantees isn't true for appends but...)
            # Fallback to nearest
            return buffer[-1][1]
            
        # 3. Interpolate
        t1, v1 = prev_pt
        t2, v2 = next_pt
        
        if t2 == t1:
            return v1
            
        alpha = (now - t1) / (t2 - t1)
        return v1 + alpha * (v2 - v1)


@register_adapter("chunking")
@dataclass
class Chunking(Adapter[T]):
    """
    Samples from a time-indexed array (chunk) based on `now`.

    This adapter is designed for consuming pre-computed trajectories or action
    sequences where each buffer entry contains an array of future values with
    a known time step `dt`.

    **Use Case**: VLA (Vision-Language-Action) models output action chunks
    (e.g., 10 actions at 10Hz). A high-frequency controller (e.g., 200Hz)
    needs to sample the correct action for the current time.

    **Logic**:
    1. Find the latest chunk in buffer (most recent timestamp).
    2. Calculate index: `k = (now - chunk_timestamp) / dt`
    3. Return `chunk[k]` (clamped to valid range).

    **Expected buffer value format**: Each value should have:
    - An iterable of items (the chunk array)
    - A way to get `dt` (passed as kwarg or stored in value)

    Subclass this adapter to handle domain-specific value formats.

    Attributes:
        buffer_size: Number of chunks to retain.
        dt: Time step between chunk elements (seconds).
    """
    buffer_size: int = 5
    dt: float = 0.1

    def __call__(
        self, buffer: EventBuffer[T], now: Optional[float] = None, **kwargs
    ) -> Any:
        if not buffer:
            return None

        if now is None:
            now = time.time()

        # Get latest chunk
        chunk_ts, chunk_value = buffer[-1]

        # Extract the array from the value (subclasses can override)
        chunk_array = self._extract_array(chunk_value)
        if chunk_array is None or len(chunk_array) == 0:
            return None

        # Calculate index
        delta = now - chunk_ts
        k = int(delta / self.dt)

        # Clamp to valid range
        if k < 0:
            k = 0
        elif k >= len(chunk_array):
            return None  # Chunk exhausted

        return chunk_array[k]

    def _extract_array(self, value: T) -> Optional[Iterable]:
        """
        Extract the array from the buffer value.

        Override in subclasses for domain-specific formats.
        Default assumes value is directly iterable.
        """
        if hasattr(value, '__iter__'):
            return list(value)
        return None
