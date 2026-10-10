"""End-to-end MCP test for incremental state persistence and live context hydration."""

import json
from copy import copy, deepcopy
import os
from pathlib import Path

import pytest
import threading
import multiprocessing
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

from contextor import mcp_server
from contextor.core.analysis.incremental import engine as incremental_engine_module
from contextor.core.analysis import full_analysis_coordinator as coordinator
from contextor.mcp import report_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
    save_engine_state,
)
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.paths import repo_cache_dir
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository
from contextor.core.reference.shared import (
    materialize_reexport_facts_by_module,
    validate_reexport_facts_by_module,
)
from contextor.core.live_state import CanonicalLiveServer, LiveStateClient, read_metadata
from contextor.core.live_state import store as snapshot_store
from contextor.core.repository_identity import require_repository_identity
from contextor.core.live_state.runtime import _production_domain
from contextor.core.live_state.runtime_lease import (
    RuntimeLeaseManager,
    generation_metadata_path,
    live_lease_path,
)
from contextor.mcp.tools import update_file as update_file_module

pytestmark = pytest.mark.live


def _build_local_fallback_engine(tmp_path, monkeypatch, source):
    repo = tmp_path / "repo"
    repo.mkdir()
    provider = repo / "provider.py"
    provider.write_text(source, encoding="utf-8")
    index = index_repository(str(repo))
    modules = index.modules
    reexport_facts_by_module = materialize_reexport_facts_by_module(
        modules,
        index.reference_facts_by_module,
    )
    artifacts, failures = collect_module_artifacts(modules, str(repo))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=reexport_facts_by_module,
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
    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo.resolve()): engine})
    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
    return repo, provider, engine


def _local_update(repo, provider):
    return json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(provider))
    )


def _rehydrate_local_engine(repo):
    mcp_runtime._live_engines.clear()
    return mcp_runtime.get_or_init_engine(repo.resolve())


def _local_lease_manager(repo, *, lock_timeout=10.0):
    return RuntimeLeaseManager(
        _production_domain(require_repository_identity(repo)),
        lock_timeout=lock_timeout,
    )


def _cross_process_local_candidate_worker(
    repo_text, target_text, cache_text, entered, release, ready, update_started, results, first
):
    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
    from contextor.core import live_state

    live_state.connect = lambda _root: None
    mcp_runtime._live_engines.clear()
    mcp_runtime._live_engine_revisions.clear()
    real_persist = update_file_module._persist_live_engine
    real_update = IncrementalAnalysisEngine.update_file

    if first:
        def wait_in_persist(root, candidate):
            entered.set()
            if not release.wait(10):
                raise TimeoutError("cross-process persistence hold expired")
            return real_persist(root, candidate)

        update_file_module._persist_live_engine = wait_in_persist
    else:
        def observe_update(self, path):
            update_started.set()
            return real_update(self, path)

        IncrementalAnalysisEngine.update_file = observe_update

    try:
        if not first:
            assert mcp_runtime.get_or_init_engine(Path(repo_text)) is not None
            ready.set()
        response = _local_update(Path(repo_text), Path(target_text))
        results.put({
            "role": "first" if first else "second",
            "response": response,
        })
    except BaseException as exc:
        results.put({
            "role": "first" if first else "second",
            "response": {
                "status": "WORKER_ERROR",
                "error": repr(exc),
            },
        })


def _cross_process_full_writer_worker(repo_text, ready, entered, release, results):
    def body(_root, **_kwargs):
        entered.set()
        if not release.wait(10):
            raise TimeoutError("full-analysis body hold expired")

    ready.set()
    try:
        coordinator.run_full_analysis_exclusive(
            repo_text, owner="test_full_writer", analysis_fn=body, timeout=10.0
        )
        results.put("completed")
    except BaseException as exc:
        results.put(repr(exc))


def test_local_incremental_lease_precedes_cache_domain_and_spans_commit(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    events = []
    real_acquire = coordinator.acquire_full_analysis
    real_release = coordinator.release_full_analysis
    real_cache = mcp_runtime._engine_cache_transaction
    real_domain = RuntimeLeaseManager._lock
    real_checkpoint = engine.registry.create_checkpoint
    real_update = IncrementalAnalysisEngine.update_file
    real_persist = update_file_module._persist_live_engine

    def acquire(*args, **kwargs):
        assert kwargs == {
            "owner": "mcp_local_incremental",
            "writer_kind": "local_incremental",
            "timeout": 10.0,
        }
        lease = real_acquire(*args, **kwargs)
        events.append("lease_acquired")
        return lease

    def release(lease):
        assert mcp_runtime._live_engines[str(repo.resolve())] is not engine
        events.append("lease_released")
        return real_release(lease)

    @contextmanager
    def cache(root):
        events.append("cache_enter")
        with real_cache(root) as key:
            yield key
        events.append("cache_exit")

    @contextmanager
    def domain(self):
        events.append("domain_enter")
        with real_domain(self):
            yield
        events.append("domain_exit")

    def checkpoint():
        events.append("checkpoint")
        return real_checkpoint()

    def update(self, path):
        events.append("update")
        return real_update(self, path)

    def persist(root, candidate):
        events.append("persist")
        return real_persist(root, candidate)

    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
    monkeypatch.setattr(coordinator, "release_full_analysis", release)
    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", cache)
    monkeypatch.setattr(RuntimeLeaseManager, "_lock", domain)
    monkeypatch.setattr(engine.registry, "create_checkpoint", checkpoint)
    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)

    result, candidate, _, persisted = update_file_module._execute_local_candidate_update(
        repo, provider, engine
    )

    assert result.status == "UPDATED" and persisted is True
    assert candidate is mcp_runtime._live_engines[str(repo.resolve())]
    assert events[0:3] == ["lease_acquired", "cache_enter", "domain_enter"]
    assert events.index("checkpoint") < events.index("update") < events.index("persist")
    assert events[-3:] == ["domain_exit", "cache_exit", "lease_released"]


