from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.flow import Flow, PipelineBuilder, Rate, Trigger, flow_io, Latest

from retriever.ir import IR
from retriever.ir.execution import ExecutionGraph


@flow_io
@dataclass
class SourceOut:
    value: int


@flow_io
@dataclass
class ProcOut:
    value: int


class Source(Flow[None, SourceOut]):
    def step(self, _):  # type: ignore[override]
        return SourceOut(value=1)


class Proc(Flow[SourceOut, ProcOut]):
    def step(self, input: SourceOut) -> ProcOut:
        return ProcOut(value=input.value + 1)


class Sink(Flow[ProcOut, None]):
    def step(self, input: ProcOut) -> None:
        return None


def _build_linear_chain_ir(name: str) -> IR:
    with PipelineBuilder(name) as ctx:
        src = Source() @ Rate(hz=10)
        proc = Proc() @ Trigger("value")
        sink = Sink() @ Trigger("value")

        src.then(proc, map={"value": "value"}, sync=Latest())
        proc.then(sink, map={"value": "value"}, sync=Latest())

        return ctx.validate()


def test_compile_execution_builds_execution_graph_and_lowes_to_ir():
    ir = _build_linear_chain_ir("test_compile_execution_builds_execution_graph_and_lowes_to_ir")

    graph = ExecutionGraph.from_ir(ir, policy="aggressive")
    assert graph.ir.metadata.name == ir.metadata.name

    node_ids = [n.id for n in ir.nodes]
    covered = [nid for p in graph.partitions for nid in p.node_ids]
    assert sorted(covered) == sorted(node_ids)
    assert len(set(covered)) == len(node_ids)

    # Aggressive policy should co-locate a simple linear chain with Latest adapters.
    assert any(len(p.node_ids) > 1 for p in graph.partitions)

    execution_ir = graph.to_execution_ir()
    assert execution_ir.metadata.name == ir.metadata.name
    assert execution_ir.metadata.optimized is True
    assert execution_ir.optimization is not None
    assert len(execution_ir.nodes) < len(ir.nodes)






