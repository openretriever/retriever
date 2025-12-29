from dataclasses import dataclass, field
from typing import Optional, List, Union
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

# Global configuration state
_global_config = {
    "record": None,  # Optional[RecordConfig]
    "backend": "multiprocessing", # Default backend
    "name": None,    # Session name
}

def set_global_config(
    name: Optional[str] = None,
    record: Optional[Union[RecordConfig, str]] = None,
    backend: Optional[str] = None,
):
    if name is not None:
        _global_config["name"] = name
        
    if backend is not None:
        _global_config["backend"] = backend

    if record is not None:
        if isinstance(record, str):
            _global_config["record"] = RecordConfig(path=record)
        else:
            _global_config["record"] = record

def get_global_config():
    return _global_config
