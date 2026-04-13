import importlib
import inspect

import pytest

import retriever
from retriever.config import RecordConfig, VizConfig, get_global_config
from retriever.error import ERROR_MSGS, ErrCode
from retriever.flow import EdgeConfig, Flow, Pipeline, PipelineEdge, PipelineGraph, PipelineNode, Rate, io
from retriever.flow.pipeline import run as run_default_pipeline
from retriever.registry.pipeline import run_pipeline
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
    assert callable(retriever.reset_default_pipeline)


def test_retriever_init_can_clear_optional_defaults(tmp_path):
    retriever.init(
        record=str(tmp_path / "session.mcap"),
        default_sync=object(),
        default_viz=VizConfig(hz=2.0),
    )

    config = get_global_config()
    assert isinstance(config["record"], RecordConfig)
    assert config["default_sync"] is not None
    assert config["default_viz"] is not None

    retriever.init(record=None, default_sync=None, default_viz=None)

    assert config["record"] is None
    assert config["default_sync"] is None
    assert config["default_viz"] is None


def test_context_module_imports_without_optional_mcp_runtime():
    context = importlib.import_module("retriever.context")
    assert context.MCPConfig is not None


def test_types_umbrella_exports_packages_not_registry_helpers():
    import retriever.types as types_pkg
    from retriever.types.symbolic import Object, ObjectType

    assert types_pkg.data is not None
    assert types_pkg.language is not None
    assert types_pkg.perception is not None
    assert types_pkg.spatial is not None
    assert types_pkg.symbolic is not None
    assert not hasattr(types_pkg, "register_type")
    assert not hasattr(types_pkg, "Object")
    assert not hasattr(types_pkg, "semantic")
    assert Object is not None
    assert ObjectType is not None


def test_data_package_keeps_root_surface_contract_only():
    import retriever.types.data as data_pkg

    assert data_pkg.Event is not None
    assert data_pkg.streams is not None
    assert data_pkg.dataset is not None
    assert data_pkg.interop is not None
    assert not hasattr(data_pkg, "StreamId")
    assert not hasattr(data_pkg, "SchemaRef")
    assert not hasattr(data_pkg, "ClockDomain")
    assert not hasattr(data_pkg, "hold")
    assert not hasattr(data_pkg, "build_dataset_manifest")


def test_runtime_flow_types_use_timed_buffer_name_only():
    import retriever.flow.types as flow_types

    assert hasattr(flow_types, "TimedBuffer")
    assert not hasattr(flow_types, "EventBuffer")


def test_legacy_typing_namespace_modules_are_removed():
    for module_name in (
        "retriever.data_spec",
        "retriever.robotics_typing",
        "retriever.types.data_spec",
        "retriever.types.robotics",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


def test_public_run_helpers_default_to_multiprocessing():
    assert inspect.signature(run_default_pipeline).parameters["backend"].default == "multiprocessing"
    assert inspect.signature(run_pipeline).parameters["backend"].default == "multiprocessing"
    assert "build" not in inspect.signature(run_default_pipeline).parameters
    assert "build" not in inspect.signature(Pipeline.run).parameters


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


def test_pipeline_run_record_requires_explicit_in_process_backend(tmp_path):
    pipe = Pipeline("record_backend_guard")
    with pipe:
        TickSource() @ Rate(hz=1)

    with pytest.raises(ValueError, match="requires backend='in-process'"):
        pipe.run(duration=0.1, record=str(tmp_path / "session.mcap"))
