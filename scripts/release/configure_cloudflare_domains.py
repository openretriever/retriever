#!/usr/bin/env python3
"""Configure Retriever Cloudflare Pages custom domains and DNS records.

Dry-run mode prints the exact public launch bindings without requiring
Cloudflare credentials. Actual mode requires:

  CLOUDFLARE_ACCOUNT_ID or CF_ACCOUNT_ID
  CLOUDFLARE_API_TOKEN or CF_API_TOKEN

The token must have Cloudflare Pages project access and DNS record read/edit
access for the relevant zones.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


API_BASE = "https://api.cloudflare.com/client/v4"

PAGES_DOMAINS = (
    ("openretriever-docs", "retriever.build"),
    ("retriever-space", "golden.retriever.build"),
    ("retriever-space", "golden.golden.retriever.build"),
    ("retriever-space", "golden.retriever.systems"),
)

DNS_RECORDS = (
    ("openretriever.org", "CNAME", "retriever.build", "retriever.build", True),
    ("golden.retriever.build", "CNAME", "golden.retriever.build", "golden.retriever.build", True),
    ("golden.retriever.build", "CNAME", "golden.golden.retriever.build", "golden.retriever.build", True),
    ("retriever.systems", "CNAME", "golden.retriever.systems", "golden.retriever.build", True),
)


@dataclass(frozen=True)
class Result:
    name: str
    ok: bool
    action: str
    detail: str


class CloudflareClient:
    def __init__(self, token: str, account_id: str, *, timeout: float = 30.0) -> None:
        self.token = token
        self.account_id = account_id
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            API_BASE + path,
            data=payload,
            headers=self.headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return {
                "success": False,
                "errors": [{"code": exc.code, "message": text}],
                "result": None,
            }

    def zone_id(self, zone_name: str) -> str | None:
        query = urllib.parse.urlencode({"name": zone_name, "per_page": 5})
        data = self.request("GET", f"/zones?{query}")
        if not data.get("success"):
            return None
        result = data.get("result") or []
        return result[0]["id"] if result else None


def _credential_client(timeout: float) -> CloudflareClient:
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID")
    if not token:
        raise SystemExit("Missing CLOUDFLARE_API_TOKEN or CF_API_TOKEN.")
    if not account_id:
        raise SystemExit("Missing CLOUDFLARE_ACCOUNT_ID or CF_ACCOUNT_ID.")
    return CloudflareClient(token=token, account_id=account_id, timeout=timeout)


def dry_run_results() -> list[Result]:
    results: list[Result] = []
    for project, domain in PAGES_DOMAINS:
        results.append(
            Result(
                name=f"pages:{project}:{domain}",
                ok=True,
                action="would ensure",
                detail=f"custom domain {domain}",
            )
        )
    for zone, record_type, name, content, proxied in DNS_RECORDS:
        proxy_text = "proxied" if proxied else "dns-only"
        results.append(
            Result(
                name=f"dns:{zone}:{name}",
                ok=True,
                action="would upsert",
                detail=f"{record_type} {name} -> {content} ({proxy_text})",
            )
        )
    return results


def ensure_pages_domains(client: CloudflareClient) -> list[Result]:
    results: list[Result] = []
    seen_projects = sorted({project for project, _domain in PAGES_DOMAINS})
    domains_by_project: dict[str, set[str]] = {}
    status_by_project_domain: dict[tuple[str, str], str] = {}

    for project in seen_projects:
        data = client.request(
            "GET",
            f"/accounts/{client.account_id}/pages/projects/{project}/domains",
        )
        if not data.get("success"):
            results.append(
                Result(
                    name=f"pages:{project}",
                    ok=False,
                    action="list failed",
                    detail=json.dumps(data.get("errors")),
                )
            )
            continue
        domains: set[str] = set()
        for item in data.get("result") or []:
            domain = item.get("name")
            if not domain:
                continue
            domains.add(domain)
            status_by_project_domain[(project, domain)] = item.get("status", "unknown")
        domains_by_project[project] = domains

    for project, domain in PAGES_DOMAINS:
        if domain in domains_by_project.get(project, set()):
            status = status_by_project_domain.get((project, domain), "unknown")
            results.append(Result(f"pages:{project}:{domain}", True, "exists", f"status={status}"))
            continue
        data = client.request(
            "POST",
            f"/accounts/{client.account_id}/pages/projects/{project}/domains",
            {"name": domain},
        )
        results.append(
            Result(
                name=f"pages:{project}:{domain}",
                ok=bool(data.get("success")),
                action="created" if data.get("success") else "create failed",
                detail=json.dumps(data.get("errors") or data.get("result")),
            )
        )
    return results


def ensure_dns_records(client: CloudflareClient) -> list[Result]:
    results: list[Result] = []
    for zone, record_type, name, content, proxied in DNS_RECORDS:
        zid = client.zone_id(zone)
        if zid is None:
            results.append(Result(f"dns:{zone}:{name}", False, "zone lookup failed", "zone not found or unauthorized"))
            continue
        query = urllib.parse.urlencode({"type": record_type, "name": name, "per_page": 10})
        listed = client.request("GET", f"/zones/{zid}/dns_records?{query}")
        if not listed.get("success"):
            results.append(
                Result(
                    name=f"dns:{zone}:{name}",
                    ok=False,
                    action="record list failed",
                    detail=json.dumps(listed.get("errors")),
                )
            )
            continue
        body = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": 1,
            "proxied": proxied,
        }
        existing = listed.get("result") or []
        if existing:
            record_id = existing[0]["id"]
            updated = client.request("PUT", f"/zones/{zid}/dns_records/{record_id}", body)
            results.append(
                Result(
                    name=f"dns:{zone}:{name}",
                    ok=bool(updated.get("success")),
                    action="updated" if updated.get("success") else "update failed",
                    detail=json.dumps(updated.get("errors") or updated.get("result")),
                )
            )
        else:
            created = client.request("POST", f"/zones/{zid}/dns_records", body)
            results.append(
                Result(
                    name=f"dns:{zone}:{name}",
                    ok=bool(created.get("success")),
                    action="created" if created.get("success") else "create failed",
                    detail=json.dumps(created.get("errors") or created.get("result")),
                )
            )
    return results


def print_results(results: list[Result], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(result) for result in results], indent=2))
        return
    width = max(len(result.name) for result in results)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name:<{width}}  {result.action}: {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned bindings without credentials.")
    parser.add_argument("--skip-pages", action="store_true", help="Do not create/check Pages custom domains.")
    parser.add_argument("--skip-dns", action="store_true", help="Do not create/update DNS records.")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        results = dry_run_results()
    else:
        client = _credential_client(args.timeout)
        results = []
        if not args.skip_pages:
            results.extend(ensure_pages_domains(client))
        if not args.skip_dns:
            results.extend(ensure_dns_records(client))

    print_results(results, as_json=args.json)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
