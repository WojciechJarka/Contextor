import json
import pytest
from pathlib import Path

from contextor.core.domain.graph import ProjectGraph
from contextor.core.analysis.incremental_engine import (
    IncrementalAnalysisEngine,
    LocalDegreeDeltaResult,
)
from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
)
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository
from contextor import mcp_server


# =========================================================================
# Pure Unit Tests for _calculate_degree_deltas (Stage 2A Primitives)
# =========================================================================

def test_modify_adds_hard_edge():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
    )

    assert result.complete is True
    assert result.fan_out_updates == {"pkg.mod_a": 1}
    assert result.fan_in_updates == {"pkg.mod_b": 1}
    assert result.added_modules == set()
    assert result.removed_modules == set()


def test_modify_removes_hard_edge():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
    )

    assert result.complete is True
    assert result.fan_out_updates == {"pkg.mod_a": 0}
    assert result.fan_in_updates == {"pkg.mod_b": 0}
    assert result.added_modules == set()
    assert result.removed_modules == set()


def test_add_resolves_existing_consumer():
    old_graph = ProjectGraph(
        hard_edges={"pkg.consumer": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.consumer": {"pkg.provider"}, "pkg.provider": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.consumer"],
        new_modules=["pkg.consumer", "pkg.provider"],
    )

    assert result.complete is True
    assert result.added_modules == {"pkg.provider"}
    assert result.removed_modules == set()
    assert result.fan_out_updates == {"pkg.consumer": 1, "pkg.provider": 0}
    assert result.fan_in_updates == {"pkg.provider": 1}


def test_add_module_with_outgoing_edge():
    old_graph = ProjectGraph(
        hard_edges={"pkg.target": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.target": set(), "pkg.new_mod": {"pkg.target"}},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.target"],
        new_modules=["pkg.target", "pkg.new_mod"],
    )

    assert result.complete is True
    assert result.added_modules == {"pkg.new_mod"}
    assert result.removed_modules == set()
    assert result.fan_out_updates == {"pkg.new_mod": 1}
    assert result.fan_in_updates == {"pkg.new_mod": 0, "pkg.target": 1}


def test_delete_consumer_edge():
    old_graph = ProjectGraph(
        hard_edges={"pkg.consumer": {"pkg.provider"}, "pkg.provider": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.consumer": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.consumer", "pkg.provider"],
        new_modules=["pkg.consumer"],
    )

    assert result.complete is True
    assert result.added_modules == set()
    assert result.removed_modules == {"pkg.provider"}
    assert result.fan_out_updates == {"pkg.consumer": 0}
    assert result.fan_in_updates == {}


def test_delete_module_that_had_outgoing_edge():
    old_graph = ProjectGraph(
        hard_edges={"pkg.provider": {"pkg.target"}, "pkg.target": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.target": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.provider", "pkg.target"],
        new_modules=["pkg.target"],
    )

    assert result.complete is True
    assert result.added_modules == set()
    assert result.removed_modules == {"pkg.provider"}
    assert result.fan_out_updates == {}
    assert result.fan_in_updates == {"pkg.target": 0}


def test_isolated_add_with_zero_degrees():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.isolated": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.mod_a"],
        new_modules=["pkg.mod_a", "pkg.isolated"],
    )

    assert result.complete is True
    assert result.added_modules == {"pkg.isolated"}
    assert result.removed_modules == set()
    assert result.fan_out_updates == {"pkg.isolated": 0}
    assert result.fan_in_updates == {"pkg.isolated": 0}
    assert "pkg.mod_a" not in result.fan_out_updates
    assert "pkg.mod_a" not in result.fan_in_updates


def test_isolated_delete_represented_as_removal():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.isolated": set()},
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.mod_a", "pkg.isolated"],
        new_modules=["pkg.mod_a"],
    )

    assert result.complete is True
    assert result.added_modules == set()
    assert result.removed_modules == {"pkg.isolated"}
    assert result.fan_out_updates == {}
    assert result.fan_in_updates == {}
    assert "pkg.mod_a" not in result.fan_out_updates
    assert "pkg.mod_a" not in result.fan_in_updates


