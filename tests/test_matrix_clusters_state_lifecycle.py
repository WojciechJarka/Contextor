"""
tests/test_matrix_clusters_state_lifecycle.py

ETAP 2A — Canonical Dependency Matrix + Shared Usage Clusters Lifecycle Tests.

Proves:
- State field defaults
- Full analysis seeds both families fresh
- Save/hydrate exact parity (fresh payload preserved)
- Legacy absence -> deferred
- Deferred -> RAM materialization (pure RAM, no I/O)
- Stale/resync no-heal
- Empty valid result can be fresh (with explicit empty graph)
- Persisted fresh no recompute
- Recompute failure fails closed (independent per family)
- Independent freshness (matrix stale + clusters fresh, and vice versa)
- Snapshot parity
- Prerequisite trust/freshness propagation (stale prerequisite -> stale derived)
- False-fresh coverage regression (state="fresh" but invalid coverage -> stale derived)
- Deferred prerequisite degrades derived fresh to deferred
- Legacy deferred recovery via materialize_incremental_state
- Graph prerequisite trust for Matrix (missing graph -> Matrix stale, Clusters fresh)
- Real Facade bootstrap resync fails closed to stale
- Real Facade bootstrap Matrix failure isolation (Matrix stale, Clusters fresh)
- Real Facade bootstrap Clusters failure isolation (Matrix fresh, Clusters stale)
- artifact_consumption_is_fresh and dependency_matrix_inputs_are_fresh contract tables
"""

from __future__ import annotations

import builtins
import json
import pickle
import types
import unittest.mock
from pathlib import Path
from typing import Any

import pytest

from contextor.core.analysis.incremental.materialization import (
    ensure_artifact_consumption,
    ensure_dependency_matrix,
    ensure_shared_usage_clusters,
    materialize_incremental_state,
)
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    artifact_consumption_is_fresh,
    dependency_matrix_inputs_are_fresh,
    validate_canonical_artifact_consumption_coverage,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.graph import ProjectGraph
from contextor.core.live_state import hydrate_repository_engine
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.reporting_engine.graph_analytics import (
    compute_dependency_matrix_from_state,
    compute_shared_usage_clusters_from_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_fresh_state() -> RepositoryAnalysisState:
    """Minimal state with fresh artifact_consumption and valid empty graph."""
    st = RepositoryAnalysisState()
    st.artifact_consumption = {}
    st.artifact_consumption_state = "fresh"
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    return st


def _make_nontrivial_fresh_state() -> RepositoryAnalysisState:
    """Fresh state with a concrete artifact + consumption entry and valid graph."""
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo"],
            "symbols": {"functions": ["foo"], "classes": [], "methods": [], "globals": []},
            "consumers": {},
        }
    }
    st.artifact_consumption = {
        "mod_a::foo": {"consumers": [], "channels": {}}
    }
    st.artifact_consumption_state = "fresh"
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    return st


# ---------------------------------------------------------------------------
# 1. State field defaults
# ---------------------------------------------------------------------------

def test_state_fields_present():
    """New fields have correct defaults."""
    st = RepositoryAnalysisState()
    assert hasattr(st, "dependency_matrix")
    assert hasattr(st, "dependency_matrix_state")
    assert hasattr(st, "shared_usage_clusters")
    assert hasattr(st, "shared_usage_clusters_state")
    assert st.dependency_matrix == {}
    assert st.dependency_matrix_state == "deferred"
    assert st.shared_usage_clusters == []
    assert st.shared_usage_clusters_state == "deferred"


# ---------------------------------------------------------------------------
# 2. Full analysis seeds both families fresh
# ---------------------------------------------------------------------------

def test_full_analysis_seeds_both_families_fresh(tmp_path: Path):
    """ContextorFacade.analyze_project seeds dependency_matrix and shared_usage_clusters as fresh."""
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (tmp_path / "mod_b.py").write_text(
        "from mod_a import foo\ndef bar():\n    return foo()\n",
        encoding="utf-8",
    )

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(tmp_path))
    assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"
    assert isinstance(st.dependency_matrix, dict)
    assert isinstance(st.shared_usage_clusters, list)


