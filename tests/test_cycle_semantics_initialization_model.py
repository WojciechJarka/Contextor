import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.initialization_model import (
    evaluate_flat_import_order,
)


def _assess(sources, entry):
    return evaluate_flat_import_order(
        {name: ast.parse(code) for name, code in sources.items()}, entry
    )


def _actual(tmp_path, sources, entry):
    for name, code in sources.items():
        (tmp_path / (name + ".py")).write_text(code, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", (
            "import importlib,sys; "
            "sys.path.insert(0,sys.argv[1]); "
            "importlib.import_module(sys.argv[2])"
        ), str(tmp_path), entry],
        capture_output=True, text=True, timeout=10, check=False,
    )
    return result.returncode == 0


def test_plain_cycle_both_orders(tmp_path):
    sources = {"a": "import b\nvalue = 1\n", "b": "import a\nother = 2\n"}
    for entry in ("a", "b"):
        assert _assess(sources, entry).outcome == "MODEL_PASS"
        assert _actual(tmp_path, sources, entry)


def test_missing_attribute_first_order_hazard(tmp_path):
    sources = {"a": "import b\nvalue = 1\n", "b": "import a\nobserved = a.value\n"}
    assert _assess(sources, "a").outcome == "EARLY_BINDING_HAZARD"
    assert _assess(sources, "b").outcome == "MODEL_PASS"
    assert not _actual(tmp_path, sources, "a")
    assert _actual(tmp_path, sources, "b")


def test_move_binding_before_import_changes_outcome_not_edges(tmp_path):
    sources = {"a": "value = 1\nimport b\n", "b": "import a\nobserved = a.value\n"}
    for entry in ("a", "b"):
        assert _assess(sources, entry).outcome == "MODEL_PASS"
        assert _actual(tmp_path, sources, entry)


def test_from_import_hazard(tmp_path):
    sources = {"a": "import b\nvalue = 1\n", "b": "from a import value\n"}
    assert _assess(sources, "a").outcome == "EARLY_BINDING_HAZARD"
    assert _assess(sources, "b").outcome == "MODEL_PASS"
    assert not _actual(tmp_path, sources, "a")
    assert _actual(tmp_path, sources, "b")


def test_from_import_completed_missing_export():
    r = _assess({"a": "from b import missing\n", "b": "pass\n"}, "a")
    assert r.outcome == "MISSING_EXPORT"
    assert r.target_module == "b"
    assert r.symbol == "missing"


def test_missing_attribute_completed_module():
    r = _assess({"a": "import b\nx = b.missing\n", "b": "pass\n"}, "a")
    assert r.outcome == "MISSING_ATTRIBUTE"


def test_self_import_is_not_automatically_failure():
    assert _assess({"a": "import a\nx = 1\n"}, "a").outcome == "MODEL_PASS"


def test_repeated_import_and_alias():
    sources = {"a": "import b as alias\nimport b\nx = alias.value\n", "b": "value=3\n"}
    assert _assess(sources, "a").outcome == "MODEL_PASS"


def test_from_import_alias_binding():
    assert _assess({"a": "from b import value as x\n", "b": "value = 3\n"}, "a").outcome == "MODEL_PASS"


@pytest.mark.parametrize("source", [
    "if True:\n    import b\n",
    "def f():\n    import b\n",
    "import importlib\nimportlib.import_module('b')\n",
    "import pkg.b\n",
    "from . import b\n",
    "from b import *\n",
    "x = f()\n",
    "class X: pass\n",
    "import b\nx = getattr(b,'value')\n",
    "x, y = (1,2)\n",
    "raise RuntimeError('must never execute')\n",
    "import b\ndel b\n",
    "import b\nawait b\n",
])
def test_unsupported_fail_closed(source):
    assert _assess({"a": source, "b": "value=2\n"}, "a").outcome == "UNKNOWN"


def test_external_dependency_unknown():
    assert _assess({"a": "import os\n"}, "a").outcome == "UNKNOWN"


def test_invalid_inputs_unknown():
    assert evaluate_flat_import_order(None, "a").outcome == "UNKNOWN"
    assert evaluate_flat_import_order({"a": None}, "a").outcome == "UNKNOWN"
    assert evaluate_flat_import_order({"a": ast.parse("pass\n")}, "missing").outcome == "UNKNOWN"


def test_no_ast_mutation_determinism_serializable():
    modules = {
        "a": ast.parse("import b\nx=1"),
        "b": ast.parse("import a\ny=2"),
    }
    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in modules.items()
    }
    one = evaluate_flat_import_order(modules, "a")
    two = evaluate_flat_import_order(modules, "a")
    assert one == two
    assert {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in modules.items()
    } == before
    json.dumps(asdict(one))


def test_iterative_1200_module_chain():
    modules = {
        f"m{i}": ast.parse(f"import m{i+1}\n")
        for i in range(1200)
    }
    modules["m1200"] = ast.parse("x=1\n")
    assert evaluate_flat_import_order(modules, "m0").outcome == "MODEL_PASS"