def test_unrelated_nodes_excluded():
    old_graph = ProjectGraph(
        hard_edges={
            "pkg.mod_a": {"pkg.mod_b"},
            "pkg.mod_b": set(),
            "pkg.unrelated_src": {"pkg.unrelated_tgt"},
            "pkg.unrelated_tgt": set(),
        },
        soft_edges={},
    )
    new_graph = ProjectGraph(
        hard_edges={
            "pkg.mod_a": {"pkg.mod_b", "pkg.new_mod"},
            "pkg.mod_b": set(),
            "pkg.new_mod": set(),
            "pkg.unrelated_src": {"pkg.unrelated_tgt"},
            "pkg.unrelated_tgt": set(),
        },
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
        old_modules=["pkg.mod_a", "pkg.mod_b", "pkg.unrelated_src", "pkg.unrelated_tgt"],
        new_modules=["pkg.mod_a", "pkg.mod_b", "pkg.new_mod", "pkg.unrelated_src", "pkg.unrelated_tgt"],
    )

    assert result.complete is True
    assert "pkg.unrelated_src" not in result.fan_out_updates
    assert "pkg.unrelated_tgt" not in result.fan_in_updates
    assert "pkg.mod_b" not in result.fan_in_updates
    assert result.fan_out_updates == {"pkg.mod_a": 2, "pkg.new_mod": 0}
    assert result.fan_in_updates == {"pkg.new_mod": 1}


def test_hard_to_soft_transition_behaves_as_hard_removal():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
        soft_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
        soft_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
    )

    assert result.complete is True
    assert result.fan_out_updates == {"pkg.mod_a": 0}
    assert result.fan_in_updates == {"pkg.mod_b": 0}


def test_soft_to_hard_transition_behaves_as_hard_addition():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
        soft_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
    )
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
        soft_edges={"pkg.mod_a": set(), "pkg.mod_b": set()},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=new_graph,
    )

    assert result.complete is True
    assert result.fan_out_updates == {"pkg.mod_a": 1}
    assert result.fan_in_updates == {"pkg.mod_b": 1}


def test_missing_old_graph_marks_complete_false():
    new_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=None,
        new_graph=new_graph,
    )

    assert result.complete is False
    assert result.fan_in_updates == {}
    assert result.fan_out_updates == {}


def test_missing_new_graph_marks_complete_false():
    old_graph = ProjectGraph(
        hard_edges={"pkg.mod_a": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=old_graph,
        new_graph=None,
    )

    assert result.complete is False
    assert result.fan_in_updates == {}
    assert result.fan_out_updates == {}


def test_identical_old_new_graph_no_degree_updates():
    graph = ProjectGraph(
        hard_edges={"pkg.mod_a": {"pkg.mod_b"}, "pkg.mod_b": set()},
        soft_edges={},
    )

    result = IncrementalAnalysisEngine._calculate_degree_deltas(
        old_graph=graph,
        new_graph=graph,
    )

    assert result.complete is True
    assert result.fan_in_updates == {}
    assert result.fan_out_updates == {}
    assert result.added_modules == set()
    assert result.removed_modules == set()


# =========================================================================
# Stage 2B Integration Tests (Canonical State & MCP Verification)
# =========================================================================

def _setup_engine(tmp_path):
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("def target():\n    return 2\n", encoding="utf-8")

    modules = index_repository(str(tmp_path)).modules
    artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    graph = build_graph(modules, trie=trie, package_root=package_root)

    # Canonical macro graph summary metrics
    macro_metrics = {
        "nodes": 2,
        "edges_hard": 0,
        "edges_soft": 0,
        "edges_total": 0,
        "density_hard": 0.0,
        "in_degree_max": 0,
        "out_degree_max": 0,
    }

    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=graph,
        trie=trie,
        package_root=package_root,
        metrics=dict(macro_metrics),
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(provider))
    state_manager.update_state(str(target))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))
    return engine, provider, target, macro_metrics


