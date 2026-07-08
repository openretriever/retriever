"""Small command-line wrapper around Retriever repo Pixi tasks.

The CLI intentionally delegates task execution to Pixi instead of becoming a
second task registry. Retriever owns the friendly command names; Pixi owns the
reproducible environment and task definitions.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ALIASES: dict[str, str] = {
    "basic": "demo-basic-flow",
    "basic-flow": "demo-basic-flow",
    "webcam": "demo-webcam-detection",
    "webcam-live": "demo-webcam-detection",
    "webcam-mock": "demo-webcam-detection-mock",
    "webcam-rerun": "demo-webcam-detection-mp-rerun",
    "stepper": "demo-stepper",
    "webcam-stepper": "demo-webcam-stepper",
    "graph": "docs-tutorial-perception-html",
    "graph-perception": "docs-tutorial-perception-html",
    "graph-composable": "docs-tutorial-composable-html",
    "record": "demo-webcam-record",
    "replay": "demo-webcam-replay-rrd",
    "docs": "docs-serve",
    "docs-build": "docs-build",
    "test": "test",
}

COMPOUND_ALIASES: dict[tuple[str, str], str] = {
    ("demo", "basic"): "demo-basic-flow",
    ("demo", "webcam"): "demo-webcam-detection",
    ("demo", "mock"): "demo-webcam-detection-mock",
    ("demo", "rerun"): "demo-webcam-detection-mp-rerun",
    ("debug", "stepper"): "demo-stepper",
    ("debug", "record"): "demo-webcam-record",
    ("debug", "replay"): "demo-webcam-replay-rrd",
    ("graph", "perception"): "docs-tutorial-perception-html",
    ("graph", "composable"): "docs-tutorial-composable-html",
}

HELP = """Retriever CLI

Usage:
  retriever <alias-or-pixi-task> [-- task args...]
  retriever run <pixi-task> [-- task args...]
  retriever tasks
  retriever --dry-run <alias-or-pixi-task> [-- task args...]

Common aliases:
  webcam-mock       -> pixi run demo-webcam-detection-mock
  webcam            -> pixi run demo-webcam-detection
  webcam-rerun      -> pixi run demo-webcam-detection-mp-rerun
  basic-flow        -> pixi run demo-basic-flow
  graph             -> pixi run docs-tutorial-perception-html
  record            -> pixi run demo-webcam-record
  replay            -> pixi run demo-webcam-replay-rrd
  docs              -> pixi run docs-serve

Raw Pixi task forwarding:
  retriever run demo-pipeline-ergonomics
  retriever demo-pipeline-ergonomics

Arguments after -- are passed to the Pixi task command.
"""


@dataclass(frozen=True)
class Command:
    task: str | None
    args: tuple[str, ...] = ()
    dry_run: bool = False
    list_tasks: bool = False
    show_help: bool = False


def find_pixi_workspace(start: Path | None = None) -> Path | None:
    """Return the nearest parent containing ``pixi.toml``."""
    current = (start or Path.cwd()).resolve()
    candidates = (current, *current.parents)
    for candidate in candidates:
        if (candidate / "pixi.toml").is_file():
            return candidate
    return None


def _strip_separator(args: Sequence[str]) -> tuple[str, ...]:
    if args and args[0] == "--":
        return tuple(args[1:])
    return tuple(args)


def parse_command(argv: Sequence[str]) -> Command:
    args = list(argv)
    dry_run = False
    if args and args[0] == "--dry-run":
        dry_run = True
        args.pop(0)

    if not args or args[0] in {"-h", "--help", "help"}:
        return Command(task=None, dry_run=dry_run, show_help=True)

    if args[0] in {"tasks", "list"}:
        return Command(task=None, dry_run=dry_run, list_tasks=True)

    if args[0] == "run":
        if len(args) == 1:
            return Command(task=None, dry_run=dry_run, show_help=True)
        return Command(
            task=args[1],
            args=_strip_separator(args[2:]),
            dry_run=dry_run,
        )

    if len(args) >= 2:
        compound = COMPOUND_ALIASES.get((args[0], args[1]))
        if compound is not None:
            return Command(
                task=compound,
                args=_strip_separator(args[2:]),
                dry_run=dry_run,
            )

    return Command(
        task=ALIASES.get(args[0], args[0]),
        args=_strip_separator(args[1:]),
        dry_run=dry_run,
    )


def build_pixi_command(command: Command) -> list[str]:
    if command.task is None:
        raise ValueError("cannot build a Pixi command without a task")
    return ["pixi", "run", command.task, *command.args]


def render_tasks() -> str:
    rows = ["Retriever aliases (thin wrappers over pixi run):"]
    width = max(len(alias) for alias in ALIASES)
    for alias, task in sorted(ALIASES.items()):
        rows.append(f"  {alias:<{width}}  ->  pixi run {task}")
    rows.append("")
    rows.append("Any Pixi task also works directly: retriever run <task>")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    command = parse_command(sys.argv[1:] if argv is None else argv)

    if command.show_help:
        print(HELP)
        return 0
    if command.list_tasks:
        print(render_tasks())
        return 0

    pixi_command = build_pixi_command(command)
    if command.dry_run:
        print(" ".join(pixi_command))
        return 0

    workspace = find_pixi_workspace()
    if workspace is None:
        print(
            "retriever: no pixi.toml found in this directory or its parents; "
            "run from a Retriever source checkout.",
            file=sys.stderr,
        )
        return 2

    return subprocess.call(pixi_command, cwd=str(workspace))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
