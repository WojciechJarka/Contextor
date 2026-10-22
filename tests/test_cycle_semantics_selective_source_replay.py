"""P1D0 selective bounded replay — no source-origin certificate."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
from contextor.core.cycle_semantics import selective_source_replay as replay
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine.indexer import index_repository


def _repo(tmp_path):
    root = tmp_path / "repo"
    package = root / "pkg"
    package.mkdir(parents=True)

    contents = {
        "__init__.py": b"",
        "a.py": b"import pkg.b\nimport pkg.helper\n",
        "b.py": b"import pkg.a\n",
        "helper.py": b"value = 1\n",
        "unrelated.py": b"value = 999\n",
    }

    for name, raw in contents.items():
        (package / name).write_bytes(raw)

    return root


def _analyze(root):
    index = index_repository(str(root))
    graph = build_graph(index.modules)
    return index, graph.hard_edges


def _capture(root, index, edges, **kwargs):
    return tuple(
        replay.iter_selective_scc_source_replays(
            root,
            edges,
            index,
            **kwargs,
        )
    )


def test_p1d0_t01_only_reachable_scc_closure_is_captured(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (item,) = _capture(root, index, edges)

    assert item.members == ("pkg.a", "pkg.b")
    assert item.status == (
        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
    assert item.reason is None
    assert "pkg.unrelated" not in item.reachable_modules
    assert set(item.source_snapshots) == set(
        item.reachable_modules
    )

    for module_id, snapshot in item.source_snapshots.items():
        assert snapshot.source_fingerprint == (
            index.source_fingerprints_by_module[module_id]
        )
        assert hashlib.sha256(snapshot.raw).hexdigest() == (
            snapshot.source_fingerprint
        )

    assert item.retained_raw_bytes == sum(
        len(snapshot.raw)
        for snapshot in item.source_snapshots.values()
    )
    assert "NOT_ORIGINAL_INDEXER_CAPTURE" in item.authority
    assert "NOT_ATOMIC" in item.authority


def test_p1d0_t02_warm_cache_has_same_replay_contract(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    _analyze(root)
    warm_index, edges = _analyze(root)

    (item,) = _capture(root, warm_index, edges)

    assert item.status == (
        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
    assert set(item.source_snapshots) == set(
        item.reachable_modules
    )


def test_p1d0_t03_process_pool_index_is_compatible(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )
    root = _repo(tmp_path)

    try:
        index, edges = _analyze(root)
        (item,) = _capture(root, index, edges)
        assert item.status == (
            "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
        )
        assert set(item.source_snapshots) == set(
            item.reachable_modules
        )
    finally:
        terminate_active_process_pools(timeout=1.0)


def test_p1d0_t04_source_drift_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (root / "pkg" / "a.py").write_bytes(
        b"import pkg.b\nchanged = True\n"
    )

    (item,) = _capture(root, index, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason == (
        "SOURCE_INDEX_BYTES_MISMATCH:pkg.a"
    )
    assert item.source_snapshots == {}
    assert item.retained_raw_bytes == 0


def test_p1d0_t05_source_size_budget_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (item,) = _capture(
        root,
        index,
        edges,
        max_source_bytes=16,
    )

    assert item.status == "UNAVAILABLE"
    assert item.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )
    assert not item.source_snapshots
    assert item.retained_raw_bytes == 0


def test_p1d0_t06_missing_index_member_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    modules = dict(index.modules)
    modules.pop("pkg.helper")
    incomplete = replace(index, modules=modules)

    (item,) = _capture(root, incomplete, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason == "MODULE_NOT_INDEXED:pkg.helper"
    assert item.source_snapshots == {}


def test_p1d0_t07_forged_index_imports_fail_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    modules = dict(index.modules)
    modules["pkg.a"] = replace(
        modules["pkg.a"],
        imports=[],
    )
    forged = replace(index, modules=modules)

    (item,) = _capture(root, forged, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason == (
        "SOURCE_INDEX_IMPORTS_MISMATCH:pkg.a"
    )
    assert item.source_snapshots == {}


def test_p1d0_t08_many_unrelated_files_are_not_read_again(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)

    for number in range(250):
        (root / "pkg" / f"unused_{number:04d}.py").write_text(
            f"value = {number}\n",
            encoding="utf-8",
        )

    index, edges = _analyze(root)

    observed = []
    original_read = replay._read_bounded_bytes

    def traced_read(path, maximum):
        observed.append(path.name)
        return original_read(path, maximum)

    monkeypatch.setattr(
        replay,
        "_read_bounded_bytes",
        traced_read,
    )

    (item,) = _capture(root, index, edges)

    assert item.status == (
        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
    assert observed
    assert "a.py" in observed
    assert "b.py" in observed
    assert not any(
        name.startswith("unused_")
        for name in observed
    )


def test_p1d0_t09_acyclic_graph_yields_no_positive_proof(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    index, edges = _analyze(root)
    assert _capture(root, index, edges) == ()


def test_p1d0_t10_invalid_limits_are_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    for kwargs in (
        {"max_source_bytes": 0},
        {"max_source_bytes": True},
        {"max_source_bytes": 65 * 1024 * 1024},
        {"max_closure_bytes": 0},
        {"max_closure_bytes": True},
        {"max_closure_bytes": 257 * 1024 * 1024},
    ):
        with pytest.raises(ValueError):
            _capture(root, index, edges, **kwargs)


def test_p1d0_t11_cumulative_closure_budget_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
    )
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (complete,) = _capture(root, index, edges)
    assert complete.status == (
        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )

    total = complete.retained_raw_bytes
    assert total > 1
    del complete

    # Each file fits independently, but the complete
    # reachable closure exceeds this cumulative budget.
    (limited,) = _capture(
        root,
        index,
        edges,
        max_source_bytes=1024,
        max_closure_bytes=total - 1,
    )

    assert limited.status == "UNAVAILABLE"
    assert limited.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )
    assert limited.source_snapshots == {}
    assert limited.retained_raw_bytes == 0


def test_p1d0_t12_independent_sccs_have_independent_budgets(
    tmp_path, isolated_dirs, monkeypatch,
):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
    )
    root = _repo(tmp_path)

    other = root / "other"
    other.mkdir()
    (other / "__init__.py").write_bytes(b"")
    (other / "a.py").write_bytes(
        b"import other.b\n"
    )
    (other / "b.py").write_bytes(
        b"import other.a\n"
    )

    index, edges = _analyze(root)

    outcomes = {
        result.members: result
        for result in replay.iter_selective_scc_source_replays(
            root,
            edges,
            index,
            max_source_bytes=128,
            max_closure_bytes=32,
        )
    }

    assert set(outcomes) == {
        ("pkg.a", "pkg.b"),
        ("other.a", "other.b"),
    }

    large = outcomes[("pkg.a", "pkg.b")]
    small = outcomes[("other.a", "other.b")]

    assert large.status == "UNAVAILABLE"
    assert large.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )
    assert large.source_snapshots == {}
    assert large.retained_raw_bytes == 0

    assert small.status == (
        "BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
    assert small.reason is None
    assert set(small.source_snapshots) == set(
        small.reachable_modules
    )
    assert small.retained_raw_bytes <= 32