# ---------------------------------------------------------------------------
# 3. Save/hydrate exact parity (fresh payload preserved)
# ---------------------------------------------------------------------------

def test_save_hydrate_exact_parity(tmp_path: Path):
    """After save + hydrate, both payloads are preserved exactly and states are fresh."""
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (tmp_path / "mod_b.py").write_text(
        "from mod_a import foo\ndef bar():\n    return foo()\n",
        encoding="utf-8",
    )

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(tmp_path))
    assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"

    # Re-compute from current state and compare exact equality
    ref_matrix = compute_dependency_matrix_from_state(st)
    ref_clusters = compute_shared_usage_clusters_from_state(st)

    assert st.dependency_matrix == ref_matrix
    assert st.shared_usage_clusters == ref_clusters


# ---------------------------------------------------------------------------
# 4. Legacy absence -> deferred
# ---------------------------------------------------------------------------

def test_legacy_absence_gives_deferred(tmp_path: Path):
    """Loading a pickle without new fields yields deferred defaults."""
    old_st = RepositoryAnalysisState()
    old_dict = {k: v for k, v in old_st.__dict__.items()
                if k not in ("dependency_matrix", "dependency_matrix_state",
                              "shared_usage_clusters", "shared_usage_clusters_state")}
    old_obj = types.SimpleNamespace(**old_dict)

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    pkl = cache_dir / "engine_state.pkl"
    pkl.write_bytes(pickle.dumps({"metadata": {
        "schema_version": "1.2", "state_id": "test", "revision": 1,
        "writer": "test", "repo_id": "", "root_path": ""
    }, "state": old_obj}))
    (cache_dir / "engine_state.meta.json").write_text(
        json.dumps({
            "schema_version": "1.2", "state_id": "test", "revision": 1,
            "writer": "test", "repo_id": "", "root_path": ""
        }),
        encoding="utf-8",
    )

    result = load_snapshot(str(cache_dir))
    assert result is not None
    loaded_st, _ = result

    assert getattr(loaded_st, "dependency_matrix", None) == {}
    assert getattr(loaded_st, "dependency_matrix_state", None) == "deferred"
    assert getattr(loaded_st, "shared_usage_clusters", None) == []
    assert getattr(loaded_st, "shared_usage_clusters_state", None) == "deferred"


# ---------------------------------------------------------------------------
# 5. Deferred materialization — pure RAM, no I/O
# ---------------------------------------------------------------------------

def test_deferred_materialization_pure_ram():
    """ensure_dependency_matrix and ensure_shared_usage_clusters work with I/O blocked."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"

    ref_matrix = compute_dependency_matrix_from_state(st)
    ref_clusters = compute_shared_usage_clusters_from_state(st)

    def _blocked_open(*args, **kwargs):
        raise AssertionError("Dependency Matrix/Clusters materialization must not open files")

    def _blocked_read_text(self, *args, **kwargs):
        raise AssertionError("Dependency Matrix/Clusters materialization must not read_text")

    def _blocked_read_bytes(self, *args, **kwargs):
        raise AssertionError("Dependency Matrix/Clusters materialization must not read_bytes")

    with (
        unittest.mock.patch("builtins.open", side_effect=_blocked_open),
        unittest.mock.patch.object(Path, "read_text", _blocked_read_text),
        unittest.mock.patch.object(Path, "read_bytes", _blocked_read_bytes),
    ):
        ensure_dependency_matrix(st)
        ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"
    assert st.dependency_matrix == ref_matrix
    assert st.shared_usage_clusters == ref_clusters


# ---------------------------------------------------------------------------
# 6. Stale: no auto-heal
# ---------------------------------------------------------------------------

def test_stale_no_heal():
    """Stale matrix and clusters are NOT recomputed even with fresh artifact_consumption."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix = {"SENTINEL": {}}
    st.dependency_matrix_state = "stale"
    st.shared_usage_clusters = [{"SENTINEL": True}]
    st.shared_usage_clusters_state = "stale"

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"
    assert st.dependency_matrix == {"SENTINEL": {}}
    assert st.shared_usage_clusters == [{"SENTINEL": True}]


