from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class _ConnectVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.offenders: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "connect":
            if not any(keyword.arg == "sync" for keyword in node.keywords):
                self.offenders.append(node.lineno)
        self.generic_visit(node)


def test_tutorial_examples_use_explicit_sync_on_pipe_connect() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / "examples" / "tutorial").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _ConnectVisitor()
        visitor.visit(tree)
        offenders.extend(f"{path.relative_to(REPO_ROOT)}:{line}" for line in visitor.offenders)
    assert offenders == []
