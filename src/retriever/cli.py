"""Retriever command-line surface for package and source-checkout workflows.

The PyPI package installs this executable through ``[project.scripts]``. The CLI
owns Retriever verbs such as ``init``, ``install``, and ``run``; the source
checkout currently uses Pixi as the reproducible environment and task backend.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

RUN_TARGETS: dict[str, str] = {
    "basic": "demo-basic-flow",
    "basic-flow": "demo-basic-flow",
    "composable-pipelines": "demo-composable-pipelines",
    "ir-validation": "demo-ir-validation",
    "multirate": "demo-multirate",
    "record-replay": "demo-record-replay",
    "rt-execution": "demo-rt-execution",
    "webcam": "demo-webcam-detection",
    "webcam-live": "demo-webcam-detection",
    "webcam-mock": "demo-webcam-detection-mock",
    "webcam-rerun": "demo-webcam-detection-mp-rerun",
    "webcam-dora": "demo-webcam-detection-dora",
    "dora-perception": "demo-webcam-detection-dora",
    "stepper": "demo-stepper",
    "perception-stepper": "demo-perception-stepper",
    "webcam-stepper": "demo-webcam-stepper",
    "graph": "docs-tutorial-perception-html",
    "graph-perception": "docs-tutorial-perception-html",
    "graph-composable": "docs-tutorial-composable-html",
    "record": "demo-webcam-record",
    "replay": "demo-webcam-replay-rrd",
    "incident-replay": "demo-incident-replay",
    "docs": "docs-serve",
    "docs-build": "docs-build",
    "test": "test",
}

COMPOUND_RUN_TARGETS: dict[tuple[str, str], str] = {
    ("demo", "basic"): "demo-basic-flow",
    ("demo", "webcam"): "demo-webcam-detection",
    ("demo", "mock"): "demo-webcam-detection-mock",
    ("demo", "rerun"): "demo-webcam-detection-mp-rerun",
    ("graph", "perception"): "docs-tutorial-perception-html",
    ("graph", "composable"): "docs-tutorial-composable-html",
}

PIXI_INSTALL_COMMAND = "curl -fsSL https://pixi.sh/install.sh | sh"
STARTER_PIXI = """[workspace]
channels = ["https://prefix.dev/conda-forge"]
platforms = ["osx-arm64", "linux-64", "win-64"]

[dependencies]
python = "3.11.*"
pip = "*"

[pypi-dependencies]
retriever-core = "*"

[tasks]
hello = "python main.py"
"""
STARTER_MAIN = """from dataclasses import dataclass

from retriever import Flow, Latest, Pipeline, Rate, Trigger, io


@io
@dataclass
class Number:
    value: int


@io
@dataclass
class Doubled:
    value: int


class Source(Flow[None, Number]):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def step(self, _inp: None = None) -> Number:
        self.count += 1
        return Number(self.count)


class Double(Flow[Number, Doubled]):
    def step(self, inp: Number) -> Doubled:
        return Doubled(inp.value * 2)


class Printer(Flow[Doubled, None]):
    def step(self, inp: Doubled) -> None:
        print(f"doubled={inp.value}")
        return None


pipe = Pipeline("hello-retriever")
with pipe:
    source = Source() @ Rate(hz=2)
    double = Double() @ Trigger("value")
    printer = Printer() @ Trigger("value")

    source.then(double, sync=Latest())
    double.then(printer, sync=Latest())

pipe.validate()
pipe.run(backend="in-process", duration=1.0)
"""
HELP = """Retriever CLI

Usage:
  retriever --version
  retriever init [path] [--bootstrap-pixi]
  retriever install [--bootstrap-pixi]
  retriever run <target-or-pixi-task> [-- task args...]
  retriever hub parse <ref> [--json]
  retriever hub inspect <ref> [--refresh] [--json]
  retriever hub cache-dir [--json]
  retriever tasks
  retriever --dry-run run <target-or-pixi-task> [-- task args...]

