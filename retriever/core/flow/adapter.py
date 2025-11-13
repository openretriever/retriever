"""
Adapter module for queue sampling strategies.

Adapters determine how messages are sampled from input queues
for temporal alignment between cross-clock flow connections.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar, Generic, List, Tuple, Optional, Any, Type, Dict, Literal
from retriever.core.error import FlowError, ErrCode

T = TypeVar('T')
TQueue = List[Tuple[float, T]]

# Global adapter registry
_adapter_registry: Dict[str, Type['Adapter']] = {}


class Adapter(ABC, Generic[T]):
    """Abstract base class for queue sampling strategies."""

    @abstractmethod
    def __call__(self, queue: TQueue[T]) -> Any:
        """
        Apply sampling strategy to the queue.

        Args:
            queue: List of (timestamp, value) tuples

        Returns:
            Sampled value(s) from the queue
        """
        pass


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
                f"Adapter name '{adapter_name}' already registered to {existing.__name__}",
                name=adapter_name,
                existing=existing.__name__,
                new=cls.__name__
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
    """Samples the most recent value from the queue."""

    def __call__(self, queue: TQueue[T]) -> T:
        _, value = queue[-1]
        return value


@register_adapter("hold")
@dataclass
class Hold(Adapter[T]):
    """Zero-order hold with optional debounce."""

    debounce: float = 0.0
    _last_value: Optional[T] = field(default=None, init=False, repr=False)
    _last_time: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        if self.debounce < 0:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "Hold debounce must be non-negative",
                debounce=self.debounce
            )

    def __call__(self, queue: TQueue[T]) -> T:
        timestamp, value = queue[-1]

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

    duration: float
    agg: Literal["first", "last", "max", "min", "mean"] = "last"

    def __post_init__(self):
        if self.duration <= 0:
            raise FlowError(
                ErrCode.FLOW_ADAPTER_INVALID,
                "Window duration must be positive",
                duration=self.duration
            )

    def __call__(self, queue: TQueue[T]) -> T:
        current_time = time.time()
        start_time = current_time - self.duration

        window_values = [value for ts, value in queue if ts >= start_time]

        if not window_values:  # falls back to latest
            _, value = queue[-1]
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

