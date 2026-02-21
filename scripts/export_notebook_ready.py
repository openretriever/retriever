#!/usr/bin/env python3
"""
Export tutorial markdown pages into notebook-ready artifacts.

Artifacts:
- JSON cell manifests (stable for downstream conversion pipelines)
- Optional .ipynb scaffolds for immediate Jupyter rendering

Run:
  python scripts/export_notebook_ready.py --emit-ipynb
  python scripts/export_notebook_ready.py --check
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PYTHON_FENCE_LANGS = {"python", "py", "ipython"}
SHELL_FENCE_LANGS = {"bash", "sh", "zsh", "shell"}


@dataclass
class ParsedCell:
    kind: str
    source: str
    start_line: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines(keepends=True)
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text

    meta: dict[str, str] = {}
    for raw in lines[1:end_idx]:
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')

    body = "".join(lines[end_idx + 1 :])
    return meta, body


def _split_markdown_into_cells(text: str) -> list[ParsedCell]:
    lines = text.splitlines(keepends=True)
    cells: list[ParsedCell] = []

    md_buffer: list[str] = []
    code_buffer: list[str] = []
    in_fence = False
    fence_lang = ""
    fence_start_line = 1

    def flush_markdown(start_line: int) -> None:
        if not md_buffer:
            return
        source = "".join(md_buffer)
        if source.strip():
            cells.append(ParsedCell(kind="markdown", source=source, start_line=start_line))
        md_buffer.clear()

    md_start_line = 1

    for idx, line in enumerate(lines, start=1):
        fence_match = re.match(r"^\s*```([^\s`]*)?.*$", line)

        if not in_fence and fence_match:
            flush_markdown(md_start_line)
            in_fence = True
            fence_lang = (fence_match.group(1) or "").strip().lower()
            fence_start_line = idx
            code_buffer = []
            continue

        if in_fence and line.strip().startswith("```"):
            source = "".join(code_buffer)
            if fence_lang in PYTHON_FENCE_LANGS:
                cells.append(ParsedCell(kind="python", source=source, start_line=fence_start_line))
            elif fence_lang in SHELL_FENCE_LANGS:
                cells.append(ParsedCell(kind="shell", source=source, start_line=fence_start_line))
            else:
                fenced = f"```{fence_lang}\n{source}```\n"
                cells.append(ParsedCell(kind="markdown", source=fenced, start_line=fence_start_line))

            in_fence = False
            fence_lang = ""
            md_start_line = idx + 1
            continue

        if in_fence:
            code_buffer.append(line)
        else:
            if not md_buffer:
                md_start_line = idx
            md_buffer.append(line)

    if in_fence:
        md_buffer.append(f"```{fence_lang}\n")
        md_buffer.extend(code_buffer)

    flush_markdown(md_start_line)
    return cells


def _normalize_source_for_ipynb(source: str) -> list[str]:
    if not source.endswith("\n"):
        source = source + "\n"
    return source.splitlines(keepends=True)


def _shell_source_for_notebook(shell_source: str) -> str:
    if shell_source.strip().startswith("%%bash"):
        return shell_source
    return "%%bash\n" + shell_source


def _cell_to_ipynb(cell: ParsedCell) -> dict:
    if cell.kind == "markdown":
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": _normalize_source_for_ipynb(cell.source),
        }

    if cell.kind == "python":
        code = cell.source
    elif cell.kind == "shell":
        code = _shell_source_for_notebook(cell.source)
    else:
        code = cell.source

    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _normalize_source_for_ipynb(code),
    }


def _slugify(path: Path) -> str:
    raw = "_".join(path.with_suffix("").parts)
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()


def _collect_markdown_files(docs_root: Path) -> list[Path]:
    files = [p for p in docs_root.rglob("*.md") if p.is_file()]
    files.sort()
    return files


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export tutorial markdown into notebook-ready manifests and scaffolds.")
    p.add_argument(
        "--docs-root",
        type=Path,
        default=Path("docs/tutorials"),
        help="Root folder containing tutorial markdown pages.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out/jupyter-notebook"),
        help="Output directory for notebook-ready artifacts.",
    )
    p.add_argument(
        "--emit-ipynb",
        action="store_true",
        help="Also emit .ipynb scaffold notebooks.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Validate conversion only; do not write output files.",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not args.docs_root.exists():
        raise FileNotFoundError(f"Tutorial docs root not found: {args.docs_root}")

    docs_root = args.docs_root.resolve()
    files = _collect_markdown_files(docs_root)
    if not files:
        raise RuntimeError(f"No markdown files found under: {docs_root}")

    generated_at = utc_now_iso()
    index_rows: list[dict[str, object]] = []

    for src_abs in files:
        rel = src_abs.relative_to(docs_root)
        slug = _slugify(rel)

        text = src_abs.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        cells = _split_markdown_into_cells(body)
        if not cells:
            cells = [ParsedCell(kind="markdown", source=body, start_line=1)]

        counts = {"markdown": 0, "python": 0, "shell": 0}
        for c in cells:
            if c.kind in counts:
                counts[c.kind] += 1

        title = frontmatter.get("title") or rel.stem

        manifest = {
            "schema_version": "retriever.notebook_ready.v1",
            "generated_at": generated_at,
            "source_markdown": str(rel),
            "title": title,
            "cells": [
                {
                    "index": idx,
                    "kind": c.kind,
                    "start_line": c.start_line,
                    "source": c.source,
                }
                for idx, c in enumerate(cells)
            ],
            "counts": counts,
        }

        ipynb = {
            "cells": [_cell_to_ipynb(c) for c in cells],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "name": "python",
                    "pygments_lexer": "ipython3",
                },
                "retriever": {
                    "generated_at": generated_at,
                    "source_markdown": str(rel),
                    "conversion": "scripts/export_notebook_ready.py",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        manifest_rel = Path("manifests") / f"{slug}.cells.json"
        notebook_rel = Path("notebooks") / f"{slug}.ipynb"

        index_rows.append(
            {
                "source_markdown": str(rel),
                "title": title,
                "manifest": str(manifest_rel),
                "notebook": str(notebook_rel) if args.emit_ipynb else None,
                "counts": counts,
            }
        )

        if not args.check:
            write_json(args.out_dir / manifest_rel, manifest)
            if args.emit_ipynb:
                write_json(args.out_dir / notebook_rel, ipynb)

    summary = {
        "schema_version": "retriever.notebook_ready.index.v1",
        "generated_at": generated_at,
        "docs_root": str(docs_root),
        "files": index_rows,
    }

    if not args.check:
        write_json(args.out_dir / "index.json", summary)

    print(f"[notebook-ready] docs={len(index_rows)} check_only={args.check} emit_ipynb={args.emit_ipynb}")
    for row in index_rows:
        c = row["counts"]
        print(
            f" - {row['source_markdown']}: markdown={c['markdown']} python={c['python']} shell={c['shell']}"
        )
    if not args.check:
        print(f"[notebook-ready] wrote artifacts to {args.out_dir}")


if __name__ == "__main__":
    main()
