"""Tests for hub isolated import loader."""

import sys
import pytest
from pathlib import Path

from retriever.hub._loader import ModuleProxy, _HUB_NS, load_exports
from retriever.hub._ref import ModuleRef


def _create_package(tmp_path: Path, pkg_name: str, files: dict[str, str]) -> Path:
    """Create a minimal Python package in tmp_path.

    Args:
        tmp_path: Root directory.
        pkg_name: Package name (directory name).
        files: {relative_path: content} within the package dir.

    Returns:
        The module root (tmp_path itself).
    """
    pkg_dir = tmp_path / pkg_name
    pkg_dir.mkdir()
    for rel_path, content in files.items():
        file_path = pkg_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    return tmp_path


class TestLoadExports:
    def test_load_simple_export(self, tmp_path: Path):
        module_root = _create_package(tmp_path, "test_pkg", {
            "__init__.py": "",
            "flow.py": "class TestFlow:\n    pass\n",
        })
        exports = load_exports(
            module_root, "test_pkg", {"TestFlow": "test_pkg.flow:TestFlow"}
        )
        assert "TestFlow" in exports
        assert exports["TestFlow"].__name__ == "TestFlow"

        # Cleanup sys.modules
        for key in list(sys.modules):
            if "test_pkg" in key:
                del sys.modules[key]

    def test_load_multiple_exports(self, tmp_path: Path):
        module_root = _create_package(tmp_path, "multi_pkg", {
            "__init__.py": "",
            "flow.py": "class FlowA:\n    pass\n\nclass FlowB:\n    pass\n",
            "config.py": "class Config:\n    pass\n",
        })
        exports = load_exports(module_root, "multi_pkg", {
            "FlowA": "multi_pkg.flow:FlowA",
            "FlowB": "multi_pkg.flow:FlowB",
            "Config": "multi_pkg.config:Config",
        })
        assert len(exports) == 3
        assert exports["FlowA"].__name__ == "FlowA"
        assert exports["Config"].__name__ == "Config"

        for key in list(sys.modules):
            if "multi_pkg" in key:
                del sys.modules[key]

    def test_intra_package_import(self, tmp_path: Path):
        module_root = _create_package(tmp_path, "intra_pkg", {
            "__init__.py": "",
            "config.py": "VALUE = 42\n",
            "flow.py": "from intra_pkg.config import VALUE\n\nclass MyFlow:\n    val = VALUE\n",
        })
        exports = load_exports(
            module_root, "intra_pkg", {"MyFlow": "intra_pkg.flow:MyFlow"}
        )
        assert exports["MyFlow"].val == 42

        for key in list(sys.modules):
            if "intra_pkg" in key:
                del sys.modules[key]

    def test_relative_import(self, tmp_path: Path):
        module_root = _create_package(tmp_path, "rel_pkg", {
            "__init__.py": "",
            "config.py": "VALUE = 99\n",
            "flow.py": "from . import config\n\nclass RelFlow:\n    val = config.VALUE\n",
        })
        exports = load_exports(
            module_root, "rel_pkg", {"RelFlow": "rel_pkg.flow:RelFlow"}
        )
        assert exports["RelFlow"].val == 99

        for key in list(sys.modules):
            if "rel_pkg" in key:
                del sys.modules[key]

    def test_sys_path_unchanged(self, tmp_path: Path):
        original_path = sys.path.copy()
        module_root = _create_package(tmp_path, "path_pkg", {
            "__init__.py": "",
            "flow.py": "class F:\n    pass\n",
        })
        load_exports(module_root, "path_pkg", {"F": "path_pkg.flow:F"})
        assert sys.path == original_path

        for key in list(sys.modules):
            if "path_pkg" in key:
                del sys.modules[key]


class TestModuleProxy:
    def test_attribute_access(self):
        proxy = ModuleProxy(
            {"FlowA": "obj_a", "FlowB": "obj_b"},
            ModuleRef(org="org", name="mod"),
        )
        assert proxy.FlowA == "obj_a"
        assert proxy.FlowB == "obj_b"

    def test_missing_attribute(self):
        proxy = ModuleProxy(
            {"FlowA": "obj_a"},
            ModuleRef(org="org", name="mod"),
        )
        with pytest.raises(AttributeError, match="NoSuch"):
            proxy.NoSuch

    def test_dir(self):
        proxy = ModuleProxy(
            {"FlowA": "a", "Config": "b"},
            ModuleRef(org="org", name="mod"),
        )
        assert set(dir(proxy)) == {"FlowA", "Config"}

    def test_repr(self):
        proxy = ModuleProxy(
            {"FlowA": "a"},
            ModuleRef(org="company", name="slam"),
        )
        r = repr(proxy)
        assert "company/slam" in r
        assert "FlowA" in r


class TestSrcLayout:
    def test_load_exports_from_src_layout(self, tmp_path: Path):
        """Packages under the standard src/ layout resolve like flat ones."""
        pkg_dir = tmp_path / "src" / "src_pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "types.py").write_text("class Pose:\n    frame = 'map'\n")
        (pkg_dir / "deep").mkdir()
        (pkg_dir / "deep" / "__init__.py").write_text("")
        (pkg_dir / "deep" / "flow.py").write_text("class DeepFlow:\n    pass\n")

        exports = load_exports(tmp_path, "src_pkg", {
            "Pose": "src_pkg.types:Pose",
            "DeepFlow": "src_pkg.deep.flow:DeepFlow",
        })
        assert exports["Pose"].frame == "map"
        assert exports["DeepFlow"].__name__ == "DeepFlow"

        for key in list(sys.modules):
            if "src_pkg" in key:
                del sys.modules[key]

    def test_missing_package_error_mentions_src(self, tmp_path: Path):
        from retriever.error import HubError

        with pytest.raises(HubError) as excinfo:
            load_exports(tmp_path, "ghost_pkg", {"X": "ghost_pkg.mod:X"})
        assert "src/" in str(excinfo.value)
