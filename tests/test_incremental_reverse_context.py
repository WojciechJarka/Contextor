"""Focused graph-freshness test for a newly added importing module."""

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository


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
