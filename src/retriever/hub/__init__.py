"""
Retriever Hub - Dynamically load modules from Git repositories.

Usage::

    from retriever import hub

    # Load a specific export
    LidarSlam = hub.use("company-abc/lidar-slam:LidarSlamFlow")
    slam = LidarSlam(resolution=0.05) @ Rate(hz=10)

    # Load a whole package
    lidar = hub.use("company-abc/lidar-slam")
    slam = lidar.LidarSlamFlow(resolution=0.05) @ Rate(hz=10)

    # With version
    LidarSlam = hub.use("company-abc/lidar-slam:LidarSlamFlow@0.1.0")

Environment variables:
    RETRIEVER_HUB_INDEX_URL: Override the default hub index URL.
    RETRIEVER_HUB_TOKEN: GitHub token for accessing private repositories.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from retriever.error import ErrCode, HubError
from retriever.hub._cache import (
    cache_dir_for,
    clear_cache as _clear_disk_cache,
    get_cached_module_root,
    is_cached,
    mark_cached,
)
from retriever.hub._check import (
    check_dependencies,
    check_min_retriever_version,
    read_module_metadata,
)
from retriever.hub._fetch import download_and_extract
from retriever.hub._index import lookup_module, parse_github_url
from retriever.hub._loader import ModuleProxy, load_exports, unload_namespace
from retriever.hub._ref import ModuleRef, parse_ref
from retriever.hub._resolve import resolve_version

logger = logging.getLogger(__name__)

# In-process cache: {(org, name, commit_sha): loaded_exports_dict}
_loaded: Dict[Tuple[str, str, str], Dict[str, Any]] = {}


def use(ref: str, *, refresh: bool = False) -> Any:
    """Load a module (or specific export) from the Retriever Hub.

    Args:
        ref: Module reference string: '{org}/{name}[:{attribute}][@{version}]'
        refresh: If True, re-fetch even if cached locally.

    Returns:
        If :attribute is specified: the specific exported object.
        If no :attribute: a ModuleProxy with all exports as attributes.

    Raises:
        HubError: On any failure (see error codes 5000-5099).
    """
    # 1. Parse reference
    parsed = parse_ref(ref)

    # 2. Look up in index
    entry = lookup_module(parsed.org, parsed.name)
    owner, repo = parse_github_url(entry.repo_url)

    # 3. Resolve version -> commit SHA
    tag_name, commit_sha = resolve_version(owner, repo, parsed.version)

    # 4. Check in-process cache
    cache_key = (parsed.org, parsed.name, commit_sha)
    if not refresh and cache_key in _loaded:
        return _return(_loaded[cache_key], parsed)

    # 5. Check disk cache or download
    if refresh:
        _loaded.pop(cache_key, None)

    if not refresh and is_cached(parsed.org, parsed.name, commit_sha):
        module_root = get_cached_module_root(parsed.org, parsed.name, commit_sha)
    else:
        dest = cache_dir_for(parsed.org, parsed.name, commit_sha)
        module_root = download_and_extract(owner, repo, commit_sha, dest, replace=refresh)
        mark_cached(parsed.org, parsed.name, commit_sha)

    # 6. Read and validate metadata
    rtv_config, proj_config = read_module_metadata(module_root)

    # 7. Check min_retriever_version
    min_ver = rtv_config.get("min_retriever_version")
    if min_ver:
        check_min_retriever_version(min_ver)

    # 8. Check dependencies
    deps = proj_config.get("dependencies", [])
    if deps:
        check_dependencies(deps)

    # 9. Load exports
    module_name = rtv_config["module"]
    export_table = rtv_config.get("exports", {})
    namespace = f"{parsed.org}_{parsed.name}_{commit_sha[:12]}"
    if refresh:
        unload_namespace(module_name, namespace)
    exports = load_exports(
        module_root,
        module_name,
        export_table,
        namespace=namespace,
        hub_meta={
            "org": parsed.org,
            "name": parsed.name,
            "commit": commit_sha,
        },
    )

    # 10. Cache in process
    _loaded[cache_key] = exports

    logger.info(
        "Loaded hub module %s/%s@%s (commit %s)",
        parsed.org, parsed.name, tag_name, commit_sha[:12],
    )

    return _return(exports, parsed)


def _return(exports: Dict[str, Any], parsed: ModuleRef) -> Any:
    """Return either a specific export or a ModuleProxy."""
    if parsed.attribute:
        if parsed.attribute not in exports:
            available = list(exports.keys())
            raise HubError(
                ErrCode.HUB_EXPORT_NOT_FOUND,
                f"Export '{parsed.attribute}' not found in module "
                f"'{parsed.org}/{parsed.name}'. "
                f"Available exports: {available}",
            )
        return exports[parsed.attribute]
    return ModuleProxy(exports, parsed)


def clear_cache(org: Optional[str] = None, name: Optional[str] = None) -> int:
    """Clear hub cache (both disk and in-process).

    Args:
        org: If provided, only clear modules for this org.
        name: If provided (with org), only clear this specific module.

    Returns:
        Number of cached versions removed from disk.
    """
    # Clear in-process cache
    if org is None:
        _loaded.clear()
    else:
        keys_to_remove = [
            k for k in _loaded
            if k[0] == org and (name is None or k[1] == name)
        ]
        for k in keys_to_remove:
            del _loaded[k]

    return _clear_disk_cache(org=org, name=name)
