"""
Plugin loading for Retriever.

This provides a minimal plugin discovery mechanism so that external packages
can register pipelines/components into Retriever at import/runtime time.

Convention:
  - Plugins are exposed via Python entry points under the group `retriever.plugins`
  - Each entry point must resolve to a callable with signature `() -> None`
    that performs registration (e.g., calls `register_pipeline(...)`).
"""

from __future__ import annotations

import logging
from importlib import metadata
from typing import Iterable, Any

logger = logging.getLogger(__name__)

_PLUGINS_LOADED = False


def _iter_entry_points(group: str) -> Iterable[Any]:
    """Iterate entry points for a given group across Python versions."""
    eps = metadata.entry_points()
    # Python 3.10+: EntryPoints has `.select`
    if hasattr(eps, "select"):
        return eps.select(group=group)  # type: ignore[attr-defined]
    # Older: dict-like
    return eps.get(group, [])  # type: ignore[return-value]


def load_plugins(*, force: bool = False, group: str = "retriever.plugins") -> int:
    """
    Load plugins registered under the given entry point group.

    Returns:
        Number of successfully invoked plugin callables.
    """
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED and not force:
        return 0

    invoked = 0
    for ep in _iter_entry_points(group):
        try:
            plugin = ep.load()
        except Exception as e:
            logger.warning("Failed to load plugin entry point '%s': %s", getattr(ep, "name", ep), e)
            continue

        if not callable(plugin):
            logger.warning(
                "Plugin entry point '%s' resolved to non-callable: %r",
                getattr(ep, "name", ep),
                plugin,
            )
            continue

        try:
            plugin()
            invoked += 1
        except Exception as e:
            logger.warning("Plugin '%s' raised during registration: %s", getattr(ep, "name", ep), e)

    _PLUGINS_LOADED = True
    return invoked

