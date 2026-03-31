"""Tests for hub version and dependency validation."""

import pytest
from pathlib import Path
from unittest.mock import patch

from retriever.error import ErrCode, HubError
from retriever.hub._check import (
    check_dependencies,
    check_min_retriever_version,
    read_module_metadata,
)


class TestReadModuleMetadata:
    def test_valid_pyproject(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = ["numpy"]\n\n'
            '[tool.retriever.module]\nmodule = "test_mod"\n'
            'min_retriever_version = "1.0.0"\n\n'
            '[tool.retriever.module.exports]\n'
            'TestFlow = "test_mod.flow:TestFlow"\n'
        )
        rtv, proj = read_module_metadata(tmp_path)
        assert rtv["module"] == "test_mod"
        assert rtv["min_retriever_version"] == "1.0.0"
        assert rtv["exports"]["TestFlow"] == "test_mod.flow:TestFlow"
        assert proj["dependencies"] == ["numpy"]

    def test_missing_pyproject(self, tmp_path: Path):
        with pytest.raises(HubError) as exc_info:
            read_module_metadata(tmp_path)
        assert exc_info.value.code == ErrCode.HUB_PYPROJECT_MISSING

    def test_missing_retriever_section(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')
        with pytest.raises(HubError) as exc_info:
            read_module_metadata(tmp_path)
        assert exc_info.value.code == ErrCode.HUB_PYPROJECT_INVALID


class TestCheckMinRetrieverVersion:
    @patch("retriever.hub._check.retriever")
    def test_version_satisfied(self, mock_retriever):
        mock_retriever.__version__ = "2.0.0"
        # Should not raise
        check_min_retriever_version("1.0.0")

    @patch("retriever.hub._check.retriever")
    def test_version_equal(self, mock_retriever):
        mock_retriever.__version__ = "1.0.0"
        # Should not raise
        check_min_retriever_version("1.0.0")

    @patch("retriever.hub._check.retriever")
    def test_version_too_old(self, mock_retriever):
        mock_retriever.__version__ = "0.5.0"
        with pytest.raises(HubError) as exc_info:
            check_min_retriever_version("1.0.0")
        assert exc_info.value.code == ErrCode.HUB_MIN_VERSION_MISMATCH
        assert "retriever>=1.0.0" in exc_info.value.message


class TestCheckDependencies:
    @patch("retriever.hub._check.metadata")
    def test_all_satisfied(self, mock_metadata):
        mock_metadata.version.return_value = "1.26.0"
        mock_metadata.PackageNotFoundError = Exception
        # Should not raise
        check_dependencies(["numpy>=1.24,<2"])

    @patch("retriever.hub._check.metadata")
    def test_missing_package(self, mock_metadata):
        from importlib.metadata import PackageNotFoundError
        mock_metadata.PackageNotFoundError = PackageNotFoundError
        mock_metadata.version.side_effect = PackageNotFoundError("nonexistent-pkg")
        with pytest.raises(HubError) as exc_info:
            check_dependencies(["nonexistent-pkg"])
        assert exc_info.value.code == ErrCode.HUB_DEPENDENCY_MISSING
        assert "nonexistent-pkg" in exc_info.value.message

    @patch("retriever.hub._check.metadata")
    def test_version_mismatch(self, mock_metadata):
        mock_metadata.version.return_value = "1.23.0"
        mock_metadata.PackageNotFoundError = Exception
        with pytest.raises(HubError) as exc_info:
            check_dependencies(["numpy>=1.24,<2"])
        assert exc_info.value.code == ErrCode.HUB_DEPENDENCY_VERSION
        assert "1.23.0" in exc_info.value.message

    @patch("retriever.hub._check.metadata")
    def test_skips_markers(self, mock_metadata):
        mock_metadata.PackageNotFoundError = Exception
        # Should not raise (marker should be skipped)
        check_dependencies(['pywin32; sys_platform == "win32"'])
        mock_metadata.version.assert_not_called()

    @patch("retriever.hub._check.metadata")
    def test_no_specifier(self, mock_metadata):
        mock_metadata.version.return_value = "0.1.0"
        mock_metadata.PackageNotFoundError = Exception
        # Bare dep with no version specifier — should pass if installed
        check_dependencies(["requests"])
