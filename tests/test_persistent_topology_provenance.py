"""
tests/test_persistent_topology_provenance.py

Stage 3D.2b — Persistent Topology Freshness Provenance Tests.
Proves persistent provenance across snapshot save/reload, stale non-empty guard,
fresh snapshot preservation, legacy snapshot reconstruction, and consumer guard.
"""

from pathlib import Path
from unittest.mock import patch
import copy
import json
import pytest

from contextor.core.analysis.incremental_engine import (
    IncrementalAnalysisEngine,
    IncrementalUpdateResult,
)
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    FileStateManager,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.imports import ImportRef
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.live_state.store import save_snapshot, load_snapshot
from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp_server import get_module_context
from contextor.mcp.runtime import _live_engines


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


def test_stale_non_empty_snapshot_restart_and_consumer_guard(tmp_path):
    """1. Stale non-empty topology analytics retains stale provenance and blocks live projection."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.core": Module("app.core", "app/core.py", str(core_file), []),
        "app.utils": Module("app.utils", "app/utils.py", str(utils_file), []),
        "app.main": Module("app.main", "app/main.py", str(main_file), [
            ImportRef("app.core", 0, [], False),
            ImportRef("app.utils", 0, [], False),
        ]),
    }
    hard_edges = {"app.main": {"app.core", "app.utils"}, "app.core": set(), "app.utils": set()}
    soft_edges = {"app.main": set(), "app.core": set(), "app.utils": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)
    topo = compute_topology_analytics(hard_edges, soft_edges, metrics)

    # State has non-empty topology analytics, but is explicitly marked STALE
    state = RepositoryAnalysisState(
        modules=modules,
        dependency_graph=graph,
        metrics=metrics,
        topology_analytics=topo,
        topology_metrics_state="stale",
    )

    save_snapshot(state, cache_dir, "stale_snap", repo_id="repo1", root_path=str(tmp_path))

    # Reload snapshot
    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="stale_snap")
    assert loaded_state.topology_metrics_state == "stale"
    assert loaded_state.topology_analytics == topo

    engine = IncrementalAnalysisEngine(
        loaded_state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    # Engine must NOT falsely mark fresh merely because topology_analytics is non-empty
    assert engine.state.topology_metrics_state == "stale"

    # Register in MCP and call get_module_context
    root_resolved = Path(tmp_path).expanduser().resolve()
    _live_engines[str(root_resolved)] = engine

    fn = getattr(get_module_context, "fn", get_module_context)
    res_raw = fn(str(tmp_path), "app.main", compact=True)
    res = json.loads(res_raw)

    # Consumer guard: must NOT claim live_canonical_graph when stale
    assert res["metrics_source"] != "live_canonical_graph"


def test_fresh_snapshot_restart_preservation(tmp_path):
    """2. Fresh snapshot preserves fresh provenance and enables live projection without recompute."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.core": Module("app.core", "app/core.py", str(core_file), []),
        "app.main": Module("app.main", "app/main.py", str(main_file), [ImportRef("app.core", 0, [], False)]),
    }
    hard_edges = {"app.main": {"app.core"}, "app.core": set()}
    soft_edges = {"app.main": set(), "app.core": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)
    topo = compute_topology_analytics(hard_edges, soft_edges, metrics)

    state = RepositoryAnalysisState(
        modules=modules,
        dependency_graph=graph,
        metrics=metrics,
        topology_analytics=topo,
        topology_metrics_state="fresh",
    )

    save_snapshot(state, cache_dir, "fresh_snap", repo_id="repo1", root_path=str(tmp_path))

    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="fresh_snap")
    assert loaded_state.topology_metrics_state == "fresh"

    engine = IncrementalAnalysisEngine(
        loaded_state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    assert engine.state.topology_metrics_state == "fresh"
    assert engine.state.topology_analytics == topo

    root_resolved = Path(tmp_path).expanduser().resolve()
    _live_engines[str(root_resolved)] = engine

    fn = getattr(get_module_context, "fn", get_module_context)
    res_raw = fn(str(tmp_path), "app.main", compact=True)
    res = json.loads(res_raw)
    assert res["metrics_source"] == "live_canonical_topology"
    assert res["metrics"]["pagerank"] == topo["pagerank"]["app.main"]


class LegacyStateObj:
    def __init__(self, core_file):
        self.modules = {"app.core": Module("app.core", "app/core.py", str(core_file), [])}
        self.dependency_graph = ProjectGraph({"app.core": set()}, {"app.core": set()})
        self.metrics = compute_graph_metrics({"app.core": set()}, {"app.core": set()})


def test_legacy_snapshot_reconstruction_with_provenance(tmp_path):
    """3. Legacy snapshot lacking topology fields initializes deferred and reconstructs cleanly."""
    core_file, utils_file, _ = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    save_snapshot(LegacyStateObj(core_file), cache_dir, "leg_snap", repo_id="repo1", root_path=str(tmp_path))


    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="leg_snap")
    assert hasattr(loaded_state, "topology_metrics_state")
    assert loaded_state.topology_metrics_state == "deferred"

    with patch("builtins.open", side_effect=OSError("Disk read blocked")):
        engine = IncrementalAnalysisEngine(
            loaded_state,
            PersistentIdentityRegistry(str(tmp_path)),
            FileStateManager(str(cache_dir)),
            str(tmp_path),
        )

    # Reconstructed to fresh with zero disk reads
    assert engine.state.topology_metrics_state == "fresh"
    assert "app.core" in engine.state.topology_analytics["pagerank"]


def test_body_only_preserves_stale_or_fresh_provenance(tmp_path):
    """4. BODY-only changes preserve existing provenance (fresh remains fresh, stale remains stale)."""
    core_file, utils_file, main_file = _create_sample_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(core_file))
    engine.update_file(str(utils_file))
    engine.update_file(str(main_file))

    assert engine.state.topology_metrics_state == "fresh"

    # Modify body
    main_file.write_text("import app.core\nimport app.utils\n\ndef main(): pass\n", encoding="utf-8")
    res1 = engine.update_file(str(main_file))
    assert res1.topology_metrics_state == "fresh"
    assert engine.state.topology_metrics_state == "fresh"

    # Artificially set stale
    engine.state.topology_metrics_state = "stale"
    main_file.write_text("import app.core\nimport app.utils\n\ndef main():\n    print(1)\n", encoding="utf-8")
    res2 = engine.update_file(str(main_file))
    assert res2.topology_metrics_state == "stale"
    assert engine.state.topology_metrics_state == "stale"
