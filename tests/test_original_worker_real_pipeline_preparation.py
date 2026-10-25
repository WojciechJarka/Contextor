"""P1D2D: real analysis components to prepared-only worker manifest."""

from __future__ import annotations

from dataclasses import replace

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.cycle_semantics.contracts import (
    fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.materialization import (
    materialize_cycle_semantics,
)
from contextor.core.cycle_semantics.original_worker_preparation import (
    prepare_original_worker_cycle_manifest,
)
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine.indexer import index_repository


_SELECTED = frozenset({
    "pkg.__init__",
    "pkg.a",
    "pkg.b",
    "pkg.helper",
})


@pytest.fixture(autouse=True)
def _inline_by_default(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path):
    root = tmp_path / "repo"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)

    (pkg / "__init__.py").write_bytes(b"")
    (pkg / "a.py").write_bytes(
        b"import pkg.b\n"
        b"import pkg.helper\n"
        b"def fa():\n"
        b"    return 1\n"
    )
    (pkg / "b.py").write_bytes(
        b"import pkg.a\n"
        b"def fb():\n"
        b"    return 2\n"
    )
    (pkg / "helper.py").write_bytes(b"value = 1\n")
    (pkg / "unrelated.py").write_bytes(b"value = 999\n")

    return root


def _analyze_components(root, selected=_SELECTED):
    index = index_repository(
        str(root),
        source_capture_module_ids=selected,
    )
    graph = build_graph(index.modules)
    snapshot = materialize_cycle_semantics(
        root,
        graph.hard_edges,
        {
            module_id: module.path
            for module_id, module in index.modules.items()
        },
        index.source_fingerprints_by_module,
    )
    return index, graph, snapshot


def _prepare(index, graph, snapshot):
    return prepare_original_worker_cycle_manifest(
        index,
        graph.hard_edges,
        snapshot,
    )


def test_p1d2d_t01_real_component_chain_prepares_only(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, graph, snapshot = _analyze_components(root)

    assert index.original_worker_capture_status == (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    )
    assert snapshot.coverage_status == (
        "FILESYSTEM_STABLE_NON_ATOMIC"
    )
    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
    assert snapshot.graph_sha256 == fingerprint_hard_edges(
        graph.hard_edges
    )

    result = _prepare(index, graph, snapshot)

    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.reason is None
    assert result.manifest is not None
    assert result.manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )
    assert result.manifest.source_manifest_sha256 is not None
    assert result.manifest.components[0].members == (
        "pkg.a",
        "pkg.b",
    )
    assert {
        "pkg.a",
        "pkg.b",
        "pkg.helper",
    }.issubset(result.source_modules)
    assert "pkg.unrelated" not in result.source_modules


def test_p1d2d_t02_warm_cache_keeps_preparation_valid(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index_repository(str(root))

    index, graph, snapshot = _analyze_components(root)

    assert set(index.original_worker_ast_modes.values()) == {
        "CACHE_SHA256_EQUIVALENT"
    }

    result = _prepare(index, graph, snapshot)

    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert result.manifest is not None


def test_p1d2d_t03_default_index_cannot_prepare_manifest(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, graph, snapshot = _analyze_components(
        root,
        selected=None,
    )

    result = _prepare(index, graph, snapshot)

    assert result.status == "UNAVAILABLE"
    assert result.reason == "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
    assert result.manifest is None


def test_p1d2d_t04_missing_reachable_capture_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    selected = frozenset({
        "pkg.__init__",
        "pkg.a",
        "pkg.b",
    })
    index, graph, snapshot = _analyze_components(
        root,
        selected=selected,
    )

    result = _prepare(index, graph, snapshot)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_CLOSURE_CAPTURE_MISSING:pkg.helper"
    )
    assert result.manifest is None
    assert result.source_modules == ()


def test_p1d2d_t05_cyclic_source_drift_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)

    index = index_repository(
        str(root),
        source_capture_module_ids=_SELECTED,
    )
    graph = build_graph(index.modules)

    (root / "pkg" / "a.py").write_bytes(
        b"import pkg.b\n"
        b"import pkg.helper\n"
        b"def fa():\n"
        b"    return 99\n"
    )

    snapshot = materialize_cycle_semantics(
        root,
        graph.hard_edges,
        {
            module_id: module.path
            for module_id, module in index.modules.items()
        },
        index.source_fingerprints_by_module,
    )

    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"

    result = _prepare(index, graph, snapshot)

    assert result.status == "UNAVAILABLE"
    assert result.manifest is None


def test_p1d2d_t06_graph_identity_mismatch_rejected(
    tmp_path, isolated_dirs,
):
    index, graph, snapshot = _analyze_components(_repo(tmp_path))

    altered = replace(snapshot, graph_sha256="0" * 64)
    result = _prepare(index, graph, altered)

    assert result.status == "UNAVAILABLE"
    assert result.manifest is None


def test_p1d2d_t07_real_process_pool_component_chain(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    terminate_active_process_pools(timeout=1.0)
    try:
        index, graph, snapshot = _analyze_components(root)
        result = _prepare(index, graph, snapshot)

        assert index.original_worker_capture_status == (
            "ALL_SELECTED_CAPTURED_NON_ATOMIC"
        )
        assert result.status == (
            "PREPARED_UNPUBLISHED_NON_ATOMIC"
        )
        assert result.manifest is not None
    finally:
        terminate_active_process_pools(timeout=1.0)
