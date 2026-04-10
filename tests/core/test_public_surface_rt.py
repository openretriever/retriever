import inspect

import pytest

import retriever
from retriever.error import ERROR_MSGS, ErrCode
from retriever.flow import Flow, Pipeline, PipelineEdge, PipelineGraph, PipelineNode, Rate, io
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

    with pytest.raises(NotImplementedError, match="requires a live Pipeline instance"):
        execute_ir(ir, backend="in-process")


def test_dora_unknown_error_code_is_spelled_correctly():
    assert ErrCode.DORA_UNKNOWN == 4200
    assert ERROR_MSGS[ErrCode.DORA_UNKNOWN] == "Unknown dora backend error"
