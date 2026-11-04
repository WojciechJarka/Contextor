"""Focused Python 3.15 explicit-lazy import preservation and model guards."""

import ast
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
from contextor.core.cycle_semantics.execution_context import project_execution_context
from contextor.core.cycle_semantics.initialization_model import evaluate_flat_import_order
from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from contextor.core.cycle_semantics.provenance import extract_import_provenance
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.cycle_semantics import selective_source_replay
from contextor.core.cycle_semantics import selective_worker_capture
from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.graph.graph import build_graph
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.source import ParsedSourceInput
from contextor.core.symbol_engine.indexer import (
    AdvancedImportVisitor,
    IMPORT_CLASSIFICATION_SEMANTICS_VERSION,
)
from contextor.core.symbol_engine import indexer


def _imports(source):
    visitor = AdvancedImportVisitor()
    visitor.visit(ast.parse(source))
    return visitor.found_imports


def _provenance(source):
    return extract_import_provenance(
        ast.parse(source),
        module_id="a",
        source_key="a.py",
        source_path="a.py",
        source_fingerprint="fingerprint",
    )


def test_explicit_lazy_import_and_from_preserved_in_importref():
    eager = _imports("import b\nfrom b import value\n")
    lazy = _imports("lazy import b\nlazy from b import value\n")
    assert [item.is_lazy for item in eager] == [False, False]
    assert [item.is_lazy for item in lazy] == [True, True]
    for left, right in zip(eager, lazy):
        assert {k: v for k, v in asdict(left).items() if k != "is_lazy"} == {
            k: v for k, v in asdict(right).items() if k != "is_lazy"
        }
        assert ImportRef(**asdict(right)) == right


def test_provenance_and_lexical_execution_projections_preserve_declaration():
    facts = _provenance("lazy import b\nlazy from b import value\n")
    assert [item.is_lazy for item in facts.occurrences] == [True, True]
    assert [(item.ordinal, item.line, item.column, item.form) for item in facts.occurrences] == [
        (0, 1, 0, "IMPORT"),
        (1, 2, 0, "IMPORT_FROM"),
    ]
    assert all(item.source_fingerprint == "fingerprint" for item in [facts])
    assert [item.is_lazy for item in project_execution_context(facts).contexts] == [True, True]
    assert all(
        item.initialization_reachability == "UNKNOWN"
        for item in project_execution_context(facts).contexts
    )


def test_legacy_ast_without_lazy_field_defaults_false():
    tree = ast.parse("import b\nfrom b import value\n")
    for node in tree.body:
        if hasattr(node, "is_lazy"):
            del node.is_lazy
    visitor = AdvancedImportVisitor()
    visitor.visit(tree)
    facts = extract_import_provenance(
        tree,
        module_id="a",
        source_key="a.py",
        source_path="a.py",
        source_fingerprint="fingerprint",
    )
    assert [item.is_lazy for item in visitor.found_imports] == [False, False]
    assert [item.is_lazy for item in facts.occurrences] == [False, False]


def test_malformed_ast_lazy_flag_is_rejected():
    tree = ast.parse("import b")
    tree.body[0].is_lazy = "unexpected"
    visitor = AdvancedImportVisitor()
    with pytest.raises(ValueError, match="is_lazy"):
        visitor.visit(tree)
    with pytest.raises(ValueError, match="is_lazy"):
        extract_import_provenance(
            tree, module_id="a", source_key="a.py",
            source_path="a.py", source_fingerprint="fingerprint",
        )


def test_l03_no_false_flat_hazard_and_l01_eager_hazard_retained():
    eager = {
        "a": ast.parse("from b import value\nvalue = 1\n"),
        "b": ast.parse("from a import value\nvalue = 2\n"),
    }
    lazy = {
        "a": ast.parse("lazy from b import value\nvalue = 1\n"),
        "b": ast.parse("lazy from a import value\nvalue = 2\n"),
    }
    assert evaluate_flat_import_order(eager, "a").outcome == "EARLY_BINDING_HAZARD"
    assert evaluate_flat_import_order(lazy, "a").outcome == "UNKNOWN"
    graph = {"a": {"b"}, "b": {"a"}}
    result = analyze_cycle_scenarios(graph, lazy)
    assert result.components[0].classification == "INDETERMINATE"
    assert result.components[0].coverage == "NONE"
    assert result.components[0].reason == "UNMODELED_EXPLICIT_LAZY_IMPORT"
    assert result.topology == analyze_cycle_scenarios(graph, eager).topology


@pytest.mark.parametrize(
    "source",
    [
        "lazy import b\nx = b.value\nvalue = 1\n",
        "lazy from b import value\nx = value\nvalue = 1\n",
    ],
)
def test_lazy_first_use_is_never_model_pass(source):
    tree = ast.parse(source)
    assert evaluate_flat_import_order({"a": tree, "b": ast.parse("import a\nvalue = 2")}, "a").outcome == "UNKNOWN"


def test_package_model_rejects_lazy_imports_in_source_closure():
    sources = {
        "pkg.__init__": ast.parse("lazy from pkg import child\nvalue = 1\n"),
        "pkg.child": ast.parse("from pkg import value\n"),
    }
    assert evaluate_package_import_order(sources, "pkg").outcome == "UNKNOWN"
    graph = {"pkg.__init__": {"pkg.child"}, "pkg.child": {"pkg.__init__"}}
    component = analyze_cycle_scenarios(graph, sources).components[0]
    assert (component.classification, component.coverage, component.reason) == (
        "INDETERMINATE", "NONE", "UNMODELED_EXPLICIT_LAZY_IMPORT",
    )


