import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def _find_mock_calls_in_file(file_path: Path) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(ast.parse(file_path.read_text()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Mock"
    ]


def _find_all_mock_calls() -> dict[Path, list[ast.Call]]:
    mock_calls: dict[Path, list[ast.Call]] = {}
    for tests_dir in ROOT.rglob("tests"):
        if not tests_dir.is_dir():
            continue
        for py_file in tests_dir.rglob("*.py"):
            if calls := _find_mock_calls_in_file(py_file):
                mock_calls[py_file] = calls
    return mock_calls


def _is_suppressed(path: Path, lineno: int) -> bool:
    line = path.read_text().splitlines()[lineno - 1]
    return line.endswith("# test: allow-specless-mock")


def test_find_all_mock_calls() -> None:
    for path, calls in _find_all_mock_calls().items():
        for call in calls:
            if not (call.args or _is_suppressed(path, call.lineno)):
                msg = f"{path.relative_to(ROOT)}:{call.lineno} -> specless mock found"
                pytest.fail(msg)
