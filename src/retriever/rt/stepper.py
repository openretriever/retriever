"""
In-process pipeline stepper for single-step debugging.

`Pipeline.run(...)` executes a validated pipeline on a backend (multiprocessing/dora).
For interactive debugging, it's often useful to execute a pipeline *in-process* and
advance it one discrete step at a time. This module provides that capability.

The stepper intentionally models the same per-execution semantics as the backends:
  sample → run → publish

It is **not** a production backend; it is a lightweight debugging tool.
"""

from __future__ import annotations

import gzip
import pickle
import time
import types
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from retriever.error import FlowError, RTError, ErrCode
from retriever.flow.adapter import Adapter
from retriever.flow.types import EventBuffer
from retriever.flow.base import Flow
from retriever.flow.clock import Clock, Hybrid, Rate, Trigger
from retriever.flow.builder import PipelineBuilder
from retriever.flow.temporal import TemporalFlow
from retriever.ir.core import IR, IREdge
from retriever.rt.step import IOStep
from retriever.rt.step import IOStep

T = TypeVar("T")


class InMemoryChannel:
    """
    In-process timestamped channel.

    Implements the minimal Publisher/Subscriber protocol used by `Signal` and
    schedulers: `put_one`, `get_all`, `new_arrival`, `empty`, `clear`.
    """

    def __init__(self, buffer_size: int):
        self._buffer = deque(maxlen=buffer_size)
        self._arrival_flag = False

    def put_one(self, value: Any, timestamp: float, block: bool = True) -> None:  # noqa: ARG002
        self._buffer.append((timestamp, value))
        self._arrival_flag = True

    def get_all(self):
        return EventBuffer(self._buffer)

    def new_arrival(self) -> bool:
        result = self._arrival_flag
        self._arrival_flag = False
        return result

    def empty(self) -> bool:
        return len(self._buffer) == 0

    def clear(self) -> None:
        self._buffer.clear()
        self._arrival_flag = False


@dataclass(frozen=True)
class StepResult:
    """Result of one `Pipeline.step()` call."""

    now: float
    executed: List[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]


