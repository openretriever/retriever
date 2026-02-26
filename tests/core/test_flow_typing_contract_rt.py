from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.error import ErrCode, FlowError
from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, flow_io
from retriever.rt.step import IOStep


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
    timestamp: float | None = None


@flow_io
@dataclass
class D:
    d: int | None = None
    timestamp: float | None = None


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


class SourceA(Flow[None, A]):
    def step(self, _):
        return A(a=2)


class SourceB(Flow[None, B]):
    def step(self, _):
        return B(b=3)


class SplitAFlow(Flow[A, (C, D)]):
    def step(self, input):
        return (
            C(c=(input.a or 0) + 1, timestamp=1.5),
            D(d=(input.a or 0) + 2, timestamp=2.5),
        )


class SinkC(Flow[C, None]):
    def init(self):
        self.values = []

    def step(self, input):
        self.values.append(input.c)
        return None


class SinkD(Flow[D, None]):
    def init(self):
        self.values = []

    def step(self, input):
        self.values.append(input.d)
        return None


class CapturePublisher:
    def __init__(self):
        self.items = []

    def put_one(self, value, timestamp, block=False):
        self.items.append((value, timestamp))


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


def test_tuple_output_publishes_in_stepper() -> None:
    pipe = Pipeline("tuple_output_stepper")
    with pipe:
        src = SourceA() @ Rate(hz=100)
        split = SplitAFlow() @ Trigger("a")
        sink_c = SinkC() @ Trigger("c")
        sink_d = SinkD() @ Trigger("d")
        src.then(split, sync=Latest())
        split.then(sink_c, sync=Latest())
        split.then(sink_d, sync=Latest())

    pipe.step(dt=0.01)
    assert sink_c.flow.values == [3]
    assert sink_d.flow.values == [4]


def test_full_composite_in_out_end_to_end_routing() -> None:
    pipe = Pipeline("tuple_in_out_stepper")
    with pipe:
        src_a = SourceA() @ Rate(hz=100)
        src_b = SourceB() @ Rate(hz=100)
        split = TupleInOutFlow() @ Trigger("a")
        sink_c = SinkC() @ Trigger("c")
        sink_d = SinkD() @ Trigger("d")
        src_a.then(split, sync=Latest())
        src_b.then(split, sync=Latest())
        split.then(sink_c, sync=Latest())
        split.then(sink_d, sync=Latest())

    pipe.step(dt=0.01)
    assert sink_c.flow.values == [2]
    assert sink_d.flow.values == [3]


def test_tuple_output_publishes_in_mp_backend() -> None:
    c_pub = CapturePublisher()
    d_pub = CapturePublisher()

    IOStep(
        instance=(C(c=5, timestamp=1.0), D(d=6, timestamp=2.0)),
        output_types=(C, D),
        now=50.0,
    ).publish(
        {
            "c": [c_pub],
            "d": [d_pub],
        }
    )

    assert c_pub.items == [(5, 1.0)]
    assert d_pub.items == [(6, 2.0)]


def test_tuple_output_publishes_in_dora_backend() -> None:
    c_pub = CapturePublisher()
    d_pub = CapturePublisher()

    IOStep(
        instance=(C(c=7, timestamp=3.0), D(d=8, timestamp=4.0)),
        output_types=(C, D),
        now=60.0,
    ).publish(
        {
            "c": [c_pub],
            "d": [d_pub],
        }
    )

    assert c_pub.items == [(7, 3.0)]
    assert d_pub.items == [(8, 4.0)]


def test_generator_completion_tuple_output_publish() -> None:
    c_pub = CapturePublisher()
    d_pub = CapturePublisher()

    IOStep(
        instance=(C(c=9, timestamp=9.5), D(d=10, timestamp=10.5)),
        output_types=(C, D),
        now=99.0,
    ).publish(
        {
            "c": [c_pub],
            "d": [d_pub],
        }
    )

    assert c_pub.items == [(9, 9.5)]
    assert d_pub.items == [(10, 10.5)]
