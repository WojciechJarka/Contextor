"""Focused durable-generation publication contract."""

import copy
import threading
from contextlib import contextmanager
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.live_state import ipc as ipc_module
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
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


def _raw_publish_without_writer_lease(repo_path, endpoint, response_queue):
    from contextor.core.analysis.full_analysis_lease import (
        FullAnalysisBusyError,
        acquire_full_analysis,
        release_full_analysis,
    )

    try:
        lease = acquire_full_analysis(
            repo_path, owner="raw-publish-lease-probe", timeout=0.0
        )
    except FullAnalysisBusyError:
        lease_denied = True
    else:
        release_full_analysis(lease)
        lease_denied = False
    response = LiveStateClient(endpoint).publish(
        SimpleNamespace(state_id="sid", revision=2),
        origin="unleased_raw_ipc",
        timeout=10.0,
    )
    response_queue.put((lease_denied, response))


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


def test_opt_in_ack_confirms_exact_installed_generation_without_mutation(
    durable_harness,
):
    from contextor.core.analysis.state_manager import FileStateManager

    committed_state, committed_metadata = durable_harness.commit(
        1, value="committed"
    )
    server = durable_harness.server(
        state=committed_state,
        revision=committed_metadata.revision,
    )
    before_server = _unchanged(server)
    before_disk, before_disk_metadata = load_snapshot(
        durable_harness.cache,
        expected_repo_id=durable_harness.identity.repo_id,
        expected_root_path=durable_harness.identity.root_path,
    )
    before_metadata = read_metadata(durable_harness.cache)
    before_file_state_revision = FileStateManager(
        str(durable_harness.cache)
    ).revision

    response = _publish(
        server,
        1,
        acknowledge_installed=True,
    )

    assert response == {
        "status": "ok",
        "revision": 1,
        "seq": before_server[2],
        "source": "committed_snapshot",
        "already_installed": True,
        "origin_verified": False,
    }
    _assert_unchanged(server, before_server)
    assert server._state is committed_state

    after_disk, after_disk_metadata = load_snapshot(
        durable_harness.cache,
        expected_repo_id=durable_harness.identity.repo_id,
        expected_root_path=durable_harness.identity.root_path,
    )
    assert after_disk_metadata == before_disk_metadata
    assert after_disk_metadata == before_metadata
    assert after_disk.state_id == before_disk.state_id == "sid"
    assert after_disk.revision == before_disk.revision == 1
    assert read_metadata(durable_harness.cache) == before_metadata
    assert FileStateManager(str(durable_harness.cache)).revision == (
        before_file_state_revision
    )


@pytest.mark.parametrize(
    ("case", "expected_error"),
    [
        ("wrong_candidate_state_id", "committed_publish_generation_mismatch"),
        ("uncommitted_candidate_revision", "committed_publish_generation_mismatch"),
        ("live_state_id_mismatch", "non_monotonic_canonical_revision"),
        ("live_revision_mismatch", "non_monotonic_canonical_revision"),
        ("older_than_live", "non_monotonic_canonical_revision"),
        ("committed_snapshot_missing", "committed_snapshot_unavailable"),
    ],
)
def test_opt_in_ack_rejects_nonmatching_or_unavailable_generation(
    durable_harness,
    case,
    expected_error,
):
    committed_state, committed_metadata = durable_harness.commit(1)
    if case == "committed_snapshot_missing":
        @contextmanager
        def unavailable_reader():
            yield None

        server = durable_harness.server(
            state=committed_state,
            revision=1,
            custom_reader=unavailable_reader,
        )
    elif case == "older_than_live":
        server = durable_harness.server(
            state=SimpleNamespace(state_id="sid", revision=2),
            revision=2,
        )
    else:
        server = durable_harness.server(
            state=committed_state,
            revision=committed_metadata.revision,
        )

    candidate_revision = 1
    candidate_state_id = "sid"
    if case == "wrong_candidate_state_id":
        candidate_state_id = "wrong"
    elif case == "uncommitted_candidate_revision":
        candidate_revision = 2
    elif case == "live_state_id_mismatch":
        server._state = SimpleNamespace(state_id="wrong", revision=1)
    elif case == "live_revision_mismatch":
        server._state = SimpleNamespace(state_id="sid", revision=0)

    before = _unchanged(server)
    response = _publish(
        server,
        candidate_revision,
        state_id=candidate_state_id,
        acknowledge_installed=True,
    )

    assert response["status"] == "error"
    assert response["error"] == expected_error
    assert response.get("already_installed") is not True
    _assert_unchanged(server, before)


