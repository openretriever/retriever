import ast
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
