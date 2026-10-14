"""Restricted SCC02 import-order projection.

Read actual Contextor source only to verify lexical anchors.
Execute ONLY synthesized minimal modules in isolated processes.
No result here certifies the behavior of the production GUI.
"""

import ast
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


_ROOT = Path(__file__).resolve().parents[1]


def _real_tree(relative_path):
    path = _ROOT.joinpath(*relative_path.split("/"))
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def _from(tree, module, member, level=0):
    found = [
        stmt
        for stmt in tree.body
        if isinstance(stmt, ast.ImportFrom)
        and stmt.module == module
        and stmt.level == level
        and any(
            alias.name == member
            for alias in stmt.names
        )
    ]
    assert len(found) == 1
    return found[0]


def _definition(tree, name):
    found = [
        stmt
        for stmt in tree.body
        if isinstance(
            stmt,
            (ast.FunctionDef, ast.ClassDef),
        )
        and stmt.name == name
    ]
    assert len(found) == 1
    return found[0]


def _projection():
    return {
        "contextor.__init__": "pass",
        "contextor.repo_generator.__init__": (
            "from contextor.repo_generator.main "
            "import run_repo_generator"
        ),
        "contextor.repo_generator.main": (
            "from contextor.repo_generator.filters "
            "import FilterWindow\n"
            "def run_repo_generator():\n"
            "    pass"
        ),
        "contextor.repo_generator.filters": (
            "from contextor.ui import theme\n"
            "def FilterWindow():\n"
            "    pass"
        ),
        "contextor.ui.__init__": (
            "from contextor.ui.gui import run"
        ),
        "contextor.ui.gui": (
            "from contextor.repo_generator "
            "import run_repo_generator\n"
            "def run():\n"
            "    pass"
        ),
        "contextor.ui.theme": "pass",
    }


def _model(source, entry):
    return evaluate_package_import_order(
        {
            name: ast.parse(code)
            for name, code in source.items()
        },
        entry,
    )


def _runtime(tmp_path, source, entry):
    for module, code in source.items():
        parts = module.split(".")

        if parts[-1] == "__init__":
            path = tmp_path.joinpath(
                *parts[:-1],
                "__init__.py",
            )
        else:
            path = tmp_path.joinpath(
                *parts[:-1],
                parts[-1] + ".py",
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            code + "\n",
            encoding="utf-8",
        )

    process = subprocess.run(
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

    return process


def test_scc02_source_chain_still_exists():
    repo = _real_tree(
        "contextor/repo_generator/__init__.py"
    )
    main = _real_tree(
        "contextor/repo_generator/main.py"
    )
    filters = _real_tree(
        "contextor/repo_generator/filters.py"
    )
    ui = _real_tree(
        "contextor/ui/__init__.py"
    )
    gui = _real_tree(
        "contextor/ui/gui.py"
    )

    _from(
        repo,
        "contextor.repo_generator.main",
        "run_repo_generator",
    )
    _from(
        main,
        "contextor.repo_generator.filters",
        "FilterWindow",
    )
    _from(
        filters,
        "contextor.ui",
        "theme",
    )
    _from(
        ui,
        "gui",
        "run",
        level=1,
    )
    _from(
        gui,
        "contextor.repo_generator",
        "run_repo_generator",
    )


def test_scc02_reexport_bindings_follow_imports():
    main = _real_tree(
        "contextor/repo_generator/main.py"
    )
    filters = _real_tree(
        "contextor/repo_generator/filters.py"
    )
    gui = _real_tree(
        "contextor/ui/gui.py"
    )

    assert _from(
        main,
        "contextor.repo_generator.filters",
        "FilterWindow",
    ).lineno < _definition(
        main,
        "run_repo_generator",
    ).lineno

    assert _from(
        filters,
        "contextor.ui",
        "theme",
    ).lineno < _definition(
        filters,
        "FilterWindow",
    ).lineno

    assert _from(
        gui,
        "contextor.repo_generator",
        "run_repo_generator",
    ).lineno < _definition(
        gui,
        "run",
    ).lineno


def test_scc02_projection_repo_generator_first_hazard():
    result = _model(
        _projection(),
        "contextor.repo_generator",
    )

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert (
        result.target_module
        == "contextor.repo_generator"
    )
    assert result.symbol == "run_repo_generator"

    assert not any(
        event.operation == "DEFINE_FUNCTION"
        and event.module == "contextor.repo_generator.main"
        and event.symbol == "run_repo_generator"
        for event in result.events
    )


def test_scc02_projection_ui_first_passes():
    result = _model(
        _projection(),
        "contextor.ui",
    )

    assert result.outcome == "MODEL_PASS"

    ready = [
        event.module
        for event in result.events
        if event.operation == "READY"
    ]

    assert (
        ready.index("contextor.repo_generator.main")
        < ready.index("contextor.repo_generator")
    )

    assert (
        ready.index("contextor.repo_generator")
        < ready.index("contextor.ui.gui")
    )


@pytest.mark.parametrize(
    "entry,expected_success",
    [
        ("contextor.repo_generator", False),
        ("contextor.ui", True),
    ],
)
def test_scc02_projection_matches_fresh_cpython(
    tmp_path,
    entry,
    expected_success,
):
    process = _runtime(
        tmp_path,
        _projection(),
        entry,
    )

    assert (
        process.returncode == 0
    ) is expected_success


def test_scc02_prebinding_changes_result_without_import_changes(
    tmp_path,
):
    original = _projection()
    prebound = dict(original)

    prebound["contextor.repo_generator.__init__"] = (
        "def run_repo_generator():\n"
        "    pass\n"
        + original["contextor.repo_generator.__init__"]
    )

    original_imports = {
        module: tuple(
            ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(code))
            if isinstance(
                node,
                (ast.Import, ast.ImportFrom),
            )
        )
        for module, code in original.items()
    }

    prebound_imports = {
        module: tuple(
            ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(code))
            if isinstance(
                node,
                (ast.Import, ast.ImportFrom),
            )
        )
        for module, code in prebound.items()
    }

    assert original_imports == prebound_imports

    original_result = _model(
        original,
        "contextor.repo_generator",
    )
    changed_result = _model(
        prebound,
        "contextor.repo_generator",
    )

    assert (
        original_result.outcome
        == "EARLY_BINDING_HAZARD"
    )
    assert changed_result.outcome == "MODEL_PASS"

    process = _runtime(
        tmp_path,
        prebound,
        "contextor.repo_generator",
    )
    assert process.returncode == 0


def test_scc02_projection_determinism_and_no_ast_mutation():
    sources = {
        name: ast.parse(code)
        for name, code in _projection().items()
    }

    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    }

    first = evaluate_package_import_order(
        sources,
        "contextor.repo_generator",
    )
    second = evaluate_package_import_order(
        sources,
        "contextor.repo_generator",
    )

    assert first == second
    assert first.outcome == "EARLY_BINDING_HAZARD"

    assert {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    } == before

    json.dumps(asdict(first))
