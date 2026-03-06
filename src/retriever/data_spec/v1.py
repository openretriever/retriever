"""Retriever data/event specification v1.

This module defines immutable contracts for event records, stream policies,
and dataset manifests used by collection/replay/export workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, Mapping, Optional, TypeVar, Literal

T = TypeVar("T")

JoinMode = Literal["exact", "latest_before", "window"]
WindowAgg = Literal["first", "last", "max", "min", "mean"]


@dataclass(frozen=True, order=True)
class StreamId:
    """Stable stream identifier used in event ordering and manifests."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("stream id must be non-empty")

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def parse(value: str | "StreamId") -> "StreamId":
        if isinstance(value, StreamId):
            return value
        return StreamId(value=value)


@dataclass(frozen=True)
class ClockDomain:
    """Clock domain for streams and data specs."""

    name: str = "event_time"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("clock domain name must be non-empty")


@dataclass(frozen=True)
class SchemaRef:
    """Schema identity for typed payloads."""

    name: str
    version: str = "v1"
    encoding: str = "python"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("schema name must be non-empty")
        if not self.version:
            raise ValueError("schema version must be non-empty")


@dataclass(frozen=True)
class EventRef:
    """Reference to a single source event for lineage tracking."""

    stream_id: StreamId
    event_time_ns: int
    ingest_time_ns: int
    seq: int
    type_name: str

    def __post_init__(self) -> None:
        if self.event_time_ns < 0:
            raise ValueError("event_time_ns must be >= 0")
        if self.ingest_time_ns < 0:
            raise ValueError("ingest_time_ns must be >= 0")
        if self.seq < 0:
            raise ValueError("seq must be >= 0")
        if not self.type_name:
            raise ValueError("type_name must be non-empty")


@dataclass(frozen=True)
class LineageRef:
    """Lineage metadata attached to derived events."""

    sources: tuple[EventRef, ...] = ()
    transform: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))


@dataclass(frozen=True)
class Event(Generic[T]):
    """Canonical event record in event-time space."""

    stream_id: StreamId
    event_time_ns: int
    ingest_time_ns: int
    seq: int
    value: T
    type_name: str = ""
    schema: Optional[SchemaRef] = None
    frame_id: Optional[str] = None
    units: Optional[str] = None
    lineage: Optional[LineageRef] = None

    def __post_init__(self) -> None:
        if self.event_time_ns < 0:
            raise ValueError("event_time_ns must be >= 0")
        if self.ingest_time_ns < 0:
            raise ValueError("ingest_time_ns must be >= 0")
        if self.seq < 0:
            raise ValueError("seq must be >= 0")
        if not self.type_name:
            object.__setattr__(self, "type_name", type(self.value).__name__)

    def ordering_key(self) -> tuple[int, int, str, int]:
        return (
            self.event_time_ns,
            self.ingest_time_ns,
            str(self.stream_id),
            self.seq,
        )

    def ref(self) -> EventRef:
        return EventRef(
            stream_id=self.stream_id,
            event_time_ns=self.event_time_ns,
            ingest_time_ns=self.ingest_time_ns,
            seq=self.seq,
            type_name=self.type_name,
        )


@dataclass(frozen=True)
class EventBuffer(Generic[T]):
    """Immutable event buffer."""

    events: tuple[Event[T], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))

    def __iter__(self):
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __getitem__(self, idx: int) -> Event[T]:
        return self.events[idx]

    def sorted(self) -> "EventBuffer[T]":
        return EventBuffer(tuple(sorted(self.events, key=lambda event: event.ordering_key())))

    def append(self, event: Event[T]) -> "EventBuffer[T]":
        return EventBuffer(self.events + (event,))

    def latest_event(self) -> Optional[Event[T]]:
        if not self.events:
            return None
        return self.sorted().events[-1]

    def latest_value(self) -> Optional[T]:
        event = self.latest_event()
        if event is None:
            return None
        return event.value

    def within(self, start_ns: int, end_ns: int) -> "EventBuffer[T]":
        if end_ns < start_ns:
            raise ValueError("end_ns must be >= start_ns")
        return EventBuffer(
            tuple(
                event
                for event in self.events
                if start_ns <= event.event_time_ns <= end_ns
            )
        )

    def values(self) -> tuple[T, ...]:
        return tuple(event.value for event in self.events)