# ---------------------------------------------------------------------------
# 7. Resync forces stale on both families
# ---------------------------------------------------------------------------

def test_resync_forces_stale():
    """resync_required=True marks both families stale (even if deferred/fresh)."""
    st = _make_nontrivial_fresh_state()
    st.resync_required = True
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "fresh"

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


# ---------------------------------------------------------------------------
# 8. Empty valid result can be fresh (with explicit empty graph)
# ---------------------------------------------------------------------------

def test_empty_result_is_fresh():
    """Empty repo with explicit valid empty graph produces {} matrix and [] clusters, both marked fresh."""
    st = _make_minimal_fresh_state()  # artifact_consumption = {}, graph = ProjectGraph({}, {})

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "fresh"
    assert st.dependency_matrix == {}
    assert st.shared_usage_clusters_state == "fresh"
    assert st.shared_usage_clusters == []


# ---------------------------------------------------------------------------
# 9. Persisted fresh -> no recompute during materialization
# ---------------------------------------------------------------------------

def test_persisted_fresh_no_recompute():
    """Fresh payload must NOT be recomputed — compute_*_from_state must not be called."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix = {"persisted": {}}
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters = [{"persisted": True}]
    st.shared_usage_clusters_state = "fresh"

    def _raise_matrix(s, **kw):
        raise AssertionError("compute_dependency_matrix_from_state must NOT be called for fresh state")

    def _raise_clusters(s, **kw):
        raise AssertionError("compute_shared_usage_clusters_from_state must NOT be called for fresh state")

    with (
        unittest.mock.patch(
            "contextor.core.reporting_engine.graph_analytics.compute_dependency_matrix_from_state",
            side_effect=_raise_matrix,
        ),
        unittest.mock.patch(
            "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
            side_effect=_raise_clusters,
        ),
    ):
        ensure_dependency_matrix(st)
        ensure_shared_usage_clusters(st)

    # State unchanged
    assert st.dependency_matrix == {"persisted": {}}
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters == [{"persisted": True}]
    assert st.shared_usage_clusters_state == "fresh"


# ---------------------------------------------------------------------------
# 10. Recompute failure fails closed (independent per family)
# ---------------------------------------------------------------------------

def test_recompute_failure_matrix_fails_closed_clusters_unaffected():
    """Matrix recompute failure -> matrix stale, clusters unaffected."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"

    ref_clusters = compute_shared_usage_clusters_from_state(st)

    def _raise(*args, **kw):
        raise RuntimeError("simulated matrix failure")

    with unittest.mock.patch(
        "contextor.core.reporting_engine.graph_analytics.compute_dependency_matrix_from_state",
        side_effect=_raise,
    ):
        ensure_dependency_matrix(st)
        ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"
    assert st.shared_usage_clusters == ref_clusters


