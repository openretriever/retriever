"""Version and dependency validation."""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.version import Version

import retriever
from retriever.error import ErrCode, HubError


def read_module_metadata(module_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read pyproject.toml and return (retriever_module_config, project_config).

    retriever_module_config is pyproject['tool']['retriever']['module'].
    project_config is pyproject.get('project', {}).
    """
    pyproject_path = module_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise HubError(
            ErrCode.HUB_PYPROJECT_MISSING,
            f"Module at {module_root} is missing pyproject.toml",
        )
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    try:
        rtv_config = data["tool"]["retriever"]["module"]
    except KeyError:
        raise HubError(
            ErrCode.HUB_PYPROJECT_INVALID,
            f"pyproject.toml is missing [tool.retriever.module] section",
        )
    return rtv_config, data.get("project", {})


def check_min_retriever_version(required: str) -> None:
    """Check that running retriever version satisfies >= required."""
    current = Version(retriever.__version__)
    minimum = Version(required)
    if current < minimum:
        raise HubError(
            ErrCode.HUB_MIN_VERSION_MISMATCH,
            f"Module requires retriever>={required}, but you have "
            f"retriever=={retriever.__version__}. "
            f"Please upgrade: pip install --upgrade retriever-core",
        )


def check_dependencies(dependencies: list[str]) -> None:
    """Check that all PEP 508 dependencies are installed and version-compatible.

    Skips extras and environment markers for now.
    """
    for dep_str in dependencies:
        req = Requirement(dep_str)

        # Skip deps with environment markers
        if req.marker is not None:
            continue

        try:
            installed_version = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            raise HubError(
                ErrCode.HUB_DEPENDENCY_MISSING,
                f"Required package '{req.name}' is not installed. "
                f"Install it with: pip install '{dep_str}'",
            )

        if req.specifier and not req.specifier.contains(installed_version):
            raise HubError(
                ErrCode.HUB_DEPENDENCY_VERSION,
                f"Requires '{dep_str}' but you have "
                f"{req.name}=={installed_version}",
            )
