"""
Worker process logging setup.

Configures logging for a worker process:
- Console: QueueHandler → QueueListener in main process
- File: Direct FileHandler per node
- OTel: Direct uptrace export per process
"""

import sys
import logging
from logging.handlers import QueueHandler
from pathlib import Path
import multiprocessing as mp

from retriever.rt.logging.config import LogConfig, SERVICE_NAME
from retriever.rt.logging.handlers.file import create_file_handler
from retriever.rt.logging.handlers.otel import configure_otel

# Custom log levels for stdout/stderr capture
STDOUT = 25  # Between INFO (20) and WARNING (30)
STDERR = 45  # Between ERROR (40) and CRITICAL (50)

logging.addLevelName(STDOUT, 'STDOUT')
logging.addLevelName(STDERR, 'STDERR')


class StreamToLogger:
    """Redirect stdout/stderr to logger."""

    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level = level

    def write(self, msg: str) -> None:
        if msg.strip():
            self._logger.log(self._level, msg.rstrip())

    def flush(self) -> None:
        pass


def configure_worker(
    node_id: str,
    flow_name: str,
    queue: mp.Queue,
    config: LogConfig,
    log_dir: Path,
) -> None:
    """Configure logging for a worker process."""
    # Clear inherited handlers from parent process
    logging.getLogger('retriever').handlers.clear()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # Filter that adds flow_name to all log records
    class NodeFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.flow_name = flow_name
            return True

    node_filter = NodeFilter()

    # Console via queue
    if config.console_level is not None:
        queue_handler = QueueHandler(queue)
        queue_handler.setLevel(config.console_level)
        queue_handler.addFilter(node_filter)
        root.addHandler(queue_handler)

    # File direct
    if config.file_level is not None:
        log_path = log_dir / f'{node_id}.log'
        file_handler = create_file_handler(config.file_level, log_path)
        file_handler.addFilter(node_filter)
        root.addHandler(file_handler)

    # OTel direct
    if config.otel_enabled:
        configure_otel(SERVICE_NAME, attrs={'worker.id': node_id}, reset_providers=True)

    # Redirect stdout/stderr
    stdio_logger = logging.getLogger(f'stdio.{node_id}')
    sys.stdout = StreamToLogger(stdio_logger, STDOUT)
    sys.stderr = StreamToLogger(stdio_logger, STDERR)
