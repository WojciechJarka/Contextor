"""P1D2A: bounded original-worker capture handoff, not publication."""

from __future__ import annotations

import hashlib

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.symbol_engine import indexer


@pytest.fixture(autouse=True)
def _inline_by_default(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(b"import os\nvalue = os.name\n")
    (root / "b.py").write_bytes(b"other = 2\n")
    return root


def _index(root, *selected):
    return indexer.index_repository(
        str(root), source_capture_module_ids=frozenset(selected),
    )


def test_p1d2a_t01_default_remains_capture_free(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    result = indexer.index_repository(str(root))
    assert result.original_worker_capture_status == "NOT_REQUESTED"
    assert result.original_worker_source_snapshots == {}
    assert result.original_worker_ast_modes == {}
    assert result.original_worker_capture_reason is None


def test_p1d2a_t02_only_selected_original_worker_bytes(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    result = _index(root, "a")
    assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    assert result.original_worker_capture_reason is None
    assert set(result.original_worker_source_snapshots) == {"a"}
    assert set(result.original_worker_ast_modes) == {"a"}
    raw = (root / "a.py").read_bytes()
    snap = result.original_worker_source_snapshots["a"]
    assert snap.raw == raw
    assert snap.source_fingerprint == hashlib.sha256(raw).hexdigest()
    assert snap.source_fingerprint == result.source_fingerprints_by_module["a"]
    assert result.original_worker_ast_modes["a"] in {
        "PARSED_FROM_WORKER_READ", "CACHE_SHA256_EQUIVALENT",
    }
    assert "b" in result.modules


def test_p1d2a_t03_warm_cache_keeps_equivalent_mode(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    indexer.index_repository(str(root))
    result = _index(root, "a")
    assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    assert result.original_worker_ast_modes["a"] == "CACHE_SHA256_EQUIVALENT"


def test_p1d2a_t04_missing_selected_module_no_partial_data(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    result = _index(root, "a", "missing")
    assert result.original_worker_capture_status == "UNAVAILABLE"
    assert result.original_worker_capture_reason == "SELECTED_MODULE_NOT_INDEXED"
    assert result.original_worker_source_snapshots == {}
    assert result.original_worker_ast_modes == {}


def test_p1d2a_t05_byte_limit_fails_closed(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "big.py").write_bytes(b"#" + b"a" * (2 * 1024 * 1024) + b"\n")
    result = _index(root, "a", "big")
    assert result.original_worker_capture_status == "UNAVAILABLE"
    assert result.original_worker_capture_reason == "BYTE_LIMIT"
    assert result.original_worker_source_snapshots == {}
    assert result.original_worker_ast_modes == {}


def test_p1d2a_t06_invalid_selector_rejected(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    invalid = [
        "a",
        frozenset({""}),
        frozenset({"a", 7}),
        frozenset(f"x{i}" for i in range(257)),
    ]
    for selected in invalid:
        with pytest.raises(ValueError):
            indexer.index_repository(str(root), source_capture_module_ids=selected)


def test_p1d2a_t07_forged_worker_capture_rejected(tmp_path, isolated_dirs, monkeypatch):
    root = _repo(tmp_path)
    original = indexer._process_single_file

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        if result["module_id"] == "a":
            result["source_capture_bytes"] = b"forged"
        return result

    monkeypatch.setattr(indexer, "_process_single_file", forged)
    result = _index(root, "a")
    assert result.original_worker_capture_status == "UNAVAILABLE"
    assert result.original_worker_capture_reason == "INVALID_WORKER_CAPTURE"
    assert result.original_worker_source_snapshots == {}


def test_p1d2a_t08_selected_parse_failure_no_partial_data(tmp_path, isolated_dirs):
    root = _repo(tmp_path)
    (root / "broken.py").write_bytes(b"def oops(:\n    pass\n")
    result = _index(root, "a", "broken")
    assert result.original_worker_capture_status == "UNAVAILABLE"
    assert result.original_worker_capture_reason == "SOURCE_PARSE_FAILED"
    assert result.original_worker_source_snapshots == {}


def test_p1d2a_t09_real_pool_capture(tmp_path, isolated_dirs, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    terminate_active_process_pools(timeout=1.0)
    try:
        result = _index(root, "a")
        assert result.original_worker_capture_status == "ALL_SELECTED_CAPTURED_NON_ATOMIC"
        raw = (root / "a.py").read_bytes()
        assert result.original_worker_source_snapshots["a"].raw == raw
        assert result.original_worker_source_snapshots["a"].source_fingerprint == (
            result.source_fingerprints_by_module["a"]
        )
    finally:
        terminate_active_process_pools(timeout=1.0)
