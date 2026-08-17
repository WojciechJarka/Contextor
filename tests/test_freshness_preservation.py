"""
tests/test_freshness_preservation.py

Stage 3C.2b — Freshness Preservation Semantics Tests.
Verifies invalidation and preservation semantics for all freshness fields across
BODY-ONLY, NO-OP, IMPORT CHANGE, and requires_resync scenarios without adding fake work.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _create_engine(tmp_path: Path) -> IncrementalAnalysisEngine:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    return IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )


def test_freshness_scenario_a_body_only(tmp_path):
    """
    BODY-ONLY:
    Graph is NOT invalidated -> graph_state remains 'fresh' without graph patch execution.
    Artifact consumption is invalidated and patched -> artifact_consumption_state is 'fresh'.
    Blast radius is not computed for body-only -> blast_radius_state is 'deferred'.
    """
    engine = _create_engine(tmp_path)
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")

    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))

    # Modify body only: foo() -> bar()
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    # Assert plan-vs-execution invariant: NO graph patch or graph recomputation in plan
    assert "dependency_graph" not in res.shadow_plan.patch_families
    assert res.shadow_plan.graph_recomputations == ()
    assert res.execution_trace["patch_families"] == res.shadow_plan.patch_families
    assert res.execution_trace["graph_recomputations"] == ()

    # Assert freshness semantics: graph is preserved fresh, blast radius is deferred
    assert res.graph_state == "fresh"
    assert res.dependencies_state == "fresh"
    assert res.artifact_consumption_state == "fresh"
    assert res.blast_radius_state == "deferred"
    assert res.local_metrics_state == "deferred"
    assert res.global_metrics_state == "deferred"


def test_freshness_scenario_b_noop(tmp_path):
    """
    NO-OP:
    No execution work is run.
    Previously fresh state is preserved as 'fresh'.
    No freshness downgrade to 'stale'.
    """
    engine = _create_engine(tmp_path)
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    engine.update_file(str(f_target))

    # 1. mtime unchanged no-op
    res1 = engine.update_file(str(f_target))
    assert res1.status == "UNCHANGED"
    assert res1.graph_state == "fresh"
    assert res1.dependencies_state == "fresh"
    assert res1.artifact_consumption_state == "fresh"

    # 2. Semantic no-op with mtime change (same content, newer timestamp)
    import os, time
    now = time.time() + 10
    os.utime(str(f_target), (now, now))
    res2 = engine.update_file(str(f_target))

    assert res2.status == "UNCHANGED"
    if res2.shadow_plan is not None:
        assert res2.shadow_plan.is_empty
    assert res2.graph_state == "fresh"
    assert res2.dependencies_state == "fresh"
    assert res2.artifact_consumption_state == "fresh"
    assert res2.blast_radius_state == "deferred"




def test_freshness_scenario_c_import_change(tmp_path):
    """
    IMPORT CHANGE:
    Graph is invalidated and patched -> graph_state is 'fresh'.
    Reverse blast-radius is computed -> blast_radius_state is 'fresh'.
    Artifact consumption is patched -> artifact_consumption_state is 'fresh'.
    """
    engine = _create_engine(tmp_path)
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_other = tmp_path / "other.py"
    f_other.write_text("def bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\ntarget.foo()\n", encoding="utf-8")

    engine.update_file(str(f_target))
    engine.update_file(str(f_other))
    engine.update_file(str(f_consumer))

    # Add import other
    f_consumer.write_text("import target\nimport other\ntarget.foo()\nother.bar()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    assert "dependency_graph" in res.shadow_plan.patch_families
    assert "reverse_blast_radius" in res.shadow_plan.graph_recomputations
    assert res.execution_trace["patch_families"] == res.shadow_plan.patch_families
    assert res.execution_trace["graph_recomputations"] == res.shadow_plan.graph_recomputations

    assert res.graph_state == "fresh"
    assert res.dependencies_state == "fresh"
    assert res.blast_radius_state == "fresh"
    assert res.artifact_consumption_state == "fresh"
    assert res.affected_modules != []


def test_freshness_scenario_d_requires_resync(tmp_path):
    """
    requires_resync:
    Invalidated families do NOT falsely preserve old 'fresh' status.
    Must clearly report 'stale' / 'deferred'.
    """
    engine = _create_engine(tmp_path)
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    engine.update_file(str(f_target))

    resync_plan = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("module_usages",),
        graph_recomputations=(),
        refresh_completeness="requires_resync",
        reason="Resync required for structural change",
    )

    with patch.object(RefreshPlanner, "plan_refresh", return_value=resync_plan):
        f_target.write_text("def foo(): pass\ndef new_func(): pass\n", encoding="utf-8")
        res = engine.update_file(str(f_target))

        assert res.graph_state == "stale"
        assert res.dependencies_state == "stale"
        assert res.artifact_consumption_state == "stale"
        assert res.blast_radius_state == "deferred"
        assert res.shadow_plan.refresh_completeness == "requires_resync"
