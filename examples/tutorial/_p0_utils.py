"""Shared helpers for P0 tutorial additions (024-029)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile in [0, 100]."""
    if not values:
        return 0.0

    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]

    pct = max(0.0, min(100.0, float(p)))
    rank = (len(ordered) - 1) * pct / 100.0
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def format_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Format rows as a simple fixed-width table."""
    widths = [len(str(h)) for h in headers]
    normalized: list[list[str]] = []

    for row in rows:
        values = [str(v) for v in row]
        normalized.append(values)
        for i, value in enumerate(values):
            widths[i] = max(widths[i], len(value))

    def render(parts: Sequence[str]) -> str:
        return " | ".join(str(part).ljust(widths[i]) for i, part in enumerate(parts))

    divider = "-+-".join("-" * w for w in widths)
    lines = [render(headers), divider]
    lines.extend(render(row) for row in normalized)
    return "\n".join(lines)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