@dataclass(frozen=True)
class MultiStreamBuffer:
    """Named collection of stream buffers."""

    streams: Mapping[str, EventBuffer[Any]]

    def __post_init__(self) -> None:
        canon: Dict[str, EventBuffer[Any]] = {}
        for name, buffer in self.streams.items():
            if not name:
                raise ValueError("stream name must be non-empty")
            canon[name] = buffer
        object.__setattr__(self, "streams", canon)

    def stream_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.streams.keys()))

    def get(self, name: str) -> EventBuffer[Any]:
        return self.streams[name]


@dataclass(frozen=True)
class JoinPolicy:
    """Policy used by event-time join operators."""

    mode: JoinMode = "exact"
    max_delta_ns: int = 0
    window_ns: int = 0

    def __post_init__(self) -> None:
        if self.max_delta_ns < 0:
            raise ValueError("max_delta_ns must be >= 0")
        if self.window_ns < 0:
            raise ValueError("window_ns must be >= 0")


@dataclass(frozen=True)
class WatermarkPolicy:
    """Watermark policy for pruning old or late events."""

    watermark_ns: int
    allowed_lateness_ns: int = 0
    drop_late: bool = True

    def __post_init__(self) -> None:
        if self.watermark_ns < 0:
            raise ValueError("watermark_ns must be >= 0")
        if self.allowed_lateness_ns < 0:
            raise ValueError("allowed_lateness_ns must be >= 0")


@dataclass(frozen=True)
class WindowPolicy:
    """Windowed aggregation policy."""

    duration_ns: int
    agg: WindowAgg = "last"

    def __post_init__(self) -> None:
        if self.duration_ns <= 0:
            raise ValueError("duration_ns must be > 0")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type_name: str
    required: bool = True
    frame_id: Optional[str] = None
    units: Optional[str] = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("field name must be non-empty")
        if not self.type_name:
            raise ValueError("field type_name must be non-empty")


@dataclass(frozen=True)
class StreamSpec:
    stream_id: StreamId
    schema: SchemaRef
    clock_domain: ClockDomain = ClockDomain("event_time")
    fields: tuple[FieldSpec, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(self.fields))


@dataclass(frozen=True)
class DataSpec:
    name: str
    version: str
    streams: tuple[StreamSpec, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("data spec name must be non-empty")
        if not self.version:
            raise ValueError("data spec version must be non-empty")
        object.__setattr__(self, "streams", tuple(self.streams))

    def stream_map(self) -> dict[str, StreamSpec]:
        return {str(stream.stream_id): stream for stream in self.streams}


@dataclass(frozen=True)
class EpisodeManifest:
    episode_id: str
    stream_ids: tuple[str, ...]
    start_event_time_ns: int
    end_event_time_ns: int
    event_count: int
    artifacts: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        if self.start_event_time_ns < 0:
            raise ValueError("start_event_time_ns must be >= 0")
        if self.end_event_time_ns < self.start_event_time_ns:
            raise ValueError("end_event_time_ns must be >= start_event_time_ns")
        if self.event_count < 0:
            raise ValueError("event_count must be >= 0")
        object.__setattr__(self, "stream_ids", tuple(self.stream_ids))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", tuple(self.metadata))


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    spec: DataSpec
    episodes: tuple[EpisodeManifest, ...]
    created_at_ns: int
    source: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id must be non-empty")
        if self.created_at_ns <= 0:
            raise ValueError("created_at_ns must be > 0")
        if not self.source:
            raise ValueError("source must be non-empty")
        object.__setattr__(self, "episodes", tuple(self.episodes))
        object.__setattr__(self, "metadata", tuple(self.metadata))

    @property
    def event_count(self) -> int:
        return sum(episode.event_count for episode in self.episodes)


__all__ = [
    "ClockDomain",
    "DataSpec",
    "DatasetManifest",
    "EpisodeManifest",
    "Event",
    "EventBuffer",
    "EventRef",
    "FieldSpec",
    "JoinMode",
    "JoinPolicy",
    "LineageRef",
    "MultiStreamBuffer",
    "SchemaRef",
    "StreamId",
    "StreamSpec",
    "WatermarkPolicy",
    "WindowAgg",
    "WindowPolicy",
]
