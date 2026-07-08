from pathlib import Path

from retriever.cli import build_pixi_command, find_pixi_workspace, parse_command


def test_cli_alias_wraps_visual_quickstart() -> None:
    command = parse_command(["webcam-mock"])

    assert build_pixi_command(command) == [
        "pixi",
        "run",
        "demo-webcam-detection-mock",
    ]


def test_cli_forwards_raw_pixi_task_and_args() -> None:
    command = parse_command([
        "run",
        "demo-webcam-detection",
        "--",
        "--duration",
        "1",
    ])

    assert build_pixi_command(command) == [
        "pixi",
        "run",
        "demo-webcam-detection",
        "--duration",
        "1",
    ]


def test_cli_accepts_compound_aliases() -> None:
    command = parse_command(["graph", "composable"])

    assert build_pixi_command(command) == [
        "pixi",
        "run",
        "docs-tutorial-composable-html",
    ]


def test_cli_finds_nearest_pixi_workspace(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    child = root / "a" / "b"
    child.mkdir(parents=True)
    (root / "pixi.toml").write_text("[tasks]\n", encoding="utf-8")

    assert find_pixi_workspace(child) == root
