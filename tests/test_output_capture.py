"""
Tests for output capture system.
"""

import pytest
import sys
import time
from unittest.mock import Mock, MagicMock
from retriever.rt.control.output_capture import (
    LogEntry,
    LogBuffer,
    FlowOutputCapture,
)
from retriever.rt.control.channel import ControlCommand


class TestLogEntry:
    """Test LogEntry dataclass."""

    def test_log_entry_creation(self):
        """Test creating a log entry."""
        entry = LogEntry(
            timestamp=time.time(),
            node_id="test_node",
            level="INFO",
            message="Test message"
        )

        assert entry.node_id == "test_node"
        assert entry.level == "INFO"
        assert entry.message == "Test message"

    def test_log_entry_to_dict(self):
        """Test converting log entry to dict."""
        timestamp = time.time()
        entry = LogEntry(
            timestamp=timestamp,
            node_id="test_node",
            level="ERROR",
            message="Error occurred"
        )

        data = entry.to_dict()
        assert data["node_id"] == "test_node"
        assert data["level"] == "ERROR"
        assert data["message"] == "Error occurred"
        assert data["timestamp"] == timestamp
        assert "time_str" in data


class TestLogBuffer:
    """Test LogBuffer ring buffer."""

    def test_log_buffer_creation(self):
        """Test creating a log buffer."""
        buffer = LogBuffer(maxlen=100)
        assert len(buffer.get_all()) == 0

    def test_add_log_entry(self):
        """Test adding log entries."""
        buffer = LogBuffer(maxlen=100)

        entry1 = LogEntry(time.time(), "node1", "INFO", "Message 1")
        entry2 = LogEntry(time.time(), "node2", "ERROR", "Message 2")

        buffer.add(entry1)
        buffer.add(entry2)

        all_logs = buffer.get_all()
        assert len(all_logs) == 2
        assert all_logs[0] == entry1
        assert all_logs[1] == entry2

    def test_log_buffer_maxlen(self):
        """Test that buffer respects maxlen."""
        buffer = LogBuffer(maxlen=3)

        for i in range(5):
            entry = LogEntry(time.time(), f"node{i}", "INFO", f"Message {i}")
            buffer.add(entry)

        all_logs = buffer.get_all()
        assert len(all_logs) == 3
        # Should have messages 2, 3, 4 (oldest removed)
        assert all_logs[0].message == "Message 2"
        assert all_logs[2].message == "Message 4"

    def test_get_recent(self):
        """Test getting recent N entries."""
        buffer = LogBuffer(maxlen=100)

        for i in range(10):
            buffer.add(LogEntry(time.time(), "node", "INFO", f"Msg {i}"))

        recent = buffer.get_recent(5)
        assert len(recent) == 5
        # Should get last 5 messages
        assert recent[0].message == "Msg 5"
        assert recent[4].message == "Msg 9"

    def test_filter_by_node_id(self):
        """Test filtering by node_id."""
        buffer = LogBuffer(maxlen=100)

        buffer.add(LogEntry(time.time(), "node1", "INFO", "A"))
        buffer.add(LogEntry(time.time(), "node2", "INFO", "B"))
        buffer.add(LogEntry(time.time(), "node1", "INFO", "C"))
        buffer.add(LogEntry(time.time(), "node3", "INFO", "D"))

        filtered = buffer.filter(node_id="node1")
        assert len(filtered) == 2
        assert all(e.node_id == "node1" for e in filtered)

    def test_filter_by_level(self):
        """Test filtering by log level."""
        buffer = LogBuffer(maxlen=100)

        buffer.add(LogEntry(time.time(), "node", "INFO", "A"))
        buffer.add(LogEntry(time.time(), "node", "ERROR", "B"))
        buffer.add(LogEntry(time.time(), "node", "INFO", "C"))
        buffer.add(LogEntry(time.time(), "node", "WARN", "D"))

        filtered = buffer.filter(level="ERROR")
        assert len(filtered) == 1
        assert filtered[0].message == "B"

    def test_filter_combined(self):
        """Test filtering by both node_id and level."""
        buffer = LogBuffer(maxlen=100)

        buffer.add(LogEntry(time.time(), "node1", "INFO", "A"))
        buffer.add(LogEntry(time.time(), "node1", "ERROR", "B"))
        buffer.add(LogEntry(time.time(), "node2", "ERROR", "C"))
        buffer.add(LogEntry(time.time(), "node1", "ERROR", "D"))

        filtered = buffer.filter(node_id="node1", level="ERROR")
        assert len(filtered) == 2
        assert all(e.node_id == "node1" and e.level == "ERROR" for e in filtered)

    def test_clear(self):
        """Test clearing the buffer."""
        buffer = LogBuffer(maxlen=100)

        for i in range(5):
            buffer.add(LogEntry(time.time(), "node", "INFO", f"Msg {i}"))

        assert len(buffer.get_all()) == 5

        buffer.clear()
        assert len(buffer.get_all()) == 0


class TestFlowOutputCapture:
    """Test FlowOutputCapture."""

    def test_output_capture_creation(self):
        """Test creating an output capture."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")

        assert capture.node_id == "test_node"
        assert capture.stream_type == "stdout"

    def test_write_to_stdout(self):
        """Test that write sends to both original stream and channel."""
        mock_channel = Mock()
        original_stdout = sys.stdout

        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()  # Mock to avoid actual output

        # Write a message
        capture.write("Test message")

        # Should call original stream
        capture.original_stream.write.assert_called_once_with("Test message")

        # Should send to channel
        assert mock_channel.send_command.called

    def test_empty_message_not_sent(self):
        """Test that empty/whitespace messages are not sent to channel."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        # Write empty/whitespace messages
        capture.write("")
        capture.write("   ")
        capture.write("\n")

        # Original stream should still be called
        assert capture.original_stream.write.call_count == 3

        # But channel should not be called (no non-empty messages)
        assert not mock_channel.send_command.called

    def test_level_detection_info(self):
        """Test INFO level detection."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        capture.write("This is a normal message")

        # Should detect INFO level for stdout
        call_args = mock_channel.send_command.call_args[0][0]
        assert call_args.payload["level"] == "INFO"

    def test_level_detection_error(self):
        """Test ERROR level detection."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        capture.write("ERROR: Something went wrong")

        call_args = mock_channel.send_command.call_args[0][0]
        assert call_args.payload["level"] == "ERROR"

    def test_level_detection_warn(self):
        """Test WARN level detection."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        capture.write("WARNING: Be careful")

        call_args = mock_channel.send_command.call_args[0][0]
        assert call_args.payload["level"] == "WARN"

    def test_stderr_defaults_to_error(self):
        """Test that stderr defaults to ERROR level."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stderr")
        capture.original_stream = MagicMock()

        capture.write("Some stderr output")

        call_args = mock_channel.send_command.call_args[0][0]
        assert call_args.payload["level"] == "ERROR"

    def test_flush(self):
        """Test flush method."""
        mock_channel = Mock()
        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        capture.flush()

        # Should call flush on original stream
        capture.original_stream.flush.assert_called_once()

    def test_channel_send_failure_does_not_break(self):
        """Test that channel send failures don't break flow execution."""
        mock_channel = Mock()
        mock_channel.send_command.side_effect = Exception("Channel error")

        capture = FlowOutputCapture("test_node", mock_channel, "stdout")
        capture.original_stream = MagicMock()

        # Should not raise even if channel fails
        capture.write("Test message")

        # Original stream should still work
        capture.original_stream.write.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
