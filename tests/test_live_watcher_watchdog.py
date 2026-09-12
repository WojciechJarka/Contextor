from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from contextor.core.live_state import CanonicalLiveServer, DesktopLiveWatcher, LiveStateClient
import contextor.core.live_state.watcher as watcher_module


pytestmark = pytest.mark.live


def _event(path: str, *, directory: bool = False, dest_path: str | None = None):
    values = {"is_directory": directory, "src_path": path}
    if dest_path is not None:
        values["dest_path"] = dest_path
    return SimpleNamespace(**values)


def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
    repo = tmp_path / "repo"
    repo.mkdir()
    updates = []

    class Client:
        def snapshot(self):
            return {
                "status": "ok",
                "state": SimpleNamespace(modules={}, revision=1, state_id="sid"),
            }

        def ping(self):
            return {"status": "ok", "available": True, "revision": 1}

        def submit_update_file(self, path, **kwargs):
            updates.append((path, kwargs))
            return {
                "status": "accepted",
                "accepted": True,
                "job_id": str(len(updates)),
            }

        def mutation_status(self, job_id):
            path, _kwargs = updates[int(job_id) - 1]
            return {
                "status": "ok",
                "state": "completed",
                "response": {
                    "status": "ok",
                    "revision": int(job_id) + 1,
                    "seq": int(job_id),
                    "result": SimpleNamespace(status=result_status, file_path=path),
                },
            }

    client = Client()
    watcher = DesktopLiveWatcher(repo, client, interval=0)
    watcher._startup_requires_resync = False
    watcher._startup_pending = []
    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
        has_changed=lambda _path: True,
        tracked_paths=lambda: {item[0] for item in updates},
        revision=1,
        state_id="sid",
    )
    return repo, watcher, client, updates


class _FakeObserver:
    def __init__(self, records, *, fail_start=False):
        self.records = records
        self.fail_start = fail_start
        self.alive = True

    def schedule(self, handler, path, recursive=False):
        self.records.append(("schedule", handler, path, recursive))

    def start(self):
        self.records.append(("start",))
        if self.fail_start:
            self.alive = False
            raise OSError("native observer unavailable")

    def is_alive(self):
        return self.alive

    def stop(self):
        self.records.append(("stop",))
        self.alive = False

    def join(self, timeout=None):
        self.records.append(("join", timeout))


def test_idle_poll_once_never_scans_repository(tmp_path, monkeypatch):
    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
    monkeypatch.setattr(watcher, "_scan", lambda: (_ for _ in ()).throw(AssertionError("steady-state scan")))

    assert watcher.poll_once() == []


def test_internal_deferred_requeue_does_not_hot_wake(tmp_path):
    repo, watcher, client, _updates = _make_watcher(tmp_path)
    statuses = []
    watcher.on_status = statuses.append
    path = repo / "module.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")
    client.ping = lambda: {"status": "ok", "available": False, "revision": 1}

    watcher._enqueue_path(str(path))

    assert watcher.poll_once() == []
    assert watcher._has_pending_paths() is True
    assert watcher._wake.is_set() is False
    assert statuses == ["LIVE: no snapshot; waiting for analysis"]


def test_duplicate_modify_events_coalesce_to_one_pending_path(tmp_path):
    repo, watcher, _client, _updates = _make_watcher(tmp_path)
    path = str(repo / "module.py")

    watcher._event_handler.on_modified(_event(path))
    watcher._event_handler.on_modified(_event(path))

    assert watcher._drain_pending() == [path]


def test_non_python_ignored_and_excluded_events_are_rejected(tmp_path):
    repo, watcher, _client, _updates = _make_watcher(tmp_path)
    watcher._ignored_dirs = frozenset({"ignored"})
    watcher._excluded_paths = ("excluded.py", "excluded_dir")

    for path in (
        repo / "notes.txt",
        repo / "ignored" / "module.py",
        repo / "excluded.py",
        repo / "excluded_dir" / "module.py",
    ):
        watcher._event_handler.on_modified(_event(str(path)))

    assert watcher._drain_pending() == []


def test_move_enqueues_old_then_new(tmp_path):
    repo, watcher, _client, _updates = _make_watcher(tmp_path)
    old_path = str(repo / "old.py")
    new_path = str(repo / "new.py")

    watcher._event_handler.on_moved(_event(old_path, dest_path=new_path))

    assert watcher._drain_pending() == [old_path, new_path]


