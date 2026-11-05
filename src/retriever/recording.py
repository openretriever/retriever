"""Format-agnostic recording helpers for Retriever.

This module defines a small recording abstraction above `Pipeline.step()`
results and below concrete containers like MCAP and Rerun `.rrd`.

The intent is:
- keep `retriever.types.data` as the canonical typed/event model
- keep runtime `StepResult` / tuple-buffer semantics unchanged
- make persisted recording targets pluggable

MCAP stores typed outputs for readback and replay. Rerun `.rrd` files are
visualization artifacts only; record an explicit MCAP mirror when replay is needed.
"""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
try:
    from types import UnionType
except ImportError:  # pragma: no cover - Python < 3.10
    UnionType = None
from typing import Any, Literal, Optional, Protocol, Sequence, Type, Union, get_args, get_origin

import numpy as np

from retriever.types.schema import ClockDomain, SchemaRef, StreamId
from retriever.registry.types import resolve_schema_ref

RecordingFormat = Literal["mcap", "rrd"]


def detect_recording_format(path: str | Path) -> Optional[RecordingFormat]:
    suffix = Path(path).suffix.lower()
    if suffix == ".mcap":
        return "mcap"
    if suffix == ".rrd":
        return "rrd"
    return None


@dataclass(frozen=True)
class RecordingArtifactSpec:
    """Concrete recording artifact target."""

    path: Path
    format: RecordingFormat


@dataclass(frozen=True)
class RecordingStreamSpec:
    """Narrow schema hook for recorded runtime streams.

    This is intentionally lightweight for the first slice. We keep stable stream
    ids and schema refs here so a future `RecordingSession` can use the same
    primitives without reinterpreting container-specific metadata.
    """

    stream_id: StreamId
    node_id: str
    io_kind: Literal["input", "output"] = "output"
    clock_domain: ClockDomain = ClockDomain("retriever_time")
    schema: SchemaRef = SchemaRef(name="Unknown", version="v1", encoding="python")


def schema_ref_for_value(value: Any) -> SchemaRef:
    """Infer a stable schema identity hook for a runtime value."""
    registered = resolve_schema_ref(value)
    if registered is not None:
        return registered
    type_name = getattr(type(value), "__name__", "Unknown") or "Unknown"
    return SchemaRef(name=type_name, version="v1", encoding="python")


def infer_output_stream_specs(step_result: Any) -> tuple[RecordingStreamSpec, ...]:
    """Derive stable output stream descriptors from a step result."""
    outputs = getattr(step_result, "outputs", None) or {}
    specs: list[RecordingStreamSpec] = []
    for node_id, value in outputs.items():
        if value is None:
            continue
        specs.append(
            RecordingStreamSpec(
                stream_id=StreamId(f"{node_id}/output"),
                node_id=node_id,
                io_kind="output",
                clock_domain=ClockDomain("retriever_time"),
                schema=schema_ref_for_value(value),
            )
        )
    return tuple(specs)


class RecordingSink(Protocol):
    """Protocol for persisted recording targets."""

    def open(self) -> None:
        ...

    def write_step(self, result: Any, step_idx: int) -> None:
        ...

    def close(self) -> None:
        ...


class RecordingReader(Protocol):
    """Protocol for persisted recording readers."""

    def list_node_ids(self) -> list[str]:
        ...

    def read_node_stream(
        self,
        node_id: str,
        *,
        output_type: Optional[Type[Any]] = None,
    ) -> list[tuple[float, Any]]:
        ...

    def get_stream_spec(self, node_id: str) -> Optional["RecordingStreamSpec"]:
        ...


class CompositeRecordingSink:
    """Fan out one step stream into multiple persisted recording targets."""

    def __init__(self, sinks: Sequence[RecordingSink]):
        self._sinks = list(sinks)
        self._opened = False

    def open(self) -> None:
        if self._opened:
            return
        for sink in self._sinks:
            sink.open()
        self._opened = True

    def write_step(self, result: Any, step_idx: int) -> None:
        for sink in self._sinks:
            sink.write_step(result, step_idx)

    def close(self) -> None:
        first_error: Optional[BaseException] = None
        for sink in reversed(self._sinks):
            try:
                sink.close()
            except BaseException as exc:  # noqa: BLE001 - close every sink first
                if first_error is None:
                    first_error = exc
        self._opened = False
        if first_error is not None:
            raise first_error


