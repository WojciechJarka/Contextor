"""
tests/test_cycles_live_lifecycle.py

Canonical LIVE lifecycle tests for cycle detection without full repository source scanning.
Verifies bootstrap, legacy hydration, restart preservation, freshness states, incremental triggers,
atomic failure handling, and exact snapshot-vs-live parity across all topological edge cases.
"""

from pathlib import Path
from unittest.mock import patch
import copy
import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    FileStateManager,
    FileDelta,
)
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.incremental.materialization import ensure_cycles
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.graph.cycles import detect_cycles
from contextor.core.live_state.store import save_snapshot, load_snapshot
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


class LegacySnapshotStateWithoutCycles:
    """Fixture simulating an older snapshot lacking cycles and cycles_state fields."""
    def __init__(self, modules, graph, metrics):
        self.modules = modules
        self.dependency_graph = graph
        self.metrics = metrics
        self.artifacts = {}
        self.artifact_consumption = {}
        self.module_usages = {}
        self.topology_analytics = {}
        self.cached_analytics = {}


def _create_cyclic_repo(tmp_path: Path):
    """Creates a sample repository on disk with modules a, b, c."""
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    a_file = app_dir / "a.py"
    a_file.write_text("import app.b\ndef fa(): pass\n", encoding="utf-8")

    b_file = app_dir / "b.py"
    b_file.write_text("import app.c\ndef fb(): pass\n", encoding="utf-8")

    c_file = app_dir / "c.py"
    c_file.write_text("import app.a\ndef fc(): pass\n", encoding="utf-8")

    return a_file, b_file, c_file


# ==========================================================
# 1. BOOTSTRAP & ENSURE_CYCLES LIFECYCLE INVARIANTS
# ==========================================================

def test_bootstrap_cycles_fresh_populated():
    """Bootstrap with detected cycles gives fresh state and preserves result."""
    hard_edges = {"a": {"b"}, "b": {"a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})
    expected = detect_cycles(hard_edges)

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        cycles=expected,
        cycles_state="fresh",
    )
    old_list = state.cycles
    ensure_cycles(state)
    assert state.cycles_state == "fresh"
    assert state.cycles is old_list
    assert state.cycles == [["a", "b", "a"]]


def test_bootstrap_zero_cycles_fresh_empty():
    """Bootstrap with acyclic graph gives [] + fresh and is NOT treated as missing/deferred."""
    hard_edges = {"a": {"b"}, "b": set()}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        cycles=[],
        cycles_state="fresh",
    )
    old_list = state.cycles
    ensure_cycles(state)
    assert state.cycles_state == "fresh"
    assert state.cycles is old_list
    assert state.cycles == []


def test_ensure_cycles_deferred_recomputes_in_ram():
    """Deferred cycles with valid graph recomputes in RAM to fresh."""
    hard_edges = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}, "c": {}},
        dependency_graph=graph,
        cycles=[],
        cycles_state="deferred",
    )
    ensure_cycles(state)
    assert state.cycles_state == "fresh"
    assert state.cycles == [["a", "b", "c", "a"]]


