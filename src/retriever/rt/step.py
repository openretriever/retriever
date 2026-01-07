"""
Execution-step I/O pipeline for flow execution.

This module operates on discrete-time per-port event streams (timestamped buffers)
provided by `Subscriber.get_all()`.

`Signal` is *not* itself an event stream: it is a small helper used by executors to
perform one execution step:
  sample → transform → publish

Uses Publisher/Subscriber protocols for backend abstraction.
"""

import time
import types
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
    Tuple,
)

from retriever.flow.adapter import Adapter, Latest
from retriever.flow.types import EventStream
from retriever.error import ErrCode, FlowError
from dataclasses import fields, is_dataclass

if TYPE_CHECKING:
    from retriever.rt.backend.interface import Publisher, Subscriber

import logging

logger = logging.getLogger(__name__)

_DEFAULT_LATEST = Latest()


# =============================================================================
# IOView - Unified view over one or more IO instances
# =============================================================================

class IOView:
    """
    Unified view over one or more IO instances.

    Provides dual access patterns:
    1. Qualified: view.TypeName.field
    2. Direct: view.field (if unambiguous)

    Same interface as @io decorated types:
    ._set_signal(), ._get_signal(), ._has_signal(), ._signals
    """

    def __init__(self, types: List[Type], instances: Dict[str, Any] = None):
        object.__setattr__(self, '_types', {t.__name__: t for t in types})
        object.__setattr__(self, '_instances', instances or {t.__name__: t() for t in types})
        object.__setattr__(self, '_routes', self._build_routes())

    def _build_routes(self) -> Dict[str, List[str]]:
        """Build field_name → [type_names] mapping."""
        routes: Dict[str, List[str]] = {}
        for name, t in self._types.items():
            if not is_dataclass(t):
                continue
            for f in fields(t):
                routes.setdefault(f.name, []).append(name)
        return routes

    def __getattr__(self, name: str) -> Any:
        # 1. Qualified: view.TypeName
        if name in self._instances:
            return self._instances[name]

        # 2. Direct: view.field
        sources = self._routes.get(name, [])
        if not sources:
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

        if len(sources) > 1:
            paths = [f"{s}.{name}" for s in sources]
            raise FlowError(
                ErrCode.FLOW_AMBIGUOUS_FIELD,
                f"Ambiguous field '{name}'. Exists in: {', '.join(paths)}. Use qualified access."
            )

        return getattr(self._instances[sources[0]], name)

    def _set_signal(self, field_name: str, value: Any) -> None:
        sources = self._routes.get(field_name, [])
        if not sources:
            raise FlowError(ErrCode.FLOW_IO_FIELD_NOT_FOUND, f"Field '{field_name}' not found")
        for s in sources:
            self._instances[s]._set_signal(field_name, value)

    def _get_signal(self, field_name: str) -> Any:
        return getattr(self, field_name)

    def _has_signal(self, field_name: str) -> bool:
        sources = self._routes.get(field_name, [])
        return any(self._instances[s]._has_signal(field_name) for s in sources)

    @property
    def _signals(self) -> List[str]:
        active = []
        for field_name, sources in self._routes.items():
            if any(self._instances[s]._has_signal(field_name) for s in sources):
                active.append(field_name)
        return active

    def __repr__(self) -> str:
        return f"<IOView: {', '.join(self._instances.keys())}>"

    @staticmethod
    def resolve_ports(types: List[Type]) -> Dict[str, Tuple[str, str]]:
        """
        Resolve port names for a set of IO types, handling collisions.

        Returns:
            Dict[port_name, (type_name, field_name)]

        Strategy:
        1. If a field name is unique across all types, use it (e.g. 'data').
        2. If a field name collides, qualify it (e.g. 'Image.timestamp').
        """
        from retriever.flow.io import is_flow_io

        # Map field_name -> list of type_names
        field_map: Dict[str, List[str]] = {}

        for t in types:
            if t is type(None) or not is_dataclass(t):
                continue
            t_name = t.__name__
            for f in fields(t):
                field_map.setdefault(f.name, []).append(t_name)

        # Generate ports
        ports: Dict[str, Tuple[str, str]] = {}
        for field_name, type_names in field_map.items():
            if len(type_names) == 1:
                ports[field_name] = (type_names[0], field_name)
            else:
                for t_name in type_names:
                    ports[f"{t_name}.{field_name}"] = (t_name, field_name)

        return ports