class McapRecordingSink:
    """Persist step results to MCAP."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._writer = None
        self._written_specs: set[str] = set()

    def open(self) -> None:
        from retriever.lib.mcap import MCAPWriter

        if self._writer is not None:
            return
        self._writer = MCAPWriter(self.path)
        self._writer.__enter__()

    def write_step(self, result: Any, step_idx: int) -> None:
        if self._writer is None:
            raise RuntimeError("MCAP recording sink is not open")
        timestamp_ns = int(float(getattr(result, "now", 0.0) or 0.0) * 1e9)
        for spec in infer_output_stream_specs(result):
            if spec.node_id in self._written_specs:
                continue
            self._writer.write_stream_spec(spec, timestamp_ns=timestamp_ns)
            self._written_specs.add(spec.node_id)
        self._writer.write_step(result, step_idx)

    def close(self) -> None:
        if self._writer is None:
            return
        try:
            self._writer.__exit__(None, None, None)
        finally:
            self._writer = None
            self._written_specs.clear()


class RrdRecordingSink:
    """Persist step results to a Rerun `.rrd` recording."""

    def __init__(
        self,
        path: str | Path,
        *,
        app_id: str,
        auto_open: bool = False,
    ):
        self.path = Path(path)
        self.app_id = app_id
        self.auto_open = auto_open
        self._manager = None

    def open(self) -> None:
        from retriever.lib.rerun import RerunConfig, RerunManager

        if self._manager is not None:
            return
        cfg = RerunConfig(
            mode="record",
            recording_path=str(self.path),
            app_id=self.app_id,
            auto_open_on_exit=self.auto_open,
        )
        self._manager = RerunManager(cfg, app_id=self.app_id)
        self._manager.init()

    def write_step(self, result: Any, step_idx: int) -> None:
        if self._manager is None:
            raise RuntimeError("RRD recording sink is not open")
        self._manager.log_step_result(result, step_idx)

    def close(self) -> None:
        if self._manager is None:
            return
        self._manager.cleanup()
        self._manager = None


class McapRecordingReader:
    """Read node streams from MCAP recordings."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def list_node_ids(self) -> list[str]:
        from retriever.lib.mcap import MCAPReader

        node_ids: set[str] = set()
        with MCAPReader(self.path) as reader:
            for _schema, channel, _message in reader._reader.iter_messages():
                topic = channel.topic
                if topic.startswith("/retriever/flows/") and topic.endswith("/output"):
                    node_ids.add(topic.split("/")[3])
        return sorted(node_ids)

    def read_node_stream(
        self,
        node_id: str,
        *,
        output_type: Optional[Type[Any]] = None,
    ) -> list[tuple[float, Any]]:
        from retriever.lib.mcap import MCAPReader
        recorded_node_id = _resolve_recorded_node_id(node_id, self.list_node_ids())

        with MCAPReader(self.path) as reader:
            buffer = reader.read_node_stream(recorded_node_id)
        if output_type is None:
            return buffer
        return [(ts, _hydrate_recorded_value(value, output_type)) for ts, value in buffer]

    def get_stream_spec(self, node_id: str) -> Optional[RecordingStreamSpec]:
        from retriever.lib.mcap import MCAPReader

        recorded_node_id = _resolve_recorded_node_id(node_id, self.list_node_ids())
        topic = f"/retriever/streams/{recorded_node_id}/spec"
        with MCAPReader(self.path) as reader:
            for _schema, _channel, message in reader._reader.iter_messages(topics=[topic]):
                return _stream_spec_from_json(json.loads(message.data.decode("utf-8")))
        return None


def build_recording_artifacts(record_config: Any) -> tuple[RecordingArtifactSpec, ...]:
    """Resolve persisted artifacts from a RecordConfig-like object."""
    seen: set[Path] = set()
    artifacts: list[RecordingArtifactSpec] = []
    for path in record_config.artifact_paths():
        resolved = Path(path)
        if resolved in seen:
            continue
        fmt = detect_recording_format(resolved)
        if fmt is None:
            raise ValueError(
                f"Unsupported recording artifact path: {resolved}. "
                "Supported persisted formats are .mcap and .rrd."
            )
        artifacts.append(RecordingArtifactSpec(path=resolved, format=fmt))
        seen.add(resolved)
    return tuple(artifacts)


def build_recording_sink(record_config: Any, *, app_id: str) -> CompositeRecordingSink:
    """Create persisted recording sinks from a RecordConfig-like object."""
    sinks: list[RecordingSink] = []
    for artifact in build_recording_artifacts(record_config):
        if artifact.format == "mcap":
            sinks.append(McapRecordingSink(artifact.path))
        elif artifact.format == "rrd":
            sinks.append(
                RrdRecordingSink(
                    artifact.path,
                    app_id=app_id,
                    auto_open=bool(getattr(record_config, "auto_open", False)),
                )
            )
    return CompositeRecordingSink(sinks)


def open_recording_reader(path: str | Path) -> RecordingReader:
    """Open an MCAP reader without importing the visualization SDK."""
    path = Path(path)
    fmt = detect_recording_format(path)
    if fmt == "mcap":
        return McapRecordingReader(path)
    if fmt == "rrd":
        raise ValueError("RRD is visualization-only. Replay the explicitly recorded MCAP (.mcap) artifact instead.")
    raise ValueError(
        f"Unsupported recording path: {path}. Supported replay format is .mcap."
    )


def read_node_stream_from_recording(
    path: str | Path,
    node_id: str,
    *,
    output_type: Optional[Type[Any]] = None,
) -> list[tuple[float, Any]]:
    """Read one node's replay stream from any supported recording artifact."""
    return open_recording_reader(path).read_node_stream(node_id, output_type=output_type)