def test_local_incremental_timeout_does_not_start_candidate(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_registry = engine.registry.create_checkpoint()
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    observed = []

    def reject(*args, **kwargs):
        observed.append(kwargs)
        raise coordinator.FullAnalysisBusyError("full-analysis lease busy")

    def forbidden(*_args, **_kwargs):
        pytest.fail("candidate, registry, or snapshot started after lease rejection")

    monkeypatch.setattr(coordinator, "acquire_full_analysis", reject)
    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", forbidden)
    response = _local_update(repo, provider)

    assert observed == [{
        "owner": "mcp_local_incremental",
        "writer_kind": "local_incremental",
        "timeout": 10.0,
    }]
    assert response["status"] == "ERROR"
    assert "busy" in response["error"]
    assert mcp_runtime._live_engines[str(repo.resolve())] is engine
    assert engine.registry._state == before_registry
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta


@pytest.mark.parametrize("failure", ["persistence", "update", "rollback"])
def test_local_incremental_lease_released_after_candidate_failure(
    tmp_path, monkeypatch, failure
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_registry = engine.registry.create_checkpoint()
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    events = []
    real_acquire = coordinator.acquire_full_analysis
    real_release = coordinator.release_full_analysis
    real_restore = engine.registry.restore_checkpoint

    def acquire(*args, **kwargs):
        lease = real_acquire(*args, **kwargs)
        events.append("acquire")
        return lease

    def release(lease):
        events.append("release")
        return real_release(lease)

    def restore(checkpoint):
        events.append("rollback")
        if failure == "rollback":
            raise RuntimeError("forced rollback failure")
        return real_restore(checkpoint)

    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
    monkeypatch.setattr(coordinator, "release_full_analysis", release)
    monkeypatch.setattr(engine.registry, "restore_checkpoint", restore)
    if failure in {"persistence", "rollback"}:
        monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_: False)
    else:
        def fail_update(*_args):
            raise RuntimeError("forced update failure")
        monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", fail_update)

    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert events == ["acquire", "rollback", "release"]
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
    if failure == "rollback":
        assert str(repo.resolve()) not in mcp_runtime._live_engines
    else:
        assert mcp_runtime._live_engines[str(repo.resolve())] is engine
        assert engine.registry._state == before_registry
    subsequent = real_acquire(repo, owner="after_failure", timeout=1.0)
    real_release(subsequent)


def test_local_incremental_blocks_wrapped_full_analysis_through_persistence(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    real_persist = update_file_module._persist_live_engine
    entered = threading.Event()
    release = threading.Event()
    full_body = threading.Event()
    results = {}

    def persist(root, candidate):
        entered.set()
        assert release.wait(10)
        return real_persist(root, candidate)

    def full_analysis():
        try:
            coordinator.run_full_analysis_exclusive(
                repo,
                analysis_fn=lambda *_args, **_kwargs: full_body.set(),
                timeout=5.0,
            )
            results["full"] = "completed"
        except BaseException as exc:
            results["full"] = repr(exc)

    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
    full = threading.Thread(target=full_analysis)
    try:
        local.start()
        assert entered.wait(10)
        full.start()
        assert not full_body.wait(0.25)
    finally:
        release.set()
        local.join(10)
        full.join(10)

    assert not local.is_alive() and not full.is_alive()
    assert results["local"]["status"] == "UPDATED"
    assert results["full"] == "completed" and full_body.is_set()


def test_local_wait_for_full_analysis_holds_neither_cache_nor_domain(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    held = coordinator.acquire_full_analysis(repo, owner="holder", timeout=1.0)
    cache_entered = threading.Event()
    domain_entered = threading.Event()
    update_entered = threading.Event()
    real_cache = mcp_runtime._engine_cache_transaction
    real_domain = RuntimeLeaseManager._lock
    real_update = IncrementalAnalysisEngine.update_file
    results = {}

    @contextmanager
    def cache(root):
        cache_entered.set()
        with real_cache(root) as key:
            yield key

    @contextmanager
    def domain(self):
        domain_entered.set()
        with real_domain(self):
            yield

    def update(self, path):
        update_entered.set()
        return real_update(self, path)

    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", cache)
    monkeypatch.setattr(RuntimeLeaseManager, "_lock", domain)
    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update)
    local = threading.Thread(
        target=lambda: results.setdefault(
            "local", update_file_module._execute_local_candidate_update(repo, provider, engine)
        )
    )
    try:
        local.start()
        assert not cache_entered.wait(0.3)
        assert not domain_entered.is_set()
        assert not update_entered.is_set()
    finally:
        coordinator.release_full_analysis(held)
        local.join(10)

    assert not local.is_alive()
    assert results["local"][0].status == "UPDATED"
    assert cache_entered.is_set() and domain_entered.is_set() and update_entered.is_set()


def test_full_analysis_os_lock_excludes_other_process_during_local_persistence(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    entered = threading.Event()
    release_local = threading.Event()
    real_persist = update_file_module._persist_live_engine
    results = {}

    def persist(root, candidate):
        entered.set()
        assert release_local.wait(10)
        return real_persist(root, candidate)

    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    full_body = ctx.Event()
    release_full = ctx.Event()
    full_results = ctx.Queue()
    full = ctx.Process(
        target=_cross_process_full_writer_worker,
        args=(str(repo), ready, full_body, release_full, full_results),
    )
    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
    try:
        local.start()
        assert entered.wait(10)
        full.start()
        assert ready.wait(15)
        assert not full_body.wait(0.3)
    finally:
        release_local.set()
        local.join(10)
        release_full.set()
        if full.pid is not None:
            full.join(15)
        if full.is_alive():
            full.terminate()
            full.join(5)

    assert not local.is_alive() and full.exitcode == 0
    assert results["local"]["status"] == "UPDATED"
    assert full_body.is_set()
    assert full_results.get(timeout=5) == "completed"


@pytest.mark.parametrize("prior_generation", ["never_acquired", "released"])
def test_local_writer_accepts_only_clean_absence_states(
    tmp_path, monkeypatch, prior_generation
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    if prior_generation == "released":
        authority = _local_lease_manager(repo)
        authority.release(authority.acquire())
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")

    response = _local_update(repo, provider)

    assert response["status"] == "UPDATED"
    assert read_metadata(repo_cache_dir(repo)).revision == 2


@pytest.mark.parametrize(
    "authority_state",
    [
        "active",
        "reserved",
        "active_missing_lease",
        "fenced",
        "mismatched_generation",
        "malformed_generation",
        "malformed_lease",
        "foreign_generation",
        "foreign_lease",
        "transport_failure_with_active_lease",
    ],
)
def test_local_writer_rejects_untrusted_authority_before_mutation(
    tmp_path, monkeypatch, authority_state
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    cache_dir = repo_cache_dir(repo)
    previous_meta = (cache_dir / "engine_state.meta.json").read_bytes()
    previous_registry = engine.registry.create_checkpoint()
    previous_engine = mcp_runtime._live_engines[str(repo.resolve())]
    authority = _local_lease_manager(repo)
    domain = authority.domain

    if authority_state in {"active", "transport_failure_with_active_lease"}:
        authority.acquire()
    elif authority_state in {
        "reserved", "active_missing_lease", "fenced", "mismatched_generation"
    }:
        lease = authority.acquire()
        if authority_state == "reserved":
            with authority._lock():
                authority._write_generation(
                    replace(authority._read_generation(), status="reserved")
                )
        elif authority_state == "active_missing_lease":
            live_lease_path(domain).unlink()
        elif authority_state == "fenced":
            authority.fence_owner(lease)
        else:
            with authority._lock():
                authority._write_generation(
                    replace(
                        authority._read_generation(),
                        last_service_instance_id="different-service",
                    )
                )
    elif authority_state == "malformed_generation":
        generation_metadata_path(domain).write_text("{broken", encoding="utf-8")
    elif authority_state == "malformed_lease":
        live_lease_path(domain).write_text("{broken", encoding="utf-8")
    elif authority_state == "foreign_generation":
        generation_metadata_path(domain).write_text(
            json.dumps(replace(authority.read_generation(), repo_id="foreign-repo").to_dict()),
            encoding="utf-8",
        )
    elif authority_state == "foreign_lease":
        lease = authority.acquire()
        live_lease_path(domain).write_text(
            json.dumps(replace(lease, repo_id="foreign-repo").to_dict()),
            encoding="utf-8",
        )

    # The fixture forces connect(root)=None, including the transport-failure case.
    def forbidden(*_args, **_kwargs):
        raise AssertionError("local mutation started despite untrusted authority")

    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", forbidden)
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")

    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "Local writer denied" in response["error"] or "malformed" in response["error"] or "belongs to another domain" in response["error"]
    assert mcp_runtime._live_engines[str(repo.resolve())] is previous_engine
    assert (cache_dir / "engine_state.meta.json").read_bytes() == previous_meta
    assert engine.registry._state == previous_registry


def test_local_writer_rejects_stale_revision_before_checkpoint_or_update(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_registry = engine.registry.create_checkpoint()
    engine.revision = 0
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate or registry checkpoint began before baseline gate")

    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "stale engine revision" in response["error"]
    assert engine.registry._state == before_registry
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta


def test_local_domain_fence_blocks_live_acquire_until_persistence_finishes(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    real_persist = update_file_module._persist_live_engine
    entered = threading.Event()
    release = threading.Event()
    acquired = threading.Event()
    results = {}

    def wait_in_persist(root, candidate):
        entered.set()
        assert release.wait(10)
        return real_persist(root, candidate)

    def acquire_live():
        results["lease"] = _local_lease_manager(repo, lock_timeout=3).acquire()
        acquired.set()

    monkeypatch.setattr(update_file_module, "_persist_live_engine", wait_in_persist)
    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
    live = threading.Thread(target=acquire_live)
    try:
        local.start()
        assert entered.wait(10)
        live.start()
        assert not acquired.wait(0.25)
    finally:
        release.set()
        local.join(10)
        live.join(10)

    assert not local.is_alive() and not live.is_alive()
    assert results["local"]["status"] == "UPDATED"
    assert acquired.is_set()
    assert results["lease"].lease_generation == 1


def test_local_registry_rollback_completes_before_domain_fence_release(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    rollback_entered = threading.Event()
    release_rollback = threading.Event()
    acquired = threading.Event()
    real_restore = engine.registry.restore_checkpoint
    results = {}

    def wait_in_rollback(checkpoint):
        rollback_entered.set()
        assert release_rollback.wait(10)
        return real_restore(checkpoint)

    def acquire_live():
        results["lease"] = _local_lease_manager(repo, lock_timeout=3).acquire()
        acquired.set()

    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)
    monkeypatch.setattr(engine.registry, "restore_checkpoint", wait_in_rollback)
    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
    live = threading.Thread(target=acquire_live)
    try:
        local.start()
        assert rollback_entered.wait(10)
        live.start()
        assert not acquired.wait(0.25)
    finally:
        release_rollback.set()
        local.join(10)
        live.join(10)

    assert not local.is_alive() and not live.is_alive()
    assert results["local"]["status"] == "ERROR"
    assert acquired.is_set()


def test_local_writer_domain_lock_timeout_preserves_state(tmp_path, monkeypatch):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_registry = engine.registry.create_checkpoint()
    original_manager = RuntimeLeaseManager
    held = _local_lease_manager(repo)
    entered = threading.Event()
    release = threading.Event()

    def hold_lock():
        with held._lock():
            entered.set()
            assert release.wait(10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert entered.wait(10)
    import contextor.core.live_state.runtime_lease as lease_module

    monkeypatch.setattr(
        lease_module,
        "RuntimeLeaseManager",
        lambda domain: original_manager(domain, lock_timeout=0.1),
    )
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    try:
        response = _local_update(repo, provider)
    finally:
        release.set()
        holder.join(10)

    assert response["status"] == "ERROR"
    assert "timed out waiting for domain lock" in response["error"]
    assert mcp_runtime._live_engines[str(repo.resolve())] is engine
    assert engine.registry._state == before_registry
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta


def test_two_mcp_processes_cannot_enter_local_candidate_concurrently(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    extra = repo / "extra.py"
    extra.write_text("value = 3\n", encoding="utf-8")
    ctx = multiprocessing.get_context("spawn")
    entered = ctx.Event()
    release = ctx.Event()
    ready = ctx.Event()
    update_started = ctx.Event()
    results = ctx.Queue()
    cache_root = os.environ["CONTEXTOR_CACHE_DIR"]
    first = ctx.Process(
        target=_cross_process_local_candidate_worker,
        args=(
            str(repo), str(provider), cache_root, entered, release, ready,
            update_started, results, True,
        ),
    )
    second = ctx.Process(
        target=_cross_process_local_candidate_worker,
        args=(
            str(repo), str(extra), cache_root, entered, release, ready,
            update_started, results, False,
        ),
    )
    try:
        first.start()
        assert entered.wait(15)
        second.start()
        assert ready.wait(15)
        assert not update_started.wait(0.4)
    finally:
        release.set()
        first.join(15)
        if second.pid is not None:
            second.join(15)
        if first.is_alive():
            first.terminate()
            first.join(5)
        if second.pid is not None and second.is_alive():
            second.terminate()
            second.join(5)

    assert first.exitcode == 0
    assert second.exitcode == 0
    received = [
        results.get(timeout=5),
        results.get(timeout=5),
    ]
    by_role = {
        item["role"]: item["response"]
        for item in received
    }
    assert set(by_role) == {"first", "second"}

    first_result = by_role["first"]
    second_result = by_role["second"]

    assert first_result["status"] == "UPDATED"
    assert second_result["status"] == "ERROR"
    assert "stale" in second_result.get("error", "").lower()
    assert not update_started.is_set()
    assert read_metadata(repo_cache_dir(repo)).revision == 2


def test_local_candidate_cow_keeps_original_nested_facts_and_tracked_files(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    original_state = engine.state
    original_artifacts = original_state.artifacts["provider"]
    original_module = original_state.modules["provider"]
    artifact_content = deepcopy(original_artifacts)
    original_tracked = engine.state_manager._state
    tracked_content = deepcopy(original_tracked)
    checkpoint = engine.registry.create_checkpoint()

    candidate_state = original_state.clone_for_update()
    candidate_manager = copy(engine.state_manager)
    candidate_manager._state = dict(original_tracked)
    candidate = IncrementalAnalysisEngine(
        candidate_state, engine.registry, candidate_manager, str(repo)
    )
    assert candidate.state is not original_state
    assert candidate.state_manager._state is not original_tracked

    provider.write_text(
        "def run():\n    return 1\n\ndef added():\n    return 2\n",
        encoding="utf-8",
    )
    try:
        assert candidate.update_file(str(provider)).status == "UPDATED"
        assert original_state.modules["provider"] is original_module
        assert original_state.artifacts["provider"] is original_artifacts
        assert original_state.artifacts["provider"] == artifact_content
        assert engine.state_manager._state is original_tracked
        assert engine.state_manager._state == tracked_content
    finally:
        engine.registry.restore_checkpoint(checkpoint)


def test_local_candidate_rejected_persistence_preserves_cache_state_manager_and_registry(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_modules = dict(engine.state.modules)
    before_artifacts = deepcopy(engine.state.artifacts)
    provider_module = engine.state.modules["provider"]
    provider_artifacts = engine.state.artifacts["provider"]
    before_tracked = engine.state_manager._state
    before_tracked_content = deepcopy(before_tracked)
    before_registry = engine.registry.create_checkpoint()

    extra = repo / "extra.py"
    extra.write_text("def added():\n    return 2\n", encoding="utf-8")
    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)
    response = _local_update(repo, extra)

    assert response["status"] == "ERROR"
    assert response["live_state_persisted"] is False
    assert mcp_runtime._live_engines[key] is engine
    assert engine.state.modules == before_modules
    assert engine.state.modules["provider"] is provider_module
    assert engine.state.artifacts == before_artifacts
    assert engine.state.artifacts["provider"] is provider_artifacts
    assert engine.state_manager._state is before_tracked
    assert engine.state_manager._state == before_tracked_content
    assert engine.revision == engine.state.revision == 1
    assert mcp_runtime._live_engine_revisions[key] == 1
    assert engine.registry._state == before_registry
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
    assert str(provider) in engine.state_manager.tracked_paths()


def test_local_candidate_metadata_commit_failure_keeps_prior_cache_and_snapshot(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    cache_dir = repo_cache_dir(repo)
    before_meta = (cache_dir / "engine_state.meta.json").read_bytes()
    before_artifacts = deepcopy(engine.state.artifacts)
    before_registry = engine.registry.create_checkpoint()
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    original_replace = snapshot_store.os.replace

    def failing_replace(source, target):
        if target.name == "engine_state.meta.json":
            raise OSError("injected metadata commit failure")
        return original_replace(source, target)

    monkeypatch.setattr(snapshot_store.os, "replace", failing_replace)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert mcp_runtime._live_engines[key] is engine
    assert engine.state.artifacts == before_artifacts
    assert engine.state_manager.revision == engine.state.revision == 1
    assert engine.registry._state == before_registry
    assert (cache_dir / "engine_state.meta.json").read_bytes() == before_meta
    assert read_metadata(cache_dir).revision == 1


def test_local_candidate_persister_exception_before_commit_restores_registry(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    cache_dir = repo_cache_dir(repo)
    before_meta = (cache_dir / "engine_state.meta.json").read_bytes()
    before_artifacts = deepcopy(engine.state.artifacts)
    before_tracked = deepcopy(engine.state_manager._state)
    before_registry = engine.registry.create_checkpoint()
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")

    def fail_persist(*_args):
        raise OSError("injected precommit persistence exception")

    monkeypatch.setattr(update_file_module, "_persist_live_engine", fail_persist)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "precommit persistence exception" in response["error"]
    assert mcp_runtime._live_engines[key] is engine
    assert engine.state.artifacts == before_artifacts
    assert engine.state_manager._state == before_tracked
    assert engine.registry._state == before_registry
    assert engine.state.revision == mcp_runtime._live_engine_revisions[key] == 1
    assert (cache_dir / "engine_state.meta.json").read_bytes() == before_meta


def test_local_candidate_engine_error_after_candidate_publication_preserves_prior_cache(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
    before_artifacts = deepcopy(engine.state.artifacts)
    before_registry = engine.registry.create_checkpoint()
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    real_update = IncrementalAnalysisEngine.update_file

    def update_then_raise(self, file_path):
        result = real_update(self, file_path)
        assert result.status == "UPDATED"
        raise RuntimeError("injected post-publication engine failure")

    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update_then_raise)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "post-publication engine failure" in response["error"]
    assert mcp_runtime._live_engines[key] is engine
    assert engine.state.artifacts == before_artifacts
    assert engine.state_manager.revision == engine.state.revision == 1
    assert engine.registry._state == before_registry
    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta


def test_local_candidate_updated_installs_only_after_exact_persistence(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    original_artifacts = deepcopy(engine.state.artifacts)
    provider.write_text(
        "def run():\n    return 1\n\ndef added():\n    return 2\n", encoding="utf-8"
    )
    real_persist = update_file_module._persist_live_engine
    seen = []

    def assert_before_publish(root, candidate):
        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
        persisted = real_persist(root, candidate)
        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
        return persisted

    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
    response = _local_update(repo, provider)
    published = mcp_runtime._live_engines[key]

    assert response["status"] == "UPDATED"
    assert response["live_state_persisted"] is True
    assert seen == [(True, True), (True, True)]
    assert published is not engine
    assert published.state is not engine.state
    assert published.state_manager._state is not engine.state_manager._state
    assert engine.state.artifacts == original_artifacts
    assert published.state.artifacts != original_artifacts
    assert read_metadata(repo_cache_dir(repo)).revision == 2
    assert published.revision == mcp_runtime._live_engine_revisions[key] == 2


def test_local_candidate_syntax_lkg_recovery_and_unchanged_publish_after_persist(
    tmp_path, monkeypatch
):
    repo, provider, original = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, original) is True
    key = str(repo.resolve())
    original_module = original.state.modules["provider"]
    real_persist = update_file_module._persist_live_engine
    calls = []

    def assert_before_publish(root, candidate):
        calls.append((mcp_runtime._live_engines[key], candidate))
        return real_persist(root, candidate)

    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
    early = _local_update(repo, provider)
    assert early["status"] == "UNCHANGED"
    assert early["live_state_persisted"] is True
    assert calls[-1][0] is original
    early_engine = mcp_runtime._live_engines[key]
    assert early_engine is not original

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    reconciled = _local_update(repo, provider)
    assert reconciled["status"] in {"UPDATED", "UNCHANGED"}
    assert reconciled["live_state_persisted"] is True
    reconciled_engine = mcp_runtime._live_engines[key]
    assert reconciled_engine is not early_engine
    assert calls[-1][0] is early_engine

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    parsed = _local_update(repo, provider)
    assert parsed["status"] == "UNCHANGED"
    assert parsed["live_state_persisted"] is True
    parsed_engine = mcp_runtime._live_engines[key]
    assert parsed_engine is not reconciled_engine
    assert calls[-1][0] is reconciled_engine

    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
    syntax = _local_update(repo, provider)
    assert syntax["status"] == "SYNTAX_ERROR"
    assert syntax["live_state_persisted"] is True
    stale_engine = mcp_runtime._live_engines[key]
    assert stale_engine is not parsed_engine
    assert calls[-1][0] is parsed_engine
    assert stale_engine.state.modules["provider"] is original_module
    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
    assert "provider" not in original.state.module_parse_freshness

    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    recovered = _local_update(repo, provider)
    assert recovered["status"] == "RECOVERED"
    assert recovered["live_state_persisted"] is True
    fresh_engine = mcp_runtime._live_engines[key]
    assert fresh_engine is not stale_engine
    assert calls[-1][0] is stale_engine
    assert "provider" not in fresh_engine.state.module_parse_freshness
    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
    assert read_metadata(repo_cache_dir(repo)).revision == 6


def test_local_candidate_rollback_failure_evicts_cache(tmp_path, monkeypatch):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)

    def failed_restore(_checkpoint):
        raise OSError("injected registry rollback failure")

    monkeypatch.setattr(engine.registry, "restore_checkpoint", failed_restore)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "rollback" in response["error"].lower()
    assert key not in mcp_runtime._live_engines
    assert key not in mcp_runtime._live_engine_revisions
    assert read_metadata(repo_cache_dir(repo)).revision == 1


def test_local_candidate_disk_ahead_does_not_restore_older_registry(tmp_path, monkeypatch):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    real_persist = update_file_module._persist_live_engine
    restore_calls = []

    def commit_then_report_failure(root, candidate):
        assert real_persist(root, candidate) is True
        return False

    def record_restore(checkpoint):
        restore_calls.append(checkpoint)
        raise AssertionError("older registry checkpoint must not be restored")

    monkeypatch.setattr(update_file_module, "_persist_live_engine", commit_then_report_failure)
    monkeypatch.setattr(engine.registry, "restore_checkpoint", record_restore)
    response = _local_update(repo, provider)

    assert response["status"] == "ERROR"
    assert "divergence" in response["error"].lower()
    assert restore_calls == []
    assert key not in mcp_runtime._live_engines
    assert key not in mcp_runtime._live_engine_revisions
    assert read_metadata(repo_cache_dir(repo)).revision == 2


def test_local_candidate_serializes_update_through_persistence(tmp_path, monkeypatch):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    extra = repo / "extra.py"
    extra.write_text("value = 3\n", encoding="utf-8")
    real_update = IncrementalAnalysisEngine.update_file
    real_persist = update_file_module._persist_live_engine
    persist_entered = threading.Event()
    release_persist = threading.Event()
    second_update_entered = threading.Event()
    results = {}
    calls = []

    def observe_update(self, path):
        if Path(path).name == "extra.py":
            second_update_entered.set()
        return real_update(self, path)

    def block_first_persistence(root, candidate):
        calls.append(candidate)
        if len(calls) == 1:
            persist_entered.set()
            assert release_persist.wait(10)
        return real_persist(root, candidate)

    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", observe_update)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", block_first_persistence)
    first = threading.Thread(
        target=lambda: results.setdefault("first", _local_update(repo, provider)), daemon=True
    )
    second = threading.Thread(
        target=lambda: results.setdefault("second", _local_update(repo, extra)), daemon=True
    )
    try:
        first.start()
        assert persist_entered.wait(10)
        second.start()
        assert second_update_entered.wait(0.3) is False
    finally:
        release_persist.set()
        first.join(10)
        second.join(10)

    assert not first.is_alive() and not second.is_alive()
    assert results["first"]["status"] == "UPDATED"
    assert results["second"]["status"] == "UPDATED"
    assert second_update_entered.is_set()
    assert len(calls) == 2
    assert read_metadata(repo_cache_dir(repo)).revision == 3


def test_local_exact_generation_initial_successor_and_filestate_hydration(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    cache_dir = repo_cache_dir(repo)
    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))
    assert tracked_sha

    def forbidden_save(*_args, **_kwargs):
        raise AssertionError("FileStateManager.save must not be called")

    monkeypatch.setattr(engine.state_manager, "save", forbidden_save)
    assert update_file_module._persist_live_engine(repo, engine) is True
    initial = read_metadata(cache_dir)
    assert initial.revision == 1
    assert initial.state_file.startswith("engine_state.r1.")
    assert initial.file_state_file.startswith("file_state.r1.")
    assert (cache_dir / initial.state_file).is_file()
    initial_payload = json.loads((cache_dir / initial.file_state_file).read_text())
    assert initial_payload["_meta"] == {"state_id": initial.state_id, "revision": 1}
    assert initial_payload["files"][str(provider)]["sha256"] == tracked_sha
    assert not (cache_dir / "file_state.json").exists()

    hydrated = _rehydrate_local_engine(repo)
    assert hydrated is not None
    assert hydrated.state.revision == hydrated.state_manager.revision == 1
    assert hydrated.state.state_id == hydrated.state_manager.state_id == initial.state_id
    assert hydrated.state_manager.get_tracked_sha256(str(provider)) == tracked_sha
    assert hydrated.state_manager.has_changed(str(provider)) is False

    assert update_file_module._persist_live_engine(repo, hydrated) is True
    successor = read_metadata(cache_dir)
    assert successor.revision == 2
    assert successor.state_id == initial.state_id
    assert successor.state_file != initial.state_file
    assert successor.file_state_file != initial.file_state_file
    assert json.loads((cache_dir / successor.file_state_file).read_text())["_meta"] == {
        "state_id": initial.state_id,
        "revision": 2,
    }


@pytest.mark.parametrize("revision_owner", ["engine", "state", "cache"])
def test_local_exact_generation_rejects_stale_revision_before_publication(
    tmp_path, monkeypatch, revision_owner
):
    repo, _provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    cache_dir = repo_cache_dir(repo)
    before = (cache_dir / "engine_state.meta.json").read_bytes()
    if revision_owner == "engine":
        engine.revision = 0
    elif revision_owner == "state":
        engine.state.revision = 0
    else:
        mcp_runtime._live_engine_revisions[str(repo.resolve())] = 0

    with pytest.raises(RuntimeError, match="revision"):
        update_file_module._persist_live_engine(repo, engine)
    assert (cache_dir / "engine_state.meta.json").read_bytes() == before


def test_local_exact_generation_rejects_invalid_existing_metadata(
    tmp_path, monkeypatch
):
    repo, _provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    cache_dir = repo_cache_dir(repo)
    metadata_path = cache_dir / "engine_state.meta.json"
    metadata_path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(RuntimeError, match="metadata is invalid"):
        update_file_module._persist_live_engine(repo, engine)
    assert metadata_path.read_text(encoding="utf-8") == "{invalid"


def test_local_exact_generation_serializer_failure_preserves_original_identity(
    tmp_path, monkeypatch
):
    repo, _provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    before_revision = getattr(engine.state, "revision", None)
    before_state_id = getattr(engine.state, "state_id", None)

    def failing_dump(*_args, **_kwargs):
        raise OSError("injected serializer failure")

    monkeypatch.setattr(snapshot_store.pickle, "dump", failing_dump)
    assert update_file_module._persist_live_engine(repo, engine) is False
    assert getattr(engine.state, "revision", None) == before_revision
    assert getattr(engine.state, "state_id", None) == before_state_id
    assert read_metadata(repo_cache_dir(repo)) is None


@pytest.mark.parametrize("failure_stage", ["file_state", "metadata_pointer"])
def test_local_exact_generation_staging_failure_preserves_prior_generation(
    tmp_path, monkeypatch, failure_stage
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    cache_dir = repo_cache_dir(repo)
    before = (cache_dir / "engine_state.meta.json").read_bytes()
    previous = read_metadata(cache_dir)
    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))

    if failure_stage == "file_state":
        original_dump = snapshot_store.json.dump

        def failing_dump(value, stream, *args, **kwargs):
            if stream.name.endswith(".json") and "file_state.r2." in stream.name:
                raise OSError("injected FileState generation failure")
            return original_dump(value, stream, *args, **kwargs)

        monkeypatch.setattr(snapshot_store.json, "dump", failing_dump)
    else:
        original_replace = snapshot_store.os.replace

        def failing_replace(source, target):
            if target.name == "engine_state.meta.json":
                raise OSError("injected metadata pointer failure")
            return original_replace(source, target)

        monkeypatch.setattr(snapshot_store.os, "replace", failing_replace)

    assert update_file_module._persist_live_engine(repo, engine) is False
    assert (cache_dir / "engine_state.meta.json").read_bytes() == before
    assert read_metadata(cache_dir) == previous
    assert engine.state.revision == engine.revision == 1
    assert engine.state_manager.revision == 1
    loaded = load_engine_state(
        str(cache_dir), previous.state_id,
        expected_repo_id=require_repository_identity(repo).repo_id,
        expected_root_path=repo,
    )
    assert loaded is not None and loaded.revision == 1
    reloaded_manager = FileStateManager(str(cache_dir))
    assert reloaded_manager.revision == 1
    assert reloaded_manager.get_tracked_sha256(str(provider)) == tracked_sha


@pytest.mark.parametrize("existing_state_id", ["", "legacy-valid-id"])
def test_local_exact_generation_migrates_legacy_filestate_and_state_id(
    tmp_path, monkeypatch, existing_state_id
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    cache_dir = repo_cache_dir(repo)
    identity = require_repository_identity(repo)
    baseline = save_engine_state(
        engine.state, str(cache_dir), existing_state_id,
        writer="mcp", repo_id=identity.repo_id, root_path=identity.root_path,
    )
    assert baseline is not None and baseline.revision == 1
    engine.state_manager.save(existing_state_id, revision=1)
    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))
    assert not read_metadata(cache_dir).file_state_file

    assert update_file_module._persist_live_engine(repo, engine) is True
    migrated = read_metadata(cache_dir)
    assert migrated.revision == 2
    assert migrated.state_id == (existing_state_id or identity.repo_id)
    assert migrated.file_state_file.startswith("file_state.r2.")
    assert (cache_dir / migrated.file_state_file).is_file()
    hydrated = _rehydrate_local_engine(repo)
    assert hydrated.state.state_id == hydrated.state_manager.state_id == migrated.state_id
    assert hydrated.state_manager.revision == 2
    assert hydrated.state_manager.get_tracked_sha256(str(provider)) == tracked_sha


def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
    first = RepositoryAnalysisState(modules={"old": object()})
    second = RepositoryAnalysisState(modules={"new": object()})
    server = CanonicalLiveServer(first)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})

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
        initial = mcp_runtime.get_or_init_engine(tmp_path)
        assert set(initial.state.modules) == {"old"}

        client.publish(second)
        refreshed = mcp_runtime.get_or_init_engine(tmp_path)
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
    index = index_repository(str(repo))
    modules = index.modules
    reexport_facts_by_module = materialize_reexport_facts_by_module(
        modules,
        index.reference_facts_by_module,
    )
    artifacts, failures = collect_module_artifacts(modules, str(repo))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=reexport_facts_by_module,
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
    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo.resolve()): engine})

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
        report_helpers,
        "get_canonical_report",
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

    mcp_runtime._live_engines.clear()
    hydrated = mcp_runtime.get_or_init_engine(repo.resolve())
    assert hydrated is not None
    assert validate_reexport_facts_by_module(
        hydrated.state.reexport_facts_by_module,
        hydrated.state.modules,
    )
    context = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo), file_path="provider.py", compact=False
        )
    )

    assert context["consumers"]["items"] == [
        {"module_id": registry.get_module_id("consumer"), "module": "consumer"}
    ]
    assert context["dependency_data_source"] == "live_canonical_graph"


