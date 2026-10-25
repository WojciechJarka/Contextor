"""P1D2B: pure SCC-closure binding of opted-in original indexer bytes."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.original_worker_binding import (
    assess_original_worker_cycle_closure,
)
from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import index_repository


_GRAPH = {
    "a": {"b", "helper"},
    "b": {"a"},
    "helper": set(),
}


@pytest.fixture(autouse=True)
def _inline_index(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(b"import b\nimport helper\n")
    (root / "b.py").write_bytes(b"import a\n")
    (root / "helper.py").write_bytes(b"value = 1\n")
    return root


def _index(root, *selected):
    return index_repository(
        str(root), source_capture_module_ids=frozenset(selected),
    )


def test_p1d2b_t01_complete_original_indexer_closure(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    index = _index(root, "a", "b", "helper")
    result = assess_original_worker_cycle_closure(index, _GRAPH)
    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    assert result.reason is None
    assert result.cyclic_components == (("a", "b"),)
    assert result.reachable_modules == ("a", "b", "helper")
    assert set(result.source_snapshots) == set(result.reachable_modules)
    assert set(dict(result.ast_modes)) == set(result.reachable_modules)
    assert result.retained_raw_bytes == sum(
        len(item.raw) for item in result.source_snapshots.values()
    )
    for module_id, snapshot in result.source_snapshots.items():
        assert snapshot.raw == (root / f"{module_id}.py").read_bytes()
        assert hashlib.sha256(snapshot.raw).hexdigest() == (
            index.source_fingerprints_by_module[module_id]
        )


def test_p1d2b_t02_default_index_not_authorized(tmp_path, isolated_dirs):
    index = index_repository(str(_repo(tmp_path)))
    result = assess_original_worker_cycle_closure(index, _GRAPH)
    assert result.status == "UNAVAILABLE"
    assert result.reason == "INDEX_CAPTURE_NOT_COMPLETE"
    assert result.source_snapshots == {}
    assert result.retained_raw_bytes == 0


def test_p1d2b_t03_missing_closure_source_rejects_all(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b")
    result = assess_original_worker_cycle_closure(index, _GRAPH)
    assert result.reason == "CLOSURE_CAPTURE_MISSING:helper"
    assert result.source_snapshots == {}
    assert result.ast_modes == ()


def test_p1d2b_t04_tampered_original_bytes_rejected(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b", "helper")
    altered = dict(index.original_worker_source_snapshots)
    old = altered["a"]
    altered["a"] = SourceSnapshot(b"forged", old.source_fingerprint)
    forged_index = replace(index, original_worker_source_snapshots=altered)
    result = assess_original_worker_cycle_closure(forged_index, _GRAPH)
    assert result.reason == "CLOSURE_SOURCE_DIGEST_MISMATCH:a"
    assert result.source_snapshots == {}


def test_p1d2b_t05_invalid_ast_mode_rejected(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b", "helper")
    modes = dict(index.original_worker_ast_modes)
    modes["b"] = "FAKE_AST_MODE"
    result = assess_original_worker_cycle_closure(
        replace(index, original_worker_ast_modes=modes), _GRAPH,
    )
    assert result.reason == "CLOSURE_AST_MODE_INVALID:b"
    assert result.source_snapshots == {}


def test_p1d2b_t06_nonindexed_reachable_module_rejected(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b", "helper")
    graph = {"a": {"b", "ghost"}, "b": {"a"}, "ghost": set()}
    result = assess_original_worker_cycle_closure(index, graph)
    assert result.reason == "CLOSURE_MODULE_NOT_INDEXED:ghost"
    assert result.source_snapshots == {}


def test_p1d2b_t07_closure_above_selection_budget_rejected(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b", "helper")
    graph = {"a": {"a", *(f"x{i}" for i in range(16))}}
    result = assess_original_worker_cycle_closure(index, graph)
    assert result.reason == "CLOSURE_MODULE_LIMIT"
    assert result.source_snapshots == {}


def test_p1d2b_t08_no_cycle_does_not_claim_evidence(tmp_path, isolated_dirs):
    index = _index(_repo(tmp_path), "a", "b", "helper")
    result = assess_original_worker_cycle_closure(index, {
        "a": {"helper"}, "helper": set(), "b": set(),
    })
    assert result.reason == "NO_CYCLIC_COMPONENTS"
    assert result.source_snapshots == {}


def test_p1d2b_t09_multiple_sccs_no_partial_success(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "c.py").write_bytes(b"import d\n")
    (root / "d.py").write_bytes(b"import c\n")
    graph = {**_GRAPH, "c": {"d"}, "d": {"c"}}
    index = _index(root, "a", "b", "helper", "c", "d")
    valid = assess_original_worker_cycle_closure(index, graph)
    assert valid.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    assert valid.cyclic_components == (("a", "b"), ("c", "d"))
    assert valid.reachable_modules == ("a", "b", "c", "d", "helper")
    invalid = assess_original_worker_cycle_closure(
        _index(root, "a", "b", "helper", "c"), graph,
    )
    assert invalid.reason == "CLOSURE_CAPTURE_MISSING:d"
    assert invalid.source_snapshots == {}


def test_p1d2b_t10_warm_cache_equivalence_explicit(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    index_repository(str(root))
    index = _index(root, "a", "b", "helper")
    result = assess_original_worker_cycle_closure(index, _GRAPH)
    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    assert set(dict(result.ast_modes).values()) == {"CACHE_SHA256_EQUIVALENT"}


def test_p1d2b_t11_binding_performs_no_filesystem_reads(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index = _index(root, "a", "b", "helper")

    def forbidden_read(self):
        raise AssertionError("binding performed a new filesystem read")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    result = assess_original_worker_cycle_closure(index, _GRAPH)
    assert result.status == "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