def test_ensure_cycles_stale_remains_stale():
    """Stale state representing untrusted graph is NOT auto-healed."""
    hard_edges = {"a": {"b"}, "b": {"a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        cycles=[["a", "b", "a"]],
        cycles_state="stale",
    )
    ensure_cycles(state)
    assert state.cycles_state == "stale"
    assert state.cycles == [["a", "b", "a"]]


def test_ensure_cycles_atomic_failure_handling():
    """Failure during cycle computation preserves existing cycles and marks deferred (not fresh)."""
    hard_edges = {"a": {"b"}, "b": {"a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        cycles=[["old", "cycle"]],
        cycles_state="deferred",
    )
    with patch("contextor.core.graph.cycles.detect_cycles", side_effect=RuntimeError("Cycle compute error")):
        ensure_cycles(state)
    assert state.cycles_state == "deferred"
    assert state.cycles == [["old", "cycle"]]


def test_cycles_lifecycle_isolation_from_topology_and_cached_analytics():
    """ensure_cycles does not mutate topology_metrics_state or cached_analytics_state."""
    hard_edges = {"a": {"b"}, "b": {"a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        topology_metrics_state="deferred",
        cached_analytics_state="deferred",
        cycles_state="deferred",
    )
    ensure_cycles(state)
    assert state.cycles_state == "fresh"
    assert state.topology_metrics_state == "deferred"  # unchanged
    assert state.cached_analytics_state == "deferred"  # unchanged


# ==========================================================
# 2. PERSISTENCE, HYDRATION & RESTART
# ==========================================================

def test_legacy_snapshot_hydration_recomputes_cycles_in_ram(tmp_path):
    """Legacy snapshot without cycles/cycles_state hydraizes and computes fresh cycles with 0 disk reads."""
    a_file, b_file, c_file = _create_cyclic_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.a": Module(module_id="app.a", path="app/a.py", absolute_path=str(a_file), imports=[ImportRef("app.b", 0, [], False)]),
        "app.b": Module(module_id="app.b", path="app/b.py", absolute_path=str(b_file), imports=[ImportRef("app.c", 0, [], False)]),
        "app.c": Module(module_id="app.c", path="app/c.py", absolute_path=str(c_file), imports=[ImportRef("app.a", 0, [], False)]),
    }
    hard_edges = {"app.a": {"app.b"}, "app.b": {"app.c"}, "app.c": {"app.a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})
    legacy_state = LegacySnapshotStateWithoutCycles(modules, graph, metrics={})

    save_snapshot(legacy_state, cache_dir, "legacy_snap", repo_id="repo1", root_path=str(tmp_path))

    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="legacy_snap")
    assert loaded_state is not None
    assert hasattr(loaded_state, "cycles")
    assert hasattr(loaded_state, "cycles_state")
    assert loaded_state.cycles_state == "deferred"

    with patch("builtins.open", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")):
        engine = IncrementalAnalysisEngine(
            loaded_state,
            PersistentIdentityRegistry(str(tmp_path)),
            FileStateManager(str(cache_dir)),
            str(tmp_path),
        )

    assert engine.state.cycles_state == "fresh"
    assert engine.state.cycles == [["app.a", "app.b", "app.c", "app.a"]]


def test_persisted_fresh_cycles_preserved_across_restart(tmp_path):
    """Fresh cycles are persisted to snapshot and preserved on restart with zero recomputation."""
    a_file, b_file, c_file = _create_cyclic_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    modules = {
        "app.a": Module(module_id="app.a", path="app/a.py", absolute_path=str(a_file), imports=[ImportRef("app.b", 0, [], False)]),
        "app.b": Module(module_id="app.b", path="app/b.py", absolute_path=str(b_file), imports=[ImportRef("app.c", 0, [], False)]),
    }
    hard_edges = {"app.a": {"app.b"}, "app.b": {"app.a"}}
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})
    cycles_expected = [["app.a", "app.b", "app.a"]]

    state = RepositoryAnalysisState(
        modules=modules,
        dependency_graph=graph,
        cycles=cycles_expected,
        cycles_state="fresh",
    )
    save_snapshot(state, cache_dir, "fresh_snap", repo_id="repo1", root_path=str(tmp_path))

    loaded_state, _ = load_snapshot(cache_dir, expected_state_id="fresh_snap")
    assert loaded_state.cycles_state == "fresh"
    assert loaded_state.cycles == cycles_expected

    with patch("contextor.core.graph.cycles.detect_cycles", side_effect=AssertionError("detect_cycles should not be called on fresh state")):
        engine = IncrementalAnalysisEngine(
            loaded_state,
            PersistentIdentityRegistry(str(tmp_path)),
            FileStateManager(str(cache_dir)),
            str(tmp_path),
        )

    assert engine.state.cycles_state == "fresh"
    assert engine.state.cycles == cycles_expected


# ==========================================================
# 3. INCREMENTAL TRIGGERS & PLAN VS EXECUTION
# ==========================================================

def test_body_only_change_preserves_fresh_cycles_without_recompute(tmp_path):
    """Body-only modification does not schedule cycles recomputation and keeps cycles fresh."""
    a_file, b_file, c_file = _create_cyclic_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(a_file))
    engine.update_file(str(b_file))
    engine.update_file(str(c_file))

    assert engine.state.cycles_state == "fresh"
    assert len(engine.state.cycles) == 1
    old_cycles = list(engine.state.cycles)

    # Change only the body of a.py
    a_file.write_text("import app.b\ndef fa():\n    print('updated body')\n", encoding="utf-8")
    res = engine.update_file(str(a_file))

    assert res.status == "UPDATED"
    assert "cycles" not in res.shadow_plan.graph_recomputations
    assert "cycles" not in res.execution_trace["graph_recomputations"]
    assert res.cycles_state == "fresh"
    assert engine.state.cycles == old_cycles


def test_import_add_creates_cycle(tmp_path):
    """Adding an import that completes a cycle recomputes cycles and transitions state."""
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    a_file = app_dir / "a.py"
    a_file.write_text("import app.b\ndef fa(): pass\n", encoding="utf-8")

    b_file = app_dir / "b.py"
    b_file.write_text("def fb(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(a_file))
    engine.update_file(str(b_file))

    assert engine.state.cycles == []
    assert engine.state.cycles_state == "fresh"

    # Add import app.a to b.py -> creates cycle a <-> b
    b_file.write_text("import app.a\ndef fb(): pass\n", encoding="utf-8")
    res = engine.update_file(str(b_file))

    assert res.status == "UPDATED"
    assert "cycles" in res.shadow_plan.graph_recomputations
    assert "cycles" in res.execution_trace["graph_recomputations"]
    assert res.cycles_state == "fresh"
    assert engine.state.cycles == [["app.a", "app.b", "app.a"]]


def test_import_remove_breaks_cycle(tmp_path):
    """Removing an import that forms a cycle recomputes cycles and sets [] + fresh."""
    a_file, b_file, c_file = _create_cyclic_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(a_file))
    engine.update_file(str(b_file))
    engine.update_file(str(c_file))

    assert len(engine.state.cycles) == 1

    # Remove import from c.py -> breaks cycle
    c_file.write_text("def fc(): pass\n", encoding="utf-8")
    res = engine.update_file(str(c_file))

    assert res.status == "UPDATED"
    assert "cycles" in res.shadow_plan.graph_recomputations
    assert "cycles" in res.execution_trace["graph_recomputations"]
    assert res.cycles_state == "fresh"
    assert engine.state.cycles == []


def test_module_delete_removes_cycle(tmp_path):
    """Deleting a module in a cycle recomputes cycles and updates canonical state."""
    a_file, b_file, c_file = _create_cyclic_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(a_file))
    engine.update_file(str(b_file))
    engine.update_file(str(c_file))

    assert len(engine.state.cycles) == 1

    # Delete c.py
    c_file.unlink()
    res = engine.update_file(str(c_file))

    assert res.status == "DELETED"
    assert "cycles" in res.shadow_plan.graph_recomputations
    assert "cycles" in res.execution_trace["graph_recomputations"]
    assert res.cycles_state == "fresh"
    assert engine.state.cycles == []


