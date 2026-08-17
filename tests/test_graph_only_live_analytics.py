"""
tests/test_graph_only_live_analytics.py

Stage 3D.2 — GRAPH_ONLY Advanced Analytics LIVE Integration Tests.
Proves canonical topology analytics family, production parity, zero I/O,
plan-vs-execution exactness, snapshot compatibility, and freshness preservation.
"""

from pathlib import Path
from unittest.mock import patch
import copy
import pytest

from contextor.core.analysis.incremental_engine import (
    IncrementalAnalysisEngine,
    IncrementalUpdateResult,
)
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    FileStateManager,
    FileDelta,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.live_state.store import save_snapshot, load_snapshot
from contextor.core.reporting_engine.graph_analytics import (
    compute_topology_analytics,
    _compute_pagerank,
    _compute_betweenness,
    _compute_hub_authority,
    _compute_bridge_score,
)
from contextor.core.hotspots.engine import detect_hotspots
from contextor.core.reporting_engine.risk_signals import (
    _compute_module_risk,
    _compute_inspection_targets,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


from contextor.core.domain.imports import ImportRef


class LegacyStateForSnapshotTest:
    def __init__(self):
        self.modules = {"a": Module("a", "a.py", "/a.py", [])}


def _create_fixture_engine(tmp_path: Path):
    """Initializes an IncrementalAnalysisEngine with a 3-module canonical graph."""
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = tmp_path / ".contextor" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    core_file = app_dir / "core.py"
    core_file.write_text("class Core:\n    def run(self):\n        pass\n", encoding="utf-8")

    utils_file = app_dir / "utils.py"
    utils_file.write_text("def helper():\n    pass\n", encoding="utf-8")

    main_file = app_dir / "main.py"
    main_file.write_text("import app.core\nimport app.utils\n\ndef main():\n    app.core.Core().run()\n", encoding="utf-8")

    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(cache_dir))
    state = RepositoryAnalysisState(modules={})

    engine = IncrementalAnalysisEngine(
        state,
        registry,
        state_manager,
        str(tmp_path),
    )
    engine.update_file(str(core_file))
    engine.update_file(str(utils_file))
    engine.update_file(str(main_file))
    return engine, tmp_path, app_dir




def test_topology_analytics_schema_and_initial_parity(tmp_path):
    """1. Test canonical topology analytics schema & oracle parity."""
    engine, _, _ = _create_fixture_engine(tmp_path)
    topo = engine.state.topology_analytics

    required_keys = {
        "pagerank",
        "betweenness",
        "hub_scores",
        "authority_scores",
        "bridge_scores",
        "hotspots",
        "module_risk",
        "inspection_targets",
    }
    assert set(topo.keys()) == required_keys

    # Compare with oracle
    oracle = compute_topology_analytics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
        engine.state.metrics,
    )
    assert topo == oracle


def test_case_a_body_only_preserves_topology_analytics(tmp_path):
    """2. Case A — BODY-only change does NOT recompute and preserves freshness."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)
    main_file = app_dir / "main.py"

    old_topo = copy.deepcopy(engine.state.topology_analytics)

    # Change body only (call helper instead)
    main_file.write_text("import app.core\nimport app.utils\n\ndef main():\n    app.utils.helper()\n", encoding="utf-8")

    res = engine.update_file(str(main_file))
    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" not in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" not in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"
    assert res.global_metrics_state == "deferred"

    # Topology analytics remained intact and matches fresh oracle
    assert engine.state.topology_analytics == old_topo
    oracle = compute_topology_analytics(engine.state.dependency_graph.hard_edges, engine.state.dependency_graph.soft_edges, engine.state.metrics)
    assert engine.state.topology_analytics == oracle


def test_case_b_import_add_recomputes_with_parity(tmp_path):
    """3. Case B — IMPORT ADD schedules advanced_graph_metrics and maintains parity."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)

    # Add new module app/extra.py
    extra_file = app_dir / "extra.py"
    extra_file.write_text("def extra(): pass\n", encoding="utf-8")
    engine.update_file(str(extra_file))

    # Import extra in core.py
    core_file = app_dir / "core.py"
    core_file.write_text("import app.extra\nclass Core:\n    def run(self):\n        pass\n", encoding="utf-8")

    res = engine.update_file(str(core_file))
    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"

    oracle = compute_topology_analytics(engine.state.dependency_graph.hard_edges, engine.state.dependency_graph.soft_edges, engine.state.metrics)
    assert engine.state.topology_analytics == oracle
    assert "app.extra" in engine.state.topology_analytics["pagerank"]


def test_case_c_import_remove_recomputes_with_parity(tmp_path):
    """4. Case C — IMPORT REMOVE schedules advanced_graph_metrics and maintains parity."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)
    main_file = app_dir / "main.py"

    # Remove import of app.utils
    main_file.write_text("import app.core\n\ndef main():\n    app.core.Core().run()\n", encoding="utf-8")

    res = engine.update_file(str(main_file))
    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"

    oracle = compute_topology_analytics(engine.state.dependency_graph.hard_edges, engine.state.dependency_graph.soft_edges, engine.state.metrics)
    assert engine.state.topology_analytics == oracle
    assert "app.utils" not in engine.state.dependency_graph.hard_edges["app.main"]


def test_case_d_module_add_recomputes_with_parity(tmp_path):
    """5. Case D — MODULE ADD schedules advanced_graph_metrics and maintains parity."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)

    new_file = app_dir / "new_mod.py"
    new_file.write_text("import app.core\ndef func(): pass\n", encoding="utf-8")

    res = engine.update_file(str(new_file))
    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"

    assert "app.new_mod" in engine.state.topology_analytics["pagerank"]
    oracle = compute_topology_analytics(engine.state.dependency_graph.hard_edges, engine.state.dependency_graph.soft_edges, engine.state.metrics)
    assert engine.state.topology_analytics == oracle


