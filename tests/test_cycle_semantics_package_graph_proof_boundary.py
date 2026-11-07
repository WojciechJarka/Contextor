"""Internal graph proof is separate from import execution uncertainty."""

import ast
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.model_source_closure import (
    compute_cycle_model_source_closures_with_optional_children,
)
from contextor.core.cycle_semantics.package_graph_consistency import (
    assess_package_graph_consistency,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.symbol_engine.indexer import read_imports


PROVED = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"


def _case(source, *, namespace=False, edge=True):
    target = "pkg.ns.b" if namespace else "pkg.b"
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {target} if edge else set(),
        target: set(),
    }
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(source),
        target: ast.parse("pass\n"),
    }
    return graph, trees


def _assess(graph, trees, order=None):
    return assess_package_graph_consistency(
        graph,
        trees,
        tuple(trees) if order is None else order,
    )


def _not_proved(result, reason):
    assert result.status == "INDETERMINATE"
    assert result.reason == reason
    assert result.internal_graph_state == "NOT_PROVED"
    assert result.checked_source_modules == ()


def test_closed_internal_graph_has_bounded_proof():
    graph, trees = _case("import pkg.b\n")
    result = _assess(graph, trees)
    assert result.status == "CONSISTENT"
    assert result.reason is None
    assert result.internal_graph_state == PROVED
    assert result.checked_source_modules == tuple(sorted(trees))
    assert result.unmodeled_external_imports == ()
    assert result.unmodeled_namespace_parents == ()


def test_external_uncertainty_preserves_internal_graph_proof():
    graph, trees = _case("import os\nimport pkg.b\n")
    result = _assess(graph, trees)
    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert result.internal_graph_state == PROVED
    assert result.checked_source_modules == tuple(sorted(trees))
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "os"),
    )


def test_namespace_uncertainty_preserves_internal_graph_proof():
    graph, trees = _case("import pkg.ns.b\n", namespace=True)
    result = _assess(graph, trees)
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.internal_graph_state == PROVED
    assert result.checked_source_modules == tuple(sorted(trees))
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
    )


def test_combined_uncertainty_preserves_both_diagnostics_and_proof():
    graph, trees = _case(
        "import os\nimport pkg.ns.b\n", namespace=True
    )
    result = _assess(graph, trees)
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.internal_graph_state == PROVED
    assert result.checked_source_modules == tuple(sorted(trees))
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "os"),
    )
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
    )


@pytest.mark.parametrize(
    "source,namespace",
    [
        ("import os\nimport pkg.b\n", False),
        ("import pkg.ns.b\n", True),
    ],
)
def test_graph_mismatch_never_exposes_partial_proof(source, namespace):
    graph, trees = _case(source, namespace=namespace, edge=False)
    _not_proved(
        _assess(graph, trees),
        "GRAPH_SOURCE_IMPORT_MISMATCH",
    )


def test_missing_indexed_target_has_no_proof():
    graph, trees = _case("import pkg.missing\n", edge=False)
    _not_proved(_assess(graph, trees), "MISSING_INDEXED_TARGET")


def test_missing_indexed_initializer_ast_has_no_proof():
    graph, trees = _case("import pkg.ns\n", namespace=True, edge=False)
    graph["pkg.ns.__init__"] = set()
    _not_proved(_assess(graph, trees), "MISSING_REQUIRED_INITIALIZER")


def test_unsupported_import_form_has_no_proof():
    graph, trees = _case("from pkg import *\n", edge=False)
    _not_proved(_assess(graph, trees), "UNSUPPORTED_IMPORT_FORM")


def test_ambiguous_module_package_collision_has_no_proof():
    graph, trees = _case("import pkg.ns\n", namespace=True, edge=False)
    graph["pkg.ns"] = set()
    trees["pkg.ns"] = ast.parse("pass\n")
    _not_proved(_assess(graph, trees), "AMBIGUOUS_PACKAGE_TARGET")


def test_proof_is_deterministic_and_inputs_are_unchanged():
    graph, trees = _case(
        "import os\nimport pkg.ns.b\n", namespace=True
    )
    graph_before = {name: set(targets) for name, targets in graph.items()}
    trees_before = dict(trees)
    first = _assess(graph, trees, tuple(trees))
    second = _assess(graph, trees, tuple(reversed(trees)))
    assert first == second
    assert first.checked_source_modules == tuple(sorted(trees))
    assert graph == graph_before
    assert trees == trees_before
    assert all(trees[name] is tree for name, tree in trees_before.items())


@pytest.mark.parametrize("namespace", [False, True])
def test_optional_scc_remains_indeterminate(namespace):
    target = "pkg.ns.b" if namespace else "pkg.b"
    source = (
        "import pkg.ns.b\nimport os\n"
        if namespace
        else "import pkg.b\nimport os\n"
    )
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {target},
        target: {"pkg.a"},
    }
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(source),
        target: ast.parse("import pkg.a\n"),
    }
    imports = {}
    for name, tree in trees.items():
        extracted, error = read_imports(
            Path(*name.split(".")).with_suffix(".py"),
            tree=tree,
        )
        assert error is None
        imports[name] = extracted
    closures = compute_cycle_model_source_closures_with_optional_children(
        graph, imports
    )
    report = analyze_cycle_scenarios(
        graph,
        trees,
        source_selection="OPTIONAL_NAMED_CHILDREN",
        indexed_imports_by_module=imports,
        source_closures=closures,
    )
    component = report.components[0]
    assert component.classification == "INDETERMINATE"
    assert component.coverage == "NONE"
    assert component.entry_assessments == ()
    assert component.reason == (
        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
        if namespace
        else "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    )
