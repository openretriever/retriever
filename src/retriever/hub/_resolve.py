"""Version resolution via GitHub API."""

from __future__ import annotations

import logging
from typing import Optional

from packaging.version import InvalidVersion, Version

from retriever.error import ErrCode, HubError
from retriever.hub._http import fetch_json

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _parse_semver(tag_name: str) -> Optional[Version]:
    """Try to parse a tag name as a semver version, stripping leading 'v'."""
    raw = tag_name.lstrip("v") if tag_name.startswith("v") else tag_name
    try:
        return Version(raw)
    except InvalidVersion:
        return None


def resolve_version(
    owner: str, repo: str, version: Optional[str] = None
) -> tuple[str, str]:
    """Resolve a version (or latest) to (tag_name, commit_sha).

    Args:
        owner: GitHub repo owner.
        repo: GitHub repo name.
        version: Semver string (e.g. "1.0.0") or None for latest.

    Returns:
        (tag_name, commit_sha) tuple.
    """
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/tags?per_page=100"
    tags = fetch_json(url)  # raises on HTTP error

    # Build list of (Version, tag_name, commit_sha) sorted descending
    semver_tags: list[tuple[Version, str, str]] = []
    for tag in tags:
        name = tag["name"]
        sha = tag["commit"]["sha"]
        ver = _parse_semver(name)
        if ver is not None:
            semver_tags.append((ver, name, sha))

    semver_tags.sort(key=lambda t: t[0], reverse=True)

    if not semver_tags:
        raise HubError(
            ErrCode.HUB_NO_SEMVER_TAGS,
            f"Repository '{owner}/{repo}' has no semver tags. "
            "Module authors must create at least one tag like 'v1.0.0'.",
        )

    if version is None:
        # Latest
        best = semver_tags[0]
        logger.debug("Resolved latest version: %s -> %s", best[1], best[2][:12])
        return best[1], best[2]

    # Find matching version
    target = _parse_semver(version)
    if target is None:
        raise HubError(
            ErrCode.HUB_VERSION_NOT_FOUND,
            f"'{version}' is not a valid semver version.",
        )

    for ver, tag_name, sha in semver_tags:
        if ver == target:
            return tag_name, sha

    available = ", ".join(str(v) for v, _, _ in semver_tags)
    raise HubError(
        ErrCode.HUB_VERSION_NOT_FOUND,
        f"Version '{version}' not found for '{owner}/{repo}'. "
        f"Available versions: {available}",
    )
