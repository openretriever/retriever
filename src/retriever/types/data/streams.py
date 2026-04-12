"""Event stream helpers and multi-stream joins."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, TypeVar

from .events import Event, EventBuffer, JoinPolicy, LineageRef, StreamId, WatermarkPolicy, WindowPolicy

A = TypeVar("A")
B = TypeVar("B")


def merge_sorted(*buffers: EventBuffer[Any]) -> EventBuffer[Any]:
    merged = []
    for buffer in buffers:
        merged.extend(buffer.events)
    return EventBuffer(tuple(sorted(merged, key=lambda event: event.ordering_key())))


def watermark_prune(buffer: EventBuffer[Any], policy: WatermarkPolicy) -> EventBuffer[Any]:
    threshold = policy.watermark_ns - policy.allowed_lateness_ns
    if not policy.drop_late:
        return buffer
    return EventBuffer(tuple(event for event in buffer.events if event.event_time_ns >= threshold))


def latest(buffer: EventBuffer[Any]) -> Any:
    event = buffer.latest_event()
    if event is None:
        raise IndexError("cannot sample latest from empty buffer")
    return event.value


def hold(buffer: EventBuffer[Any], *, now_ns: int, last_value: Optional[Any] = None) -> Optional[Any]:
    if now_ns < 0:
        raise ValueError("now_ns must be >= 0")

    candidates = [event for event in buffer.events if event.event_time_ns <= now_ns]
    if not candidates:
        return last_value
    return sorted(candidates, key=lambda event: event.ordering_key())[-1].value


def window_values(buffer: EventBuffer[Any], *, now_ns: int, duration_ns: int) -> tuple[Any, ...]:
    if duration_ns <= 0:
        raise ValueError("duration_ns must be > 0")
    start = now_ns - duration_ns
    window = buffer.within(start_ns=start, end_ns=now_ns)
    ordered = window.sorted()
    return ordered.values()


def window_agg(
    buffer: EventBuffer[Any],
    *,
    now_ns: int,
    policy: WindowPolicy,
    fallback: Optional[Any] = None,
) -> Any:
    values = window_values(buffer, now_ns=now_ns, duration_ns=policy.duration_ns)
    if not values:
        return fallback

    if policy.agg == "first":
        return values[0]
    if policy.agg == "last":
        return values[-1]
    if policy.agg == "max":
        return max(values)
    if policy.agg == "min":
        return min(values)
    if policy.agg == "mean":
        total = 0.0
        for value in values:
            total += float(value)
        return total / len(values)

    raise ValueError(f"unsupported aggregation: {policy.agg}")


def event_window(
    buffer: EventBuffer[Any],
    *,
    now_ns: int,
    duration_ns: int,
) -> EventBuffer[Any]:
    if duration_ns <= 0:
        raise ValueError("duration_ns must be > 0")
    start_ns = now_ns - duration_ns
    return buffer.within(start_ns=start_ns, end_ns=now_ns).sorted()


def processing_window_agg(
    buffer: EventBuffer[Any],
    *,
    now_ns: int,
    policy: WindowPolicy,
    fallback: Optional[Any] = None,
) -> Any:
    return window_agg(buffer, now_ns=now_ns, policy=policy, fallback=fallback)


def from_events(events: Iterable[Event[Any]]) -> EventBuffer[Any]:
    return EventBuffer(tuple(events)).sorted()


def _joined_event(
    *,
    stream_id: str,
    seq: int,
    event_time_ns: int,
    ingest_time_ns: int,
    left: Event[A],
    right: Event[B],
) -> Event[tuple[A, B]]:
    lineage = LineageRef(sources=(left.ref(), right.ref()), transform="event_join")
    return Event(
        stream_id=StreamId.parse(stream_id),
        event_time_ns=event_time_ns,
        ingest_time_ns=ingest_time_ns,
        seq=seq,
        value=(left.value, right.value),
        type_name=f"tuple[{left.type_name},{right.type_name}]",
        lineage=lineage,
    )


def align_exact(
    left: EventBuffer[A],
    right: EventBuffer[B],
    *,
    output_stream_id: str = "join.exact",
) -> EventBuffer[tuple[A, B]]:
    left_groups: Dict[int, List[Event[A]]] = defaultdict(list)
    right_groups: Dict[int, List[Event[B]]] = defaultdict(list)

    for event in left.sorted():
        left_groups[event.event_time_ns].append(event)
    for event in right.sorted():
        right_groups[event.event_time_ns].append(event)

    out = []
    seq = 0
    for timestamp in sorted(set(left_groups.keys()) & set(right_groups.keys())):
        left_events = sorted(left_groups[timestamp], key=lambda event: event.ordering_key())
        right_events = sorted(right_groups[timestamp], key=lambda event: event.ordering_key())
        pair_count = min(len(left_events), len(right_events))
        for idx in range(pair_count):
            left_event = left_events[idx]
            right_event = right_events[idx]
            out.append(
                _joined_event(
                    stream_id=output_stream_id,
                    seq=seq,
                    event_time_ns=timestamp,
                    ingest_time_ns=max(left_event.ingest_time_ns, right_event.ingest_time_ns),
                    left=left_event,
                    right=right_event,
                )
            )
            seq += 1

    return EventBuffer(tuple(out))


def align_latest_before(
    left: EventBuffer[A],
    right: EventBuffer[B],
    *,
    max_delta_ns: int,
    output_stream_id: str = "join.latest_before",
) -> EventBuffer[tuple[A, B]]:
    if max_delta_ns < 0:
        raise ValueError("max_delta_ns must be >= 0")

    left_events = list(left.sorted())
    right_events = list(right.sorted())

    out = []
    seq = 0
    left_idx = 0
    latest_candidate: Event[A] | None = None

    for right_event in right_events:
        while left_idx < len(left_events) and left_events[left_idx].event_time_ns <= right_event.event_time_ns:
            latest_candidate = left_events[left_idx]
            left_idx += 1

        if latest_candidate is None:
            continue

        delta = right_event.event_time_ns - latest_candidate.event_time_ns
        if delta > max_delta_ns:
            continue

        out.append(
            _joined_event(
                stream_id=output_stream_id,
                seq=seq,
                event_time_ns=right_event.event_time_ns,
                ingest_time_ns=max(latest_candidate.ingest_time_ns, right_event.ingest_time_ns),
                left=latest_candidate,
                right=right_event,
            )
        )
        seq += 1

    return EventBuffer(tuple(out))


def align_window(
    left: EventBuffer[A],
    right: EventBuffer[B],
    *,
    window_ns: int,
    output_stream_id: str = "join.window",
) -> EventBuffer[tuple[A, B]]:
    if window_ns < 0:
        raise ValueError("window_ns must be >= 0")

    left_events = list(left.sorted())
    right_events = list(right.sorted())

    out = []
    seq = 0

    for right_event in right_events:
        candidates = [
            left_event
            for left_event in left_events
            if abs(left_event.event_time_ns - right_event.event_time_ns) <= window_ns
        ]
        if not candidates:
            continue

        candidates.sort(
            key=lambda left_event: (
                abs(left_event.event_time_ns - right_event.event_time_ns),
                left_event.ordering_key(),
            )
        )
        chosen = candidates[0]
        out.append(
            _joined_event(
                stream_id=output_stream_id,
                seq=seq,
                event_time_ns=max(chosen.event_time_ns, right_event.event_time_ns),
                ingest_time_ns=max(chosen.ingest_time_ns, right_event.ingest_time_ns),
                left=chosen,
                right=right_event,
            )
        )
        seq += 1

    return EventBuffer(tuple(out))


def join_with_policy(
    left: EventBuffer[A],
    right: EventBuffer[B],
    *,
    policy: JoinPolicy,
    output_stream_id: str = "join.policy",
) -> EventBuffer[tuple[A, B]]:
    if policy.mode == "exact":
        return align_exact(left, right, output_stream_id=output_stream_id)
    if policy.mode == "latest_before":
        return align_latest_before(
            left,
            right,
            max_delta_ns=policy.max_delta_ns,
            output_stream_id=output_stream_id,
        )
    if policy.mode == "window":
        return align_window(
            left,
            right,
            window_ns=policy.window_ns,
            output_stream_id=output_stream_id,
        )
    raise ValueError(f"unsupported join mode: {policy.mode}")


__all__ = [
    "align_exact",
    "align_latest_before",
    "align_window",
    "event_window",
    "from_events",
    "hold",
    "join_with_policy",
    "latest",
    "merge_sorted",
    "processing_window_agg",
    "watermark_prune",
    "window_agg",
    "window_values",
]
