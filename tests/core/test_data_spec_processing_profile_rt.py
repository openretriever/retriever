from __future__ import annotations

import pytest

from retriever.types.data import Event, EventBuffer, StreamId, WindowPolicy
from retriever.types.data.streams import hold, latest, window_agg


def _evt(t: int, seq: int, value: float) -> Event[float]:
    return Event(
        stream_id=StreamId("sensor"),
        event_time_ns=t,
        ingest_time_ns=t,
        seq=seq,
        value=value,
        type_name="float",
    )


def test_latest_returns_most_recent_value() -> None:
    buffer = EventBuffer((_evt(100, 0, 1.0), _evt(200, 1, 2.0), _evt(150, 2, 1.5)))
    assert latest(buffer) == 2.0


def test_hold_samples_last_value_before_now() -> None:
    buffer = EventBuffer((_evt(100, 0, 1.0), _evt(200, 1, 2.0), _evt(400, 2, 4.0)))

    assert hold(buffer, now_ns=250) == 2.0
    assert hold(buffer, now_ns=50, last_value=-1.0) == -1.0


def test_window_agg_semantics() -> None:
    buffer = EventBuffer((_evt(100, 0, 1.0), _evt(200, 1, 2.0), _evt(280, 2, 4.0)))

    mean_policy = WindowPolicy(duration_ns=200, agg="mean")
    first_policy = WindowPolicy(duration_ns=200, agg="first")
    last_policy = WindowPolicy(duration_ns=200, agg="last")

    assert window_agg(buffer, now_ns=300, policy=mean_policy) == pytest.approx(7.0 / 3.0)
    assert window_agg(buffer, now_ns=300, policy=first_policy) == 1.0
    assert window_agg(buffer, now_ns=300, policy=last_policy) == 4.0
