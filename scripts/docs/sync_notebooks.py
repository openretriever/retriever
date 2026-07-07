#!/usr/bin/env python3
"""Regenerate downloadable notebooks from their jupytext sources.

    notebooks/src/<name>.py  ->  docs-site/public/notebooks/<name-with-hyphens>.ipynb

The ``.py`` files (jupytext ``py:percent``) are the source of truth — reviewable,
clean git diffs. The ``.ipynb`` files are generated artifacts served for download
and "Open in Colab".

Usage:
    python scripts/docs/sync_notebooks.py           # regenerate all
    python scripts/docs/sync_notebooks.py --check    # fail if any is stale (CI)

``--check`` compares only the *cell sources* (ignoring notebook ids / metadata /
outputs, which jupytext may vary run to run), so it is stable in CI.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import jupytext

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "notebooks" / "src"
OUT_DIR = ROOT / "docs-site" / "public" / "notebooks"


def target_for(src: pathlib.Path) -> pathlib.Path:
    return OUT_DIR / (src.stem.replace("_", "-") + ".ipynb")


def cell_sources(nb) -> list[str]:
    return [c.source for c in nb.cells]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if any notebook is stale")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    srcs = sorted(SRC_DIR.glob("*.py"))
    if not srcs:
        print("no notebook sources in notebooks/src/")
        return 0

    stale: list[str] = []
    for src in srcs:
        dest = target_for(src)
        fresh = jupytext.read(src)
        if args.check:
            if not dest.exists():
                stale.append(f"{dest.name} (missing)")
                continue
            existing = jupytext.read(dest)
            if cell_sources(existing) != cell_sources(fresh):
                stale.append(f"{dest.name} (out of date vs {src.name})")
        else:
            jupytext.write(fresh, dest, fmt="ipynb")
            print(f"  {src.name} -> {dest.relative_to(ROOT)}")

    if args.check:
        if stale:
            print("Stale notebooks (run `pixi run nb-sync`):", file=sys.stderr)
            for s in stale:
                print(f"  - {s}", file=sys.stderr)
            return 1
        print(f"All {len(srcs)} notebook(s) in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