def test_recompute_failure_clusters_fails_closed_matrix_unaffected():
    """Clusters recompute failure -> clusters stale, matrix unaffected."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"

    ref_matrix = compute_dependency_matrix_from_state(st)

    def _raise(*args, **kw):
        raise RuntimeError("simulated clusters failure")

    with unittest.mock.patch(
        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
        side_effect=_raise,
    ):
        ensure_dependency_matrix(st)
        ensure_shared_usage_clusters(st)

    assert st.shared_usage_clusters_state == "stale"
    assert st.dependency_matrix_state == "fresh"
    assert st.dependency_matrix == ref_matrix


# ---------------------------------------------------------------------------
# 11. Independent freshness
# ---------------------------------------------------------------------------

def test_independent_freshness_matrix_stale_clusters_fresh():
    """Matrix stale + clusters fresh is a legal independent state."""
    st = _make_nontrivial_fresh_state()
    ref_clusters = compute_shared_usage_clusters_from_state(st)
    st.dependency_matrix_state = "stale"
    st.dependency_matrix = {}
    st.shared_usage_clusters = ref_clusters
    st.shared_usage_clusters_state = "fresh"

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"
    assert st.shared_usage_clusters == ref_clusters


def test_independent_freshness_matrix_fresh_clusters_stale():
    """Matrix fresh + clusters stale is a legal independent state."""
    st = _make_nontrivial_fresh_state()
    ref_matrix = compute_dependency_matrix_from_state(st)
    st.dependency_matrix = ref_matrix
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "stale"
    st.shared_usage_clusters = []

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "stale"
    assert st.dependency_matrix == ref_matrix


# ---------------------------------------------------------------------------
# 12. Snapshot parity vs compute_*_from_state
# ---------------------------------------------------------------------------

def test_snapshot_parity(tmp_path: Path):
    """Hydrated state matrix/clusters == compute_*_from_state(hydrated_state)."""
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (tmp_path / "mod_b.py").write_text(
        "from mod_a import foo\ndef bar():\n    return foo()\n",
        encoding="utf-8",
    )

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(tmp_path))
    assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"

    ref_matrix = compute_dependency_matrix_from_state(st)
    ref_clusters = compute_shared_usage_clusters_from_state(st)

    assert st.dependency_matrix == ref_matrix, "Dependency matrix must match compute_*_from_state"
    assert st.shared_usage_clusters == ref_clusters, "Clusters must match compute_*_from_state"


# ---------------------------------------------------------------------------
# 13. materialize_incremental_state calls both new families
# ---------------------------------------------------------------------------

def test_materialize_incremental_state_calls_both_families():
    """materialize_incremental_state materializes both matrix and clusters."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"
    st.module_usages = {}

    materialize_incremental_state(st)

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"


# ---------------------------------------------------------------------------
# 14. Prerequisite Stale Propagation
# ---------------------------------------------------------------------------

def test_prerequisite_stale_propagates_to_derived_fresh_direct_ensure():
    """
    When artifact_consumption_state == 'stale', derived families previously marked 'fresh'
    must NOT survive and must become 'stale'.
    """
    st = _make_nontrivial_fresh_state()
    st.artifact_consumption_state = "stale"
    st.dependency_matrix = {"persisted": {}}
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters = [{"persisted": True}]
    st.shared_usage_clusters_state = "fresh"

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_prerequisite_stale_propagates_to_derived_fresh_materialize():
    """
    When artifact_consumption_state is 'stale' (even with valid structural coverage),
    materialize_incremental_state forces derived states to 'stale'.
    """
    st = _make_nontrivial_fresh_state()
    st.artifact_consumption_state = "stale"
    st.dependency_matrix = {"persisted": {}}
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters = [{"persisted": True}]
    st.shared_usage_clusters_state = "fresh"
    st.module_usages = {}

    materialize_incremental_state(st)

    assert st.artifact_consumption_state == "stale"
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


# ---------------------------------------------------------------------------
# 15. False-Fresh Coverage Regression
# ---------------------------------------------------------------------------

def test_prerequisite_false_fresh_invalid_coverage_direct_ensure():
    """
    When artifact_consumption_state claims 'fresh' but coverage is invalid (missing symbol),
    derived families must NOT remain fresh — must become 'stale'.
    """
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo", "bar"],
            "symbols": {"functions": ["foo", "bar"], "classes": [], "methods": [], "globals": []},
            "consumers": {},
        }
    }
    st.artifact_consumption = {
        "mod_a::foo": {"consumers": [], "channels": {}}
    }
    st.artifact_consumption_state = "fresh"  # false fresh!
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    st.dependency_matrix = {"cached": {}}
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters = [{"cached": True}]
    st.shared_usage_clusters_state = "fresh"

    assert not artifact_consumption_is_fresh(st)

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_prerequisite_false_fresh_invalid_coverage_materialize():
    """
    When artifact_consumption has incomplete coverage and state is 'fresh',
    materialize_incremental_state degrades artifact_consumption to 'stale'
    and derived families to 'stale'.
    """
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo", "bar"],
            "symbols": {"functions": ["foo", "bar"], "classes": [], "methods": [], "globals": []},
            "consumers": {},
        }
    }
    st.artifact_consumption = {
        "mod_a::foo": {"consumers": [], "channels": {}}
    }
    st.artifact_consumption_state = "fresh"
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "fresh"
    st.module_usages = {}

    materialize_incremental_state(st)

    assert st.artifact_consumption_state == "stale"
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


