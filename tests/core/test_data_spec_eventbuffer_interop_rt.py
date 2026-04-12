from __future__ import annotations

from retriever.types.data.interop import (
    from_runtime_event_buffer,
    is_runtime_event_buffer,
    to_runtime_event_buffer,
)
from retriever.flow.types import EventBuffer as RuntimeEventBuffer


def test_runtime_buffer_roundtrip() -> None:
    runtime = [(1.0, "a"), (2.5, "b")]
    typed = from_runtime_event_buffer(runtime, stream_id="cam")

    assert len(typed) == 2
    assert typed[0].event_time_ns == 1_000_000_000
    assert typed[1].value == "b"

    back = to_runtime_event_buffer(typed)
    assert back == runtime


def test_runtime_buffer_shape_detection() -> None:
    assert is_runtime_event_buffer([(1.0, 1), (2.0, 2)])
    assert is_runtime_event_buffer([])
    assert not is_runtime_event_buffer({"ts": 1.0})


def test_interop_with_runtime_eventbuffer_class() -> None:
    runtime_buffer = RuntimeEventBuffer([(3.0, 33), (4.0, 44)])

    typed = from_runtime_event_buffer(runtime_buffer, stream_id="imu")
    back = to_runtime_event_buffer(typed)

    assert back == [(3.0, 33), (4.0, 44)]
