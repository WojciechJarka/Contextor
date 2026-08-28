"""Unit and integration boundaries for the shared canonical LIVE snapshot store."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from contextor.mcp import analysis_jobs
from contextor.core.live_state import (
    load_snapshot,
    migrate_legacy_snapshot,
    read_metadata,
    save_snapshot,
    SnapshotRevisionConflict,
)
from contextor.core.paths import app_cache_dir, legacy_repo_cache_dir, repo_cache_dir
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)

pytestmark = pytest.mark.live


def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
    first = save_snapshot({"value": 1}, tmp_path, "state-a", writer="desktop")
    second = save_snapshot({"value": 2}, tmp_path, "state-a", writer="mcp")

    state, metadata = load_snapshot(tmp_path, "state-a")

    assert state == {"value": 2}
    assert (first.revision, second.revision, metadata.revision) == (1, 2, 2)
    assert metadata.writer == "mcp"
    assert read_metadata(tmp_path) == metadata


def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
    import contextor.core.live_state.store as store

    replacements = []
    original_replace = store.os.replace
    monkeypatch.setattr(store.os, "replace", lambda source, target: (replacements.append((source, target)), original_replace(source, target))[1])
    save_snapshot({"value": 1}, tmp_path, "state-a")
    assert replacements[0][1].name == "engine_state.pkl"
    assert replacements[0][0].name != "engine_state.pkl"
    assert replacements[0][0].name.endswith(".tmp")


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
    save_snapshot({"value": 7}, legacy, "legacy-state", writer="desktop")
    (legacy / "file_state.json").write_text('{"files": {}}', encoding="utf-8")
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
    assert (target / "file_state.json").is_file()
    assert (legacy / "engine_state.pkl").is_file()


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