# ---------------------------------------------------------------------------
# 16. Deferred Prerequisite Degradation
# ---------------------------------------------------------------------------

def test_prerequisite_deferred_degrades_derived_fresh_to_deferred():
    """
    If artifact_consumption is 'deferred' (not yet materialized) and derived family
    is marked 'fresh', direct ensure degrades derived to 'deferred'.
    """
    st = _make_nontrivial_fresh_state()
    st.artifact_consumption_state = "deferred"
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "fresh"

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "deferred"
    assert st.shared_usage_clusters_state == "deferred"


# ---------------------------------------------------------------------------
# 17. Legacy Deferred Recovery
# ---------------------------------------------------------------------------

def test_legacy_deferred_artifact_consumption_recovers_to_fresh():
    """
    Legacy _report artifact_consumption in deferred state with valid graph:
    materialize_incremental_state migrates artifact_consumption to fresh,
    then materializes dependency_matrix and shared_usage_clusters to fresh.
    """
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo"],
            "symbols": {"functions": ["foo"], "classes": [], "methods": [], "globals": []},
            "consumers": {
                "foo": {"consumers": ["mod_b"], "usage": {"direct_calls": ["mod_b"]}}
            },
        }
    }
    st.artifact_consumption = {"_report": {"some": "legacy"}}
    st.artifact_consumption_state = "deferred"
    st.dependency_graph = ProjectGraph(hard_edges={"mod_b": {"mod_a"}}, soft_edges={})
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"
    st.module_usages = {}

    materialize_incremental_state(st)

    assert st.artifact_consumption_state == "fresh"
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"
    assert "mod_a::foo" in st.artifact_consumption
    assert isinstance(st.dependency_matrix, dict)
    assert isinstance(st.shared_usage_clusters, list)


# ---------------------------------------------------------------------------
# 18. Helper Contract Table Tests (Requirement 11)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "ac_state, coverage_valid, resync, expected_ac_fresh, expected_dm_fresh",
    [
        ("fresh", True, False, True, True),
        ("fresh", False, False, False, False),
        ("deferred", True, False, False, False),
        ("stale", True, False, False, False),
        (None, True, False, False, False),
        ("fresh", True, True, False, False),
    ],
)
def test_helper_contract_table(ac_state, coverage_valid, resync, expected_ac_fresh, expected_dm_fresh):
    """Verifies the exact truth table for artifact_consumption_is_fresh and dependency_matrix_inputs_are_fresh."""
    st = RepositoryAnalysisState()
    if coverage_valid:
        st.artifacts = {
            "m": {"own_symbols": ["s"], "symbols": {"functions": ["s"], "classes": [], "methods": [], "globals": []}, "consumers": {}}
        }
        st.artifact_consumption = {"m::s": {"consumers": [], "channels": {}}}
    else:
        st.artifacts = {
            "m": {"own_symbols": ["s", "missing"], "symbols": {"functions": ["s", "missing"], "classes": [], "methods": [], "globals": []}, "consumers": {}}
        }
        st.artifact_consumption = {"m::s": {"consumers": [], "channels": {}}}

    st.artifact_consumption_state = ac_state
    st.resync_required = resync
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})

    assert artifact_consumption_is_fresh(st) is expected_ac_fresh
    assert dependency_matrix_inputs_are_fresh(st) is expected_dm_fresh


# ---------------------------------------------------------------------------
# 19. Graph Prerequisite Tests (Requirement 12)
# ---------------------------------------------------------------------------

