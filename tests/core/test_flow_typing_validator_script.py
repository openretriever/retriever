from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_validator(root: Path, strict: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "scripts/quality/validate_flow_typing.py",
        "--root",
        str(root),
    ]
    if strict:
        cmd.append("--strict-single-io")
    return subprocess.run(cmd, cwd=_repo_root(), capture_output=True, text=True)


def test_validator_allows_tuple_literal_and_tuple_output_by_default(tmp_path: Path) -> None:
    src = tmp_path / "tuple_allowed.py"
    src.write_text(
        """
from dataclasses import dataclass
from retriever.flow import Flow, io

@io
class A:
    a: int | None = None

@io
class B:
    b: int | None = None

@io
class C:
    c: int | None = None

@io
class D:
    d: int | None = None

class F1(Flow[(A, B), C]):
    def step(self, input):
        return C(c=1)

class F2(Flow[A, tuple[C, D]]):
    def step(self, input):
        return (C(c=1), D(d=2))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_validator(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "errors: 0" in result.stdout


def test_validator_rejects_local_non_io_types(tmp_path: Path) -> None:
    src = tmp_path / "bad_local_type.py"
    src.write_text(
        """
from dataclasses import dataclass
from retriever.flow import Flow, io

@io
class A:
    a: int | None = None

@dataclass
class NotIO:
    x: int | None = None

class Bad(Flow[(A, NotIO), A]):
    def step(self, input):
        return A(a=1)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_validator(tmp_path)
    assert result.returncode == 1
    assert "LOCAL_TYPE_NOT_FLOW_IO" in result.stdout


def test_validator_rejects_mixed_none_tuple(tmp_path: Path) -> None:
    src = tmp_path / "mixed_none_tuple.py"
    src.write_text(
        """
from dataclasses import dataclass
from retriever.flow import Flow, io

@io
class A:
    a: int | None = None

@io
class C:
    c: int | None = None

class Bad(Flow[(A, None), C]):
    def step(self, input):
        return C(c=1)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_validator(tmp_path)
    assert result.returncode == 1
    assert "MIXED_NONE_TUPLE_INVALID" in result.stdout


def test_validator_strict_mode_rejects_tuple_input_and_output(tmp_path: Path) -> None:
    src = tmp_path / "strict_tuple.py"
    src.write_text(
        """
from dataclasses import dataclass
from retriever.flow import Flow, io

@io
class A:
    a: int | None = None

@io
class B:
    b: int | None = None

@io
class C:
    c: int | None = None

class F(Flow[(A, B), (C, C)]):
    def step(self, input):
        return (C(c=1), C(c=2))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_validator(tmp_path, strict=True)
    assert result.returncode == 1
    assert "STRICT_SINGLE_IO_INPUT" in result.stdout
    assert "STRICT_SINGLE_IO_OUTPUT" in result.stdout

