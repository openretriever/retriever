from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.error import ErrCode, FlowError
from retriever.flow import Flow, flow_io


@flow_io
@dataclass
class A:
    a: int | None = None


@flow_io
@dataclass
class B:
    b: int | None = None


@flow_io
@dataclass
class C:
    c: int | None = None


@flow_io
@dataclass
class D:
    d: int | None = None


class TupleLiteralInputFlow(Flow[(A, B), C]):
    def step(self, input):
        return C(c=(input.A.a or 0) + (input.B.b or 0))


class TypingTupleInputFlow(Flow[tuple[A, B], C]):
    def step(self, input):
        return C(c=(input.A.a or 0) + (input.B.b or 0))


class TupleOutputFlow(Flow[A, (C, D)]):
    def step(self, input):
        return (C(c=input.a), D(d=input.a))


class TupleInOutFlow(Flow[(A, B), (C, D)]):
    def step(self, input):
        return (C(c=input.A.a), D(d=input.B.b))


class SourceFlow(Flow[None, C]):
    def step(self, _):
        return C(c=1)


class SinkFlow(Flow[A, None]):
    def step(self, _):
        return None


class NoIOFlow(Flow[None, None]):
    def step(self, _):
        return None


def test_tuple_literal_input_signature_declares() -> None:
    assert TupleLiteralInputFlow._input_types == (A, B)
    assert TupleLiteralInputFlow._output_types == (C,)
    assert TupleLiteralInputFlow._input_type is A
    assert TupleLiteralInputFlow._output_type is C


def test_tuple_literal_and_typing_tuple_are_equivalent() -> None:
    assert TupleLiteralInputFlow._input_types == TypingTupleInputFlow._input_types
    assert TupleLiteralInputFlow._output_types == TypingTupleInputFlow._output_types


def test_tuple_output_signatures_are_declared() -> None:
    assert TupleOutputFlow._input_types == (A,)
    assert TupleOutputFlow._output_types == (C, D)
    assert TupleInOutFlow._input_types == (A, B)
    assert TupleInOutFlow._output_types == (C, D)


def test_none_input_output_normalization() -> None:
    assert SourceFlow._input_types == ()
    assert SourceFlow._output_types == (C,)
    assert SinkFlow._input_types == (A,)
    assert SinkFlow._output_types == ()
    assert NoIOFlow._input_types == ()
    assert NoIOFlow._output_types == ()


def test_mixed_tuple_none_element_is_rejected() -> None:
    with pytest.raises(FlowError) as exc_info:

        class _InvalidMixedTupleFlow(Flow[(A, None), C]):
            def step(self, _):
                return C(c=0)

    assert exc_info.value.code == int(ErrCode.FLOW_TYPE_INVALID)

