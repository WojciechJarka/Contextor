"""End-to-end MCP test for incremental state persistence and live context hydration."""

import json

import pytest
import threading

from contextor import mcp_server
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.paths import repo_cache_dir
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository
from contextor.core.live_state import CanonicalLiveServer, LiveStateClient

pytestmark = pytest.mark.live


def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
    first = RepositoryAnalysisState(modules={"old": object()})
    second = RepositoryAnalysisState(modules={"new": object()})
    server = CanonicalLiveServer(first)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
    monkeypatch.setattr(mcp_server, "_live_engines", {})
    monkeypatch.setattr(mcp_server, "_live_engine_revisions", {})

    class FakeManager:
        state_id = ""

        def __init__(self, _cache):
            pass

    class FakeEngine:
        def __init__(self, state, *_args):
            self.state = state

    monkeypatch.setattr("contextor.core.analysis.state_manager.FileStateManager", FakeManager)
    monkeypatch.setattr("contextor.core.analysis.incremental_engine.IncrementalAnalysisEngine", FakeEngine)
    try:
        initial = mcp_server._get_or_init_engine(tmp_path)
        assert set(initial.state.modules) == {"old"}

        client.publish(second)
        refreshed = mcp_server._get_or_init_engine(tmp_path)
        assert set(refreshed.state.modules) == {"new"}
        assert refreshed is not initial
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_persist_restart_hydrate_keeps_live_reverse_context(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    provider = repo / "provider.py"
    provider.write_text("def run():\n    return 1\n", encoding="utf-8")
    modules = index_repository(str(repo)).modules
    artifacts, failures = collect_module_artifacts(modules, str(repo))
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
    registry = PersistentIdentityRegistry(str(repo))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    cache_dir = repo_cache_dir(repo)
    state_manager = FileStateManager(str(cache_dir))
    state_manager.update_state(str(provider))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(repo))
    monkeypatch.setattr(mcp_server, "_live_engines", {str(repo.resolve()): engine})

    graph_report = tmp_path / "graph.json"
    artifact_report = tmp_path / "artifacts.json"
    summary_report = tmp_path / "summary.json"
    graph_report.write_text(
        json.dumps({"modules": {}, "module_dependency_matrix": {}}), encoding="utf-8"
    )
    artifact_report.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")
    summary_report.write_text(json.dumps({"top_hotspots": []}), encoding="utf-8")
    reports = {
        "graph_analytics.json": graph_report,
        "artifacts_compact.json": artifact_report,
        "summary.json": summary_report,
    }
    monkeypatch.setattr(
        mcp_server,
        "_get_canonical_report",
        lambda _root, name: next(
            (path for suffix, path in reports.items() if name.endswith(suffix)), None
        ),
    )

    consumer = repo / "consumer.py"
    consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
    update = json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(consumer))
    )
    assert update["status"] == "UPDATED"
    assert update["live_state_persisted"] is True
    assert update["runtime_restart_required"] is False

    mcp_server._live_engines.clear()
    hydrated = mcp_server._get_or_init_engine(repo.resolve())
    assert hydrated is not None
    context = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo), file_path="provider.py", compact=False
        )
    )

    assert context["consumers"]["items"] == [
        {"module_id": registry.get_module_id("consumer"), "module": "consumer"}
    ]
    assert context["dependency_data_source"] == "live_canonical_graph"
