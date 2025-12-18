"""
Logging configuration.
"""

import logging
from dataclasses import dataclass
from typing import Optional

SERVICE_NAME = 'retriever'


@dataclass
class LogConfig:
    """
    Logging system configuration.

    Set level to None to disable that output.
    OTel export requires UPTRACE_DSN environment variable.
    """
    console_level: Optional[int] = logging.INFO
    file_level: Optional[int] = logging.DEBUG
    otel_enabled: bool = False
    log_dir: str = "./logs"

    def __repr__(self) -> str:
        def level_name(level: Optional[int]) -> str:
            return logging.getLevelName(level) if level is not None else 'OFF'
        return (
            f'LogConfig(console={level_name(self.console_level)}, '
            f'file={level_name(self.file_level)}, '
            f'otel={self.otel_enabled})'
        )
