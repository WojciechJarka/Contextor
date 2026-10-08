import threading
from collections import OrderedDict, deque
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.live_state.watcher import (
    RECOVERY_DEFERRED,
    DesktopLiveWatcher,
    _PendingMutationIntent,
    _WatcherMutationJob,
)
from contextor.ui.gui import ContextorGUI


class _Manager:
    def has_changed(self, path):
        return True

    def tracked_paths(self):
        return []

    def get_current_file_state(self, path, *, compute_hash):
        stat = Path(path).stat()
        return SimpleNamespace(
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            sha256="current-sha256" if compute_hash else None,
        )


class _Client:
    def __init__(self):
        self.revision = 1
        self.submissions = []
        self.mutation_status_calls = []
        self.status_by_job = {}

    def ping(self):
        return {"available": True, "revision": self.revision}

    def snapshot(self):
        return {
            "status": "ok",
            "revision": self.revision,
            "state": SimpleNamespace(
                revision=self.revision,
                state_id="state-id",
                modules={},
            ),
        }

    def mutation_status(self, job_id):
        self.mutation_status_calls.append(job_id)
        return self.status_by_job.get(
            job_id, {"status": "ok", "state": "queued", "job_id": job_id}
        )

    def submit_update_file(self, path, **kwargs):
        self.submissions.append((path, kwargs))
        job_id = f"job-{len(self.submissions)}"
        return {"status": "accepted", "accepted": True, "job_id": job_id}


def _watcher(tmp_path, client=None, *, recovery_admission=None):
    source = tmp_path / "sample.py"
    source.write_text("value = 2\n", encoding="utf-8")
    client = client or _Client()
    watcher = DesktopLiveWatcher.__new__(DesktopLiveWatcher)
    watcher.root = tmp_path.resolve()
    watcher.client = client
    watcher.recovery_admission = recovery_admission
    watcher._pending_lock = threading.Lock()
    watcher._pending_paths = deque()
    watcher._pending_set = set()
    watcher._wake = threading.Event()
    watcher._snapshot = {str(source.resolve()): (0, 0)}
    watcher._startup_pending = []
    watcher._startup_requires_resync = False
    watcher._startup_resync_attempted = False
    watcher._recovery_rebaseline_pending = False
    watcher._pending_intents = {}
    watcher._ambiguous_updates = set()
    watcher._inflight_updates = OrderedDict()
    watcher._excluded_paths = ()
    watcher._ignored_dirs = frozenset()
    watcher._using_polling_fallback = False
    watcher.interval = 0.01
    watcher.on_status = lambda *_args, **_kwargs: None
    watcher.on_reconnect = None
    watcher.on_resync = None
    watcher.owner_pid = None
    watcher.owner_token = None
    watcher.desktop_instance_id = None
    watcher._trusted_file_state = lambda _snapshot=None: _Manager()
    watcher._candidate_requires_update = (
        lambda _path, _current, _snapshot, _manager: True
    )
    watcher._scan = lambda: {
        str(source.resolve()): (
            source.stat().st_mtime_ns,
            source.stat().st_size,
        )
    }
    watcher._startup_reconciliation_paths = lambda _current: []
    return watcher, source


def test_recovery_preserves_pending_paths_intents_ambiguity_and_startup_work(
    tmp_path,
):
    active = True
    client = _Client()

    def admission(action):
        return RECOVERY_DEFERRED if active else action()

    watcher, source = _watcher(
        tmp_path, client, recovery_admission=admission
    )
    path = str(source.resolve())
    watcher._enqueue_path(path)
    watcher._startup_pending = [path]
    intent = _PendingMutationIntent(
        "intent-1", path, "trace-1", (1, 1), 1.0, "sha"
    )
    watcher._pending_intents[path] = intent
    watcher._ambiguous_updates.add(path)
    original_scan = watcher._scan
    watcher._scan = lambda: pytest.fail("blocked poll must not rescan")

    assert watcher.poll_once() == []
    assert list(watcher._pending_paths) == [path]
    assert watcher._startup_pending == [path]
    assert watcher._pending_intents[path] is intent
    assert path in watcher._ambiguous_updates
    assert client.submissions == []

    watcher._scan = original_scan


