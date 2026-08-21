import json
import threading

import pytest

from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
)
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.api.facade import exclude_state_file
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
from contextor.core.live_state.runtime import _repository_updater
from contextor.core.live_state.watcher import DesktopLiveWatcher
from contextor.core.paths import repo_cache_dir
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
)
from contextor.core.symbol_engine.indexer import index_repository


pytestmark = pytest.mark.live


def _bootstrap_state(repo):
    registry = PersistentIdentityRegistry(str(repo))
    modules = index_repository(str(repo)).modules
    artifacts, _ = collect_module_artifacts(modules, str(repo))
    trie = build_trie(modules)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules),
        trie=trie,
        package_root=detect_package_root(modules, trie),
    )
    manager = FileStateManager(str(repo_cache_dir(repo)))
    for path in repo.rglob("*.py"):
        manager.update_state(str(path))
    manager.save()
    return registry, state


def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    existing = repo / "existing.py"
    removed = repo / "removed.py"
    existing.write_text("def value():\n    return 1\n", encoding="utf-8")
    removed.write_text("def obsolete():\n    return 1\n", encoding="utf-8")
    _registry, state = _bootstrap_state(repo)

    added = repo / "added.py"
    added.write_text(
        "from existing import value\n\ndef added():\n    return value()\n",
        encoding="utf-8",
    )
    existing.write_text(
        "def value():\n    return 2\n\ndef changed():\n    return True\n",
        encoding="utf-8",
    )
    removed.unlink()

    server = CanonicalLiveServer(state, updater=_repository_updater(repo))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    try:
        watcher = DesktopLiveWatcher(repo, client)
        changed = watcher.poll_once()
        assert changed == sorted([str(added), str(existing), str(removed)])

        reconciled = client.snapshot()
        assert reconciled["revision"] == 3
        current = reconciled["state"]
        assert "added" in current.modules
        assert "added" in current.artifacts
        assert "added" in current.dependency_graph.hard_edges
        assert "existing" in current.dependency_graph.hard_edges["added"]
        assert "changed" in current.artifacts["existing"]["own_symbols"]
        assert "removed" not in current.modules
        assert "removed" not in current.artifacts
        assert "removed" not in current.dependency_graph.hard_edges
        assert all(
            "removed" not in targets
            for targets in current.dependency_graph.hard_edges.values()
        )

        restarted = DesktopLiveWatcher(repo, client)
        assert restarted.poll_once() == []
        assert client.snapshot()["revision"] == 3
    finally:
        server.close()
        thread.join(timeout=2)


def test_startup_reconciliation_does_not_resurrect_excluded_files(tmp_path):
    repo = tmp_path / "repo"
    excluded_dir = repo / "excluded"
    excluded_dir.mkdir(parents=True)
    excluded_file = excluded_dir / "ignored.py"
    excluded_file.write_text("VALUE = 1\n", encoding="utf-8")
    state_file = exclude_state_file(str(repo))
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps({"excluded": ["excluded"], "auto_exclude_dirs": []}),
        encoding="utf-8",
    )

    class Client:
        def snapshot(self):
            return {"status": "ok", "state": RepositoryAnalysisState()}

        def ping(self):
            return {"status": "ok", "available": True}

        def update_file(self, *_args, **_kwargs):
            raise AssertionError("excluded file must not enter incremental update")

    watcher = DesktopLiveWatcher(repo, Client())
    assert str(excluded_file) not in watcher._snapshot
    assert watcher.poll_once() == []


def test_startup_candidate_is_revalidated_after_fingerprint_refresh(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    PersistentIdentityRegistry(str(repo))
    modules = index_repository(str(repo)).modules
    state = RepositoryAnalysisState(
        modules=dict(modules),
        dependency_graph=build_graph(modules),
    )
    updates = []

    class Client:
        def snapshot(self):
            return {"status": "ok", "state": state}

        def ping(self):
            return {"status": "ok", "available": True}

        def update_file(self, path, **_kwargs):
            updates.append(path)
            raise AssertionError("stale startup candidate must be filtered")

    watcher = DesktopLiveWatcher(repo, Client())
    assert watcher._startup_pending == [str(source)]

    manager = FileStateManager(str(repo_cache_dir(repo)))
    manager.update_state(str(source))
    manager.save()

    assert watcher.poll_once() == []
    assert updates == []


def test_semantic_noop_acknowledges_missing_persisted_fingerprint(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")
    registry, state = _bootstrap_state(repo)
    manager = FileStateManager(str(tmp_path / "first-empty-file-state"))
    engine = IncrementalAnalysisEngine(state, registry, manager, str(repo))
    engine.update_file(str(source))

    missing_manager = FileStateManager(str(tmp_path / "second-empty-file-state"))
    engine = IncrementalAnalysisEngine(state, registry, missing_manager, str(repo))
    assert missing_manager.has_changed(str(source)) is True
    result = engine.update_file(str(source))
    assert result.status == "UNCHANGED"
    assert missing_manager.has_changed(str(source)) is False
