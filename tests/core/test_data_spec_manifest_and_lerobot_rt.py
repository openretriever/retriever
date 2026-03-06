from __future__ import annotations

import pytest

from retriever.data_spec import (
    DataSpec,
    Event,
    EventBuffer,
    SchemaRef,
    StreamId,
    StreamSpec,
    build_dataset_manifest,
    build_episode_manifest,
    from_lerobot_records,
    to_lerobot_records,
    validate_dataset_manifest,
    validate_lerobot_mapping,
)


def _evt(stream: str, event_ns: int, ingest_ns: int, seq: int, value: object, type_name: str) -> Event[object]:
    return Event(
        stream_id=StreamId(stream),
        event_time_ns=event_ns,
        ingest_time_ns=ingest_ns,
        seq=seq,
        value=value,
        type_name=type_name,
    )


def _rows() -> list[dict]:
    return [
        {
            "episode_id": "ep-1",
            "stream_id": "cam",
            "event_time_ns": 100,
            "ingest_time_ns": 110,
            "seq": 0,
            "type_name": "RGBImage",
            "payload": {"id": 1},
            "lineage": [],
            "frame_id": "camera",
            "units": None,
        },
        {
            "episode_id": "ep-1",
            "stream_id": "cam",
            "event_time_ns": 200,
            "ingest_time_ns": 210,
            "seq": 1,
            "type_name": "RGBImage",
            "payload": {"id": 2},
            "lineage": [],
            "frame_id": "camera",
            "units": None,
        },
        {
            "episode_id": "ep-1",
            "stream_id": "joint",
            "event_time_ns": 150,
            "ingest_time_ns": 151,
            "seq": 0,
            "type_name": "JointState",
            "payload": {"q": [0.1, 0.2]},
            "lineage": [],
            "frame_id": "base",
            "units": "rad",
        },
    ]


def test_dataset_manifest_validation() -> None:
    spec = DataSpec(
        name="robot-episode",
        version="1.0",
        streams=(
            StreamSpec(stream_id=StreamId("cam"), schema=SchemaRef(name="RGBImage")),
            StreamSpec(stream_id=StreamId("joint"), schema=SchemaRef(name="JointState")),
        ),
    )
    events_by_stream = {
        "cam": EventBuffer((_evt("cam", 100, 100, 0, {"id": 1}, "RGBImage"),)),
        "joint": EventBuffer((_evt("joint", 150, 150, 0, {"q": [0.1]}, "JointState"),)),
    }
    episode = build_episode_manifest("ep-1", events_by_stream)
    manifest = build_dataset_manifest("ds-1", spec=spec, episodes=(episode,), source="unit-test")
    validate_dataset_manifest(manifest)

    bad_episode = build_episode_manifest("ep-2", {"missing": EventBuffer()})
    bad_manifest = build_dataset_manifest("ds-2", spec=spec, episodes=(bad_episode,), source="unit-test")
    with pytest.raises(ValueError, match="not present in data spec"):
        validate_dataset_manifest(bad_manifest)


def test_lerobot_roundtrip_preserves_core_fields() -> None:
    rows = _rows()
    records = to_lerobot_records(rows)

    validate_lerobot_mapping(records)

    roundtrip = from_lerobot_records(records)
    assert len(roundtrip) == len(rows)

    by_key = {
        (row["stream_id"], row["event_time_ns"], row["type_name"]): row
        for row in roundtrip
    }
    assert by_key[("cam", 100, "RGBImage")]["payload"] == {"id": 1}
    assert by_key[("joint", 150, "JointState")]["units"] == "rad"


def test_lerobot_validation_rejects_missing_fields() -> None:
    bad = [{"episode_id": "ep", "stream_id": "cam"}]
    with pytest.raises(ValueError):
        validate_lerobot_mapping(bad)
