"""Unit and integration boundaries for the shared canonical LIVE snapshot store."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from contextor.mcp import analysis_jobs
from contextor.core.api.facade import ContextorFacade
from contextor.core.analysis.state_manager import canonical_artifact_consumption_targets
from contextor.core.live_state import (
    load_snapshot,
    migrate_legacy_snapshot,
    read_metadata,
    save_snapshot,
    SnapshotRevisionConflict,
)
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core.repository_identity import read_repository_identity

pytestmark = pytest.mark.live


def test_artifact_consumption_exact_full_and_incremental_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _root: None)
    repo = tmp_path / "repo"
    repo.mkdir()
    a = repo / "a.py"
    b = repo / "b.py"
    c = repo / "c.py"
    a.write_text(
        "def used():\n    return 1\n\n"
        "def spare():\n    return 2\n\n"
        "def unused():\n    return 3\n",
        encoding="utf-8",
    )
    b.write_text("from a import used\n\ndef call_b():\n    return used()\n", encoding="utf-8")
    c.write_text(
        "from a import used, spare\n\ndef call_c():\n    return used()\n",
        encoding="utf-8",
    )

    errors, _ = ContextorFacade().analyze_project(str(repo))
    assert not errors, errors
    cache = repo_cache_dir(repo)
    identity = read_repository_identity(repo)
    assert identity is not None
    metadata = read_metadata(cache)
    assert metadata is not None
    hydrated = hydrate_repository_engine(repo)
    assert hydrated is not None
    assert hydrated.source == "snapshot"
    engine = hydrated.engine
    state = engine.state
    assert state.artifact_consumption_state == "fresh"
    assert set(state.artifact_consumption) == canonical_artifact_consumption_targets(state.artifacts)
    used_entry = state.artifact_consumption["a::used"]
    assert set(used_entry["consumers"]) == {"b", "c"}
    assert set(used_entry["channels"]["b"]) == {"api_imports", "direct_calls"}
    assert set(used_entry["channels"]["c"]) == {"api_imports", "direct_calls"}
    assert state.artifact_consumption["a::spare"]["channels"]["c"] == ["api_imports"]
    assert state.artifact_consumption["a::unused"] == {"consumers": [], "channels": {}}
    full_map = deepcopy(state.artifact_consumption)
    full_marker = state.artifact_consumption_state

    loaded = load_snapshot(
        cache,
        metadata.state_id,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    assert loaded is not None
    loaded_state, loaded_metadata = loaded
    assert loaded_state.artifact_consumption == full_map
    assert loaded_state.artifact_consumption_state == full_marker
    missing_consumer = deepcopy(full_map)
    missing_consumer["a::used"]["consumers"].remove("b")
    assert loaded_state.artifact_consumption != missing_consumer
    missing_channel = deepcopy(full_map)
    missing_channel["a::used"]["channels"]["c"].remove("direct_calls")
    assert loaded_state.artifact_consumption != missing_channel
    assert loaded_state.state_id == loaded_metadata.state_id == metadata.state_id
    assert loaded_state.revision == loaded_metadata.revision == metadata.revision

    rehydrated = hydrate_repository_engine(repo)
    assert rehydrated is not None
    assert rehydrated.source == "snapshot"
    assert rehydrated.engine.state.artifact_consumption == full_map
    assert rehydrated.engine.state.artifact_consumption_state == full_marker
    assert rehydrated.engine.state.artifact_consumption["a::unused"] == {
        "consumers": [], "channels": {}
    }

    b.write_text("B_VALUE = 1\n", encoding="utf-8")
    result = engine.update_file(str(b))
    assert result.status == "UPDATED"
    state = engine.state
    assert state.artifact_consumption_state == "fresh"
    assert set(state.artifact_consumption) == canonical_artifact_consumption_targets(state.artifacts)
    updated_used = state.artifact_consumption["a::used"]
    assert "b" not in updated_used["consumers"]
    assert "b" not in updated_used["channels"]
    assert "c" in updated_used["consumers"]
    assert updated_used["channels"]["c"] == full_map["a::used"]["channels"]["c"]
    assert state.artifact_consumption["a::spare"] == full_map["a::spare"]
    assert state.artifact_consumption["a::unused"] == full_map["a::unused"]
    updated_map = deepcopy(state.artifact_consumption)
    updated_marker = state.artifact_consumption_state

    next_revision = metadata.revision + 1
    saved = save_snapshot(
        state,
        cache,
        metadata.state_id,
        writer="test-incremental-roundtrip",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        exact_revision=next_revision,
        file_state_payload=engine.state_manager.build_payload(
            metadata.state_id, next_revision
        ),
    )
    assert saved.revision == next_revision
    assert read_metadata(cache) == saved
    updated_loaded = load_snapshot(
        cache,
        metadata.state_id,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    assert updated_loaded is not None
    updated_state, updated_metadata = updated_loaded
    assert updated_state.artifact_consumption == updated_map
    assert updated_state.artifact_consumption_state == updated_marker
    assert updated_state.state_id == updated_metadata.state_id == metadata.state_id
    assert updated_state.revision == updated_metadata.revision == next_revision

    updated_hydrated = hydrate_repository_engine(repo)
    assert updated_hydrated is not None
    assert updated_hydrated.source == "snapshot"
    assert updated_hydrated.engine.state.artifact_consumption == updated_map
    assert updated_hydrated.engine.state.artifact_consumption_state == updated_marker
    assert set(updated_hydrated.engine.state.artifact_consumption) == (
        canonical_artifact_consumption_targets(updated_hydrated.engine.state.artifacts)
    )
    assert "b" not in updated_hydrated.engine.state.artifact_consumption["a::used"]["consumers"]
    assert "b" not in updated_hydrated.engine.state.artifact_consumption["a::used"]["channels"]


def test_artifact_consumption_fresh_empty_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _root: None)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "empty.py").write_text("pass\n", encoding="utf-8")

    errors, _ = ContextorFacade().analyze_project(str(repo))
    assert not errors, errors
    cache = repo_cache_dir(repo)
    identity = read_repository_identity(repo)
    assert identity is not None
    metadata = read_metadata(cache)
    assert metadata is not None
    loaded = load_snapshot(
        cache,
        metadata.state_id,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    assert loaded is not None
    state, loaded_metadata = loaded
    assert canonical_artifact_consumption_targets(state.artifacts) == set()
    assert state.artifact_consumption == {}
    assert state.artifact_consumption_state == "fresh"
    assert loaded_metadata == metadata

    hydrated = hydrate_repository_engine(repo)
    assert hydrated is not None
    assert hydrated.source == "snapshot"
    assert hydrated.engine.state.artifact_consumption == {}
    assert hydrated.engine.state.artifact_consumption_state == "fresh"


def test_module_usage_manifest_roundtrips_with_repository_state(tmp_path):
    manifest={"pkg.mod":{"module_id":"pkg.mod","path":"C:/x.py","sha256":"abc","semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}}
    state=RepositoryAnalysisState(module_usages_manifest=manifest)
    save_snapshot(state,tmp_path,"manifest")
    loaded,_=load_snapshot(tmp_path,"manifest")
    assert loaded.module_usages_manifest == manifest


def test_legacy_state_without_manifest_loads_with_empty_manifest(tmp_path):
    legacy=SimpleNamespace(modules={},dependency_graph=None,module_usages={})
    save_snapshot(legacy,tmp_path,"legacy-manifest")
    loaded,_=load_snapshot(tmp_path,"legacy-manifest")
    assert loaded.module_usages_manifest == {}


def _split_lineage_test_state(*source_keys):
    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )
    from contextor.core.domain.module import Module
    from contextor.core.domain.lineage_facts import (
        LINEAGE_FACTS_SEMANTIC_VERSION,
        LineageFamilyStatus,
        MaterializedLineageSourceFacts,
        SourceLineageManifest,
    )

    sources = {}

    for index, source_key in enumerate(
        source_keys
    ):
        sources[source_key] = (
            MaterializedLineageSourceFacts(
                manifest=SourceLineageManifest(
                    source_key=source_key,
                    source_fingerprint=(
                        f"source-{index}"
                    ),
                    semantic_version=(
                        LINEAGE_FACTS_SEMANTIC_VERSION
                    ),
                    status=(
                        LineageFamilyStatus.FRESH
                    ),
                    anchor_count=0,
                    flow_count=0,
                    surface_count=0,
                )
            )
        )

    return RepositoryAnalysisState(
        modules={
            source_key: Module(
                module_id=source_key,
                path=source_key,
                absolute_path=str(Path(source_key).resolve()),
                imports=[],
            )
            for source_key in source_keys
        },
        reexport_facts_by_module={
            source_key: {
                "exporter": source_key,
                "explicit_all": None,
                "bindings": {},
                "star_sources": [],
            }
            for source_key in source_keys
        },
        lineage_facts_by_source=sources,
        lineage_facts_state=(
            LineageFamilyStatus.FRESH.value
        ),
        lineage_facts_semantic_version=(
            LINEAGE_FACTS_SEMANTIC_VERSION
        ),
    )


def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
    first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
    second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")

    state, metadata = load_snapshot(tmp_path, "state-a")

    assert state == {"value": 2}
    assert (first.revision, second.revision, metadata.revision) == (1, 2, 2)
    assert metadata.writer == "mcp"
    assert read_metadata(tmp_path) == metadata



def _snapshot_lock_holder(lock_path, ready, release):
    import contextor.core.live_state.store as store

    fd = store._acquire_lock(Path(lock_path))
    try:
        ready.set()
        release.wait(30)
    finally:
        store._release_lock(fd)


def _snapshot_lock_probe(lock_path, timeout, connection):
    import contextor.core.live_state.store as store

    try:
        try:
            fd = store._acquire_lock(Path(lock_path), timeout=timeout)
        except BaseException as exc:
            connection.send(
                (type(exc).__name__, str(exc), getattr(exc, "errno", None), getattr(exc, "winerror", None))
            )
        else:
            try:
                store._release_lock(fd)
            except BaseException as exc:
                connection.send(
                    (type(exc).__name__, str(exc), getattr(exc, "errno", None), getattr(exc, "winerror", None))
                )
            else:
                connection.send(("acquired",))
    finally:
        connection.close()


def _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout):
    receiving, sending = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_snapshot_lock_probe, args=(str(lock_path), timeout, sending))
    process.start()
    sending.close()
    try:
        assert receiving.poll(15), f"snapshot lock probe exited without a result: {process.exitcode}"
        result = receiving.recv()
        process.join(15)
        assert process.exitcode == 0, result
        return result
    finally:
        receiving.close()
        if process.is_alive():
            process.terminate()
            process.join(5)


def _start_spawned_snapshot_lock_holder(ctx, lock_path):
    ready = ctx.Event()
    release = ctx.Event()
    process = ctx.Process(target=_snapshot_lock_holder, args=(str(lock_path), ready, release))
    process.start()
    if not ready.wait(15):
        process.terminate()
        process.join(5)
        pytest.fail(f"snapshot lock holder did not acquire the lock: exitcode={process.exitcode}")
    assert process.is_alive()
    return process, release


def test_snapshot_lock_sequential_acquisition_leaves_stable_file(tmp_path):
    import contextor.core.live_state.store as store

    lock_path = tmp_path / "engine_state.lock"
    first = store._acquire_lock(lock_path)
    store._release_lock(first)
    assert lock_path.is_file()

    second = store._acquire_lock(lock_path)
    store._release_lock(second)
    assert lock_path.is_file()


def test_snapshot_lock_same_process_contention_times_out(tmp_path):
    import contextor.core.live_state.store as store

    lock_path = tmp_path / "engine_state.lock"
    first = store._acquire_lock(lock_path)
    try:
        with pytest.raises(TimeoutError):
            store._acquire_lock(lock_path, timeout=0.1)
    finally:
        store._release_lock(first)

    second = store._acquire_lock(lock_path)
    store._release_lock(second)
    assert lock_path.is_file()


def test_snapshot_lock_cross_process_exclusion(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "engine_state.lock"
    holder, release = _start_spawned_snapshot_lock_holder(ctx, lock_path)
    try:
        result = _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=0.1)
        assert result[0] == "TimeoutError", result
        assert holder.is_alive()
    finally:
        release.set()
        holder.join(10)
        if holder.is_alive():
            holder.terminate()
            holder.join(5)
    assert holder.exitcode == 0
    assert lock_path.is_file()
    assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)


def test_snapshot_lock_process_death_releases_ownership(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "engine_state.lock"
    holder, _ = _start_spawned_snapshot_lock_holder(ctx, lock_path)
    try:
        holder.terminate()
        holder.join(10)
        assert not holder.is_alive()
        assert lock_path.is_file()
        assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)
    finally:
        if holder.is_alive():
            holder.terminate()
            holder.join(5)


def test_snapshot_lock_old_mtime_does_not_steal_ownership(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "engine_state.lock"
    holder, release = _start_spawned_snapshot_lock_holder(ctx, lock_path)
    try:
        old = time.time() - 3600
        os.utime(lock_path, (old, old))
        assert lock_path.stat().st_mtime < time.time() - 30
        result = _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=0.1)
        assert result[0] == "TimeoutError", result
        assert holder.is_alive()
    finally:
        release.set()
        holder.join(10)
        if holder.is_alive():
            holder.terminate()
            holder.join(5)
    assert holder.exitcode == 0
    assert lock_path.is_file()
    assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)


def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    replacements = []
    original_replace = store.os.replace
    monkeypatch.setattr(store.os, "replace", lambda source, target: (replacements.append((source, target)), original_replace(source, target))[1])
    save_snapshot({"value": 1}, tmp_path, "state-a")
    assert replacements[0][1].name == "engine_state.pkl"
    assert replacements[0][0].name != "engine_state.pkl"
    assert replacements[0][0].name.endswith(".tmp")


def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    baseline = save_snapshot({"value": 1}, tmp_path, "state-a")
    original_replace = store.os.replace
    original_unlink = type(tmp_path).unlink

    def failing_replace(source, target):
        if target.name == "engine_state.meta.json":
            raise RuntimeError("authoritative persistence failure")
        return original_replace(source, target)

    monkeypatch.setattr(store.os, "replace", failing_replace)
    def failing_unlink(self, *args, **kwargs):
        if self.name == "engine_state.lock":
            raise AssertionError("stable snapshot lock must not be unlinked")
        raise OSError("cleanup failure")
    monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
    with pytest.raises(RuntimeError, match="authoritative persistence failure"):
        save_snapshot({"value": 2}, tmp_path, "state-a", exact_revision=baseline.revision + 1, file_state_payload={"_meta": {"state_id": "state-a", "revision": baseline.revision + 1}, "files": {}})
    assert read_metadata(tmp_path).revision == baseline.revision
    monkeypatch.setattr(type(tmp_path), "unlink", original_unlink)
    monkeypatch.setattr(store.os, "replace", original_replace)
    assert save_snapshot({"value": 3}, tmp_path, "state-a").revision == baseline.revision + 1


def test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite(tmp_path):
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
    for _ in range(9):
        save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a")
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(SimpleNamespace(value="bad"), tmp_path, "state-a", exact_revision=12, file_state_payload={"_meta": {"state_id": "state-a", "revision": 12}, "files": {}})
    save_snapshot(SimpleNamespace(value="ahead"), tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    candidate = SimpleNamespace(value="candidate")
    with pytest.raises(SnapshotRevisionConflict) as exc_info:
        save_snapshot(candidate, tmp_path, "state-a", exact_revision=11, file_state_payload={"_meta": {"state_id": "state-a", "revision": 11}, "files": {}})
    assert (exc_info.value.current_revision, exc_info.value.requested_revision) == (11, 11)
    with pytest.raises(SnapshotRevisionConflict):
        save_snapshot(candidate, tmp_path, "state-a", exact_revision=10, file_state_payload={"_meta": {"state_id": "state-a", "revision": 10}, "files": {}})


def test_exact_snapshot_rejects_file_state_payload_mismatches(tmp_path):
    state = SimpleNamespace(value="candidate")
    with pytest.raises(ValueError, match="state_id"):
        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "other", "revision": 1}, "files": {}})
    with pytest.raises(ValueError, match="revision"):
        save_snapshot(state, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 2}, "files": {}})


def test_legacy_dict_snapshot_returns_tuple(tmp_path):
    (tmp_path / "engine_state.pkl").write_bytes(__import__("pickle").dumps({"legacy": True}))
    (tmp_path / "engine_state.meta.json").write_text(
        '{"schema_version":"1.2","state_id":"legacy","revision":1}',
        encoding="utf-8",
    )
    loaded = load_snapshot(tmp_path, "legacy")
    assert loaded is not None
    assert loaded[0] == {"legacy": True}


def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
    candidate = SimpleNamespace(value="candidate")
    metadata = save_snapshot(candidate, tmp_path, "state-a", exact_revision=1, file_state_payload={"_meta": {"state_id": "state-a", "revision": 1}, "files": {}})
    loaded, loaded_metadata = load_snapshot(tmp_path, "state-a")
    assert metadata.revision == loaded_metadata.revision == loaded.revision == 1


def test_current_schema_14_splits_lineage_and_roundtrips(tmp_path):
    import json
    import pickle

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    assert metadata.schema_version == "1.4"
    assert metadata.lineage_manifest_file

    with (
        tmp_path
        / metadata.state_file
    ).open("rb") as stream:
        core_payload = pickle.load(
            stream
        )

    assert (
        core_payload[
            "state"
        ].lineage_facts_by_source
        == {}
    )

    manifest = json.loads(
        (
            tmp_path
            / metadata.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest[
            "schema_version"
        ]
        == "1.0"
    )
    assert (
        manifest[
            "state_id"
        ]
        == "sid"
    )
    assert (
        manifest[
            "revision"
        ]
        == 1
    )
    assert set(
        manifest[
            "sources"
        ]
    ) == {
        "pkg/a.py",
        "pkg/b.py",
    }

    for entry in manifest[
        "sources"
    ].values():
        assert (
            tmp_path
            / entry[
                "file"
            ]
        ).is_file()

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "sid",
        )
    )

    assert loaded_metadata == metadata
    assert (
        loaded_state.lineage_facts_by_source
        == state.lineage_facts_by_source
    )


def test_split_manifest_omitted_active_source_is_rejected(tmp_path):
    import json

    state = _split_lineage_test_state("a.py", "b.py")
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )
    assert metadata.schema_version == "1.4"
    assert set(state.lineage_facts_by_source) == {"a.py", "b.py"}
    assert all(
        not (slice_.anchors or slice_.flows or slice_.surfaces)
        for slice_ in state.lineage_facts_by_source.values()
    )
    baseline = load_snapshot(tmp_path, "sid")
    assert baseline is not None
    assert set(baseline[0].lineage_facts_by_source) == {"a.py", "b.py"}

    manifest_path = tmp_path / metadata.lineage_manifest_file
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["sources"]) == {"a.py", "b.py"}
    manifest["sources"].pop("b.py")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    assert load_snapshot(tmp_path, "sid") is None
    assert read_metadata(tmp_path) == metadata


@pytest.mark.parametrize("case", ["embedded_repo_id_mismatch", "embedded_state_id_missing"])
def test_reproducer_split_embedded_metadata_gap(tmp_path, case):
    import pickle

    state = _split_lineage_test_state("a.py")
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        repo_id="repo-original",
        root_path=str(tmp_path),
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )
    assert metadata.schema_version == "1.4"
    baseline = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-original",
        expected_root_path=str(tmp_path),
    )
    assert baseline is not None
    assert baseline[0].state_id == baseline[1].state_id == "sid"

    state_path = tmp_path / metadata.state_file
    payload = pickle.loads(state_path.read_bytes())
    assert payload["metadata"]["repo_id"] == "repo-original"
    assert payload["metadata"]["state_id"] == "sid"
    if case == "embedded_repo_id_mismatch":
        payload["metadata"]["repo_id"] = "repo-different"
    else:
        payload["metadata"].pop("state_id")
    state_path.write_bytes(pickle.dumps(payload))

    assert load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-original",
        expected_root_path=str(tmp_path),
    ) is None
    assert read_metadata(tmp_path) == metadata


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "state_id",
        "revision",
        "writer",
        "repo_id",
        "root_path",
        "state_file",
        "file_state_file",
        "lineage_manifest_file",
    ],
)
@pytest.mark.parametrize("tamper", ["missing", "mismatched"])
def test_schema_14_rejects_missing_or_mismatched_embedded_field(tmp_path, field, tamper):
    import pickle

    state = _split_lineage_test_state("a.py")
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        writer="desktop",
        repo_id="repo-original",
        root_path=str(tmp_path),
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )
    assert metadata.schema_version == "1.4"
    expected_load = {
        "expected_repo_id": "repo-original",
        "expected_root_path": str(tmp_path),
    }
    assert load_snapshot(tmp_path, "sid", **expected_load) is not None

    state_path = tmp_path / metadata.state_file
    payload = pickle.loads(state_path.read_bytes())
    assert payload["metadata"][field] == getattr(metadata, field)
    if tamper == "missing":
        payload["metadata"].pop(field)
    else:
        mismatched = {
            "schema_version": "1.3",
            "state_id": "other-sid",
            "revision": 2,
            "writer": "other-writer",
            "repo_id": "other-repo",
            "root_path": str(tmp_path / "other-root"),
            "state_file": "other-state.pkl",
            "file_state_file": "other-file-state.json",
            "lineage_manifest_file": "other-manifest.json",
        }
        payload["metadata"][field] = mismatched[field]
    state_path.write_bytes(pickle.dumps(payload))

    assert load_snapshot(tmp_path, "sid", **expected_load) is None
    assert read_metadata(tmp_path) == metadata


def test_split_deferred_lineage_allows_missing_active_source(tmp_path):
    state = _split_lineage_test_state("a.py", "b.py")
    state.lineage_facts_by_source.pop("b.py")
    state.lineage_facts_state = "deferred"
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )

    loaded = load_snapshot(tmp_path, "sid")
    assert loaded is not None
    loaded_state, loaded_metadata = loaded
    assert loaded_metadata == metadata
    assert {module.path for module in loaded_state.modules.values()} == {"a.py", "b.py"}
    assert set(loaded_state.lineage_facts_by_source) == {"a.py"}
    assert loaded_state.lineage_facts_state == "deferred"


def test_split_lineage_rejects_foreign_source_key(tmp_path):
    state = _split_lineage_test_state("a.py", "b.py")
    state.modules.pop("b.py")
    state.reexport_facts_by_module.pop("b.py")
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )
    assert metadata.lineage_manifest_file
    assert set(state.lineage_facts_by_source) == {"a.py", "b.py"}
    assert {module.path for module in state.modules.values()} == {"a.py"}

    assert load_snapshot(tmp_path, "sid") is None


def test_split_lineage_accepts_valid_zero_fact_slice(tmp_path):
    state = _split_lineage_test_state("a.py")
    source_slice = state.lineage_facts_by_source["a.py"]
    assert source_slice.manifest.anchor_count == 0
    assert source_slice.manifest.flow_count == 0
    assert source_slice.manifest.surface_count == 0
    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {"state_id": "sid", "revision": 1},
            "files": {},
        },
    )

    loaded = load_snapshot(tmp_path, "sid")
    assert loaded is not None
    loaded_state, loaded_metadata = loaded
    assert loaded_metadata == metadata
    assert loaded_state.lineage_facts_by_source == {"a.py": source_slice}
    assert loaded_state.lineage_facts_state == "fresh"
    assert loaded_state.lineage_query_index_state == "fresh"


def test_current_schema_reexport_facts_roundtrip(tmp_path):
    facts = {
        "pkg.mod": {
            "exporter": "pkg.mod",
            "explicit_all": None,
            "bindings": {},
            "star_sources": [],
        }
    }
    state = RepositoryAnalysisState(
        modules={"pkg.mod": SimpleNamespace()},
        reexport_facts_by_module=facts,
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "reexport-roundtrip",
    )
    loaded, loaded_metadata = load_snapshot(
        tmp_path,
        "reexport-roundtrip",
    )

    assert metadata.schema_version == "1.4"
    assert loaded_metadata.schema_version == "1.4"
    assert loaded.reexport_facts_by_module == facts


def test_save_snapshot_rejects_incomplete_canonical_reexport_facts(
    tmp_path,
):
    state = RepositoryAnalysisState(
        modules={"pkg.mod": SimpleNamespace()},
        reexport_facts_by_module={},
    )

    with pytest.raises(
        ValueError,
        match=(
            "Cannot persist RepositoryAnalysisState with incomplete "
            "canonical re-export facts"
        ),
    ):
        save_snapshot(
            state,
            tmp_path,
            "incomplete-reexport",
        )


def test_legacy_canonical_snapshot_without_reexport_facts_is_rejected(
    tmp_path,
):
    import json
    import pickle

    state = RepositoryAnalysisState(
        modules={"pkg.mod": SimpleNamespace()},
        reexport_facts_by_module={
            "pkg.mod": {
                "exporter": "pkg.mod",
                "explicit_all": None,
                "bindings": {},
                "star_sources": [],
            }
        },
    )
    del vars(state)["reexport_facts_by_module"]
    (tmp_path / "engine_state.pkl").write_bytes(
        pickle.dumps(state)
    )
    (tmp_path / "engine_state.meta.json").write_text(
        json.dumps(
            {
                "schema_version": "1.3",
                "state_id": "legacy-canonical",
                "revision": 1,
            }
        ),
        encoding="utf-8",
    )

    assert load_snapshot(
        tmp_path,
        "legacy-canonical",
    ) is None


def test_split_snapshot_load_emits_non_overlapping_phase_timings(tmp_path):
    import contextor.core.runtime_trace as runtime_trace

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    with runtime_trace.capture_trace_events() as events:
        loaded = load_snapshot(
            tmp_path,
            "sid",
            expected_repo_id="repo-test",
            expected_root_path=str(tmp_path),
        )

    assert loaded is not None

    phase_events = [
        item
        for item in events
        if item.get("ev")
        == "LIVE_SNAPSHOT_LOAD_PHASE"
    ]

    assert [
        item["component"]
        for item in phase_events
    ] == [
        "metadata_read",
        "core_pickle_unpickle",
        "split_lineage_load",
        "normalize_symbol_call_facts",
        "normalize_lineage_facts_state",
        "normalize_lineage_query_index_state",
        "normalize_reexport_facts_state",
        "post_normalization_finalize",
    ]

    assert all(
        item["repo_id"] == "repo-test"
        for item in phase_events
    )

    assert all(
        isinstance(item["elapsed_ms"], (int, float))
        and item["elapsed_ms"] >= 0
        for item in phase_events
    )

    split_event = next(
        item
        for item in phase_events
        if item["component"]
        == "split_lineage_load"
    )

    lineage_normalize_event = next(
        item
        for item in phase_events
        if item["component"]
        == "normalize_lineage_facts_state"
    )

    assert split_event["count"] == 2
    assert lineage_normalize_event["count"] == 2

    assert all(
        item["timing_semantics"]
        == "non_overlapping_load_snapshot_phase"
        for item in phase_events
    )


def test_split_lineage_validation_cache_skips_repeat_deep_revalidation(
    tmp_path,
    monkeypatch,
):
    import json

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert first_loaded is not None

    cache_path = (
        tmp_path
        / store._LINEAGE_VALIDATION_CACHE_NAME
    )

    assert cache_path.is_file()

    cache_payload = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        cache_payload[
            "schema_version"
        ]
        == store.LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION
    )
    assert (
        cache_payload[
            "validation_contract_version"
        ]
        == store.LINEAGE_VALIDATION_CONTRACT_VERSION
    )

    assert (
        cache_payload[
            "schema_version"
        ]
        == "2"
    )

    assert (
        cache_payload[
            "repo_id"
        ]
        == "repo-test"
    )

    assert set(cache_payload) == {
        "schema_version",
        "validation_contract_version",
        "repo_id",
        "lineage_semantic_version",
        "chunks",
    }

    assert (
        set(
            cache_payload[
                "chunks"
            ]
        )
        == {
            "pkg/a.py",
            "pkg/b.py",
        }
    )

    def unexpected_revalidation(
        source_slice,
    ):
        raise AssertionError(
            "trusted lineage chunk was deeply revalidated"
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        unexpected_revalidation,
    )

    second_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert second_loaded is not None

    second_state, second_metadata = (
        second_loaded
    )

    assert second_metadata == metadata
    assert (
        second_state.lineage_facts_by_source
        == first_loaded[
            0
        ].lineage_facts_by_source
    )


def test_split_lineage_validation_cache_contract_mismatch_revalidates(
    tmp_path,
    monkeypatch,
):
    import json

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert first_loaded is not None

    cache_path = (
        tmp_path
        / store._LINEAGE_VALIDATION_CACHE_NAME
    )

    cache_payload = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    cache_payload[
        "validation_contract_version"
    ] = "stale"

    cache_path.write_text(
        json.dumps(
            cache_payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    original = (
        store._revalidate_lineage_slice
    )
    calls = []

    def counting_revalidation(
        source_slice,
    ):
        calls.append(
            source_slice.manifest.source_key
        )
        return original(
            source_slice
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        counting_revalidation,
    )

    second_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert second_loaded is not None

    assert sorted(calls) == [
        "pkg/a.py",
        "pkg/b.py",
    ]

    rewritten = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        rewritten[
            "validation_contract_version"
        ]
        == store.LINEAGE_VALIDATION_CONTRACT_VERSION
    )

    assert (
        second_loaded[
            1
        ]
        == metadata
    )

def test_split_lineage_validation_cache_survives_revision_churn_with_reused_chunks(
    tmp_path,
    monkeypatch,
):
    import json

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    first_metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert first_loaded is not None

    cache_path = (
        tmp_path
        / store._LINEAGE_VALIDATION_CACHE_NAME
    )

    cache_before = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first_metadata.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    candidate = (
        first_loaded[
            0
        ].clone_for_update()
    )

    second_metadata = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=first_loaded[0],
    )

    second_manifest = json.loads(
        (
            tmp_path
            / second_metadata.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        first_manifest[
            "sources"
        ]
        == second_manifest[
            "sources"
        ]
    )

    def unexpected_revalidation(
        source_slice,
    ):
        raise AssertionError(
            "revision churn revalidated unchanged lineage chunk"
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        unexpected_revalidation,
    )

    second_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert second_loaded is not None
    assert second_loaded[1] == second_metadata

    cache_after = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    assert cache_after == cache_before

    assert "revision" not in cache_after
    assert "state_id" not in cache_after
    assert (
        "lineage_manifest_file"
        not in cache_after
    )
    assert (
        "manifest_sha256"
        not in cache_after
    )

def test_split_lineage_validation_cache_revalidates_only_changed_chunk(
    tmp_path,
    monkeypatch,
):
    import json
    from dataclasses import replace

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert first_loaded is not None

    first_state = first_loaded[0]

    candidate = first_state.clone_for_update()

    previous_b = (
        candidate.lineage_facts_by_source[
            "pkg/b.py"
        ]
    )

    candidate.lineage_facts_by_source[
        "pkg/b.py"
    ] = replace(
        previous_b,
        manifest=replace(
            previous_b.manifest,
            source_fingerprint=(
                "source-1-next"
            ),
        ),
    )

    second_metadata = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=first_state,
    )

    original_revalidate = (
        store._revalidate_lineage_slice
    )
    calls = []

    def counting_revalidation(
        source_slice,
    ):
        calls.append(
            source_slice.manifest.source_key
        )
        return original_revalidate(
            source_slice
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        counting_revalidation,
    )

    second_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert second_loaded is not None
    assert second_loaded[1] == second_metadata

    assert calls == [
        "pkg/b.py",
    ]

    cache_path = (
        tmp_path
        / store._LINEAGE_VALIDATION_CACHE_NAME
    )

    refreshed_cache = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        refreshed_cache[
            "chunks"
        ][
            "pkg/b.py"
        ][
            "source_fingerprint"
        ]
        == "source-1-next"
    )

    def unexpected_revalidation(
        source_slice,
    ):
        raise AssertionError(
            "refreshed per-chunk trust performed deep revalidation"
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        unexpected_revalidation,
    )

    third_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert third_loaded is not None
    assert third_loaded[1] == second_metadata

def test_split_lineage_validation_cache_chunk_mutation_falls_back_and_fails_closed(
    tmp_path,
    monkeypatch,
):
    import json
    import pickle

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        repo_id="repo-test",
        root_path=str(tmp_path),
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert first_loaded is not None

    cache_path = (
        tmp_path
        / store._LINEAGE_VALIDATION_CACHE_NAME
    )

    assert cache_path.is_file()

    cache_payload = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    lineage_manifest = json.loads(
        (
            tmp_path
            / metadata.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    chunk_file = (
        lineage_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    chunk_path = (
        tmp_path
        / chunk_file
    )

    cached_sha256 = (
        cache_payload[
            "chunks"
        ][
            "pkg/a.py"
        ][
            "sha256"
        ]
    )

    source_slice = (
        first_loaded[
            0
        ].lineage_facts_by_source[
            "pkg/a.py"
        ]
    )

    object.__setattr__(
        source_slice.manifest,
        "flow_count",
        source_slice.manifest.flow_count + 1,
    )

    chunk_path.write_bytes(
        pickle.dumps(
            source_slice
        )
    )

    assert (
        store._sha256_bytes(
            chunk_path.read_bytes()
        )
        != cached_sha256
    )

    original_revalidate = (
        store._revalidate_lineage_slice
    )
    calls = []

    def counting_revalidation(
        candidate,
    ):
        calls.append(
            candidate.manifest.source_key
        )
        return original_revalidate(
            candidate
        )

    monkeypatch.setattr(
        store,
        "_revalidate_lineage_slice",
        counting_revalidation,
    )

    second_loaded = load_snapshot(
        tmp_path,
        "sid",
        expected_repo_id="repo-test",
        expected_root_path=str(tmp_path),
    )

    assert second_loaded is None

    assert calls == [
        "pkg/a.py",
    ]

    unchanged_cache = json.loads(
        cache_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        unchanged_cache[
            "chunks"
        ][
            "pkg/a.py"
        ][
            "sha256"
        ]
        == cached_sha256
    )


def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
    tmp_path,
):
    import json
    from dataclasses import replace

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    candidate = state.clone_for_update()

    previous_b = (
        candidate.lineage_facts_by_source[
            "pkg/b.py"
        ]
    )

    candidate.lineage_facts_by_source[
        "pkg/b.py"
    ] = replace(
        previous_b,
        manifest=replace(
            previous_b.manifest,
            source_fingerprint=(
                "source-1-next"
            ),
        ),
    )

    second = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=state,
    )

    second_manifest = json.loads(
        (
            tmp_path
            / second.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
        == first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/b.py"
        ][
            "file"
        ]
        != first_manifest[
            "sources"
        ][
            "pkg/b.py"
        ][
            "file"
        ]
    )

    assert len(
        list(
            tmp_path.glob(
                "lineage_source.r2.*.pkl"
            )
        )
    ) == 1

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "sid",
        )
    )

    assert loaded_metadata == second

    assert (
        loaded_state.lineage_facts_by_source
        == candidate.lineage_facts_by_source
    )


def test_exact_split_lineage_does_not_reuse_equal_distinct_slice(
    tmp_path,
):
    import json
    from dataclasses import replace

    state = _split_lineage_test_state(
        "pkg/a.py"
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    candidate = state.clone_for_update()

    previous_slice = (
        state.lineage_facts_by_source[
            "pkg/a.py"
        ]
    )

    equal_distinct = replace(
        previous_slice
    )

    assert (
        equal_distinct
        == previous_slice
    )

    assert (
        equal_distinct
        is not previous_slice
    )

    candidate.lineage_facts_by_source[
        "pkg/a.py"
    ] = equal_distinct

    second = save_snapshot(
        candidate,
        tmp_path,
        "sid",
        exact_revision=2,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 2,
            },
            "files": {},
        },
        previous_state=state,
    )

    second_manifest = json.loads(
        (
            tmp_path
            / second.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        second_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
        != first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    assert len(
        list(
            tmp_path.glob(
                "lineage_source.r2.*.pkl"
            )
        )
    ) == 1


def test_split_lineage_reuse_failure_preserves_previous_chunk(
    tmp_path,
    monkeypatch,
):
    import json
    from dataclasses import replace

    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    first = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    first_manifest = json.loads(
        (
            tmp_path
            / first.lineage_manifest_file
        ).read_text(
            encoding="utf-8"
        )
    )

    reused_chunk = (
        tmp_path
        / first_manifest[
            "sources"
        ][
            "pkg/a.py"
        ][
            "file"
        ]
    )

    candidate = state.clone_for_update()

    previous_b = (
        candidate.lineage_facts_by_source[
            "pkg/b.py"
        ]
    )

    candidate.lineage_facts_by_source[
        "pkg/b.py"
    ] = replace(
        previous_b,
        manifest=replace(
            previous_b.manifest,
            source_fingerprint=(
                "source-1-next"
            ),
        ),
    )

    original_replace = store.os.replace

    def fail_metadata_replace(
        source,
        target,
    ):
        if (
            Path(
                target
            ).name
            == "engine_state.meta.json"
        ):
            raise RuntimeError(
                "synthetic metadata commit failure"
            )

        return original_replace(
            source,
            target,
        )

    monkeypatch.setattr(
        store.os,
        "replace",
        fail_metadata_replace,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "^synthetic metadata commit failure$"
        ),
    ):
        save_snapshot(
            candidate,
            tmp_path,
            "sid",
            exact_revision=2,
            file_state_payload={
                "_meta": {
                    "state_id": "sid",
                    "revision": 2,
                },
                "files": {},
            },
            previous_state=state,
        )

    assert reused_chunk.is_file()

    assert (
        read_metadata(
            tmp_path
        ).revision
        == 1
    )

    assert not list(
        tmp_path.glob(
            "engine_state.r2.*.pkl"
        )
    )

    assert not list(
        tmp_path.glob(
            "file_state.r2.*.json"
        )
    )

    assert not list(
        tmp_path.glob(
            "lineage_manifest.r2.*.json"
        )
    )

    assert not list(
        tmp_path.glob(
            "lineage_source.r2.*.pkl"
        )
    )


@pytest.mark.parametrize(
    "failure",
    [
        "missing_chunk",
        "manifest_revision",
        "corrupt_chunk",
    ],
)
def test_split_lineage_corruption_fails_closed(
    tmp_path,
    failure,
):
    import json

    state = _split_lineage_test_state(
        "pkg/a.py"
    )

    metadata = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    manifest_path = (
        tmp_path
        / metadata.lineage_manifest_file
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    entry = manifest[
        "sources"
    ][
        "pkg/a.py"
    ]

    chunk_path = (
        tmp_path
        / entry[
            "file"
        ]
    )

    if failure == "missing_chunk":
        chunk_path.unlink()

    elif failure == "manifest_revision":
        manifest[
            "revision"
        ] = 2
        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    elif failure == "corrupt_chunk":
        chunk_path.write_bytes(
            b"not-a-pickle"
        )

    assert (
        load_snapshot(
            tmp_path,
            "sid",
        )
        is None
    )


def test_split_lineage_failed_metadata_commit_cleans_new_generation(
    tmp_path,
    monkeypatch,
):
    import contextor.core.live_state.store as store

    state = _split_lineage_test_state(
        "pkg/a.py",
        "pkg/b.py",
    )

    baseline = save_snapshot(
        state,
        tmp_path,
        "sid",
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "sid",
                "revision": 1,
            },
            "files": {},
        },
    )

    candidate = state.clone_for_update()

    original_replace = (
        store.os.replace
    )

    def fail_metadata_replace(
        source,
        target,
    ):
        if (
            Path(
                target
            ).name
            == "engine_state.meta.json"
        ):
            raise RuntimeError(
                "synthetic metadata commit failure"
            )

        return original_replace(
            source,
            target,
        )

    monkeypatch.setattr(
        store.os,
        "replace",
        fail_metadata_replace,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "^synthetic metadata commit failure$"
        ),
    ):
        save_snapshot(
            candidate,
            tmp_path,
            "sid",
            exact_revision=2,
            file_state_payload={
                "_meta": {
                    "state_id": "sid",
                    "revision": 2,
                },
                "files": {},
            },
        )

    assert (
        read_metadata(
            tmp_path
        ).revision
        == baseline.revision
    )

    assert not list(
        tmp_path.glob(
            "engine_state.r2.*.pkl"
        )
    )
    assert not list(
        tmp_path.glob(
            "file_state.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_manifest.r2.*.json"
        )
    )
    assert not list(
        tmp_path.glob(
            "lineage_source.r2.*.pkl"
        )
    )


def test_schema_12_monolithic_snapshot_remains_loadable(
    tmp_path,
):
    import json
    import pickle

    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )

    state = RepositoryAnalysisState()
    state.state_id = "legacy-sid"
    state.revision = 1

    state_file = (
        "engine_state.r1.legacy.pkl"
    )

    metadata = {
        "schema_version": "1.2",
        "state_id": "legacy-sid",
        "revision": 1,
        "writer": "legacy",
        "repo_id": "",
        "root_path": "",
        "state_file": state_file,
        "file_state_file": "",
    }

    with (
        tmp_path
        / state_file
    ).open("wb") as stream:
        pickle.dump(
            {
                "metadata": metadata,
                "state": state,
            },
            stream,
        )

    (
        tmp_path
        / "engine_state.meta.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    loaded_state, loaded_metadata = (
        load_snapshot(
            tmp_path,
            "legacy-sid",
        )
    )

    assert (
        loaded_metadata.schema_version
        == "1.2"
    )
    assert (
        loaded_metadata.lineage_manifest_file
        == ""
    )
    assert (
        loaded_state.state_id
        == "legacy-sid"
    )
    assert (
        loaded_state.revision
        == 1
    )


def test_build_payload_is_side_effect_free(tmp_path):
    manager = FileStateManager(str(tmp_path))
    manager.state_id = "sid-r1"
    manager.revision = 1
    payload = manager.build_payload("sid-r2", 2)
    assert manager.state_id == "sid-r1"
    assert manager.revision == 1
    assert payload["_meta"] == {"state_id": "sid-r2", "revision": 2}


@pytest.mark.parametrize("failure", ["missing", "invalid", "oserror"])
def test_referenced_filestate_generation_fail_closed_without_legacy_fallback(tmp_path, monkeypatch, failure):
    import builtins
    import json

    manager = FileStateManager(str(tmp_path))
    manager._state = {}
    manager.save("sid", revision=1)
    metadata = {
        "schema_version": "1.2",
        "state_id": "sid",
        "revision": 2,
        "file_state_file": "file_state.r2.test.json",
    }
    (tmp_path / "engine_state.meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    (tmp_path / "file_state.json").write_text(json.dumps({"files": {"legacy.py": {"size": 1}}}), encoding="utf-8")
    referenced = tmp_path / "file_state.r2.test.json"
    if failure == "invalid":
        referenced.write_text("{not-json", encoding="utf-8")
    elif failure == "oserror":
        original_open = builtins.open
        def raising_open(path, *args, **kwargs):
            if str(path).endswith("file_state.r2.test.json"):
                raise OSError("synthetic read failure")
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(builtins, "open", raising_open)
    reloaded = FileStateManager(str(tmp_path))
    assert reloaded._state == {}
    assert reloaded.revision is None


def test_referenced_filestate_without_meta_fails_closed(tmp_path):
    import json

    (tmp_path / "engine_state.meta.json").write_text(
        json.dumps({"state_id": "sid", "revision": 2, "file_state_file": "file_state.r2.json"}),
        encoding="utf-8",
    )
    (tmp_path / "file_state.r2.json").write_text(
        json.dumps({"files": {"current.py": {"size": 4}}}),
        encoding="utf-8",
    )
    manager = FileStateManager(str(tmp_path))
    assert manager._state == {}
    assert manager.state_id == ""
    assert manager.revision is None


def test_legacy_filestate_without_meta_loads_entries_but_remains_unverified(tmp_path):
    import json

    (tmp_path / "engine_state.meta.json").write_text(
        json.dumps({"state_id": "sid", "revision": 2}),
        encoding="utf-8",
    )
    (tmp_path / "file_state.json").write_text(
        json.dumps({"legacy.py": {"size": 4}}),
        encoding="utf-8",
    )
    manager = FileStateManager(str(tmp_path))
    assert "legacy.py" in manager._state
    assert manager.state_id == ""
    assert manager.revision is None


def test_snapshot_rejects_a_different_state_identity(tmp_path):
    save_snapshot(SimpleNamespace(value=1), tmp_path, "current")

    assert load_snapshot(tmp_path, "stale") is None


def test_snapshot_rejects_wrong_repository_identity_or_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    save_snapshot(
        {"value": 1},
        tmp_path / "cache",
        "current",
        repo_id="ctx_12345678",
        root_path=str(repo),
    )

    assert load_snapshot(
        tmp_path / "cache",
        expected_repo_id="ctx_87654321",
        expected_root_path=str(repo),
    ) is None
    assert load_snapshot(
        tmp_path / "cache",
        expected_repo_id="ctx_12345678",
        expected_root_path=str(tmp_path / "other"),
    ) is None


def test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source(
    tmp_path, monkeypatch
):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    legacy = legacy_repo_cache_dir(repo)
    legacy_metadata = save_snapshot(
        {"value": 7}, legacy, "legacy-state", writer="desktop"
    )
    legacy_file_state = legacy / "file_state.json"
    legacy_file_state.write_text(
        json.dumps({"legacy.py": {"size": 4}}, indent=2),
        encoding="utf-8",
    )
    legacy_file_state_bytes = legacy_file_state.read_bytes()
    registry = PersistentIdentityRegistry(str(repo))

    target = migrate_legacy_snapshot(repo)
    loaded = load_snapshot(
        target,
        expected_repo_id=registry.repo_id,
        expected_root_path=str(repo),
    )

    assert target == repo_cache_dir(repo)
    assert loaded is not None and loaded[0] == {"value": 7}
    assert loaded[1].repo_id == registry.repo_id
    assert loaded[1].state_id == "legacy-state"
    assert loaded[1].revision == legacy_metadata.revision + 1
    assert (target / "file_state.json").is_file()
    assert (target / "file_state.json").read_bytes() == legacy_file_state_bytes
    migrated_file_state = FileStateManager(str(target))
    assert "legacy.py" in migrated_file_state._state
    assert migrated_file_state.baseline_status == "untrusted"
    assert (legacy / "engine_state.pkl").is_file()


def _migration_race_full_analysis_holder(
    repo_text, cache_text, lease_held, release_lease, results
):
    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
    from contextor.core.analysis.full_analysis_coordinator import (
        acquire_full_analysis,
        release_full_analysis,
    )

    lease = None
    try:
        lease = acquire_full_analysis(
            repo_text,
            owner="migration_race_full_writer",
            writer_kind="full_analysis",
            timeout=5.0,
        )
        lease_held.set()
        if not release_lease.wait(15):
            raise TimeoutError("full-analysis lease hold expired")
        results.put({"worker": "lease", "status": "released"})
    except BaseException as exc:
        results.put({"worker": "lease", "status": "error", "error": repr(exc)})
    finally:
        if lease is not None:
            release_full_analysis(lease)


def _migration_race_migrate_worker(
    repo_text,
    cache_text,
    migration_started,
    snapshot_write_entered,
    allow_snapshot_write,
    results,
):
    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
    import contextor.core.live_state.store as store

    real_save_snapshot = store.save_snapshot

    def observe_snapshot_write(*args, **kwargs):
        snapshot_write_entered.set()
        if not allow_snapshot_write.wait(15):
            raise TimeoutError("migration snapshot write hold expired")
        return real_save_snapshot(*args, **kwargs)

    store.save_snapshot = observe_snapshot_write
    try:
        migration_started.set()
        target = store.migrate_legacy_snapshot(repo_text)
        results.put({"worker": "migration", "status": "completed", "target": str(target)})
    except BaseException as exc:
        results.put({"worker": "migration", "status": "error", "error": repr(exc)})
    finally:
        store.save_snapshot = real_save_snapshot


def test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held(
    tmp_path, monkeypatch
):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    identity = PersistentIdentityRegistry(str(repo))
    assert identity.repo_id

    legacy = legacy_repo_cache_dir(repo)
    legacy_metadata = save_snapshot(
        {"value": 7}, legacy, "legacy-state", writer="desktop"
    )
    assert load_snapshot(legacy) is not None
    target = repo_cache_dir(repo)
    assert read_metadata(target) is None

    context = multiprocessing.get_context("spawn")
    lease_held = context.Event()
    release_lease = context.Event()
    migration_started = context.Event()
    snapshot_write_entered = context.Event()
    allow_snapshot_write = context.Event()
    results = context.Queue()
    holder = context.Process(
        target=_migration_race_full_analysis_holder,
        args=(str(repo), str(cache_root), lease_held, release_lease, results),
    )
    migrator = context.Process(
        target=_migration_race_migrate_worker,
        args=(
            str(repo),
            str(cache_root),
            migration_started,
            snapshot_write_entered,
            allow_snapshot_write,
            results,
        ),
    )
    processes = (holder, migrator)
    early_snapshot_write = False
    migration_reached_write = False
    worker_results = []
    try:
        holder.start()
        assert lease_held.wait(5), "Process A did not acquire full_analysis.lock"

        migrator.start()
        assert migration_started.wait(5), "Process B did not start legacy migration"
        early_snapshot_write = snapshot_write_entered.wait(1.0)

        # Release both explicit holds only after recording whether the real
        # migration writer boundary was entered while Process A owned the lease.
        release_lease.set()
        allow_snapshot_write.set()
        migration_reached_write = snapshot_write_entered.wait(5)

        for process in processes:
            process.join(timeout=10)
        worker_results = [results.get(timeout=2) for _ in range(2)]
    finally:
        release_lease.set()
        allow_snapshot_write.set()
        for process in processes:
            if process.pid is not None:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
        results.close()
        results.join_thread()

    assert migration_reached_write, f"migration did not reach save_snapshot: {worker_results}"
    assert all(not process.is_alive() for process in processes)
    assert all(process.exitcode == 0 for process in processes), worker_results
    assert {result["status"] for result in worker_results} == {"released", "completed"}, worker_results
    assert legacy_metadata.revision == 1
    assert not early_snapshot_write, (
        "migration entered the real save_snapshot boundary while another process "
        "held the repository full_analysis.lock"
    )


def test_migration_does_not_publish_legacy_filestate_after_newer_generation_commit(
    tmp_path, monkeypatch
):
    import contextor.core.live_state.store as store

    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    identity = read_repository_identity(repo)
    assert identity is not None and identity.repo_id == registry.repo_id

    legacy = legacy_repo_cache_dir(repo)
    target = repo_cache_dir(repo)
    legacy_metadata = save_snapshot(
        {"value": "legacy"}, legacy, "legacy-state", writer="desktop"
    )
    legacy_file_state = legacy / "file_state.json"
    legacy_file_state.write_text(
        json.dumps(
            {
                "_meta": {
                    "state_id": legacy_metadata.state_id,
                    "revision": legacy_metadata.revision,
                },
                "files": {"legacy.py": {"size": 6}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    legacy_file_state_bytes = legacy_file_state.read_bytes()

    real_store_save = store.save_snapshot
    real_copy2 = store.shutil.copy2
    migration_snapshot_returned = threading.Event()
    resume_migration = threading.Event()
    observations = {"order": [], "copy": []}
    migration_outcome = []

    def pause_after_migration_snapshot_save(*args, **kwargs):
        metadata = real_store_save(*args, **kwargs)
        if threading.current_thread().name == "legacy-migration":
            observations["migration_metadata"] = metadata
            observations["order"].append("migration_snapshot_saved")
            migration_snapshot_returned.set()
            if not resume_migration.wait(10):
                raise TimeoutError("migration resume hold expired")
        return metadata

    def observe_legacy_file_state_copy(src, dst, *args, **kwargs):
        result = real_copy2(src, dst, *args, **kwargs)
        observations["copy"].append(
            {"src": str(src), "dst": str(dst), "bytes": Path(dst).read_bytes()}
        )
        observations["order"].append("legacy_file_state_copy_committed")
        return result

    monkeypatch.setattr(store, "save_snapshot", pause_after_migration_snapshot_save)
    monkeypatch.setattr(store.shutil, "copy2", observe_legacy_file_state_copy)

    def run_migration():
        try:
            migration_outcome.append(migrate_legacy_snapshot(repo))
        except BaseException as exc:
            migration_outcome.append(exc)

    migration = threading.Thread(target=run_migration, name="legacy-migration")
    try:
        migration.start()
        assert migration_snapshot_returned.wait(5), "migration did not return from snapshot save"

        migration_metadata = read_metadata(target)
        assert migration_metadata is not None
        assert migration_metadata.revision == legacy_metadata.revision + 1
        assert migration_metadata.state_id == legacy_metadata.state_id
        assert migration_metadata.file_state_file == ""
        assert not (target / "file_state.json").exists()

        next_revision = migration_metadata.revision + 1
        new_file_state_payload = {
            "_meta": {"state_id": migration_metadata.state_id, "revision": next_revision},
            "files": {"current.py": {"size": 11}},
        }
        newer_metadata = save_snapshot(
            {"value": "newer"},
            target,
            migration_metadata.state_id,
            writer="competing_snapshot_writer",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
            exact_revision=next_revision,
            file_state_payload=new_file_state_payload,
        )
        observations["order"].append("newer_generation_committed")
        newer_metadata_bytes = (target / "engine_state.meta.json").read_bytes()
        newer_file_state_path = target / newer_metadata.file_state_file
        newer_file_state_bytes = newer_file_state_path.read_bytes()

        resume_migration.set()
        migration.join(timeout=10)
    finally:
        resume_migration.set()
        migration.join(timeout=5)

    assert not migration.is_alive(), "migration thread did not terminate"
    assert len(migration_outcome) == 1 and isinstance(migration_outcome[0], Path), migration_outcome
    assert observations["order"].index("newer_generation_committed") < (
        observations["order"].index("legacy_file_state_copy_committed")
        if "legacy_file_state_copy_committed" in observations["order"]
        else len(observations["order"])
    )

    final_metadata = read_metadata(target)
    assert final_metadata == newer_metadata
    assert final_metadata.revision == next_revision
    assert final_metadata.state_id == legacy_metadata.state_id
    assert final_metadata.file_state_file == newer_metadata.file_state_file
    assert (target / "engine_state.meta.json").read_bytes() == newer_metadata_bytes
    assert newer_file_state_path.read_bytes() == newer_file_state_bytes
    assert legacy_file_state_bytes == legacy_file_state.read_bytes()

    legacy_target_file_state = target / "file_state.json"
    assert legacy_target_file_state.is_file()
    assert legacy_target_file_state.read_bytes() == legacy_file_state_bytes
    assert observations["copy"] == [
        {
            "src": str(legacy_file_state),
            "dst": str(legacy_target_file_state),
            "bytes": legacy_file_state_bytes,
        }
    ]

    loaded = load_snapshot(
        target,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    assert loaded is not None and loaded[0]["value"] == "newer"
    loaded_file_state = FileStateManager(str(target))
    assert loaded_file_state.state_id == newer_metadata.state_id
    assert loaded_file_state.revision == newer_metadata.revision
    assert loaded_file_state.baseline_status == "trusted"
    assert loaded_file_state._state["current.py"].size == 11

    assert "legacy_file_state_copy_committed" not in observations["order"], (
        "migration published the stale unversioned legacy FileState after a newer "
        f"generation committed; order={observations['order']}; "
        f"metadata_file_state={final_metadata.file_state_file!r}; "
        "the metadata-referenced FileState consumer remained trusted"
    )


def test_migration_does_not_write_when_valid_target_metadata_exists(
    tmp_path, monkeypatch
):
    import contextor.core.live_state.store as store

    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    identity = read_repository_identity(repo)
    if identity is None:
        registry = PersistentIdentityRegistry(str(repo))
        identity = read_repository_identity(repo)
        assert identity is not None and identity.repo_id == registry.repo_id

    legacy = legacy_repo_cache_dir(repo)
    target = repo_cache_dir(repo)
    save_snapshot({"value": "legacy"}, legacy, "legacy-state", writer="desktop")
    target_metadata = save_snapshot(
        {"value": "already-current"},
        target,
        "target-state",
        writer="existing-target",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
    )
    metadata_bytes = (target / "engine_state.meta.json").read_bytes()
    state_bytes = (target / "engine_state.pkl").read_bytes()

    def forbidden_migration_write(*_args, **_kwargs):
        pytest.fail("migration wrote despite valid target metadata")

    monkeypatch.setattr(store, "save_snapshot", forbidden_migration_write)
    assert migrate_legacy_snapshot(repo) == target
    assert read_metadata(target) == target_metadata
    assert (target / "engine_state.meta.json").read_bytes() == metadata_bytes
    assert (target / "engine_state.pkl").read_bytes() == state_bytes
    assert not (target / "file_state.json").exists()


def test_concurrent_writers_publish_complete_monotonic_snapshots(tmp_path):
    def publish(value):
        return save_snapshot({"value": value}, tmp_path, "same", writer=str(value)).revision

    with ThreadPoolExecutor(max_workers=4) as pool:
        revisions = sorted(pool.map(publish, range(8)))

    state, metadata = load_snapshot(tmp_path, "same")
    assert revisions == list(range(1, 9))
    assert metadata.revision == 8
    assert state["value"] in range(8)


def test_mcp_and_desktop_resolve_the_same_repository_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("contextor.core.paths.app_cache_dir", lambda: tmp_path)

    assert analysis_jobs._mcp_cache_root(tmp_path / "repo") == tmp_path


def _snapshot_lock_simultaneous_worker(lock_path, start, results):
    import contextor.core.live_state.store as store

    start.wait(10)

    try:
        fd = store._acquire_lock(
            Path(lock_path),
            timeout=0.3,
        )
    except TimeoutError:
        results.put("timeout")
        return
    except BaseException as exc:
        results.put(f"unexpected:{type(exc).__name__}:{exc}")
        return

    try:
        time.sleep(0.6)
        results.put("acquired")
    finally:
        store._release_lock(fd)


def test_snapshot_lock_concurrent_initial_creation(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "engine_state.lock"

    assert not lock_path.exists()

    start = ctx.Event()
    results = ctx.Queue()

    def verify(result_list):
        assert sorted(result_list) == ["acquired", "timeout"]
        assert lock_path.is_file()

    processes = [
        ctx.Process(
            target=_snapshot_lock_simultaneous_worker,
            args=(str(lock_path), start, results),
        )
        for _ in range(2)
    ]

    for process in processes:
        process.start()

    try:
        start.set()
        outcomes = [
            results.get(timeout=15)
            for _ in processes
        ]
        for process in processes:
            process.join(10)
        assert all(process.exitcode == 0 for process in processes)
        verify(outcomes)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
