from __future__ import annotations

from dataclasses import dataclass

from retriever.flow import Flow, PipelineBuilder, Rate, flow_io, Latest
from retriever.pipeline_registry import build_ir, build_pipeline_surface, register_pipeline


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


@flow_io
@dataclass
class RichOut:
    value: int
    aux: int


@flow_io
@dataclass
class RichIn:
    value: int
    bias: int


class RichSource(Flow[None, RichOut]):
    def step(self, _):  # type: ignore[override]
        return RichOut(value=1, aux=9)


class RichProc(Flow[RichIn, ProcOut]):
    def step(self, input: RichIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias)


def test_pipeline_registry_factory_returns_irstruct():
    @register_pipeline("test_pipeline_registry_factory_returns_irstruct", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_factory_returns_irstruct") as ctx:
            src = Source() @ Rate(hz=10)
            proc = Proc() @ Rate(hz=10)
            sink = Sink() @ Rate(hz=10)

            src.then(proc, sync=Latest())
            proc.then(sink, sync=Latest())

            return ctx.validate()

    ir = build_ir("test_pipeline_registry_factory_returns_irstruct")
    assert ir.metadata.name == "test_pipeline_registry_factory_returns_irstruct"
    assert len(ir.nodes) == 3
    assert len(ir.edges) == 2


def test_pipeline_registry_factory_returns_flowcontext():
    @register_pipeline("test_pipeline_registry_factory_returns_flowcontext", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_factory_returns_flowcontext") as ctx:
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


def test_pipeline_registry_auto_surface_exposes_unused_ports():
    @register_pipeline("test_pipeline_registry_auto_surface", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_auto_surface") as ctx:
            src = RichSource() @ Rate(hz=10)
            proc = RichProc() @ Rate(hz=10)
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    surface = build_pipeline_surface("test_pipeline_registry_auto_surface")
    assert {(port.node_type, port.port) for port in surface.inputs} == {("RichProc", "bias")}
    assert {(port.node_type, port.port) for port in surface.outputs} == {
        ("RichSource", "aux"),
        ("RichProc", "value"),
    }


def test_pipeline_registry_explicit_surface_selectors():
    @register_pipeline(
        "test_pipeline_registry_explicit_surface",
        surface_policy="explicit",
        input_ports=["RichProc.bias"],
        output_ports=["RichSource.aux"],
        overwrite=True,
    )
    def build():
        with PipelineBuilder("test_pipeline_registry_explicit_surface") as ctx:
            src = RichSource() @ Rate(hz=10)
            proc = RichProc() @ Rate(hz=10)
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    surface = build_pipeline_surface("test_pipeline_registry_explicit_surface")
    assert [port.node_type for port in surface.inputs] == ["RichProc"]
    assert [port.port for port in surface.inputs] == ["bias"]
    assert [port.node_type for port in surface.outputs] == ["RichSource"]
    assert [port.port for port in surface.outputs] == ["aux"]
