from __future__ import annotations

import json
import multiprocessing
import os
import threading
from pathlib import Path
from typing import Any

import pytest

import contextor.core.live_state.runtime_lease as runtime_lease_module
from contextor.core.live_state.runtime_domain import RuntimeDomain
from contextor.core.live_state.runtime_lease import (
    AuthorityGenerationRecord,
    DefaultLivenessVerifier,
    EndpointBindingError,
    ForeignLeaseError,
    LeaseAlreadyHeld,
    LeaseLivenessUnknown,
    LeaseNotOwner,
    LeaseRecoveryRequired,
    LivenessResult,
    LivenessStatus,
    ProcessIdentity,
    RuntimeLease,
    RuntimeLeaseError,
    RuntimeLeaseManager,
    generation_metadata_path,
    live_lease_path,
)


class ScriptedVerifier:
    def __init__(self, result: LivenessResult):
        self.result = result
        self.calls: list[RuntimeLease] = []

    def verify(self, lease: RuntimeLease) -> LivenessResult:
        self.calls.append(lease)
        return self.result


class CrashAt:
    def __init__(self, point: str):
        self.point = point

    def __call__(self, point: str) -> None:
        if point == self.point:
            raise RuntimeError(f"simulated crash at {point}")


def _domain(tmp_path: Path) -> RuntimeDomain:
    context = tmp_path / "test-domain" / "run-1"
    cache = context / "cache" / "ctx_repo"
    return RuntimeDomain.create(
        repo_id="ctx_repo",
        repo_root=tmp_path / "repo",
        mode="test",
        cache_root=cache,
        logs_root=context / "logs",
        lock_root=cache / "runtime",
        ipc_endpoint_root=cache,
        test_context_root=context,
        test_run_id="run-1",
        known_production_roots=(tmp_path / "production-cache", tmp_path / "production-logs"),
    )


def _manager(
    domain: RuntimeDomain,
    *,
    verifier: ScriptedVerifier | None = None,
    process_start_identity: str = "test-process-start",
    failure_injector=None,
) -> RuntimeLeaseManager:
    production_roots = (
        domain.test_context_root.parent.parent.parent / "production-cache",
        domain.test_context_root.parent.parent.parent / "production-logs",
    )
    return RuntimeLeaseManager(
        domain,
        process_identity=ProcessIdentity(os.getpid(), process_start_identity, "pytest"),
        liveness_verifier=verifier,
        known_production_roots=production_roots,
        failure_injector=failure_injector,
    )


def _live_result() -> LivenessResult:
    return LivenessResult(
        LivenessStatus.LIVE,
        process_alive=True,
        process_identity_matches=True,
        endpoint_available=True,
        endpoint_matches=True,
        reason="fake authority is live",
    )


def _stale_result(*, pid_reuse: bool = False) -> LivenessResult:
    return LivenessResult.stale(
        process_alive=True if pid_reuse else False,
        process_identity_matches=False,
        endpoint_available=False,
        endpoint_matches=False,
        reason="fake confirmed stale authority",
        endpoint_evidence_verified=True,
    )


def _acquire_in_process(
    domain: RuntimeDomain,
    production_roots: tuple[Path, ...],
    start_event: Any,
    result_queue: Any,
    index: int,
) -> None:
    start_event.wait()
    try:
        lease = RuntimeLeaseManager(
            domain,
            process_identity=ProcessIdentity(os.getpid(), f"child-{index}", "pytest"),
            liveness_verifier=ScriptedVerifier(_live_result()),
            known_production_roots=production_roots,
        ).acquire()
        result_queue.put(("winner", lease.lease_generation))
    except BaseException as exc:  # pragma: no cover - parent assertion reports failures
        result_queue.put((type(exc).__name__, str(exc)))


def test_first_acquisition_allocates_generation_one_and_fresh_service_id(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)

    lease = manager.acquire()

    assert lease.lease_generation == 1
    assert lease.service_instance_id
    assert lease.owner_token
    assert lease.endpoint_fingerprint is None
    assert manager.read_generation().last_lease_generation == 1
    assert manager.read_live_lease() == lease


