import ast
import json
from pathlib import Path

from retriever.cli import (
    STARTER_MAIN,
    WEBCAM_HUB_REF,
    build_demo_invocation,
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


def test_cli_parses_no_clone_webcam_demo() -> None:
    command = parse_command([
        "demo",
        "webcam",
        "--seconds",
        "60",
        "--hz",
        "15",
        "--camera-index",
        "2",
        "--visualize",
        "rerun",
        "--refresh",
        "--no-rerun-spawn",
    ])

    assert command.action == "demo"
    assert command.demo_name == "webcam"
    assert command.refresh is True
    assert build_demo_invocation(command) == (
        WEBCAM_HUB_REF,
        {
            "seconds": 60.0,
            "hz": 15.0,
            "camera_index": 2,
            "visualize": "rerun",
            "rerun_spawn": False,
        },
    )


def test_cli_demo_webcam_runs_hub_without_pixi(tmp_path: Path, monkeypatch) -> None:
    from retriever import cli

    calls = {}

    def fake_hub_use(ref: str, *, refresh: bool = False):
        calls["ref"] = ref
        calls["refresh"] = refresh

        def run(**kwargs):
            calls["kwargs"] = kwargs

        return run

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_hub_use", fake_hub_use)
    monkeypatch.setattr(cli, "_ensure_rerun_available", lambda command: True)

    assert (tmp_path / "pixi.toml").exists() is False
    assert cli.main([
        "demo",
        "webcam",
        "--seconds",
        "1",
        "--hz",
        "5",
        "--camera-index",
        "2",
        "--visualize",
        "both",
        "--refresh",
        "--no-rerun-spawn",
    ]) == 0

    assert calls == {
        "ref": WEBCAM_HUB_REF,
        "refresh": True,
        "kwargs": {
            "seconds": 1.0,
            "hz": 5.0,
            "camera_index": 2,
            "visualize": "both",
            "rerun_spawn": False,
        },
    }


def test_cli_demo_webcam_help_after_subcommand() -> None:
    assert parse_command(["demo", "webcam", "--help"]).action == "help"
    assert parse_command(["demo", "webcam", "help"]).action == "help"


def test_cli_demo_webcam_rejects_malformed_numeric_flags() -> None:
    bad_argvs = [
        ["demo", "webcam", "--seconds", "abc"],
        ["demo", "webcam", "--hz", "abc"],
        ["demo", "webcam", "--camera-index", "abc"],
    ]

    for argv in bad_argvs:
        assert parse_command(argv).action == "error"


def test_cli_demo_webcam_checks_rerun_before_loading_hub(monkeypatch) -> None:
    from retriever import cli

    def fail_hub_use(ref: str, *, refresh: bool = False):  # pragma: no cover
        raise AssertionError("hub should not load when rerun-sdk is missing")

    monkeypatch.setattr(cli, "_hub_use", fail_hub_use)
    monkeypatch.setattr(cli, "_ensure_rerun_available", lambda command: False)

    assert cli.main(["demo", "webcam", "--visualize", "rerun"]) == 2


def test_cli_demo_webcam_dry_run_prints_hub_call(capsys) -> None:
    from retriever.cli import main

    assert main(["--dry-run", "demo", "webcam", "--seconds", "0"]) == 0

    out = capsys.readouterr().out
    assert "hub.use('openretriever/webcam-demo:run', refresh=False)" in out
    assert "seconds=0.0" in out


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