class PipelineStepper:
    """
    In-process stepper bound to a PipelineBuilder/Pipeline.

    Loads adapters from IR (so buffer sizes match runtime) but executes *the same*
    flow instances that were used when authoring the Pipeline.
    """

    def __init__(self, ctx: PipelineBuilder):
        self._ctx = ctx
        self._ir: IR = ctx.validate()

        self._flows: Dict[str, TemporalFlow] = {n.id: ctx.get_handle_for_node(n.id) for n in self._ir.nodes}

        self._channels: Dict[str, InMemoryChannel] = {}
        self._inputs: Dict[str, Dict[str, InMemoryChannel]] = {}
        self._outputs: Dict[str, Dict[str, List[InMemoryChannel]]] = {}
        self._adapters: Dict[str, Dict[str, Adapter]] = {}

        self._node_order: List[str] = [nid for group in self._ir.topology.groups for nid in group]

        self._initialized = False
        self._now: Optional[float] = None

        self._build_io()

    @property
    def ir(self) -> IR:
        return self._ir

    def close(self) -> None:
        """Finalize all flows and clear buffers."""
        if self._initialized:
            for handle in self._flows.values():
                try:
                    handle.flow.finalize()
                except Exception:
                    # Debug helper should not mask the original exception
                    pass
        self._initialized = False
        self.reset_buffers()

    def reset_buffers(self) -> None:
        for ch in self._channels.values():
            ch.clear()

    def reset(self) -> None:
        """
        Reset stepper state for repeated debugging runs.

        Calls `Flow.reset()` on all flows and clears all channel buffers.
        """
        for handle in self._flows.values():
            try:
                handle.flow.reset()
            except Exception:
                pass
        self.reset_buffers()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        # Important for debugging: do not wrap exceptions raised by user code
        # so debuggers can break at the original source location inside Flow.init().
        for handle in self._flows.values():
            handle.flow.init()
        self._initialized = True

    def _build_io(self) -> None:
        # Initialize empty maps for all nodes
        for node in self._ir.nodes:
            self._inputs[node.id] = {}
            self._outputs[node.id] = {}
            self._adapters[node.id] = {}

        # Build per-node input subscribers + adapter map
        # Fan-in edges share one channel per logical port
        for edge in self._ir.edges:
            if not self._is_runtime_edge(edge):
                continue
            dst = edge.destination.node
            actual_port = edge.destination.port
            logical_port = IR.get_logical_port(actual_port)

            if IR.is_fan_in_port(actual_port):
                # Fan-in: share one channel for all edges to same logical port
                if logical_port not in self._inputs[dst]:
                    adapter = edge.instantiate_adapter()
                    channel = InMemoryChannel(buffer_size=adapter.buffer_size)
                    self._inputs[dst][logical_port] = channel
                    self._adapters[dst][logical_port] = adapter
                # Reuse existing channel for this edge
                self._channels[edge.id] = self._inputs[dst][logical_port]
            else:
                # Normal: one channel per edge
                adapter = edge.instantiate_adapter()
                channel = InMemoryChannel(buffer_size=adapter.buffer_size)
                self._channels[edge.id] = channel
                self._inputs[dst][logical_port] = channel
                self._adapters[dst][logical_port] = adapter

        # Build per-node output publishers (support broadcasting)
        for edge in self._ir.edges:
            if not self._is_runtime_edge(edge):
                continue
            src = edge.source.node
            port = edge.source.port

            self._outputs[src].setdefault(port, []).append(self._channels[edge.id])

    @staticmethod
    def _is_runtime_edge(edge: IREdge) -> bool:
        """
        Return True for normal data edges.

        Service edges currently have `adapter=None` / `qsize=None` and are handled
        by specialized executor logic (Dora generator + RPC). The in-process stepper
        intentionally ignores them for now.
        """
        return edge.adapter is not None and edge.qsize is not None

    def _compute_now(self, *, now: Optional[float], dt: Optional[float]) -> float:
        if now is not None:
            self._now = float(now)
            return self._now

        if dt is not None:
            if self._now is None:
                self._now = time.time()
            self._now = self._now + float(dt)
            return self._now

        self._now = time.time()
        return self._now

    def step(self, *, now: Optional[float] = None, dt: Optional[float] = None) -> StepResult:
        """
        Execute one discrete debugging step in-process.

        Semantics (debug-focused, not real-time):
          - Rate/Tick flows execute once per step.
          - Trigger flows execute when a new arrival is observed on a trigger field.
          - Hybrid flows prefer trigger execution; otherwise execute once per step.

        Args:
            now: Optional wall-clock timestamp to associate with this step.
            dt: If provided, advance an internal logical clock by `dt` seconds.

        Returns:
            StepResult with per-node input/output snapshots.
        """
        self._ensure_initialized()
        step_now = self._compute_now(now=now, dt=dt)

        executed: List[str] = []
        inputs_snapshot: Dict[str, Any] = {}
        outputs_snapshot: Dict[str, Any] = {}

        for node_id in self._node_order:
            handle = self._flows[node_id]
            clock = handle.config.clock

            should_execute, fields = self._should_execute(clock, self._inputs[node_id])
            if not should_execute:
                continue

            signal = IOStep(self._inputs[node_id], fields_filter=fields, now=step_now)
            signal.sample(handle.flow.input_types, self._adapters[node_id], now=step_now)
            inputs_snapshot[node_id] = signal.instance

            signal.transform(handle.flow.run)

            # Basic support for generator-returning flows (services not supported here)
            if isinstance(signal.instance, types.GeneratorType):
                raise RTError(
                    ErrCode.RT_INVALID_YIELD,
                    "Pipeline.step() does not support generator-based flows (service calls) yet",
                    node=node_id,
                )

            outputs_snapshot[node_id] = signal.instance
            signal.publish(self._outputs[node_id])

            executed.append(node_id)

        return StepResult(now=step_now, executed=executed, inputs=inputs_snapshot, outputs=outputs_snapshot)

    @staticmethod
    def _should_execute(clock: Clock, inputs: Dict[str, InMemoryChannel]) -> tuple[bool, List[str]]:
        if isinstance(clock, Rate):
            return True, ["..."]

        if isinstance(clock, Trigger):
            for field in clock.fields:
                ch = inputs.get(field)
                if ch is not None and ch.new_arrival():
                    return True, [field]
            return False, []

        if isinstance(clock, Hybrid):
            for field in clock.trigger_fields:
                ch = inputs.get(field)
                if ch is not None and ch.new_arrival():
                    return True, [field]
            return True, ["..."]

        raise FlowError(
            ErrCode.FLOW_CLOCK_INVALID,
            f"Unknown clock type: {type(clock).__name__}",
        )


