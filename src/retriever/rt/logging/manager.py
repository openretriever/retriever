"""
LogManager - Central logging management for runtime.

Handles initialization, QueueListener, and shutdown.
"""

import logging
import multiprocessing as mp
from datetime import datetime
from logging.handlers import QueueListener
from pathlib import Path
from typing import Optional

from retriever.core.rt.logging.config import LogConfig, SERVICE_NAME
from retriever.core.rt.logging.handlers.console import create_console_handler
from retriever.core.rt.logging.handlers.file import create_file_handler
from retriever.core.rt.logging.handlers.otel import configure_otel, shutdown_otel


class LogManager:
    """Singleton manager for logging system."""

    _instance: Optional['LogManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'LogManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if LogManager._initialized:
            return
        self._config: Optional[LogConfig] = None
        self._queue: Optional[mp.Queue] = None
        self._listener: Optional[QueueListener] = None
        self._log_dir: Optional[Path] = None

    def init(self, config: LogConfig, pipeline_name: str) -> None:
        """
        Initialize logging system.

        Args:
            config: Logging configuration
            pipeline_name: Pipeline name for log directory
        """
        if LogManager._initialized:
            return

        self._config = config

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._log_dir = Path(config.log_dir) / f'{pipeline_name}_{timestamp}'
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Setup main process logging
        self._setup_main_process()

        # Start QueueListener for worker console output
        self._queue = mp.Queue()
        if self._config.console_level is not None:
            console_handler = create_console_handler(self._config.console_level)
            self._listener = QueueListener(self._queue, console_handler)
            self._listener.start()

        LogManager._initialized = True

        logger = logging.getLogger('retriever')
        logger.info(f'LogManager initialized: {self._config}, dir={self._log_dir}')

    def _setup_main_process(self) -> None:
        """Configure logging for main process."""
        # Clear any pre-existing handlers
        logging.getLogger().handlers.clear()
        logger = logging.getLogger('retriever')
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        # Console handler
        if self._config.console_level is not None:
            console = create_console_handler(self._config.console_level)
            logger.addHandler(console)

        # File handler for main process
        if self._config.file_level is not None:
            log_path = self._log_dir / 'retriever.log'
            file_handler = create_file_handler(self._config.file_level, log_path)
            logger.addHandler(file_handler)

        # OTel for main process
        if self._config.otel_enabled:
            configure_otel(SERVICE_NAME)

    def get_queue(self) -> mp.Queue:
        """Get queue for worker processes."""
        if self._queue is None:
            raise RuntimeError('LogManager not initialized')
        return self._queue

    def get_config(self) -> LogConfig:
        """Get logging configuration."""
        if self._config is None:
            raise RuntimeError('LogManager not initialized')
        return self._config

    def get_log_dir(self) -> Path:
        """Get log directory path."""
        if self._log_dir is None:
            raise RuntimeError('LogManager not initialized')
        return self._log_dir

    def shutdown(self) -> None:
        """Shutdown logging system."""
        if not LogManager._initialized:
            return

        logger = logging.getLogger('retriever')
        logger.info('Shutting down logging')

        # Stop QueueListener
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

        # Shutdown OTel
        if self._config.otel_enabled:
            shutdown_otel()

        # Close handlers on retriever logger
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        self._queue = None
        self._config = None
        self._log_dir = None
        LogManager._initialized = False
        LogManager._instance = None

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if logging is initialized."""
        return cls._initialized
