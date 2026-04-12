from dataclasses import dataclass, field
from typing import Any, List, Optional, Union
from pathlib import Path


@dataclass
class RecordConfig:
    """
    Configuration for session recording.

    Attributes:
        path: Primary output path for the recording (e.g. "session.mcap")
        mirrors: Additional persisted artifacts to write from the same run.
        visualize: Whether to stream to Rerun live during recording (default False)
        format: Primary recording format ("mcap", "rrd", or "pickle"),
                auto-detected from the primary path if None.
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
            suffix = self.path.suffix.lower()
            if suffix == ".mcap":
                self.format = "mcap"
            elif suffix == ".rrd":
                self.format = "rrd"
            elif suffix == ".gz" and self.path.name.endswith(".pkl.gz"):
                self.format = "pickle"
            else:
                self.format = "mcap"  # Default to mcap

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
    name: Optional[str] = None,
    record: Optional[Union[RecordConfig, str]] = None,
    backend: Optional[str] = None,
    backend_config: Optional[dict] = None,
    default_sync: Optional[Any] = None,
    default_viz: Optional[VizConfig] = None,
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
    if name is not None:
        _global_config["name"] = name

    if backend is not None:
        _global_config["backend"] = backend

    if backend_config is not None:
        _global_config["backend_config"] = backend_config

    if default_sync is not None:
        _global_config["default_sync"] = default_sync

    if default_viz is not None:
        _global_config["default_viz"] = default_viz

    if record is not None:
        if isinstance(record, str):
            _global_config["record"] = RecordConfig(path=record)
        else:
            _global_config["record"] = record


def get_global_config():
    return _global_config
