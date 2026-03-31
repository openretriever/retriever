"""Disk cache management for hub modules."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_ROOT = Path.home() / ".retriever" / "hub" / "cache"
_MARKER = ".retriever_cached"


def cache_dir_for(org: str, name: str, commit_sha: str) -> Path:
    """Return the cache directory path for a specific module@commit."""
    return _CACHE_ROOT / org / name / commit_sha


def is_cached(org: str, name: str, commit_sha: str) -> bool:
    """Check if a module version is cached and has a valid marker."""
    d = cache_dir_for(org, name, commit_sha)
    return (d / _MARKER).exists()


def get_cached_module_root(org: str, name: str, commit_sha: str) -> Path:
    """Return path to cached module root."""
    return cache_dir_for(org, name, commit_sha)


def mark_cached(org: str, name: str, commit_sha: str) -> None:
    """Write marker file after successful extraction."""
    marker = cache_dir_for(org, name, commit_sha) / _MARKER
    marker.touch()


def clear_cache(org: str | None = None, name: str | None = None) -> int:
    """Clear cached modules. Returns number of entries removed.

    - clear_cache() removes everything
    - clear_cache(org="x") removes all modules for that org
    - clear_cache(org="x", name="y") removes that specific module (all versions)
    """
    if org is None:
        target = _CACHE_ROOT
    elif name is None:
        target = _CACHE_ROOT / org
    else:
        target = _CACHE_ROOT / org / name

    if not target.exists():
        return 0

    # Count leaf directories (commit SHA dirs)
    count = 0
    if org is None:
        for org_dir in target.iterdir():
            if org_dir.is_dir():
                for name_dir in org_dir.iterdir():
                    if name_dir.is_dir():
                        count += sum(1 for d in name_dir.iterdir() if d.is_dir())
    elif name is None:
        for name_dir in target.iterdir():
            if name_dir.is_dir():
                count += sum(1 for d in name_dir.iterdir() if d.is_dir())
    else:
        count = sum(1 for d in target.iterdir() if d.is_dir())

    shutil.rmtree(target)
    return count
