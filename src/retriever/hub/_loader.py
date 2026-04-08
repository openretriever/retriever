"""Isolated importlib loader and ModuleProxy."""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional

from retriever.error import ErrCode, HubError
from retriever.hub._ref import ModuleRef

_HUB_NS = "_retriever_hub"


def _ensure_namespace() -> None:
    """Ensure the _retriever_hub namespace package exists in sys.modules."""
    if _HUB_NS not in sys.modules:
        ns = types.ModuleType(_HUB_NS)
        ns.__path__ = []  # type: ignore[attr-defined]
        ns.__package__ = _HUB_NS
        sys.modules[_HUB_NS] = ns


def _sanitize_namespace(namespace: str) -> str:
    sanitized = re.sub(r"[^0-9A-Za-z_]+", "_", namespace).strip("_")
    if not sanitized:
        return "module"
    if sanitized[0].isdigit():
        return f"n_{sanitized}"
    return sanitized


def _qualified_root(module_name: str, namespace: Optional[str]) -> str:
    if not namespace:
        return f"{_HUB_NS}.{module_name}"
    return f"{_HUB_NS}.{_sanitize_namespace(namespace)}__{module_name}"


def _evict_stale_bare_aliases(module_name: str) -> None:
    prefix = f"{module_name}."
    for key, mod in list(sys.modules.items()):
        if key != module_name and not key.startswith(prefix):
            continue
        mod_name = getattr(mod, "__name__", "")
        if isinstance(mod_name, str) and mod_name.startswith(f"{_HUB_NS}."):
            sys.modules.pop(key, None)


def _attach_hub_metadata(
    module: types.ModuleType,
    *,
    module_name: str,
    source_module: str,
    namespace: Optional[str],
    hub_meta: Optional[Dict[str, Any]],
) -> None:
    if hub_meta is None:
        return
    module.__retriever_hub__ = {
        **hub_meta,
        "module_name": module_name,
        "namespace": namespace,
        "source_module": source_module,
    }


def _load_package(
    module_root: Path,
    module_name: str,
    *,
    namespace: Optional[str] = None,
    hub_meta: Optional[Dict[str, Any]] = None,
) -> types.ModuleType:
    """Load a Python package from module_root without modifying sys.path.

    The package is registered under '_retriever_hub.{module_name}' in sys.modules
    to avoid collisions. It is also registered under the bare '{module_name}' so
    that intra-package absolute imports work.
    """
    _ensure_namespace()

    pkg_dir = module_root / module_name
    init_path = pkg_dir / "__init__.py"

    if not pkg_dir.is_dir():
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Package directory '{module_name}' not found at {module_root}",
        )

    # A package without __init__.py — treat as namespace package
    qualified = _qualified_root(module_name, namespace)

    if qualified in sys.modules:
        return sys.modules[qualified]

    _evict_stale_bare_aliases(module_name)

    if init_path.exists():
        spec = importlib.util.spec_from_file_location(
            qualified,
            str(init_path),
            submodule_search_locations=[str(pkg_dir)],
        )
    else:
        # Namespace package (no __init__.py)
        spec = importlib.util.spec_from_file_location(
            qualified,
            None,
            submodule_search_locations=[str(pkg_dir)],
        )

    if spec is None:
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Could not create import spec for '{module_name}'",
        )

    module = importlib.util.module_from_spec(spec)
    module.__package__ = qualified
    module.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]
    _attach_hub_metadata(
        module,
        module_name=module_name,
        source_module=module_name,
        namespace=namespace,
        hub_meta=hub_meta,
    )

    # Register before exec so relative imports inside __init__.py work
    sys.modules[qualified] = module
    sys.modules[module_name] = module

    if spec.loader is not None:
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            # Clean up on failure
            sys.modules.pop(qualified, None)
            sys.modules.pop(module_name, None)
            raise HubError(
                ErrCode.HUB_IMPORT_FAILED,
                f"Failed to import '{module_name}': {exc}",
            ) from exc

    return module