class IOStep:
    """
    Per-execution-step helper for multi-field input/output processing.

    Wraps multiple subscribers (one per field) with timestamped values.
    Provides fluent API for sampling, transformation, and publishing.

    Uses Publisher/Subscriber protocols for backend abstraction.

    Usage:
        IOStep(input_subscribers, fields_filter) \\
            .sample(input_type, adapters) \\
            .transform(flow.run) \\
            .publish(output_publishers)
    """

    def __init__(
        self,
        subscribers: Dict[str, "Subscriber"] = None,
        fields_filter: List[str] = None,
        instance: Any = None,
        now: Optional[float] = None,
    ):
        """
        Initialize IOStep from input subscribers or with direct instance.

        Args:
            subscribers: Dict mapping field name to Subscriber
            fields_filter: [] (no), ["..."] (all), or list (specific)
            instance: Optional direct instance (skips sample)
        """
        self.subscribers = subscribers or {}
        self.fields_filter = fields_filter or []
        self.instance = instance
        self.now = now



    def sample(
        self,
        input_type: Union[Type, Tuple[Type, ...], None],
        adapters: Dict[str, Adapter],
        *,
        now: Optional[float] = None,
    ) -> "IOStep":
        """
        Sample from subscribers using adapters to create input instance.

        For each field:
        1. Get timestamped data from subscriber: [(ts, value), ...]
        2. Apply adapter to sample single value
        3. Set signal on input instance

        Args:
            input_type: Flow input type (or None for source flows)
            adapters: Dict mapping field name to Adapter

        Returns:
            Self for chaining
        """
        if input_type is None:
            # Source flow - no input
            self.instance = None
            return self

        if isinstance(input_type, tuple):
             # Composite Flow - use IOView
             types_list = list(input_type)
             instances = {t.__name__: t() for t in types_list}
             self.instance = IOView(types_list, instances)
        else:
             # Single Flow
             self.instance = input_type()

        # Determine which fields triggered execution (for _signals metadata)
        if not self.fields_filter:
            triggered_fields = []
        elif self.fields_filter == ["..."]:
            triggered_fields = list(self.subscribers.keys())
        else:
            triggered_fields = self.fields_filter

        # ALWAYS sample ALL subscriber fields (not just triggers)
        # This ensures Latest() adapters populate their values even when another field triggers
        fields_to_sample = list(self.subscribers.keys())

        # Sample each field
        effective_now = self.now if now is None else now
        for field_name in fields_to_sample:
            if field_name not in self.subscribers:
                continue

            subscriber = self.subscribers[field_name]

            if subscriber.empty():
                continue

            adapter = adapters.get(field_name)
            if adapter is None:
                adapter = _DEFAULT_LATEST

            # Tier B.3 fast-path: Subscribers may implement `sample(adapter, now=...)`
            if hasattr(subscriber, "sample"):
                value = subscriber.sample(adapter, now=effective_now)
            else:
                value = adapter.sample(subscriber.get_all(), now=effective_now)

            # Set signal on input instance (FlowIO treats None as "no signal")
            self.instance._set_signal(field_name, value)

        return self

    def transform(self, fn: Callable) -> "IOStep":
        """
        Transform signal by applying function.

        Typically: fn = flow.run
        Transforms: input instance → output instance

        Args:
            fn: Transformation function (input -> output)

        Returns:
            Self for chaining
        """
        if fn is not None:
            tracer_cm = nullcontext()
            try:
                from opentelemetry import trace  # type: ignore

                tracer = trace.get_tracer("retriever.runtime")
                tracer_cm = tracer.start_as_current_span("transform")
            except Exception:
                tracer_cm = nullcontext()

            with tracer_cm:
                self.instance = fn(self.instance)
        return self

    def fold(self, on: Callable[[Generator], None]) -> "IOStep":
        """
        Handle generator output (Async/ServiceCall support).

        If transformation returned a generator, pass it to 'on' callback
        and suppress downstream publishing for this step (async continuation).

        Args:
            on: Callback to handle generator

        Returns:
            Self (with instance=None if yielded)
        """
        if isinstance(self.instance, types.GeneratorType):
            on(self.instance)
            self.instance = None
        return self



    def publish(self, output_publishers: Dict[str, List["Publisher"]]) -> "IOStep":
        """
        Publish output signals to publishers.

        For each field in output instance:
        1. Get signal value
        2. Send (value, timestamp) to all publishers for that port (broadcasting)

        Args:
            output_publishers: Dict mapping field name to List[Publisher] (supports broadcasting)

        Returns:
            Self for chaining
        """
        if self.instance is None:
            # Sink flow - no output
            return self

        # Default to execution time
        timestamp = self.now if self.now is not None else time.time()

        # If data has explicit timestamp, propagate it (Critical for synchronization)
        # Check standard 'timestamp' field first
        found_ts = False
        if hasattr(self.instance, "timestamp") and self.instance.timestamp is not None:
            try:
                timestamp = float(self.instance.timestamp)
                found_ts = True
            except (ValueError, TypeError):
                pass

        if not found_ts:
            # Check for 'ts_val' (fallback/rename)
            if hasattr(self.instance, "ts_val") and self.instance.ts_val is not None:
                try:
                    timestamp = float(self.instance.ts_val)
                    found_ts = True
                except (ValueError, TypeError):
                    pass

        if not found_ts and hasattr(self.instance, "_has_signal"):
            # For FlowIO wrapped objects, try _get_signal but handle errors
            try:
                if self.instance._has_signal("timestamp"):
                    val = self.instance._get_signal("timestamp")
                    if val is not None:
                        timestamp = float(val)
            except Exception:
                pass

        # Publish each output field to all its publishers
        for field_name, publisher_list in output_publishers.items():
            if self.instance._has_signal(field_name):
                value = self.instance._get_signal(field_name)

                # Broadcast to all publishers for this port
                for publisher in publisher_list:
                    try:
                        publisher.put_one(value, timestamp, block=False)
                        # logger.debug(f"Published {field_name}={value}")
                    except Exception as e:
                        # HACK: queue.Full is common in MP during startup/heavy load.
                        # Don't spam stack traces for it.
                        if "Full" in str(e) or e.__class__.__name__ == "Full":
                            logger.warning(f"Dropped frame on {field_name}: queue full")
                        else:
                            # Log actual error
                            logger.error(
                                f"Failed to publish {field_name}: {e}", exc_info=True
                            )

        return self
