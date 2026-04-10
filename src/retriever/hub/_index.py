"""Hub index lookup."""

from __future__ import annotations

import os
import re
try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib
from dataclasses import dataclass, field
from typing import List

from retriever.error import ErrCode, HubError
from retriever.hub._http import fetch_text

_DEFAULT_INDEX_RAW_URL = (
    "https://raw.githubusercontent.com/openretriever/hub-index/main"
)


@dataclass(frozen=True)
class IndexEntry:
    """Parsed module entry from the hub index."""

    repo_url: str
    description: str = ""
    author: str = ""
    license: str = ""
    tags: List[str] = field(default_factory=list)


def _get_index_url() -> str:
    return os.environ.get("RETRIEVER_HUB_INDEX_URL", _DEFAULT_INDEX_RAW_URL)


def lookup_module(org: str, name: str) -> IndexEntry:
    """Fetch and parse a module entry from the hub index.

    Raises HubError(HUB_MODULE_NOT_FOUND) if the module is not in the index.
    """
    index_url = _get_index_url().rstrip("/")
    url = f"{index_url}/modules/{org}/{name}.toml"
    text = fetch_text(url)  # raises HUB_MODULE_NOT_FOUND on 404
    try:
        data = tomllib.loads(text)
    except Exception as exc:
        raise HubError(
            ErrCode.HUB_PYPROJECT_INVALID,
            f"Failed to parse index entry for '{org}/{name}': {exc}",
        ) from exc
    mod = data.get("module", {})
    if "repo" not in mod:
        raise HubError(
            ErrCode.HUB_PYPROJECT_INVALID,
            f"Index entry for '{org}/{name}' is missing [module].repo",
        )
    return IndexEntry(
        repo_url=mod["repo"],
        description=mod.get("description", ""),
        author=mod.get("author", ""),
        license=mod.get("license", ""),
        tags=mod.get("tags", []),
    )


_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL."""
    m = _GITHUB_URL_RE.match(url)
    if m is None:
        raise HubError(
            ErrCode.HUB_REPO_NOT_ACCESSIBLE,
            f"Cannot parse GitHub URL: {url}",
        )
    return m.group("owner"), m.group("repo")