def test_raw_ipc_publish_front_runs_lease_owner_same_committed_generation(
    durable_harness,
):
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )
    from contextor.core.analysis.state_manager import FileStateManager

    durable_harness.commit(1)
    initial = load_snapshot(
        durable_harness.cache,
        expected_repo_id=durable_harness.identity.repo_id,
        expected_root_path=durable_harness.identity.root_path,
    )
    server = durable_harness.server(state=initial[0], revision=initial[1].revision)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    lease = acquire_full_analysis(
        durable_harness.repo, owner="legitimate-full-writer", timeout=5.0
    )
    try:
        candidate, committed = durable_harness.commit(2, value="owner-generation")
        before = _unchanged(server)
        assert client.publish(
            SimpleNamespace(state_id="sid", revision=3),
            origin="invalid_uncommitted",
            timeout=10.0,
        )["error"] == "committed_publish_generation_mismatch"
        _assert_unchanged(server, before)
        assert client.publish(
            SimpleNamespace(state_id="wrong", revision=2),
            origin="invalid_identity",
            timeout=10.0,
        )["error"] == "committed_publish_generation_mismatch"
        _assert_unchanged(server, before)

        context = get_context("spawn")
        response_queue = context.Queue()
        raw = context.Process(
            target=_raw_publish_without_writer_lease,
            args=(str(durable_harness.repo), server.endpoint, response_queue),
        )
        raw.start()
        try:
            lease_denied, raw_response = response_queue.get(timeout=12.0)
            raw.join(5.0)
        finally:
            if raw.is_alive():
                raw.terminate()
                raw.join(5.0)
        assert raw.exitcode == 0
        assert lease_denied is True
        assert raw_response == {
            "status": "ok",
            "revision": 2,
            "seq": 1,
            "source": "committed_snapshot",
        }
        assert server._revision == 2
        assert server._state.state_id == committed.state_id
        assert server._state.revision == 2
        assert server._state.value == "owner-generation"
        assert server._activity_seq == 1
        assert len(server._events) == 1
        assert server._events[0]["origin"] == "unleased_raw_ipc"
        assert server._events[0]["canonical_revision"] == 2

        owner_response = client.publish(
            candidate, origin="legitimate_full_writer", timeout=10.0
        )
        assert owner_response == {
            "status": "error",
            "error": "non_monotonic_canonical_revision",
            "revision": 2,
            "candidate_revision": 2,
            "expected_revision": 3,
        }
        before_retry = _unchanged(server)
        assert client.publish(
            candidate, origin="legitimate_full_writer", timeout=10.0
        ) == owner_response
        _assert_unchanged(server, before_retry)

        disk = load_snapshot(
            durable_harness.cache,
            expected_repo_id=durable_harness.identity.repo_id,
            expected_root_path=durable_harness.identity.root_path,
        )
        assert disk[1].revision == committed.revision == 2
        assert disk[1].state_id == committed.state_id == "sid"
        assert disk[0].revision == server._state.revision == 2
        assert disk[0].state_id == server._state.state_id
        assert FileStateManager(str(durable_harness.cache)).revision == 2
        assert read_metadata(durable_harness.cache) == disk[1]
        assert server._activity_seq == 1
        assert len(server._events) == 1
        assert server._events[0]["origin"] == "unleased_raw_ipc"
    finally:
        release_full_analysis(lease)
        server.close()
        thread.join(5.0)
    assert not thread.is_alive()


def test_raw_ipc_front_run_gets_validated_owner_already_installed_ack(
    durable_harness,
):
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )
    from contextor.core.analysis.state_manager import FileStateManager

    durable_harness.commit(1)
    initial = load_snapshot(
        durable_harness.cache,
        expected_repo_id=durable_harness.identity.repo_id,
        expected_root_path=durable_harness.identity.root_path,
    )
    server = durable_harness.server(
        state=initial[0],
        revision=initial[1].revision,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    lease = acquire_full_analysis(
        durable_harness.repo,
        owner="legitimate-full-writer",
        timeout=5.0,
    )
    try:
        candidate, committed = durable_harness.commit(
            2, value="owner-generation"
        )
        context = get_context("spawn")
        response_queue = context.Queue()
        raw = context.Process(
            target=_raw_publish_without_writer_lease,
            args=(str(durable_harness.repo), server.endpoint, response_queue),
        )
        raw.start()
        try:
            lease_denied, raw_response = response_queue.get(timeout=12.0)
            raw.join(5.0)
        finally:
            if raw.is_alive():
                raw.terminate()
                raw.join(5.0)

        assert raw.exitcode == 0
        assert lease_denied is True
        assert raw_response == {
            "status": "ok",
            "revision": 2,
            "seq": 1,
            "source": "committed_snapshot",
        }
        before_owner_ack = _unchanged(server)
        disk_before_ack = load_snapshot(
            durable_harness.cache,
            expected_repo_id=durable_harness.identity.repo_id,
            expected_root_path=durable_harness.identity.root_path,
        )
        metadata_before_ack = read_metadata(durable_harness.cache)
        file_state_revision_before_ack = FileStateManager(
            str(durable_harness.cache)
        ).revision

        owner_response = client.publish(
            candidate,
            origin="legitimate_full_writer",
            timeout=10.0,
            acknowledge_installed=True,
        )

        assert owner_response == {
            "status": "ok",
            "revision": 2,
            "seq": 1,
            "source": "committed_snapshot",
            "already_installed": True,
            "origin_verified": False,
        }
        _assert_unchanged(server, before_owner_ack)
        assert server._state.state_id == committed.state_id == "sid"
        assert server._state.revision == committed.revision == 2
        assert server._state.value == "owner-generation"
        assert len(server._events) == 1
        assert server._events[0]["origin"] == "unleased_raw_ipc"
        assert server._events[0]["canonical_revision"] == 2

        disk_after_ack = load_snapshot(
            durable_harness.cache,
            expected_repo_id=durable_harness.identity.repo_id,
            expected_root_path=durable_harness.identity.root_path,
        )
        assert disk_after_ack[1] == disk_before_ack[1] == metadata_before_ack
        assert disk_after_ack[0].state_id == server._state.state_id
        assert disk_after_ack[0].revision == server._state.revision == 2
        assert FileStateManager(str(durable_harness.cache)).revision == (
            file_state_revision_before_ack
        )
        assert server._activity_seq == 1
        assert len(server._events) == 1
    finally:
        release_full_analysis(lease)
        server.close()
        thread.join(5.0)
    assert not thread.is_alive()


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
