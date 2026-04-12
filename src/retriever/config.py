from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union


_UNSET = object()
_SESSION_RECORDING_FORMATS = {"mcap", "rrd"}


def _detect_session_recording_format(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    if suffix == ".mcap":
        return "mcap"
    if suffix == ".rrd":
        return "rrd"
    return None


def _validate_session_recording_path(path: Path) -> str:
    fmt = _detect_session_recording_format(path)
    if fmt is None:
        raise ValueError(
            f"Unsupported persisted recording path: {path}. "
            "Use a .mcap or .rrd path for RecordConfig/session recording."
        )
    return fmt


@dataclass
class RecordConfig:
    """
    Configuration for session recording.

    Attributes:
        path: Primary output path for the recording (e.g. "session.mcap")
        mirrors: Additional persisted artifacts to write from the same run.
        visualize: Whether to stream to Rerun live during recording (default False)
        format: Primary persisted recording format ("mcap" or "rrd").
                Auto-detected from the primary path if None.
        auto_open: Whether a `.rrd` recording should auto-open in Rerun on cleanup.
    """
    path: Union[str, Path]
    mirrors: tuple[Union[str, Path], ...] = field(default_factory=tuple)
    visualize: bool = False
    format: Optional[str] = None
    auto_open: bool = False

    def __post_init__(self):
        self.path = Path(self.path)
        self.mirrors = tuple(Path(p) for p in self.mirrors)
        if self.format is None:
            self.format = _validate_session_recording_path(self.path)
        else:
            self.format = str(self.format).lower()
            if self.format not in _SESSION_RECORDING_FORMATS:
                raise ValueError(
                    f"Unsupported RecordConfig.format={self.format!r}. "
                    "Use 'mcap' or 'rrd' for persisted session recording."
                )
        for mirror in self.mirrors:
            _validate_session_recording_path(mirror)

    def artifact_paths(self) -> tuple[Path, ...]:
        return (self.path, *self.mirrors)


@dataclass
class VizConfig:
    """
    Visualization policy for a flow's output port in Rerun.

    Declared at connection time via `.then(viz=VizConfig(...))`, or set as the
    global fallback via `retriever.init(default_viz=VizConfig(...))`.

    Attributes:
        hz: Maximum log rate in Hz. Outputs are sub-sampled if the flow runs
            faster than this. Default 5 Hz — reasonable for images/tensors.
        fields: Which output fields to log. None means all fields.
        path: Override the Rerun entity path for this node's output.
              Defaults to "flows/{node_id}/output".
    """
    hz: float = 5.0
    fields: Optional[List[str]] = None
    path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.hz <= 0:
            raise ValueError(f"VizConfig.hz must be positive, got {self.hz}")


_global_config = {
    "record": None,        # Optional[RecordConfig]
    "backend": "multiprocessing",
    "backend_config": {},
    "name": None,
    "default_sync": None,  # Default sync adapter. If None, sync must be explicit.
    "default_viz": None,   # Optional[VizConfig]. Fallback for nodes without viz= on .then().
}


def set_global_config(
    name: Optional[str] | object = _UNSET,
    record: Optional[Union[RecordConfig, str, Path]] | object = _UNSET,
    backend: Optional[str] | object = _UNSET,
    backend_config: Optional[dict] | object = _UNSET,
    default_sync: Optional[Any] | object = _UNSET,
    default_viz: Optional[VizConfig] | object = _UNSET,
) -> None:
    """Configure global Retriever settings.

    Args:
        name: Session name for logging.
        record: Recording config (RecordConfig or path string).
        backend: Default execution backend ("multiprocessing", "dora", etc.).
        backend_config: Default backend configuration dict. Values are merged
                        with (and overridden by) `pipe.run(backend_config=...)`.
        default_sync: Default sync adapter for connections. If None, every
                      connection must explicitly specify `sync=`.
        default_viz: Default visualization policy for all output ports that do
                     not have an explicit `viz=` on their `.then()` connection.
                     Pass `VizConfig(hz=5.0)` to enable lightweight visualization
                     across the whole pipeline without annotating each node.
    """
    if name is not _UNSET:
        _global_config["name"] = name

    if backend is not _UNSET:
        _global_config["backend"] = "multiprocessing" if backend is None else backend

    if backend_config is not _UNSET:
        _global_config["backend_config"] = {} if backend_config is None else backend_config

    if default_sync is not _UNSET:
        _global_config["default_sync"] = default_sync

    if default_viz is not _UNSET:
        _global_config["default_viz"] = default_viz

    if record is not _UNSET:
        if record is None:
            _global_config["record"] = None
        elif isinstance(record, (str, Path)):
            _global_config["record"] = RecordConfig(path=record)
        else:
            _global_config["record"] = record


def get_global_config():
    return _global_config