def test_local_fallback_updated_facts_survive_snapshot_hydration(tmp_path, monkeypatch):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    original_artifacts = deepcopy(engine.state.artifacts["provider"])
    provider.write_text(
        "def run():\n    return 1\n\ndef added():\n    return 2\n",
        encoding="utf-8",
    )

    response = _local_update(repo, provider)
    assert response["status"] == "UPDATED"
    assert response["live_state_persisted"] is True

    updated_engine = mcp_runtime._live_engines[str(repo.resolve())]
    assert updated_engine.state.artifacts["provider"] != original_artifacts
    hydrated = _rehydrate_local_engine(repo)
    assert hydrated is not None
    assert hydrated.state.artifacts["provider"] == updated_engine.state.artifacts["provider"]


def test_local_fallback_syntax_error_and_recovery_survive_snapshot_hydration(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    original_module = deepcopy(engine.state.modules["provider"])
    original_artifacts = deepcopy(engine.state.artifacts["provider"])

    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
    syntax_error = _local_update(repo, provider)
    assert syntax_error["status"] == "SYNTAX_ERROR"
    assert syntax_error["live_state_persisted"] is True

    syntax_hydrated = _rehydrate_local_engine(repo)
    assert syntax_hydrated is not None
    assert syntax_hydrated.state.modules["provider"] == original_module
    assert syntax_hydrated.state.artifacts["provider"] == original_artifacts
    assert syntax_hydrated.state.module_parse_freshness["provider"]["state"] == "stale"
    assert (
        syntax_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
        == "checked_with_errors"
    )

    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
    recovered = _local_update(repo, provider)
    assert recovered["status"] == "RECOVERED"
    assert recovered["live_state_persisted"] is True

    recovered_hydrated = _rehydrate_local_engine(repo)
    assert recovered_hydrated is not None
    assert "provider" not in recovered_hydrated.state.module_parse_freshness
    assert (
        recovered_hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
        == "checked_and_none"
    )


def test_local_fallback_early_and_parsed_unchanged_are_persisted_and_hydrated(
    tmp_path, monkeypatch
):
    repo, provider, _engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    real_persist = update_file_module._persist_live_engine
    persist_calls = []

    def persist_and_record(root, engine):
        persist_calls.append((root, engine))
        return real_persist(root, engine)

    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist_and_record)

    early_unchanged = _local_update(repo, provider)
    assert early_unchanged["status"] == "UNCHANGED"
    assert early_unchanged["live_state_persisted"] is True
    assert len(persist_calls) == 1

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    reconciled = _local_update(repo, provider)
    assert reconciled["status"] in {"UPDATED", "UNCHANGED"}
    assert reconciled["live_state_persisted"] is True
    assert len(persist_calls) == 2

    stat = provider.stat()
    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
    parsed_unchanged = _local_update(repo, provider)
    assert parsed_unchanged["status"] == "UNCHANGED", parsed_unchanged
    assert parsed_unchanged["live_state_persisted"] is True
    assert len(persist_calls) == 3

    parsed_engine = mcp_runtime._live_engines[str(repo.resolve())]
    expected_lineage = deepcopy(parsed_engine.state.lineage_facts_by_source)
    assert "provider.py" in expected_lineage
    hydrated = _rehydrate_local_engine(repo)
    assert hydrated is not None
    assert (
        hydrated.state.syntax_diagnostics_by_path["provider.py"]["status"]
        == "checked_and_none"
    )
    assert hydrated.state.lineage_facts_by_source == expected_lineage
    assert hydrated.state_manager.has_changed(str(provider)) is False


def test_local_fallback_structured_preparation_error_persists_published_mutations(
    tmp_path, monkeypatch
):
    repo, provider, _engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    provider.write_text(
        "def run():\n    return 1\n# trigger preparation\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        incremental_engine_module,
        "prepare_source_update",
        lambda **_kwargs: SimpleNamespace(
            has_error=True,
            error_status="ERROR",
            error_message="structured preparation failure",
            line_number=2,
            column_number=3,
        ),
    )

    response = _local_update(repo, provider)
    assert response["status"] == "ERROR"
    assert response["live_state_persisted"] is True

    hydrated = _rehydrate_local_engine(repo)
    assert hydrated is not None
    assert hydrated.state.module_parse_freshness["provider"]["state"] == "stale"
