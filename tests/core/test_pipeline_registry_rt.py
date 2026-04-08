from __future__ import annotations

import pytest

from retriever.flow import Flow, Pipeline, PipelineBuilder, Rate, io, Latest
from retriever.pipeline_registry import (
    build_ir,
    build_pipeline_flow,
    build_pipeline_surface,
    register_pipeline,
)


@io
class SourceOut:
    value: int


@io
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


@io
class RichOut:
    value: int
    aux: int


@io
class RichIn:
    value: int
    bias: int


@io
class BiasOut:
    bias: int


class RichSource(Flow[None, RichOut]):
    def step(self, _):  # type: ignore[override]
        return RichOut(value=1, aux=9)


class CountingRichSource(Flow[None, RichOut]):
    def init(self) -> None:
        self.count = 0

    def reset(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return RichOut(value=self.count, aux=9)


class RichProc(Flow[RichIn, ProcOut]):
    def step(self, input: RichIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias)


class ReplacementProc(Flow[RichIn, ProcOut]):
    def step(self, input: RichIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias + 10)


class BiasSource(Flow[None, BiasOut]):
    def __init__(self, *, bias: int):
        super().__init__()
        self.bias = bias

    def step(self, _):  # type: ignore[override]
        return BiasOut(bias=self.bias)


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


def test_pipeline_registry_explicit_surface_selectors_support_named_flow_ids():
    @register_pipeline(
        "test_pipeline_registry_explicit_surface",
        surface_policy="explicit",
        input_ports=["processor.bias"],
        output_ports=["source.aux"],
        overwrite=True,
    )
    def build():
        with PipelineBuilder("test_pipeline_registry_explicit_surface") as ctx:
            src = (RichSource() @ Rate(hz=10)).named("source")
            proc = (RichProc() @ Rate(hz=10)).named("processor")
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    surface = build_pipeline_surface("test_pipeline_registry_explicit_surface")
    assert [port.node_id for port in surface.inputs] == ["processor"]
    assert [port.port for port in surface.inputs] == ["bias"]
    assert [port.node_id for port in surface.outputs] == ["source"]
    assert [port.port for port in surface.outputs] == ["aux"]
    assert [port.external_name for port in surface.inputs] == ["bias"]
    assert [port.external_name for port in surface.outputs] == ["aux"]


def test_pipeline_select_flow_and_get_flow_dict_use_stable_ids():
    pipe = Pipeline("test_pipeline_select_flow")
    with pipe:
        src = (RichSource() @ Rate(hz=10)).named("source")
        proc = (RichProc() @ Rate(hz=10)).named("processor")
        src.then(proc, map={"value": "value"}, sync=Latest())

    assert set(pipe.get_flow_dict()) == {"source", "processor"}
    assert pipe.select_flow("source") is src
    assert pipe.select_flow("processor") is proc
    assert pipe.select_flow("RichProc") is proc


def test_pipeline_replace_preserves_flow_selector_by_default():
    pipe = Pipeline("test_pipeline_replace_keeps_selector")
    with pipe:
        src = (CountingRichSource() @ Rate(hz=10)).named("source")
        proc = (RichProc() @ Rate(hz=10)).named("processor")
        src.then(proc, map={"value": "value"}, sync=Latest())

    replacement = ReplacementProc() @ Rate(hz=10)
    pipe.replace(proc, replacement)

    pipe.inject_input("processor", "bias", 4, timestamp=0.0)
    result = pipe.step(now=0.0)

    assert pipe.select_flow("processor") is replacement
    assert pipe.get_node_id(replacement) == "processor"
    assert result.outputs["processor"].value == 15

    ir = pipe.validate()
    assert any(node.id == "processor" and node.type == "ReplacementProc" for node in ir.nodes)


def test_pipeline_registry_can_build_flow_wrapper_from_surface():
    @register_pipeline("test_pipeline_registry_flow_wrapper", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_flow_wrapper") as ctx:
            src = (CountingRichSource() @ Rate(hz=10)).named("source")
            proc = (RichProc() @ Rate(hz=10)).named("processor")
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


def test_pipeline_registry_flow_wrapper_can_be_nested_in_outer_pipeline(monkeypatch):
    from retriever.rt.stepper import PipelineStepper

    step_calls: list[float | None] = []
    inject_calls: list[float | None] = []
    original_step = PipelineStepper.step
    original_inject_inputs = PipelineStepper.inject_inputs

    def spy_step(self, *, now=None, dt=None):
        step_calls.append(now)
        return original_step(self, now=now, dt=dt)

    def spy_inject_inputs(self, values, *, timestamp=None):
        inject_calls.append(timestamp)
        return original_inject_inputs(self, values, timestamp=timestamp)

    monkeypatch.setattr(PipelineStepper, "step", spy_step)
    monkeypatch.setattr(PipelineStepper, "inject_inputs", spy_inject_inputs)

    @register_pipeline("test_pipeline_registry_nested_wrapper", overwrite=True)
    def build():
        with PipelineBuilder("test_pipeline_registry_nested_wrapper") as ctx:
            src = (CountingRichSource() @ Rate(hz=10)).named("source")
            proc = (RichProc() @ Rate(hz=10)).named("processor")
            src.then(proc, map={"value": "value"}, sync=Latest())
            return ctx

    outer = Pipeline("test_pipeline_registry_outer")
    with outer:
        bias = (BiasSource(bias=4) @ Rate(hz=10)).named("bias")
        stage = (build_pipeline_flow("test_pipeline_registry_nested_wrapper") @ Rate(hz=10)).named("stage")
        bias.then(stage, sync=Latest())

    try:
        ir = outer.validate()
        assert any(node.id == "stage" and node.config.get("in_process_only") for node in ir.nodes)

        result = outer.step(now=7.0)
        assert result.outputs["stage"].value == 5
        assert result.outputs["stage"].aux == 9
        assert step_calls == [7.0, 7.0]
        assert inject_calls == [7.0]
    finally:
        outer.close_stepper()


def test_pipeline_registry_flow_wrapper_respects_explicit_surface():
    @register_pipeline(
        "test_pipeline_registry_flow_wrapper_explicit",
        surface_policy="explicit",
        input_ports=["processor.bias"],
        output_ports=["source.aux"],
        overwrite=True,
    )
    def build():
        pipe = Pipeline("test_pipeline_registry_flow_wrapper_explicit")
        with pipe:
            src = (RichSource() @ Rate(hz=10)).named("source")
            proc = (RichProc() @ Rate(hz=10)).named("processor")
            src.then(proc, map={"value": "value"}, sync=Latest())
        return pipe

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
