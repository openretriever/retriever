"""Interop adapters for runtime event buffers and LeRobot-style row exports.

These helpers bridge between:
- runtime tuple buffers: `list[(timestamp_seconds, value)]`
- canonical `retriever.types.data.EventBuffer`
- plain row dictionaries for export tooling
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional, Sequence

from .events import Event, EventBuffer, StreamId


def from_runtime_event_buffer(
    runtime_buffer: Sequence[tuple[float, Any]],
    *,
    stream_id: str,
    frame_id: Optional[str] = None,
    units: Optional[str] = None,
    ingest_offset_ns: int = 0,
) -> EventBuffer[Any]:
    """Convert a runtime tuple buffer into a typed data-event buffer.

    This is a structural adapter. It preserves order and timestamps, but it does
    not infer schemas beyond the provided stream/frame/unit metadata.
    """
    if ingest_offset_ns < 0:
        raise ValueError("ingest_offset_ns must be >= 0")

    events = []
    for seq, (timestamp_sec, value) in enumerate(runtime_buffer):
        event_time_ns = int(float(timestamp_sec) * 1_000_000_000)
        ingest_time_ns = event_time_ns + ingest_offset_ns
        events.append(
            Event(
                stream_id=StreamId.parse(stream_id),
                event_time_ns=event_time_ns,
                ingest_time_ns=ingest_time_ns,
                seq=seq,
                value=value,
                type_name=type(value).__name__,
                frame_id=frame_id,
                units=units,
            )
        )
    return EventBuffer(tuple(events)).sorted()


def to_runtime_event_buffer(buffer: EventBuffer[Any]) -> list[tuple[float, Any]]:
    return [
        (event.event_time_ns / 1_000_000_000.0, event.value)
        for event in buffer.sorted()
    ]


def is_runtime_event_buffer(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    if not value:
        return True
    first = value[0]
    return isinstance(first, (tuple, list)) and len(first) == 2


def to_lerobot_records(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project plain event rows into LeRobot-style episode/frame records."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["episode_id"], row["stream_id"])].append(row)

    records = []
    for (episode_id, stream_id), group in grouped.items():
        ordered = sorted(
            group,
            key=lambda row: (
                row["event_time_ns"],
                row["ingest_time_ns"],
                row["stream_id"],
                row["seq"],
            ),
        )
        for frame_index, row in enumerate(ordered):
            records.append(
                {
                    "episode_id": episode_id,
                    "stream_id": stream_id,
                    "frame_index": frame_index,
                    "timestamp_ns": row["event_time_ns"],
                    "type_name": row["type_name"],
                    "payload": row["payload"],
                    "metadata": {
                        "ingest_time_ns": row["ingest_time_ns"],
                        "seq": row["seq"],
                        "frame_id": row.get("frame_id"),
                        "units": row.get("units"),
                        "lineage": row.get("lineage", []),
                    },
                }
            )

    records.sort(key=lambda rec: (rec["episode_id"], rec["stream_id"], rec["frame_index"]))
    return records


def from_lerobot_records(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert LeRobot-style records back into plain event-row dictionaries."""
    rows = []
    for record in records:
        metadata = record.get("metadata", {})
        timestamp_ns = int(record["timestamp_ns"])
        rows.append(
            {
                "episode_id": record["episode_id"],
                "stream_id": record["stream_id"],
                "event_time_ns": timestamp_ns,
                "ingest_time_ns": int(metadata.get("ingest_time_ns", timestamp_ns)),
                "seq": int(metadata.get("seq", record.get("frame_index", 0))),
                "type_name": record["type_name"],
                "payload": record.get("payload"),
                "lineage": metadata.get("lineage", []),
                "frame_id": metadata.get("frame_id"),
                "units": metadata.get("units"),
            }
        )

    rows.sort(
        key=lambda row: (
            row["event_time_ns"],
            row["ingest_time_ns"],
            row["stream_id"],
            row["seq"],
        )
    )
    return rows


def validate_lerobot_mapping(records: Sequence[dict[str, Any]]) -> None:
    """Validate the minimal row-shape invariants expected by the LeRobot adapters."""
    required = {
        "episode_id",
        "stream_id",
        "frame_index",
        "timestamp_ns",
        "type_name",
        "payload",
        "metadata",
    }

    frame_indices: dict[tuple[str, str], list[int]] = defaultdict(list)

    for idx, record in enumerate(records):
        missing = sorted(required.difference(record.keys()))
        if missing:
            raise ValueError(f"record[{idx}] missing keys: {missing}")

        frame_index = int(record["frame_index"])
        if frame_index < 0:
            raise ValueError(f"record[{idx}] frame_index must be >= 0")

        timestamp_ns = int(record["timestamp_ns"])
        if timestamp_ns < 0:
            raise ValueError(f"record[{idx}] timestamp_ns must be >= 0")

        key = (str(record["episode_id"]), str(record["stream_id"]))
        frame_indices[key].append(frame_index)

    for key, indices in frame_indices.items():
        expected = list(range(len(indices)))
        if sorted(indices) != expected:
            raise ValueError(
                f"non-contiguous frame_index for {key}: got {sorted(indices)}, expected {expected}"
            )


__all__ = [
    "from_lerobot_records",
    "from_runtime_event_buffer",
    "is_runtime_event_buffer",
    "to_lerobot_records",
    "to_runtime_event_buffer",
    "validate_lerobot_mapping",
]
