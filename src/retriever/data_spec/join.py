"""Multi-stream event-time join operators."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, TypeVar

from .v1 import Event, EventBuffer, JoinPolicy, LineageRef, StreamId

A = TypeVar("A")
B = TypeVar("B")


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
    "join_with_policy",
]