def test_graph_prerequisite_explicit_empty_graph():
    """Explicit valid empty graph + fresh AC -> Matrix fresh {}."""
    st = _make_minimal_fresh_state()
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})

    assert dependency_matrix_inputs_are_fresh(st)
    ensure_dependency_matrix(st)
    assert st.dependency_matrix_state == "fresh"
    assert st.dependency_matrix == {}


def test_graph_prerequisite_missing_graph_gives_stale_matrix_clusters_fresh():
    """Missing graph (dependency_graph=None) -> Matrix stale, Clusters can be fresh."""
    st = _make_nontrivial_fresh_state()
    st.dependency_graph = None  # Graph is absent!
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"

    assert not dependency_matrix_inputs_are_fresh(st)
    assert artifact_consumption_is_fresh(st)

    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"


def test_graph_prerequisite_empty_hard_edges_not_treated_as_missing():
    """Graph with hard_edges={} must NOT be treated as missing."""
    st = _make_nontrivial_fresh_state()
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})

    assert dependency_matrix_inputs_are_fresh(st)


def test_graph_prerequisite_resync_with_valid_graph_gives_stale_matrix():
    """resync_required=True with valid graph -> Matrix stale."""
    st = _make_nontrivial_fresh_state()
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    st.resync_required = True

    assert not dependency_matrix_inputs_are_fresh(st)
    ensure_dependency_matrix(st)
    assert st.dependency_matrix_state == "stale"


# ---------------------------------------------------------------------------
# 20. Real Facade Bootstrap Resync & Failure Isolation (Requirements 9, 10)
# ---------------------------------------------------------------------------

def test_real_facade_resync_bootstrap_fails_closed(tmp_path: Path):
    """
    Real execution through ContextorFacade.analyze_project when pipeline result
    contains resync_required=True -> persisted and hydrated state has stale matrix and clusters.
    """
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")

    from contextor.core.reporting_engine import pipeline as pipeline_mod
    real_execute = pipeline_mod.execute_global_pipeline

    def _execute_with_resync(*args, **kwargs):
        res = real_execute(*args, **kwargs)
        analysis_res = res.get("_analysis_result")
        if analysis_res is not None:
            analysis_res.resync_required = True
        return res

    with unittest.mock.patch(
        "contextor.core.api.facade.execute_global_pipeline",
        side_effect=_execute_with_resync,
    ):
        facade = ContextorFacade()
        errors, _ = facade.analyze_project(str(tmp_path))
        assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert getattr(st, "resync_required", False) is True
    assert not artifact_consumption_is_fresh(st)
    assert not dependency_matrix_inputs_are_fresh(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_real_facade_matrix_failure_isolation(tmp_path: Path):
    """
    Real execution through ContextorFacade.analyze_project when Matrix compute fails:
    Matrix is marked stale, while Clusters is marked fresh and persisted.
    """
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")

    def _matrix_raise(s, **kw):
        raise RuntimeError("simulated matrix computation error in facade")

    with unittest.mock.patch(
        "contextor.core.reporting_engine.graph_analytics.compute_dependency_matrix_from_state",
        side_effect=_matrix_raise,
    ):
        facade = ContextorFacade()
        errors, _ = facade.analyze_project(str(tmp_path))
        assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"
    assert isinstance(st.shared_usage_clusters, list)


def test_real_facade_clusters_failure_isolation(tmp_path: Path):
    """
    Real execution through ContextorFacade.analyze_project when Clusters compute fails:
    Matrix is marked fresh, while Clusters is marked stale and persisted.
    """
    (tmp_path / "mod_a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")

    def _clusters_raise(s, **kw):
        raise RuntimeError("simulated clusters computation error in facade")

    with unittest.mock.patch(
        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
        side_effect=_clusters_raise,
    ), unittest.mock.patch(
        "contextor.core.reporting_engine.graph_analytics.is_valid_shared_usage_clusters_handoff",
        return_value=False,
    ):
        facade = ContextorFacade()
        errors, _ = facade.analyze_project(str(tmp_path))
        assert not errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state

    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "stale"
    assert isinstance(st.dependency_matrix, dict)


# ---------------------------------------------------------------------------
# 21. Acceptance Matrix Scenarios
# ---------------------------------------------------------------------------

def test_acceptance_matrix_full_analysis(tmp_path: Path):
    """Full analysis successful -> both fresh."""
    (tmp_path / "a.py").write_text("def x(): pass\n", encoding="utf-8")
    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(tmp_path))
    assert not errors
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    st = hydrated.engine.state
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"


