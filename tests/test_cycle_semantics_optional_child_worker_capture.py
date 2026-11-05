"""P1B optional named-child original worker byte capture, without publication."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.original_worker_binding import (
    assess_original_worker_cycle_closure,
)
from contextor.core.cycle_semantics.original_worker_reindex_planning import (
    plan_original_worker_reindex,
    verify_original_worker_reindex,
)
from contextor.core.domain.imports import ImportRef
from contextor.core.graph.graph import build_graph
from contextor.core.graph.resolver import build_trie, detect_package_root
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import index_repository
from tests.cycle_semantics_lab import write_synthetic_repository


@pytest.fixture(autouse=True)
def _inline(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


FILES = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": "import pkg.b\nfrom pkg import child\n",
    "pkg/b.py": "import pkg.a\n",
    "pkg/child.py": "import pkg.helper\n",
    "pkg/helper.py": "pass\n",
}


def _pass(root, *, selected=None):
    index = index_repository(
        str(root), source_capture_module_ids=selected
    )
    facts = materialize_reexport_facts_by_module(
        index.modules, index.reference_facts_by_module
    )
    trie = build_trie(index.modules)
    graph = build_graph(
        index.modules, trie=trie,
        package_root=detect_package_root(index.modules, trie),
        reexport_facts_by_module=facts,
    )
    return index, graph


def _case(tmp_path, files=FILES, mode="OPTIONAL_NAMED_CHILDREN"):
    root = tmp_path / "repo"
    write_synthetic_repository(root, files)
    first, graph = _pass(root)
    plan = plan_original_worker_reindex(
        first, graph.hard_edges, source_selection=mode
    )
    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
    second, second_graph = _pass(root, selected=plan.selected_module_ids)
    return root, first, graph, plan, second, second_graph


def _verify(case):
    _, first, graph, plan, second, second_graph = case
    return verify_original_worker_reindex(
        plan, first, graph.hard_edges, second, second_graph.hard_edges
    )


def test_p01_p08_legacy_hard_only_parity(tmp_path):
    case = _case(tmp_path, mode="HARD_ONLY")
    _, first, graph, plan, second, _ = case
    assert plan.source_selection == "HARD_ONLY"
    assert "pkg.child" not in plan.selected_module_ids
    assert plan == plan_original_worker_reindex(first, graph.hard_edges)
    assert assess_original_worker_cycle_closure(
        second, graph.hard_edges
    ).status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"


def test_p02_p04_optional_child_hard_dependency_and_raw_bytes(tmp_path):
    case = _case(tmp_path)
    root, _, graph, plan, second, _ = case
    assert {"pkg.child", "pkg.helper", "pkg.__init__"} <= plan.selected_module_ids
    assert "pkg.child" not in graph.hard_edges["pkg.a"]
    assert set(second.original_worker_source_snapshots) == plan.selected_module_ids
    binding = assess_original_worker_cycle_closure(
        second, graph.hard_edges, source_selection=plan.source_selection
    )
    assert binding.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    for module_id in plan.selected_module_ids:
        raw = binding.source_snapshots[module_id].raw
        assert hashlib.sha256(raw).hexdigest() == dict(plan.fingerprints)[module_id]
    assert _verify(case).source_modules == binding.reachable_modules


def test_p03_eventual_reexport_shadow(tmp_path):
    files = {**FILES, "pkg/__init__.py": "child = 1\n"}
    case = _case(tmp_path, files)
    _, _, graph, plan, _, _ = case
    assert "pkg.child" not in graph.soft_edges["pkg.a"]
    assert "pkg.child" in plan.selected_module_ids
    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"


def test_p05_p06_fixed_point_and_ancestors(tmp_path):
    files = {**FILES, "pkg/child.py": "from pkg.nested import next_child\n",
             "pkg/nested/__init__.py": "pass\n",
             "pkg/nested/next_child.py": "pass\n"}
    case = _case(tmp_path, files)
    plan = case[3]
    assert {"pkg.child", "pkg.nested.__init__", "pkg.nested.next_child"} <= plan.selected_module_ids
    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"


def test_p07_crlf_raw_fingerprint(tmp_path):
    case = _case(tmp_path, {**FILES, "pkg/child.py": "import pkg.helper\r\n"})
    root, _, _, plan, second, _ = case
    raw = second.original_worker_source_snapshots["pkg.child"].raw
    assert b"\r\n" in raw
    assert raw == (root / "pkg" / "child.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == dict(plan.fingerprints)["pkg.child"]
    assert _verify(case).status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"


def test_n01_n02_n03_n04_n05_capture_guards(tmp_path):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    snapshots = dict(second.original_worker_source_snapshots)
    snapshots.pop("pkg.child")
    missing = replace(second, original_worker_source_snapshots=snapshots)
    assert assess_original_worker_cycle_closure(
        missing, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "INDEX_CAPTURE_SHAPE_INVALID"
    assert _verify((None, first, graph, plan, missing, second_graph)).reason == "REINDEX_SELECTION_MISMATCH"

    snapshots = dict(second.original_worker_source_snapshots)
    old = snapshots["pkg.child"]
    snapshots["pkg.child"] = SourceSnapshot(b"forged", old.source_fingerprint)
    wrong = replace(second, original_worker_source_snapshots=snapshots)
    assert assess_original_worker_cycle_closure(
        wrong, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:pkg.child"

    fingerprints = dict(second.source_fingerprints_by_module)
    fingerprints["pkg.child"] = "0" * 64
    stale = replace(second, source_fingerprints_by_module=fingerprints)
    assert assess_original_worker_cycle_closure(
        stale, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:pkg.child"
    assert _verify((None, first, graph, plan, stale, second_graph)).reason == "REINDEX_SOURCE_CHANGED"

    modes = dict(second.original_worker_ast_modes)
    modes["pkg.child"] = "INVALID"
    invalid_mode = replace(second, original_worker_ast_modes=modes)
    assert assess_original_worker_cycle_closure(
        invalid_mode, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_AST_MODE_INVALID:pkg.child"

    snapshots = dict(second.original_worker_source_snapshots)
    snapshots["outside"] = old
    modes = dict(second.original_worker_ast_modes)
    modes["outside"] = "PARSED_FROM_WORKER_READ"
    extra = replace(second, original_worker_source_snapshots=snapshots,
                    original_worker_ast_modes=modes)
    assert assess_original_worker_cycle_closure(
        extra, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_CAPTURE_SET_MISMATCH"
    assert _verify((None, first, graph, plan, extra, second_graph)).reason == "REINDEX_SELECTION_MISMATCH"


def test_n07_n08_n09_n10_n11_selection_and_inventory_guards(tmp_path):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    altered = replace(second, modules={**second.modules, "ghost": second.modules["pkg.a"]})
    assert _verify((None, first, graph, plan, altered, second_graph)).reason == "REINDEX_MODULE_INVENTORY_CHANGED"
    bad_mode = replace(plan, source_selection="INVALID")
    assert _verify((None, first, graph, bad_mode, second, second_graph)).reason == "SOURCE_SELECTION_INVALID"
    assert plan_original_worker_reindex(first, graph.hard_edges,
        source_selection="INVALID").reason == "SOURCE_SELECTION_INVALID"
    malformed = replace(first, modules={**first.modules, "ghost": first.modules["pkg.a"]})
    assert plan_original_worker_reindex(malformed, graph.hard_edges,
        source_selection="OPTIONAL_NAMED_CHILDREN").reason == "GRAPH_INDEX_DOMAIN_MISMATCH"
    hard = {name: set(targets) for name, targets in graph.hard_edges.items()}
    hard["pkg.a"].update(f"pkg.extra{i}" for i in range(257))
    for i in range(257):
        hard[f"pkg.extra{i}"] = set()
    synthetic = replace(first, modules={**first.modules, **{
        f"pkg.extra{i}": first.modules["pkg.a"] for i in range(257)
    }}, source_fingerprints_by_module={**first.source_fingerprints_by_module,
        **{f"pkg.extra{i}": "0" * 64 for i in range(257)}})
    assert plan_original_worker_reindex(synthetic, hard,
        source_selection="OPTIONAL_NAMED_CHILDREN").reason == (
            "SOURCE_SELECTION_INVALID:Selected source capacity exceeded"
        )
    changed_graph = {name: set(targets) for name, targets in second_graph.hard_edges.items()}
    changed_graph["pkg.a"].add("pkg.helper")
    assert _verify((None, first, graph, plan, second, replace(second_graph,
        hard_edges=changed_graph))).reason == "REINDEX_GRAPH_CHANGED"


def test_n07_changed_import_facts_and_package_root(tmp_path):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    module = second.modules["pkg.a"]
    altered = replace(second, modules={**second.modules, "pkg.a": replace(
        module, imports=[ImportRef(module="pkg.b", level=0, names=[], is_from_import=False)]
    )})
    assert _verify((None, first, graph, plan, altered, second_graph)).reason == (
        "REINDEX_CLOSURE_CHANGED"
    )
    root_changed = replace(second, modules={**second.modules, "pkg.a": replace(
        module, imports=[
            ImportRef(module="pkg.b", level=0, names=[], is_from_import=False),
            ImportRef(module="outer.pkg", level=0, names=["child"], is_from_import=True),
            ImportRef(module="outer.pkg.child", level=0, names=[], is_from_import=False),
        ]
    )})
    assert _verify((None, first, graph, plan, root_changed, second_graph)).reason == (
        "REINDEX_PACKAGE_ROOT_CHANGED"
    )


def test_n12_verified_capture_has_no_publication_claim(tmp_path):
    result = _verify(_case(tmp_path))
    assert result.status == "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    assert not hasattr(result, "prepared_manifest")
    assert not hasattr(result, "model_pass")
    assert not hasattr(result, "installed_claim")


def _replace_imports(index, module_id, imports):
    return replace(index, modules={**index.modules, module_id: replace(
        index.modules[module_id], imports=imports
    )})


@pytest.mark.parametrize("field,value", [
    ("is_local", True),
    ("type_only", True),
    ("names", ["child", "helper"]),
])
def test_p1c0_n01_n03_captured_import_fact_replay(tmp_path, field, value):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    original = second.modules["pkg.a"].imports
    changed = [replace(imp, **{field: value}) if imp.is_from_import else imp
               for imp in original]
    forged_first = _replace_imports(first, "pkg.a", changed)
    forged_second = _replace_imports(second, "pkg.a", changed)
    binding = assess_original_worker_cycle_closure(
        forged_second, graph.hard_edges, source_selection=plan.source_selection
    )
    assert binding.reason == "CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
    assert _verify((None, forged_first, graph, plan, forged_second, second_graph)).reason == (
        "REINDEX_BINDING_CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
    )


def test_p1c0_n04_import_order_replay(tmp_path):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    changed = list(reversed(second.modules["pkg.a"].imports))
    assert changed != second.modules["pkg.a"].imports
    forged_first = _replace_imports(first, "pkg.a", changed)
    forged_second = _replace_imports(second, "pkg.a", changed)
    assert assess_original_worker_cycle_closure(
        forged_second, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
    assert _verify((None, forged_first, graph, plan, forged_second, second_graph)).reason == (
        "REINDEX_BINDING_CLOSURE_IMPORT_FACTS_MISMATCH:pkg.a"
    )


def test_p1c0_n05_discovery_import_fact_parity(tmp_path):
    case = _case(tmp_path)
    _, first, graph, plan, second, second_graph = case
    changed = [replace(imp, is_local=True) if imp.is_from_import else imp
               for imp in first.modules["pkg.a"].imports]
    forged_first = _replace_imports(first, "pkg.a", changed)
    assert _verify((None, forged_first, graph, plan, second, second_graph)).reason == (
        "REINDEX_IMPORT_FACTS_CHANGED:pkg.a"
    )


def test_p1c0_n06_unparsable_captured_bytes(tmp_path):
    case = _case(tmp_path)
    _, _, graph, plan, second, _ = case
    raw = b"def =\n"
    digest = hashlib.sha256(raw).hexdigest()
    snapshots = dict(second.original_worker_source_snapshots)
    snapshots["pkg.child"] = SourceSnapshot(raw, digest)
    fingerprints = dict(second.source_fingerprints_by_module)
    fingerprints["pkg.child"] = digest
    forged = replace(second, original_worker_source_snapshots=snapshots,
                     source_fingerprints_by_module=fingerprints)
    assert assess_original_worker_cycle_closure(
        forged, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_IMPORT_REPLAY_UNAVAILABLE:pkg.child"


def test_p1c0_n07_extractor_unavailable(tmp_path, monkeypatch):
    case = _case(tmp_path)
    _, _, graph, plan, second, _ = case
    monkeypatch.setattr(
        "contextor.core.symbol_engine.indexer.read_imports",
        lambda path, *, tree: (None, "unavailable"),
    )
    assert assess_original_worker_cycle_closure(
        second, graph.hard_edges, source_selection=plan.source_selection
    ).reason == "CLOSURE_IMPORT_REPLAY_UNAVAILABLE:pkg.__init__"
