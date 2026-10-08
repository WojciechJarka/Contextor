"""Focused durable-generation publication contract."""

import copy
from contextlib import contextmanager
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.live_state import ipc as ipc_module
from contextor.core.live_state.ipc import CanonicalLiveServer
from contextor.core.live_state.store import (
    load_snapshot,
    locked_committed_snapshot,
    read_metadata,
    save_snapshot,
)
from contextor.core.repository_identity import ensure_repository_identity


def _hold_snapshot_lock(lock_path, ready, release):
    from contextor.core.live_state.store import _acquire_lock, _release_lock

    fd = _acquire_lock(Path(lock_path))
    try:
        ready.set()
        release.wait(15)
    finally:
        _release_lock(fd)


@pytest.fixture
def durable_harness(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    identity = ensure_repository_identity(repo)[0]
    cache = tmp_path / "cache"
    servers = []

    def commit(revision, *, value=None):
        state = SimpleNamespace(
            state_id="sid",
            revision=revision,
            value=revision if value is None else value,
        )
        metadata = save_snapshot(
            state,
            cache,
            "sid",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
            exact_revision=revision,
            file_state_payload={
                "_meta": {"state_id": "sid", "revision": revision},
                "files": {},
            },
        )
        return state, metadata

    def reader():
        return locked_committed_snapshot(
            cache,
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )

    def server(*, state=None, revision=None, custom_reader=None, retention=100):
        result = CanonicalLiveServer(
            state,
            revision=revision,
            committed_snapshot_reader=reader if custom_reader is None else custom_reader,
            retention=retention,
        )
        servers.append(result)
        return result

    yield SimpleNamespace(
        repo=repo,
        identity=identity,
        cache=cache,
        commit=commit,
        reader=reader,
        server=server,
    )

    for instance in servers:
        instance.close()


def _publish(server, revision, *, state_id="sid", **request_fields):
    return server._dispatch({
        "operation": "publish",
        "state": SimpleNamespace(state_id=state_id, revision=revision),
        **request_fields,
    })


def _unchanged(server):
    return (
        server._state,
        server._revision,
        server._activity_seq,
        copy.deepcopy(server._events),
    )


def _assert_unchanged(server, before):
    assert server._state is before[0]
    assert server._revision == before[1]
    assert server._activity_seq == before[2]
    assert server._events == before[3]


def test_r1_memory_only_publish_keeps_next_revision_behavior():
    server = CanonicalLiveServer(SimpleNamespace(value=0), revision=0)
    try:
        candidate = SimpleNamespace(value=1)
        response = server._dispatch({"operation": "publish", "state": candidate})
        assert response["status"] == "ok"
        assert response["revision"] == 1
        assert server._state is candidate
        assert server._committed_snapshot_reader is None
    finally:
        server.close()


def test_r2_r11_committed_publish_installs_disk_object_and_isolates_candidate(durable_harness):
    durable_harness.commit(1, value=["disk"])
    server = durable_harness.server()
    candidate = SimpleNamespace(state_id="sid", revision=1, value=["request"])

    response = server._dispatch({
        "operation": "publish", "state": candidate, "origin": "desktop_analysis"
    })
    candidate.value.append("mutated")

    assert response == {
        "status": "ok", "revision": 1, "seq": 1, "source": "committed_snapshot"
    }
    assert server._state is not candidate
    assert server._state.value == ["disk"]
    assert server._events[0]["canonical_revision"] == 1


def test_r3_r5_r8_r9_r15_rejections_leave_live_and_event_unchanged(durable_harness):
    durable_harness.commit(1)
    server = durable_harness.server()
    assert _publish(server, 1)["status"] == "ok"
    before = _unchanged(server)

    assert _publish(server, 2)["error"] == "committed_publish_generation_mismatch"
    _assert_unchanged(server, before)
    assert _publish(server, 1, state_id="different")["error"] == "committed_publish_generation_mismatch"
    _assert_unchanged(server, before)
    assert _publish(server, 1)["error"] == "non_monotonic_canonical_revision"
    _assert_unchanged(server, before)

    durable_harness.commit(2)
    durable_harness.commit(3)
    assert _publish(server, 2)["error"] == "committed_publish_generation_mismatch"
    _assert_unchanged(server, before)
    assert _publish(server, 3)["status"] == "ok"
    latest = _unchanged(server)
    assert _publish(server, 3)["error"] == "non_monotonic_canonical_revision"
    _assert_unchanged(server, latest)


def test_r4_r12_r29_durable_catch_up_after_earlier_publish_failure(durable_harness):
    durable_harness.commit(1)
    failed = durable_harness.server(
        custom_reader=lambda: (_ for _ in ()).throw(OSError("publish unavailable"))
    )
    assert _publish(failed, 1)["error"] == "committed_publish_failed"
    _assert_unchanged(failed, (None, 0, 0, []))

    durable_harness.commit(2)
    durable_harness.commit(3)
    server = durable_harness.server(state=SimpleNamespace(state_id="sid", revision=1))
    response = _publish(server, 3)
    assert response["status"] == "ok"
    assert server._revision == 3
    assert server._state.revision == 3
    assert read_metadata(durable_harness.cache).revision == 3
    assert [event["canonical_revision"] for event in server._events] == [3]


def test_r6_r7_missing_and_corrupt_snapshot_fail_closed(durable_harness):
    server = durable_harness.server()
    before = _unchanged(server)
    response = _publish(server, 1)
    assert response["error"] == "committed_snapshot_unavailable"
    assert response["resync_required"] is True
    _assert_unchanged(server, before)

    _, metadata = durable_harness.commit(1)
    (durable_harness.cache / metadata.state_file).write_bytes(b"not a pickle")
    response = _publish(server, 1)
    assert response["status"] == "error"
    assert response["resync_required"] is True
    _assert_unchanged(server, before)


def test_r10_committed_publish_respects_cross_process_store_lock(durable_harness):
    durable_harness.commit(1)
    ctx = get_context("spawn")
    ready = ctx.Event()
    release = ctx.Event()
    holder = ctx.Process(
        target=_hold_snapshot_lock,
        args=(str(durable_harness.cache / "engine_state.lock"), ready, release),
    )
    holder.start()
    try:
        assert ready.wait(15)
        server = durable_harness.server()
        response = _publish(server, 1)
        assert response["status"] == "error"
        assert response["resync_required"] is True
        assert server._revision == 0
    finally:
        release.set()
        holder.join(15)
        if holder.is_alive():
            holder.terminate()
            holder.join(5)
    assert holder.exitcode == 0


def test_r16_r17_r22_invalid_origin_and_trace_leave_everything_unchanged(durable_harness):
    durable_harness.commit(1)
    server = durable_harness.server()
    before = _unchanged(server)

    class BadString:
        def __str__(self):
            raise RuntimeError("must not stringify")

    assert _publish(server, 1, origin=BadString())["error"] == "invalid_publish_origin"
    _assert_unchanged(server, before)
    assert _publish(server, 1, trace_op=BadString())["error"] == "invalid_publish_trace_op"
    _assert_unchanged(server, before)


def test_r26_identity_extraction_failure_precedes_commit(durable_harness):
    class BadMetadata:
        @property
        def revision(self):
            raise RuntimeError("identity extraction failed")

    @contextmanager
    def bad_identity_reader():
        yield (SimpleNamespace(state_id="sid", revision=1), BadMetadata())

    server = durable_harness.server(custom_reader=bad_identity_reader)
    before = _unchanged(server)
    response = _publish(server, 1)
    assert response["error"] == "committed_publish_failed"
    _assert_unchanged(server, before)


@pytest.mark.parametrize("failure", ["reader", "timestamp", "provenance", "events"])
def test_r18_r26_precommit_failures_leave_authority_unchanged(
    durable_harness, monkeypatch, failure
):
    durable_harness.commit(1)
    if failure == "reader":
        reader = lambda: (_ for _ in ()).throw(OSError("read failed"))
    else:
        reader = durable_harness.reader
    server = durable_harness.server(custom_reader=reader)
    before = _unchanged(server)

    if failure == "timestamp":
        class BadDateTime:
            @staticmethod
            def now(_zone):
                raise RuntimeError("timestamp failed")
        monkeypatch.setattr(ipc_module, "datetime", BadDateTime)
    elif failure == "provenance":
        monkeypatch.setattr(
            ipc_module, "_mark_live_state_provenance",
            lambda _state: (_ for _ in ()).throw(RuntimeError("provenance failed")),
        )
    elif failure == "events":
        class BadEvents(list):
            def __add__(self, _other):
                raise RuntimeError("event replacement failed")
        server._events = BadEvents()
        before = _unchanged(server)

    response = _publish(server, 1)
    assert response["error"] == "committed_publish_failed"
    _assert_unchanged(server, before)


def test_r19_r20_r21_r23_publish_event_is_prepared_once_and_ignores_request_metadata(
    durable_harness, monkeypatch
):
    server = durable_harness.server(retention=2)
    monkeypatch.setattr(
        server, "_record_event",
        lambda *_a, **_k: pytest.fail("_record_event must not be invoked"),
    )
    for revision in (1, 2, 3):
        durable_harness.commit(revision)
        response = _publish(
            server,
            revision,
            origin="desktop_analysis",
            diagnostic_changes={"forged": True},
            message="forged",
            file_path="forged.py",
        )
        assert response["status"] == "ok"
        assert server._events[-1]["canonical_revision"] == revision
    assert server._activity_seq == 3
    assert [event["seq"] for event in server._events] == [2, 3]
    assert all(
        not ({"diagnostic_changes", "message", "file_path"} & event.keys())
        for event in server._events
    )


def test_r24_r25_r27_r28_reader_exit_failure_reports_installed_generation(
    durable_harness
):
    durable_harness.commit(1)

    @contextmanager
    def failing_exit_reader():
        with durable_harness.reader() as loaded:
            yield loaded
            raise OSError("release failed")

    server = durable_harness.server(custom_reader=failing_exit_reader)
    response = _publish(server, 1)
    assert response == {
        "status": "ok",
        "revision": 1,
        "seq": 1,
        "source": "committed_snapshot",
        "resync_required": True,
        "warning": "snapshot_lock_release_unverified",
    }
    assert server._revision == 1
    assert server._activity_seq == 1
    assert len(server._events) == 1
    assert server._events[0]["operation"] == "publish"


def test_r30_publish_does_not_persist_another_revision(durable_harness):
    durable_harness.commit(1)
    server = durable_harness.server()
    before = read_metadata(durable_harness.cache)
    assert _publish(server, 1)["status"] == "ok"
    after = read_metadata(durable_harness.cache)
    assert after == before
    loaded = load_snapshot(
        durable_harness.cache,
        expected_repo_id=durable_harness.identity.repo_id,
        expected_root_path=durable_harness.identity.root_path,
    )
    assert loaded is not None
    assert loaded[1].revision == 1
