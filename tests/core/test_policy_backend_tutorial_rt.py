from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _example_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}"
    return env


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, 'examples/tutorial/f_policy_backends/01_closed_loop_policy_backend_abstraction.py', *args],
        cwd=REPO_ROOT,
        env=_example_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_policy_backend_tutorial_help_runs() -> None:
    result = _run_script('--help')
    assert result.returncode == 0, result.stderr
    assert 'Closed-loop policy backend abstraction tutorial' in result.stdout
    assert '--backends' in result.stdout


def test_policy_backend_tutorial_emits_console_and_optional_artifacts(tmp_path: Path) -> None:
    csv_path = tmp_path / 'metrics.csv'
    json_path = tmp_path / 'metrics.json'

    result = _run_script(
        '--steps', '4',
        '--out-csv', str(csv_path),
        '--out-json', str(json_path),
    )
    assert result.returncode == 0, result.stderr
    assert '[Contract]' in result.stdout
    assert 'First-step Action Preview' in result.stdout
    assert 'Backend Comparison (optional evidence)' in result.stdout
    assert csv_path.exists() and csv_path.stat().st_size > 0
    assert json_path.exists() and json_path.stat().st_size > 0

    payload = json.loads(json_path.read_text(encoding='utf-8'))
    backends = {row['backend'] for row in payload['metrics']}
    assert backends == {'openpi_pi05', 'lerobot', 'mock'}
    assert payload['steps'] == 4

    csv_rows = csv_path.read_text(encoding='utf-8').strip().splitlines()
    assert csv_rows[0] == 'backend,mean_ms,p95_ms,mean_chunk_len,mean_abs_action'
    assert {row.split(',')[0] for row in csv_rows[1:]} == {'openpi_pi05', 'lerobot', 'mock'}