def _import_submodule(
    module_root: Path,
    module_name: str,
    dotted_path: str,
    *,
    namespace: Optional[str] = None,
    hub_meta: Optional[Dict[str, Any]] = None,
) -> types.ModuleType:
    """Import a submodule like 'lidar_slam.flow'."""
    _ensure_namespace()

    if dotted_path == module_name:
        return _load_package(
            module_root,
            module_name,
            namespace=namespace,
            hub_meta=hub_meta,
        )

    qualified_root = _qualified_root(module_name, namespace)
    parts = dotted_path.split(".")
    if not parts or parts[0] != module_name:
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Export module '{dotted_path}' must be inside package '{module_name}'",
        )

    relative_parts = parts[1:]
    qualified = f"{qualified_root}.{'.'.join(relative_parts)}"
    if qualified in sys.modules:
        return sys.modules[qualified]

    # Build file path
    rel_path = Path(*parts)
    file_path = module_root / (str(rel_path) + ".py")
    if not file_path.exists():
        # Try as sub-package
        file_path = module_root / rel_path / "__init__.py"

    if not file_path.exists():
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Cannot find module file for '{dotted_path}' at {module_root}",
        )

    spec = importlib.util.spec_from_file_location(qualified, str(file_path))
    if spec is None or spec.loader is None:
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Could not create import spec for '{dotted_path}'",
        )

    submod = importlib.util.module_from_spec(spec)
    parent_relative = ".".join(relative_parts[:-1])
    submod.__package__ = (
        f"{qualified_root}.{parent_relative}" if parent_relative else qualified_root
    )
    _attach_hub_metadata(
        submod,
        module_name=module_name,
        source_module=dotted_path,
        namespace=namespace,
        hub_meta=hub_meta,
    )

    sys.modules[qualified] = submod
    sys.modules[dotted_path] = submod

    # Wire into parent module
    if relative_parts:
        parent_qualified = (
            f"{qualified_root}.{parent_relative}" if parent_relative else qualified_root
        )
        parent = sys.modules.get(parent_qualified)
        if parent is not None:
            setattr(parent, parts[-1], submod)

    try:
        spec.loader.exec_module(submod)
    except Exception as exc:
        sys.modules.pop(qualified, None)
        sys.modules.pop(dotted_path, None)
        raise HubError(
            ErrCode.HUB_IMPORT_FAILED,
            f"Failed to import '{dotted_path}': {exc}",
        ) from exc

    return submod


def _resolve_export(
    module_root: Path,
    module_name: str,
    export_path: str,
    *,
    namespace: Optional[str] = None,
    hub_meta: Optional[Dict[str, Any]] = None,
) -> Any:
    """Resolve an export path like 'lidar_slam.flow:LidarSlamFlow'."""
    module_path, _, attr_name = export_path.partition(":")
    if not attr_name:
        raise HubError(
            ErrCode.HUB_PYPROJECT_INVALID,
            f"Export path '{export_path}' must contain ':' separator "
            "(e.g. 'pkg.module:ClassName')",
        )

    submod = _import_submodule(
        module_root,
        module_name,
        module_path,
        namespace=namespace,
        hub_meta=hub_meta,
    )
    try:
        return getattr(submod, attr_name)
    except AttributeError:
        raise HubError(
            ErrCode.HUB_EXPORT_NOT_FOUND,
            f"Module '{module_path}' has no attribute '{attr_name}'",
        )


def load_exports(
    module_root: Path,
    module_name: str,
    exports: Dict[str, str],
    *,
    namespace: Optional[str] = None,
    hub_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load all declared exports from a module.

    Args:
        module_root: Path containing the package.
        module_name: Python package name (e.g. 'lidar_slam').
        exports: {export_name: 'dotted.module:Attribute'} from pyproject.toml.

    Returns:
        {export_name: actual_object}
    """
    # Ensure the top-level package is loaded first
    _load_package(
        module_root,
        module_name,
        namespace=namespace,
        hub_meta=hub_meta,
    )

    result: Dict[str, Any] = {}
    for export_name, export_path in exports.items():
        result[export_name] = _resolve_export(
            module_root,
            module_name,
            export_path,
            namespace=namespace,
            hub_meta=hub_meta,
        )
    return result


def ensure_module_loaded(
    module_root: Path,
    module_name: str,
    dotted_path: str,
    *,
    namespace: Optional[str] = None,
    hub_meta: Optional[Dict[str, Any]] = None,
) -> types.ModuleType:
    """Ensure one package/submodule is loaded under the hub namespace."""
    _load_package(
        module_root,
        module_name,
        namespace=namespace,
        hub_meta=hub_meta,
    )
    return _import_submodule(
        module_root,
        module_name,
        dotted_path,
        namespace=namespace,
        hub_meta=hub_meta,
    )


class ModuleProxy:
    """Namespace proxy for whole-package hub.use() (no :attribute).

    Provides attribute access to the module's declared exports.
    """

    def __init__(self, exports: Dict[str, Any], ref: ModuleRef) -> None:
        self._exports = exports
        self._ref = ref

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._exports[name]
        except KeyError:
            raise AttributeError(
                f"Module '{self._ref.org}/{self._ref.name}' has no export '{name}'. "
                f"Available exports: {list(self._exports.keys())}"
            )

    def __dir__(self) -> list[str]:
        return list(self._exports.keys())

    def __repr__(self) -> str:
        return (
            f"<HubModule '{self._ref.org}/{self._ref.name}' "
            f"exports={list(self._exports.keys())}>"
        )
