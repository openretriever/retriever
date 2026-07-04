"""Regression tests for authoring-layer bugs found in pre-release review.

Covers:
- Tick construction (previously crashed passing removed `fields=` to Rate)
- self-connection rejection (previously hung IR chain partitioning)
- chain partitioner termination on cyclic graphs
- PipelineBuilder.require_active() raising a proper FlowError
- duplicate node ids rejected by PipelineGraph
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.error import ErrCode, FlowError
from retriever.flow import Flow, Latest, Pipeline, Rate, Tick, io
from retriever.flow.builder import PipelineBuilder
from retriever.flow.graph import PipelineGraph
from retriever.ir.execution import ChainPartitioner


@io
@dataclass
class Value:
    value: int


class Source(Flow[None, Value]):
    def step(self, _):  # type: ignore[override]
        return Value(value=1)


class Echo(Flow[Value, Value]):
    def step(self, input: Value) -> Value:
        return Value(value=input.value)


def test_tick_constructs_like_rate() -> None:
    tick = Tick(hz=10)
    assert tick.hz == 10
    assert tick.interval == pytest.approx(0.1)
    assert repr(tick) == "Tick(hz=10)"


def test_tick_normalizes_on_lag_aliases() -> None:
    assert Tick(hz=5, on_lag="panic").on_lag == "error"


def test_self_connection_is_rejected() -> None:
    pipe = Pipeline("self_loop")
    node = Echo() @ Rate(hz=10)
    with pytest.raises(FlowError) as excinfo:
        pipe.connect(node, node, sync=Latest())
    assert excinfo.value.code == ErrCode.FLOW_CONNECTION_INVALID


def test_chain_partitioner_terminates_on_cycle() -> None:
    pipe = Pipeline("cycle")
    a = Echo() @ Rate(hz=10)
    b = Echo() @ Rate(hz=10)
    pipe.connect(a, b, sync=Latest())
    pipe.connect(b, a, sync=Latest())
    ir = pipe.validate()

    chains = ChainPartitioner().partition(ir, None, lambda *args: True)
    for chain in chains:
        assert len(chain) == len(set(chain))


def test_require_active_raises_flow_error_outside_context() -> None:
    assert PipelineBuilder.active() is None
    with pytest.raises(FlowError) as excinfo:
        PipelineBuilder.require_active()
    assert excinfo.value.code == ErrCode.PIPELINE_BUILDER_INACTIVE


def test_duplicate_node_id_is_rejected() -> None:
    graph = PipelineGraph()
    graph.add_node("n", {}, {"out": int})
    with pytest.raises(FlowError) as excinfo:
        graph.add_node("n", {}, {"out": int})
    assert excinfo.value.code == ErrCode.PIPELINE_GRAPH_DUPLICATE_NODE
