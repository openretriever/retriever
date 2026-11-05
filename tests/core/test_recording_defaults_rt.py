"""Keep the public replay entry points on their established RRD defaults."""
import importlib
from pathlib import Path
import sys
import tomllib

from retriever.cli import build_run_command, parse_command


def test_replay_example_keeps_rrd_default(monkeypatch):
    module = importlib.import_module(
        "examples.tutorial.c_debug_and_replay.04_record_replay_perception"
    )
    monkeypatch.setattr(sys, "argv", ["record-replay", "replay"])
    assert module.parse_args().recording == Path("logs/perception.rrd")


def test_record_replay_task_keeps_rrd_default():
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pixi.toml").read_text())
    task = config["tasks"]["demo-record-replay"]
    if isinstance(task, dict):
        task = task["cmd"]
    assert "replay --recording logs/perception.rrd" in task
    assert build_run_command(parse_command(["run", "replay"])) == [
        "pixi", "run", "demo-webcam-replay-rrd"
    ]
