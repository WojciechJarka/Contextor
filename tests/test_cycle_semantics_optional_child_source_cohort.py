"""Index-backed optional package-child source selection."""

from __future__ import annotations

import pytest

from contextor.core.cycle_semantics.model_source_closure import (
    compute_cycle_model_source_closures,
    compute_cycle_model_source_closures_with_optional_children,
)
from contextor.core.domain.imports import ImportRef
from contextor.core.graph.graph import build_graph
from contextor.core.graph.resolver import build_trie, detect_package_root
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.symbol_engine.indexer import index_repository
from tests.cycle_semantics_lab import write_synthetic_repository


def _candidate(tmp_path, files):
    root = tmp_path / "repo"
    write_synthetic_repository(root, files)
    index = index_repository(str(root))
    facts = materialize_reexport_facts_by_module(
        index.modules, index.reference_facts_by_module
    )
    trie = build_trie(index.modules)
    package_root = detect_package_root(index.modules, trie)
    graph = build_graph(
        index.modules, trie=trie, package_root=package_root,
        reexport_facts_by_module=facts,
    )
    imports = {name: module.imports for name, module in index.modules.items()}
    original = compute_cycle_model_source_closures(graph.hard_edges)
    expanded = compute_cycle_model_source_closures_with_optional_children(
        graph.hard_edges, imports, package_root=package_root
    )
    return graph, imports, original, expanded


BASE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "import pkg.b\nfrom pkg import value\n",
    "pkg/b.py": "import pkg.a\n",
}


def test_p01_no_indexed_child_preserves_original(tmp_path):
    graph, _, original, expanded = _candidate(tmp_path, BASE)
    assert expanded == original
    assert graph.hard_edges


def _fixed_point_case(tmp_path):
    files = {
        "contextor/__init__.py": "pass\n",
        "contextor/ui/__init__.py": "theme = 1\n",
        "contextor/ui/theme.py": "import contextor.extra\n",
        "contextor/repo_generator/__init__.py": "pass\n",
        "contextor/repo_generator/run_repo_generator.py": "pass\n",
        "contextor/extra.py": "from contextor.repo_generator import run_repo_generator\n",
        "contextor/a.py": "import contextor.b\nfrom contextor.ui import theme\n",
        "contextor/b.py": "import contextor.a\n",
    }
    return _candidate(tmp_path, files)


def test_p02_optional_named_child(tmp_path):
    _, _, original, expanded = _fixed_point_case(tmp_path)
    assert "contextor.ui.theme" in expanded[0].evidence_source_modules
    assert "contextor.ui.theme" not in original[0].evidence_source_modules


def test_p03_eventual_reexport_shadow(tmp_path):
    graph, _, _, expanded = _fixed_point_case(tmp_path)
    assert "contextor.ui.theme" not in graph.soft_edges["contextor.a"]
    assert "contextor.ui.theme" in expanded[0].evidence_source_modules


def test_p04_transitive_hard_dependency(tmp_path):
    graph, _, original, expanded = _fixed_point_case(tmp_path)
    assert "contextor.extra" in graph.hard_edges["contextor.ui.theme"]
    assert "contextor.extra" not in original[0].evidence_source_modules
    assert "contextor.extra" in expanded[0].evidence_source_modules


def test_p05_second_level_optional_child(tmp_path):
    graph, _, _, expanded = _fixed_point_case(tmp_path)
    assert "contextor.repo_generator.run_repo_generator" not in graph.hard_edges["contextor.extra"]
    assert "contextor.repo_generator.run_repo_generator" in expanded[0].evidence_source_modules


def test_p06_ancestor_initializers(tmp_path):
    _, _, original, expanded = _fixed_point_case(tmp_path)
    assert {"contextor.ui.__init__", "contextor.repo_generator.__init__"} <= set(
        expanded[0].evidence_source_modules
    )
    assert expanded[0].implicit_initializer_modules == original[0].implicit_initializer_modules


def test_p07_fact_order_independence(tmp_path):
    graph, imports, original, expanded = _fixed_point_case(tmp_path)
    selected = set(expanded[0].evidence_source_modules)
    assert {"contextor.ui.theme", "contextor.extra",
            "contextor.repo_generator.run_repo_generator",
            "contextor.ui.__init__", "contextor.repo_generator.__init__"} <= selected
    assert expanded[0].hard_reachable_modules == original[0].hard_reachable_modules
    assert expanded[0].implicit_initializer_modules == original[0].implicit_initializer_modules
    assert "contextor.ui.theme" not in graph.hard_edges["contextor.a"]
    assert "contextor.ui.theme" not in graph.soft_edges["contextor.a"]
    reordered = {name: list(reversed(rows)) for name, rows in imports.items()}
    assert compute_cycle_model_source_closures_with_optional_children(
        graph.hard_edges, reordered
    ) == expanded
    assert compute_cycle_model_source_closures(graph.hard_edges) == original


