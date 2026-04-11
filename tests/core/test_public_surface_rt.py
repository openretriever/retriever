import inspect

import pytest

import retriever
from retriever.error import ERROR_MSGS, ErrCode
from retriever.flow import EdgeConfig, Flow, Pipeline, PipelineEdge, PipelineGraph, PipelineNode, Rate, io
from retriever.flow.pipeline import run as run_default_pipeline
from retriever.pipeline_registry import run_pipeline
from retriever.rt import execute_ir


@io
class TickOut:
    value: int


class TickSource(Flow[None, TickOut]):
    def step(self, _):  # type: ignore[override]
        return TickOut(value=1)


def test_flow_module_exports_pipeline_graph_names_only():
    assert PipelineGraph is not None
    assert PipelineNode is not None
    assert PipelineEdge is not None
    assert EdgeConfig is not None

    with pytest.raises(ImportError):
        exec("from retriever.flow import FlowGraph")


def test_top_level_retriever_exports_clear_default_pipeline():
    assert callable(retriever.clear_default_pipeline)


def test_public_run_helpers_default_to_multiprocessing():
    assert inspect.signature(run_default_pipeline).parameters["backend"].default == "multiprocessing"
    assert inspect.signature(run_pipeline).parameters["backend"].default == "multiprocessing"


def test_execute_ir_in_process_requires_live_pipeline_instance():
    pipe = Pipeline("in_process_guard")
    with pipe:
        TickSource() @ Rate(hz=1)
    ir = pipe.validate()

    with pytest.raises(ValueError, match="live-Pipeline debug/recording surface"):
        execute_ir(ir, backend="in-process")


def test_dora_unknown_error_code_is_spelled_correctly():
    assert ErrCode.DORA_UNKNOWN == 4200
    assert ERROR_MSGS[ErrCode.DORA_UNKNOWN] == "Unknown dora backend error"


def test_pipeline_run_rejects_deploy_on_non_dora_backend():
    pipe = Pipeline("deploy_guard")
    with pipe:
        src = TickSource() @ Rate(hz=1)

    with pytest.raises(ValueError, match="backend='dora'"):
        pipe.run(
            backend="multiprocessing",
            duration=0.1,
            deploy={pipe.get_node_id(src): "machine-a"},
        )


def test_pipeline_run_rejects_host_affinity_on_non_dora_backend():
    pipe = Pipeline("affinity_guard")
    with pipe:
        (TickSource() @ Rate(hz=1)).deploy("machine-a")

    with pytest.raises(ValueError, match="backend='dora'"):
        pipe.run(backend="multiprocessing", duration=0.1)
