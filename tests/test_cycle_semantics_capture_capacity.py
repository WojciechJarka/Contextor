"""WARN-5C bounded source capture cohort regression tests."""

from __future__ import annotations

import pytest

from contextor.core.cycle_semantics import (
    original_worker_binding,
    original_worker_reindex_planning,
)
from contextor.core.symbol_engine import indexer


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def test_t01_module_cap_contracts_are_aligned():
    assert (
        original_worker_reindex_planning._MAX_SELECTED
        == original_worker_binding._MAX_MODULES
        == indexer._MAX_ORIGINAL_WORKER_CAPTURE_MODULES
        == 256
    )


def test_t02_over_limit_capture_selection_rejected(tmp_path):
    selected = frozenset(
        f"module_{index}" for index in range(257)
    )

    with pytest.raises(ValueError):
        indexer.index_repository(
            str(tmp_path),
            source_capture_module_ids=selected,
        )


def test_t03_total_byte_budget_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = tmp_path / "repo"
    root.mkdir()

    (root / "a.py").write_bytes(
        b"value = '" + b"a" * 70 + b"'\n"
    )
    (root / "b.py").write_bytes(
        b"value = '" + b"b" * 70 + b"'\n"
    )

    monkeypatch.setattr(
        indexer,
        "_MAX_ORIGINAL_WORKER_CAPTURE_TOTAL_BYTES",
        100,
    )

    result = indexer.index_repository(
        str(root),
        source_capture_module_ids=frozenset({"a", "b"}),
    )

    assert result.original_worker_capture_status == "UNAVAILABLE"
    assert result.original_worker_capture_reason == (
        "CAPTURE_TOTAL_BYTE_LIMIT"
    )
    assert result.original_worker_source_snapshots == {}
    assert result.original_worker_ast_modes == {}


def test_t04_default_indexing_does_not_capture_sources(
    tmp_path, isolated_dirs,
):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(b"value = 1\n")

    result = indexer.index_repository(str(root))

    assert result.original_worker_capture_status == "NOT_REQUESTED"
    assert result.original_worker_source_snapshots == {}
