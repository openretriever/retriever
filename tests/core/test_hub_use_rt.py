"""End-to-end tests for hub.use() with mocked HTTP."""

import io as pyio
import tarfile
import pytest
from pathlib import Path
from unittest.mock import patch
import sys

from retriever.error import ErrCode, HubError
from retriever.hub._loader import ModuleProxy
from retriever.flow import Flow, Pipeline, Rate, Latest, io
from retriever.flow.io import get_flow_io_fields, get_flow_io_types, is_flow_io
from retriever.rt.lifecycle import initialize_flow_runtime, instantiate_flow_from_node
from retriever.rt.runtime import execute_ir


@io
class OverrideIn:
    value: int
    bias: int


@io
class OverrideOut:
    value: int


class OverrideProc(Flow[OverrideIn, OverrideOut]):
    def __init__(self, *, delta: int = 10):
        super().__init__()
        self.delta = delta

    def step(self, input: OverrideIn) -> OverrideOut:
        return OverrideOut(value=input.value + input.bias + self.delta)


@io
class BiasOut:
    bias: int


class BiasSource(Flow[None, BiasOut]):
    def __init__(self, *, bias: int):
        super().__init__()
        self.bias = bias

    def init_config(self) -> dict:
        return {"bias": self.bias}

    def step(self, _):  # type: ignore[override]
        return BiasOut(bias=self.bias)


def _build_tarball(files: dict[str, str], top_dir: str = "repo-sha123") -> bytes:
    """Build an in-memory tarball.

    Args:
        files: {relative_path: content} — paths relative to top_dir.
        top_dir: Top-level directory name in the archive.

    Returns:
        gzipped tar bytes.
    """
    buf = pyio.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel_path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"{top_dir}/{rel_path}")
            info.size = len(data)
            tf.addfile(info, pyio.BytesIO(data))
    return buf.getvalue()


_INDEX_TOML = """\
[module]
repo = "https://github.com/test-org/test-mod"
description = "Test module"
author = "Test"
"""

_PYPROJECT_TOML = """\
[project]
name = "test-mod"
dependencies = []

[tool.retriever.module]
module = "test_mod"

[tool.retriever.module.exports]
TestFlow = "test_mod.flow:TestFlow"
TestConfig = "test_mod.config:TestConfig"
SharedPose = "test_mod.types:SharedPose"
pose_to_tuple = "test_mod.transforms:pose_to_tuple"
GreeterFlow = "test_mod.greeter:GreeterFlow"
GreeterInput = "test_mod.greeter_types:GreeterInput"
GreeterOutput = "test_mod.greeter_types:GreeterOutput"
BuildTestPipeline = "test_mod.pipeline:build_test_pipeline"
BuildTestPipelineFlow = "test_mod.pipeline:build_test_pipeline_flow"
"""

_TAGS_JSON = [
    {"name": "v1.0.0", "commit": {"sha": "abc123def456789012345678901234567890abcd"}},
    {"name": "v0.9.0", "commit": {"sha": "older_sha_padding_to_fill_space_here_1234"}},
]


@pytest.fixture(autouse=True)
def _clean_hub_state():
    """Clear hub in-process cache and sys.modules before each test."""
    import retriever.hub as hub_mod
    hub_mod._loaded.clear()
    yield
    hub_mod._loaded.clear()
    # Clean up any test modules from sys.modules
    for key in list(sys.modules):
        if "test_mod" in key or "_retriever_hub" in key:
            del sys.modules[key]


