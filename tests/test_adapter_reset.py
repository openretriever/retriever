"""
Tests for adapter reset functionality.
"""

import pytest
from retriever.flow.adapter import Latest, Hold, Events, Window
from retriever.flow.types import EventBuffer


class TestAdapterReset:
    """Test reset() method for all adapters."""

    def test_latest_reset(self):
        """Latest adapter should have reset (even if it does nothing)."""
        adapter = Latest()
        # Latest doesn't maintain state, but should have reset method
        adapter.reset()
        # No error means success

    def test_hold_reset(self):
        """Hold adapter should clear its last value and timestamp."""
        adapter = Hold(debounce=0.5)

        # Simulate some state
        buffer = EventBuffer([(1.0, "value1"), (2.0, "value2")])
        result = adapter(buffer)
        assert result == "value2"
        assert adapter._last_value == "value2"
        assert adapter._last_time == 2.0

        # Reset should clear state
        adapter.reset()
        assert adapter._last_value is None
        assert adapter._last_time == 0.0

    def test_hold_reset_debounce_behavior(self):
        """After reset, debounce logic should start fresh."""
        adapter = Hold(debounce=1.0)

        # First event
        buffer1 = EventBuffer([(1.0, "first")])
        result1 = adapter(buffer1)
        assert result1 == "first"

        # Second event within debounce window (should be ignored normally)
        buffer2 = EventBuffer([(1.5, "second")])
        result2 = adapter(buffer2)
        assert result2 == "first"  # Held due to debounce

        # Reset
        adapter.reset()

        # After reset, new event should not be debounced
        buffer3 = EventBuffer([(1.6, "third")])
        result3 = adapter(buffer3)
        assert result3 == "third"  # Not debounced because state was reset

    def test_events_reset(self):
        """Events adapter should have reset (even if it does nothing)."""
        adapter = Events(buffer_size=10)
        adapter.reset()
        # No error means success

    def test_window_reset(self):
        """Window adapter should have reset (even if it does nothing)."""
        adapter = Window(buffer_size=10, duration=1.0)
        adapter.reset()
        # No error means success

    def test_all_adapters_have_reset(self):
        """Ensure all adapter types have reset() method."""
        from retriever.flow.adapter import Exact, Linear, Chunking

        adapters = [
            Latest(),
            Hold(),
            Events(buffer_size=10),
            Window(buffer_size=10, duration=1.0),
            Exact(),
            Linear(),
            Chunking(),
        ]

        for adapter in adapters:
            assert hasattr(adapter, 'reset'), f"{type(adapter).__name__} missing reset()"
            # Should not raise
            adapter.reset()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