# ==========================================================
# 4. SNAPSHOT VS LIVE TOPOLOGICAL PARITY
# ==========================================================

@pytest.mark.parametrize(
    "graph_structure, expected_cycles",
    [
        # 1. Zero cycles
        (
            {"a": {"b"}, "b": {"c"}, "c": set()},
            [],
        ),
        # 2. A -> B -> A
        (
            {"a": {"b"}, "b": {"a"}},
            [["a", "b", "a"]],
        ),
        # 3. A -> B -> C -> A
        (
            {"a": {"b"}, "b": {"c"}, "c": {"a"}},
            [["a", "b", "c", "a"]],
        ),
        # 4. Self-loop
        (
            {"a": {"a"}},
            [["a", "a"]],
        ),
        # 5. Multiple independent cycles
        (
            {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}},
            [["a", "b", "a"], ["x", "y", "x"]],
        ),
        # 6. Overlapping cycles
        (
            {"a": {"b"}, "b": {"c", "d"}, "c": {"a"}, "d": {"a"}},
            [["a", "b", "c", "a"], ["a", "b", "d", "a"]],
        ),
        # 7. Duplicate rotations normalize to one canonical cycle
        (
            {"b": {"c"}, "c": {"a"}, "a": {"b"}},
            [["a", "b", "c", "a"]],
        ),
    ]
)
def test_snapshot_live_topological_parity(tmp_path, graph_structure, expected_cycles):
    """Proves exact parity between offline detect_cycles oracle and LIVE canonical cycle state."""
    # Offline snapshot oracle
    oracle_cycles = detect_cycles(graph_structure)
    assert oracle_cycles == expected_cycles

    # LIVE canonical state materialization
    graph = ProjectGraph(hard_edges=graph_structure, soft_edges={})
    state = RepositoryAnalysisState(
        modules={m: {} for m in graph_structure},
        dependency_graph=graph,
        cycles=[],
        cycles_state="deferred",
    )
    ensure_cycles(state)

    assert state.cycles_state == "fresh"
    assert state.cycles == oracle_cycles


def test_soft_edges_ignored_for_cycles():
    """Proves that soft dependencies are ignored and only hard_edges define cycle boundaries."""
    hard_edges = {"a": {"b"}, "b": set()}
    soft_edges = {"b": {"a"}}  # Soft back-edge does NOT make a cycle
    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)

    state = RepositoryAnalysisState(
        modules={"a": {}, "b": {}},
        dependency_graph=graph,
        cycles=[],
        cycles_state="deferred",
    )
    ensure_cycles(state)

    assert state.cycles_state == "fresh"
    assert state.cycles == []
