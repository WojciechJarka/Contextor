"""Unit and integration boundaries for the shared canonical LIVE snapshot store."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.core.live_state import load_snapshot, read_metadata, save_snapshot
from contextor.core.paths import app_cache_dir

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

    assert mcp_server._mcp_cache_root(tmp_path / "repo") == tmp_path
