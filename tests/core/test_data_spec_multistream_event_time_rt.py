from __future__ import annotations

from retriever.data_spec import (
    Event,
    EventBuffer,
    JoinPolicy,
    StreamId,
    align_exact,
    align_latest_before,
    align_window,
    join_with_policy,
)


def _evt(stream: str, t: int, seq: int, value: int) -> Event[int]:
    return Event(
        stream_id=StreamId(stream),
        event_time_ns=t,
        ingest_time_ns=t,
        seq=seq,
        value=value,
        type_name="int",
    )


def test_align_exact_pairs_only_equal_timestamps() -> None:
    left = EventBuffer((_evt("a", 100, 0, 1), _evt("a", 200, 1, 2)))
    right = EventBuffer((_evt("b", 200, 0, 20), _evt("b", 300, 1, 30)))

    out = align_exact(left, right)

    assert len(out) == 1
    assert out[0].value == (2, 20)
    assert out[0].lineage is not None
    assert len(out[0].lineage.sources) == 2


def test_align_latest_before_respects_delta() -> None:
    left = EventBuffer((_evt("a", 100, 0, 1), _evt("a", 180, 1, 2)))
    right = EventBuffer((_evt("b", 200, 0, 20), _evt("b", 450, 1, 30)))

    out = align_latest_before(left, right, max_delta_ns=50)

    assert len(out) == 1
    assert out[0].value == (2, 20)


def test_align_window_uses_nearest_event_within_window() -> None:
    left = EventBuffer((_evt("a", 100, 0, 1), _evt("a", 190, 1, 2), _evt("a", 260, 2, 3)))
    right = EventBuffer((_evt("b", 200, 0, 20),))

    out = align_window(left, right, window_ns=20)

    assert len(out) == 1
    assert out[0].value == (2, 20)


def test_join_with_policy_dispatch() -> None:
    left = EventBuffer((_evt("a", 100, 0, 1),))
    right = EventBuffer((_evt("b", 100, 0, 9),))

    exact_policy = JoinPolicy(mode="exact")
    out = join_with_policy(left, right, policy=exact_policy)

    assert len(out) == 1
    assert out[0].value == (1, 9)


def test_binary_composed_n_way_join_is_deterministic() -> None:
    a = EventBuffer((_evt("a", 100, 0, 1),))
    b = EventBuffer((_evt("b", 100, 0, 2),))
    c = EventBuffer((_evt("c", 100, 0, 3),))

    ab = align_exact(a, b, output_stream_id="join.ab")
    abc = align_exact(ab, c, output_stream_id="join.abc")

    assert len(abc) == 1
    assert abc[0].value == ((1, 2), 3)
