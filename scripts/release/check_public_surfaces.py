#!/usr/bin/env python3
"""Check public launch surfaces that are not covered by unit tests.

This verifier is intentionally network-facing and manual. It catches release
blockers such as a GitHub default branch still pointing at an audit branch,
custom domains without DNS records, or a package name that is not published yet.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


HTTP_TARGETS = (
    ("landing", "https://openretriever.org/"),
    ("landing-www", "https://www.openretriever.org/"),
    ("core-docs-pages", "https://openretriever-docs.pages.dev/"),
    ("core-docs-custom", "https://docs.openretriever.org/"),
    ("golden-pages", "https://retriever-space.pages.dev/"),
    ("golden-root-custom", "https://retriever.space/"),
    ("golden-space-custom", "https://golden.retriever.space/"),
    ("golden-systems-custom", "https://golden.retriever.systems/"),
)

DNS_TARGETS = (
    "openretriever.org",
    "www.openretriever.org",
    "docs.openretriever.org",
    "retriever.space",
    "golden.retriever.space",
    "golden.retriever.systems",
)

PYPI_TARGETS = (
    ("pypi", "https://pypi.org/pypi/retriever-core/json"),
    ("testpypi", "https://test.pypi.org/pypi/retriever-core/json"),
)


def _open(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "retriever-release-check/0.1"},
    )
    # The checker only opens fixed release URLs declared in this file.
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.status, resp.geturl()


def check_http(timeout: float) -> Iterable[CheckResult]:
    for name, url in HTTP_TARGETS:
        try:
            status, final_url = _open(url, timeout)
            ok = 200 <= status < 400
            yield CheckResult(f"http:{name}", ok, f"{status} {final_url}")
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            yield CheckResult(f"http:{name}", False, f"{type(exc).__name__}: {exc}")


def check_dns() -> Iterable[CheckResult]:
    for host in DNS_TARGETS:
        try:
            answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            ips = sorted({item[4][0] for item in answers})
            yield CheckResult(f"dns:{host}", bool(ips), ", ".join(ips[:4]))
        except socket.gaierror as exc:
            yield CheckResult(f"dns:{host}", False, str(exc))


def check_pypi(timeout: float) -> Iterable[CheckResult]:
    for name, url in PYPI_TARGETS:
        try:
            status, _ = _open(url, timeout)
            yield CheckResult(f"package:{name}:retriever-core", status == 200, f"HTTP {status}")
        except urllib.error.HTTPError as exc:
            yield CheckResult(f"package:{name}:retriever-core", False, f"HTTP {exc.code}")
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            yield CheckResult(f"package:{name}:retriever-core", False, f"{type(exc).__name__}: {exc}")


def check_github_default_branch(remote: str, expected: str) -> CheckResult:
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--symref", remote, "HEAD"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult("github:default-branch", False, f"{type(exc).__name__}: {exc}")

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"git exited {proc.returncode}"
        return CheckResult("github:default-branch", False, detail)

    first = proc.stdout.splitlines()[0] if proc.stdout.splitlines() else ""
    prefix = "ref: refs/heads/"
    if first.startswith(prefix) and first.endswith("\tHEAD"):
        branch = first[len(prefix) : -len("\tHEAD")]
        ok = branch == expected
        return CheckResult("github:default-branch", ok, f"HEAD -> {branch}")

    return CheckResult("github:default-branch", False, f"could not parse ls-remote output: {first!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--github-remote",
        default="git@github.com:openretriever/retriever.git",
        help="Git remote used for default-branch verification.",
    )
    parser.add_argument("--expected-default-branch", default="main")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    results = [check_github_default_branch(args.github_remote, args.expected_default_branch)]
    results.extend(check_http(args.timeout))
    results.extend(check_dns())
    results.extend(check_pypi(args.timeout))

    if args.json:
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        width = max(len(result.name) for result in results)
        for result in results:
            status = "PASS" if result.ok else "FAIL"
            print(f"[{status}] {result.name:<{width}}  {result.detail}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
