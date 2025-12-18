"""
Logging handlers.
"""

from retriever.rt.logging.handlers.console import create_console_handler
from retriever.rt.logging.handlers.file import create_file_handler
from retriever.rt.logging.handlers.otel import configure_otel, shutdown_otel

__all__ = [
    'create_console_handler',
    'create_file_handler',
    'configure_otel',
    'shutdown_otel',
]
