from contextlib import contextmanager
import threading
from types import SimpleNamespace

import pytest

from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient


def _recovery_server(
    root,
    *,
    live_state="state",
    committed_state="state",
    committed_metadata=None,
    identity=None,
    snapshot_error=None,
    updater=None,
):
    root_path = str(root.resolve())
    repo_id = "repo-id"
    if live_state == "state":
        live_state = SimpleNamespace(state_id="state-id", revision=1)
    if committed_state == "state":
        committed_state = SimpleNamespace(state_id="state-id", revision=1)
    if committed_metadata is None:
        committed_metadata = SimpleNamespace(
            repo_id=repo_id,
            root_path=root_path,
            state_id="state-id",
            revision=1,
        )
    if identity is None:
        identity = SimpleNamespace(repo_id=repo_id, root_path=root_path)

    lock = __import__("threading").Lock()
    entered = []
    exited = []
    persists = []

    @contextmanager
    def verification_guard():
        lock.acquire()
        entered.append(True)
        try:
            yield
        finally:
            exited.append(True)
            lock.release()

    @contextmanager
    def committed_reader():
        if snapshot_error is not None:
            raise snapshot_error
        if committed_state is None:
            yield None
        else:
            yield committed_state, committed_metadata

    server = CanonicalLiveServer(
        live_state,
        revision=(getattr(live_state, "revision", 1) if live_state is not None else 1),
        updater=updater,
        persister=lambda *_args: persists.append(True),
        committed_snapshot_reader=committed_reader,
        recovery_verification_guard=verification_guard,
        repository_identity_reader=lambda: identity,
        authority_identity={"repo_id": repo_id, "root_path": root_path},
    )
    server._test_guard_entered = entered
    server._test_guard_exited = exited
    server._test_persists = persists
    return server


def _verify(server, generation=1):
    return server._dispatch(
        {"operation": "verify_recovery", "incident_generation": generation}
    )


def _finish(server, certificate, operation="complete_recovery_verification"):
    return server._dispatch(
        {
            "operation": operation,
            "certificate_id": certificate["certificate_id"],
            "incident_generation": certificate["incident_generation"],
        }
    )


def test_recovery_certificate_holds_writer_and_mutation_fences_until_ack(tmp_path):
    server = _recovery_server(tmp_path)
    try:
        result = _verify(server)
        assert result["status"] == "ok"
        certificate = result["certificate"]
        assert certificate == {
            "certificate_id": certificate["certificate_id"],
            "incident_generation": 1,
            "repo_id": "repo-id",
            "root_path": str(tmp_path.resolve()),
            "state_id": "state-id",
            "revision": 1,
        }
        assert server._test_guard_entered == [True]
        assert server._test_guard_exited == []
        assert server._test_persists == []
        assert server._mutation_coordinator.recovery_verification_active()

        update = server._dispatch(
            {"operation": "update_file", "file_path": str(tmp_path / "a.py")}
        )
        submitted = server._dispatch(
            {
                "operation": "submit_update_file",
                "file_path": str(tmp_path / "a.py"),
                "idempotency_key": "blocked-update",
            }
        )
        published = server._dispatch(
            {
                "operation": "publish",
                "state": SimpleNamespace(state_id="state-id", revision=2),
                "origin": "test",
            }
        )
        assert update["error"] == "recovery_verification_in_progress"
        assert submitted["accepted"] is False
        assert submitted["error"] == "recovery_verification_in_progress"
        assert published["error"] == "recovery_verification_in_progress"
        assert server._revision == 1

        completed = _finish(server, certificate)
        assert completed["status"] == "ok"
        assert completed["released"] is True
        assert completed["incident_generation"] == 1
        assert server._test_guard_exited == [True]
        assert not server._mutation_coordinator.recovery_verification_active()
    finally:
        server.close()


