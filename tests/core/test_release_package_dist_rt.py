import importlib.util
from pathlib import Path


def _load_package_dist_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "release" / "package_dist.py"
    spec = importlib.util.spec_from_file_location("package_dist", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_bundle_ignores_generated_local_artifacts():
    module = _load_package_dist_module()

    ignored = module._ignore_generated_artifacts(
        "examples/tutorial",
        [
            "__pycache__",
            "01_basic_flow.py",
            "frame.mcap",
            "session.rrd",
            "logs",
            "out",
            "keep.md",
        ],
    )

    assert ignored == {"__pycache__", "frame.mcap", "session.rrd", "logs", "out"}
