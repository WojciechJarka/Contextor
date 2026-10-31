"""P1D2C: original-worker evidence reaches P1C0 preparation only."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.original_worker_preparation import (
    prepare_original_worker_cycle_manifest,
)
from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import index_repository
from tests.test_cycle_semantics_evidence import (
    PAIR,
    PASS,
    _bound,
)


@pytest.fixture(autouse=True)
def _inline_index(monkeypatch):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        "1",
    )


def _repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for module_id, source in PASS.items():
        (root / f"{module_id}.py").write_bytes(
            source.encode("utf-8")
        )
    return root


def _index(root, *selected):
    return index_repository(
        str(root),
        source_capture_module_ids=frozenset(selected),
    )


def _snapshot():
    return _bound(PAIR, PASS)[1]


def _prepare(index, snapshot=None, graph=None):
    return prepare_original_worker_cycle_manifest(
        index,
        PAIR if graph is None else graph,
        _snapshot() if snapshot is None else snapshot,
    )


def test_p1d2c_t01_original_bytes_prepare_unpublished_manifest(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    result = _prepare(index)

    assert result.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert result.reason is None
    assert result.source_modules == ("a", "b")

    manifest = result.manifest
    assert manifest is not None
    assert manifest.source_manifest_sha256 is not None
    assert len(manifest.source_manifest_sha256) == 64
    assert manifest.authority == (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    )
    assert len(manifest.components) == 1
    assert manifest.components[0].members == ("a", "b")
    assert manifest.components[0].preparation_state == (
        "PREPARED_UNPUBLISHED"
    )


def test_p1d2c_t02_default_capture_remains_unavailable(
    tmp_path, isolated_dirs,
):
    index = index_repository(str(_repo(tmp_path)))
    result = _prepare(index)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
    )
    assert result.manifest is None
    assert result.source_modules == ()


def test_p1d2c_t03_missing_capture_cannot_prepare(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a")
    result = _prepare(index)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_CLOSURE_CAPTURE_MISSING:b"
    )
    assert result.manifest is None


def test_p1d2c_t04_modified_worker_bytes_rejected(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    altered = dict(index.original_worker_source_snapshots)
    previous = altered["a"]

    altered["a"] = SourceSnapshot(
        raw=b"forged",
        source_fingerprint=previous.source_fingerprint,
    )

    result = _prepare(
        replace(
            index,
            original_worker_source_snapshots=altered,
        )
    )

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_CLOSURE_SOURCE_DIGEST_MISMATCH:a"
    )
    assert result.manifest is None


def test_p1d2c_t05_inconsistent_semantic_graph_rejected(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    snapshot = replace(
        _snapshot(),
        graph_sha256="0" * 64,
    )

    result = _prepare(index, snapshot=snapshot)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "SOURCE_MANIFEST_GRAPH_MISMATCH"
    )
    assert result.manifest is None


def test_p1d2c_t06_partial_semantics_rejected(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    snapshot = replace(
        _snapshot(),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
        source_issues=(
            ("a", "SOURCE_CHANGED_DURING_READ"),
        ),
    )

    result = _prepare(index, snapshot=snapshot)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
    )
    assert result.manifest is None


def test_p1d2c_t07_no_cyclic_component_no_manifest(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    graph = {
        "a": {"b"},
        "b": set(),
    }

    result = _prepare(index, graph=graph)

    assert result.status == "UNAVAILABLE"
    assert result.reason == (
        "BINDING_NO_CYCLIC_COMPONENTS"
    )
    assert result.manifest is None


def test_p1d2c_t08_warm_cache_is_explicit(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index_repository(str(root))
    index = _index(root, "a", "b")

    assert set(
        index.original_worker_ast_modes.values()
    ) == {
        "CACHE_SHA256_EQUIVALENT",
    }

    result = _prepare(index)

    assert result.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert result.manifest is not None


def test_p1d2c_t09_no_filesystem_read_during_preparation(
    tmp_path, isolated_dirs, monkeypatch,
):
    index = _index(_repo(tmp_path), "a", "b")
    snapshot = _snapshot()

    def forbidden_read(self):
        raise AssertionError(
            "manifest preparation attempted filesystem read"
        )

    monkeypatch.setattr(
        Path,
        "read_bytes",
        forbidden_read,
    )

    result = _prepare(
        index,
        snapshot=snapshot,
    )

    assert result.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )


def test_p1d2c_t10_invalid_snapshot_rejected(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")

    with pytest.raises(TypeError):
        prepare_original_worker_cycle_manifest(
            index,
            PAIR,
            None,
        )


def test_p1d2c_t11_deterministic_preparation(
    tmp_path, isolated_dirs,
):
    index = _index(_repo(tmp_path), "a", "b")
    snapshot = _snapshot()

    before = repr((index, snapshot))

    first = _prepare(
        index,
        snapshot=snapshot,
    )
    second = _prepare(
        index,
        snapshot=snapshot,
    )

    assert first == second
    assert first.status == (
        "PREPARED_UNPUBLISHED_NON_ATOMIC"
    )
    assert repr((index, snapshot)) == before
