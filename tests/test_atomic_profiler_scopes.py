import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.profiling.atomic import AtomicRecorder
from contextor.core.profiling.scopes import reports, live_ipc, snapshot_metadata
from contextor.core.live_state.store import LiveStateMetadata


def _recorder(scope):
    return AtomicRecorder(scope, frozenset(), 0)


@pytest.mark.parametrize("raw_revision,valid", [
    (True, False), (False, False), ("1", False), (1.0, False),
    (None, False), (0, False), (-1, False), (1, True), (2, True),
])
def test_raw_revision_validation(tmp_path, monkeypatch, raw_revision, valid):
    root = tmp_path / "repo"
    root.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    metadata = {
        "state_id": "state-1", "revision": raw_revision, "repo_id": "ctx_test",
        "root_path": str(root), "schema_version": "1.4",
    }
    (cache / "engine_state.meta.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(snapshot_metadata, "read_repository_identity", lambda _: SimpleNamespace(repo_id="ctx_test"))
    monkeypatch.setattr(snapshot_metadata, "repo_cache_dir", lambda _: cache)
    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
        state_id="state-1", revision=int(raw_revision or 0) if raw_revision is not None else 0,
        repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
    result = snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))
    assert (result["status"] == "ok") is valid
    assert not (cache / "lineage_validation_cache.json").exists()
    assert sorted(path.name for path in cache.iterdir()) == ["engine_state.meta.json"]


def test_metadata_mismatch_and_replacement(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    path = cache / "engine_state.meta.json"
    raw = {"state_id": "a", "revision": 1, "repo_id": "ctx_test",
           "root_path": str(root), "schema_version": "1.4"}
    path.write_text(json.dumps(raw))
    monkeypatch.setattr(snapshot_metadata, "read_repository_identity", lambda _: SimpleNamespace(repo_id="ctx_test"))
    monkeypatch.setattr(snapshot_metadata, "repo_cache_dir", lambda _: cache)
    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
        state_id="different", revision=1, repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
    assert snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))["status"] == "invalid_identity"
    monkeypatch.setattr(snapshot_metadata, "read_metadata", lambda _: LiveStateMetadata(
        state_id="a", revision=1, repo_id="ctx_test", root_path=str(root), schema_version="1.4", writer="legacy"))
    original = Path.read_bytes
    reads = [0]
    def changing(self):
        if self == path:
            reads[0] += 1
            if reads[0] == 2:
                return b'{"changed":true}'
        return original(self)
    monkeypatch.setattr(Path, "read_bytes", changing)
    assert snapshot_metadata.run_scope(root, _recorder("snapshot.metadata"))["status"] == "changed_during_read"


def test_reports_missing_and_invalid(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(reports, "output_dir", lambda: out)
    assert reports.run_scope(root, _recorder("reports.summary"))["status"] == "unavailable"
    report = out / "repo_summary.json"
    report.write_text("{invalid")
    assert reports.run_scope(root, _recorder("reports.summary"))["status"] == "invalid_data"
    report.write_text('{"secret": "must-not-return"}')
    result = reports.run_scope(root, _recorder("reports.summary"))
    assert result["status"] == "ok"
    assert "secret" not in str(result)


def test_live_uses_existing_connect_and_only_ping(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(live_ipc, "connect", lambda root: calls.append("connect") or SimpleNamespace(
        ping=lambda: calls.append("ping") or {"status": "ok", "revision": 2}))
    result = live_ipc.run_scope(tmp_path, _recorder("live.ping"))
    assert calls == ["connect", "ping"]
    assert result["observed_revision"] == 2
    monkeypatch.setattr(live_ipc, "connect", lambda root: None)
    assert live_ipc.run_scope(tmp_path, _recorder("live.ping"))["status"] == "unavailable"
