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