def test_inflight_status_reconciles_during_recovery_without_trusting_baseline(
    tmp_path,
):
    client = _Client()
    active = True
    watcher, source = _watcher(
        tmp_path,
        client,
        recovery_admission=lambda action: (
            RECOVERY_DEFERRED if active else action()
        ),
    )
    path = str(source.resolve())
    old_baseline = watcher._snapshot[path]
    watcher._inflight_updates["job-existing"] = _WatcherMutationJob(
        "job-existing", path, "trace", "idem", old_baseline, 1.0, "sha"
    )
    client.status_by_job["job-existing"] = {
        "status": "ok",
        "state": "completed",
        "response": {
            "status": "ok",
            "revision": 2,
            "seq": 3,
            "result": SimpleNamespace(status="UPDATED"),
        },
    }

    watcher.poll_once()

    assert client.mutation_status_calls == ["job-existing"]
    assert "job-existing" not in watcher._inflight_updates
    assert watcher._snapshot[path] == old_baseline
    assert list(watcher._pending_paths) == [path]
    assert client.submissions == []


def test_mid_poll_recovery_defers_remaining_paths_and_keeps_intent(
    tmp_path,
):
    client = _Client()
    watcher, first = _watcher(tmp_path, client)
    second = tmp_path / "later.py"
    second.write_text("value = 3\n", encoding="utf-8")
    second_path = str(second.resolve())
    watcher._snapshot[second_path] = (0, 0)
    active = False
    first_path = str(first.resolve())

    def admission(action):
        nonlocal active
        if active:
            return RECOVERY_DEFERRED
        result = action()
        if client.submissions:
            active = True
        return result

    watcher.recovery_admission = admission
    watcher._enqueue_path(first_path)
    watcher._enqueue_path(second_path)
    pending_intent = _PendingMutationIntent(
        "intent-2", second_path, "trace-2", (1, 1), 2.0, "sha-2"
    )
    watcher._pending_intents[second_path] = pending_intent

    watcher.poll_once()

    assert len(client.submissions) == 1
    assert client.submissions[0][0] == first_path
    assert watcher._pending_intents[second_path] is pending_intent
    assert second_path in watcher._pending_paths
    assert "job-1" in watcher._inflight_updates


def test_recovery_release_rescans_and_revalidates_against_current_live(
    tmp_path,
):
    client = _Client()
    active = True
    seen_revisions = []

    def admission(action):
        return RECOVERY_DEFERRED if active else action()

    watcher, source = _watcher(
        tmp_path, client, recovery_admission=admission
    )
    path = str(source.resolve())
    watcher._enqueue_path(path)
    watcher._startup_pending = [path]
    watcher._candidate_requires_update = (
        lambda _path, _current, snapshot, _manager: (
            seen_revisions.append(snapshot["revision"]) or True
        )
    )
    watcher.poll_once()
    assert client.submissions == []

    active = False
    client.revision = 2
    watcher.complete_recovery_certificate()
    watcher.poll_once()

    assert seen_revisions == [2]
    assert client.submissions[0][0] == path
    assert not watcher._recovery_rebaseline_pending


