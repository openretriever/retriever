import ast
import json
from pathlib import Path

from retriever.cli import (
    STARTER_MAIN,
    build_install_commands,
    build_run_command,
    find_pixi_workspace,
    parse_command,
)


def test_cli_run_target_wraps_visual_quickstart() -> None:
    command = parse_command(["run", "webcam-mock"])

    assert build_run_command(command) == [
        "pixi",
        "run",
        "demo-webcam-detection-mock",
    ]


def test_cli_run_forwards_raw_pixi_task_and_args() -> None:
    command = parse_command([
        "run",
        "demo-webcam-detection",
        "--",
        "--duration",
        "1",
    ])

    assert build_run_command(command) == [
        "pixi",
        "run",
        "demo-webcam-detection",
        "--duration",
        "1",
    ]


def test_cli_accepts_compound_run_targets() -> None:
    command = parse_command(["run", "graph", "composable"])

    assert build_run_command(command) == [
        "pixi",
        "run",
        "docs-tutorial-composable-html",
    ]


def test_cli_exposes_documented_perception_stepper_target() -> None:
    command = parse_command(["run", "perception-stepper"])

    assert build_run_command(command) == [
        "pixi",
        "run",
        "demo-perception-stepper",
    ]


def test_cli_exposes_runtime_execution_target() -> None:
    command = parse_command(["run", "rt-execution"])

    assert build_run_command(command) == [
        "pixi",
        "run",
        "demo-rt-execution",
    ]


def test_cli_exposes_runtime_guide_targets() -> None:
    expected = {
        "ir-validation": "demo-ir-validation",
        "multirate": "demo-multirate",
        "webcam-dora": "demo-webcam-detection-dora",
        "record-replay": "demo-record-replay",
        "incident-replay": "demo-incident-replay",
        "composable-pipelines": "demo-composable-pipelines",
    }

    for target, task in expected.items():
        assert build_run_command(parse_command(["run", target])) == [
            "pixi",
            "run",
            task,
        ]


def test_cli_install_can_bootstrap_pixi() -> None:
    command = parse_command(["install", "--bootstrap-pixi"])

    assert build_install_commands(command) == [
        "curl -fsSL https://pixi.sh/install.sh | sh",
        "pixi install",
    ]


def test_cli_init_can_bootstrap_pixi() -> None:
    command = parse_command(["init", "robot-app", "--bootstrap-pixi"])

    assert command.action == "init"
    assert command.path == Path("robot-app")
    assert build_install_commands(command) == [
        "curl -fsSL https://pixi.sh/install.sh | sh",
        "pixi install",
    ]


def test_cli_finds_nearest_pixi_workspace(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    child = root / "a" / "b"
    child.mkdir(parents=True)
    (root / "pixi.toml").write_text("[tasks]\n", encoding="utf-8")

    assert find_pixi_workspace(child) == root


def test_cli_starter_main_is_valid_python() -> None:
    ast.parse(STARTER_MAIN)


def test_cli_unknown_command_is_an_error() -> None:
    command = parse_command(["steper"])

    assert command.action == "error"


def test_cli_parses_hub_parse_command() -> None:
    command = parse_command(["hub", "parse", "openretriever/hello-world:HelloFlow@0.1.0", "--json"])

    assert command.action == "hub"
    assert command.hub_command == "parse"
    assert command.hub_ref == "openretriever/hello-world:HelloFlow@0.1.0"
    assert command.json_output is True


def test_cli_parses_hub_inspect_refresh_command() -> None:
    command = parse_command(["hub", "inspect", "openretriever/hello-world", "--refresh"])

    assert command.action == "hub"
    assert command.hub_command == "inspect"
    assert command.hub_ref == "openretriever/hello-world"
    assert command.refresh is True


def test_cli_parses_hub_cache_dir_command() -> None:
    command = parse_command(["hub", "cache-dir"])

    assert command.action == "hub"
    assert command.hub_command == "cache-dir"


def test_cli_hub_parse_prints_json(capsys) -> None:
    from retriever.cli import main

    assert main(["hub", "parse", "openretriever/hello-world:HelloFlow", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "attribute": "HelloFlow",
        "name": "hello-world",
        "org": "openretriever",
        "ref": "openretriever/hello-world:HelloFlow",
        "version": None,
    }
