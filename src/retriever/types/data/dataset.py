"""Dataset manifest helpers for retriever.types.data.v1."""

from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

from .buffer import merge_sorted
from .v1 import DataSpec, DatasetManifest, EpisodeManifest, Event, EventBuffer, LineageRef

EVENT_TABLE_COLUMNS = (
    "episode_id",
    "stream_id",
    "event_time_ns",
    "ingest_time_ns",
    "seq",
    "type_name",
    "payload",
    "lineage",
    "frame_id",
    "units",
)


def _lineage_to_rows(lineage: LineageRef | None) -> list[dict[str, Any]]:
    if lineage is None:
        return []
    rows = []
    for source in lineage.sources:
        rows.append(
            {
                "stream_id": str(source.stream_id),
                "event_time_ns": source.event_time_ns,
                "ingest_time_ns": source.ingest_time_ns,
                "seq": source.seq,
                "type_name": source.type_name,
            }
        )
    return rows


def event_to_row(event: Event[Any], *, episode_id: str) -> dict[str, Any]:
    return {
        "episode_id": episode_id,
        "stream_id": str(event.stream_id),
        "event_time_ns": event.event_time_ns,
        "ingest_time_ns": event.ingest_time_ns,
        "seq": event.seq,
        "type_name": event.type_name,
        "payload": event.value,
        "lineage": _lineage_to_rows(event.lineage),
        "frame_id": event.frame_id,
        "units": event.units,
    }


def event_table_rows(events: EventBuffer[Any], *, episode_id: str) -> list[dict[str, Any]]:
    return [event_to_row(event, episode_id=episode_id) for event in events.sorted()]


def build_episode_manifest(
    episode_id: str,
    events_by_stream: Mapping[str, EventBuffer[Any]],
    *,
    artifacts: Sequence[str] = (),
    metadata: Mapping[str, str] | None = None,
) -> EpisodeManifest:
    merged = merge_sorted(*events_by_stream.values()) if events_by_stream else EventBuffer()

    if len(merged) == 0:
        start_ns = 0
        end_ns = 0
    else:
        ordered = merged.sorted().events
        start_ns = ordered[0].event_time_ns
        end_ns = ordered[-1].event_time_ns

    metadata_items = tuple(sorted((metadata or {}).items()))
    return EpisodeManifest(
        episode_id=episode_id,
        stream_ids=tuple(sorted(events_by_stream.keys())),
        start_event_time_ns=start_ns,
        end_event_time_ns=end_ns,
        event_count=len(merged),
        artifacts=tuple(artifacts),
        metadata=metadata_items,
    )


def build_dataset_manifest(
    dataset_id: str,
    *,
    spec: DataSpec,
    episodes: Sequence[EpisodeManifest],
    source: str,
    created_at_ns: int | None = None,
    metadata: Mapping[str, str] | None = None,
) -> DatasetManifest:
    if created_at_ns is None:
        created_at_ns = time.time_ns()
    return DatasetManifest(
        dataset_id=dataset_id,
        spec=spec,
        episodes=tuple(episodes),
        created_at_ns=created_at_ns,
        source=source,
        metadata=tuple(sorted((metadata or {}).items())),
    )


def validate_dataset_manifest(manifest: DatasetManifest) -> None:
    spec_streams = set(manifest.spec.stream_map().keys())
    for episode in manifest.episodes:
        for stream_id in episode.stream_ids:
            if stream_id not in spec_streams:
                raise ValueError(
                    f"episode '{episode.episode_id}' references stream '{stream_id}' not present in data spec"
                )


__all__ = [
    "EVENT_TABLE_COLUMNS",
    "build_dataset_manifest",
    "build_episode_manifest",
    "event_table_rows",
    "event_to_row",
    "validate_dataset_manifest",
]
