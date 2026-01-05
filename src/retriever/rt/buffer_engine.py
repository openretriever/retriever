"""
Buffer engine for per-port event buffering + sampling.

Tier B.3 goal: keep the user-facing authoring API in Python, while allowing the
runtime hot-path (buffering + adapter sampling) to be swapped for a faster
implementation (eventually Rust, e.g. via a native extension).

Today we provide:
  - PythonBufferEngine: reference implementation backed by a deque

Future:
  - NativeBufferEngine: drop-in implementation (Rust) with identical semantics
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Generic, Literal, Optional, TypeVar

from retriever.flow.adapter import Adapter, Latest
from retriever.flow.types import EventBuffer

T = TypeVar("T")

BufferEngineKind = Literal["python", "native"]


class BufferEngine(Generic[T]):
    """Per-port event buffer + adapter sampling."""

    def push(self, timestamp: float, value: T) -> None:  # pragma: no cover
        raise NotImplementedError

    def empty(self) -> bool:  # pragma: no cover
        raise NotImplementedError

    def clear(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def events(self) -> EventBuffer[T]:  # pragma: no cover
        raise NotImplementedError

    def sample(self, adapter: Adapter[T], *, now: Optional[float] = None) -> Any:  # pragma: no cover
        raise NotImplementedError


@dataclass
class PythonBufferEngine(BufferEngine[T]):
    """
    Reference buffer engine implementation.

    Stores a bounded `(timestamp, value)` deque and samples it using built-in
    adapters. This keeps semantics in one place and gives us a clean seam to
    swap in a Rust implementation later.
    """

    buffer_size: int

    def __post_init__(self) -> None:
        if self.buffer_size < 1:
            raise ValueError(f"buffer_size must be >= 1 (got {self.buffer_size})")
        self._buffer: Deque[tuple[float, T]] = deque(maxlen=self.buffer_size)

    def push(self, timestamp: float, value: T) -> None:
        self._buffer.append((timestamp, value))

    def empty(self) -> bool:
        return len(self._buffer) == 0

    def clear(self) -> None:
        self._buffer.clear()

    def events(self) -> EventBuffer[T]:
        return EventBuffer(self._buffer)

    def sample(self, adapter: Adapter[T], *, now: Optional[float] = None) -> Any:
        if not self._buffer:
            raise IndexError("cannot sample empty buffer")

        # Fast-path common adapters where performance is critical and logic is trivial.
        if isinstance(adapter, Latest):
            return self._buffer[-1][1]
        
        # For complex adapters (Window, Events, Hold, Custom), delegate to the Adapter implementation.
        # This ensures the Adapter class (and EventStream/EventBuffer definitions) is the single source of truth.
        # Note: This involves converting deque -> EventBuffer (list copy), which is O(N).
        return adapter.sample(EventBuffer(self._buffer), now=now)


def create_buffer_engine(kind: BufferEngineKind, *, buffer_size: int) -> BufferEngine[Any]:
    """
    Create a buffer engine instance.

    Args:
        kind: "python" (default) or "native"
        buffer_size: retention depth for the per-port event buffer
    """
    if kind == "python":
        return PythonBufferEngine(buffer_size=buffer_size)

    if kind == "native":
        # Future: load a Rust-native engine (e.g., `retriever_native` pyo3 extension).
        raise ImportError(
            "Native buffer engine not implemented in this repo yet. "
            "Use buffer_engine='python' for now."
        )

    raise ValueError(f"Unknown buffer engine kind: {kind!r}")

