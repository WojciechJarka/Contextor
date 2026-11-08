from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

CHILD_CODE = r"""
import importlib
import json
import sys
import traceback

entry = sys.argv[1]
root = sys.argv[2]
sys.path.insert(0, root)

try:
    importlib.import_module(entry)

    from contextor.repo_generator import run_repo_generator
    from contextor.ui import run

    if not callable(run_repo_generator):
        raise AssertionError("Generator export is not callable")

    if not callable(run):
        raise AssertionError("UI export is not callable")

except BaseException as exc:
    print(json.dumps({
        "entry": entry,
        "status": "EXCEPTION",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc(),
    }, ensure_ascii=False))
    sys.exit(1)

print(json.dumps({
    "entry": entry,
    "status": "PASS",
    "generator_export": True,
    "ui_export": True,
}, ensure_ascii=False))
"""


@pytest.mark.parametrize(
    "entry",
    (
        "contextor.repo_generator",
        "contextor.ui",
    ),
)
def test_scc2_fresh_import_order(entry):
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CHILD_CODE,
            entry,
            str(ROOT),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        check=False,
    )

    assert completed.returncode == 0, (
        f"entry={entry}\n"
        f"stdout={completed.stdout}\n"
        f"stderr={completed.stderr}"
    )

    result = json.loads(completed.stdout.strip())

    assert result == {
        "entry": entry,
        "status": "PASS",
        "generator_export": True,
        "ui_export": True,
    }


def test_scc2_gui_generator_import_remains_method_scoped():
    path = ROOT / "contextor" / "ui" / "gui.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    def matching_import(node):
        return (
            isinstance(node, ast.ImportFrom)
            and node.module == "contextor.repo_generator"
            and any(
                alias.name == "run_repo_generator"
                for alias in node.names
            )
        )

    assert not any(
        matching_import(node)
        for node in tree.body
    )

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ContextorGUI"
    ]
    assert len(classes) == 1

    methods = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
        and node.name == "open_repo_builder"
    ]
    assert len(methods) == 1

    imports = [
        node
        for node in ast.walk(methods[0])
        if matching_import(node)
    ]
    assert len(imports) == 1