def test_absolute_package_root_normalization(tmp_path):
    files = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": "import pkg.b\nfrom outer.pkg import child\n",
        "pkg/b.py": "import pkg.a\n",
        "pkg/child.py": "pass\n",
    }
    graph, imports, _, _ = _candidate(tmp_path, files)
    expanded = compute_cycle_model_source_closures_with_optional_children(
        graph.hard_edges, imports, package_root="outer"
    )
    assert "pkg.child" in expanded[0].evidence_source_modules


def test_n01_n02_domain_and_fact_validation(tmp_path):
    graph, imports, _, _ = _candidate(tmp_path, BASE)
    missing = dict(imports)
    missing.pop("pkg.a")
    with pytest.raises(ValueError):
        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges, missing)
    malformed = dict(imports)
    malformed["pkg.a"] = [object()]
    with pytest.raises(ValueError):
        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges, malformed)


def test_n03_n04_ambiguity_and_invalid_relative(tmp_path):
    graph, imports, _, _ = _candidate(tmp_path, BASE)
    hard = dict(graph.hard_edges)
    hard["pkg"] = set()
    imports["pkg"] = []
    with pytest.raises(ValueError):
        compute_cycle_model_source_closures_with_optional_children(hard, imports)
    imports = dict(imports)
    imports["pkg.a"] = [ImportRef(module=None, level=9, names=["value"], is_from_import=True)]
    with pytest.raises(ValueError):
        compute_cycle_model_source_closures_with_optional_children(graph.hard_edges,
            {name: rows for name, rows in imports.items() if name != "pkg"})


def _pure_capacity_graph(extra_count):
    hard = {"pkg.__init__": set(), "pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}
    hard.update({f"pkg.extra{i}": set() for i in range(extra_count)})
    return hard, {name: [] for name in hard}


def test_n05a_initial_hard_closure_capacity():
    hard, imports = _pure_capacity_graph(257)
    hard["pkg.a"].update(f"pkg.extra{i}" for i in range(257))
    assert set(hard["pkg.a"]) <= set(hard)
    assert set(imports) == set(hard)
    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
        compute_cycle_model_source_closures_with_optional_children(hard, imports)


def test_n05b_optional_expansion_capacity():
    hard = {"pkg.__init__": set(), "pkg.a": {"pkg.b", "pkg.__init__"},
            "pkg.b": {"pkg.a"}}
    hard.update({f"pkg.child{i}": set() for i in range(257)})
    imports = {name: [] for name in hard}
    imports["pkg.a"] = [ImportRef(
        module="pkg", level=0,
        names=[f"child{i}" for i in range(257)], is_from_import=True
    )]
    assert len(compute_cycle_model_source_closures(hard)[0].evidence_source_modules) < 256
    assert set(imports) == set(hard)
    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
        compute_cycle_model_source_closures_with_optional_children(hard, imports)


def test_n05c_multiple_scc_union_capacity():
    hard = {"one.a": {"one.b"}, "one.b": {"one.a"},
            "two.a": {"two.b"}, "two.b": {"two.a"}}
    for prefix in ("one", "two"):
        for i in range(128):
            hard[f"{prefix}.extra{i}"] = set()
            hard[f"{prefix}.a"].add(f"{prefix}.extra{i}")
    imports = {name: [] for name in hard}
    closures = compute_cycle_model_source_closures(hard)
    assert len(closures) == 2
    assert all(len(row.evidence_source_modules) <= 256 for row in closures)
    assert len(set().union(*(set(row.evidence_source_modules) for row in closures))) > 256
    with pytest.raises(ValueError, match="^Selected source capacity exceeded$"):
        compute_cycle_model_source_closures_with_optional_children(hard, imports)


def test_n05d_invalid_hard_target_control(tmp_path):
    graph, imports, _, _ = _candidate(tmp_path, BASE)
    hard = {name: set(targets) for name, targets in graph.hard_edges.items()}
    hard["pkg.a"].add("pkg.missing")
    with pytest.raises(ValueError, match="^Invalid hard graph targets$"):
        compute_cycle_model_source_closures_with_optional_children(hard, imports)


def test_n06_optional_fixed_point_cycle(tmp_path):
    files = {**BASE, "pkg/value.py": "from pkg import a\n"}
    graph, imports, _, expanded = _candidate(tmp_path, files)
    before = {name: set(targets) for name, targets in graph.hard_edges.items()}
    selected = set(expanded[0].evidence_source_modules)
    assert set(expanded[0].members) <= selected
    assert {"pkg.value", "pkg.a"} <= selected
    assert compute_cycle_model_source_closures_with_optional_children(
        graph.hard_edges, imports
    ) == expanded
    assert graph.hard_edges == before


def test_n08_n09_n10_candidate_never_certifies_or_mutates(tmp_path):
    graph, imports, original, expanded = _candidate(tmp_path, BASE)
    before = {name: set(targets) for name, targets in graph.hard_edges.items()}
    assert graph.hard_edges == before
    assert expanded == original
    assert all(not hasattr(row, "status") and not hasattr(row, "model_pass")
               for row in expanded)
