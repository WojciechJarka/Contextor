"""Restricted function-local from-import semantics.

CPython comparisons use only generated synthetic packages.
No real Contextor SCC module, GUI or watcher is imported.
"""

import ast
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(sources, entry):
    return evaluate_package_import_order(
        {
            name: ast.parse(code)
            for name, code in sources.items()
        },
        entry,
    )


def _runtime(tmp_path, sources, entry, postcondition=""):
    for module, code in sources.items():
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

    command = (
        "import importlib,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "importlib.import_module(sys.argv[2])"
    )

    if postcondition:
        command += ";" + postcondition

    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            command,
            str(tmp_path),
            entry,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_deferred_from_not_executed(tmp_path):
    sources = {
        "pkg.__init__": (
            "def later():\n"
            "    from pkg.child import value"
        ),
        "pkg.child": (
            "from pkg import not_yet\n"
            "value = 1"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _runtime(
        tmp_path,
        sources,
        "pkg",
    ).returncode == 0


def test_called_from_activates_early_binding_hazard(tmp_path):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import value\n"
            "go()\n"
            "not_yet = 7"
        ),
        "pkg.child": (
            "from pkg import not_yet\n"
            "value = 1"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "not_yet"

    process = _runtime(
        tmp_path,
        sources,
        "pkg",
    )

    assert process.returncode != 0
    assert "ImportError" in process.stderr


def test_binding_before_called_from_passes(tmp_path):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import value\n"
            "not_yet = 7\n"
            "go()"
        ),
        "pkg.child": (
            "from pkg import not_yet\n"
            "value = 1"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FUNCTION_LOCAL_FROM"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _runtime(
        tmp_path,
        sources,
        "pkg",
    ).returncode == 0


def test_local_alias_not_exported_to_package(tmp_path):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import value as local_only\n"
            "go()"
        ),
        "pkg.child": "value = 1",
        "pkg.consumer": "from pkg import local_only",
    }

    result = _model(
        sources,
        "pkg.consumer",
    )

    assert result.outcome == "MISSING_EXPORT"
    assert result.target_module == "pkg"
    assert result.symbol == "local_only"

    process = _runtime(
        tmp_path,
        sources,
        "pkg.consumer",
    )

    assert process.returncode != 0
    assert "ImportError" in process.stderr


def test_top_level_from_still_exports_to_package(tmp_path):
    sources = {
        "pkg.__init__": (
            "from pkg.child import value as exported"
        ),
        "pkg.child": "value = 1",
        "pkg.consumer": "from pkg import exported",
    }

    result = _model(
        sources,
        "pkg.consumer",
    )

    assert result.outcome == "MODEL_PASS"

    assert _runtime(
        tmp_path,
        sources,
        "pkg.consumer",
    ).returncode == 0


def test_multi_member_preparation_precedes_local_binding(
    tmp_path,
):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg import a, b\n"
            "go()\n"
            "ready = 1"
        ),
        "pkg.a": "value = 1",
        "pkg.b": (
            "from pkg import ready\n"
            "value = 2"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "ready"

    assert not any(
        event.operation == "FUNCTION_LOCAL_FROM"
        for event in result.events
    )

    process = _runtime(
        tmp_path,
        sources,
        "pkg",
    )

    assert process.returncode != 0
    assert "ImportError" in process.stderr


def test_multi_member_local_aliases_not_exported(tmp_path):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import "
            "a as local_a, b as local_b\n"
            "go()"
        ),
        "pkg.child": (
            "a = 1\n"
            "b = 2"
        ),
        "pkg.consumer": "from pkg import local_a",
    }

    result = _model(
        sources,
        "pkg.consumer",
    )

    assert result.outcome == "MISSING_EXPORT"
    assert result.symbol == "local_a"

    local_events = [
        event
        for event in result.events
        if event.operation == "FUNCTION_LOCAL_FROM"
    ]

    assert len(local_events) == 2

    assert _runtime(
        tmp_path,
        sources,
        "pkg.consumer",
    ).returncode != 0


def test_relative_from_inside_function(tmp_path):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from .child import value\n"
            "go()"
        ),
        "pkg.child": "value = 1",
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert _runtime(
        tmp_path,
        sources,
        "pkg",
    ).returncode == 0


def test_flat_module_from_inside_function_hazard(tmp_path):
    sources = {
        "a": (
            "def go():\n"
            "    from b import value\n"
            "go()\n"
            "ready = 1"
        ),
        "b": (
            "from a import ready\n"
            "value = 2"
        ),
    }

    result = _model(sources, "a")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "a"
    assert result.symbol == "ready"

    process = _runtime(
        tmp_path,
        sources,
        "a",
    )

    assert process.returncode != 0
    assert "ImportError" in process.stderr


def test_reentrant_child_local_from_fallback(tmp_path):
    sources = {
        "pkg.__init__": (
            "from pkg.child import value"
        ),
        "pkg.child": (
            "def activate():\n"
            "    from pkg import child as local_child\n"
            "activate()\n"
            "value = 1"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert any(
        event.operation
        == "FUNCTION_LOCAL_FROM_REENTRANT_CHILD"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _runtime(
        tmp_path,
        sources,
        "pkg",
    ).returncode == 0


def test_local_from_does_not_shadow_module_global(tmp_path):
    sources = {
        "pkg.__init__": (
            "sentinel = 1\n"
            "def go():\n"
            "    from pkg.child import value as sentinel\n"
            "go()"
        ),
        "pkg.child": "value = 2",
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    process = _runtime(
        tmp_path,
        sources,
        "pkg",
        postcondition=(
            "assert importlib.import_module('pkg').sentinel == 1"
        ),
    )

    assert process.returncode == 0


def test_repeated_function_calls_do_not_reimport_child(
    tmp_path,
):
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import value\n"
            "go()\n"
            "go()"
        ),
        "pkg.child": "value = 1",
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert sum(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    ) == 1

    assert sum(
        event.operation == "FUNCTION_LOCAL_FROM"
        and event.target == "pkg.child"
        for event in result.events
    ) == 2

    assert _runtime(
        tmp_path,
        sources,
        "pkg",
    ).returncode == 0


def test_unsupported_function_semantics_stay_unknown():
    unsupported = (
        (
            "def go():\n"
            "    from pkg.child import *"
        ),
        (
            "def go(x=1):\n"
            "    from pkg.child import value"
        ),
        (
            "def go():\n"
            "    from ..child import value"
        ),
        (
            "def go():\n"
            "    value = 1"
        ),
    )

    for source in unsupported:
        result = _model(
            {
                "pkg.__init__": source,
                "pkg.child": "value = 1",
            },
            "pkg",
        )

        assert result.outcome == "UNKNOWN"


def test_determinism_and_source_ast_unchanged():
    sources = {
        "pkg.__init__": (
            "def go():\n"
            "    from pkg.child import "
            "value as local_value\n"
            "go()"
        ),
        "pkg.child": "value = 1",
    }

    trees = {
        name: ast.parse(source)
        for name, source in sources.items()
    }

    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in trees.items()
    }

    first = evaluate_package_import_order(
        trees,
        "pkg",
    )

    second = evaluate_package_import_order(
        trees,
        "pkg",
    )

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in trees.items()
    } == before

    json.dumps(asdict(first))
