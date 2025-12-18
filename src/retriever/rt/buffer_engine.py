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

import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Generic, Literal, Optional, TypeVar

from retriever.core.flow.adapter import Adapter, EventBuffer, Events, Hold, Latest, Window

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
        return list(self._buffer)

    def sample(self, adapter: Adapter[T], *, now: Optional[float] = None) -> Any:
        if not self._buffer:
            raise IndexError("cannot sample empty buffer")

        # Fast-path common adapters without materializing a list.
        if isinstance(adapter, Latest):
            return self._buffer[-1][1]

        if isinstance(adapter, Hold):
            # Preserve Hold's internal state by calling the adapter implementation.
            return adapter.sample([self._buffer[-1]], now=now)

        if isinstance(adapter, Window):
            current_time = time.time() if now is None else now
            start_time = current_time - adapter.duration

            # Match Window semantics: include events with ts >= start_time.
            window_values = [v for ts, v in self._buffer if ts >= start_time]
            if not window_values:
                return self._buffer[-1][1]

            if adapter.agg == "first":
                return window_values[0]
            if adapter.agg == "last":
                return window_values[-1]
            if adapter.agg == "max":
                return max(window_values)
            if adapter.agg == "min":
                return min(window_values)
            if adapter.agg == "mean":
                return sum(window_values) / len(window_values)

            raise ValueError(f"Unknown Window.agg: {adapter.agg!r}")

        if isinstance(adapter, Events):
            if adapter.duration is None:
                events: EventBuffer[T] = list(self._buffer)
            else:
                current_time = time.time() if now is None else now
                start_time = current_time - adapter.duration
                events = [(ts, v) for ts, v in self._buffer if ts >= start_time]

            if adapter.include_timestamps:
                return events
            return [v for _, v in events]

        # Fallback: preserve semantics for custom adapters by delegating.
        return adapter.sample(list(self._buffer), now=now)


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

