import json
import os
import threading
import time
from types import SimpleNamespace

import pytest

from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
)
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.api.facade import exclude_state_file
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
from contextor.core.live_state.runtime import _repository_persister, _repository_updater
from contextor.core.live_state.store import save_snapshot
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
    metadata = save_snapshot(state, repo_cache_dir(repo), "bootstrap", exact_revision=1, file_state_payload=manager.build_payload("bootstrap", 1))
    manager.save("bootstrap", revision=metadata.revision)
    state.revision = metadata.revision
    state.state_id = metadata.state_id
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

    adapter_holder = {}
    server = CanonicalLiveServer(
        state,
        updater=_repository_updater(repo, adapter_holder),
        persister=_repository_persister(repo, adapter_holder),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    try:
        watcher = DesktopLiveWatcher(repo, client)
        changed = watcher.poll_once()
        assert changed == sorted([str(added), str(existing), str(removed)])

        reconciled = client.snapshot()
        assert reconciled["revision"] == 4
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
        assert client.snapshot()["revision"] == 4
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
    assert watcher._startup_pending == []
    assert watcher._startup_requires_resync is True

    manager = FileStateManager(str(repo_cache_dir(repo)))
    manager.update_state(str(source))
    manager.save("bootstrap", revision=1)

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


def test_untrusted_startup_filestate_uses_single_resync_not_per_file_replay(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(9):
        (repo / f"module_{index}.py").write_text(f"VALUE = {index}\n", encoding="utf-8")
    calls = []

    class Client:
        def snapshot(self):
            return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
        def ping(self):
            return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs):
            calls.append("update")

    watcher = DesktopLiveWatcher(
        repo,
        Client(),
        on_resync=lambda: (calls.append("resync") or [], object()),
    )
    assert watcher.poll_once() == []
    assert calls == ["resync"]


def test_unchanged_restart_with_coherent_filestate_emits_zero_updates(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _registry, state = _bootstrap_state(repo)
    server = CanonicalLiveServer(state, updater=_repository_updater(repo))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    try:
        watcher = DesktopLiveWatcher(repo, client)
        assert watcher.poll_once() == []
        assert client.snapshot()["revision"] == 1
    finally:
        server.close(); thread.join(timeout=2)


def test_startup_with_trusted_baseline_reconciles_only_real_offline_change(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(); (repo / "a.py").write_text("A = 1\n", encoding="utf-8"); (repo / "b.py").write_text("B = 1\n", encoding="utf-8")
    _registry, state = _bootstrap_state(repo)
    (repo / "a.py").write_text("A = 2\n", encoding="utf-8")
    server = CanonicalLiveServer(state, updater=_repository_updater(repo)); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); client = LiveStateClient(server.endpoint)
    try:
        assert DesktopLiveWatcher(repo, client).poll_once() == [str(repo / "a.py")]
    finally:
        server.close(); thread.join(timeout=2)


def test_failed_startup_resync_does_not_fallback_to_mass_incremental_updates(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(); (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    calls = []
    class Client:
        def snapshot(self): return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
        def ping(self): return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs): calls.append("update")
    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: False)
    assert watcher.poll_once() == []
    assert calls == []
    assert watcher._startup_requires_resync is True


def test_successful_startup_resync_establishes_stable_next_restart_baseline(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    calls = []
    _registry, state = _bootstrap_state(repo)
    cache = repo_cache_dir(repo)
    (cache / "engine_state.meta.json").write_text(
        json.dumps(
            {
                "revision": 99,
                "state_id": "untrusted",
                "file_state_file": "missing-generation.json",
            }
        ),
        encoding="utf-8",
    )

    class Client:
        def snapshot(self): return {"status": "ok", "state": state}
        def ping(self): return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs): calls.append("update")

    def real_resync():
        calls.append("resync")
        (cache / "engine_state.meta.json").unlink()
        manager = FileStateManager(str(cache))
        for path in repo.rglob("*.py"):
            manager.update_state(str(path))
        metadata = save_snapshot(
            state, cache, "resynced", exact_revision=2,
            file_state_payload=manager.build_payload("resynced", 2),
        )
        state.revision = metadata.revision
        state.state_id = metadata.state_id
        return [], SimpleNamespace(live_publish_status="success")

    watcher = DesktopLiveWatcher(repo, Client(), on_resync=real_resync)
    assert watcher.poll_once() == []
    assert calls == ["resync"]
    restarted = DesktopLiveWatcher(repo, Client(), on_resync=lambda: calls.append("second-resync"))
    assert restarted.poll_once() == []
    assert calls == ["resync"]


def test_real_semantic_unchanged_edit_still_advances_filestate_once(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")
    registry, state = _bootstrap_state(repo)
    warm_manager = FileStateManager(str(tmp_path / "warm-state"))
    IncrementalAnalysisEngine(state, registry, warm_manager, str(repo)).update_file(
        str(source)
    )
    manager = FileStateManager(str(tmp_path / "current-state"))
    engine = IncrementalAnalysisEngine(state, registry, manager, str(repo))
    # A filesystem-only edit is intentionally semantic-UNCHANGED while still
    # requiring FileState acknowledgement for restart reconciliation.
    time.sleep(0.01)
    os.utime(source, None)
    result = engine.update_file(str(source))
    assert result.status == "UNCHANGED"
    assert manager.has_changed(str(source)) is False
    manager.save("semantic-noop", revision=1)
    assert FileStateManager(str(tmp_path / "current-state")).has_changed(str(source)) is False


def test_full_analysis_publishes_current_filestate_generation(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "other.py").write_text("OTHER = 2\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive

    errors, result = run_full_analysis_exclusive(repo, timeout=15.0)
    assert result is not None
    manager = FileStateManager(str(repo_cache_dir(repo)))
    assert manager.baseline_status == "trusted"
    assert str(repo / "module.py") in manager.tracked_paths()
    assert str(repo / "other.py") in manager.tracked_paths()
    from contextor.core.live_state.store import read_metadata
    metadata = read_metadata(repo_cache_dir(repo))
    assert manager.revision == metadata.revision
    assert manager.state_id == metadata.state_id


def test_watcher_lease_timeout_never_dispatches_unguarded_update(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _registry, state = _bootstrap_state(repo)
    calls = []

    class Client:
        def snapshot(self): return {"status": "ok", "state": state}
        def ping(self): return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}

    from contextor.core.analysis import full_analysis_coordinator as coordinator
    monkeypatch.setattr(
        coordinator, "acquire_full_analysis",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(coordinator.FullAnalysisBusyError("busy")),
    )
    watcher = DesktopLiveWatcher(repo, Client())
    source.write_text("VALUE = 2\n", encoding="utf-8")
    assert watcher.poll_once() == []
    assert calls == []
    assert watcher._startup_pending == [str(source)]


@pytest.mark.parametrize("state", [
    SimpleNamespace(modules={}, revision=None, state_id="sid"),
    SimpleNamespace(modules={}, revision=1, state_id=""),
])
def test_filestate_is_not_trusted_without_authoritative_live_generation_identity(
    tmp_path, state
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _registry, _state = _bootstrap_state(repo)

    class Client:
        def snapshot(self): return {"status": "ok", "state": state}
        def ping(self): return {"status": "ok", "available": True}

    watcher = DesktopLiveWatcher(repo, Client())
    assert watcher._trusted_file_state(Client().snapshot()) is None
    assert watcher._startup_requires_resync is True


def test_post_lease_snapshot_failure_never_dispatches_unverified_update(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _registry, state = _bootstrap_state(repo)
    calls = []

    class Client:
        def __init__(self): self.snapshot_calls = 0
        def snapshot(self):
            self.snapshot_calls += 1
            if self.snapshot_calls == 1:
                return {"status": "ok", "state": state}
            raise ConnectionError("post-lease snapshot unavailable")
        def ping(self): return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs): calls.append("update")

    watcher = DesktopLiveWatcher(repo, Client())
    source.write_text("VALUE = 2\n", encoding="utf-8")
    assert watcher.poll_once() == []
    assert calls == []
    assert watcher._startup_pending == [str(source)]


def test_startup_resync_with_analysis_errors_remains_untrusted(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    class Client:
        def snapshot(self): return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
        def ping(self): return {"status": "ok", "available": True}
        def update_file(self, *_args, **_kwargs): raise AssertionError("fallback update")
    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: (["error"], object()))
    assert watcher.poll_once() == []
    assert watcher._startup_requires_resync is True


def test_full_analysis_waits_for_inflight_watcher_mutation(tmp_path):
    from contextor.core.analysis.full_analysis_coordinator import acquire_full_analysis, release_full_analysis
    repo = tmp_path / "repo"; repo.mkdir(); PersistentIdentityRegistry(str(repo))
    lease = acquire_full_analysis(repo, owner="watcher", timeout=1)
    entered = threading.Event()
    finished = threading.Event()
    def run():
        try:
            other = acquire_full_analysis(repo, owner="analysis", timeout=2)
            entered.set(); release_full_analysis(other)
        finally: finished.set()
    thread = threading.Thread(target=run); thread.start()
    assert not entered.wait(0.1)
    release_full_analysis(lease); assert finished.wait(2); thread.join()


def test_watcher_does_not_mutate_during_full_analysis_and_rebases_after_publish(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []
    from contextor.core.analysis import full_analysis_coordinator as coordinator
    original = coordinator.acquire_full_analysis
    busy = {"first": True}
    def acquire(root, *, owner, timeout):
        if busy["first"]:
            busy["first"] = False
            raise coordinator.FullAnalysisBusyError("analysis owns lease")
        return original(root, owner=owner, timeout=timeout)
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
    watcher = DesktopLiveWatcher(repo, Client())
    watcher._snapshot = {str(source): (0, 1)}
    source.write_text("VALUE = 2\n", encoding="utf-8")
    watcher._trusted_file_state = lambda _snapshot: object()
    watcher._candidate_requires_update = lambda *_args: False
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
    try:
        assert watcher.poll_once() == []
        assert calls == []
        assert watcher.poll_once() == []
        assert calls == []
    finally:
        monkeypatch.undo()


def test_change_during_startup_resync_is_not_lost(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
    def resync():
        source.write_text("VALUE = 2\n", encoding="utf-8")
        return ([], object())
    watcher = DesktopLiveWatcher(repo, Client(), on_resync=resync)
    watcher._startup_requires_resync = True
    watcher._trusted_file_state = lambda _snapshot: object()
    watcher._candidate_requires_update = lambda *_args: True
    assert watcher.poll_once() == []
    assert calls == []
    watcher._snapshot = {str(source): (0, 1)}
    assert watcher.poll_once() == [str(source)]
    assert calls == ["update"]


def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")

    def run_case(candidate_values, commit_first, expected_calls):
        calls = []
        class Client:
            def __init__(self): self.recovered = False
            def ping(self): return {"status": "ok", "available": True}
            def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=2 if commit_first else 1, state_id="g")}
            def update_file(self, *_args, **_kwargs):
                calls.append("update")
                if len(calls) == 1 and commit_first: raise ConnectionError("response lost after commit")
                if len(calls) == 1 and not commit_first: raise ConnectionError("before commit")
                return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
        client = Client()
        watcher = DesktopLiveWatcher(repo, client)
        watcher._snapshot = {str(source): (0, 1)}
        source.write_text("VALUE = 2\n", encoding="utf-8")
        watcher._trusted_file_state = lambda _snapshot: object()
        values = iter(candidate_values)
        watcher._candidate_requires_update = lambda *_args: next(values)
        watcher._recover_client = lambda: client
        result = watcher.poll_once()
        assert len(calls) == expected_calls
        return result

    assert run_case([True, False], True, 1) == []
    assert run_case([True, True], False, 2) == [str(source)]
    assert run_case([True, None], False, 1) == []


def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, *_args, **_kwargs):
            calls.append("update")
            status = "ERROR" if len(calls) == 1 else "UPDATED"
            return {"status": "ok", "result": SimpleNamespace(status=status)}
    watcher = DesktopLiveWatcher(repo, Client())
    watcher._snapshot = {str(source): (0, 1)}
    source.write_text("VALUE = 2\n", encoding="utf-8")
    watcher._trusted_file_state = lambda _snapshot: object()
    watcher._candidate_requires_update = lambda *_args: True

    assert watcher.poll_once() == []
    assert calls == ["update"]
    assert watcher._startup_pending == [str(source)]
    assert watcher.poll_once() == [str(source)]
    assert calls == ["update", "update"]


def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    first = repo / "a.py"; second = repo / "b.py"
    first.write_text("A = 1\n", encoding="utf-8"); second.write_text("B = 1\n", encoding="utf-8")
    calls = []
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, path, **_kwargs): calls.append(path); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
    watcher = DesktopLiveWatcher(repo, Client())
    watcher._snapshot = {str(first): (0, 1), str(second): (0, 1)}
    first.write_text("A = 2\n", encoding="utf-8"); second.write_text("B = 2\n", encoding="utf-8")
    watcher._trusted_file_state = lambda _snapshot: object()
    deferred = {str(second)}
    watcher._candidate_requires_update = lambda path, *_args: None if path in deferred else True
    assert watcher.poll_once() == [str(first)]
    assert calls == [str(first)]
    deferred.clear()
    assert watcher.poll_once() == [str(second)]
    assert calls == [str(first), str(second)]


def test_missing_update_result_is_not_acknowledged(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, *_args, **_kwargs): return {"status": "ok"}
    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
    source.write_text("VALUE = 2\n", encoding="utf-8")
    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
    assert watcher.poll_once() == []
    assert watcher._startup_pending == [str(source)]


def test_error_top_level_response_is_not_acknowledged(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
    class Client:
        def ping(self): return {"status": "ok", "available": True}
        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
        def update_file(self, *_args, **_kwargs): return {"status": "error", "error": "rejected"}
    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
    source.write_text("VALUE = 2\n", encoding="utf-8")
    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
    with pytest.raises(RuntimeError, match="rejected"):
        watcher.poll_once()
    assert watcher._snapshot[str(source)] == (0, 1)