def test_concurrent_publish_cannot_cross_recovery_fence(tmp_path):
    server = _recovery_server(tmp_path)
    publish_initial_check = threading.Event()
    recovery_fence_started = threading.Event()
    publish_result = {}
    verify_result = {}
    original_active = server._mutation_coordinator.recovery_verification_active
    original_begin = server._mutation_coordinator.begin_recovery_verification

    def observe_active():
        active = original_active()
        if threading.current_thread().name == "racing-publish" and not active:
            publish_initial_check.set()
        return active

    def observe_begin(timeout):
        admitted = original_begin(timeout)
        if admitted:
            recovery_fence_started.set()
        return admitted

    server._mutation_coordinator.recovery_verification_active = observe_active
    server._mutation_coordinator.begin_recovery_verification = observe_begin
    execution_lock = server._mutation_execution_lock

    def publish():
        publish_result.update(
            server._dispatch(
                {
                    "operation": "publish",
                    "state": SimpleNamespace(state_id="state-id", revision=2),
                    "origin": "racing-test",
                }
            )
        )

    def verify():
        verify_result.update(_verify(server))

    publish_thread = threading.Thread(target=publish, name="racing-publish")
    verify_thread = threading.Thread(target=verify, name="recovery-verification")
    execution_lock_held = False
    try:
        execution_lock.acquire()
        execution_lock_held = True
        try:
            publish_thread.start()
            assert publish_initial_check.wait(2)
            verify_thread.start()
            assert recovery_fence_started.wait(2)
        finally:
            execution_lock.release()
            execution_lock_held = False

        publish_thread.join(2)
        verify_thread.join(2)
        assert not publish_thread.is_alive()
        assert not verify_thread.is_alive()
        assert verify_result["status"] == "ok"
        assert publish_result["status"] == "error"
        assert publish_result["error"] == "recovery_verification_in_progress"
        assert server._revision == 1
        assert server._mutation_coordinator.recovery_verification_active()
        assert _finish(server, verify_result["certificate"])["released"] is True
    finally:
        if execution_lock_held:
            execution_lock.release()
        if publish_thread.ident is not None:
            publish_thread.join(2)
        if verify_thread.ident is not None:
            verify_thread.join(2)
        server.close()


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        (
            {
                "committed_state": SimpleNamespace(state_id="other", revision=1),
                "committed_metadata": SimpleNamespace(
                    repo_id="repo-id",
                    root_path="ROOT",
                    state_id="other",
                    revision=1,
                ),
            },
            "recovery_live_identity_mismatch",
        ),
        (
            {
                "live_state": SimpleNamespace(state_id="state-id", revision=2),
            },
            "recovery_live_revision_mismatch",
        ),
        (
            {
                "committed_metadata": SimpleNamespace(
                    repo_id="other",
                    root_path="ROOT",
                    state_id="state-id",
                    revision=1,
                ),
            },
            "recovery_snapshot_identity_mismatch",
        ),
        (
            {
                "committed_metadata": SimpleNamespace(
                    repo_id="repo-id",
                    root_path="ROOT",
                    state_id="state-id",
                    revision=0,
                ),
            },
            "recovery_snapshot_invalid",
        ),
        (
            {"committed_state": None},
            "recovery_snapshot_missing",
        ),
        (
            {"snapshot_error": OSError("unreadable")},
            "recovery_snapshot_unreadable",
        ),
        (
            {"identity": SimpleNamespace(repo_id="other", root_path="ROOT")},
            "recovery_identity_mismatch",
        ),
        (
            {"identity": SimpleNamespace(repo_id="repo-id", root_path="wrong-root")},
            "recovery_identity_mismatch",
        ),
        (
            {"live_state": None},
            "recovery_live_missing",
        ),
    ],
)
def test_recovery_verification_rejects_invalid_authority_pairs(
    tmp_path, kwargs, error
):
    root_path = str(tmp_path.resolve())
    if "committed_metadata" in kwargs:
        kwargs = {
            **kwargs,
            "committed_metadata": SimpleNamespace(
                **{
                    **vars(kwargs["committed_metadata"]),
                    "root_path": root_path,
                }
            ),
        }
    if "identity" in kwargs and kwargs["identity"].root_path == "ROOT":
        kwargs = {
            **kwargs,
            "identity": SimpleNamespace(
                repo_id=kwargs["identity"].repo_id, root_path=root_path
            ),
        }
    server = _recovery_server(tmp_path, **kwargs)
    try:
        result = _verify(server)
        assert result == {"status": "error", "error": error}
        assert not server._mutation_coordinator.recovery_verification_active()
        assert server._test_guard_exited == server._test_guard_entered
    finally:
        server.close()


def test_recovery_generation_and_certificate_are_required_to_release_fence(tmp_path):
    server = _recovery_server(tmp_path)
    try:
        result = _verify(server, generation=8)
        certificate = result["certificate"]
        wrong = server._dispatch(
            {
                "operation": "complete_recovery_verification",
                "certificate_id": "wrong",
                "incident_generation": 8,
            }
        )
        assert wrong == {
            "status": "error",
            "error": "recovery_certificate_mismatch",
        }
        assert server._mutation_coordinator.recovery_verification_active()

        cancelled = _finish(
            server, certificate, operation="cancel_recovery_verification"
        )
        assert cancelled["status"] == "ok"
        assert cancelled["cancelled"] is True
        assert cancelled["incident_generation"] == 8
        assert not server._mutation_coordinator.recovery_verification_active()
    finally:
        server.close()


def test_inflight_update_prevents_recovery_certificate(tmp_path):
    updater_entered = threading.Event()
    release_updater = threading.Event()

    def updater(_candidate, _path):
        updater_entered.set()
        assert release_updater.wait(5)
        return SimpleNamespace(status="UNCHANGED")

    server = _recovery_server(tmp_path, updater=updater)
    try:
        accepted = server._dispatch(
            {
                "operation": "submit_update_file",
                "file_path": str(tmp_path / "a.py"),
                "idempotency_key": "inflight-update",
            }
        )
        assert accepted["accepted"] is True
        assert updater_entered.wait(2)

        result = _verify(server)
        assert result == {
            "status": "error",
            "error": "recovery_mutations_pending",
        }
        assert server._test_guard_entered == []
        assert not server._mutation_coordinator.recovery_verification_active()
    finally:
        release_updater.set()
        server.close()


def test_recovery_verification_and_ack_round_trip_through_live_ipc(tmp_path):
    server = _recovery_server(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    try:
        verified = client.verify_recovery(3)
        assert verified["status"] == "ok"
        certificate = verified["certificate"]
        assert certificate["incident_generation"] == 3
        assert server._mutation_coordinator.recovery_verification_active()

        blocked = client.submit_update_file(
            str(tmp_path / "change.py"),
            idempotency_key="while-recovery-is-fenced",
        )
        assert blocked["accepted"] is False
        assert blocked["error"] == "recovery_verification_in_progress"

        released = client.complete_recovery_verification(
            certificate["certificate_id"], 3
        )
        assert released["status"] == "ok"
        assert released["released"] is True
        assert not server._mutation_coordinator.recovery_verification_active()
    finally:
        server.close()
        thread.join(2)
