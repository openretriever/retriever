"""
Adapter module for buffer sampling strategies.

Adapters determine how messages are sampled from input buffers
for temporal alignment between cross-clock flow connections.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Any
from typing import Type, List, Tuple, Dict, Literal
from retriever.core.error import FlowError, ErrCode

T = TypeVar('T')
EventBuffer = List[Tuple[float, T]]
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
    def __call__(self, buffer: EventBuffer[T]) -> Any:
        """
        Apply sampling strategy to the buffer.

        Args:
            buffer: List of (timestamp, value) tuples

        Returns:
            Sampled value(s) from the buffer
        """
        pass

    def sample(self, buffer: EventBuffer[T], *, now: Optional[float] = None) -> Any:
        """
        Sample from a timestamped buffer at a given time.

        This is a thin compatibility layer to support time-aware adapters without
        breaking older adapters that only implement `__call__(buffer)`.

        Args:
            buffer: List of (timestamp, value)
            now: Optional wall-clock timestamp associated with this sampling

        Returns:
            Sampled value(s)
        """
        try:
            return self.__call__(buffer, now=now)  # type: ignore[misc]
        except TypeError:
            return self.__call__(buffer)


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

    def __call__(self, buffer: EventBuffer[T]) -> T:
        _, value = buffer[-1]
        return value


@register_adapter("hold")
@dataclass
class Hold(Adapter[T]):
    """Zero-order hold with optional debounce."""
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

    def __call__(self, buffer: EventBuffer[T]) -> T:
        timestamp, value = buffer[-1]

        if self.debounce > 0:
            if self._last_value is not None:
                elapsed = timestamp - self._last_time
                if elapsed < self.debounce:
                    return self._last_value

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

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None) -> T:
        current_time = time.time() if now is None else now
        start_time = current_time - self.duration

        window_values = [value for ts, value in buffer if ts >= start_time]

        if not window_values:  # falls back to latest
            _, value = buffer[-1]
            return value

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
            # Should never reach here due to Literal type
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

    def __call__(self, buffer: EventBuffer[T], now: Optional[float] = None) -> Any:
        events: EventBuffer[T]
        if self.duration is None:
            events = list(buffer)
        else:
            current_time = time.time() if now is None else now
            start_time = current_time - self.duration
            events = [(ts, value) for ts, value in buffer if ts >= start_time]

        if self.include_timestamps:
            return events
        return [value for _, value in events]
