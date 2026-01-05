from __future__ import annotations

import collections
from retriever.flow.adapter import EventBuffer
from retriever.rt.buffer_engine import PythonBufferEngine

def test_event_buffer_is_list_and_stream():
    buf = EventBuffer([(1.0, "a"), (2.0, "b")])
    
    # Check List behavior
    assert isinstance(buf, list)
    assert len(buf) == 2
    assert buf[0] == (1.0, "a")
    
    # Check EventStream behavior
    assert hasattr(buf, "map")
    assert hasattr(buf, "filter")
    assert hasattr(buf, "events")
    
    # Check self-reference
    assert buf.events() is buf

def test_event_buffer_functional_methods():
    buf = EventBuffer([(1.0, 1), (2.0, 2), (3.0, 3)])
    
    # map
    mapped = buf.map(lambda x: x * 2)
    assert isinstance(mapped, EventStream) # map returns EventStream, not necessarily EventBuffer directly unless realized
    assert mapped.events() == [(1.0, 2), (2.0, 4), (3.0, 6)]
    
    # filter
    filtered = buf.filter(lambda x: x > 1)
    assert filtered.events() == [(2.0, 2), (3.0, 3)]
    
    # latest
    assert buf.latest() == 3

def test_buffer_engine_returns_event_buffer():
    eng = PythonBufferEngine(buffer_size=10)
    eng.push(1.0, "a")
    eng.push(2.0, "b")
    
    events = eng.events()
    assert isinstance(events, EventBuffer)
    assert events == [(1.0, "a"), (2.0, "b")]
    assert events.latest() == "b"

from retriever.flow.types import EventStream

def test_event_stream_import_compatibility():
    # Ensure EventStream is available from rt.frp where it used to be
    assert EventStream is not None
