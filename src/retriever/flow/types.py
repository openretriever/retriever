"""
FRP Combinators and Utilities.

This module provides high-level functional reactive programming combinators
built on top of the core runtime primitives. These allow users to compose
complex temporal behaviors from simple blocks.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Dict,
)

if TYPE_CHECKING:
    from retriever.flow.adapter import Adapter

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class EventStream(Generic[T]):
    """
    Discrete-time stream of timestamped values.

    `events()` returns a chronologically-ordered list of `(timestamp, value)`.
    """

    events: Callable[[], "TimedBuffer[T]"]

    @property
    def stream(self) -> Callable[[], "TimedBuffer[T]"]:
        """
        Backward-compatible alias used by older FRP code (`stream()` returns events).
        """
        return self.events

    @staticmethod
    def empty() -> "EventStream[T]":
        """Create empty event stream."""
        return EventStream(lambda: TimedBuffer([]))

    @staticmethod
    def single(timestamp: float, value: T) -> "EventStream[T]":
        """Create event stream with single event."""
        return EventStream(lambda: TimedBuffer([(timestamp, value)]))

    @staticmethod
    def periodic(period: float, value_fn: Callable[[float], T]) -> "EventStream[T]":
        """
        Create event stream that generates events periodically.

        Note: For actual periodic execution, use `Rate(hz=...)` clock.
        This is for generating synthetic event streams for testing/simulation.
        """
        start_time = time.time()

        def periodic_stream_fn() -> TimedBuffer[T]:
            current_time = time.time()
            elapsed = current_time - start_time

            events: TimedBuffer[T] = TimedBuffer()
            event_count = int(elapsed / period)
            for i in range(event_count + 1):
                event_time = start_time + (i * period)
                if event_time <= current_time:
                    event_value = value_fn(event_time)
                    events.append((event_time, event_value))

            return events

        return EventStream(periodic_stream_fn)

    def sample(self, adapter: "Adapter[T]", *, now: Optional[float] = None) -> Any:
        """
        Sample this event stream using an Adapter at time `now`.

        This is the single-stream equivalent of what executors do across ports:
        they read an `TimedBuffer` from a Subscriber, then apply an Adapter.
        """
        return adapter.sample(self.events(), now=now)

    def latest(self) -> Optional[T]:
        """Return the most recent value from the stream, or None if empty."""
        buf = self.events()
        if not buf:
            return None
        return buf[-1][1]

    def within(self, *, duration: float, now: float) -> "TimedBuffer[T]":
        """
        Return events within the time window [now - duration, now].

        Both boundaries are inclusive. Events with timestamps outside this
        range (including future events) are excluded.
        """
        start = now - duration
        return TimedBuffer([(ts, v) for ts, v in self.events() if start <= ts <= now])

    def map(self, fn: Callable[[T], U]) -> "EventStream[U]":
        """
        Transform each event's value using a function.

        FRP Concept: `map` is a fundamental functor operation. It applies a pure
        function to each value in the stream without changing the timing of events.

        Example:
            temperatures_celsius = temperatures_fahrenheit.map(lambda f: (f - 32) * 5/9)
        """
        return EventStream(lambda: TimedBuffer([(ts, fn(v)) for ts, v in self.events()]))

    def filter(self, pred: Callable[[T], bool]) -> "EventStream[T]":
        """
        Keep only events where the predicate returns True.

        FRP Concept: `filter` removes events from the stream based on their values.
        The timing of remaining events is preserved.

        Example:
            positive_values = values.filter(lambda x: x > 0)
        """
        return EventStream(
            lambda: TimedBuffer([(ts, v) for ts, v in self.events() if pred(v)])
        )

    def merge(self, other: "EventStream[T]") -> "EventStream[T]":
        """
        Combine two event streams into one, interleaving by timestamp.

        FRP Concept: `merge` is the fundamental way to combine discrete events.
        Events from both streams appear in the output, ordered by time.
        If events have identical timestamps, ordering is implementation-defined.

        Example:
            all_inputs = keyboard_events.merge(mouse_events)
        """
        def merged() -> TimedBuffer[T]:
            buf = list(self.events()) + list(other.events())
            buf.sort(key=lambda x: x[0])
            return TimedBuffer(buf)
        return EventStream(merged)

    def fold(self, initial: U, fn: Callable[[U, T], U]) -> "Behavior[U]":
        """
        Accumulate events into a time-varying Behavior.

        FRP Concept: `fold` (also called `scan` or `accumulate`) creates a continuous
        behavior from discrete events by maintaining an accumulator. At any time `t`,
        the behavior's value is the result of folding all events up to time `t`.

        Example:
            # Count button clicks over time
            click_count: Behavior[int] = button_clicks.fold(0, lambda count, _: count + 1)
        """
        def folded(t: float) -> U:
            acc = initial
            for ts, v in self.events():
                if ts <= t:
                    acc = fn(acc, v)
            return acc
        return Behavior(folded)

    def snapshot(self, behavior: "Behavior[U]") -> "EventStream[Tuple[T, U]]":
        """
        Sample a Behavior's value each time this stream fires.

        FRP Concept: `snapshot` bridges discrete and continuous worlds. When an event
        occurs, it "takes a picture" of the behavior's current value, pairing the
        event value with the sampled behavior value.

        This is essential for combining user actions (discrete) with system state
        (continuous). The behavior is sampled at the exact timestamp of each event.

        Example:
            # When user clicks, capture both click position and current scroll offset
            click_with_scroll = click_events.snapshot(scroll_position_behavior)
            # Result: stream of (ClickEvent, ScrollOffset) pairs
        """
        def sampled() -> TimedBuffer[Tuple[T, U]]:
            return TimedBuffer([(ts, (v, behavior.at(ts))) for ts, v in self.events()])
        return EventStream(sampled)

    def delay(self, dt: float) -> "EventStream[T]":
        """
        Delay all events by a fixed time offset.

        FRP Concept: `delay` shifts the temporal position of all events. An event
        that occurred at time `t` will appear at time `t + dt` in the output stream.

        Use cases:
        - Simulating network latency
        - Creating echo/reverb effects
        - Coordinating events that should happen "after" something

        Example:
            delayed_commands = commands.delay(0.5)  # 500ms delay
        """
        def delayed() -> TimedBuffer[T]:
            return TimedBuffer([(ts + dt, v) for ts, v in self.events()])
        return EventStream(delayed)

    def take(self, n: int) -> "EventStream[T]":
        """
        Keep only the first N events from the stream.

        FRP Concept: `take` limits the stream to a finite number of events.
        Once N events have occurred, subsequent events are ignored.

        Example:
            first_three_clicks = clicks.take(3)
        """
        def taken() -> TimedBuffer[T]:
            return TimedBuffer(self.events()[:n])
        return EventStream(taken)

    def drop(self, n: int) -> "EventStream[T]":
        """
        Skip the first N events from the stream.

        FRP Concept: `drop` ignores the initial events, keeping only those after
        the first N have passed.

        Example:
            after_warmup = sensor_data.drop(100)  # Ignore first 100 readings
        """
        def dropped() -> TimedBuffer[T]:
            return TimedBuffer(self.events()[n:])
        return EventStream(dropped)

    def zip_with(self, other: "EventStream[U]") -> "EventStream[Tuple[T, U]]":
        """
        Pair up events from two streams by position (not time).

        FRP Concept: `zip` combines streams element-wise. The Nth event from
        this stream is paired with the Nth event from the other stream.
        If streams have different lengths, extra events are discarded.

        Note: This pairs by *position*, not by *timestamp*. For time-based
        pairing, use `combine_latest`.

        Example:
            questions_and_answers = questions.zip_with(answers)
        """
        def zipped() -> TimedBuffer[Tuple[T, U]]:
            self_events = self.events()
            other_events = other.events()
            min_len = min(len(self_events), len(other_events))
            # Use the earlier timestamp of each pair
            return TimedBuffer([
                (min(self_events[i][0], other_events[i][0]),
                 (self_events[i][1], other_events[i][1]))
                for i in range(min_len)
            ])
        return EventStream(zipped)

    def combine_latest(self, other: "EventStream[U]") -> "EventStream[Tuple[T, U]]":
        """
        Emit the latest values from both streams whenever either fires.

        FRP Concept: `combine_latest` merges two streams by pairing each event
        with the most recent event from the other stream. This is useful when
        you need to react to changes in either stream while using state from both.

        The output fires when *either* input fires, using the latest known value
        from the other stream. No output occurs until both streams have fired
        at least once.

        Example:
            # Track both slider position and checkbox state
            combined = slider_changes.combine_latest(checkbox_changes)
        """
        def combined() -> TimedBuffer[Tuple[T, U]]:
            self_events = list(self.events())
            other_events = list(other.events())
            if not self_events or not other_events:
                return TimedBuffer([])

            result: List[Tuple[float, Tuple[T, U]]] = []
            latest_self: Optional[T] = None
            latest_other: Optional[U] = None

            # Merge both event lists by timestamp
            all_events: List[Tuple[float, str, Any]] = []
            for ts, v in self_events:
                all_events.append((ts, 'self', v))
            for ts, v in other_events:
                all_events.append((ts, 'other', v))
            all_events.sort(key=lambda x: x[0])

            for ts, source, value in all_events:
                if source == 'self':
                    latest_self = value
                else:
                    latest_other = value

                if latest_self is not None and latest_other is not None:
                    result.append((ts, (latest_self, latest_other)))

            return TimedBuffer(result)
        return EventStream(combined)

    def flat_map(self, fn: Callable[[T], "EventStream[U]"]) -> "EventStream[U]":
        """
        Map each event to a new stream, then flatten all streams into one.

        FRP Concept: `flat_map` (also called `bind` or `>>=` in Haskell) is the
        monadic bind operation for event streams. It allows dynamic stream creation
        based on event values.

        Each event in this stream is transformed into a new EventStream by `fn`.
        All resulting streams are merged together into a single output stream.

        Use cases:
        - Spawning sub-processes or sub-streams based on events
        - Dynamic event routing
        - Chaining async operations

        Example:
            # Each search query spawns a stream of results
            all_results = search_queries.flat_map(lambda query: search_api(query))
        """
        def flattened() -> TimedBuffer[U]:
            result: List[Tuple[float, U]] = []
            for ts, v in self.events():
                child_stream = fn(v)
                result.extend(child_stream.events())
            result.sort(key=lambda x: x[0])
            return TimedBuffer(result)
        return EventStream(flattened)


class TimedBuffer(list, EventStream[T]):
    """
    A concrete, immutable-ish snapshot of events: list of (timestamp, value) tuples.

    TimedBuffer is BOTH a list AND an EventStream. This dual inheritance means:
    - Use it like a list: `len(buf)`, `buf[0]`, `buf[-1]`, iteration, slicing
    - Use it like a stream: `.map()`, `.filter()`, `.merge()`, etc.

    Key distinction from EventStream:
    - EventStream is LAZY: wraps a callable, re-evaluates on each `.events()` call
    - TimedBuffer is EAGER: data is fixed at creation time

    When you call transformation methods on TimedBuffer, they return NEW TimedBuffers
    (eager evaluation). This is efficient for finite, already-computed event lists.
    """

    def __init__(self, data: Optional[Iterable[Tuple[float, T]]] = None):
        if data is None:
            list.__init__(self)
        else:
            list.__init__(self, data)
        # EventStream expects a callable - we return self (identity)
        EventStream.__init__(self, events=lambda: self)

    # Override transformation methods to return TimedBuffer directly (eager)
    # This avoids the nested closure pattern and is more efficient for fixed data.

    def map(self, fn: Callable[[T], U]) -> "TimedBuffer[U]":
        """Transform each value, returning a new TimedBuffer (eager)."""
        return TimedBuffer([(ts, fn(v)) for ts, v in self])

    def filter(self, pred: Callable[[T], bool]) -> "TimedBuffer[T]":
        """Keep matching events, returning a new TimedBuffer (eager)."""
        return TimedBuffer([(ts, v) for ts, v in self if pred(v)])

    def merge(self, other: "TimedBuffer[T]") -> "TimedBuffer[T]":
        """Merge with another buffer by timestamp (eager)."""
        combined = list(self) + list(other)
        combined.sort(key=lambda x: x[0])
        return TimedBuffer(combined)

    def delay(self, dt: float) -> "TimedBuffer[T]":
        """Delay all events by dt seconds (eager)."""
        return TimedBuffer([(ts + dt, v) for ts, v in self])

    def take(self, n: int) -> "TimedBuffer[T]":
        """Keep first N events (eager)."""
        return TimedBuffer(self[:n])

    def drop(self, n: int) -> "TimedBuffer[T]":
        """Skip first N events (eager)."""
        return TimedBuffer(self[n:])


@dataclass(frozen=True)
class Behavior(Generic[T]):
    """
    Continuous-time behavior: a value that can be sampled at any time `t`.
    """

    sample: Callable[[float], T]

    @staticmethod
    def constant(value: T) -> "Behavior[T]":
        """
        Create a behavior that always returns the same value.

        FRP Concept: `constant` is the simplest behavior - a value that never changes.
        When sampled at any time `t`, it returns the same value.

        Example:
            gravity = Behavior.constant(9.81)
        """
        return Behavior(lambda t: value)

    @staticmethod
    def time() -> "Behavior[float]":
        """
        Create a behavior that returns the current sample time.

        FRP Concept: This is the identity behavior for time. When sampled at time `t`,
        it returns `t`. Useful for time-dependent computations.

        Example:
            elapsed = Behavior.time().map(lambda t: t - start_time)
        """
        return Behavior(lambda t: t)

    @staticmethod
    def select(control: "Behavior[bool]", true_behavior: "Behavior[T]", false_behavior: "Behavior[T]") -> "Behavior[T]":
        """
        Switch between two behaviors based on a boolean control.

        FRP Concept: `select` (or `switch`) dynamically chooses which behavior to
        sample based on a control signal. At each sample time, if the control is True,
        sample from true_behavior; otherwise sample from false_behavior.

        Example:
            output = Behavior.select(is_paused, frozen_value, live_value)
        """
        def switched_sample(t: float) -> T:
            if control.at(t):
                return true_behavior.at(t)
            else:
                return false_behavior.at(t)
        return Behavior(switched_sample)

    @staticmethod
    def lift2(fn: Callable[[T, U], Any], b1: "Behavior[T]", b2: "Behavior[U]") -> "Behavior[Any]":
        """
        Apply a two-argument function to two behaviors pointwise.

        FRP Concept: `lift` generalizes function application to behaviors. Instead of
        applying a function to two values, we apply it to two behaviors, producing
        a new behavior whose value at time `t` is `fn(b1.at(t), b2.at(t))`.

        This is the applicative functor pattern for behaviors.

        Example:
            distance = Behavior.lift2(lambda x, y: math.sqrt(x**2 + y**2), pos_x, pos_y)
        """
        return Behavior(lambda t: fn(b1.at(t), b2.at(t)))

    @staticmethod
    def lift3(fn: Callable[[Any, Any, Any], Any], b1: "Behavior[Any]", b2: "Behavior[Any]", b3: "Behavior[Any]") -> "Behavior[Any]":
        """
        Apply a three-argument function to three behaviors pointwise.

        FRP Concept: Same as `lift2` but for three behaviors.

        Example:
            rgb = Behavior.lift3(lambda r, g, b: (r, g, b), red, green, blue)
        """
        return Behavior(lambda t: fn(b1.at(t), b2.at(t), b3.at(t)))

    @staticmethod
    def hold(initial: T, event_stream: EventStream[T]) -> "Behavior[T]":
        """
        Create a behavior that holds the most recent event value.

        FRP Concept: `hold` converts a discrete event stream into a continuous behavior.
        The behavior starts with `initial`, and whenever an event occurs, the behavior
        "steps" to the new value and holds it until the next event.

        This is the fundamental bridge from discrete to continuous: events become
        state that persists between occurrences.

        Also known as: `stepper`, `hold`, or "zero-order hold" in signal processing.

        Example:
            # Track the last clicked button
            selected_button: Behavior[str] = Behavior.hold("none", button_clicks)
        """
        def held(t: float) -> T:
            events = event_stream.events()
            # Find the most recent event before or at time t
            latest_value = initial
            for ts, v in events:
                if ts <= t:
                    latest_value = v
                else:
                    break  # Events are sorted, no need to continue
            return latest_value
        return Behavior(held)

    def at(self, t: float) -> T:
        """Sample this behavior at time `t`."""
        return self.sample(t)

    def at_time(self, t: float) -> T:
        """Backward-compatible alias (`at_time(t)` matches older FRP naming)."""
        return self.sample(t)

    def map(self, fn: Callable[[T], U]) -> "Behavior[U]":
        """
        Transform this behavior's value using a function.

        FRP Concept: `map` applies a pure function to the behavior's value at each
        sample time. The timing is unchanged; only the value is transformed.

        Example:
            celsius = fahrenheit.map(lambda f: (f - 32) * 5/9)
        """
        return Behavior(lambda t: fn(self.sample(t)))

    def combine(self, other: "Behavior[U]") -> "Behavior[Tuple[T, U]]":
        """
        Pair this behavior with another, sampling both at the same time.

        FRP Concept: `combine` creates a product behavior. At any time `t`, the
        resulting behavior's value is a tuple of both input behaviors' values.

        Example:
            position = x_pos.combine(y_pos)  # Behavior[(float, float)]
        """
        return Behavior(lambda t: (self.sample(t), other.sample(t)))

    def until(self, event_stream: EventStream[Any], default_value: T) -> "Behavior[T]":
        """Behavior that switches to default value when event occurs."""
        def until_sample(t: float) -> T:
            if event_stream.within(duration=0.001, now=t):
                return default_value
            return self.at(t)
        return Behavior(until_sample)

    def sample_at_rate(self, hz: float) -> "Behavior[T]":
        """
        Rate-limit sampling to at most `hz` by caching the last sampled value.
        """
        if hz <= 0:
            raise ValueError(f"hz must be > 0 (got {hz})")

        last_sample_time = [0.0]
        last_value: List[Optional[T]] = [None]
        period = 1.0 / hz
        lock = threading.Lock()

        def rate_limited_sample(t: float) -> T:
            with lock:
                if t - last_sample_time[0] >= period or last_value[0] is None:
                    last_value[0] = self.sample(t)
                    last_sample_time[0] = t
                # mypy: last_value[0] cannot be None here
                return last_value[0]  # type: ignore[return-value]

        return Behavior(rate_limited_sample)

    def filter_map(self, fn: Callable[[T], Optional[U]]) -> "EventStream[U]":
        """
        Convert a Behavior to an EventStream by emitting an event when `fn(value)` returns a value.
        """
        buffer: TimedBuffer[U] = TimedBuffer()
        lock = threading.Lock()

        def event_generator() -> TimedBuffer[U]:
            now = time.time()
            value = self.sample(now)
            result = fn(value)

            with lock:
                if result is not None:
                    buffer.append((now, result))
                    cutoff = now - 60.0
                    buffer[:] = TimedBuffer([(t, v) for t, v in buffer if t >= cutoff])
                return list(buffer)

        return EventStream(event_generator)


class EventManager:
    """Manages event streams and their coordination.

    Handles event-driven behaviors like obstacle detection triggering replanning.
    This is a high-level pattern for registering handlers on named event streams.

    Note: For actual multi-rate execution, use the Clock system (Rate, Trigger, Hybrid)
    with the runtime's Scheduler. This class is for application-level event routing.
    """

    def __init__(self):
        self.event_streams: Dict[str, EventStream] = {}
        self.event_handlers: Dict[str, List[Callable[[Any, float], None]]] = {}

    def register_event_stream(self, name: str, stream: EventStream):
        """Register an event stream."""
        self.event_streams[name] = stream
        if name not in self.event_handlers:
            self.event_handlers[name] = []

    def add_event_handler(self, event_name: str, handler: Callable[[Any, float], None]):
        """Add handler for specific event type."""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)

    def process_events(self, current_time: float, window: float = 0.1):
        """Process recent events and call handlers."""
        for event_name, stream in self.event_streams.items():
            recent_events = stream.within(duration=window, now=current_time)
            handlers = self.event_handlers.get(event_name, [])

            for ts, event_value in recent_events:
                for handler in handlers:
                    try:
                        handler(event_value, ts)
                    except Exception as e:
                        print(f"Error in event handler for {event_name}: {e}")

    def create_merged_event_stream(self, *event_names: str) -> EventStream[Tuple[str, Any]]:
        """Create event stream that merges multiple named event streams."""
        def merged_stream_fn() -> TimedBuffer[Tuple[str, Any]]:
            all_events: TimedBuffer[Tuple[str, Any]] = TimedBuffer([])
            for name in event_names:
                if name in self.event_streams:
                    stream_events = self.event_streams[name].events()
                    tagged_events = [(t, (name, v)) for t, v in stream_events]
                    all_events.extend(tagged_events)

            return TimedBuffer(sorted(all_events, key=lambda x: x[0]))

        return EventStream(merged_stream_fn)


def behavior_from_events(stream: EventStream[T], adapter: "Adapter[T]") -> Behavior[T]:
    """Create a behavior by sampling an event stream with an adapter."""
    return Behavior(lambda t: stream.sample(adapter, now=t))


def events_from_iter(events: Iterable[Tuple[float, T]]) -> EventStream[T]:
    """Convenience: wrap a static iterable as an EventStream."""
    buf = list(events)
    buf.sort(key=lambda x: x[0])
    return EventStream(lambda: TimedBuffer(buf))

