from __future__ import annotations

from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, Latest, flow_io
from retriever.ir import validate


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


def test_pipeline_default_on_lag_applies_to_default_rate_nodes():
    pipe = Pipeline("demo", on_lag="error")

    src = Source() @ Rate(hz=10)  # default on_lag="warn" -> should become "error"
    add = AddOne() @ Rate(hz=10, on_lag="drop")  # explicit non-default should be preserved
    sink = Sink() @ Rate(hz=10)

    pipe.connect(src, add, sync=Latest())
    pipe.connect(add, sink, sync=Latest())

    validate(pipe)

    assert src.config.clock.on_lag == "error"
    assert add.config.clock.on_lag == "drop"
    assert sink.config.clock.on_lag == "error"


def test_pipeline_context_wiring_sets_pipeline_and_persists_after_context():
    pipe = Pipeline("demo")

    with pipe:
        src = Source() @ Rate(hz=10)
        add = AddOne() @ Rate(hz=10)
        src >> add

    # After leaving the context, `add` is already tagged with `pipe`, so chaining
    # should continue to attach edges into the same pipeline.
    sink = Sink() @ Rate(hz=10)
    add >> sink

    assert src.pipeline is pipe
    assert add.pipeline is pipe
    assert sink.pipeline is pipe

    ir = validate(pipe)
    assert len(ir.nodes) == 3
    assert len(ir.edges) == 2


def test_retriever_connect_uses_default_pipeline_by_default():
    import retriever

    retriever.reset_default_pipeline()

    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)

    retriever.connect(src, add)

    pipe = retriever.default_pipeline()
    assert src.pipeline is pipe
    assert add.pipeline is pipe

    ir = validate(pipe)
    assert len(ir.nodes) == 2
    assert len(ir.edges) == 1


def test_retriever_connect_respects_active_pipeline_context():
    import retriever

    retriever.reset_default_pipeline()
    default = retriever.default_pipeline()

    pipe = Pipeline("demo")
    with pipe:
        src = Source() @ Rate(hz=10)
        add = AddOne() @ Rate(hz=10)
        retriever.connect(src, add)

    assert src.pipeline is pipe
    assert add.pipeline is pipe
    assert len(default.get_handles()) == 0
    assert len(default.get_connections()) == 0


def test_reset_default_pipeline_clears_accumulated_graph():
    import retriever

    retriever.reset_default_pipeline()
    old = retriever.default_pipeline()

    src = Source() @ Rate(hz=10)
    add = AddOne() @ Rate(hz=10)
    retriever.connect(src, add)

    assert len(old.get_handles()) == 2
    assert len(old.get_connections()) == 1

    new = retriever.reset_default_pipeline()
    assert new is not old
    assert len(new.get_handles()) == 0
    assert len(new.get_connections()) == 0
