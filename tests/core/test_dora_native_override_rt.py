import pytest


yaml = pytest.importorskip("yaml")  # PyYAML (optional; required for dora compiler)


from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, Rate, flow_io, Latest


@flow_io
@dataclass
class Val:
    x: int


class Src(Flow[None, Val]):
    def step(self, _):  # type: ignore[override]
        return Val(x=1)


class Add(Flow[Val, Val]):
    def step(self, input: Val) -> Val:
        return Val(x=input.x + 1)


def _build_ir():
    pipe = Pipeline("native_override_test")
    a = Src() @ Rate(hz=1)
    b = Add() @ Rate(hz=1)
    pipe.connect(a, b, sync=Latest())
    return pipe.validate()


def test_dora_compiler_respects_native_overrides_by_type():
    from retriever.rt.backend.dora.compiler import compile_and_validate

    ir = _build_ir()
    assert len(ir.nodes) == 2

    native_path = "native:dummy-binary"
    overrides = {ir.nodes[0].type: native_path}

    yaml_str = compile_and_validate(ir, node_path_overrides=overrides)
    parsed = yaml.safe_load(yaml_str)

    nodes = {n["id"]: n for n in parsed["nodes"]}
    assert nodes[ir.nodes[0].id]["path"] == native_path
    assert nodes[ir.nodes[1].id]["path"] == "dynamic"


def test_dora_compiler_override_priority_node_id_wins():
    from retriever.rt.backend.dora.compiler import compile_and_validate

    ir = _build_ir()
    node0 = ir.nodes[0]

    yaml_str = compile_and_validate(
        ir,
        node_path_overrides={
            node0.type: "native:type",
            node0.id: "native:id",
        },
    )
    parsed = yaml.safe_load(yaml_str)
    nodes = {n["id"]: n for n in parsed["nodes"]}
    assert nodes[node0.id]["path"] == "native:id"


def test_dora_engine_skips_python_executor_for_native_node():
    dora = pytest.importorskip("dora")  # noqa: F401
    pyarrow = pytest.importorskip("pyarrow")  # noqa: F401

    from retriever.rt.backend.dora.engine import DoraEngine

    ir = _build_ir()
    native_path = "native:dummy-binary"
    overrides = {ir.nodes[0].type: native_path}

    engine = DoraEngine(ir, config={"native_overrides": overrides})
    engine.build()

    # Only the non-native node should have a Python executor.
    assert len(engine.executors) == 1

