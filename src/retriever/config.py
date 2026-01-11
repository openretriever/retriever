from dataclasses import dataclass
from typing import Any, Optional, Union
from pathlib import Path

@dataclass
class RecordConfig:
    """
    Configuration for session recording.
    
    Attributes:
        path: Output path for the recording (e.g. "session.mcap")
        visualize: Whether to stream to Rerun live during recording (default False)
        format: Recording format ("mcap" or "pickle", auto-detected from path if None)
    """
    path: Union[str, Path]
    visualize: bool = False
    format: Optional[str] = None
    
    def __post_init__(self):
        self.path = Path(self.path)
        if self.format is None:
            if self.path.suffix.lower() == ".mcap":
                self.format = "mcap"
            else:
                self.format = "mcap" # Default to mcap

_global_config = {
    "record": None,       # Optional[RecordConfig]
    "backend": "multiprocessing",  # Default backend
    "backend_config": {},  # Default backend config (merged with run() overrides)
    "name": None,         # Session name
    "default_sync": None, # Default sync adapter (e.g., Latest()). If None, sync is required.
}

def set_global_config(
    name: Optional[str] = None,
    record: Optional[Union[RecordConfig, str]] = None,
    backend: Optional[str] = None,
    backend_config: Optional[dict] = None,
    default_sync: Optional[Any] = None,
):
    """Configure global Retriever settings.

    Args:
        name: Session name for logging.
        record: Recording config (RecordConfig or path string).
        backend: Default execution backend ("multiprocessing", "dora", etc.).
        backend_config: Default backend configuration dict. Values are merged
                        with (and overridden by) `pipe.run(backend_config=...)`.
        default_sync: Default sync adapter for connections. If None, every
                      connection must explicitly specify `sync=`.
    """
    if name is not None:
        _global_config["name"] = name

    if backend is not None:
        _global_config["backend"] = backend

    if backend_config is not None:
        _global_config["backend_config"] = backend_config

    if default_sync is not None:
        _global_config["default_sync"] = default_sync

    if record is not None:
        if isinstance(record, str):
            _global_config["record"] = RecordConfig(path=record)
        else:
            _global_config["record"] = record

def get_global_config():
    return _global_config
