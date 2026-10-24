"""P1D1B selective SCC worker-source capture regressions."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.analysis.process_pool_lifecycle import (
    managed_reusable_process_pool,
    terminate_active_process_pools,
)
from contextor.core.cycle_semantics import (
    selective_worker_capture as capture,
)
from contextor.core.cycle_semantics import (
    selective_source_replay,
)
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine import indexer as worker_indexer
from contextor.core.symbol_engine.indexer import (
    index_repository,
)
from contextor.core.validator.collisions import (
    compute_collisions_from_facts,
    extract_module_collision_facts,
)


@pytest.fixture(autouse=True)
def _inline_initial_index(monkeypatch):
    monkeypatch.setenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL", "1"
    )


def _repo(tmp_path):
    root = tmp_path / "repo"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    contents = {
        "__init__.py": b"",
        "a.py": b"import pkg.b\nimport pkg.helper\n",
        "b.py": b"import pkg.a\n",
        "helper.py": b"value = 1\n",
        "unrelated.py": b"value = 999\n",
    }
    for name, raw in contents.items():
        (pkg / name).write_bytes(raw)
    return root


def _analyze(root):
    index = index_repository(str(root))
    graph = build_graph(index.modules)
    return index, graph.hard_edges


def _results(root, index, edges, **kwargs):
    return tuple(
        capture.iter_selective_scc_worker_captures(
            root,
            edges,
            index,
            **kwargs,
        )
    )


def _assert_complete(item, index):
    assert item.status == (
        "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
    )
    assert item.reason is None
    assert set(item.source_snapshots) == set(
        item.reachable_modules
    )
    assert set(dict(item.ast_modes)) == set(
        item.reachable_modules
    )
    assert item.retained_raw_bytes == sum(
        len(source.raw)
        for source in item.source_snapshots.values()
    )
    for module_id, source in item.source_snapshots.items():
        assert hashlib.sha256(source.raw).hexdigest() == (
            index.source_fingerprints_by_module[module_id]
        )
    assert "SECOND_PASS" in item.authority
    assert "NOT_ORIGINAL_FULL_INDEX" in item.authority
    assert "NOT_LIVE_CERTIFIED" in item.authority


def test_p1d1b_t01_only_scc_closure_replayed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (item,) = _results(root, index, edges)

    assert item.members == ("pkg.a", "pkg.b")
    assert "pkg.helper" in item.reachable_modules
    assert "pkg.unrelated" not in item.reachable_modules
    _assert_complete(item, index)


def test_p1d1b_t02_warm_cache_mode_is_explicit(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    def forbidden_parse(*args, **kwargs):
        raise AssertionError(
            "warm-cache worker reparsed source"
        )

    monkeypatch.setattr(
        worker_indexer,
        "parse_source_snapshot",
        forbidden_parse,
    )

    (item,) = _results(root, index, edges)

    _assert_complete(item, index)
    assert set(dict(item.ast_modes).values()) == {
        "CACHE_SHA256_EQUIVALENT",
    }


def test_p1d1b_t03_real_process_pool_capture(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    try:
        with managed_reusable_process_pool(
            "indexer"
        ) as (executor, _, _):
            (item,) = _results(
                root, index, edges, executor=executor
            )
        _assert_complete(item, index)
    finally:
        terminate_active_process_pools(timeout=1.0)


def test_p1d1b_t04_post_index_source_drift_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    (root / "pkg" / "a.py").write_bytes(
        b"import pkg.b\nvalue = 123\n"
    )

    (item,) = _results(root, index, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason == (
        "WORKER_INDEX_BYTES_MISMATCH:pkg.a"
    )
    assert item.source_snapshots == {}
    assert item.retained_raw_bytes == 0


def test_p1d1b_t05_per_source_budget_blocks_worker(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    observed = []

    def forbidden(*args, **kwargs):
        observed.append(True)
        raise AssertionError("worker must not execute")

    monkeypatch.setattr(
        capture, "_process_single_file", forbidden
    )

    (item,) = _results(
        root, index, edges, max_source_bytes=4
    )

    assert item.status == "UNAVAILABLE"
    assert item.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )
    assert observed == []
    assert item.source_snapshots == {}


def test_p1d1b_t06_cumulative_closure_budget_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    (complete,) = _results(root, index, edges)
    _assert_complete(complete, index)

    total = complete.retained_raw_bytes
    assert total > 1
    del complete

    (limited,) = _results(
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
    assert limited.ast_modes == ()
    assert limited.retained_raw_bytes == 0


def test_p1d1b_t07_missing_index_member_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    modules = dict(index.modules)
    modules.pop("pkg.helper")
    incomplete = replace(index, modules=modules)

    (item,) = _results(root, incomplete, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason == "MODULE_NOT_INDEXED:pkg.helper"
    assert not item.source_snapshots


def test_p1d1b_t08_import_forgery_fails_closed(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    modules = dict(index.modules)
    modules["pkg.a"] = replace(
        modules["pkg.a"], imports=[]
    )

    (item,) = _results(
        root, replace(index, modules=modules), edges
    )

    assert item.status == "UNAVAILABLE"
    assert item.reason == (
        "WORKER_INDEX_IMPORTS_MISMATCH:pkg.a"
    )
    assert not item.source_snapshots


def test_p1d1b_t09_index_fingerprint_missing(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    hashes = dict(index.source_fingerprints_by_module)
    hashes.pop("pkg.a")

    (item,) = _results(
        root,
        replace(
            index,
            source_fingerprints_by_module=hashes,
        ),
        edges,
    )

    assert item.status == "UNAVAILABLE"
    assert item.reason == (
        "INDEX_FINGERPRINT_UNAVAILABLE:pkg.a"
    )


def test_p1d1b_t10_unrelated_files_not_replayed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    for number in range(250):
        (root / "pkg" / f"unused_{number:04d}.py").write_text(
            f"value = {number}\n",
            encoding="utf-8",
        )

    index, edges = _analyze(root)
    observed = []
    original = capture._process_single_file

    def traced(path, *args, **kwargs):
        observed.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(
        capture, "_process_single_file", traced
    )

    (item,) = _results(root, index, edges)

    _assert_complete(item, index)
    assert observed
    assert not any(
        "unused_" in path for path in observed
    )


def test_p1d1b_t11_independent_scc_budgets(
    tmp_path, isolated_dirs,
):
    root = _repo(tmp_path)
    other = root / "other"
    other.mkdir()
    (other / "__init__.py").write_bytes(b"")
    (other / "a.py").write_bytes(b"import other.b\n")
    (other / "b.py").write_bytes(b"import other.a\n")

    index, edges = _analyze(root)
    outcomes = {
        item.members: item
        for item in capture.iter_selective_scc_worker_captures(
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

    assert outcomes[("pkg.a", "pkg.b")].status == (
        "UNAVAILABLE"
    )
    small = outcomes[("other.a", "other.b")]
    _assert_complete(small, index)
    assert small.retained_raw_bytes <= 32


def test_p1d1b_t12_forged_worker_origin_rejected(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    original = capture._process_single_file

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        result["source_capture_origin"] = "FAKE"
        return result

    monkeypatch.setattr(
        capture, "_process_single_file", forged
    )

    (item,) = _results(root, index, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason.startswith(
        "WORKER_CAPTURE_ORIGIN_INVALID:"
    )
    assert item.source_snapshots == {}


def test_p1d1b_t13_acyclic_graph_has_no_capture(
    tmp_path, isolated_dirs,
):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_bytes(b"value = 1\n")
    index, edges = _analyze(root)

    assert _results(root, index, edges) == ()


def test_p1d1b_t14_invalid_limits_rejected(
    tmp_path, isolated_dirs,
):
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
            _results(root, index, edges, **kwargs)


def test_p1d1b_t15_worker_exception_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)

    def fail(*args, **kwargs):
        raise RuntimeError("injected worker failure")

    monkeypatch.setattr(
        capture, "_process_single_file", fail
    )

    (item,) = _results(root, index, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason.startswith(
        "WORKER_EXECUTION_FAILED:"
    )
    assert item.source_snapshots == {}


def test_p1d1b_t16_worker_module_identity_fails_closed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = _repo(tmp_path)
    index, edges = _analyze(root)
    original = capture._process_single_file

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        result["module_id"] = "forged.module"
        return result

    monkeypatch.setattr(
        capture, "_process_single_file", forged
    )

    (item,) = _results(root, index, edges)

    assert item.status == "UNAVAILABLE"
    assert item.reason.startswith(
        "WORKER_IDENTITY_MISMATCH:"
    )
    assert item.source_snapshots == {}


def test_p1d1b_t17_no_public_definition_collision_with_p1d0():
    modules = {
        "selective_source_replay": selective_source_replay,
        "selective_worker_capture": capture,
    }

    facts = {}

    for module_id, module in modules.items():
        path = Path(module.__file__).resolve()
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        facts[module_id] = extract_module_collision_facts(
            tree,
            module_id,
            str(path),
        )

    assert compute_collisions_from_facts(facts) == []
