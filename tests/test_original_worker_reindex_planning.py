"""P1D2E: bounded two-pass capture plan and consistency gates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.cycle_semantics.materialization import (
    materialize_cycle_semantics,
)
from contextor.core.cycle_semantics.original_worker_preparation import (
    prepare_original_worker_cycle_manifest,
)
from contextor.core.cycle_semantics.original_worker_reindex_planning import (
    plan_original_worker_reindex,
    verify_original_worker_reindex,
)
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine.indexer import index_repository


@pytest.fixture(autouse=True)
def _inline_by_default(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(
        b"import b\nimport helper\nvalue = 1\n"
    )
    (root / "b.py").write_bytes(
        b"import a\nvalue = 2\n"
    )
    (root / "helper.py").write_bytes(b"value = 3\n")
    (root / "unrelated.py").write_bytes(b"value = 999\n")
    return root


def _index_and_graph(root, selected=None):
    if selected is None:
        index = index_repository(str(root))
    else:
        index = index_repository(
            str(root),
            source_capture_module_ids=selected,
        )
    return index, build_graph(index.modules).hard_edges


def _two_pass(root):
    first, first_edges = _index_and_graph(root)
    plan = plan_original_worker_reindex(first, first_edges)
    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"

    second, second_edges = _index_and_graph(
        root,
        plan.selected_module_ids,
    )
    return first, first_edges, plan, second, second_edges


def _verify(first, first_edges, plan, second, second_edges):
    return verify_original_worker_reindex(
        plan,
        first,
        first_edges,
        second,
        second_edges,
    )


def test_p1d2e_t01_real_two_pass_then_prepared_only(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges, plan, second, second_edges = _two_pass(root)

    assert plan.selected_module_ids == frozenset({
        "a", "b", "helper",
    })
    assert "unrelated" not in plan.selected_module_ids
    assert first.original_worker_capture_status == "NOT_REQUESTED"

    verified = _verify(
        first, first_edges, plan, second, second_edges,
    )
    assert verified.status == (
        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    )
    assert verified.reason is None
    assert verified.source_modules == ("a", "b", "helper")

    snapshot = materialize_cycle_semantics(
        root,
        second_edges,
        {
            module_id: module.path
            for module_id, module in second.modules.items()
        },
        second.source_fingerprints_by_module,
    )
    prepared = prepare_original_worker_cycle_manifest(
        second, second_edges, snapshot,
    )
    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert prepared.manifest is not None
    assert prepared.manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )


def test_p1d2e_t02_warm_cache_second_pass(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges, plan, second, second_edges = _two_pass(root)

    assert set(second.original_worker_ast_modes.values()) == {
        "CACHE_SHA256_EQUIVALENT"
    }
    verified = _verify(
        first, first_edges, plan, second, second_edges,
    )
    assert verified.status == (
        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    )


def test_p1d2e_t03_no_cycle_produces_no_plan(
    tmp_path, isolated_dirs,
):
    first, _ = _index_and_graph(_repo(tmp_path))
    acyclic = {
        "a": {"helper"},
        "b": set(),
        "helper": set(),
        "unrelated": set(),
    }
    plan = plan_original_worker_reindex(first, acyclic)
    assert plan.status == "UNAVAILABLE"
    assert plan.reason == "NO_CYCLIC_COMPONENTS"
    assert plan.selected_module_ids == frozenset()


def test_p1d2e_t04_large_closure_rejected_before_reindex(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    imports = [b"import b", b"import helper"]
    for number in range(255):
        name = f"h{number}"
        (root / f"{name}.py").write_bytes(b"value = 1\n")
        imports.append(f"import {name}".encode("ascii"))

    (root / "a.py").write_bytes(
        b"\n".join(imports) + b"\nvalue = 1\n"
    )

    first, graph = _index_and_graph(root)
    plan = plan_original_worker_reindex(first, graph)

    assert plan.status == "UNAVAILABLE"
    assert plan.reason == "CLOSURE_MODULE_LIMIT"
    assert plan.selected_module_ids == frozenset()


def test_warn_5c_217_module_cohort_remains_verified(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    imports = [b"import b", b"import helper"]

    for number in range(214):
        name = f"h{number}"
        (root / f"{name}.py").write_bytes(b"value = 1\n")
        imports.append(f"import {name}".encode("ascii"))

    (root / "a.py").write_bytes(
        b"\n".join(imports) + b"\nvalue = 1\n"
    )

    first, graph = _index_and_graph(root)
    plan = plan_original_worker_reindex(first, graph)

    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
    assert plan.reason is None
    assert len(plan.selected_module_ids) == 217

    second, second_graph = _index_and_graph(
        root,
        plan.selected_module_ids,
    )

    assert second.original_worker_capture_status == (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    )
    assert len(second.original_worker_source_snapshots) == 217
    assert len(second.original_worker_ast_modes) == 217

    verified = _verify(
        first,
        graph,
        plan,
        second,
        second_graph,
    )

    assert verified.status == (
        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    )
    assert verified.source_modules == tuple(
        sorted(plan.selected_module_ids)
    )


def test_p1d2e_t05_source_change_between_passes_rejected(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges = _index_and_graph(root)
    plan = plan_original_worker_reindex(first, first_edges)

    (root / "helper.py").write_bytes(b"value = 300\n")

    second, second_edges = _index_and_graph(
        root, plan.selected_module_ids,
    )
    verified = _verify(
        first, first_edges, plan, second, second_edges,
    )

    assert verified.status == "UNAVAILABLE"
    assert verified.reason == "REINDEX_SOURCE_CHANGED"
    assert verified.source_modules == ()


def test_p1d2e_t06_changed_graph_rejected(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges, plan, second, second_edges = _two_pass(root)

    altered = {
        name: set(targets)
        for name, targets in second_edges.items()
    }
    altered["a"].remove("helper")

    verified = _verify(
        first, first_edges, plan, second, altered,
    )
    assert verified.status == "UNAVAILABLE"
    assert verified.reason == "REINDEX_GRAPH_CHANGED"


def test_p1d2e_t07_missing_capture_selection_rejected(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges = _index_and_graph(root)
    plan = plan_original_worker_reindex(first, first_edges)

    second, second_edges = _index_and_graph(
        root, frozenset({"a", "b"}),
    )
    verified = _verify(
        first, first_edges, plan, second, second_edges,
    )

    assert verified.status == "UNAVAILABLE"
    assert verified.reason == "REINDEX_SELECTION_MISMATCH"


def test_p1d2e_t08_changed_module_inventory_rejected(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    first, first_edges, plan, second, second_edges = _two_pass(root)

    altered_modules = dict(second.modules)
    altered_modules.pop("unrelated")
    altered_second = replace(
        second,
        modules=altered_modules,
    )

    verified = _verify(
        first, first_edges, plan, altered_second, second_edges,
    )
    assert verified.status == "UNAVAILABLE"
    assert verified.reason == "REINDEX_MODULE_INVENTORY_CHANGED"


def test_p1d2e_t09_real_process_pool_two_pass(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    terminate_active_process_pools(timeout=1.0)
    try:
        first, first_edges, plan, second, second_edges = _two_pass(root)
        verified = _verify(
            first, first_edges, plan, second, second_edges,
        )
        assert verified.status == (
            "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
        )
    finally:
        terminate_active_process_pools(timeout=1.0)


def test_p1d2e_t10_graph_inventory_mismatch_rejected(
    tmp_path, isolated_dirs,
):
    first, edges = _index_and_graph(_repo(tmp_path))
    altered = {
        key: value
        for key, value in edges.items()
        if key != "unrelated"
    }
    plan = plan_original_worker_reindex(first, altered)

    assert plan.status == "UNAVAILABLE"
    assert plan.reason == "GRAPH_INDEX_DOMAIN_MISMATCH"


def test_p1d2e_t11_planning_verification_no_disk_reads(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    first, first_edges, plan, second, second_edges = _two_pass(root)

    def forbidden_read(self):
        raise AssertionError("unexpected source read")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)

    repeated = plan_original_worker_reindex(
        first, first_edges,
    )
    verified = _verify(
        first, first_edges, repeated, second, second_edges,
    )

    assert repeated == plan
    assert verified.status == (
        "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"
    )

