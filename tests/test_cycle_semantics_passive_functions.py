"""CPython parity for passive function definitions in package imports."""

import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(sources, entry):
    return evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        entry,
    )


def _actual(tmp_path, sources, entry):
    for module, source in sources.items():
        parts = module.split(".")
        path = tmp_path.joinpath(
            *parts[:-1],
            "__init__.py"
            if parts[-1] == "__init__"
            else parts[-1] + ".py",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source + "\n", encoding="utf-8")

    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            (
                "import importlib,sys;"
                "sys.path.insert(0,sys.argv[1]);"
                "importlib.import_module(sys.argv[2])"
            ),
            str(tmp_path),
            entry,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_c23_positional_default_opaque_binding(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": 'def f(value=None):\n    raise RuntimeError("not called")',
    }
    result = _model(sources, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "f"
        for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_c23_keyword_only_default_opaque_binding(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "def run(*, single_instance=None):\n"
            '    raise RuntimeError("not called")'
        ),
    }
    result = _model(sources, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "run"
        for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_c23_zero_arg_opaque_body_not_executed(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "def f():\n    dangerous()",
    }
    result = _model(sources, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(event.operation == "DEFINE_OPAQUE_FUNCTION" for event in result.events)
    assert not any(event.operation == "CALL_FUNCTION" for event in result.events)
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_c23_existing_restricted_function_preserved(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "def f():\n    from pkg import child\nf()",
        "pkg.child": "pass",
    }
    result = _model(sources, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(event.operation == "CALL_FUNCTION" for event in result.events)
    assert any(
        event.operation.startswith("FUNCTION_LOCAL_FROM") for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_c23_passive_reexport_is_available(tmp_path):
    sources = {
        "pkg.__init__": "from pkg.a import f",
        "pkg.a": "def f(x=None):\n    dangerous()",
    }
    result = _model(sources, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "f"
        for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg").returncode == 0


def test_c23_reentrant_early_export_still_hazard(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "from pkg.b import ready\ndef f(x=None):\n    dangerous()",
        "pkg.b": "from pkg.a import f\nready = 1",
    }
    result = _model(sources, "pkg.a")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert (result.target_module, result.symbol) == ("pkg.a", "f")
    process = _actual(tmp_path, sources, "pkg.a")
    assert process.returncode != 0
    assert "ImportError" in process.stderr


@pytest.mark.parametrize(
    ("entry", "expected_outcome", "expected_module", "expected_symbol"),
    [
        ("repo", "EARLY_BINDING_HAZARD", "repo", "run_repo_generator"),
        ("ui", "MODEL_PASS", None, None),
    ],
)
def test_c23_two_package_entry_order(
    tmp_path, entry, expected_outcome, expected_module, expected_symbol
):
    sources = {
        "repo.__init__": "from repo.main import run_repo_generator",
        "repo.main": (
            "from repo.filters import ready\n"
            "def run_repo_generator(parent=None):\n"
            "    dangerous()"
        ),
        "repo.filters": "from ui import theme\nready = 1",
        "ui.__init__": "from ui.gui import run",
        "ui.gui": (
            "from repo import run_repo_generator\n"
            "def run(*, single_instance=None):\n"
            "    dangerous()"
        ),
        "ui.theme": "ready = 1",
    }
    result = _model(sources, entry)
    assert result.outcome == expected_outcome
    assert (result.target_module, result.symbol) == (
        expected_module,
        expected_symbol,
    )
    process = _actual(tmp_path, sources, entry)
    if expected_outcome == "MODEL_PASS":
        assert process.returncode == 0
    else:
        assert process.returncode != 0
        assert "ImportError" in process.stderr


def test_c23_opaque_call_is_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "def f(value=None):\n    pass\nf()",
    }
    assert _model(sources, "pkg.a").outcome == "UNKNOWN"


def test_c23_dynamic_default_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "def f(x=compute_default()):\n    pass",
    }
    assert _model(sources, "pkg.a").outcome == "UNKNOWN"


def test_c23_decorator_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "@decorator\ndef f():\n    pass",
    }
    assert _model(sources, "pkg.a").outcome == "UNKNOWN"


def test_c23_annotation_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "def f(x: unknown_annotation):\n    pass",
    }
    assert _model(sources, "pkg.a").outcome == "UNKNOWN"


def test_c23_determinism_ast_immutability_json():
    trees = {
        "pkg.__init__": ast.parse("from pkg.a import f"),
        "pkg.a": ast.parse("def f(x=None):\n    dangerous()"),
    }
    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in trees.items()
    }
    first = evaluate_package_import_order(trees, "pkg")
    second = evaluate_package_import_order(trees, "pkg")
    assert first == second
    assert first.outcome == "MODEL_PASS"
    assert before == {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in trees.items()
    }
    json.dumps(asdict(first))
