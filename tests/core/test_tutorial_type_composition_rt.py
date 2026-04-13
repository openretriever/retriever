from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _example_env() -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}"
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


def test_spatial_type_boundaries_runs_without_envelope_wrapper() -> None:
    result = _run_script('examples/tutorial/g_operations_interfaces/05_spatial_type_boundaries.py')
    assert result.returncode == 0, result.stderr
    assert 'Registry Parity' in result.stdout
    assert 'Boundary Walkthrough' in result.stdout


def test_multirate_robot_system_runs_with_composite_control_input() -> None:
    result = _run_script(
        'examples/tutorial/e_resource_and_sync/03_multirate_robot_system.py',
        '--backend', 'multiprocessing',
        '--duration', '0.5',
    )
    assert result.returncode == 0, result.stderr
    assert 'err_x=' in result.stdout
