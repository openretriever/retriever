"""Format-agnostic recording helpers for Retriever.

This module defines a small recording abstraction above `Pipeline.step()`
results and below concrete containers like MCAP and Rerun `.rrd`.

The intent is:
- keep `retriever.data_spec` as the canonical typed/event model
- keep runtime `StepResult` / tuple-buffer semantics unchanged
- make persisted recording targets pluggable

Today, `.mcap` remains the replay/interchange format, while `.rrd` is a
first-class persisted viewing artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Protocol, Sequence

from retriever.data_spec import ClockDomain, SchemaRef, StreamId

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
        for sink in reversed(self._sinks):
            sink.close()
        self._opened = False


class McapRecordingSink:
    """Persist step results to MCAP."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._writer = None

    def open(self) -> None:
        from retriever.lib.mcap import MCAPWriter

        if self._writer is not None:
            return
        self._writer = MCAPWriter(self.path)
        self._writer.__enter__()

    def write_step(self, result: Any, step_idx: int) -> None:
        if self._writer is None:
            raise RuntimeError("MCAP recording sink is not open")
        self._writer.write_step(result, step_idx)

    def close(self) -> None:
        if self._writer is None:
            return
        self._writer.__exit__(None, None, None)
        self._writer = None


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
        subprocess.Popen(["rerun", str(path)])
        return
    raise ValueError(
        f"Unsupported recording path: {path}. Supported view formats are .mcap and .rrd."
    )


__all__ = [
    "CompositeRecordingSink",
    "RecordingArtifactSpec",
    "RecordingFormat",
    "RecordingSink",
    "RecordingStreamSpec",
    "build_recording_artifacts",
    "build_recording_sink",
    "detect_recording_format",
    "infer_output_stream_specs",
    "schema_ref_for_value",
    "view_recording",
]
