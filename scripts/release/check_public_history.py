#!/usr/bin/env python3
"""Reject public-facing agent attribution from a pull request."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIFF_PATHS = (
    "AGENTS.md",
    "scripts/release/check_public_history.py",
    "tests/core/test_public_history_rt.py",
)
MARKERS = (
    (
        "agent co-author trailer",
        re.compile(
            r"(?im)^co-authored-by:\s*[^\n]*"
            r"(?:claude|codex|chatgpt|anthropic|openai|copilot|gemini|gpt(?:-\d+)?)\b"
        ),
    ),
    (
        "agent session marker",
        re.compile(r"(?im)^\s*(?:claude|codex|chatgpt)[-_ ]session\s*:"),
    ),
    (
        "agent generation marker",
        re.compile(
            r"(?i)\b(?:generated|created|written)\s+(?:with|by)\s+"
            r"(?:claude|codex|chatgpt|anthropic|openai|copilot|gemini)\b"
        ),
    ),
)
AGENT_IDENTITY = re.compile(
    r"(?i)(?:\b(?:claude|codex|chatgpt|copilot|gemini|gpt(?:-\d+)?)\b|"
    r"noreply@(?:anthropic|openai)\.com)"
)


def _git(*args: str, repo: Path = ROOT) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def find_markers(text: str) -> tuple[str, ...]:
    return tuple(label for label, pattern in MARKERS if pattern.search(text))


def check_commit_range(base: str, head: str, *, repo: Path = ROOT) -> list[str]:
    failures: list[str] = []
    commits = _git("rev-list", "--reverse", f"{base}..{head}", repo=repo).splitlines()
    for commit in commits:
        message = _git("show", "-s", "--format=%B", commit, repo=repo)
        markers = find_markers(message)
        if markers:
            failures.append(f"commit {commit[:12]}: {', '.join(markers)}")

        identity = _git(
            "show", "-s", "--format=%an%n%ae%n%cn%n%ce", commit, repo=repo
        )
        if AGENT_IDENTITY.search(identity):
            failures.append(f"commit {commit[:12]}: agent author or committer identity")
    return failures


def check_added_lines(base: str, head: str, *, repo: Path = ROOT) -> list[str]:
    exclusions = [f":(exclude){path}" for path in EXCLUDED_DIFF_PATHS]
    diff = _git(
        "diff",
        "--unified=0",
        "--no-color",
        f"{base}...{head}",
        "--",
        ".",
        *exclusions,
        repo=repo,
    )
    failures: list[str] = []
    path = "unknown"
    line_number = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            line_number = int(match.group(1)) if match else 0
            continue
        if line.startswith("+") and not line.startswith("+++"):
            markers = find_markers(line[1:])
            if markers:
                failures.append(f"{path}:{line_number}: {', '.join(markers)}")
            line_number += 1
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("PUBLIC_HISTORY_BASE"))
    parser.add_argument("--head", default=os.environ.get("PUBLIC_HISTORY_HEAD", "HEAD"))
    args = parser.parse_args()
    if not args.base:
        parser.error("--base or PUBLIC_HISTORY_BASE is required")

    try:
        failures = check_commit_range(args.base, args.head)
        failures.extend(check_added_lines(args.base, args.head))
    except RuntimeError as exc:
        print(f"public history check could not run: {exc}", file=sys.stderr)
        return 2

    pr_text = "\n".join(
        (os.environ.get("PUBLIC_PR_TITLE", ""), os.environ.get("PUBLIC_PR_BODY", ""))
    )
    markers = find_markers(pr_text)
    if markers:
        failures.append(f"pull request title/body: {', '.join(markers)}")

    if failures:
        print("Public history guardrail failed:")
        for failure in failures:
            print(f"- {failure}")
        print(
            "Remove agent attribution and session metadata, then rewrite the "
            "affected commits."
        )
        return 1

    print("Public history guardrail passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
