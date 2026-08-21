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
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository
from contextor import mcp_server
from contextor.mcp import runtime as mcp_runtime


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
# Stage 2C Macro Metrics & MCP Overlay Integration Tests
# =========================================================================

def _setup_engine(tmp_path):
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("def target_fn():\n    return 2\n", encoding="utf-8")

    modules = index_repository(str(tmp_path)).modules
    artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    graph = build_graph(modules, trie=trie, package_root=package_root)

    macro_metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)

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


def test_stage2c_add_isolated_module_macro_metrics(tmp_path):
    engine, provider, target, initial_metrics = _setup_engine(tmp_path)
    assert initial_metrics["nodes"] == 2
    assert initial_metrics["edges_hard"] == 0

    isolated = tmp_path / "isolated.py"
    isolated.write_text("VALUE = 42\n", encoding="utf-8")

    result = engine.update_file(str(isolated))
    assert result.status == "UPDATED"
    assert result.local_metrics_state == "deferred"
    assert result.global_metrics_state == "deferred"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 3
    assert engine.state.metrics["edges_hard"] == 0
    assert engine.state.metrics["edges_total"] == 0


def test_stage2c_add_module_with_hard_import_macro_metrics(tmp_path, monkeypatch):
    engine, provider, target, initial_metrics = _setup_engine(tmp_path)

    consumer = tmp_path / "consumer.py"
    consumer.write_text("import target\n", encoding="utf-8")

    result = engine.update_file(str(consumer))
    assert result.status == "UPDATED"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 3
    assert engine.state.metrics["edges_hard"] == 1
    assert engine.state.metrics["edges_total"] == 1
    assert engine.state.metrics["out_degree_max"] == 1
    assert engine.state.metrics["in_degree_max"] == 1

    # MCP overlay verification
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    resp_consumer = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="consumer")
    )
    assert resp_consumer["metrics"]["fan_in"] == 0
    assert resp_consumer["metrics"]["fan_out"] == 1
    assert resp_consumer["degree_metrics_source"] == "live_canonical_graph"



def test_stage2c_modify_adding_hard_edge_macro_metrics(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    provider.write_text("import target\n", encoding="utf-8")
    result = engine.update_file(str(provider))
    assert result.status == "UPDATED"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 2
    assert engine.state.metrics["edges_hard"] == 1
    assert engine.state.metrics["edges_total"] == 1
    assert engine.state.metrics["density_hard"] == 0.5


def test_stage2c_modify_removing_hard_edge_macro_metrics(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    # First add edge
    provider.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(provider))
    assert engine.state.metrics["edges_hard"] == 1

    # Now remove edge
    provider.write_text("def run(): pass\n", encoding="utf-8")
    result = engine.update_file(str(provider))
    assert result.status == "UPDATED"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 2
    assert engine.state.metrics["edges_hard"] == 0
    assert engine.state.metrics["edges_total"] == 0
    assert engine.state.metrics["density_hard"] == 0.0


def test_stage2c_delete_module_macro_metrics(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    # Connect provider -> target
    provider.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(provider))
    assert engine.state.metrics["nodes"] == 2
    assert engine.state.metrics["edges_hard"] == 1

    # Delete provider
    provider.unlink()
    result = engine.update_file(str(provider))
    assert result.status == "DELETED"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 1
    assert engine.state.metrics["edges_hard"] == 0
    assert engine.state.metrics["edges_total"] == 0


def test_stage2c_density_and_degree_max_match_canonical_graph(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    # Add mod_a and mod_b both importing target
    mod_a = tmp_path / "mod_a.py"
    mod_a.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(mod_a))

    mod_b = tmp_path / "mod_b.py"
    mod_b.write_text("import target\nimport mod_a\n", encoding="utf-8")
    engine.update_file(str(mod_b))

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["nodes"] == 4
    assert engine.state.metrics["edges_hard"] == 3
    # Target has in_degree = 2 (from mod_a and mod_b), mod_b has out_degree = 2
    assert engine.state.metrics["in_degree_max"] == 2
    assert engine.state.metrics["out_degree_max"] == 2
    assert engine.state.metrics["density_hard"] == round(3 / (4 * 3), 4)


def test_stage2c_soft_edge_change_affects_soft_total_only(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    # Fallback import in provider targeting target (produces a soft edge)
    provider.write_text(
        "from target.submodule import item\n",
        encoding="utf-8",
    )
    result = engine.update_file(str(provider))
    assert result.status == "UPDATED"

    expected = compute_graph_metrics(
        engine.state.dependency_graph.hard_edges,
        engine.state.dependency_graph.soft_edges,
    )
    assert engine.state.metrics == expected
    assert engine.state.metrics["edges_hard"] == 0
    assert engine.state.metrics["edges_soft"] == 1
    assert engine.state.metrics["edges_total"] == 1
    assert engine.state.metrics["in_degree_max"] == 0
    assert engine.state.metrics["out_degree_max"] == 0


def test_stage2c_failed_registry_transaction_leaves_old_metrics_unchanged(tmp_path, monkeypatch):
    engine, provider, target, initial_metrics = _setup_engine(tmp_path)

    def failing_sync(*args, **kwargs):
        raise OSError("Simulated disk failure during transaction")

    monkeypatch.setattr(engine.registry, "sync_with_workspace", failing_sync)

    provider.write_text("def provide_service():\n    pass\n", encoding="utf-8")
    with pytest.raises(OSError):
        engine.update_file(str(provider))

    # state.metrics must remain exactly the old initial metrics
    assert engine.state.metrics == initial_metrics


def test_stage2c_no_module_keys_introduced_into_state_metrics(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    mod_a = tmp_path / "mod_a.py"
    mod_a.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(mod_a))

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
    assert "provider" not in engine.state.metrics
    assert "target" not in engine.state.metrics
    assert "mod_a" not in engine.state.metrics


def test_stage2c_get_module_context_behavior_preserved(tmp_path, monkeypatch):
    engine, provider, target, _ = _setup_engine(tmp_path)

    provider.write_text("import target\n", encoding="utf-8")
    engine.update_file(str(provider))

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    resp_provider = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="provider")
    )
    assert resp_provider["metrics"]["fan_in"] == 0
    assert resp_provider["metrics"]["fan_out"] == 1
    assert resp_provider["degree_metrics_source"] == "live_canonical_graph"

    resp_target = json.loads(
        mcp_server.get_module_context.fn(repo_path=str(tmp_path), module_name="target")
    )
    assert resp_target["metrics"]["fan_in"] == 1
    assert resp_target["metrics"]["fan_out"] == 0
    assert resp_target["degree_metrics_source"] == "live_canonical_graph"


def test_stage2c_local_metrics_state_and_global_metrics_state_remain_deferred(tmp_path):
    engine, provider, target, _ = _setup_engine(tmp_path)

    provider.write_text("import target\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.local_metrics_state == "deferred"
    assert result.global_metrics_state == "deferred"