def test_e2e_modify_updates_hard_edges_and_get_module_context_degrees(tmp_path, monkeypatch):
    engine, provider, target, macro_metrics = _setup_engine(tmp_path)

    # Modify provider to import target
    provider.write_text("import target\ndef run():\n    return target.target()\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.status == "UPDATED"
    assert result.local_metrics_state == "deferred"

    # Canonical dependency_graph is updated
    assert engine.state.dependency_graph.hard_edges["provider"] == {"target"}

    # RepositoryAnalysisState.metrics remains macro summary, unaffected by per-module keys
    assert "provider" not in engine.state.metrics
    assert "target" not in engine.state.metrics
    assert engine.state.metrics == macro_metrics

    # get_module_context truthfully derives degrees directly from current canonical hard_edges
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: None)

    resp_provider = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="provider")
    )
    assert resp_provider["metrics"] == {"fan_in": 0, "fan_out": 1}
    assert resp_provider["degree_metrics_source"] == "live_canonical_graph"

    resp_target = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="target")
    )
    assert resp_target["metrics"] == {"fan_in": 1, "fan_out": 0}
    assert resp_target["degree_metrics_source"] == "live_canonical_graph"


def test_e2e_modify_removes_edge_updates_get_module_context_degrees(tmp_path, monkeypatch):
    engine, provider, target, _ = _setup_engine(tmp_path)

    # First add import
    provider.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(provider))
    assert engine.state.dependency_graph.hard_edges["provider"] == {"target"}

    # Now remove import
    provider.write_text("def run(): pass\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.status == "UPDATED"
    assert engine.state.dependency_graph.hard_edges["provider"] == set()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: None)

    resp_provider = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="provider")
    )
    assert resp_provider["metrics"] == {"fan_in": 0, "fan_out": 0}

    resp_target = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="target")
    )
    assert resp_target["metrics"] == {"fan_in": 0, "fan_out": 0}


def test_e2e_add_updates_dependency_graph_and_get_module_context_live_degrees(tmp_path, monkeypatch):
    engine, provider, target, macro_metrics = _setup_engine(tmp_path)

    new_file = tmp_path / "new_consumer.py"
    new_file.write_text("import target\n", encoding="utf-8")

    result = engine.update_file(str(new_file))
    assert result.status == "UPDATED"
    assert result.local_metrics_state == "deferred"

    # Canonical graph contains new module and edge
    assert engine.state.dependency_graph.hard_edges["new_consumer"] == {"target"}

    # state.metrics has no module records
    assert "new_consumer" not in engine.state.metrics
    assert engine.state.metrics == macro_metrics

    # get_module_context reflects new consumer
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: None)

    resp_consumer = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="new_consumer")
    )
    assert resp_consumer["metrics"] == {"fan_in": 0, "fan_out": 1}
    assert resp_consumer["degree_metrics_source"] == "live_canonical_graph"

    resp_target = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="target")
    )
    assert resp_target["metrics"] == {"fan_in": 1, "fan_out": 0}


def test_e2e_delete_updates_graph_and_get_module_context_degrees(tmp_path, monkeypatch):
    engine, provider, target, macro_metrics = _setup_engine(tmp_path)

    # Connect provider -> target
    provider.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(provider))

    # Now delete provider.py
    provider.unlink()
    result = engine.update_file(str(provider))

    assert result.status == "DELETED"
    assert "provider" not in engine.state.modules
    assert "provider" not in engine.state.dependency_graph.hard_edges

    # state.metrics remains macro summary
    assert "provider" not in engine.state.metrics
    assert engine.state.metrics == macro_metrics

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: None)

    resp_target = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="target")
    )
    assert resp_target["metrics"] == {"fan_in": 0, "fan_out": 0}


def test_state_metrics_not_structurally_polluted_after_incremental_updates(tmp_path):
    engine, provider, target, macro_metrics = _setup_engine(tmp_path)

    # Perform multiple ADD, MODIFY, DELETE operations
    mod_a = tmp_path / "mod_a.py"
    mod_a.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(mod_a))

    mod_b = tmp_path / "mod_b.py"
    mod_b.write_text("import mod_a\n", encoding="utf-8")
    engine.update_file(str(mod_b))

    mod_a.write_text("def a(): pass\n", encoding="utf-8")
    engine.update_file(str(mod_a))

    mod_b.unlink()
    engine.update_file(str(mod_b))

    # Exact schema invariant check
    expected_keys = {
        "nodes",
        "edges_hard",
        "edges_soft",
        "edges_total",
        "density_hard",
        "in_degree_max",
        "out_degree_max",
    }
    assert set(engine.state.metrics.keys()) == expected_keys
    assert engine.state.metrics == macro_metrics