def test_clean_release_preserves_high_water_mark_and_next_acquisition_is_two(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)

    first = manager.acquire()
    released = manager.release(first)
    assert released.status == "released"
    assert released.last_lease_generation == 1
    assert not live_lease_path(domain).exists()

    second = _manager(domain).acquire()
    assert second.lease_generation == 2
    assert second.service_instance_id != first.service_instance_id


def test_stale_recovery_increments_generation_and_fences_old_service(tmp_path: Path):
    domain = _domain(tmp_path)
    first_manager = _manager(domain)
    first = first_manager.acquire()

    stale_manager = _manager(domain, verifier=ScriptedVerifier(_stale_result()))
    second = stale_manager.acquire()

    assert second.lease_generation == 2
    assert second.service_instance_id != first.service_instance_id
    with pytest.raises(LeaseNotOwner):
        first_manager.release(first)


def test_pid_reuse_with_same_pid_but_different_start_identity_is_stale(tmp_path: Path):
    domain = _domain(tmp_path)
    first = _manager(domain).acquire()
    verifier = ScriptedVerifier(_stale_result(pid_reuse=True))

    second = _manager(domain, verifier=verifier).acquire()

    assert verifier.calls[0].service_pid == first.service_pid
    assert second.lease_generation == 2


def test_generation_gap_after_crash_before_live_write_is_never_reused(tmp_path: Path):
    domain = _domain(tmp_path)
    crashed = _manager(domain, failure_injector=CrashAt("after_generation_reservation"))
    with pytest.raises(RuntimeError, match="after_generation_reservation"):
        crashed.acquire()

    assert generation_metadata_path(domain).is_file()
    assert not live_lease_path(domain).exists()
    assert crashed.read_generation().status == "reserved"
    next_lease = _manager(domain).acquire()
    assert next_lease.lease_generation == 2


def test_crash_after_live_write_leaves_existing_authority_for_normal_liveness_check(tmp_path: Path):
    domain = _domain(tmp_path)
    crashed = _manager(
        domain,
        verifier=ScriptedVerifier(_live_result()),
        failure_injector=CrashAt("after_live_lease_persist"),
    )
    with pytest.raises(RuntimeError, match="after_live_lease_persist"):
        crashed.acquire()

    existing = RuntimeLease.from_dict(json.loads(live_lease_path(domain).read_text()))
    assert existing.lease_generation == 1
    assert _manager(domain).read_generation().status == "reserved"
    with pytest.raises(LeaseAlreadyHeld):
        _manager(domain, verifier=ScriptedVerifier(_live_result())).acquire()


def test_crash_after_generation_activation_leaves_active_authority(tmp_path: Path):
    domain = _domain(tmp_path)
    crashed = _manager(
        domain,
        verifier=ScriptedVerifier(_live_result()),
        failure_injector=CrashAt("after_generation_activation"),
    )
    with pytest.raises(RuntimeError, match="after_generation_activation"):
        crashed.acquire()

    assert crashed.read_generation().status == "active"
    assert live_lease_path(domain).exists()
    with pytest.raises(LeaseAlreadyHeld):
        _manager(domain, verifier=ScriptedVerifier(_live_result())).acquire()


@pytest.mark.parametrize(
    "status",
    [LivenessStatus.UNKNOWN, LivenessStatus.AMBIGUOUS, LivenessStatus.TIMEOUT, LivenessStatus.BUSY],
)
def test_ambiguous_timeout_or_busy_liveness_rejects_takeover(tmp_path: Path, status: LivenessStatus):
    domain = _domain(tmp_path)
    _manager(domain).acquire()
    result = LivenessResult(
        status,
        process_alive=None,
        process_identity_matches=None,
        endpoint_available=None,
        endpoint_matches=None,
        reason="not stale evidence",
    )

    with pytest.raises(LeaseLivenessUnknown):
        _manager(domain, verifier=ScriptedVerifier(result)).acquire()


