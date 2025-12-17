from __future__ import annotations

from dataclasses import dataclass

from retriever.core.flow import Flow, Pipeline, Rate, Latest, flow_io
from retriever.core.ir import validate


@flow_io
@dataclass
class Value:
    value: int


class Source(Flow[None, Value]):
    def run(self, _):  # type: ignore[override]
        return Value(value=1)


class AddOne(Flow[Value, Value]):
    def run(self, input: Value) -> Value:
        return Value(value=input.value + 1)


class Sink(Flow[Value, None]):
    def run(self, input: Value) -> None:
        return None


def test_then_outside_context_creates_pipeline():
    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    sink = Sink() @ Rate(hz=10)

    src.then(add, sync=Latest())
    add.then(sink, sync=Latest())

    pipe = src.pipeline
    assert isinstance(pipe, Pipeline)
    assert pipe is add.pipeline is sink.pipeline

    ir = validate(pipe)
    assert len(ir.nodes) == 3
    assert len(ir.edges) == 2


def test_connecting_two_pipelines_merges_them():
    src = Source() @ Rate(hz=10)
    left = AddOne() @ Rate(hz=10)

    right = AddOne() @ Rate(hz=10)
    sink = Sink() @ Rate(hz=10)

    src.then(left, sync=Latest())
    right.then(sink, sync=Latest())

    assert src.pipeline is left.pipeline
    assert right.pipeline is sink.pipeline
    assert src.pipeline is not right.pipeline

    left.then(right, sync=Latest())

    pipe = src.pipeline
    assert isinstance(pipe, Pipeline)
    assert pipe is left.pipeline is right.pipeline is sink.pipeline

    ir = validate(pipe)
    assert len(ir.nodes) == 4
    assert len(ir.edges) == 3

