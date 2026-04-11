"""Minimal standalone typed contracts for offline data tooling."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True, order=True)
class StreamId:
    """Stable stream identifier for standalone read/write tools."""

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
    """Clock domain for recorded data streams."""

    name: str = "event_time"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("clock domain name must be non-empty")


@dataclass(frozen=True)
class SchemaRef:
    """Schema identity for typed payloads."""

    name: str
    version: str = "v1"
    encoding: str = "json"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("schema name must be non-empty")
        if not self.version:
            raise ValueError("schema version must be non-empty")
        if not self.encoding:
            raise ValueError("schema encoding must be non-empty")


@dataclass(frozen=True)
class Record:
    """Portable offline record format for collaborator-facing tooling."""

    stream_id: StreamId
    timestamp_ns: int
    seq: int
    payload: Mapping[str, Any]
    schema: Optional[SchemaRef] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be >= 0")
        if self.seq < 0:
            raise ValueError("seq must be >= 0")

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stream_id"] = str(self.stream_id)
        return data

    @staticmethod
    def from_json_dict(data: Mapping[str, Any]) -> "Record":
        schema_raw = data.get("schema")
        return Record(
            stream_id=StreamId.parse(str(data["stream_id"])),
            timestamp_ns=int(data["timestamp_ns"]),
            seq=int(data["seq"]),
            payload=dict(data.get("payload", {})),
            schema=SchemaRef(**schema_raw) if isinstance(schema_raw, dict) else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class StreamManifest:
    """Manifest entry for one stream inside a dataset artifact."""

    stream_id: StreamId
    path: str
    clock_domain: ClockDomain = ClockDomain()
    schema: Optional[SchemaRef] = None
    record_count: int = 0

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("stream path must be non-empty")
        if self.record_count < 0:
            raise ValueError("record_count must be >= 0")

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stream_id"] = str(self.stream_id)
        return data

    @staticmethod
    def from_json_dict(data: Mapping[str, Any]) -> "StreamManifest":
        schema_raw = data.get("schema")
        clock_raw = data.get("clock_domain") or {}
        return StreamManifest(
            stream_id=StreamId.parse(str(data["stream_id"])),
            path=str(data["path"]),
            clock_domain=ClockDomain(**clock_raw) if isinstance(clock_raw, dict) else ClockDomain(str(clock_raw)),
            schema=SchemaRef(**schema_raw) if isinstance(schema_raw, dict) else None,
            record_count=int(data.get("record_count", 0)),
        )


@dataclass(frozen=True)
class DatasetManifest:
    """Manifest for a portable standalone dataset artifact."""

    dataset_name: str
    version: str = "v1"
    streams: tuple[StreamManifest, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dataset_name:
            raise ValueError("dataset_name must be non-empty")
        object.__setattr__(self, "streams", tuple(self.streams))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "version": self.version,
            "streams": [stream.to_json_dict() for stream in self.streams],
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_json_dict(data: Mapping[str, Any]) -> "DatasetManifest":
        return DatasetManifest(
            dataset_name=str(data["dataset_name"]),
            version=str(data.get("version", "v1")),
            streams=tuple(
                StreamManifest.from_json_dict(item)
                for item in data.get("streams", [])
                if isinstance(item, Mapping)
            ),
            metadata=dict(data.get("metadata", {})),
        )