def test_event_path_routes_through_queued_client_submission(tmp_path):
    repo, watcher, _client, updates = _make_watcher(tmp_path)
    path = repo / "module.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")
    watcher._enqueue_path(str(path))

    assert watcher.poll_once() == [str(path.resolve())]
    assert updates == [(str(path.resolve()), {"origin": "desktop_watcher", "trace_op": updates[0][1]["trace_op"]})]


def test_delete_event_routes_missing_path_as_delete_candidate(tmp_path):
    repo, watcher, _client, updates = _make_watcher(tmp_path)
    path = repo / "module.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")
    watcher._snapshot[str(path.resolve())] = (1, 10)
    path.unlink()
    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
        has_changed=lambda _path: True,
        tracked_paths=lambda: {str(path.resolve())},
        revision=1,
        state_id="sid",
    )
    watcher._enqueue_path(str(path))

    assert watcher.poll_once() == [str(path.resolve())]
    assert updates[0][0] == str(path.resolve())
    assert str(path.resolve()) not in watcher._snapshot


def test_syntax_error_and_recovery_contract_survives_watchdog_adapter(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "broken.py"
    target.write_text("def broken(:\n", encoding="utf-8")
    results = [
        SimpleNamespace(
            status="SYNTAX_ERROR",
            file_path=str(target),
            error="invalid syntax",
            line_number=1,
            column_number=12,
        ),
        SimpleNamespace(status="RECOVERED", file_path=str(target)),
    ]
    state = SimpleNamespace(revision=0, state_id="sid", modules={})

    def updater(_candidate, path):
        return results.pop(0)

    server = CanonicalLiveServer(state, revision=0, updater=updater)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    statuses = []
    watcher = DesktopLiveWatcher(
        repo,
        LiveStateClient(server.endpoint),
        interval=0,
        on_status=statuses.append,
    )
    watcher._startup_requires_resync = False
    watcher._startup_pending = []
    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
        has_changed=lambda _path: True,
        tracked_paths=lambda: {str(target.resolve())},
        revision=0,
        state_id="sid",
    )

    try:
        watcher._enqueue_path(str(target))
        assert watcher.poll_once() == [str(target.resolve())]

        target.write_text("def repaired():\n    return 1\n", encoding="utf-8")
        watcher._enqueue_path(str(target))
        assert watcher.poll_once() == [str(target.resolve())]

        events = watcher.client.get_events(after_seq=0, limit=None)["events"]
        update_events = [event for event in events if event.get("operation") == "update_file"]
        assert [event["status"] for event in update_events] == ["SYNTAX_ERROR", "RECOVERED"]
        assert all(event["origin"] == "desktop_watcher" for event in update_events)
        assert update_events[0]["line_number"] == 1
        assert update_events[0]["column_number"] == 12
        assert statuses == [
            "Updating LIVE: broken.py",
            "LIVE syntax error: broken.py line 1, column 12: invalid syntax",
            "Updating LIVE: broken.py",
            "LIVE syntax recovery: broken.py",
        ]
    finally:
        server.close()
        thread.join(timeout=2)


def test_native_observer_start_failure_uses_explicit_polling_fallback(tmp_path, monkeypatch):
    records = []
    fallback_records = []
    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records, fail_start=True))
    monkeypatch.setattr(watcher_module, "PollingObserver", lambda timeout: _FakeObserver(fallback_records))
    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
    statuses = []
    watcher.on_status = statuses.append

    try:
        watcher.start()
        assert watcher._using_polling_fallback is True
        assert any("using polling fallback" in message for message in statuses)
        assert fallback_records[0][0] == "schedule"
        assert fallback_records[0][3] is True
    finally:
        watcher.stop()


def test_start_stop_owns_observer_lifecycle(tmp_path, monkeypatch):
    records = []
    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records))
    _repo, watcher, _client, _updates = _make_watcher(tmp_path)

    watcher.start()
    watcher.start()
    watcher.stop()

    assert [record[0] for record in records] == ["schedule", "start", "stop", "join"]
    assert records[0][3] is True
    assert watcher._observer is None
    assert watcher._thread is None


def test_startup_reconciliation_scan_is_not_steady_state_polling(tmp_path, monkeypatch):
    records = []
    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records))
    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
    scan_calls = []
    original_scan = watcher._scan
    monkeypatch.setattr(
        watcher,
        "_scan",
        lambda: (scan_calls.append("scan") or original_scan()),
    )

    try:
        watcher.start()
        assert len(scan_calls) == 1
        assert watcher.poll_once() == []
        assert watcher.poll_once() == []
        assert len(scan_calls) == 1
    finally:
        watcher.stop()
