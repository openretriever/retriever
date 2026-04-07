from __future__ import annotations

import pytest

from retriever.error import ErrCode, FlowError
from retriever.flow import io
from retriever.rt.step import IOView


@io
class A:
    arg1: int
    only_a: int


@io
class B:
    arg1: int
    only_b: int


def _make_observation_type(unique_field: str):
    cls = type(
        "Observation",
        (),
        {"__annotations__": {"arg1": int, unique_field: int}},
    )
    return io(cls)


def test_unique_direct_access() -> None:
    a = A(arg1=1, only_a=10)
    b = B(arg1=2, only_b=20)
    comp = IOView([A, B], {"A": a, "B": b})

    assert comp.only_a == 10
    assert comp.only_b == 20
    assert comp._get_signal("only_a") == 10
    assert comp._get_signal("only_b") == 20
    assert comp._has_signal("only_a")


def test_ambiguous_direct_read_raises() -> None:
    comp = IOView([A, B], {"A": A(arg1=1), "B": B(arg1=2)})
    with raises_ambiguous():
        _ = comp.arg1
    with raises_ambiguous():
        comp._get_signal("arg1")


def test_qualified_collision_reads() -> None:
    comp = IOView([A, B], {"A": A(arg1=3), "B": B(arg1=4)})
    assert comp.A.arg1 == 3
    assert comp.B.arg1 == 4
    assert comp._get_signal("A.arg1") == 3
    assert comp._get_signal("B.arg1") == 4


def test_ambiguous_unqualified_write_raises() -> None:
    comp = IOView([A, B], {"A": A(arg1=1), "B": B(arg1=2)})
    with raises_ambiguous():
        comp._set_signal("arg1", 42)


def test_qualified_write_targets_single_source() -> None:
    comp = IOView([A, B], {"A": A(arg1=1), "B": B(arg1=2)})
    comp._set_signal("A.arg1", 11)
    assert comp.A.arg1 == 11
    assert comp.B.arg1 == 2


def test_ambiguous_has_signal_raises() -> None:
    comp = IOView([A, B], {"A": A(arg1=1), "B": B(arg1=2)})
    with raises_ambiguous():
        comp._has_signal("arg1")


def test_duplicate_class_name_aliases_are_deterministic() -> None:
    ObservationOne = _make_observation_type("o1")
    ObservationTwo = _make_observation_type("o2")
    comp = IOView([ObservationOne, ObservationTwo])

    aliases = list(comp._instances.keys())
    assert aliases == ["Observation__1", "Observation__2"]

    comp._set_signal("Observation__1.arg1", 7)
    comp._set_signal("Observation__2.arg1", 9)

    assert comp._get_signal("Observation__1.arg1") == 7
    assert comp._get_signal("Observation__2.arg1") == 9

    ports = IOView.resolve_ports([ObservationOne, ObservationTwo])
    assert "Observation__1.arg1" in ports
    assert "Observation__2.arg1" in ports


class raises_ambiguous:
    def __enter__(self):
        self._ctx = pytest.raises(FlowError)
        self._exc = self._ctx.__enter__()
        return self._exc

    def __exit__(self, exc_type, exc, tb):
        ok = self._ctx.__exit__(exc_type, exc, tb)
        if ok:
            assert self._exc.value.code == int(ErrCode.FLOW_AMBIGUOUS_FIELD)
        return ok
