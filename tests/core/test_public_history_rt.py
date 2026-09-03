from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.release.check_public_history import (
    check_added_lines,
    check_commit_range,
    find_markers,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def test_markers_reject_agent_metadata_but_allow_product_references() -> None:
    assert find_markers("Add an OpenAI-compatible planner backend") == ()
    assert find_markers("Co-Authored-By: Claude <bot@example.com>")
    assert find_markers("Claude-Session: https://example.invalid/session")
    assert find_markers("Generated with Codex")


def test_commit_range_reports_only_the_introduced_bad_commit(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Test Maintainer")
    _git(tmp_path, "config", "user.email", "maintainer@example.com")
    (tmp_path / "example.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "example.txt")
    _git(tmp_path, "commit", "-m", "Add example")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (tmp_path / "example.txt").write_text("updated\n", encoding="utf-8")
    _git(tmp_path, "add", "example.txt")
    _git(
        tmp_path,
        "commit",
        "-m",
        "Update example\n\nCo-Authored-By: Claude <bot@example.com>",
    )

    failures = check_commit_range(base, "HEAD", repo=tmp_path)
    assert len(failures) == 1
    assert "agent co-author trailer" in failures[0]


def test_added_public_content_is_checked_separately(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Test Maintainer")
    _git(tmp_path, "config", "user.email", "maintainer@example.com")
    (tmp_path / "README.md").write_text("Public example\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "Add README")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (tmp_path / "README.md").write_text(
        "Public example\n\nGenerated with Codex\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "Update README")

    assert check_commit_range(base, "HEAD", repo=tmp_path) == []
    failures = check_added_lines(base, "HEAD", repo=tmp_path)
    assert failures == ["README.md:3: agent generation marker"]
