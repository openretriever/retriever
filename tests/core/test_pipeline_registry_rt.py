from __future__ import annotations

from dataclasses import dataclass

import pytest

from retriever.flow import Flow, PipelineBuilder, Rate, flow_io, Latest
from retriever.pipeline_registry import (
    build_ir,
    build_pipeline_flow,
    build_pipeline_surface,
    register_pipeline,
)


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


class CountingRichSource(Flow[None, RichOut]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return RichOut(value=self.count, aux=9)


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
    assert [port.external_name for port in surface.inputs] == ["bias"]
    assert sorted(port.external_name for port in surface.outputs) == ["aux", "value"]


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
    assert [port.external_name for port in surface.inputs] == ["bias"]
    assert [port.external_name for port in surface.outputs] == ["aux"]


def test_pipeline_registry_can_build_flow_wrapper_from_surface():
    @register_pipeline("test_pipeline_registry_flow_wrapper", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_flow_wrapper") as ctx:
            src = CountingRichSource() @ Rate(hz=10)
            proc = RichProc() @ Rate(hz=10)
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    flow = build_pipeline_flow("test_pipeline_registry_flow_wrapper")
    out1 = flow.step(flow.input_type(bias=4))
    out2 = flow.step(flow.input_type(bias=4))
    flow.finalize()

    assert out1.value == 5
    assert out1.aux == 9
    assert out2.value == 6
    assert out2.aux == 9
    assert [port.external_name for port in flow.surface.inputs] == ["bias"]


def test_pipeline_registry_flow_wrapper_respects_explicit_surface():
    @register_pipeline(
        "test_pipeline_registry_flow_wrapper_explicit",
        surface_policy="explicit",
        input_ports=["RichProc.bias"],
        output_ports=["RichSource.aux"],
        overwrite=True,
    )
    def build():
        with PipelineBuilder("test_pipeline_registry_flow_wrapper_explicit") as ctx:
            src = RichSource() @ Rate(hz=10)
            proc = RichProc() @ Rate(hz=10)
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    flow = build_pipeline_flow("test_pipeline_registry_flow_wrapper_explicit")
    out = flow.step(flow.input_type(bias=3))
    flow.finalize()

    assert set(flow.input_type.__dataclass_fields__.keys()) == {"bias"}
    assert set(flow.output_type.__dataclass_fields__.keys()) == {"aux"}
    assert out.aux == 9


def test_pipeline_registry_flow_wrapper_rejects_ir_only_factories():
    @register_pipeline("test_pipeline_registry_flow_wrapper_ir_only", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_flow_wrapper_ir_only") as ctx:
            src = RichSource() @ Rate(hz=10)
            return ctx.validate()

    with pytest.raises(TypeError, match="requires a live Pipeline or PipelineBuilder"):
        build_pipeline_flow("test_pipeline_registry_flow_wrapper_ir_only")
