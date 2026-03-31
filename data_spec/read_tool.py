"""Standalone read tool for portable data_spec artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from .types import DatasetManifest, Record


def load_manifest(dataset_dir: str | Path) -> DatasetManifest:
    """Load ``manifest.json`` from a standalone dataset directory."""
    dataset_dir = Path(dataset_dir)
    manifest_path = dataset_dir / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return DatasetManifest.from_json_dict(data)


def iter_records(dataset_dir: str | Path, *, stream_id: Optional[str] = None) -> Iterable[Record]:
    """Iterate records across all streams, or one selected stream."""
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    for stream in manifest.streams:
        if stream_id is not None and str(stream.stream_id) != stream_id:
            continue
        stream_path = dataset_dir / stream.path
        with stream_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield Record.from_json_dict(json.loads(line))


def read_dataset(dataset_dir: str | Path) -> dict[str, list[Record]]:
    """Materialize the full dataset into memory grouped by stream id."""
    grouped: dict[str, list[Record]] = {}
    manifest = load_manifest(dataset_dir)
    for stream in manifest.streams:
        grouped[str(stream.stream_id)] = list(iter_records(dataset_dir, stream_id=str(stream.stream_id)))
    return grouped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect standalone data_spec artifacts.")
    parser.add_argument("dataset_dir", help="Path to the dataset directory containing manifest.json")
    parser.add_argument("--stream", dest="stream_id", help="Optional stream id to inspect")
    parser.add_argument("--limit", type=int, default=5, help="Maximum records to print per stream")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    manifest = load_manifest(args.dataset_dir)
    print(f"dataset={manifest.dataset_name} version={manifest.version} streams={len(manifest.streams)}")
    for stream in manifest.streams:
        if args.stream_id is not None and str(stream.stream_id) != args.stream_id:
            continue
        print(f"\n[{stream.stream_id}] path={stream.path} count={stream.record_count}")
        for idx, record in enumerate(iter_records(args.dataset_dir, stream_id=str(stream.stream_id))):
            if idx >= args.limit:
                print("  ...")
                break
            print(
                "  "
                f"ts={record.timestamp_ns} seq={record.seq} "
                f"schema={record.schema.name if record.schema else '(none)'} "
                f"payload={dict(record.payload)}"
            )


if __name__ == "__main__":
    main()
