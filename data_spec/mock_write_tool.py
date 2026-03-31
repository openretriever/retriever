"""Deterministic mock data writer for standalone data_spec artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .types import ClockDomain, DatasetManifest, Record, SchemaRef, StreamId, StreamManifest


def write_mock_dataset(
    output_dir: str | Path,
    *,
    dataset_name: str = "mock_dataset",
    stream_count: int = 2,
    records_per_stream: int = 5,
) -> Path:
    """Write a deterministic multi-stream artifact for collaborator testing."""
    output_dir = Path(output_dir)
    streams_dir = output_dir / "streams"
    streams_dir.mkdir(parents=True, exist_ok=True)

    manifests: list[StreamManifest] = []
    base_time_ns = 1_000_000_000

    for stream_idx in range(stream_count):
        stream_id = StreamId(f"stream_{stream_idx + 1}")
        schema = SchemaRef(name="MockPayload", version="v1", encoding="json")
        stream_relpath = Path("streams") / f"{stream_id.value}.jsonl"
        stream_path = output_dir / stream_relpath
        with stream_path.open("w", encoding="utf-8") as handle:
            for seq in range(records_per_stream):
                record = Record(
                    stream_id=stream_id,
                    timestamp_ns=base_time_ns + seq * 100_000_000 + stream_idx * 10_000_000,
                    seq=seq,
                    payload={
                        "value": stream_idx * 100 + seq,
                        "stream_index": stream_idx,
                        "label": f"{stream_id.value}_record_{seq}",
                    },
                    schema=schema,
                    metadata={"source": "mock_write_tool"},
                )
                handle.write(json.dumps(record.to_json_dict(), sort_keys=True) + "\n")

        manifests.append(
            StreamManifest(
                stream_id=stream_id,
                path=str(stream_relpath),
                clock_domain=ClockDomain("event_time"),
                schema=schema,
                record_count=records_per_stream,
            )
        )

    manifest = DatasetManifest(
        dataset_name=dataset_name,
        version="v1",
        streams=tuple(manifests),
        metadata={"generator": "data_spec.mock_write_tool"},
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a deterministic standalone data_spec artifact.")
    parser.add_argument("output_dir", help="Output directory for the generated artifact")
    parser.add_argument("--dataset-name", default="mock_dataset", help="Dataset name to encode in the manifest")
    parser.add_argument("--stream-count", type=int, default=2, help="Number of streams to generate")
    parser.add_argument("--records-per-stream", type=int, default=5, help="Number of records per stream")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    path = write_mock_dataset(
        args.output_dir,
        dataset_name=args.dataset_name,
        stream_count=args.stream_count,
        records_per_stream=args.records_per_stream,
    )
    print(path)


if __name__ == "__main__":
    main()
