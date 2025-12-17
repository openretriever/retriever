from __future__ import annotations

from dataclasses import dataclass

from retriever.core.flow import Flow, FlowContext, Rate, flow_io, Latest
from retriever.core.ir import validate
from retriever.core.pipeline_registry import build_ir, register_pipeline


@flow_io
@dataclass
class SourceOut:
    value: int


@flow_io
@dataclass
class ProcOut:
    value: int


class Source(Flow[None, SourceOut]):
    def run(self, _):  # type: ignore[override]
        return SourceOut(value=1)


class Proc(Flow[SourceOut, ProcOut]):
    def run(self, input: SourceOut) -> ProcOut:
        return ProcOut(value=input.value + 1)


class Sink(Flow[ProcOut, None]):
    def run(self, input: ProcOut) -> None:
        return None


def test_pipeline_registry_factory_returns_irstruct():
    @register_pipeline("test_pipeline_registry_factory_returns_irstruct", overwrite=True)
    def build():
        with FlowContext("test_pipeline_registry_factory_returns_irstruct") as ctx:
            src = Source() @ Rate(hz=10)
            proc = Proc() @ Rate(hz=10)
            sink = Sink() @ Rate(hz=10)

            src.then(proc, sync=Latest())
            proc.then(sink, sync=Latest())

            return validate(ctx)

    ir = build_ir("test_pipeline_registry_factory_returns_irstruct")
    assert ir.metadata.name == "test_pipeline_registry_factory_returns_irstruct"
    assert len(ir.nodes) == 3
    assert len(ir.edges) == 2


def test_pipeline_registry_factory_returns_flowcontext():
    @register_pipeline("test_pipeline_registry_factory_returns_flowcontext", overwrite=True)
    def build():
        with FlowContext("test_pipeline_registry_factory_returns_flowcontext") as ctx:
            src = Source() @ Rate(hz=10)
            proc = Proc() @ Rate(hz=10)
            sink = Sink() @ Rate(hz=10)

            src.then(proc, sync=Latest())
            proc.then(sink, sync=Latest())

            return ctx

    ir = build_ir("test_pipeline_registry_factory_returns_flowcontext")
    assert ir.metadata.name == "test_pipeline_registry_factory_returns_flowcontext"
    assert len(ir.nodes) == 3
    assert len(ir.edges) == 2

