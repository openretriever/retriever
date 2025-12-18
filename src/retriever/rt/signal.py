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
from typing import Dict, List, Tuple, Optional, Callable, Type, Any, Generator, TYPE_CHECKING

from retriever.core.flow.adapter import Adapter, Latest
from retriever.core.rt.frp import EventStream

if TYPE_CHECKING:
    from retriever.core.rt.backend.interface import Subscriber, Publisher

import logging
logger = logging.getLogger(__name__)

_DEFAULT_LATEST = Latest()


class Signal:
    """
    Per-execution-step helper for multi-field input/output processing.

    Wraps multiple subscribers (one per field) with timestamped values.
    Provides fluent API for sampling, transformation, and publishing.

    Uses Publisher/Subscriber protocols for backend abstraction.

    Usage:
        Signal(input_subscribers, fields_filter) \\
            .sample(input_type, adapters) \\
            .transform(flow.run) \\
            .publish(output_publishers)
    """

    def __init__(
        self,
        subscribers: Dict[str, 'Subscriber'] = None,
        fields_filter: List[str] = None,
        instance: Any = None,
        now: Optional[float] = None,
    ):
        """
        Initialize Signal from input subscribers or with direct instance.

        Args:
            subscribers: Dict mapping field name to Subscriber
            fields_filter: [] (no), ["..."] (all), or list (specific)
            instance: Optional direct instance (skips sample)
        """
        self.subscribers = subscribers or {}
        self.fields_filter = fields_filter or []
        self.instance = instance
        self.now = now

    def event_stream(self, field: str) -> EventStream[Any]:
        """
        Get a discrete-time event stream view over one input port.

        Returns an `EventStream` whose `events()` reads from the underlying Subscriber.
        """
        if field not in self.subscribers:
            return EventStream(lambda: [])
        subscriber = self.subscribers[field]
        return EventStream(subscriber.get_all)

    def sample(
        self,
        input_type: Optional[Type],
        adapters: Dict[str, Adapter],
        *,
        now: Optional[float] = None,
    ) -> 'Signal':
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

        # Create input instance
        self.instance = input_type()

        # Determine which fields to sample
        if not self.fields_filter:
            fields_to_sample = []
        elif self.fields_filter == ["..."]:
            fields_to_sample = self.subscribers.keys()
        else:
            fields_to_sample = self.fields_filter

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
            # to avoid materializing full Python lists per step.
            if hasattr(subscriber, "sample"):
                value = subscriber.sample(adapter, now=effective_now)  # type: ignore[attr-defined]
            else:
                value = adapter.sample(subscriber.get_all(), now=effective_now)

            # Set signal on input instance (FlowIO treats None as "no signal")
            self.instance._set_signal(field_name, value)

        return self

    def transform(self, fn: Callable) -> 'Signal':
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
                tracer = trace.get_tracer('retriever.runtime')
                tracer_cm = tracer.start_as_current_span('transform')
            except Exception:
                tracer_cm = nullcontext()

            with tracer_cm:
                self.instance = fn(self.instance)
        return self

    def fold(self, on: Callable[[Generator], None]) -> 'Signal':
        """
        Fold over generator: if instance is Generator, call handler and clear.

        Args:
            on: Handler called with Generator if transform yielded one

        Returns:
            Self for chaining (instance set to None if generator was extracted)
        """
        if isinstance(self.instance, types.GeneratorType):
            on(self.instance)
            self.instance = None
        return self

    def publish(self, output_publishers: Dict[str, List['Publisher']]) -> 'Signal':
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

        timestamp = self.now if self.now is not None else time.time()

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
                        # Log actual error
                        logger.error(
                            f"Failed to publish {field_name}: {e}",
                            exc_info=True
                        )

        return self