def test_case_e_module_delete_removes_stale_entries(tmp_path):
    """6. Case E — MODULE DELETE removes all entries for deleted module."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)
    utils_file = app_dir / "utils.py"

    # Delete utils.py
    utils_file.unlink()
    res = engine.update_file(str(utils_file))
    assert res.status == "DELETED"
    assert "advanced_graph_metrics" in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"

    # Verify app.utils is completely absent from all topology dicts
    topo = engine.state.topology_analytics
    assert "app.utils" not in topo["pagerank"]
    assert "app.utils" not in topo["betweenness"]
    assert "app.utils" not in topo["hub_scores"]
    assert "app.utils" not in topo["authority_scores"]
    assert "app.utils" not in topo["bridge_scores"]
    assert "app.utils" not in topo["module_risk"]
    assert not any(h["module"] == "app.utils" for h in topo["hotspots"])
    assert not any(t["module"] == "app.utils" for t in topo["inspection_targets"])

    oracle = compute_topology_analytics(engine.state.dependency_graph.hard_edges, engine.state.dependency_graph.soft_edges, engine.state.metrics)
    assert topo == oracle


def test_case_f_noop_preserves_freshness_and_state(tmp_path):
    """7. Case F — NO-OP preserves topology_analytics without freshness downgrade."""
    engine, _, app_dir = _create_fixture_engine(tmp_path)
    main_file = app_dir / "main.py"

    old_topo = copy.deepcopy(engine.state.topology_analytics)

    # UNCHANGED on mtime
    res1 = engine.update_file(str(main_file))
    assert res1.status == "UNCHANGED"
    assert res1.topology_metrics_state == "fresh"
    assert engine.state.topology_analytics == old_topo

    # Rewrite identical text
    main_file.write_text(main_file.read_text(encoding="utf-8"), encoding="utf-8")
    res2 = engine.update_file(str(main_file))
    assert res2.status == "UNCHANGED"
    assert res2.topology_metrics_state == "fresh"
    assert engine.state.topology_analytics == old_topo


def test_zero_source_reads_during_advanced_graph_metrics_execution(tmp_path):
    """8. Prove zero disk I/O occurs during advanced_graph_metrics execution."""
    hard_edges = {"a": {"b", "c"}, "b": {"c"}, "c": {"a"}}
    soft_edges = {"a": set(), "b": set(), "c": set()}
    metrics = compute_graph_metrics(hard_edges, soft_edges)

    with patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_bytes", side_effect=OSError("Disk read blocked")), \
         patch("builtins.open", side_effect=OSError("Disk open blocked")):

        topo = compute_topology_analytics(hard_edges, soft_edges, metrics)
        assert len(topo["pagerank"]) == 3
        assert len(topo["betweenness"]) == 3
        assert len(topo["hub_scores"]) == 3
        assert len(topo["authority_scores"]) == 3
        assert len(topo["bridge_scores"]) == 3


def test_determinism_on_identical_graph():
    """9. Prove deterministic results across multiple runs on identical graph."""
    hard_edges = {f"mod_{i}": {f"mod_{(i+1)%10}", f"mod_{(i+3)%10}"} for i in range(10)}
    soft_edges = {f"mod_{i}": set() for i in range(10)}
    metrics = compute_graph_metrics(hard_edges, soft_edges)

    run1 = compute_topology_analytics(hard_edges, soft_edges, metrics)
    run2 = compute_topology_analytics(hard_edges, soft_edges, metrics)

    assert run1 == run2


def test_snapshot_backward_and_forward_compatibility(tmp_path):
    """10. Test snapshot backward & forward roundtrip with topology_analytics."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. State WITH topology_analytics
    state = RepositoryAnalysisState(
        modules={"a": Module("a", "a.py", "/a.py", [])},
        topology_analytics={"pagerank": {"a": 1.0}},
    )
    meta = save_snapshot(state, cache_dir, "test_state", repo_id="repo1", root_path=str(tmp_path))
    loaded_state, loaded_meta = load_snapshot(cache_dir, expected_state_id="test_state")

    assert loaded_state is not None
    assert hasattr(loaded_state, "topology_analytics")
    assert loaded_state.topology_analytics == {"pagerank": {"a": 1.0}}

    # 2. Emulate legacy state WITHOUT topology_analytics attribute
    save_snapshot(LegacyStateForSnapshotTest(), cache_dir, "legacy_state", repo_id="repo1", root_path=str(tmp_path))
    legacy_loaded, _ = load_snapshot(cache_dir, expected_state_id="legacy_state")
    assert legacy_loaded is not None
    assert hasattr(legacy_loaded, "topology_analytics")
    assert legacy_loaded.topology_analytics == {}

