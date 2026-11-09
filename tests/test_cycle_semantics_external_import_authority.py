"""External import effects are not ordinary execution evidence."""

import ast
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.namespace_path_model import SearchPortion
from contextor.core.cycle_semantics.package_graph_consistency import (
    assess_package_graph_consistency,
)
from contextor.core.cycle_semantics.package_model import (
    evaluate_conditional_namespace_import_order,
    evaluate_package_import_order,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios


def _cycle(import_line):
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.a": (
            import_line
            + "if False:\n    import pkg.b\n"
            + "value = 1\nimport pkg.b\n"
        ),
        "pkg.b": "from pkg.a import value\n",
    }
    trees = {name: ast.parse(source) for name, source in sources.items()}
    edges = {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }
    return sources, trees, edges


def test_reached_typing_import_is_not_ordinary_evidence(tmp_path):
    sources, trees, edges = _cycle("from typing import TYPE_CHECKING\n")
    ordinary = evaluate_package_import_order(trees, "pkg.a")
    consistency = assess_package_graph_consistency(
        edges, trees, tuple(sorted(trees)),
    )
    scenarios = analyze_cycle_scenarios(edges, trees)

    assert ordinary.outcome == "UNKNOWN"
    assert ordinary.reached_unmodeled_import.target == "typing"
    assert ordinary.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert consistency.unmodeled_external_imports == (
        ("pkg.a", 1, "from", "typing"),
    )
    assert scenarios.components[0].classification == "INDETERMINATE"

    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_bytes(sources["pkg.__init__"].encode())
    (package / "a.py").write_bytes(sources["pkg.a"].encode())
    (package / "b.py").write_bytes(sources["pkg.b"].encode())
    (tmp_path / "typing.py").write_bytes(
        b'TYPE_CHECKING = False\nraise RuntimeError("typing import executed")\n'
    )
    run = subprocess.run(
        [
            sys.executable, "-I", "-S", "-c",
            "import sys;sys.path.insert(0,sys.argv[1]);import pkg.a",
            str(tmp_path),
        ],
        capture_output=True, text=True, timeout=10,
    )
    assert run.returncode != 0
    assert "RuntimeError: typing import executed" in run.stderr


def test_other_reached_external_import_has_same_boundary():
    _, trees, edges = _cycle("import opaque_dependency\n")
    ordinary = evaluate_package_import_order(trees, "pkg.a")
    consistency = assess_package_graph_consistency(
        edges, trees, tuple(sorted(trees)),
    )
    scenarios = analyze_cycle_scenarios(edges, trees)

    assert ordinary.outcome == "UNKNOWN"
    assert ordinary.reached_unmodeled_import.target == "opaque_dependency"
    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert scenarios.components[0].classification == "INDETERMINATE"


def test_unreached_external_import_keeps_restricted_pass():
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(
            "def later():\n    import opaque_dependency\nvalue = 1\n"
        ),
    }
    ordinary = evaluate_package_import_order(trees, "pkg.a")

    assert ordinary.outcome == "MODEL_PASS"
    assert ordinary.reached_unmodeled_import is None
    assert ordinary.assumed_external_imports == ()


def test_conditional_external_assumption_stays_conditional():
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.ns.a": ast.parse("import opaque_dependency\nvalue = 1\n"),
    }
    roots = (SearchPortion(
        "root", frozenset({"pkg/__init__.py", "pkg/ns/a.py"}),
    ),)
    result = evaluate_conditional_namespace_import_order(
        trees, "pkg.ns.a", roots,
        target_python_version=(3, 15),
        assume_passive_external_imports=True,
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.model_assessment.outcome == "MODEL_PASS"
    assert result.model_assessment.evidence_scope == (
        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_ASSUMPTION_NOT_RUNTIME_PROOF"
    )
    assert result.model_assessment.assumed_external_imports[0].target == (
        "opaque_dependency"
    )


@pytest.mark.parametrize(
    "marker, guard",
    [
        ("from typing import TYPE_CHECKING", "TYPE_CHECKING"),
        ("import typing", "typing.TYPE_CHECKING"),
    ],
    ids=("name", "attribute"),
)
def test_unproved_typing_guard_stops_ordinary_and_conditional_models(
    marker, guard,
):
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.ns.a": ast.parse(
            f"{marker}\nif {guard}:\n    import pkg.ns.b\nvalue = 1\n"
        ),
        "pkg.ns.b": ast.parse("from pkg.ns.a import value\n"),
    }
    roots = (SearchPortion(
        "root", frozenset({
            "pkg/__init__.py", "pkg/ns/a.py", "pkg/ns/b.py",
        }),
    ),)

    ordinary_trees = dict(trees)
    ordinary_trees["pkg.ns.__init__"] = ast.parse("pass\n")
    ordinary = evaluate_package_import_order(ordinary_trees, "pkg.ns.a")
    conditional = evaluate_conditional_namespace_import_order(
        trees, "pkg.ns.a", roots,
        target_python_version=(3, 15),
        assume_passive_external_imports=True,
    )

    assert ordinary.outcome == "UNKNOWN"
    assert ordinary.reached_unmodeled_import is not None
    assert ordinary.reached_unmodeled_import.target == "typing"
    assert conditional.outcome == "UNKNOWN"
    assert conditional.model_assessment is not None
    assert conditional.model_assessment.outcome == "UNKNOWN"
    assert "typing" in {
        item.target for item in conditional.model_assessment.assumed_external_imports
    }
    assert conditional.outcome != "CONDITIONAL_MODEL_PASS"
    assert ordinary.outcome != "MODEL_PASS"
