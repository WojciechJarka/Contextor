"""
tests/test_topology_bootstrap_and_consumer_truth.py

Stage 3D.2a — Topology Analytics Bootstrap, Restart & Consumer Truth Proof.
Proves bootstrap materialization, clean-start oracle parity, snapshot restart,
pure-RAM reconstruction, get_module_context live projection, and restart preservation.
"""

from pathlib import Path
from unittest.mock import patch
import copy
import json
import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    FileStateManager,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.live_state.store import save_snapshot, load_snapshot
from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp_server import get_module_context
from contextor.mcp.runtime import _live_engines



class LegacySnapshotState:
    """State fixture representing an old snapshot lacking topology_analytics."""
    def __init__(self, modules, graph, metrics):
        self.modules = modules
        self.dependency_graph = graph
        self.metrics = metrics
        self.artifacts = {}
        self.artifact_consumption = {}
        self.module_usages = {}


def _create_sample_repo(tmp_path: Path):
    """Creates a sample 3-module repository on disk."""
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    core_file = app_dir / "core.py"
    core_file.write_text("class Core:\n    def run(self):\n        pass\n", encoding="utf-8")

    utils_file = app_dir / "utils.py"
    utils_file.write_text("def helper():\n    pass\n", encoding="utf-8")

    main_file = app_dir / "main.py"
    main_file.write_text("import app.core\nimport app.utils\n\ndef main():\n    app.core.Core().run()\n", encoding="utf-8")

    return core_file, utils_file, main_file


