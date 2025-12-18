"""
Colored console handler with colored format.
"""

import logging
import sys

from retriever.core.rt.logging.worker import STDOUT, STDERR


class ColoredFormatter(logging.Formatter):
    """Formatter with ANSI colors."""

    # Colors
    BLUE = '\033[94m'
    GREY = '\033[90m'
    CYAN = '\033[36m'
    MINT = '\033[38;5;120m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    ORANGE = '\033[38;5;208m'
    RED = '\033[31m'
    BOLD_RED = '\033[1;31m'
    WHITE = '\033[37m'
    RESET = '\033[0m'

    LEVEL_COLORS = {
        logging.DEBUG: BLUE,
        logging.INFO: MINT,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
        STDOUT: WHITE,
        STDERR: ORANGE,
    }

    def __init__(self):
        super().__init__()
        self._use_color = sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        flow_name = getattr(record, 'flow_name', None)
        tag = flow_name if flow_name else 'retriever'

        # Format: YYYY-MM-DD HH:MM:SS.mmm | LEVEL | tag | file:line - message
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        msec = f'{int(record.msecs):03d}'
        level = f'{record.levelname:<8}'
        location = f'{record.filename}:{record.lineno}'

        if self._use_color:
            level_color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
            line = (
                f'{self.GREEN}{timestamp}.{msec}{self.RESET} | '
                f'{level_color}{level}{self.RESET} | '
                f'{self.CYAN}{tag:<16}{self.RESET} | '
                f'{self.GREY}{location:<16}{self.RESET} - '
                f'{record.getMessage()}'
            )
        else:
            line = (
                f'{timestamp}.{msec} | {level} | {tag:<16} | '
                f'{location:<16} - {record.getMessage()}'
            )

        if record.exc_info:
            line += '\n' + self.formatException(record.exc_info)

        return line


def create_console_handler(level: int) -> logging.Handler:
    """Create colored console handler."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(ColoredFormatter())
    return handler