# ======================================================================================
# Record / Replay (Stepper-first, debugger-friendly)
# ======================================================================================

def save_event_buffer(path: str | Path, buffer: EventBuffer[T]) -> None:
    """
    Save a timestamped `EventBuffer[T] = list[(ts, value)]` to disk.

    Storage format: gzip+pickle (debug artifact, not a stable ABI).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        pickle.dump(buffer, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_event_buffer(path: str | Path) -> EventBuffer[Any]:
    """Load an `EventBuffer` previously written by `save_event_buffer`."""
    with gzip.open(Path(path), "rb") as f:
        return pickle.load(f)


def replay_flow(buffer: EventBuffer[T], *, output_type: Type[T]) -> Flow[None, T]:
    """
    Create a replay source flow that outputs recorded items sequentially.

    Notes:
    - `output_type` must be a `@flow_io` dataclass type.
    - When exhausted, returns an "empty" output instance (all fields None),
      so no outputs are published.
    """
    items = list(buffer)

    Base = Flow[None, output_type]  # type: ignore[misc]

    class _ReplayFlow(Base):
        def init(self) -> None:
            self._i = 0
            self.done = False

        def reset(self) -> None:
            self._i = 0
            self.done = False

        def run(self, _):  # type: ignore[override]
            if self._i >= len(items):
                self.done = True
                return output_type()
            _ts, value = items[self._i]
            self._i += 1
            return value

    _ReplayFlow.__name__ = f"Replay{getattr(output_type, '__name__', 'Flow')}"
    return _ReplayFlow()


def replay_handle(buffer: EventBuffer[T], clock: Any, *, output_type: Type[T]) -> TemporalFlow:
    """Convenience: bind `replay_flow(...)` to a clock via `@`."""
    return replay_flow(buffer, output_type=output_type) @ clock


class EventStreamRecorder(Generic[T]):
    """
    Record a node's per-step outputs by calling `Pipeline.step()`.

    Conceptually, this records a finite retained history of a port/object-level
    EventStream (an `EventBuffer`) suitable for replay in the stepper.
    """

    def __init__(self, pipeline: Any, handle: TemporalFlow, *, name: str = "stream"):
        self._pipeline = pipeline
        self._handle = handle
        self._node_id = pipeline.get_node_id(handle)
        self._output_type: Optional[Type[T]] = handle.flow.output_type  # type: ignore[assignment]

        self.name = name
        self.buffer: EventBuffer[T] = []

    @property
    def output_type(self) -> Type[T]:
        if self._output_type is None:
            raise TypeError("Handle output type is not available; add Flow type parameters [I, O].")
        return self._output_type

    def step(self, *, now: Optional[float] = None, dt: Optional[float] = None):
        res = self._pipeline.step(now=now, dt=dt)
        out = res.outputs.get(self._node_id)
        if out is None:
            out = self.output_type()
        self.buffer.append((res.now, out))
        return res

    def run(
        self,
        *,
        steps: int,
        dt: Optional[float] = None,
        sleep_s: float = 0.0,
    ) -> EventBuffer[T]:
        for _ in range(steps):
            self.step(dt=dt)
            if sleep_s > 0:
                time.sleep(sleep_s)
        return self.buffer

    def save(self, path: str | Path) -> None:
        save_event_buffer(path, self.buffer)
