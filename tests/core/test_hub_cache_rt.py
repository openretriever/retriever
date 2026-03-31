"""Tests for hub cache management."""

import pytest
from pathlib import Path
from unittest.mock import patch

from retriever.hub._cache import (
    _MARKER,
    cache_dir_for,
    clear_cache,
    get_cached_module_root,
    is_cached,
    mark_cached,
)


class TestCacheDir:
    @patch("retriever.hub._cache._CACHE_ROOT", Path("/fake/cache"))
    def test_cache_dir_for(self):
        d = cache_dir_for("company-abc", "lidar-slam", "abc123def456")
        assert d == Path("/fake/cache/company-abc/lidar-slam/abc123def456")

    @patch("retriever.hub._cache._CACHE_ROOT", Path("/fake/cache"))
    def test_get_cached_module_root(self):
        d = get_cached_module_root("org", "mod", "sha123")
        assert d == Path("/fake/cache/org/mod/sha123")


class TestIsCached:
    def test_not_cached(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            assert is_cached("org", "mod", "sha123") is False

    def test_dir_exists_but_no_marker(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            d = tmp_path / "org" / "mod" / "sha123"
            d.mkdir(parents=True)
            assert is_cached("org", "mod", "sha123") is False

    def test_cached_with_marker(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            d = tmp_path / "org" / "mod" / "sha123"
            d.mkdir(parents=True)
            (d / _MARKER).touch()
            assert is_cached("org", "mod", "sha123") is True


class TestMarkCached:
    def test_mark_cached(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            d = tmp_path / "org" / "mod" / "sha123"
            d.mkdir(parents=True)
            mark_cached("org", "mod", "sha123")
            assert (d / _MARKER).exists()


class TestClearCache:
    def test_clear_all(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            # Create two cached modules
            for sha in ["sha1", "sha2"]:
                d = tmp_path / "org" / "mod" / sha
                d.mkdir(parents=True)
            count = clear_cache()
            assert count == 2
            assert not tmp_path.exists()

    def test_clear_org(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            (tmp_path / "org-a" / "mod" / "sha1").mkdir(parents=True)
            (tmp_path / "org-b" / "mod" / "sha2").mkdir(parents=True)
            count = clear_cache(org="org-a")
            assert count == 1
            assert not (tmp_path / "org-a").exists()
            assert (tmp_path / "org-b").exists()

    def test_clear_specific_module(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            (tmp_path / "org" / "mod-a" / "sha1").mkdir(parents=True)
            (tmp_path / "org" / "mod-b" / "sha2").mkdir(parents=True)
            count = clear_cache(org="org", name="mod-a")
            assert count == 1
            assert not (tmp_path / "org" / "mod-a").exists()
            assert (tmp_path / "org" / "mod-b").exists()

    def test_clear_nonexistent(self, tmp_path: Path):
        with patch("retriever.hub._cache._CACHE_ROOT", tmp_path):
            count = clear_cache(org="no-such-org")
            assert count == 0