PyPI path:
  python -m pip install retriever-core
  retriever init my-retriever-app --bootstrap-pixi
  cd my-retriever-app
  retriever run hello

Source-checkout path (after `pip install retriever-core`):
  git clone https://github.com/openretriever/retriever
  cd retriever
  retriever install --bootstrap-pixi
  retriever run webcam-mock

Common source-checkout run targets:
  retriever run webcam-mock         # deterministic first smoke, no camera/GUI
  retriever run webcam              # live webcam with Rerun/stdout fallback
  retriever run graph               # render the perception tutorial graph
  retriever run perception-stepper  # step perception without camera/GUI
  retriever run record              # record a perception run
  retriever run replay              # replay the recorded Rerun artifact
  retriever run basic-flow          # smallest Flow tutorial

Hub commands:
  retriever hub parse openretriever/hello-world:HelloFlow
  retriever hub inspect openretriever/hello-world --json
  retriever hub cache-dir

Arguments after -- are passed to the task command.
"""


@dataclass(frozen=True)
class Command:
    action: str
    task: str | None = None
    path: Path | None = None
    args: tuple[str, ...] = ()
    dry_run: bool = False
    bootstrap_pixi: bool = False
    hub_command: str | None = None
    hub_ref: str | None = None
    refresh: bool = False
    json_output: bool = False


def package_version() -> str:
    # Resolve from whichever distribution installed the `retriever` package
    # (retriever-core or the interim debug-retriever), not a fixed dist name.
    from retriever import __version__

    return __version__


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


def _pop_global_flags(args: list[str]) -> tuple[bool, list[str]]:
    dry_run = False
    while args and args[0] == "--dry-run":
        dry_run = True
        args.pop(0)
    return dry_run, args


def _parse_init_command(args: list[str], *, dry_run: bool) -> Command:
    rest = [arg for arg in args[1:] if arg != "--bootstrap-pixi"]
    path = Path(rest[0]) if rest else Path("retriever-app")
    return Command(
        action="init",
        path=path,
        dry_run=dry_run,
        bootstrap_pixi="--bootstrap-pixi" in args[1:],
    )


def _parse_run_command(args: list[str], *, dry_run: bool) -> Command:
    if len(args) == 1:
        return Command(action="help", dry_run=dry_run)
    run_args = args[1:]
    if len(run_args) >= 2:
        compound = COMPOUND_RUN_TARGETS.get((run_args[0], run_args[1]))
        if compound is not None:
            return Command(
                action="run",
                task=compound,
                args=_strip_separator(run_args[2:]),
                dry_run=dry_run,
            )
    return Command(
        action="run",
        task=RUN_TARGETS.get(run_args[0], run_args[0]),
        args=_strip_separator(run_args[1:]),
        dry_run=dry_run,
    )


def parse_command(argv: Sequence[str]) -> Command:
    args = list(argv)
    dry_run, args = _pop_global_flags(args)

    if not args or args[0] in {"-h", "--help", "help"}:
        return Command(action="help", dry_run=dry_run)

    command = args[0]
    if command in {"--version", "version"}:
        return Command(action="version", dry_run=dry_run)
    if command in {"tasks", "list"}:
        return Command(action="tasks", dry_run=dry_run)
    if command == "hub":
        return _parse_hub_command(args[1:], dry_run=dry_run)
    if command == "init":
        return _parse_init_command(args, dry_run=dry_run)
    if command == "install":
        return Command(
            action="install",
            dry_run=dry_run,
            bootstrap_pixi="--bootstrap-pixi" in args[1:],
        )
    if command == "run":
        return _parse_run_command(args, dry_run=dry_run)

    return Command(action="error", dry_run=dry_run)


def _parse_hub_command(args: list[str], *, dry_run: bool) -> Command:
    json_output = "--json" in args
    refresh = "--refresh" in args
    rest = [arg for arg in args if arg not in {"--json", "--refresh"}]

    if not rest or rest[0] in {"-h", "--help", "help"}:
        return Command(action="help", dry_run=dry_run)

    subcommand = rest[0]
    if subcommand == "cache-dir":
        return Command(
            action="hub",
            hub_command="cache-dir",
            dry_run=dry_run,
            json_output=json_output,
        )

    if subcommand in {"parse", "inspect"}:
        if len(rest) < 2:
            return Command(action="help", dry_run=dry_run)
        return Command(
            action="hub",
            hub_command=subcommand,
            hub_ref=rest[1],
            dry_run=dry_run,
            refresh=refresh,
            json_output=json_output,
        )

    return Command(action="error", dry_run=dry_run)


def build_run_command(command: Command) -> list[str]:
    if command.task is None:
        raise ValueError("cannot build a run command without a task")
    return ["pixi", "run", command.task, *command.args]


def build_install_commands(command: Command) -> list[str]:
    commands = []
    if command.bootstrap_pixi:
        commands.append(PIXI_INSTALL_COMMAND)
    commands.append("pixi install")
    return commands


def render_tasks() -> str:
    rows = ["Retriever run targets for the source checkout:"]
    width = max(len(alias) for alias in RUN_TARGETS)
    for alias, task in sorted(RUN_TARGETS.items()):
        rows.append(f"  {alias:<{width}}  ->  {task}")
    rows.append("")
    rows.append("Source checkout task escape hatch: retriever run <task>")
    return "\n".join(rows)


def _pixi_executable() -> str | None:
    found = shutil.which("pixi")
    if found is not None:
        return found
    for candidate in (
        Path.home() / ".pixi" / "bin" / "pixi",
        Path.home() / ".local" / "bin" / "pixi",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _ensure_pixi(command: Command) -> str | None:
    pixi = _pixi_executable()
    if pixi is not None:
        return pixi
    if not command.bootstrap_pixi:
        print(
            "retriever: Pixi is not installed. Install it yourself or rerun with "
            "--bootstrap-pixi to use the official Pixi installer.",
            file=sys.stderr,
        )
        print(f"manual Pixi installer: {PIXI_INSTALL_COMMAND}", file=sys.stderr)
        return None
    code = subprocess.call(["sh", "-c", PIXI_INSTALL_COMMAND])
    if code != 0:
        return None
    pixi = _pixi_executable()
    if pixi is None:
        print(
            "retriever: Pixi installer finished, but `pixi` was not found in "
            "PATH, ~/.pixi/bin, or ~/.local/bin. Restart your shell, then run "
            "`retriever install`.",
            file=sys.stderr,
        )
    return pixi


def _run_install(command: Command, workspace: Path) -> int:
    if command.dry_run:
        print("\n".join(build_install_commands(command)))
        return 0

    pixi = _ensure_pixi(command)
    if pixi is None:
        return 2

    return subprocess.call([pixi, "install"], cwd=str(workspace))


def _run_init(command: Command) -> int:
    target = (command.path or Path("retriever-app")).resolve()
    if command.dry_run:
        print(f"mkdir -p {target}")
        print(f"write {target / 'pixi.toml'}")
        print(f"write {target / 'main.py'}")
        for line in build_install_commands(command):
            print(line)
        return 0

    target.mkdir(parents=True, exist_ok=True)
    pixi_file = target / "pixi.toml"
    main_file = target / "main.py"
    if pixi_file.exists() or main_file.exists():
        print(
            "retriever: refusing to overwrite existing pixi.toml or main.py in "
            f"{target}",
            file=sys.stderr,
        )
        return 2
    pixi_file.write_text(STARTER_PIXI, encoding="utf-8")
    main_file.write_text(STARTER_MAIN, encoding="utf-8")
    print(f"created Retriever starter workspace: {target}")
    return _run_install(command, target)


def _format_hub_ref(ref: str) -> dict[str, Any]:
    from retriever.hub._ref import parse_ref

    parsed = parse_ref(ref)
    return {
        "ref": ref,
        "org": parsed.org,
        "name": parsed.name,
        "attribute": parsed.attribute,
        "version": parsed.version,
    }


def _describe_hub_object(ref: str, *, refresh: bool = False) -> dict[str, Any]:
    from retriever import hub
    from retriever.hub._loader import ModuleProxy

    obj = hub.use(ref, refresh=refresh)
    data = _format_hub_ref(ref)
    data["repr"] = repr(obj)

    if isinstance(obj, ModuleProxy):
        data["kind"] = "module"
        data["exports"] = sorted(dir(obj))
        return data

    data["kind"] = "export"
    data["type"] = type(obj).__name__
    data["module"] = getattr(obj, "__module__", None)
    data["qualname"] = getattr(obj, "__qualname__", getattr(obj, "__name__", None))
    return data


def _print_hub_data(data: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    for key in ("ref", "org", "name", "attribute", "version", "kind", "type", "module", "qualname"):
        if key in data and data[key] is not None:
            print(f"{key}: {data[key]}")
    if "exports" in data:
        print("exports:")
        for export in data["exports"]:
            print(f"  - {export}")
    if "cache_dir" in data:
        print(f"cache_dir: {data['cache_dir']}")
    if "repr" in data:
        print(f"repr: {data['repr']}")


def _run_hub_command(command: Command) -> int:
    from retriever.error import HubError
    from retriever.hub._cache import cache_root

    try:
        if command.hub_command == "cache-dir":
            _print_hub_data(
                {"cache_dir": str(cache_root())},
                json_output=command.json_output,
            )
            return 0

        if command.hub_ref is None:
            print(HELP, file=sys.stderr)
            return 2

        if command.hub_command == "parse":
            _print_hub_data(
                _format_hub_ref(command.hub_ref),
                json_output=command.json_output,
            )
            return 0

        if command.hub_command == "inspect":
            if command.dry_run:
                data = _format_hub_ref(command.hub_ref)
                data["dry_run"] = True
                data["would_call"] = "retriever.hub.use"
            else:
                data = _describe_hub_object(command.hub_ref, refresh=command.refresh)
            _print_hub_data(data, json_output=command.json_output)
            return 0
    except HubError as exc:
        print(f"retriever hub: {exc}", file=sys.stderr)
        return 2

    print(HELP, file=sys.stderr)
    return 2


def _run_workspace_action(command: Command, workspace: Path) -> int:
    if command.action == "install":
        return _run_install(command, workspace)

    if command.action != "run":
        print(HELP, file=sys.stderr)
        return 2

    run_command = build_run_command(command)
    if command.dry_run:
        print(" ".join(run_command))
        return 0

    pixi = _pixi_executable()
    if pixi is None:
        print(
            "retriever: Pixi is not installed. Run `retriever install --bootstrap-pixi` "
            "from this workspace first.",
            file=sys.stderr,
        )
        return 2
    run_command[0] = pixi
    return subprocess.call(run_command, cwd=str(workspace))


def main(argv: Sequence[str] | None = None) -> int:
    command = parse_command(sys.argv[1:] if argv is None else argv)

    if command.action == "help":
        print(HELP)
        return 0
    if command.action == "version":
        print(package_version())
        return 0
    if command.action == "tasks":
        print(render_tasks())
        return 0
    if command.action == "error":
        print(HELP, file=sys.stderr)
        return 2
    if command.action == "hub":
        return _run_hub_command(command)
    if command.action == "init":
        return _run_init(command)

    workspace = find_pixi_workspace()
    if workspace is None:
        print(
            "retriever: no pixi.toml found in this directory or its parents. "
            "Use `retriever init <path>` for a new package workspace, or run from "
            "a Retriever source checkout for repository demos.",
            file=sys.stderr,
        )
        return 2

    return _run_workspace_action(command, workspace)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