def test_confirmed_dead_process_and_unavailable_endpoint_allow_stale_takeover(tmp_path: Path):
    domain = _domain(tmp_path)
    first = _manager(domain).acquire()
    second = _manager(domain, verifier=ScriptedVerifier(_stale_result())).acquire()

    assert second.lease_generation == first.lease_generation + 1


def test_default_liveness_does_not_fabricate_endpoint_stale_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    domain = _domain(tmp_path)
    lease = _manager(domain).acquire()
    verifier = DefaultLivenessVerifier()

    monkeypatch.setattr(runtime_lease_module, "_process_identity", lambda _pid: (None, None, False))
    dead = verifier.verify(lease)
    assert dead.status is LivenessStatus.UNKNOWN
    assert dead.endpoint_evidence_verified is False
    assert not dead.confirmed_stale

    monkeypatch.setattr(runtime_lease_module, "_process_identity", lambda _pid: (None, "different", True))
    pid_reuse = verifier.verify(lease)
    assert pid_reuse.status is LivenessStatus.UNKNOWN
    assert pid_reuse.endpoint_evidence_verified is False
    assert not pid_reuse.confirmed_stale


def test_impossible_generation_record_combinations_fail_closed(tmp_path: Path):
    domain = _domain(tmp_path)
    initial = AuthorityGenerationRecord.initial(domain)

    active_zero = initial.to_dict()
    active_zero["status"] = "active"
    with pytest.raises(RuntimeLeaseError):
        AuthorityGenerationRecord.from_dict(active_zero)

    reserved_without_identity = initial.to_dict()
    reserved_without_identity.update(
        status="reserved",
        last_lease_generation=1,
        last_service_instance_id="service-a",
    )
    with pytest.raises(RuntimeLeaseError):
        AuthorityGenerationRecord.from_dict(reserved_without_identity)

    half_fence = initial.to_dict()
    half_fence.update(
        status="released",
        last_lease_generation=1,
        last_service_instance_id="service-a",
        service_pid=os.getpid(),
        process_start_identity="process-a",
        fenced_service_instance_id="service-a",
        fenced_lease_generation=None,
    )
    with pytest.raises(RuntimeLeaseError):
        AuthorityGenerationRecord.from_dict(half_fence)


def test_crash_during_release_durable_fence_prevents_old_lease_resurrection(tmp_path: Path):
    domain = _domain(tmp_path)
    first_manager = _manager(domain)
    first = first_manager.acquire()
    first_manager.failure_injector = CrashAt("before_release_live_remove")
    with pytest.raises(RuntimeError, match="before_release_live_remove"):
        first_manager.release(first)

    record = first_manager.read_generation()
    assert record.status == "released"
    assert live_lease_path(domain).exists()
    second = _manager(domain, verifier=ScriptedVerifier(_live_result())).acquire()
    assert second.lease_generation == 2
    current = RuntimeLease.deserialize(live_lease_path(domain).read_text())
    assert current.service_instance_id == second.service_instance_id
    assert current.service_instance_id != first.service_instance_id


def test_old_service_cannot_bind_endpoint_or_release_current_generation(tmp_path: Path):
    domain = _domain(tmp_path)
    first_manager = _manager(domain)
    first = first_manager.acquire()
    second = _manager(domain, verifier=ScriptedVerifier(_stale_result())).acquire()

    with pytest.raises(LeaseNotOwner):
        first_manager.bind_endpoint(first, "endpoint-old")
    with pytest.raises(LeaseNotOwner):
        first_manager.release(first)
    bound = _manager(domain).bind_endpoint(second, "endpoint-new")
    assert bound.endpoint_fingerprint == "endpoint-new"


