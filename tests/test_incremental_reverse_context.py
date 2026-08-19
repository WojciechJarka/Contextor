"""Focused graph-freshness test for a newly added importing module."""

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.symbol_engine.indexer import index_repository

pytestmark = pytest.mark.live


def test_new_importing_file_immediately_updates_forward_and_reverse_graph(tmp_path):
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    modules = index_repository(str(tmp_path)).modules
    artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(provider))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    consumer = tmp_path / "consumer.py"
    consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
    result = engine.update_file(str(consumer))

    assert result.graph_state == "fresh"
    assert engine.state.dependency_graph.hard_edges["consumer"] == {"provider"}
    reverse_consumers = {
        source
        for source, targets in engine.state.dependency_graph.hard_edges.items()
        if "provider" in targets
    }
    assert reverse_consumers == {"consumer"}


def test_deleted_file_reports_all_removed_definition_artifacts(tmp_path):
    module_file = tmp_path / "removable.py"
    module_file.write_text(
        "from pathlib import Path\n\n"
        "def run():\n    return Path('.')\n\n"
        "class Worker:\n    def execute(self):\n        return run()\n",
        encoding="utf-8",
    )
    modules = index_repository(str(tmp_path)).modules
    artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(module_file))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    module_file.unlink()
    result = engine.update_file(str(module_file))

    assert result.status == "DELETED"
    assert result.delta.is_deleted is True
    assert result.delta.artifacts_removed == ["Worker", "Worker.execute", "run"]
    assert result.delta.imports_removed == ["pathlib"]
    assert "removable" not in engine.state.artifacts


def _make_engine(tmp_path) -> IncrementalAnalysisEngine:
    state = RepositoryAnalysisState()
    registry = PersistentIdentityRegistry(str(tmp_path))
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    return IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))


def test_affected_set_direct_consumer(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B (A imports B)
    graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=graph, new_graph=graph)
    assert affected == {"A", "B"}


