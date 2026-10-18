"""Incremental invalidation of canonical cycle semantics evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
from contextor.core.cycle_semantics.contracts import (
    UNVERIFIED_RUNTIME_EXECUTION,
    UNVERIFIED_SOURCE_BINDING,
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.edge_sites import (
    CyclicImportSiteReport,
    HardEdgeSiteEvidence,
    SCCImportSiteEvidence,
)
from contextor.core.cycle_semantics.lifecycle import (
    CYCLE_SEMANTICS_INVALIDATION_REASONS,
    invalidate_cycle_semantics,
)
from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _snapshot() -> CycleSemanticsSnapshot:
    members = ("pkg.a", "pkg.b")
    edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
    topology = ImportCycleTopology(
        node_count=2, hard_edge_count=2, total_scc_count=1,
        cyclic_components=(CyclicImportComponent(
            members=members, internal_edges=edges, kind="MULTI_NODE_SCC",
        ),),
    )
    sites = CyclicImportSiteReport(
        topology=topology,
        components=(SCCImportSiteEvidence(
            members=members,
            internal_edges=tuple(
                HardEdgeSiteEvidence(source, target, "UNRESOLVED", ())
                for source, target in edges
            ),
            matched_edge_count=0, unresolved_edge_count=2,
        ),),
    )
    discovery = ConditionalDiscoveryReport(
        candidates=(), examined_outgoing_count=0,
        unavailable_source_modules=(), unresolved_lexical_edge_count=2,
        coverage_status="NO_CONDITIONAL_CANDIDATES",
    )
    return CycleSemanticsSnapshot(
        graph_sha256=fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}),
        cyclic_modules=members,
        observed_source_fingerprints=tuple(
            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
        ),
        source_issues=(), coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
        import_sites=sites, conditional_discovery=discovery,
    )


@pytest.fixture
def cyclic_engine(tmp_path: Path) -> tuple[IncrementalAnalysisEngine, Path, Path]:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    a = pkg / "a.py"
    b = pkg / "b.py"
    a.write_text("import pkg.b\ndef fa():\n    return 1\n", encoding="utf-8")
    b.write_text("import pkg.a\ndef fb():\n    return 2\n", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache)),
        str(tmp_path),
    )
    assert engine.update_file(str(a)).status in {"UPDATED", "ADDED"}
    assert engine.update_file(str(b)).status in {"UPDATED", "ADDED"}
    assert engine.state.cycles_state == "fresh"
    engine.state.cycle_semantics = _snapshot()
    engine.state.cycle_semantics_state = "fresh"
    engine.state.cycle_semantics_invalidation_reason = None
    return engine, a, b


def _assert_stale(engine: IncrementalAnalysisEngine, evidence: CycleSemanticsSnapshot,
                  reason: str) -> None:
    assert engine.state.cycle_semantics is evidence
    assert engine.state.cycle_semantics_state == "stale"
    assert engine.state.cycle_semantics_invalidation_reason == reason


def test_d2_invalidation_preserves_evidence_identity(cyclic_engine) -> None:
    engine, _, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    candidate = engine.state.clone_for_update()
    invalidate_cycle_semantics(candidate, "SOURCE_CHANGED")
    assert candidate.cycle_semantics is evidence
    assert candidate.cycle_semantics_state == "stale"
    assert candidate.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
    assert engine.state.cycle_semantics_state == "fresh"


def test_d2_absent_snapshot_remains_deferred() -> None:
    for reason in CYCLE_SEMANTICS_INVALIDATION_REASONS:
        state = RepositoryAnalysisState(cycle_semantics_state="fresh")
        invalidate_cycle_semantics(state, reason)
        assert (state.cycle_semantics, state.cycle_semantics_state,
                state.cycle_semantics_invalidation_reason) == (None, "deferred", None)


def test_d2_repeated_stale_preserves_first_reason() -> None:
    state = RepositoryAnalysisState(cycle_semantics=_snapshot(), cycle_semantics_state="fresh")
    invalidate_cycle_semantics(state, "SOURCE_CHANGED")
    invalidate_cycle_semantics(state, "SOURCE_DELETED")
    assert state.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
    invalidate_cycle_semantics(state, "CANONICAL_RESYNC_REQUIRED")
    assert state.cycle_semantics_invalidation_reason == "CANONICAL_RESYNC_REQUIRED"


def test_d2_true_unchanged_file_preserves_fresh(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    result = engine.update_file(str(a))
    assert result.status == "UNCHANGED"
    assert engine.state.cycle_semantics is evidence
    assert engine.state.cycle_semantics_state == "fresh"
    assert engine.state.cycle_semantics_invalidation_reason is None


def test_d2_body_only_change_stales_semantics(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    cycles = engine.state.cycles
    a.write_text("import pkg.b\ndef fa():\n    return 10\n", encoding="utf-8")
    engine.update_file(str(a))
    assert engine.state.cycles_state == "fresh"
    assert engine.state.cycles == cycles
    _assert_stale(engine, evidence, "SOURCE_CHANGED")


def test_d2_empty_refresh_plan_stales_semantics(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    old_sha = engine.state_manager.get_tracked_sha256(str(a))
    a.write_text("import pkg.b\ndef fa():\n    return 1\n# changed\n", encoding="utf-8")
    result = engine.update_file(str(a))
    assert result.shadow_plan is not None and result.shadow_plan.is_empty
    assert result.status == "UNCHANGED"
    assert engine.state_manager.get_tracked_sha256(str(a)) != old_sha
    assert engine.state.cycles_state == "fresh"
    _assert_stale(engine, evidence, "SOURCE_CHANGED")


def test_d2_parse_failure_stales_semantics(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    old_graph = engine.state.dependency_graph
    a.write_text("def broken(:\n", encoding="utf-8")
    result = engine.update_file(str(a))
    assert result.status == "SYNTAX_ERROR"
    assert engine.state.dependency_graph is old_graph
    _assert_stale(engine, evidence, "SOURCE_PARSE_FAILED")


def test_d2_import_change_stales_semantics(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    a.write_text("def fa():\n    return 1\n", encoding="utf-8")
    result = engine.update_file(str(a))
    assert result.shadow_plan is not None and not result.shadow_plan.is_empty
    assert engine.state.cycles_state == "fresh"
    assert engine.state.cycles == []
    _assert_stale(engine, evidence, "SOURCE_CHANGED")


def test_d2_delete_stales_semantics(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    a.unlink()
    result = engine.update_file(str(a))
    assert result.status == "DELETED"
    _assert_stale(engine, evidence, "SOURCE_DELETED")


def test_d2_resync_overrides_reason(cyclic_engine) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    engine.state.cycle_semantics_state = "stale"
    engine.state.cycle_semantics_invalidation_reason = "SOURCE_CHANGED"
    engine.state.resync_required = True
    result = engine.update_file(str(a))
    assert result.status == "UNCHANGED"
    _assert_stale(engine, evidence, "CANONICAL_RESYNC_REQUIRED")


def test_d2_normal_commit_rollback_restores_fresh(cyclic_engine, monkeypatch) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    original = engine.state
    cycles = engine.state.cycles
    a.write_text("def fa():\n    return 1\n", encoding="utf-8")
    def fail(*args, **kwargs):
        raise RuntimeError("ack failure")
    monkeypatch.setattr(engine.state_manager, "update_state", fail)
    with pytest.raises(RuntimeError, match="ack failure"):
        engine.update_file(str(a))
    assert engine.state is original
    assert engine.state.cycle_semantics is evidence
    assert engine.state.cycle_semantics_state == "fresh"
    assert engine.state.cycle_semantics_invalidation_reason is None
    assert engine.state.cycles == cycles


def test_d2_empty_plan_rollback_restores_fresh(cyclic_engine, monkeypatch) -> None:
    engine, a, _ = cyclic_engine
    evidence = engine.state.cycle_semantics
    a.write_text("import pkg.b\ndef fa():\n    return 1\n# changed\n", encoding="utf-8")
    def fail(*args, **kwargs):
        raise RuntimeError("ack failure")
    monkeypatch.setattr(engine.state_manager, "update_state", fail)
    with pytest.raises(RuntimeError, match="ack failure"):
        engine.update_file(str(a))
    assert engine.state.cycle_semantics is evidence
    assert engine.state.cycle_semantics_state == "fresh"
    assert engine.state.cycle_semantics_invalidation_reason is None


def test_d2_legacy_state_defaults_fail_closed() -> None:
    state = RepositoryAnalysisState()
    for name in (
        "cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"
    ):
        del state.__dict__[name]
    candidate = _prepare_candidate_state(state)
    assert candidate.cycle_semantics is None
    invalidate_cycle_semantics(candidate, "SOURCE_CHANGED")
    assert candidate.cycle_semantics is None
    assert candidate.cycle_semantics_state == "deferred"
    assert candidate.cycle_semantics_invalidation_reason is None


def test_d2_cold_lifecycle_import_is_isolated() -> None:
    code = (
        "import sys; import contextor.core.cycle_semantics.lifecycle; "
        "assert not any(name == prefix or name.startswith(prefix + '.') "
        "for prefix in ('contextor.ui', 'contextor.repo_generator', 'contextor.mcp') "
        "for name in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
