"""End-to-end tests for hub.use() with mocked HTTP."""

import io
import tarfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from retriever.error import ErrCode, HubError
from retriever.hub._loader import ModuleProxy


def _build_tarball(files: dict[str, str], top_dir: str = "repo-sha123") -> bytes:
    """Build an in-memory tarball.

    Args:
        files: {relative_path: content} — paths relative to top_dir.
        top_dir: Top-level directory name in the archive.

    Returns:
        gzipped tar bytes.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel_path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"{top_dir}/{rel_path}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
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
