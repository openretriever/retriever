"""Version and dependency validation."""

from __future__ import annotations

import tomllib
import warnings
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


def _runtime_distributions() -> set[str]:
    """Distribution names that provide the already-imported `retriever` package.

    A consumer calling `hub.use(...)` is, by definition, already running
    retriever. So a module listing the retriever runtime among its dependencies
    must never be re-required here.
    """
    names = {"retriever-core", "retriever"}
    try:
        from importlib.metadata import packages_distributions

        names.update(packages_distributions().get("retriever", []))
    except Exception:
        pass
    return {n.lower().replace("_", "-") for n in names}


def check_dependencies(dependencies: list[str], *, strict: bool = False) -> None:
    """Check that a module's declared dependencies are installed.

    This is advisory by default: consuming a single lightweight export should not
    require a pack's full (possibly heavy) dependency set, so missing or
    version-mismatched dependencies emit one warning and loading proceeds. If an
    export actually needs a missing package, importing it raises a normal
    ImportError. The retriever runtime is always skipped (see
    `_runtime_distributions`). Pass ``strict=True`` to raise instead of warn.
    """
    runtime = _runtime_distributions()
    problems: list[str] = []
    for dep_str in dependencies:
        req = Requirement(dep_str)

        # Skip environment-marked deps and the retriever runtime self-reference.
        if req.marker is not None:
            continue
        if req.name.lower().replace("_", "-") in runtime:
            continue

        try:
            installed_version = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            problems.append(f"'{req.name}' is not installed (pip install '{dep_str}')")
            continue

        if req.specifier and not req.specifier.contains(installed_version):
            problems.append(f"'{req.name}=={installed_version}' does not satisfy '{dep_str}'")

    if not problems:
        return

    detail = "\n  - ".join(problems)
    if strict:
        raise HubError(
            ErrCode.HUB_DEPENDENCY_MISSING,
            f"Module dependencies are not satisfied:\n  - {detail}",
        )
    warnings.warn(
        "Retriever Hub module has unmet optional dependencies; loading anyway. "
        "Install these if the module errors:\n  - " + detail,
        stacklevel=2,
    )