def test_clean_start_engine_init_parity(tmp_path):
    """1. Clean-start engine initialization materializes topology_analytics with zero source reads."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / ".contextor" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.core": Module(module_id="app.core", path="app/core.py", absolute_path=str(core_file), imports=[]),
        "app.utils": Module(module_id="app.utils", path="app/utils.py", absolute_path=str(utils_file), imports=[]),
        "app.main": Module(
            module_id="app.main",
            path="app/main.py",
            absolute_path=str(main_file),
            imports=[
                ImportRef(module="app.core", level=0, names=[], is_from_import=False),
                ImportRef(module="app.utils", level=0, names=[], is_from_import=False),
            ],
        ),
    }

    hard_edges = {
        "app.main": {"app.core", "app.utils"},
        "app.core": set(),
        "app.utils": set(),
    }
    soft_edges = {"app.main": set(), "app.core": set(), "app.utils": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)

    # State initially has topology_analytics as empty dict
    state = RepositoryAnalysisState(
        modules=modules,
        dependency_graph=graph,
        metrics=metrics,
        topology_analytics={},
    )

    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(cache_dir))

    # Zero disk reads during materialization
    with patch("builtins.open", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")):
        engine = IncrementalAnalysisEngine(
            state,
            registry,
            state_manager,
            str(tmp_path),
        )

    # Verified: topology_analytics is now fully materialized
    assert bool(engine.state.topology_analytics) is True
    oracle = compute_topology_analytics(hard_edges, soft_edges, metrics)

    # Full parity for all 7 signal families
    assert engine.state.topology_analytics["pagerank"] == oracle["pagerank"]
    assert engine.state.topology_analytics["betweenness"] == oracle["betweenness"]
    assert engine.state.topology_analytics["hub_scores"] == oracle["hub_scores"]
    assert engine.state.topology_analytics["authority_scores"] == oracle["authority_scores"]
    assert engine.state.topology_analytics["bridge_scores"] == oracle["bridge_scores"]
    assert engine.state.topology_analytics["hotspots"] == oracle["hotspots"]
    assert engine.state.topology_analytics["module_risk"] == oracle["module_risk"]
    assert engine.state.topology_analytics["inspection_targets"] == oracle["inspection_targets"]


def test_old_snapshot_reload_and_reconstruction(tmp_path):
    """2. An old snapshot without topology_analytics field reconstructs cleanly without disk I/O."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.core": Module(module_id="app.core", path="app/core.py", absolute_path=str(core_file), imports=[]),
        "app.utils": Module(module_id="app.utils", path="app/utils.py", absolute_path=str(utils_file), imports=[]),
        "app.main": Module(
            module_id="app.main",
            path="app/main.py",
            absolute_path=str(main_file),
            imports=[
                ImportRef(module="app.core", level=0, names=[], is_from_import=False),
                ImportRef(module="app.utils", level=0, names=[], is_from_import=False),
            ],
        ),
    }
    hard_edges = {"app.main": {"app.core", "app.utils"}, "app.core": set(), "app.utils": set()}
    soft_edges = {"app.main": set(), "app.core": set(), "app.utils": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)

    # Save legacy snapshot
    legacy_state = LegacySnapshotState(modules, graph, metrics)
    save_snapshot(legacy_state, cache_dir, "legacy_snap", repo_id="repo1", root_path=str(tmp_path))

    # Load legacy snapshot
    loaded_state, meta = load_snapshot(cache_dir, expected_state_id="legacy_snap")
    assert loaded_state is not None
    assert hasattr(loaded_state, "topology_analytics")
    assert loaded_state.topology_analytics == {}

    # Initialize engine on loaded state with disk reads blocked
    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(cache_dir))

    with patch("builtins.open", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")):
        engine = IncrementalAnalysisEngine(
            loaded_state,
            registry,
            state_manager,
            str(tmp_path),
        )

    # Reconstructed topology matches oracle
    oracle = compute_topology_analytics(hard_edges, soft_edges, metrics)
    assert engine.state.topology_analytics == oracle


def test_new_snapshot_save_and_restart(tmp_path):
    """3. New snapshot preserves topology_analytics across save and reload."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.core": Module(module_id="app.core", path="app/core.py", absolute_path=str(core_file), imports=[]),
        "app.utils": Module(module_id="app.utils", path="app/utils.py", absolute_path=str(utils_file), imports=[]),
    }
    hard_edges = {"app.core": set(), "app.utils": set()}
    soft_edges = {"app.core": set(), "app.utils": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)
    topo = compute_topology_analytics(hard_edges, soft_edges, metrics)

    state = RepositoryAnalysisState(
        modules=modules,
        dependency_graph=graph,
        metrics=metrics,
        topology_analytics=topo,
    )

    save_snapshot(state, cache_dir, "new_snap", repo_id="repo1", root_path=str(tmp_path))

    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="new_snap")
    assert loaded_state.topology_analytics == topo

    engine = IncrementalAnalysisEngine(
        loaded_state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    assert engine.state.topology_analytics == topo


def test_consumer_get_module_context_live_projection(tmp_path):
    """4. get_module_context reads live canonical topology_analytics with exact oracle parity."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / ".contextor" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

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

    # Register engine in MCP active engines for repo
    root_resolved = Path(tmp_path).expanduser().resolve()
    _live_engines[str(root_resolved)] = engine


    # Call get_module_context
    fn = getattr(get_module_context, "fn", get_module_context)
    res_raw = fn(str(tmp_path), "app.main", compact=True)
    res = json.loads(res_raw)


    assert res["module"] == "app.main"
    assert res["metrics_source"] == "live_canonical_topology"
    assert res["degree_metrics_source"] == "live_canonical_graph"

    topo = engine.state.topology_analytics
    assert res["metrics"]["pagerank"] == topo["pagerank"]["app.main"]
    assert res["metrics"]["betweenness"] == topo["betweenness"]["app.main"]
    assert res["metrics"]["hub_score"] == topo["hub_scores"]["app.main"]
    assert res["metrics"]["authority_score"] == topo["authority_scores"]["app.main"]
    assert res["metrics"]["bridge_score"] == topo["bridge_scores"]["app.main"]
    assert res["metrics"]["risk_score"] == topo["module_risk"]["app.main"]


def test_body_only_change_after_restart(tmp_path):
    """5. BODY-only change after restart preserves freshness without scheduling advanced_graph_metrics."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initial engine population
    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(cache_dir))
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        registry,
        state_manager,
        str(tmp_path),
    )
    engine.update_file(str(core_file))
    engine.update_file(str(utils_file))
    engine.update_file(str(main_file))

    # 2. Save snapshot and restart
    save_snapshot(engine.state, cache_dir, "snap1", repo_id="repo1", root_path=str(tmp_path))
    reloaded_state, _ = load_snapshot(cache_dir, expected_state_id="snap1")
    reloaded_engine = IncrementalAnalysisEngine(
        reloaded_state,
        registry,
        state_manager,
        str(tmp_path),
    )

    old_topo = copy.deepcopy(reloaded_engine.state.topology_analytics)

    # 3. Modify BODY only
    main_file.write_text("import app.core\nimport app.utils\n\ndef main():\n    print('updated body')\n", encoding="utf-8")
    res = reloaded_engine.update_file(str(main_file))

    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" not in res.shadow_plan.graph_recomputations
    assert "advanced_graph_metrics" not in res.execution_trace["graph_recomputations"]
    assert res.topology_metrics_state == "fresh"
    assert reloaded_engine.state.topology_analytics == old_topo


def test_import_change_after_restart(tmp_path):
    """6. IMPORT change after restart triggers advanced_graph_metrics once and commits new state."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initial engine population
    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(cache_dir))
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        registry,
        state_manager,
        str(tmp_path),
    )
    engine.update_file(str(core_file))
    engine.update_file(str(utils_file))
    engine.update_file(str(main_file))

    # 2. Save snapshot and restart
    save_snapshot(engine.state, cache_dir, "snap1", repo_id="repo1", root_path=str(tmp_path))
    reloaded_state, _ = load_snapshot(cache_dir, expected_state_id="snap1")
    reloaded_engine = IncrementalAnalysisEngine(
        reloaded_state,
        registry,
        state_manager,
        str(tmp_path),
    )

    # 3. Add extra module and import it
    extra_file = tmp_path / "app" / "extra.py"
    extra_file.write_text("def extra(): pass\n", encoding="utf-8")
    reloaded_engine.update_file(str(extra_file))

    core_file.write_text("import app.extra\nclass Core:\n    def run(self):\n        pass\n", encoding="utf-8")
    res = reloaded_engine.update_file(str(core_file))

    assert res.status == "UPDATED"
    assert "advanced_graph_metrics" in res.shadow_plan.graph_recomputations
    assert res.topology_metrics_state == "fresh"
    assert "app.extra" in reloaded_engine.state.topology_analytics["pagerank"]


