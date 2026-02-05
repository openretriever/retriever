"""
Output capture system for streaming flow stdout/stderr to web UI.

Provides FlowOutputCapture for wrapping stdout/stderr in executor processes,
and LogBuffer for storing and managing log entries in the web dashboard.
"""

import sys
import time
from dataclasses import dataclass
from collections import deque
from typing import Optional, Literal, List
from datetime import datetime


@dataclass
class LogEntry:
    """A single log entry from a flow's stdout/stderr."""

    timestamp: float
    node_id: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    message: str

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "level": self.level,
            "message": self.message,
            "time_str": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S.%f")[:-3]
        }


class FlowOutputCapture:
    """
    Capture stdout/stderr from flow execution and send to control channel.

    Wraps sys.stdout or sys.stderr to intercept print statements and
    forward them to the web dashboard via the control channel.
    """

    def __init__(self, node_id: str, control_channel, stream_type: str = "stdout"):
        """
        Initialize output capture.

        Args:
            node_id: Flow node identifier
            control_channel: ControlChannel to send log messages
            stream_type: "stdout" or "stderr"
        """
        self.node_id = node_id
        self.channel = control_channel
        self.stream_type = stream_type
        self.original_stream = sys.stdout if stream_type == "stdout" else sys.stderr

    def write(self, message: str):
        """
        Write method called by print() and logging.

        Sends output to both original stream (CLI) and control channel (web UI).
        """
        # Always write to original stream (preserve CLI output)
        self.original_stream.write(message)

        # Send to control channel for web UI (skip empty messages)
        if message.strip():
            # Detect level from message content
            level = self._detect_level(message)

            from retriever.rt.control.channel import ControlCommand, ControlMessage

            log_msg = ControlMessage(
                command=ControlCommand.LOG_OUTPUT,
                target=self.node_id,
                payload={
                    "level": level,
                    "message": message.strip(),
                    "timestamp": time.time()
                },
                timestamp=time.time(),
                request_id=""
            )

            try:
                self.channel.send_command(log_msg)
            except Exception:
                # Don't break flow execution if logging fails
                pass

    def _detect_level(self, message: str) -> str:
        """Detect log level from message content."""
        msg_upper = message.upper()

        if "ERROR" in msg_upper or "EXCEPTION" in msg_upper:
            return "ERROR"
        elif "WARN" in msg_upper or "WARNING" in msg_upper:
            return "WARN"
        elif "DEBUG" in msg_upper:
            return "DEBUG"
        else:
            # Default to ERROR for stderr, INFO for stdout
            return "ERROR" if self.stream_type == "stderr" else "INFO"

    def flush(self):
        """Flush the original stream."""
        self.original_stream.flush()


class LogBuffer:
    """
    Ring buffer for storing recent log entries.

    Used by web dashboard to maintain history and support
    filtering, searching, and export.
    """

    def __init__(self, maxlen: int = 10000):
        """
        Initialize log buffer.

        Args:
            maxlen: Maximum number of log entries to retain
        """
        self.buffer: deque[LogEntry] = deque(maxlen=maxlen)

    def add(self, entry: LogEntry) -> None:
        """Add a log entry to the buffer."""
        self.buffer.append(entry)

    def get_recent(self, count: int = 100) -> List[LogEntry]:
        """
        Get the most recent N log entries.

        Args:
            count: Number of recent entries to return

        Returns:
            List of LogEntry objects (most recent last)
        """
        return list(self.buffer)[-count:]

    def get_all(self) -> List[LogEntry]:
        """Get all log entries in buffer."""
        return list(self.buffer)

    def filter(
        self,
        node_id: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 1000
    ) -> List[LogEntry]:
        """
        Filter log entries by node_id and/or level.

        Args:
            node_id: Filter by flow node ID (None = all)
            level: Filter by log level (None = all)
            limit: Maximum entries to return

        Returns:
            Filtered list of LogEntry objects
        """
        filtered = self.buffer

        if node_id:
            filtered = [e for e in filtered if e.node_id == node_id]

        if level:
            filtered = [e for e in filtered if e.level == level]

        # Return most recent N entries
        return list(filtered)[-limit:]

    def clear(self) -> None:
        """Clear all log entries."""
        self.buffer.clear()
