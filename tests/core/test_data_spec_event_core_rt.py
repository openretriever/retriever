from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from retriever.data_spec import DataSpec, Event, EventBuffer, SchemaRef, StreamId, StreamSpec
from retriever.data_spec.v1 import EventBuffer as PinnedEventBuffer


def _evt(stream: str, event_ns: int, ingest_ns: int, seq: int, value: int) -> Event[int]:
    return Event(
        stream_id=StreamId(stream),
        event_time_ns=event_ns,
        ingest_time_ns=ingest_ns,
        seq=seq,
        value=value,
        type_name="int",
    )


def test_import_contract_event_buffer_surface() -> None:
    assert EventBuffer is PinnedEventBuffer


def test_deterministic_ordering_key_and_sort() -> None:
    e1 = _evt("cam", 200, 210, 1, 2)
    e2 = _evt("imu", 100, 120, 5, 1)
    e3 = _evt("cam", 200, 209, 0, 3)

    buf = EventBuffer((e1, e2, e3)).sorted()

    assert [event.value for event in buf] == [1, 3, 2]
    assert [event.ordering_key() for event in buf] == sorted(event.ordering_key() for event in buf)


def test_event_dataclass_is_immutable() -> None:
    event = _evt("cam", 1, 1, 0, 7)
    with pytest.raises(FrozenInstanceError):
        event.seq = 2


def test_data_spec_stream_map() -> None:
    spec = DataSpec(
        name="robot-episode",
        version="1.0",
        streams=(
            StreamSpec(stream_id=StreamId("cam"), schema=SchemaRef(name="RGBImage")),
            StreamSpec(stream_id=StreamId("joint"), schema=SchemaRef(name="JointState")),
        ),
    )

    mapping = spec.stream_map()
    assert set(mapping.keys()) == {"cam", "joint"}
    assert mapping["joint"].schema.name == "JointState"
