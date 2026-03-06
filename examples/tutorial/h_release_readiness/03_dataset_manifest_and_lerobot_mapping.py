"""Dataset manifest and LeRobot mapping tutorial.

Covers:
1) declare a retriever.data_spec data contract
2) build episode/dataset manifests from per-stream events
3) map canonical event rows to LeRobot-compatible records

Run:
  pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
"""

from __future__ import annotations

from pathlib import Path

from retriever.data_spec import (
    DataSpec,
    Event,
    EventBuffer,
    SchemaRef,
    StreamId,
    StreamSpec,
    build_dataset_manifest,
    build_episode_manifest,
    event_table_rows,
    to_lerobot_records,
    validate_dataset_manifest,
    validate_lerobot_mapping,
)

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


def _evt(stream: str, event_ns: int, seq: int, value: object, type_name: str, *, frame_id: str | None = None, units: str | None = None) -> Event[object]:
    return Event(
        stream_id=StreamId(stream),
        event_time_ns=event_ns,
        ingest_time_ns=event_ns,
        seq=seq,
        value=value,
        type_name=type_name,
        frame_id=frame_id,
        units=units,
    )


def main() -> None:
    manifest_path = Path("logs/tutorial_dataset/tut039_dataset_manifest.json")
    records_path = Path("logs/tutorial_dataset/tut039_lerobot_records.json")

    spec = DataSpec(
        name="tutorial-robot-dataset",
        version="1.0",
        streams=(
            StreamSpec(stream_id=StreamId("camera"), schema=SchemaRef(name="RGBImage")),
            StreamSpec(stream_id=StreamId("joint"), schema=SchemaRef(name="JointState")),
        ),
        description="Minimal tutorial data contract.",
    )

    events_by_stream = {
        "camera": EventBuffer(
            (
                _evt("camera", 100, 0, {"frame": 1}, "RGBImage", frame_id="camera"),
                _evt("camera", 200, 1, {"frame": 2}, "RGBImage", frame_id="camera"),
            )
        ),
        "joint": EventBuffer(
            (
                _evt("joint", 150, 0, {"q": [0.1, 0.2]}, "JointState", frame_id="base", units="rad"),
            )
        ),
    }

    episode = build_episode_manifest("ep-001", events_by_stream, artifacts=("logs/tutorial_dataset/raw_episode.jsonl",))
    manifest = build_dataset_manifest("tutorial-dataset", spec=spec, episodes=(episode,), source="tutorial")
    validate_dataset_manifest(manifest)

    rows = []
    for stream_name, buffer in events_by_stream.items():
        rows.extend(event_table_rows(buffer, episode_id="ep-001"))
    records = to_lerobot_records(rows)
    validate_lerobot_mapping(records)

    print("=== Dataset Manifest ===")
    print(format_table(["dataset_id", "episodes", "event_count"], [[manifest.dataset_id, str(len(manifest.episodes)), str(manifest.event_count)]]))
    print("\n=== LeRobot Records ===")
    preview = [[rec["episode_id"], rec["stream_id"], str(rec["frame_index"]), rec["type_name"]] for rec in records]
    print(format_table(["episode_id", "stream_id", "frame_index", "type_name"], preview))

    write_json(
        manifest_path,
        {
            "generated_at": utc_now_iso(),
            "dataset_id": manifest.dataset_id,
            "episode_count": len(manifest.episodes),
            "event_count": manifest.event_count,
            "stream_ids": list(episode.stream_ids),
        },
    )
    write_json(records_path, records)
    print(f"\n[artifact] wrote {manifest_path}")
    print(f"[artifact] wrote {records_path}")


if __name__ == "__main__":
    main()
