"""Namespace package parents stay diagnostic during graph checks."""

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


def _check(graph, source_texts, order=None):
    trees = {name: ast.parse(text) for name, text in source_texts.items()}
    selected = tuple(source_texts) if order is None else order
    return assess_package_graph_consistency(graph, trees, selected)


def _base(import_text="import pkg.ns.b\n"):
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.ns.b"},
        "pkg.ns.b": set(),
    }
    source_texts = {
        "pkg.__init__": "pass\n",
        "pkg.a": import_text,
        "pkg.ns.b": "value = 1\n",
    }
    return graph, source_texts


def test_namespace_under_regular_package():
    graph, sources = _base()
    result = _check(graph, sources)
    assert result.status == "INDETERMINATE"
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
    )
    assert result.unmodeled_external_imports == ()


def test_direct_import_of_namespace_base_has_no_synthetic_hard_edge():
    graph, sources = _base("import pkg.ns\n")
    graph["pkg.a"] = set()
    result = _check(graph, sources)
    assert result.status == "INDETERMINATE"
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
    )


def test_direct_from_namespace_base_does_not_assume_child_binding():
    graph, sources = _base("from pkg.ns import b\n")
    graph["pkg.a"] = set()
    result = _check(graph, sources)
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
    )


def test_direct_namespace_base_does_not_claim_child_hard_edge():
    graph, sources = _base("from pkg.ns import b\n")
    result = _check(graph, sources)
    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert result.unmodeled_namespace_parents == ()


def test_top_level_namespace_base_is_structural_candidate():
    graph = {"consumer": set(), "ns.b": set()}
    result = _check(
        graph,
        {"consumer": "import ns\n", "ns.b": "pass\n"},
    )
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_namespace_parents == (
        ("consumer", 1, "ns", "ns"),
    )


def test_import_between_namespace_modules():
    graph = {
        "pkg.__init__": set(),
        "pkg.ns.a": {"pkg.ns.b"},
        "pkg.ns.b": set(),
    }
    result = _check(
        graph,
        {
            "pkg.__init__": "pass\n",
            "pkg.ns.a": "import pkg.ns.b\n",
            "pkg.ns.b": "pass\n",
        },
    )
    assert result.unmodeled_namespace_parents == (
        ("pkg.ns.a", 1, "pkg.ns.b", "pkg.ns"),
    )
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"


def test_import_from_through_namespace():
    graph, sources = _base("from pkg.ns.b import value\n")
    result = _check(graph, sources)
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
    )
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"


def test_missing_indexed_initializer_is_invalid():
    graph, sources = _base()
    graph["pkg.ns.__init__"] = set()
    result = _check(graph, sources)
    assert result.reason == "MISSING_REQUIRED_INITIALIZER"
    assert result.unmodeled_namespace_parents == ()


def test_direct_namespace_base_with_missing_initializer_ast_rejected():
    graph, sources = _base("import pkg.ns\n")
    graph["pkg.a"] = set()
    graph["pkg.ns.__init__"] = set()
    result = _check(graph, sources)
    assert result.status == "INDETERMINATE"
    assert result.reason == "MISSING_REQUIRED_INITIALIZER"
    assert result.unmodeled_namespace_parents == ()


def test_module_package_collision_is_invalid():
    graph, sources = _base()
    graph["pkg.ns"] = set()
    sources["pkg.ns"] = "pass\n"
    result = _check(graph, sources)
    assert result.reason == "MISSING_REQUIRED_INITIALIZER"


def test_direct_namespace_base_colliding_with_module_rejected():
    graph, sources = _base("import pkg.ns\n")
    graph["pkg.a"] = set()
    graph["pkg.ns"] = set()
    sources["pkg.ns"] = "pass\n"
    result = _check(graph, sources)
    assert result.status == "INDETERMINATE"
    assert result.reason == "AMBIGUOUS_PACKAGE_TARGET"
    assert result.unmodeled_namespace_parents == ()


def test_missing_internal_target_is_not_namespace():
    graph, sources = _base("import pkg.ns.missing\n")
    graph["pkg.a"] = set()
    result = _check(graph, sources)
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.unmodeled_namespace_parents == ()


def test_namespace_does_not_hide_graph_source_mismatch():
    graph, sources = _base()
    graph["pkg.a"] = set()
    result = _check(graph, sources)
    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert result.unmodeled_namespace_parents == ()


def test_namespace_and_external_records_are_both_retained():
    graph, sources = _base("import os\nimport pkg.ns.b\n")
    result = _check(graph, sources)
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "os"),
    )
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
    )


def test_direct_namespace_base_preserves_external_record():
    graph, sources = _base("import unknown_vendor_xyz\nimport pkg.ns\n")
    graph["pkg.a"] = set()
    result = _check(graph, sources)
    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "unknown_vendor_xyz"),
    )
    assert result.unmodeled_namespace_parents == (
        ("pkg.a", 2, "pkg.ns", "pkg.ns"),
    )


def test_records_are_deterministic_and_inputs_unchanged():
    graph, sources = _base("import pkg.ns.b\nimport pkg.ns.b\n")
    trees = {name: ast.parse(text) for name, text in sources.items()}
    graph_before = {name: set(targets) for name, targets in graph.items()}
    trees_before = dict(trees)
    first = assess_package_graph_consistency(
        graph, trees, tuple(trees)
    )
    second = assess_package_graph_consistency(
        graph, trees, tuple(reversed(trees))
    )
    assert first == second
    assert first.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
    )
    assert graph == graph_before
    assert trees == trees_before


def test_direct_namespace_records_are_deterministic():
    graph, sources = _base("import pkg.ns\nimport pkg.ns\n")
    graph["pkg.a"] = set()
    trees = {name: ast.parse(text) for name, text in sources.items()}
    before_graph = {name: set(targets) for name, targets in graph.items()}
    before_trees = dict(trees)
    first = assess_package_graph_consistency(
        graph, trees, tuple(trees)
    )
    second = assess_package_graph_consistency(
        graph, trees, tuple(reversed(trees))
    )
    assert first == second
    assert first.unmodeled_namespace_parents == (
        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
        ("pkg.a", 2, "pkg.ns", "pkg.ns"),
    )
    assert graph == before_graph
    assert trees == before_trees


def test_optional_namespace_scc_never_model_passes():
    graph = {
        "pkg.__init__": set(),
        "pkg.ns.a": {"pkg.ns.b"},
        "pkg.ns.b": {"pkg.ns.a"},
    }
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.ns.a": ast.parse("import pkg.ns\nimport pkg.ns.b\n"),
        "pkg.ns.b": ast.parse("import pkg.ns.a\n"),
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
    assert component.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