def test_structural_graph_and_sites_preserve_eager_lazy_edges():
    graph = {"a": {"b"}, "b": {"a"}}
    outputs = []
    for keyword in ("", "lazy "):
        imports = {
            name: _imports(f"{keyword}import {target}\n")
            for name, target in (("a", "b"), ("b", "a"))
        }
        modules = {
            name: Module(name, name + ".py", "/fixture/" + name + ".py", facts)
            for name, facts in imports.items()
        }
        actual = build_graph(modules)
        parsed = {
            name: ParsedSourceInput(
                ast.parse(f"{keyword}import {target}\n"), "a" * 64,
            )
            for name, target in (("a", "b"), ("b", "a"))
        }
        sites = analyze_cyclic_import_sites(graph, parsed)
        outputs.append((actual.hard_edges, sites.topology))
        assert all(
            site.is_lazy is bool(keyword)
            for component in sites.components
            for edge in component.internal_edges
            for site in edge.sites
        )
    assert outputs[0] == outputs[1]
    assert outputs[0][0] == graph


def test_import_semantics_version_and_round_trip():
    assert IMPORT_CLASSIFICATION_SEMANTICS_VERSION == 10
    old = ImportRef("b", 0, [], False)
    new = ImportRef(**{**asdict(old), "is_lazy": True})
    assert old.is_lazy is False
    assert new.is_lazy is True
    assert ImportRef(**asdict(new)) == new


def test_full_and_incremental_import_fact_parity_for_lazy_declaration(tmp_path):
    from tests.test_incremental_equivalence import bootstrap_state, init_engine

    root = tmp_path / "repo"
    root.mkdir()
    target = root / "a.py"
    target.write_text("import b\nvalue = 1\n", encoding="utf-8")
    (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")

    registry = PersistentIdentityRegistry(str(root))
    state = bootstrap_state(root, registry)
    engine = init_engine(tmp_path, root, state, registry)
    target.write_text("lazy import b\nvalue = 1\n", encoding="utf-8")
    result = engine.update_file(str(target))
    assert result.graph_state == "fresh"

    baseline = bootstrap_state(root, PersistentIdentityRegistry(str(root)))
    assert engine.state.modules["a"].imports == baseline.modules["a"].imports
    assert engine.state.modules["a"].imports[0].is_lazy is True
    assert engine.state.dependency_graph.hard_edges == baseline.dependency_graph.hard_edges


@pytest.mark.parametrize("mutation", ["missing", "null", "string", "integer", "malformed_list"])
def test_current_version_malformed_lazy_import_cache_is_reextracted(
    tmp_path, isolated_dirs, monkeypatch, mutation,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text("lazy import b\n", encoding="utf-8")
    (root / "b.py").write_text("pass\n", encoding="utf-8")
    indexer.index_repository(str(root))
    cache = CacheManager(str(root))
    source = root / "a.py"
    record = cache.get(source)
    assert record["import_classification_semantics_version"] == 10
    assert record["imports"][0]["is_lazy"] is True
    if mutation == "missing":
        del record["imports"][0]["is_lazy"]
    elif mutation == "null":
        record["imports"][0]["is_lazy"] = None
    elif mutation == "string":
        record["imports"][0]["is_lazy"] = "true"
    elif mutation == "integer":
        record["imports"][0]["is_lazy"] = 1
    else:
        record["imports"] = {"not": "a list"}
    cache.set(source, record)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    result = indexer.index_repository(str(root))
    assert result.modules["a"].imports[0].is_lazy is True
    assert type(result.modules["a"].imports[0].is_lazy) is bool
    rewritten = cache.get(source)
    assert rewritten["imports"][0]["is_lazy"] is True


@pytest.mark.parametrize("keyword, expected", [("lazy ", True), ("", False)])
def test_current_version_valid_lazy_import_cache_is_reused(
    tmp_path, isolated_dirs, monkeypatch, keyword, expected,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(f"{keyword}import b\n", encoding="utf-8")
    (root / "b.py").write_text("pass\n", encoding="utf-8")
    indexer.index_repository(str(root))
    cache = CacheManager(str(root))
    record = cache.get(root / "a.py")
    assert record["imports"][0]["is_lazy"] is expected
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    original_parse = indexer.parse_source_snapshot

    def reject_target_parse(snapshot, path):
        if path.name == "a.py":
            raise AssertionError("valid current-version cache must be reused")
        return original_parse(snapshot, path)

    monkeypatch.setattr(indexer, "parse_source_snapshot", reject_target_parse)
    result = indexer.index_repository(str(root))
    assert result.modules["a"].imports[0].is_lazy is expected


@pytest.mark.parametrize("keyword, expected", [("lazy ", True), ("", False)])
def test_replay_and_worker_capture_keep_explicit_lazy_fact(
    tmp_path, isolated_dirs, monkeypatch, keyword, expected,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text(f"{keyword}import pkg.b\nvalue = 1\n", encoding="utf-8")
    (pkg / "b.py").write_text("import pkg.a\nvalue = 2\n", encoding="utf-8")

    cold = indexer.index_repository(
        str(root),
        source_capture_module_ids=frozenset({"pkg.a", "pkg.b"}),
    )
    assert cold.modules["pkg.a"].imports[0].is_lazy is expected
    assert cold.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    assert cold.original_worker_source_snapshots["pkg.a"].raw == (
        pkg / "a.py"
    ).read_bytes()

    warm = indexer.index_repository(str(root))
    assert warm.modules["pkg.a"].imports[0].is_lazy is expected
    edges = build_graph(warm.modules).hard_edges
    (replay,) = tuple(
        selective_source_replay.iter_selective_scc_source_replays(
            root, edges, warm,
        )
    )
    assert replay.status == "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    (capture,) = tuple(
        selective_worker_capture.iter_selective_scc_worker_captures(
            root, edges, warm,
        )
    )
    assert capture.status == (
        "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