def test_endpoint_binding_is_owner_validated_and_one_time(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    lease = manager.acquire()
    bound = manager.bind_endpoint(lease, "endpoint-1")
    assert manager.bind_endpoint(bound, "endpoint-1").endpoint_fingerprint == "endpoint-1"
    with pytest.raises(EndpointBindingError):
        manager.bind_endpoint(bound, "endpoint-2")


def test_heartbeat_is_owner_validated_but_not_liveness_evidence(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    lease = manager.acquire()
    refreshed = manager.refresh_heartbeat(lease, now=lease.started_at + 5)
    assert refreshed.last_heartbeat_at == lease.started_at + 5
    assert manager.read_live_lease() == refreshed


def test_malformed_generation_metadata_fails_closed(tmp_path: Path):
    domain = _domain(tmp_path)
    path = generation_metadata_path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RuntimeLeaseError):
        _manager(domain).acquire()


def test_malformed_live_lease_metadata_fails_closed(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    manager.acquire()
    live_lease_path(domain).write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeLeaseError):
        _manager(domain, verifier=ScriptedVerifier(_stale_result())).acquire()


@pytest.mark.parametrize("field", ["repo_id", "runtime_domain_id", "resource_root_fingerprints"])
def test_foreign_lease_metadata_fails_closed(tmp_path: Path, field: str):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    lease = manager.acquire()
    payload = lease.to_dict()
    if field == "resource_root_fingerprints":
        payload[field] = dict(payload[field])
        payload[field]["cache_root"] = "foreign-cache-fingerprint"
    else:
        payload[field] = "foreign"
    live_lease_path(domain).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ForeignLeaseError):
        _manager(domain, verifier=ScriptedVerifier(_stale_result())).acquire()


def test_concurrent_acquisitions_have_exactly_one_winner(tmp_path: Path):
    domain = _domain(tmp_path)
    barrier = threading.Barrier(4)
    results: list[RuntimeLease] = []
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            barrier.wait()
            lease = _manager(
                domain,
                verifier=ScriptedVerifier(_live_result()),
                process_start_identity=f"thread-{index}",
            ).acquire()
            results.append(lease)
        except BaseException as exc:  # pragma: no cover - assertion below reports failures
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 1
    assert len(errors) == 3
    assert all(isinstance(error, LeaseAlreadyHeld) for error in errors)


def test_cross_process_acquisitions_have_exactly_one_winner(tmp_path: Path):
    domain = _domain(tmp_path)
    production_roots = (tmp_path / "production-cache", tmp_path / "production-logs")
    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_acquire_in_process,
            args=(domain, production_roots, start_event, result_queue, index),
        )
        for index in range(2)
    ]
    for process in processes:
        process.start()
    start_event.set()
    results = [result_queue.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
    assert all(process.exitcode == 0 for process in processes)
    assert [result[0] for result in results].count("winner") == 1
    assert [result[0] for result in results].count("LeaseAlreadyHeld") == 1


def test_active_generation_with_missing_live_lease_fails_closed(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    first = manager.acquire()
    live_lease_path(domain).unlink()
    with pytest.raises(LeaseRecoveryRequired):
        _manager(domain).acquire()
    record = manager.read_generation()
    assert record.status == "active"
    assert record.last_lease_generation == first.lease_generation


def test_runtime_lease_serialization_round_trip_and_test_root_isolation(tmp_path: Path):
    domain = _domain(tmp_path)
    manager = _manager(domain)
    lease = manager.acquire()
    restored = RuntimeLease.from_dict(json.loads(json.dumps(lease.to_dict())))
    assert restored == lease
    assert set(dict(lease.resource_root_fingerprints)) == {
        "repo_root",
        "cache_root",
        "logs_root",
        "lock_root",
        "ipc_endpoint_root",
    }
    assert not (tmp_path / "production-cache").exists()
    assert not (tmp_path / "production-logs").exists()


def test_process_identity_requires_start_token_and_is_not_pid_only():
    with pytest.raises(RuntimeLeaseError):
        ProcessIdentity(os.getpid(), "")
