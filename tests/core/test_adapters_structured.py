import pytest
from retriever.flow.types import EventBuffer
from retriever.flow.adapter import Latest, Hold, Window, Events, Exact
from retriever.error import FlowError

@pytest.fixture
def simple_buffer():
    buf = EventBuffer()
    buf.append((1.0, "a"))
    buf.append((2.0, "b"))
    buf.append((3.0, "c"))
    return buf

class TestLatest:
    def test_simple_latest(self, simple_buffer):
        adapter = Latest(buffer_size=1)
        assert adapter(simple_buffer) == "c"

    def test_latest_preserves_type(self, simple_buffer):
        adapter = Latest(buffer_size=1)
        # Runtime check, although Python doesn't enforce strict types here
        assert isinstance(adapter(simple_buffer), str)

class TestWindow:
    def test_window_all(self, simple_buffer):
        # Window of 5s at time 4.0 covers [(-1.0), 4.0], so all events (1, 2, 3)
        # "mean" fails on strings, so let's use a numeric buffer for mean
        num_buf = EventBuffer([(1.0, 10), (2.0, 20), (3.0, 30)])
        
        # Test mean
        assert Window(buffer_size=10, duration=5.0, agg="mean")(num_buf, now=4.0) == 20.0
        
        # Test max
        assert Window(buffer_size=10, duration=5.0, agg="max")(num_buf, now=4.0) == 30
        
        # Test min
        assert Window(buffer_size=10, duration=5.0, agg="min")(num_buf, now=4.0) == 10
        
        # Test first (in window)
        assert Window(buffer_size=10, duration=5.0, agg="first")(num_buf, now=4.0) == 10
        
        # Test last (in window)
        assert Window(buffer_size=10, duration=5.0, agg="last")(num_buf, now=4.0) == 30

    def test_window_partial(self, simple_buffer):
        # Window of 0.5s at time 2.1 covers [1.6, 2.1]. Should capture "b" (2.0)
        adapter = Window(buffer_size=10, duration=0.5, agg="last")
        assert adapter(simple_buffer, now=2.1) == "b"

    def test_window_empty_fallback(self, simple_buffer):
        # Window of 0.1s at time 10.0 covers [9.9, 10.0]. Empty.
        # Should fall back to latest value "c"
        adapter = Window(buffer_size=10, duration=0.1, agg="last")
        assert adapter(simple_buffer, now=10.0) == "c"

class TestEvents:
    def test_events_slice(self, simple_buffer):
        adapter = Events(buffer_size=10, duration=1.5)
        # At 3.0, window is [1.5, 3.0]. Should have b(2.0), c(3.0)
        res = adapter(simple_buffer, now=3.0)
        assert len(res) == 2
        assert res[0] == (2.0, "b")
        assert res[1] == (3.0, "c")

    def test_events_no_timestamps(self, simple_buffer):
        adapter = Events(buffer_size=10, duration=1.5, include_timestamps=False)
        res = adapter(simple_buffer, now=3.0)
        assert res == ["b", "c"]

class TestHold:
    def test_hold_no_debounce(self, simple_buffer):
        adapter = Hold(buffer_size=1)
        assert adapter(simple_buffer) == "c"

    def test_hold_debounce(self):
        adapter = Hold(buffer_size=1, debounce=0.5)
        buf = EventBuffer([(1.0, "a")])
        
        # First call, sets state
        assert adapter(buf) == "a"
        
        # Update buffer with rapid event
        buf.append((1.2, "b")) # 0.2s elapsed < 0.5
        assert adapter(buf) == "a" # Should hold "a"
        
        # Update buffer with delayed event
        buf.append((2.0, "c")) # So "c" at 2.0. Delta vs 1.0 is 1.0 > 0.5. Should accept "c".
        assert adapter(buf) == "c"

class TestExact:
    def test_exact_match(self, simple_buffer):
        adapter = Exact(buffer_size=10)
        assert adapter(simple_buffer, now=2.0) == "b"

    def test_exact_tolerance(self, simple_buffer):
        adapter = Exact(buffer_size=10, tolerance=0.1)
        assert adapter(simple_buffer, now=2.05) == "b"

    def test_exact_miss(self, simple_buffer):
        adapter = Exact(buffer_size=10, tolerance=0.001)
        with pytest.raises(FlowError):
            adapter(simple_buffer, now=2.5)

