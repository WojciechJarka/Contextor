"""End-to-end MCP test for incremental state persistence and live context hydration."""

import json
from copy import deepcopy
import os

import pytest
import threading
from types import SimpleNamespace

from contextor import mcp_server
from contextor.core.analysis.incremental import engine as incremental_engine_module
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