@pytest.mark.parametrize(
    "failure",
    ["read_error", "malformed", "stale_revision", "identity_missing", "untrusted"],
)
def test_rebaseline_failure_preserves_work_and_retries(tmp_path, failure):
    client = _Client()
    watcher, source = _watcher(tmp_path, client)
    path = str(source.resolve())
    old_snapshot = dict(watcher._snapshot)
    intent = _PendingMutationIntent(
        "intent-1", path, "trace-1", (1, 1), 1.0, "sha"
    )
    job = _WatcherMutationJob(
        "job-1", path, "trace-1", "intent-1", (1, 1), 1.0, "sha"
    )
    watcher._pending_intents[path] = intent
    watcher._ambiguous_updates.add(path)
    watcher._startup_pending = [path]
    watcher._inflight_updates[job.job_id] = job
    watcher._enqueue_path(path)
    watcher.complete_recovery_certificate()
    healthy_snapshot = client.snapshot

    def failed_snapshot():
        if failure == "read_error":
            raise ConnectionError("snapshot unavailable")
        response = healthy_snapshot()
        if failure == "malformed":
            return {"status": "ok", "revision": client.revision, "state": None}
        if failure == "stale_revision":
            response["state"].revision -= 1
        if failure == "identity_missing":
            response["state"].state_id = ""
        return response

    client.snapshot = failed_snapshot
    if failure == "untrusted":
        watcher._trusted_file_state = lambda _snapshot=None: None
    assert watcher.poll_once() == []
    assert watcher._recovery_rebaseline_pending
    assert watcher._snapshot == old_snapshot
    assert watcher._startup_pending == [path]
    assert watcher._pending_intents[path] is intent
    assert path in watcher._ambiguous_updates
    assert watcher._inflight_updates[job.job_id] is job
    assert list(watcher._pending_paths) == [path]
    assert client.submissions == []
    assert client.mutation_status_calls == []

    client.snapshot = healthy_snapshot
    watcher._trusted_file_state = lambda _snapshot=None: _Manager()
    watcher.poll_once()
    assert not watcher._recovery_rebaseline_pending
    assert client.mutation_status_calls
    assert set(client.mutation_status_calls) == {job.job_id}


def test_rebaseline_queues_change_even_when_old_scan_looks_current(tmp_path):
    client = _Client()
    watcher, source = _watcher(tmp_path, client)
    path = str(source.resolve())
    watcher._snapshot = watcher._scan()
    watcher.complete_recovery_certificate()

    watcher.poll_once()

    assert not watcher._recovery_rebaseline_pending
    assert client.submissions
    assert client.submissions[0][0] == path


def test_gui_admission_serializes_registration_with_submission():
    submission_entered = threading.Event()
    registration_waiting = threading.Event()
    release_submission = threading.Event()
    registration_done = threading.Event()

    class ObservedLock:
        def __init__(self):
            self.inner = threading.Lock()

        def __enter__(self):
            if threading.current_thread().name == "recovery-registration":
                registration_waiting.set()
            self.inner.acquire()
            return self

        def __exit__(self, *_args):
            self.inner.release()

    controller = SimpleNamespace(
        _live_recovery_lock=ObservedLock(),
        _live_recovery_incidents={},
        _live_recovery_generations={},
        _live_recovery_prompt_pending=set(),
        _live_recovery_queue=__import__("queue").Queue(),
        _closing=False,
    )
    admission = ContextorGUI._watcher_recovery_admission(
        controller, str(Path.cwd())
    )

    def submit():
        submission_entered.set()
        assert release_submission.wait(5)
        return "submitted"

    submit_result = []
    submit_thread = threading.Thread(
        target=lambda: submit_result.append(admission(submit)),
        name="watcher-submission",
    )
    submit_thread.start()
    assert submission_entered.wait(2)

    def register():
        ContextorGUI._request_full_analysis_recovery(
            controller, str(Path.cwd()), "test incident"
        )
        registration_done.set()

    registration_thread = threading.Thread(
        target=register, name="recovery-registration"
    )
    registration_thread.start()
    assert registration_waiting.wait(2)
    assert not registration_done.is_set()

    release_submission.set()
    submit_thread.join(2)
    registration_thread.join(2)
    assert not submit_thread.is_alive()
    assert not registration_thread.is_alive()
    assert submit_result == ["submitted"]
    assert registration_done.is_set()
    assert len(controller._live_recovery_incidents) == 1


def test_recovery_admission_does_not_swallow_submission_transport_errors(
    tmp_path,
):
    controller = SimpleNamespace(
        _live_recovery_lock=threading.Lock(),
        _live_recovery_incidents={},
    )
    admission = ContextorGUI._watcher_recovery_admission(
        controller, str(tmp_path)
    )
    with pytest.raises(ConnectionError, match="wire failed"):
        admission(lambda: (_ for _ in ()).throw(ConnectionError("wire failed")))