def test_e2e_failed_registry_transaction_leaves_canonical_state_unchanged(tmp_path, monkeypatch):
    engine, provider, target, macro_metrics = _setup_engine(tmp_path)
    original_modules_keys = set(engine.state.modules.keys())
    original_graph_edges = dict(engine.state.dependency_graph.hard_edges)

    def failing_sync(*args, **kwargs):
        raise OSError("Simulated disk failure during transaction")

    monkeypatch.setattr(engine.registry, "sync_with_workspace", failing_sync)

    provider.write_text("import target\n", encoding="utf-8")
    with pytest.raises(OSError):
        engine.update_file(str(provider))

    # state must be completely unaltered
    assert set(engine.state.modules.keys()) == original_modules_keys
    assert engine.state.dependency_graph.hard_edges == original_graph_edges
    assert engine.state.metrics == macro_metrics


def test_get_module_context_ignores_soft_edges_for_degrees(tmp_path, monkeypatch):
    class DummyState:
        modules = {"pkg.soft_mod": object(), "pkg.target": object()}
        artifacts = {}
        dependency_graph = ProjectGraph(
            hard_edges={"pkg.soft_mod": set(), "pkg.target": set()},
            soft_edges={"pkg.soft_mod": {"pkg.target"}},
        )
        metrics = {"nodes": 2, "edges_hard": 0, "edges_soft": 1}

    class DummyEngine:
        state = DummyState()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: DummyEngine())
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: None)

    resp = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="pkg.soft_mod")
    )

    assert resp["metrics"] == {
        "fan_in": 0,
        "fan_out": 0,
    }
    assert resp["degree_metrics_source"] == "live_canonical_graph"


def test_get_module_context_overlays_live_degrees_preserving_saved_wider_metrics(tmp_path, monkeypatch):
    report_file = tmp_path / f"{tmp_path.name}_graph_analytics.json"
    report_file.write_text(
        json.dumps(
            {
                "modules": {
                    "pkg.provider": {
                        "fan_in": 0,
                        "fan_out": 0,
                        "pagerank": 0.42,
                        "export_degree": 5,
                        "visibility": "public",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    class DummyState:
        modules = {"pkg.provider": object(), "pkg.target": object()}
        artifacts = {}
        dependency_graph = ProjectGraph(
            hard_edges={"pkg.provider": {"pkg.target"}, "pkg.target": set()},
            soft_edges={},
        )
        metrics = {"nodes": 2, "edges_hard": 1}

    class DummyEngine:
        state = DummyState()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: DummyEngine())
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: report_file)

    resp = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="pkg.provider")
    )

    assert resp["module"] == "pkg.provider"
    assert resp["metrics"]["fan_out"] == 1
    assert resp["metrics"]["fan_in"] == 0
    assert resp["metrics"]["pagerank"] == 0.42
    assert resp["metrics"]["export_degree"] == 5
    assert resp["metrics"]["visibility"] == "public"
    assert resp["metrics_source"] == "saved_graph_analytics"
    assert resp["degree_metrics_source"] == "live_canonical_graph"
    assert resp["dependency_data_source"] == "live_canonical_graph"


def test_get_module_context_no_live_graph_does_not_claim_live_degree_source(tmp_path, monkeypatch):
    report_file = tmp_path / f"{tmp_path.name}_graph_analytics.json"
    report_file.write_text(
        json.dumps(
            {
                "modules": {
                    "pkg.mod": {
                        "fan_in": 5,
                        "fan_out": 7,
                        "pagerank": 0.33,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: report_file)

    resp = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="pkg.mod")
    )

    assert resp["metrics"]["fan_in"] == 5
    assert resp["metrics"]["fan_out"] == 7
    assert resp["metrics"]["pagerank"] == 0.33
    assert resp["degree_metrics_source"] == "saved_graph_analytics"
    assert resp["metrics_source"] == "saved_graph_analytics"
