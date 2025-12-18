"""
Rotating file handler for per-node logging.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class FileFormatter(logging.Formatter):
    """Loguru-like formatter for file output."""

    def format(self, record: logging.LogRecord) -> str:
        flow_name = getattr(record, 'flow_name', None)
        tag = flow_name if flow_name else 'retriever'

        # Format: YYYY-MM-DD HH:MM:SS.mmm | LEVEL | tag | file:line - message
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        msec = f'{int(record.msecs):03d}'
        level = f'{record.levelname:<8}'
        location = f'{record.filename}:{record.lineno}'

        line = (
            f'{timestamp}.{msec} | {level} | {tag:<16} | '
            f'{location:<16} - {record.getMessage()}'
        )

        if record.exc_info:
            line += '\n' + self.formatException(record.exc_info)

        return line


def create_file_handler(level: int, log_path: Path) -> logging.Handler:
    """
    Create rotating file handler for a node.

    Each node gets its own log file, written directly (no queue).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(FileFormatter())
    return handler
