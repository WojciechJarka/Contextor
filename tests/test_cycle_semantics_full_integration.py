"""Synthetic FULL integration of canonical cycle semantics evidence."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from time import perf_counter_ns

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
from contextor.core.cycle_semantics.contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
from contextor.core.cycle_semantics.edge_sites import CyclicImportSiteReport
from contextor.core.cycle_semantics.lifecycle import classify_full_cycle_semantics
from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
from contextor.core.errors import AnalysisCancelled
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.symbol_engine.indexer import index_repository


@pytest.fixture
def pair_repo(tmp_path, isolated_dirs, monkeypatch) -> Path:
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "a.py").write_text("import pkg.b\ndef fa():\n    return 1\n", encoding="utf-8")
    (package / "b.py").write_text("import pkg.a\ndef fb():\n    return 2\n", encoding="utf-8")
    return root


def _run_full(root: Path) -> tuple[RepositoryAnalysisState, object]:
    errors, result = ContextorFacade.analyze_project(str(root))
    assert all(error.kind == "ArchitectureCycle" for error in errors), errors
    assert result is not None
    metadata = read_metadata(repo_cache_dir(root))
    assert metadata is not None
    state = load_engine_state(
        str(repo_cache_dir(root)), metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert isinstance(state, RepositoryAnalysisState)
    return state, result


def _partial_snapshot(root: Path, reason: str) -> CycleSemanticsSnapshot:
    index = index_repository(str(root))
    edges = {
        "pkg.__init__": set(), "pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"},
    }
    complete = materialize_cycle_semantics(
        root, edges,
        {module_id: module.path for module_id, module in index.modules.items()},
        index.source_fingerprints_by_module,
    )
    assert complete.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
    return replace(
        complete,
        observed_source_fingerprints=complete.observed_source_fingerprints[1:],
        source_issues=((complete.cyclic_modules[0], reason),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )


def test_d3_complete_full_cycle_materialization(pair_repo) -> None:
    state, _ = _run_full(pair_repo)
    snapshot = state.cycle_semantics
    assert isinstance(snapshot, CycleSemanticsSnapshot)
    assert state.cycle_semantics_state == "fresh"
    assert state.cycle_semantics_invalidation_reason is None
    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
    assert len(snapshot.import_sites.topology.cyclic_components) == 1
    assert snapshot.graph_sha256 == fingerprint_hard_edges(state.dependency_graph.hard_edges)
    assert snapshot.source_issues == ()
    assert snapshot.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
    assert snapshot.observed_source_count == 2
    assert dict(snapshot.observed_source_fingerprints) == {
        module: hashlib.sha256((pair_repo / "pkg" / f"{module[-1]}.py").read_bytes()).hexdigest()
        for module in snapshot.cyclic_modules
    }
    assert snapshot.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
    assert snapshot.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    assert state.cycles_state == "fresh" and state.cycles


def test_d3_full_acyclic_repository(pair_repo) -> None:
    (pair_repo / "pkg" / "b.py").write_text("def fb():\n    return 2\n", encoding="utf-8")
    state, _ = _run_full(pair_repo)
    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
    assert state.cycle_semantics.cyclic_modules == ()
    assert state.cycle_semantics.source_issues == ()
    assert state.cycle_semantics_state == "fresh"
    assert state.cycle_semantics_invalidation_reason is None
    assert state.cycles == [] and state.cycles_state == "fresh"


@pytest.mark.parametrize("reason", [
    "CANONICAL_FINGERPRINT_MISMATCH", "SOURCE_CHANGED_DURING_READ",
])
def test_d3_classify_source_drift_as_stale(pair_repo, reason) -> None:
    snapshot = _partial_snapshot(pair_repo, reason)
    assert classify_full_cycle_semantics(snapshot) == ("stale", "SOURCE_CHANGED")
    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


@pytest.mark.parametrize("reason", [
    "SOURCE_FILE_LIMIT", "SOURCE_COHORT_BYTE_LIMIT", "SOURCE_NOT_COMPILABLE",
])
def test_d3_classify_bounded_partial_as_fresh(pair_repo, reason) -> None:
    snapshot = _partial_snapshot(pair_repo, reason)
    assert classify_full_cycle_semantics(snapshot) == ("fresh", None)
    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


def test_d3a_unknown_source_issue_is_not_fresh(pair_repo) -> None:
    snapshot = _partial_snapshot(pair_repo, "UNKNOWN_FUTURE_SOURCE_ISSUE")
    assert snapshot.source_issues == (("pkg.a", "UNKNOWN_FUTURE_SOURCE_ISSUE"),)
    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)


def test_d3a_unexplained_partial_coverage_is_not_fresh(pair_repo) -> None:
    snapshot = replace(
        _partial_snapshot(pair_repo, "SOURCE_FILE_LIMIT"),
        source_issues=(),
    )
    assert isinstance(snapshot, CycleSemanticsSnapshot)
    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
    assert snapshot.unobserved_source_count == 1
    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)


def test_d3a_unknown_issue_combined_with_bounded_limit(pair_repo) -> None:
    snapshot = replace(
        _partial_snapshot(pair_repo, "SOURCE_FILE_LIMIT"),
        observed_source_fingerprints=(),
        source_issues=(
            ("pkg.a", "SOURCE_FILE_LIMIT"),
            ("pkg.b", "UNKNOWN_FUTURE_SOURCE_ISSUE"),
        ),
    )
    assert snapshot.source_issues == tuple(sorted(set(snapshot.source_issues)))
    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)


def test_d3a_source_drift_precedes_unknown_reason(pair_repo) -> None:
    snapshot = replace(
        _partial_snapshot(pair_repo, "CANONICAL_FINGERPRINT_MISMATCH"),
        observed_source_fingerprints=(),
        source_issues=(
            ("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH"),
            ("pkg.b", "UNKNOWN_FUTURE_SOURCE_ISSUE"),
        ),
    )
    assert classify_full_cycle_semantics(snapshot) == ("stale", "SOURCE_CHANGED")


def test_d3a_complete_empty_cycle_remains_fresh(pair_repo) -> None:
    (pair_repo / "pkg" / "b.py").write_text("def fb():\n    return 2\n", encoding="utf-8")
    state, _ = _run_full(pair_repo)
    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
    assert state.cycle_semantics.cyclic_modules == ()
    assert classify_full_cycle_semantics(state.cycle_semantics) == ("fresh", None)


@pytest.mark.parametrize("reason", [
    "SOURCE_UNREADABLE", "MISSING_OR_INVALID_CANONICAL_PATH",
    "INVALID_CANONICAL_FINGERPRINT",
])
def test_d3_classify_authority_unavailable_as_deferred(pair_repo, reason) -> None:
    snapshot = _partial_snapshot(pair_repo, reason)
    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)


def test_d3_failed_materialization_keeps_full_available(pair_repo, monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise ValueError("synthetic materializer failure")
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail,
    )
    state, _ = _run_full(pair_repo)
    assert state.cycles_state == "fresh" and state.cycles
    assert state.cycle_semantics is None
    assert state.cycle_semantics_state == "deferred"
    assert state.cycle_semantics_invalidation_reason is None


def test_d3_full_materializer_called_once(pair_repo, monkeypatch) -> None:
    import contextor.core.api.facade as facade_module
    import contextor.core.cycle_semantics.materialization as materialization
    original = materialization.materialize_cycle_semantics
    calls = []
    durations_ms = []
    semantic_events = []
    original_trace = facade_module.trace_event
    def collect_trace(domain, event, **fields):
        if event == "CYCLE_SEMANTICS_MATERIALIZATION":
            semantic_events.append(dict(fields))
        return original_trace(domain, event, **fields)
    def counted(root, edges, paths, fingerprints):
        calls.append((root, edges, paths, fingerprints))
        started = perf_counter_ns()
        try:
            return original(root, edges, paths, fingerprints)
        finally:
            durations_ms.append((perf_counter_ns() - started) / 1_000_000)
    monkeypatch.setattr(facade_module, "trace_event", collect_trace)
    monkeypatch.setattr(materialization, "materialize_cycle_semantics", counted)
    state, _ = _run_full(pair_repo)
    assert len(calls) == 1
    root, edges, paths, fingerprints = calls[0]
    assert Path(root).resolve() == pair_repo.resolve()
    assert fingerprint_hard_edges(edges) == fingerprint_hard_edges(state.dependency_graph.hard_edges)
    assert set(paths) == set(state.modules)
    assert set(fingerprints) == set(paths)
    assert all(fingerprints[module] for module in paths)
    assert len(semantic_events) == 1
    assert semantic_events[0]["status"] == "fresh"
    assert semantic_events[0]["count"] == 2
    assert isinstance(semantic_events[0]["elapsed_ms"], (int, float))
    assert semantic_events[0]["elapsed_ms"] > 0
    assert semantic_events[0]["elapsed_ms"] >= durations_ms[0] - 0.05
    print("D3_SYNTHETIC_SEMANTIC_EVENT", semantic_events[0])
    print("D3_SYNTHETIC_MATERIALIZER_MS", durations_ms[0])


def test_d3_full_snapshot_persistence_roundtrip(pair_repo, monkeypatch) -> None:
    state, _ = _run_full(pair_repo)
    import contextor.core.cycle_semantics.materialization as materialization
    def fail(*args, **kwargs):
        raise AssertionError("load must not rematerialize")
    monkeypatch.setattr(materialization, "materialize_cycle_semantics", fail)
    metadata = read_metadata(repo_cache_dir(pair_repo))
    loaded = load_engine_state(
        str(repo_cache_dir(pair_repo)), metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(pair_repo.resolve()),
    )
    assert loaded.cycle_semantics == state.cycle_semantics
    assert isinstance(loaded.cycle_semantics.import_sites, CyclicImportSiteReport)
    assert isinstance(loaded.cycle_semantics.conditional_discovery, ConditionalDiscoveryReport)
    assert loaded.cycle_semantics_state == state.cycle_semantics_state
    assert loaded.cycles == state.cycles


def test_d3_incremental_update_invalidates_full_evidence(pair_repo) -> None:
    state, _ = _run_full(pair_repo)
    assert state.cycle_semantics_state == "fresh"
    hydrated = hydrate_repository_engine(pair_repo)
    assert hydrated is not None
    engine = hydrated.engine
    evidence = engine.state.cycle_semantics
    assert isinstance(evidence, CycleSemanticsSnapshot)
    assert engine.state.cycle_semantics_state == "fresh"
    source = pair_repo / "pkg" / "a.py"
    source.write_text("import pkg.b\ndef fa():\n    return 10\n", encoding="utf-8")
    result = engine.update_file(str(source.resolve()))
    assert result.status in {"UPDATED", "UNCHANGED"}
    assert engine.state.cycle_semantics is evidence
    assert engine.state.cycle_semantics_state == "stale"
    assert engine.state.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
    assert engine.state.cycles_state == "fresh"


def test_d3_full_does_not_execute_indexed_python(pair_repo) -> None:
    (pair_repo / "pkg" / "a.py").write_text(
        "import pkg.b\nraise RuntimeError('should not execute')\n", encoding="utf-8",
    )
    state, _ = _run_full(pair_repo)
    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
    assert state.cycle_semantics.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"


def test_d3_full_cancellation_not_swallowed(pair_repo, monkeypatch) -> None:
    def cancel(*args, **kwargs):
        raise AnalysisCancelled()
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", cancel,
    )
    with pytest.raises(AnalysisCancelled):
        ContextorFacade.analyze_project(str(pair_repo))


def test_d3_report_contract_unchanged(pair_repo) -> None:
    state, result = _run_full(pair_repo)
    output = pair_repo.parent / "output"
    reports = sorted(output.rglob("*.json"))
    assert reports
    assert state.cycles_state == "fresh" and state.cycles
    assert result.cycles == state.cycles
    assert all("cycle_semantics" not in report.read_text(encoding="utf-8") for report in reports)