def view_recording(path: str | Path) -> None:
    """Open a persisted recording artifact."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Recording not found: {path}")
    fmt = detect_recording_format(path)
    if fmt == "mcap":
        from retriever.lib.mcap import view_in_rerun

        view_in_rerun(path)
        return
    if fmt == "rrd":
        import shutil
        import subprocess

        if shutil.which("rerun") is None:
            print(f"[Rerun] Recording saved to: {path}")
            print("[Rerun] Install rerun CLI to open `.rrd`: pip install rerun-sdk[cli]")
            return
        # Detach the viewer so it outlives us and never becomes our zombie child.
        subprocess.Popen(["rerun", str(path)], start_new_session=True)
        return
    raise ValueError(
        f"Unsupported recording path: {path}. Supported view formats are .mcap and .rrd."
    )


def _stream_spec_to_json(spec: RecordingStreamSpec) -> dict[str, Any]:
    return {
        "stream_id": str(spec.stream_id),
        "node_id": spec.node_id,
        "io_kind": spec.io_kind,
        "clock_domain": spec.clock_domain.name,
        "schema": {
            "name": spec.schema.name,
            "version": spec.schema.version,
            "encoding": spec.schema.encoding,
        },
    }


def _stream_spec_from_json(data: dict[str, Any]) -> RecordingStreamSpec:
    schema_data = data.get("schema") or {}
    return RecordingStreamSpec(
        stream_id=StreamId(str(data["stream_id"])),
        node_id=str(data["node_id"]),
        io_kind=str(data.get("io_kind", "output")),
        clock_domain=ClockDomain(str(data.get("clock_domain", "retriever_time"))),
        schema=SchemaRef(
            name=str(schema_data.get("name", "Unknown")),
            version=str(schema_data.get("version", "v1")),
            encoding=str(schema_data.get("encoding", "python")),
        ),
    )


def _unwrap_optional_type(expected_type: Any) -> Any:
    origin = get_origin(expected_type)
    if origin is None:
        return expected_type
    if origin is Union or (UnionType is not None and origin is UnionType):
        args = [arg for arg in get_args(expected_type) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return expected_type


def _restore_recorded_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__numpy__"):
            if "npy_b64" in value:
                buf = io.BytesIO(base64.b64decode(value["npy_b64"]))
                return np.load(buf, allow_pickle=False)
            return np.array(value["data"], dtype=value.get("dtype"))
        if "__bytes__" in value:
            return base64.b64decode(value["__bytes__"])
        return {k: _restore_recorded_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_restore_recorded_value(v) for v in value]
    return value


def _hydrate_recorded_value(value: Any, output_type: Optional[Type[Any]]) -> Any:
    if output_type is None:
        return _restore_recorded_value(value)

    expected = _unwrap_optional_type(output_type)
    if expected in (Any, object, None):
        return _restore_recorded_value(value)

    try:
        if isinstance(value, expected):
            return value
    except TypeError:
        pass

    origin = get_origin(expected)
    if origin in (list, Sequence):
        elem_type = get_args(expected)[0] if get_args(expected) else None
        return [_hydrate_recorded_value(item, elem_type) for item in (value or [])]
    if origin is tuple:
        elem_types = get_args(expected)
        return tuple(
            _hydrate_recorded_value(item, elem_types[idx] if idx < len(elem_types) else None)
            for idx, item in enumerate(value or [])
        )
    if origin is dict:
        args = get_args(expected)
        value_type = args[1] if len(args) > 1 else None
        return {k: _hydrate_recorded_value(v, value_type) for k, v in (value or {}).items()}

    if expected is np.ndarray:
        restored = _restore_recorded_value(value)
        if isinstance(restored, np.ndarray):
            return restored
        return np.array(restored)

    if is_dataclass(expected) and isinstance(value, dict):
        kwargs = {}
        for field in fields(expected):
            if field.name in value:
                kwargs[field.name] = _hydrate_recorded_value(value[field.name], field.type)
        return expected(**kwargs)

    restored = _restore_recorded_value(value)
    try:
        if expected in (int, float, str, bool, bytes):
            return expected(restored)
    except Exception:
        pass
    return restored


def _resolve_recorded_node_id(requested_node_id: str, available_node_ids: Sequence[str]) -> str:
    if requested_node_id in available_node_ids:
        return requested_node_id

    requested_prefix = requested_node_id.split("_", 1)[0]
    prefix_matches = [node_id for node_id in available_node_ids if node_id.split("_", 1)[0] == requested_prefix]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if not prefix_matches:
        raise RuntimeError(
            f"Recording does not contain node `{requested_node_id}`. "
            f"Available recorded nodes: {list(available_node_ids)}"
        )
    raise RuntimeError(
        f"Recording node resolution for `{requested_node_id}` is ambiguous. "
        f"Matching recorded nodes: {prefix_matches}"
    )


__all__ = [
    "CompositeRecordingSink",
    "McapRecordingReader",
    "RecordingArtifactSpec",
    "RecordingFormat",
    "RecordingReader",
    "RecordingSink",
    "RecordingStreamSpec",
    "build_recording_artifacts",
    "build_recording_sink",
    "detect_recording_format",
    "infer_output_stream_specs",
    "open_recording_reader",
    "read_node_stream_from_recording",
    "schema_ref_for_value",
    "view_recording",
]