def test_ensure_topology_analytics_lifecycle_invariants():
    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics

    # 1. Fresh + populated: zero recomputation
    dep_graph = ProjectGraph(hard_edges={"a": {"b"}, "b": set()}, soft_edges={})
    state_fresh = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={"pagerank": {"a": 0.5, "b": 1.0}},
        topology_metrics_state="fresh",
    )
    old_dict = state_fresh.topology_analytics
    ensure_topology_analytics(state_fresh)
    assert state_fresh.topology_metrics_state == "fresh"
    assert state_fresh.topology_analytics is old_dict

    # 2. Legacy deferred + valid graph: recomputes in RAM to fresh
    state_deferred = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={"old": "data"},
        topology_metrics_state="deferred",
    )
    ensure_topology_analytics(state_deferred)
    assert state_deferred.topology_metrics_state == "fresh"
    assert "pagerank" in state_deferred.topology_analytics
    assert "a" in state_deferred.topology_analytics["pagerank"]

    # 3. Stale state: untrusted graph -> preserved as stale (NO auto-heal)
    state_stale = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={"old": "data"},
        topology_metrics_state="stale",
    )
    ensure_topology_analytics(state_stale)
    assert state_stale.topology_metrics_state == "stale"
    assert state_stale.topology_analytics == {"old": "data"}

    # 4. Missing/empty analytics + valid graph -> recomputes to fresh
    state_empty = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={},
        topology_metrics_state="deferred",
    )
    ensure_topology_analytics(state_empty)
    assert state_empty.topology_metrics_state == "fresh"
    assert "pagerank" in state_empty.topology_analytics

    # 5. Atomic failure handling: exception during compute preserves previous analytics and sets non-fresh
    state_fail = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={"prev": "safe"},
        topology_metrics_state="deferred",
    )
    with patch("contextor.core.reporting_engine.graph_analytics.compute_topology_analytics", side_effect=RuntimeError("Topology error")):
        ensure_topology_analytics(state_fail)
    assert state_fail.topology_metrics_state == "deferred"
    assert state_fail.topology_analytics == {"prev": "safe"}

    # Inconsistent fresh with empty analytics transitioning to deferred on failure
    state_fail_fresh = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_analytics={},
        topology_metrics_state="fresh",
    )
    with patch("contextor.core.reporting_engine.graph_analytics.compute_topology_analytics", side_effect=RuntimeError("Topology error")):
        ensure_topology_analytics(state_fail_fresh)
    assert state_fail_fresh.topology_metrics_state == "deferred"
    assert state_fail_fresh.topology_analytics == {}

    # 6. Cached analytics state remains completely untouched
    state_cached = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=dep_graph,
        topology_metrics_state="deferred",
        cached_analytics_state="deferred",
    )
    ensure_topology_analytics(state_cached)
    assert state_cached.topology_metrics_state == "fresh"
    assert state_cached.cached_analytics_state == "deferred"  # untouched!