def test_acceptance_matrix_empty_valid():
    """Empty valid result can be fresh (not a truthiness-based check)."""
    st = _make_minimal_fresh_state()
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix == {}
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters == []
    assert st.shared_usage_clusters_state == "fresh"


def test_acceptance_matrix_resync():
    """resync_required -> both stale."""
    st = _make_nontrivial_fresh_state()
    st.resync_required = True
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_acceptance_matrix_matrix_stale_clusters_fresh():
    """matrix stale + clusters fresh — independent."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "stale"
    st.shared_usage_clusters_state = "fresh"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"


def test_acceptance_matrix_matrix_fresh_clusters_stale():
    """matrix fresh + clusters stale — independent."""
    st = _make_nontrivial_fresh_state()
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "stale"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "stale"


def test_acceptance_matrix_prerequisite_stale_derived_fresh():
    """artifact_consumption stale, derived previously fresh -> stale / stale."""
    st = _make_nontrivial_fresh_state()
    st.artifact_consumption_state = "stale"
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "fresh"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_acceptance_matrix_false_fresh_invalid_coverage():
    """artifact_consumption false-fresh (state fresh, coverage invalid) -> stale / stale."""
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo", "missing_sym"],
            "symbols": {"functions": ["foo", "missing_sym"], "classes": [], "methods": [], "globals": []},
            "consumers": {},
        }
    }
    st.artifact_consumption = {
        "mod_a::foo": {"consumers": [], "channels": {}}
    }
    st.artifact_consumption_state = "fresh"
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "fresh"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "stale"


def test_acceptance_matrix_prerequisite_deferred_before_materialization():
    """artifact_consumption deferred before prerequisite materialization -> not fresh."""
    st = _make_nontrivial_fresh_state()
    st.artifact_consumption_state = "deferred"
    st.dependency_matrix_state = "fresh"
    st.shared_usage_clusters_state = "fresh"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state != "fresh"
    assert st.shared_usage_clusters_state != "fresh"
    assert st.dependency_matrix_state == "deferred"
    assert st.shared_usage_clusters_state == "deferred"


def test_acceptance_matrix_legacy_deferred_to_fresh_materialization():
    """artifact_consumption deferred -> successful canonical materialization -> derived fresh."""
    st = RepositoryAnalysisState()
    st.artifacts = {
        "mod_a": {
            "own_symbols": ["foo"],
            "symbols": {"functions": ["foo"], "classes": [], "methods": [], "globals": []},
            "consumers": {},
        }
    }
    st.artifact_consumption = {"_report": {}}
    st.artifact_consumption_state = "deferred"
    st.dependency_graph = ProjectGraph(hard_edges={}, soft_edges={})
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"
    st.module_usages = {}
    materialize_incremental_state(st)
    assert st.artifact_consumption_state == "fresh"
    assert st.dependency_matrix_state == "fresh"
    assert st.shared_usage_clusters_state == "fresh"


def test_acceptance_matrix_missing_graph_gives_stale_matrix_and_fresh_clusters():
    """AC fresh + valid coverage + dependency_graph missing -> Matrix stale, Clusters fresh."""
    st = _make_nontrivial_fresh_state()
    st.dependency_graph = None  # Missing graph
    st.dependency_matrix_state = "deferred"
    st.shared_usage_clusters_state = "deferred"
    ensure_dependency_matrix(st)
    ensure_shared_usage_clusters(st)
    assert st.dependency_matrix_state == "stale"
    assert st.shared_usage_clusters_state == "fresh"