def _make_tarball(*, flow_delta: int = 1) -> bytes:
    return _build_tarball({
        "pyproject.toml": _PYPROJECT_TOML,
        "test_mod/__init__.py": "",
        "test_mod/flow.py": """from retriever.flow import Flow, io
from test_mod.config import TestConfig


@io
class TestFlowIn:
    value: int


@io
class TestFlowOut:
    value: int


class TestFlow(Flow[TestFlowIn, TestFlowOut]):
    name = "test"

    def __init__(self):
        super().__init__()
        self.cfg = TestConfig()

    def step(self, input: TestFlowIn) -> TestFlowOut:
        return TestFlowOut(value=input.value + self.cfg.delta)
""",
        "test_mod/config.py": f"""class TestConfig:
    delta = {flow_delta}
""",
        "test_mod/types.py": """from retriever import register_type
from retriever.flow import io


@register_type(
    "HubSharedPose",
    category="geometry",
    description="Hub-exported shared pose envelope",
    tags=["hub", "pose"],
)
@io
class SharedPose:
    x: float
    y: float
    z: float
""",
        "test_mod/transforms.py": """def pose_to_tuple(pose):
    return (pose.x, pose.y, pose.z)
""",
        "test_mod/greeter_types.py": """from retriever.flow import io


@io
class GreeterInput:
    name: str


@io
class GreeterOutput:
    greeting: str
""",
        "test_mod/greeter.py": """from retriever.flow import Flow
from test_mod.greeter_types import GreeterInput, GreeterOutput


class GreeterFlow(Flow[GreeterInput, GreeterOutput]):
    def __init__(self, prefix: str = "Hello"):
        super().__init__()
        self.prefix = prefix

    def run(self, input: GreeterInput) -> GreeterOutput:
        return GreeterOutput(greeting=f"{self.prefix}, {input.name}!")
""",
        "test_mod/pipeline.py": """from retriever.flow import Flow, Pipeline, Rate, Latest, io
from retriever.pipeline_registry import register_pipeline, build_pipeline_flow


@io
class SourceOut:
    value: int
    aux: int


@io
class ProcIn:
    value: int
    bias: int


@io
class ProcOut:
    value: int


class TestSource(Flow[None, SourceOut]):
    def init(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return SourceOut(value=self.count, aux=99)


class TestProc(Flow[ProcIn, ProcOut]):
    def step(self, input: ProcIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias)


def build_test_pipeline():
    pipe = Pipeline("hub_test_pipeline")
    with pipe:
        source = (TestSource() @ Rate(hz=10)).named("source")
        processor = (TestProc() @ Rate(hz=10)).named("processor")
        source.then(processor, map={"value": "value"}, sync=Latest())
    return pipe


@register_pipeline(
    "hub_test_pipeline",
    surface_policy="explicit",
    input_ports=["processor.bias"],
    output_ports=["source.aux", "processor.value"],
    overwrite=True,
)
def _build_registered_test_pipeline():
    return build_test_pipeline()


def build_test_pipeline_flow():
    return build_pipeline_flow("hub_test_pipeline")
""",
    })


