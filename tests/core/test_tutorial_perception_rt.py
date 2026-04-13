from __future__ import annotations

import os
import importlib
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _example_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}"
    return env


def _run_script(script_rel: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, script_rel, *args],
        cwd=REPO_ROOT,
        env=_example_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_webcam_demo_help_runs() -> None:
    result = _run_script('examples/tutorial/b_ir_and_execution/06_dora_perception.py', '--help')
    assert result.returncode == 0, result.stderr
    assert 'Perception runtime demo' in result.stdout




def test_webcam_demo_auto_visualization_defaults_to_stdout() -> None:
    mod = importlib.import_module('examples.tutorial.b_ir_and_execution.06_dora_perception')
    show_window, use_rerun = mod._resolve_visualization(SimpleNamespace(visualize='auto', backend='in-process'))
    assert show_window is False
    assert use_rerun is False


def test_webcam_demo_auto_camera_mode_falls_back_without_camera(monkeypatch) -> None:
    mod = importlib.import_module('examples.tutorial.b_ir_and_execution.06_dora_perception')
    monkeypatch.setattr(mod, '_camera_available', lambda index: False)
    use_real = mod._resolve_camera_mode(SimpleNamespace(camera_mode='auto', camera_index=0))
    assert use_real is False


def test_webcam_demo_real_camera_mode_stays_explicit(monkeypatch) -> None:
    mod = importlib.import_module('examples.tutorial.b_ir_and_execution.06_dora_perception')
    monkeypatch.setattr(mod, '_camera_available', lambda index: False)
    use_real = mod._resolve_camera_mode(SimpleNamespace(camera_mode='real', camera_index=0))
    assert use_real is True

def test_record_replay_cli_help_runs() -> None:
    result = _run_script('examples/tutorial/c_debug_and_replay/04_record_replay_perception.py', '--help')
    assert result.returncode == 0, result.stderr
    assert 'record' in result.stdout
    assert 'replay' in result.stdout


def test_record_replay_cli_roundtrip_emits_rrd_and_mcap(tmp_path: Path) -> None:
    pytest.importorskip('rerun')

    rrd_path = tmp_path / 'perception.rrd'
    mcap_path = tmp_path / 'perception.mcap'

    record = _run_script(
        'examples/tutorial/c_debug_and_replay/04_record_replay_perception.py',
        'record',
        '--out', str(rrd_path),
        '--replay-out', str(mcap_path),
        '--camera-mode', 'mock',
        '--steps', '3',
        '--dt', '0.01',
        '--sleep', '0.0',
    )
    assert record.returncode == 0, record.stderr
    assert rrd_path.exists() and rrd_path.stat().st_size > 0
    assert mcap_path.exists() and mcap_path.stat().st_size > 0

    replay_rrd = _run_script(
        'examples/tutorial/c_debug_and_replay/04_record_replay_perception.py',
        'replay',
        '--recording', str(rrd_path),
        '--steps', '3',
        '--dt', '0.01',
        '--sleep', '0.0',
        '--visualize', 'stdout',
    )
    assert replay_rrd.returncode == 0, replay_rrd.stderr

    replay_mcap = _run_script(
        'examples/tutorial/c_debug_and_replay/04_record_replay_perception.py',
        'replay',
        '--recording', str(mcap_path),
        '--steps', '3',
        '--dt', '0.01',
        '--sleep', '0.0',
        '--visualize', 'stdout',
    )
    assert replay_mcap.returncode == 0, replay_mcap.stderr
