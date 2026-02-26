#!/usr/bin/env python3
"""
Validate Retriever Flow typing signatures for Hub preflight.

Default policy (v2):
- allow tuple-literal input/output: Flow[(A, B), C], Flow[A, (C, D)]
- allow typing tuple forms: Flow[tuple[A, B], C], Flow[A, tuple[C, D]]
- enforce local type compatibility: local generic element classes must use @io/@flow_io
- reject mixed tuple/None elements (e.g. (A, None))

Strict policy (`--strict-single-io`):
- require single-envelope input/output signatures (no tuple composites)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List


FLOW_IO_DECORATORS = {"io", "flow_io"}
TUPLE_NAMES = {"tuple", "Tuple", "typing.Tuple"}


@dataclass
class Violation:
    severity: str  # "error" | "warn"
    code: str
    message: str
    path: str
    line: int
    class_name: str


@dataclass
class Report:
    files_scanned: int
    flow_classes_scanned: int
    errors: list[Violation]
    warnings: list[Violation]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict:
        return {
            "files_scanned": self.files_scanned,
            "flow_classes_scanned": self.flow_classes_scanned,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [asdict(v) for v in self.errors],
            "warnings": [asdict(v) for v in self.warnings],
            "typing_contract_version": "hub.flow-typing.v2",
        }


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr
    return None


def is_decorator_flow_io(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        name = dotted_name(node.func)
    else:
        name = dotted_name(node)
    if not name:
        return False
    return name.split(".")[-1] in FLOW_IO_DECORATORS


def is_tuple_type_expr(node: ast.AST) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    name = dotted_name(node.value)
    if not name:
        return False
    if name in TUPLE_NAMES:
        return True
    return name.split(".")[-1] in {"tuple", "Tuple"}


def is_none_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is None
    if isinstance(node, ast.Name):
        return node.id == "None"
    return False


def tuple_type_args(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Tuple):
        return list(node.elts)
    if is_tuple_type_expr(node):
        assert isinstance(node, ast.Subscript)
        sl = node.slice
        if isinstance(sl, ast.Tuple):
            return list(sl.elts)
        return [sl]
    return [node]


def normalize_type_expr(node: ast.AST) -> list[ast.AST]:
    if is_none_expr(node):
        return []
    return tuple_type_args(node)


def iter_python_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            files.append(p)
    files.sort()
    return files


def _add_error(
    errors: list[Violation],
    *,
    code: str,
    message: str,
    rel_path: str,
    line: int,
    class_name: str,
) -> None:
    errors.append(
        Violation(
            severity="error",
            code=code,
            message=message,
            path=rel_path,
            line=line,
            class_name=class_name,
        )
    )


def _check_local_io_compatibility(
    *,
    errors: list[Violation],
    rel_path: str,
    class_name: str,
    line: int,
    type_exprs: list[ast.AST],
    local_classes: set[str],
    local_io_types: set[str],
) -> None:
    for expr in type_exprs:
        if is_none_expr(expr):
            continue
        name = dotted_name(expr)
        if not name:
            continue
        tail = name.split(".")[-1]
        if tail in local_classes and tail not in local_io_types:
            _add_error(
                errors,
                code="LOCAL_TYPE_NOT_FLOW_IO",
                message=f"Local type '{tail}' used in Flow generic must use @io/@flow_io",
                rel_path=rel_path,
                line=line,
                class_name=class_name,
            )


def _check_tuple_none_mix(
    *,
    errors: list[Violation],
    rel_path: str,
    class_name: str,
    line: int,
    expr: ast.AST,
    side: str,
) -> None:
    elems = tuple_type_args(expr)
    if len(elems) <= 1:
        return
    none_count = sum(1 for e in elems if is_none_expr(e))
    if 0 < none_count < len(elems):
        _add_error(
            errors,
            code="MIXED_NONE_TUPLE_INVALID",
            message=f"{side} tuple generic cannot mix None with other element types",
            rel_path=rel_path,
            line=line,
            class_name=class_name,
        )


def analyze_file(path: Path, strict_single_io: bool, workspace_root: Path) -> tuple[int, list[Violation], list[Violation]]:
    try:
        rel_path = str(path.resolve().relative_to(workspace_root.resolve()))
    except ValueError:
        rel_path = str(path)
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=rel_path)

    local_io_types: set[str] = set()
    local_classes: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            local_classes.add(node.name)
            if any(is_decorator_flow_io(d) for d in node.decorator_list):
                local_io_types.add(node.name)

    errors: list[Violation] = []
    warnings: list[Violation] = []
    flow_classes_scanned = 0

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        flow_base: ast.Subscript | None = None
        for base in node.bases:
            if not isinstance(base, ast.Subscript):
                continue
            base_name = dotted_name(base.value) or ""
            if base_name.split(".")[-1] == "Flow":
                flow_base = base
                break

        if flow_base is None:
            continue

        flow_classes_scanned += 1
        sl = flow_base.slice
        if not isinstance(sl, ast.Tuple) or len(sl.elts) < 2:
            _add_error(
                errors,
                code="FLOW_GENERIC_MISSING",
                message="Flow must declare two generic parameters: Flow[Input, Output]",
                rel_path=rel_path,
                line=node.lineno,
                class_name=node.name,
            )
            continue

        input_expr = sl.elts[0]
        output_expr = sl.elts[1]

        _check_tuple_none_mix(
            errors=errors,
            rel_path=rel_path,
            class_name=node.name,
            line=node.lineno,
            expr=input_expr,
            side="Input",
        )
        _check_tuple_none_mix(
            errors=errors,
            rel_path=rel_path,
            class_name=node.name,
            line=node.lineno,
            expr=output_expr,
            side="Output",
        )

        in_elems = normalize_type_expr(input_expr)
        out_elems = normalize_type_expr(output_expr)

        _check_local_io_compatibility(
            errors=errors,
            rel_path=rel_path,
            class_name=node.name,
            line=node.lineno,
            type_exprs=in_elems + out_elems,
            local_classes=local_classes,
            local_io_types=local_io_types,
        )

        if strict_single_io:
            if len(in_elems) > 1:
                _add_error(
                    errors,
                    code="STRICT_SINGLE_IO_INPUT",
                    message="Strict mode requires single-envelope Flow input type",
                    rel_path=rel_path,
                    line=node.lineno,
                    class_name=node.name,
                )
            if len(out_elems) > 1:
                _add_error(
                    errors,
                    code="STRICT_SINGLE_IO_OUTPUT",
                    message="Strict mode requires single-envelope Flow output type",
                    rel_path=rel_path,
                    line=node.lineno,
                    class_name=node.name,
                )

    return flow_classes_scanned, errors, warnings


def print_report(report: Report) -> None:
    print("=== Flow Typing Validation Report ===")
    print(f"files scanned: {report.files_scanned}")
    print(f"flow classes: {report.flow_classes_scanned}")
    print(f"errors: {report.error_count}")
    print(f"warnings: {report.warning_count}")
    print()

    for v in report.errors:
        print(f"[ERROR] {v.code} {v.path}:{v.line} ({v.class_name})")
        print(f"  {v.message}")
    for v in report.warnings:
        print(f"[WARN ] {v.code} {v.path}:{v.line} ({v.class_name})")
        print(f"  {v.message}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Flow typing signatures")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Root directory to scan (repeatable). Defaults to src + examples + tests",
    )
    parser.add_argument(
        "--strict-single-io",
        action="store_true",
        help="Require single-envelope input/output (reject tuple composite signatures).",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional JSON output path for CI artifacts",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    workspace_root = Path(__file__).resolve().parents[1]

    roots = [Path(r) for r in args.root] if args.root else [
        workspace_root / "src",
        workspace_root / "examples",
        workspace_root / "tests",
    ]
    py_files = iter_python_files(roots)

    total_flow_classes = 0
    errors: List[Violation] = []
    warnings: List[Violation] = []

    for path in py_files:
        count, errs, warns = analyze_file(
            path,
            strict_single_io=args.strict_single_io,
            workspace_root=workspace_root,
        )
        total_flow_classes += count
        errors.extend(errs)
        warnings.extend(warns)

    report = Report(
        files_scanned=len(py_files),
        flow_classes_scanned=total_flow_classes,
        errors=errors,
        warnings=warnings,
    )
    print_report(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return 1 if report.error_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

