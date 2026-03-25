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
        alias_items = self._build_aliases(types)
        alias_types = {alias: typ for alias, typ in alias_items}

        object.__setattr__(self, "_types", alias_types)
        object.__setattr__(self, "_instances", self._build_instances(alias_items, instances))

        unqualified_routes: Dict[str, List[str]] = {}
        qualified_routes: Dict[str, Tuple[str, str]] = {}
        for alias, typ in alias_items:
            if not is_dataclass(typ):
                continue
            for f in fields(typ):
                unqualified_routes.setdefault(f.name, []).append(alias)
                qualified_routes[f"{alias}.{f.name}"] = (alias, f.name)

        object.__setattr__(self, "_routes", unqualified_routes)
        object.__setattr__(self, "_qualified_routes", qualified_routes)

    @staticmethod
    def _build_aliases(types: List[Type]) -> List[Tuple[str, Type]]:
        dataclass_types = [t for t in types if t is not type(None) and is_dataclass(t)]
        name_counts: Dict[str, int] = {}
        for t in dataclass_types:
            name_counts[t.__name__] = name_counts.get(t.__name__, 0) + 1

        running: Dict[str, int] = {}
        alias_items: List[Tuple[str, Type]] = []
        for t in dataclass_types:
            base = t.__name__
            if name_counts[base] == 1:
                alias = base
            else:
                idx = running.get(base, 0) + 1
                running[base] = idx
                alias = f"{base}__{idx}"
            alias_items.append((alias, t))
        return alias_items

    @staticmethod
    def resolve_alias_types(types: List[Type]) -> Dict[str, Type]:
        return {alias: typ for alias, typ in IOView._build_aliases(types)}

    def _build_instances(
        self,
        alias_items: List[Tuple[str, Type]],
        instances: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        built: Dict[str, Any] = {}
        instances = instances or {}
        base_name_counts: Dict[str, int] = {}
        for _, typ in alias_items:
            base_name_counts[typ.__name__] = base_name_counts.get(typ.__name__, 0) + 1

        for alias, typ in alias_items:
            if alias in instances:
                built[alias] = instances[alias]
                continue
            if base_name_counts.get(typ.__name__, 0) == 1 and typ.__name__ in instances:
                built[alias] = instances[typ.__name__]
                continue
            built[alias] = typ()
        return built

    def _resolve_field_route(self, field_name: str) -> Tuple[str, str]:
        if "." in field_name:
            route = self._qualified_routes.get(field_name)
            if route is None:
                raise FlowError(
                    ErrCode.FLOW_IO_FIELD_NOT_FOUND,
                    f"Qualified field '{field_name}' not found",
                )
            return route

        sources = self._routes.get(field_name, [])
        if not sources:
            raise FlowError(ErrCode.FLOW_IO_FIELD_NOT_FOUND, f"Field '{field_name}' not found")
        if len(sources) > 1:
            paths = [f"{s}.{field_name}" for s in sources]
            raise FlowError(
                ErrCode.FLOW_AMBIGUOUS_FIELD,
                f"Ambiguous field '{field_name}'. Exists in: {', '.join(paths)}. Use qualified access.",
            )
        return (sources[0], field_name)

    def __getattr__(self, name: str) -> Any:
        # 1. Qualified: view.TypeName
        if name in self._instances:
            return self._instances[name]

        # 2. Direct: view.field
        if name not in self._routes:
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

        alias, field = self._resolve_field_route(name)
        return self._instances[alias]._get_signal(field)

    def _set_signal(self, field_name: str, value: Any) -> None:
        alias, field = self._resolve_field_route(field_name)
        self._instances[alias]._set_signal(field, value)

    def _get_signal(self, field_name: str) -> Any:
        alias, field = self._resolve_field_route(field_name)
        return self._instances[alias]._get_signal(field)

    def _has_signal(self, field_name: str) -> bool:
        alias, field = self._resolve_field_route(field_name)
        return self._instances[alias]._has_signal(field)

    @property
    def _signals(self) -> List[str]:
        active = []
        for field_name, sources in self._routes.items():
            if len(sources) == 1:
                alias = sources[0]
                if self._instances[alias]._has_signal(field_name):
                    active.append(field_name)
                continue

            for alias in sources:
                if self._instances[alias]._has_signal(field_name):
                    active.append(f"{alias}.{field_name}")
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
        # Map field_name -> list of aliases
        field_map: Dict[str, List[str]] = {}
        for alias, typ in IOView._build_aliases(types):
            for f in fields(typ):
                field_map.setdefault(f.name, []).append(alias)

        # Generate ports
        ports: Dict[str, Tuple[str, str]] = {}
        for field_name, aliases in field_map.items():
            if len(aliases) == 1:
                ports[field_name] = (aliases[0], field_name)
            else:
                for alias in aliases:
                    ports[f"{alias}.{field_name}"] = (alias, field_name)

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
        output_types: Optional[Union[Type, Tuple[Type, ...]]] = None,
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
        self.output_types = output_types
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
             self.instance = IOView(types_list)
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

    def _normalized_output_types(self) -> Tuple[Type, ...]:
        if self.output_types is None:
            return ()
        if isinstance(self.output_types, tuple):
            candidates = self.output_types
        else:
            candidates = (self.output_types,)
        return tuple(t for t in candidates if t is not type(None))

    def _normalize_output_instance(self) -> None:
        expected_types = self._normalized_output_types()
        if not expected_types:
            return

        if len(expected_types) == 1:
            if isinstance(self.instance, tuple):
                raise FlowError(
                    ErrCode.FLOW_TYPE_INVALID,
                    "Single-output flow returned tuple output",
                )
            expected = expected_types[0]
            if self.instance is not None and not isinstance(self.instance, expected):
                raise FlowError(
                    ErrCode.FLOW_TYPE_INVALID,
                    f"Output type mismatch: expected {expected.__name__}, got {type(self.instance).__name__}",
                )
            return

        if not isinstance(self.instance, tuple):
            raise FlowError(
                ErrCode.FLOW_TYPE_INVALID,
                "Composite output flow must return tuple output",
            )
        if len(self.instance) != len(expected_types):
            raise FlowError(
                ErrCode.FLOW_TYPE_INVALID,
                f"Output tuple arity mismatch: expected {len(expected_types)}, got {len(self.instance)}",
            )

        alias_items = IOView._build_aliases(list(expected_types))
        instances: Dict[str, Any] = {}
        for idx, ((alias, expected), value) in enumerate(zip(alias_items, self.instance)):
            if value is None:
                instances[alias] = expected()
                continue
            if not isinstance(value, expected):
                raise FlowError(
                    ErrCode.FLOW_TYPE_INVALID,
                    f"Output tuple[{idx}] type mismatch: expected {expected.__name__}, got {type(value).__name__}",
                )
            instances[alias] = value

        self.instance = IOView(list(expected_types), instances)

    def _resolve_timestamp_for_port(self, field_name: str, default: float) -> float:
        timestamp = default
        if not hasattr(self.instance, "_has_signal"):
            return timestamp

        keys = []
        if field_name == "timestamp" or field_name.endswith(".timestamp"):
            keys.append(field_name)
        if "." in field_name:
            alias = field_name.split(".", 1)[0]
            keys.append(f"{alias}.timestamp")
        else:
            if isinstance(self.instance, IOView):
                try:
                    alias, _ = self.instance._resolve_field_route(field_name)
                    keys.append(f"{alias}.timestamp")
                except Exception:
                    pass
            keys.append("timestamp")

        for key in keys:
            try:
                if self.instance._has_signal(key):
                    val = self.instance._get_signal(key)
                    if val is not None:
                        return float(val)
            except Exception:
                continue
        return timestamp

    def _log_composite_output_to_rerun(
        self,
        output_publishers: Dict[str, List["Publisher"]],
        timestamp: float,
    ) -> None:
        """
        Log the full typed output once before it is split into per-port publishers.

        This preserves richer Rerun visualizations for composite @io outputs like
        perception packets that know how to render images and overlays.
        """
        try:
            from retriever.lib.rerun import log_value_from_env
        except Exception:
            return

        base_paths = set()
        for publisher_list in output_publishers.values():
            for publisher in publisher_list:
                rerun_path = getattr(publisher, "rerun_path", None)
                if isinstance(rerun_path, str) and "/" in rerun_path:
                    base_paths.add(rerun_path.rsplit("/", 1)[0])

        if not base_paths:
            return

        def _is_rerun_loggable(value: Any) -> bool:
            return callable(getattr(value, "log_to_rerun", None))

        if isinstance(self.instance, IOView):
            alias_instances = getattr(self.instance, "_instances", {})
            for alias, value in alias_instances.items():
                if not _is_rerun_loggable(value):
                    continue
                for base_path in base_paths:
                    log_value_from_env(f"{base_path}/{alias}", value, time_seconds=timestamp)
            return

        if _is_rerun_loggable(self.instance):
            for base_path in base_paths:
                log_value_from_env(base_path, self.instance, time_seconds=timestamp)

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

        self._normalize_output_instance()

        # Default to execution time
        timestamp = self.now if self.now is not None else time.time()
        self._log_composite_output_to_rerun(output_publishers, timestamp)

        # Publish each output field to all its publishers
        for field_name, publisher_list in output_publishers.items():
            if self.instance._has_signal(field_name):
                value = self.instance._get_signal(field_name)
                port_timestamp = self._resolve_timestamp_for_port(field_name, timestamp)

                # Broadcast to all publishers for this port
                for publisher in publisher_list:
                    try:
                        publisher.put_one(value, port_timestamp, block=False)
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
