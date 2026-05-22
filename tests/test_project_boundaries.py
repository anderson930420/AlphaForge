from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "alphaforge"


def test_alphaforge_runtime_does_not_import_signalforge() -> None:
    violations: list[str] = []

    for source_path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_signalforge_module(alias.name):
                        violations.append(f"{source_path}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if _is_signalforge_module(node.module):
                    violations.append(f"{source_path}:{node.lineno}: from {node.module} import ...")

    assert violations == []


def _is_signalforge_module(module_name: str) -> bool:
    return module_name == "signalforge" or module_name.startswith("signalforge.")
