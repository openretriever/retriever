"""End-to-end tests for hub.use() with mocked HTTP."""

import io as pyio
import tarfile
import pytest
from pathlib import Path
from unittest.mock import patch
import sys

from retriever.error import ErrCode, HubError
from retriever.hub._loader import ModuleProxy
from retriever.flow import Flow, Rate, io


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


def _make_tarball() -> bytes:
    return _build_tarball({
        "pyproject.toml": _PYPROJECT_TOML,
        "test_mod/__init__.py": "",
        "test_mod/flow.py": "class TestFlow:\n    name = 'test'\n",
        "test_mod/config.py": "class TestConfig:\n    pass\n",
        "test_mod/types.py": """from retriever.flow import io


@io
class SharedPose:
    x: float
    y: float
    z: float
""",
        "test_mod/transforms.py": """def pose_to_tuple(pose):
    return (pose.x, pose.y, pose.z)
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
            out = flow.step(flow.input_type(bias=4))
            flow.finalize()

            assert out.value == 5
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
