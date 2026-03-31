"""HTTP utilities for Hub (stdlib only)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from retriever.error import ErrCode, HubError

logger = logging.getLogger(__name__)

_TIMEOUT = 30  # seconds


def _build_request(url: str) -> Request:
    """Build a urllib Request with common headers."""
    req = Request(url)
    req.add_header("User-Agent", "retriever-hub")
    token = os.environ.get("RETRIEVER_HUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def _do_request(url: str) -> bytes:
    """Perform an HTTP GET and return raw bytes."""
    req = _build_request(url)
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()  # type: ignore[no-any-return]
    except HTTPError as exc:
        if exc.code == 404:
            raise HubError(
                ErrCode.HUB_MODULE_NOT_FOUND,
                f"Resource not found: {url}",
            ) from exc
        raise HubError(
            ErrCode.HUB_FETCH_FAILED,
            f"HTTP {exc.code} when fetching {url}: {exc.reason}",
        ) from exc
    except URLError as exc:
        raise HubError(
            ErrCode.HUB_REPO_NOT_ACCESSIBLE,
            f"Cannot reach {url}: {exc.reason}",
        ) from exc


def fetch_text(url: str) -> str:
    """GET a URL and return the response body as text."""
    return _do_request(url).decode("utf-8")


def fetch_bytes(url: str) -> bytes:
    """GET a URL and return the response body as bytes."""
    return _do_request(url)


def fetch_json(url: str) -> Any:
    """GET a URL and return the response body parsed as JSON."""
    return json.loads(_do_request(url))
