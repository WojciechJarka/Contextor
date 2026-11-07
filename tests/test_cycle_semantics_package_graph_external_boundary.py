"""External imports remain opaque to the closed package cycle model."""

import ast
from pathlib import Path

from contextor.core.cycle_semantics.model_source_closure import (
    compute_cycle_model_source_closures_with_optional_children,
)
from contextor.core.cycle_semantics.package_graph_consistency import (
    assess_package_graph_consistency,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.symbol_engine.indexer import read_imports


def _check(source, *, edges=None):
    graph = {"pkg.__init__": set(), "pkg.a": set()}
    if edges is not None:
        graph["pkg.a"] = set(edges)
        graph["pkg.b"] = set()
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(source),
    }
    if edges is not None:
        trees["pkg.b"] = ast.parse("pass\n")
    return assess_package_graph_consistency(
        graph, trees, tuple(sorted(trees))
    )


def test_stdlib_import_is_opaque():
    result = _check("import os\n")
    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "os"),
    )


def test_stdlib_from_import_is_opaque():
    result = _check("from collections import Counter\n")
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "from", "collections"),
    )
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"


def test_third_party_and_nonexistent_imports_are_equally_opaque():
    result = _check(
        "import orjson\nimport definitely_nonexistent_package_xyz\n"
    )
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "orjson"),
        ("pkg.a", 2, "import", "definitely_nonexistent_package_xyz"),
    )
    assert result.status == "INDETERMINATE"


def test_missing_internal_target_still_fails_closed():
    result = _check("import pkg.missing\n")
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.unmodeled_external_imports == ()


def test_unresolved_relative_target_still_fails_closed():
    result = _check("from .missing import thing\n")
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.unmodeled_external_imports == ()


def test_external_import_does_not_hide_internal_graph_mismatch():
    result = _check("import os\nimport pkg.b\n", edges=())
    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert result.unmodeled_external_imports == ()


def test_external_records_are_sorted_without_mutating_inputs():
    graph = {"pkg.__init__": set(), "pkg.a": set()}
    trees = {
        "pkg.a": ast.parse("import zzz\nimport aaa\n"),
        "pkg.__init__": ast.parse("pass\n"),
    }
    before_graph = {name: set(targets) for name, targets in graph.items()}
    before_trees = dict(trees)
    first = assess_package_graph_consistency(
        graph, trees, ("pkg.a", "pkg.__init__")
    )
    second = assess_package_graph_consistency(
        graph, trees, ("pkg.__init__", "pkg.a")
    )
    assert first == second
    assert first.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "zzz"),
        ("pkg.a", 2, "import", "aaa"),
    )
    assert graph == before_graph
    assert trees == before_trees


def test_optional_scc_with_external_import_never_model_passes():
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse("import pkg.b\nimport os\n"),
        "pkg.b": ast.parse("import pkg.a\n"),
    }
    imports = {}
    for module_id, tree in trees.items():
        extracted, error = read_imports(
            Path(*module_id.split(".")).with_suffix(".py"),
            tree=tree,
        )
        assert error is None
        imports[module_id] = extracted
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
    assert component.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