class TestHubUse:
    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_with_attribute(self, mock_request, mock_cache_root, tmp_path: Path):
        mock_cache_root.__truediv__ = lambda self, x: tmp_path / x
        # Patch _CACHE_ROOT properly
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub
            result = hub.use("test-org/test-mod:TestFlow")
            assert result.__name__ == "TestFlow"
            assert result.name == "test"
            flow = result()
            out = flow.step(flow.input_type(value=4))
            assert out.value == 5

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_whole_module(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub
            mod = hub.use("test-org/test-mod")
            assert isinstance(mod, ModuleProxy)
            assert mod.TestFlow.__name__ == "TestFlow"
            assert mod.TestConfig.__name__ == "TestConfig"
            assert mod.SharedPose.__name__ == "SharedPose"
            assert mod.pose_to_tuple.__name__ == "pose_to_tuple"
            assert mod.BuildTestPipeline.__name__ == "build_test_pipeline"
            assert mod.BuildTestPipelineFlow.__name__ == "build_test_pipeline_flow"

            flow = mod.TestFlow()
            out = flow.step(flow.input_type(value=4))
            assert out.value == 5

            pose = mod.SharedPose(x=1.0, y=2.0, z=3.0)
            assert mod.pose_to_tuple(pose) == (1.0, 2.0, 3.0)

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_with_version(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub
            result = hub.use("test-org/test-mod:TestFlow@0.9.0")
            assert result.__name__ == "TestFlow"

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_versions_do_not_alias_same_package_namespace(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            tar_by_sha = {
                "abc123def456789012345678901234567890abcd": _make_tarball(flow_delta=1),
                "older_sha_padding_to_fill_space_here_1234": _make_tarball(flow_delta=9),
            }

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    for sha, tarball in tar_by_sha.items():
                        if sha in url:
                            return tarball
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            Flow09 = hub.use("test-org/test-mod:TestFlow@0.9.0")
            Flow10 = hub.use("test-org/test-mod:TestFlow@1.0.0")

            assert Flow09 is not Flow10
            assert Flow09.__module__ != Flow10.__module__
            assert Flow09().step(Flow09().input_type(value=1)).value == 10
            assert Flow10().step(Flow10().input_type(value=1)).value == 2
            assert hub.use("test-org/test-mod:TestFlow@0.9.0") is Flow09

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_in_process_cache(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub
            result1 = hub.use("test-org/test-mod:TestFlow")
            # Second call should use in-process cache (still needs index + resolve)
            result2 = hub.use("test-org/test-mod:TestFlow")
            assert result1 is result2

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_type_and_transform(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            SharedPose = hub.use("test-org/test-mod:SharedPose")
            pose_to_tuple = hub.use("test-org/test-mod:pose_to_tuple")

            pose = SharedPose(x=1.0, y=2.0, z=3.0)
            assert pose_to_tuple(pose) == (1.0, 2.0, 3.0)

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_io_type_behaves_like_local_io(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            SharedPose = hub.use("test-org/test-mod:SharedPose")

            assert is_flow_io(SharedPose)
            assert get_flow_io_fields(SharedPose) == ["x", "y", "z"]
            assert get_flow_io_types(SharedPose) == {"x": float, "y": float, "z": float}

            pose = SharedPose(x=1.0, z=3.0)
            assert pose._signals == ["x", "z"]
            assert pose._has_signal("x") is True
            assert pose._has_signal("y") is False
            assert pose.y is None

            @io
            class PoseSummary:
                total: float

            class PoseReducer(Flow[SharedPose, PoseSummary]):
                def step(self, input: SharedPose) -> PoseSummary:
                    return PoseSummary(total=input.x + input.y + input.z)

            flow = PoseReducer()
            out = flow.step(SharedPose(x=1.0, y=2.0, z=3.0))
            assert out.total == 6.0

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_registered_type_is_discoverable(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import find_types, get_type, hub

            SharedPose = hub.use("test-org/test-mod:SharedPose")

            assert get_type("HubSharedPose") is SharedPose
            geometry_types = find_types(category="geometry", tags=["hub", "pose"])
            assert geometry_types["HubSharedPose"].type_class is SharedPose

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_transform_accepts_local_io_equivalent(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            pose_to_tuple = hub.use("test-org/test-mod:pose_to_tuple")

            @io
            class LocalPose:
                x: float
                y: float
                z: float

            local_pose = LocalPose(x=4.0, y=5.0, z=6.0)
            assert pose_to_tuple(local_pose) == (4.0, 5.0, 6.0)

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_explicit_exports_preserve_intra_package_type_identity(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            GreeterFlow = hub.use("test-org/test-mod:GreeterFlow")
            GreeterInput = hub.use("test-org/test-mod:GreeterInput")
            GreeterOutput = hub.use("test-org/test-mod:GreeterOutput")

            greeter = GreeterFlow(prefix="Hi")
            out = greeter.run(GreeterInput(name="Retriever"))

            assert greeter.input_type is GreeterInput
            assert greeter.output_type is GreeterOutput
            assert isinstance(out, GreeterOutput)
            assert out.greeting == "Hi, Retriever!"

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_factory_for_extension(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build = hub.use("test-org/test-mod:BuildTestPipeline")
            pipe = build()
            try:
                assert set(pipe.get_flow_dict()) == {"source", "processor"}

                pipe.replace(pipe.select_flow("processor"), OverrideProc(delta=100) @ Rate(hz=10))
                pipe.inject_input("processor", "bias", 3, timestamp=0.0)
                result = pipe.step(now=0.0)

                assert pipe.get_node_id(pipe.select_flow("processor")) == "processor"
                assert result.outputs["processor"].value == 104
            finally:
                pipe.close_stepper()

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_factory_preserves_baseline_behavior(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build = hub.use("test-org/test-mod:BuildTestPipeline")
            pipe = build()
            try:
                assert set(pipe.get_flow_dict()) == {"source", "processor"}
                pipe.inject_input("processor", "bias", 3, timestamp=0.0)
                result = pipe.step(now=0.0)

                assert result.outputs["source"].aux == 99
                assert result.outputs["processor"].value == 4
            finally:
                pipe.close_stepper()

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_factory_with_shared_type_transform(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            SharedPose = hub.use("test-org/test-mod:SharedPose")
            pose_to_tuple = hub.use("test-org/test-mod:pose_to_tuple")
            build = hub.use("test-org/test-mod:BuildTestPipeline")

            pipe = build()
            try:
                pipe.replace(pipe.select_flow("processor"), OverrideProc(delta=100) @ Rate(hz=10))

                pose = SharedPose(x=1.0, y=1.0, z=1.0)
                bias = int(sum(pose_to_tuple(pose)))
                pipe.inject_input("processor", "bias", bias, timestamp=0.0)

                result = pipe.step(now=0.0)

                assert result.outputs["processor"].value == 104
            finally:
                pipe.close_stepper()

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_flow_factory(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build_flow = hub.use("test-org/test-mod:BuildTestPipelineFlow")
            flow = build_flow()
            out1 = flow.step(flow.input_type(bias=4))
            out2 = flow.step(flow.input_type(bias=4))
            flow.finalize()

            assert set(flow.input_type.__dataclass_fields__.keys()) == {"bias"}
            assert set(flow.output_type.__dataclass_fields__.keys()) == {"aux", "value"}
            assert [port.external_name for port in flow.surface.inputs] == ["bias"]
            assert sorted(port.external_name for port in flow.surface.outputs) == ["aux", "value"]
            assert out1.value == 5
            assert out1.aux == 99
            assert out2.value == 6
            assert out2.aux == 99

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_flow_factory_can_compose_and_run_on_multiprocessing(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build_flow = hub.use("test-org/test-mod:BuildTestPipelineFlow")

            outer = Pipeline("hub_outer_pipeline")
            with outer:
                bias = (BiasSource(bias=4) @ Rate(hz=10)).named("bias")
                stage = (build_flow() @ Rate(hz=10)).named("stage")
                bias.then(stage, sync=Latest())

            ir = outer.validate()
            assert "stage" not in {node.id for node in ir.nodes}
            assert {"bias", "stage__source", "stage__processor"} <= {node.id for node in ir.nodes}
            assert any(
                edge.source.node == "bias"
                and edge.destination.node == "stage__processor"
                and edge.destination.port == "bias"
                for edge in ir.edges
            )

            outer.run(backend="multiprocessing", duration=0.05)

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_flow_factory_unlowered_ir_stays_backend_guarded(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build_flow = hub.use("test-org/test-mod:BuildTestPipelineFlow")

            outer = Pipeline("hub_outer_pipeline_guarded")
            with outer:
                bias = (BiasSource(bias=4) @ Rate(hz=10)).named("bias")
                stage = (build_flow() @ Rate(hz=10)).named("stage")
                bias.then(stage, sync=Latest())

            ir = outer.validate(lower_composite_flows=False)
            with pytest.raises(ValueError, match="stage"):
                execute_ir(ir, backend="multiprocessing", duration=0.01)

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_flow_factory_can_compose_multiple_instances(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build_flow = hub.use("test-org/test-mod:BuildTestPipelineFlow")

            outer = Pipeline("hub_outer_pipeline_multi_stage")
            with outer:
                left_bias = (BiasSource(bias=4) @ Rate(hz=10)).named("left_bias")
                right_bias = (BiasSource(bias=7) @ Rate(hz=10)).named("right_bias")
                left = (build_flow() @ Rate(hz=10)).named("left")
                right = (build_flow() @ Rate(hz=10)).named("right")
                left_bias.then(left, sync=Latest())
                right_bias.then(right, sync=Latest())

            ir = outer.validate()
            node_ids = {node.id for node in ir.nodes}
            assert "left" not in node_ids
            assert "right" not in node_ids
            assert {
                "left_bias",
                "right_bias",
                "left__source",
                "left__processor",
                "right__source",
                "right__processor",
            } <= node_ids

            result = outer.step(now=0.0)
            try:
                assert result.outputs["left"].value == 5
                assert result.outputs["left"].aux == 99
                assert result.outputs["right"].value == 8
                assert result.outputs["right"].aux == 99
            finally:
                outer.close_stepper()

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_use_exported_pipeline_flow_factory_builds_on_dora(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        pytest.importorskip("dora")
        from retriever.rt.backend.dora.engine import DoraEngine

        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build_flow = hub.use("test-org/test-mod:BuildTestPipelineFlow")

            outer = Pipeline("hub_outer_pipeline_dora")
            with outer:
                bias = (BiasSource(bias=4) @ Rate(hz=10)).named("bias")
                stage = (build_flow() @ Rate(hz=10)).named("stage")
                bias.then(stage, sync=Latest())

            ir = outer.validate()
            engine = DoraEngine(ir)
            engine.build()
            try:
                executor_ids = {ex.flow_node.id for ex in engine.executors if ex.flow_node is not None}
                assert "stage" not in executor_ids
                assert {"bias", "stage__source", "stage__processor"} <= executor_ids
            finally:
                engine.stop()

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_hub_loaded_ir_nodes_can_recover_after_module_unload(
        self, mock_request, mock_cache_root, tmp_path: Path
    ):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub

            build = hub.use("test-org/test-mod:BuildTestPipeline")
            pipe = build()
            ir = pipe.validate()
            source_node = next(node for node in ir.nodes if node.id == "source")

            for key in list(sys.modules):
                if "test_mod" in key or "_retriever_hub" in key:
                    del sys.modules[key]

            flow = instantiate_flow_from_node(source_node)
            initialize_flow_runtime(flow)
            out = flow.step(None)

            assert out.value == 1
            assert out.aux == 99


class TestHubUseErrors:
    def test_invalid_ref(self):
        from retriever import hub
        with pytest.raises(HubError) as exc_info:
            hub.use("bad-ref")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF

    @patch("retriever.hub._http._do_request")
    def test_module_not_found(self, mock_request):
        mock_request.side_effect = HubError(
            ErrCode.HUB_MODULE_NOT_FOUND, "Resource not found"
        )
        from retriever import hub
        with pytest.raises(HubError) as exc_info:
            hub.use("no-org/no-mod")
        assert exc_info.value.code == ErrCode.HUB_MODULE_NOT_FOUND

    @patch("retriever.hub._http._do_request")
    def test_no_semver_tags(self, mock_request):
        import json

        def side_effect(url):
            if "raw.githubusercontent.com" in url:
                return _INDEX_TOML.encode()
            elif "api.github.com" in url:
                # Return tags with no semver
                return json.dumps([
                    {"name": "not-semver", "commit": {"sha": "abc123"}},
                ]).encode()
            raise ValueError(f"Unexpected URL: {url}")

        mock_request.side_effect = side_effect

        from retriever import hub
        with pytest.raises(HubError) as exc_info:
            hub.use("test-org/test-mod")
        assert exc_info.value.code == ErrCode.HUB_NO_SEMVER_TAGS

    @patch("retriever.hub._http._do_request")
    def test_version_not_found(self, mock_request):
        import json

        def side_effect(url):
            if "raw.githubusercontent.com" in url:
                return _INDEX_TOML.encode()
            elif "api.github.com" in url:
                return json.dumps(_TAGS_JSON).encode()
            raise ValueError(f"Unexpected URL: {url}")

        mock_request.side_effect = side_effect

        from retriever import hub
        with pytest.raises(HubError) as exc_info:
            hub.use("test-org/test-mod@99.0.0")
        assert exc_info.value.code == ErrCode.HUB_VERSION_NOT_FOUND

    @patch("retriever.hub._cache._CACHE_ROOT")
    @patch("retriever.hub._http._do_request")
    def test_export_not_found(self, mock_request, mock_cache_root, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            import json

            def side_effect(url):
                if "raw.githubusercontent.com" in url:
                    return _INDEX_TOML.encode()
                elif "api.github.com" in url:
                    return json.dumps(_TAGS_JSON).encode()
                elif "archive" in url:
                    return _make_tarball()
                raise ValueError(f"Unexpected URL: {url}")

            mock_request.side_effect = side_effect

            from retriever import hub
            with pytest.raises(HubError) as exc_info:
                hub.use("test-org/test-mod:NoSuchExport")
            assert exc_info.value.code == ErrCode.HUB_EXPORT_NOT_FOUND