def test_affected_set_transitive_chain(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B -> C
    graph = ProjectGraph(hard_edges={"A": {"B"}, "B": {"C"}}, soft_edges={})
    affected = engine._calculate_affected_set("C", old_graph=graph, new_graph=graph)
    assert affected == {"A", "B", "C"}


def test_affected_set_unrelated_isolation(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B, D independent (D -> E)
    graph = ProjectGraph(hard_edges={"A": {"B"}, "D": {"E"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=graph, new_graph=graph)
    assert affected == {"A", "B"}
    assert "D" not in affected
    assert "E" not in affected


def test_affected_set_old_edge_preservation(tmp_path):
    engine = _make_engine(tmp_path)
    # OLD: A -> B
    # NEW: edge removed (e.g. A dropped import of B)
    old_graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={})
    new_graph = ProjectGraph(hard_edges={"A": set()}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=old_graph, new_graph=new_graph)
    assert affected == {"A", "B"}


def test_affected_set_new_edge_discovery(tmp_path):
    engine = _make_engine(tmp_path)
    # OLD: no A -> B
    # NEW: A -> B added
    old_graph = ProjectGraph(hard_edges={"A": set()}, soft_edges={})
    new_graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=old_graph, new_graph=new_graph)
    assert affected == {"A", "B"}


def test_affected_set_hard_and_soft_union(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B (hard), C -> B (soft)
    graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={"C": {"B"}})
    affected = engine._calculate_affected_set("B", old_graph=graph, new_graph=graph)
    assert affected == {"A", "B", "C"}


def test_affected_set_cycle_termination(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B -> C -> A (cycle)
    graph = ProjectGraph(hard_edges={"A": {"B"}, "B": {"C"}, "C": {"A"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=graph, new_graph=graph)
    assert affected == {"A", "B", "C"}


def test_affected_set_both_graphs_absent(tmp_path):
    engine = _make_engine(tmp_path)
    affected = engine._calculate_affected_set("standalone", old_graph=None, new_graph=None)
    assert affected == {"standalone"}


def test_affected_set_downstream_provider_not_included(tmp_path):
    engine = _make_engine(tmp_path)
    # B -> D (B imports D); change B => D must NOT be in blast radius
    graph = ProjectGraph(hard_edges={"B": {"D"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=graph, new_graph=graph)
    assert affected == {"B"}
    assert "D" not in affected


def test_affected_set_only_old_graph_present(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B in old_graph, new_graph is None
    old_graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=old_graph, new_graph=None)
    assert affected == {"A", "B"}


def test_affected_set_only_new_graph_present(tmp_path):
    engine = _make_engine(tmp_path)
    # A -> B in new_graph, old_graph is None
    new_graph = ProjectGraph(hard_edges={"A": {"B"}}, soft_edges={})
    affected = engine._calculate_affected_set("B", old_graph=None, new_graph=new_graph)
    assert affected == {"A", "B"}


def test_update_file_returns_fresh_blast_radius_for_modified_provider(tmp_path):
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    consumer = tmp_path / "consumer.py"
    consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
    
    modules = index_repository(str(tmp_path)).modules
    artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(provider))
    state_manager.update_state(str(consumer))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    # Modify provider with structural import change
    provider.write_text("import sys\ndef run():\n    return 2\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.status == "UPDATED"
    assert result.blast_radius_state == "fresh"
    assert sorted(result.affected_modules) == ["consumer", "provider"]


def test_update_file_returns_fresh_blast_radius_for_deleted_file(tmp_path):
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    consumer = tmp_path / "consumer.py"
    consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
    
    modules = index_repository(str(tmp_path)).modules
    artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(provider))
    state_manager.update_state(str(consumer))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    # Delete provider
    provider.unlink()
    result = engine.update_file(str(provider))

    assert result.status == "DELETED"
    assert result.blast_radius_state == "fresh"
    assert result.affected_modules == ["consumer", "provider"]


def test_update_file_add_module_resolving_dependency(tmp_path):
    consumer = tmp_path / "consumer.py"
    consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
    
    modules = index_repository(str(tmp_path)).modules
    artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(consumer))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    # Add provider
    provider = tmp_path / "provider.py"
    provider.write_text("def run():\n    return 42\n", encoding="utf-8")
    result = engine.update_file(str(provider))

    assert result.status == "UPDATED"
    assert result.blast_radius_state == "fresh"
    assert result.affected_modules == ["consumer", "provider"]


def test_update_file_missing_graph_evidence_is_deferred_and_empty_affected_modules(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("def run():\n    pass\n", encoding="utf-8")
    from contextor.core.domain.module import Module
    module = Module(module_id="sample", path="sample.py", absolute_path=str(sample), imports=[])
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace({"sample"}, {"sample::run": "A1/1"})
    state = RepositoryAnalysisState(
        modules={"sample": module},
        artifacts={},
        dependency_graph=None,
        trie={},
        package_root=None,
        artifact_consumption={},
    )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(sample))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    sample.write_text("def run():\n    return 1\n", encoding="utf-8")
    result = engine.update_file(str(sample))
    assert result.status == "UPDATED"
    assert result.blast_radius_state == "deferred"
    assert result.affected_modules == []


def test_update_file_syntax_error_preserves_stale_and_empty_affected_modules(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("def run():\n    pass\n", encoding="utf-8")
    engine = _make_engine(tmp_path)
    engine.state_manager.update_state(str(sample))

    sample.write_text("def run(:\n", encoding="utf-8")
    result = engine.update_file(str(sample))
    assert result.status == "SYNTAX_ERROR"
    assert result.blast_radius_state == "stale"
    assert result.affected_modules == []


def test_update_file_delete_with_missing_old_graph_is_deferred_despite_rebuilt_new_graph(tmp_path):
    mod_a = tmp_path / "mod_a.py"
    mod_a.write_text("def func_a(): pass\n", encoding="utf-8")
    mod_b = tmp_path / "mod_b.py"
    mod_b.write_text("from mod_a import func_a\n", encoding="utf-8")

    from contextor.core.domain.module import Module
    module_a = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(mod_a), imports=[])
    module_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(mod_b), imports=[])

    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace({"mod_a", "mod_b"}, {"mod_a::func_a": "A1/1"})

    state = RepositoryAnalysisState(
        modules={"mod_a": module_a, "mod_b": module_b},
        artifacts={},
        dependency_graph=None,  # Missing OLD graph
        trie={},
        package_root=None,
        artifact_consumption={},
    )
    state_manager = FileStateManager(str(tmp_path / ".contextor"))
    state_manager.update_state(str(mod_a))
    state_manager.update_state(str(mod_b))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(tmp_path))

    # Delete mod_a
    mod_a.unlink()
    result = engine.update_file(str(mod_a))

    assert result.status == "DELETED"
    # Even though new_graph was rebuilt during delete, missing OLD graph means blast radius cannot be complete
    assert engine.state.dependency_graph is not None  # new_graph successfully rebuilt
    assert result.blast_radius_state == "deferred"
    assert result.affected_modules == []



