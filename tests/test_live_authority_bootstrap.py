from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from contextor.core.live_state import (
    CanonicalLiveServer,
    EndpointSchemaError,
    LiveEndpoint,
    SecondDesktopActive,
    connect,
    connect_or_start,
)
from contextor.core.live_state.runtime import endpoint_file
from contextor.core.live_state import runtime as runtime_module
from contextor.core.live_state.runtime import AuthorityLivenessVerifier
from contextor.core.paths import runtime_logs_dir
from contextor.core.live_state.runtime_domain import RuntimeDomain
from contextor.core.live_state.runtime_lease import (
    LeaseLivenessUnknown,
    LeaseNotOwner,
    LeaseAlreadyHeld,
    LivenessResult,
    LivenessStatus,
    ProcessIdentity,
    RuntimeLeaseManager,
)
from contextor.core.repository_identity import read_repository_identity
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    return repo


def _stop(client) -> None:
    try:
        client.request("shutdown", timeout=1.0)
    except Exception:
        pass
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if connect(client.endpoint.root_path) is None:
            return
        time.sleep(0.05)


def _authority_event_types(logs_root: Path) -> list[str]:
    records = []
    for path in logs_root.glob("contextor_runtime_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            if payload.get("_type") == "authority_event":
                records.append(payload["event_type"])
    return records


def test_bootstrap_publishes_exact_lease_endpoint_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _repo(tmp_path, monkeypatch)
    client = connect_or_start(
        repo,
        owner_pid=os.getpid(),
        owner_token="owner-a",
        desktop_instance_id="desktop-a",
        client_kind="desktop",
    )
    try:
        identity = read_repository_identity(repo)
        assert identity is not None
        domain = RuntimeDomain.from_identity(identity, mode="production")
        manager = RuntimeLeaseManager(domain)
        lease = manager.read_live_lease()
        record = manager.read_generation()
        status = client.authority_status()
        assert lease is not None
        assert record.status == "active"
        assert client.endpoint.repo_id == identity.repo_id
        assert client.endpoint.root_path == str(repo.resolve())
        assert client.endpoint.runtime_domain_id == domain.domain_id
        assert client.endpoint.service_instance_id == lease.service_instance_id
        assert client.endpoint.lease_generation == lease.lease_generation
        assert client.endpoint.service_pid == lease.service_pid
        assert client.endpoint.process_start_identity == lease.process_start_identity
        assert lease.endpoint_fingerprint == client.endpoint.fingerprint()
        assert record.endpoint_fingerprint == client.endpoint.fingerprint()
        assert status["service_instance_id"] == lease.service_instance_id
        assert status["lease_generation"] == lease.lease_generation
        assert status["endpoint_fingerprint"] == client.endpoint.fingerprint()
    finally:
        _stop(client)


def test_verified_existing_authority_attaches_and_second_desktop_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    first = connect_or_start(
        repo,
        owner_pid=os.getpid(),
        owner_token="owner-a",
        desktop_instance_id="desktop-a",
        client_kind="desktop",
    )
    try:
        protocol = connect_or_start(repo, client_kind="protocol")
        assert protocol.service_pid == first.service_pid
        assert protocol.is_owner is False
        with pytest.raises(SecondDesktopActive, match="already active"):
            connect_or_start(
                repo,
                owner_pid=os.getpid(),
                owner_token="owner-b",
                desktop_instance_id="desktop-b",
                client_kind="desktop",
            )
    finally:
        _stop(first)


def test_protocol_attach_ignores_broken_desktop_claim_storage_and_desktop_admission_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)

    def broken_claim_reader(_manager, *_args, **_kwargs):
        raise RuntimeError("desktop claim storage unavailable")

    monkeypatch.setattr(
        runtime_module.RuntimeLeaseManager,
        "read_desktop_claim",
        broken_claim_reader,
    )
    service_errors: list[BaseException] = []

    def run() -> None:
        try:
            runtime_module.run_service(
                repo,
                owner_pid=os.getpid(),
                owner_token="service-owner",
            )
        except BaseException as exc:
            service_errors.append(exc)

    service_thread = threading.Thread(target=run, daemon=True)
    service_thread.start()
    protocol = None
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                protocol = connect_or_start(repo, client_kind="protocol", timeout=0.5)
                break
            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                time.sleep(0.05)
        assert protocol is not None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir()):
                break
            time.sleep(0.05)
        assert "RUNTIME_AUTHORITY_READY" in _authority_event_types(runtime_logs_dir())
        assert protocol.authority_status()["status"] == "ok"
        with pytest.raises(RuntimeError, match="desktop claim storage unavailable"):
            connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-b")
        assert protocol.endpoint.service_instance_id == protocol.authority_status()["service_instance_id"]
        assert protocol.endpoint.lease_generation == protocol.authority_status()["lease_generation"]
    finally:
        try:
            protocol.request("shutdown", timeout=1.0)
        except Exception:
            pass
        service_thread.join(timeout=5)
        assert not service_thread.is_alive()
        assert service_errors == []


def test_different_repositories_may_have_independent_authorities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    first_repo = _repo(tmp_path, monkeypatch, "first")
    second_repo = _repo(tmp_path, monkeypatch, "second")
    first = connect_or_start(first_repo, client_kind="protocol")
    second = connect_or_start(second_repo, client_kind="protocol")
    try:
        assert first.service_pid != second.service_pid
        assert first.endpoint.runtime_domain_id != second.endpoint.runtime_domain_id
    finally:
        _stop(first)
        _stop(second)


def test_clean_restart_fences_old_endpoint_and_allocates_next_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    first = connect_or_start(repo, client_kind="protocol")
    old_endpoint = first.endpoint
    identity = read_repository_identity(repo)
    assert identity is not None
    domain = RuntimeDomain.from_identity(identity, mode="production")
    first_generation = RuntimeLeaseManager(domain).read_generation().last_lease_generation
    _stop(first)

    second = connect_or_start(repo, client_kind="protocol")
    try:
        assert second.endpoint.lease_generation == first_generation + 1
        assert second.endpoint.service_instance_id != old_endpoint.service_instance_id
        with pytest.raises((OSError, EOFError, ConnectionError, TimeoutError, RuntimeError)):
            from contextor.core.live_state import LiveStateClient

            LiveStateClient(old_endpoint).ping()
    finally:
        _stop(second)


def test_malformed_or_foreign_endpoint_is_rejected_without_attach_or_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    path = endpoint_file(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"host": "127.0.0.1"}), encoding="utf-8")
    with pytest.raises(EndpointSchemaError):
        connect_or_start(repo)


def test_foreign_endpoint_identity_is_rejected_without_attach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _repo(tmp_path, monkeypatch)
    client = connect_or_start(repo, client_kind="protocol")
    path = endpoint_file(repo)
    original = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(original)
    payload["repo_id"] = "ctx_foreign"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        with pytest.raises(EndpointSchemaError):
            connect_or_start(repo)
    finally:
        path.write_text(json.dumps(original), encoding="utf-8")
        _stop(client)


def test_bind_crash_between_live_and_generation_writes_is_reconciled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    identity = read_repository_identity(repo)
    assert identity is not None
    domain = RuntimeDomain.from_identity(identity, mode="production")
    manager = RuntimeLeaseManager(domain)
    lease = manager.acquire()
    endpoint = LiveEndpoint(
        "127.0.0.1",
        43210,
        "00" * 32,
        pid=lease.service_pid,
        repo_id=identity.repo_id,
        root_path=str(repo.resolve()),
        runtime_domain_id=domain.domain_id,
        service_instance_id=lease.service_instance_id,
        lease_generation=lease.lease_generation,
        process_start_identity=lease.process_start_identity,
    )
    original_write = manager._write_generation

    def crash_after_live_write(_record):
        raise RuntimeError("simulated generation write crash")

    manager._write_generation = crash_after_live_write
    with pytest.raises(RuntimeError, match="generation write crash"):
        manager.bind_endpoint(lease, endpoint.fingerprint())
    manager._write_generation = original_write
    assert manager.read_live_lease().endpoint_fingerprint == endpoint.fingerprint()
    assert manager.read_generation().endpoint_fingerprint is None
    manager.reconcile_endpoint_binding(lease, endpoint.fingerprint())
    assert manager.read_generation().endpoint_fingerprint == endpoint.fingerprint()
    manager.release(lease)


def test_protocol_first_authority_has_single_durable_desktop_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    protocol = connect_or_start(repo, client_kind="protocol")
    identity = read_repository_identity(repo)
    assert identity is not None
    domain = RuntimeDomain.from_identity(identity, mode="production")
    manager = RuntimeLeaseManager(domain)
    old_lease = manager.read_live_lease()
    assert old_lease is not None
    old_desktop_identity = ProcessIdentity.current()
    desktop_a = connect_or_start(
        repo,
        client_kind="desktop",
        desktop_instance_id="desktop-a",
        owner_pid=os.getpid(),
        owner_token="desktop-a-token",
        desktop_process_start_identity=old_desktop_identity.process_start_identity,
    )
    try:
        assert desktop_a.is_owner is True
        claim = desktop_a.desktop_claim_status()["desktop_claim"]
        assert claim["desktop_instance_id"] == "desktop-a"
        assert claim["desktop_pid"] == old_desktop_identity.pid
        assert claim["desktop_process_start_identity"] == old_desktop_identity.process_start_identity
        with pytest.raises(SecondDesktopActive):
            connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-b")
        reconnect = connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-a")
        assert reconnect.is_owner is True
        mcp = connect_or_start(repo, client_kind="protocol")
        assert mcp.is_owner is False
        assert mcp.desktop_claim_status()["desktop_claim"]["desktop_instance_id"] == "desktop-a"
    finally:
        _stop(protocol)

    next_client = connect_or_start(repo, client_kind="protocol")
    try:
        assert next_client.endpoint.lease_generation == old_lease.lease_generation + 1
        assert next_client.desktop_claim_status()["desktop_claim"] is None
        with pytest.raises(LeaseNotOwner):
            manager.release_desktop_claim(old_lease, "desktop-a", old_desktop_identity)
        assert next_client.desktop_claim_status()["desktop_claim"] is None
    finally:
        _stop(next_client)


def test_second_desktop_rejected_from_verified_claim_when_live_requests_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    protocol = connect_or_start(repo, client_kind="protocol")
    desktop_a = connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-a")
    original_verified = runtime_module._verified_existing_client
    monkeypatch.setattr(runtime_module, "_verified_existing_client", lambda *_args, **_kwargs: None)
    try:
        with pytest.raises(RuntimeError, match="exited prematurely"):
            connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-b", timeout=0.5)
    finally:
        runtime_module._verified_existing_client = original_verified
        _stop(protocol)


def test_run_service_reconciles_bind_split_before_release_and_next_generation_bootstraps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    original_manager = runtime_module.RuntimeLeaseManager

    class FailAfterLiveBindManager(original_manager):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._fail_generation_bind = False

        def bind_endpoint(self, lease, endpoint_fingerprint):
            self._fail_generation_bind = True
            try:
                return super().bind_endpoint(lease, endpoint_fingerprint)
            finally:
                self._fail_generation_bind = False

        def _write_generation(self, record):
            if self._fail_generation_bind and record.endpoint_fingerprint is not None:
                raise RuntimeError("simulated durable generation bind failure")
            return super()._write_generation(record)

    monkeypatch.setattr(runtime_module, "RuntimeLeaseManager", FailAfterLiveBindManager)
    errors: list[BaseException] = []

    def invoke() -> None:
        try:
            runtime_module.run_service(repo)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()
    thread.join(timeout=15.0)
    assert not thread.is_alive()
    assert errors and "durable generation bind failure" in str(errors[0])

    identity = read_repository_identity(repo)
    assert identity is not None
    domain = RuntimeDomain.from_identity(identity, mode="production")
    manager = original_manager(domain)
    released = manager.read_generation()
    assert released.status == "released"
    assert manager.read_live_lease() is None
    assert not endpoint_file(repo).exists()

    replacement = connect_or_start(repo, client_kind="protocol", timeout=10.0)
    try:
        assert replacement.endpoint.lease_generation == released.last_lease_generation + 1
        assert manager.read_generation().status == "active"
    finally:
        _stop(replacement)


def test_foreign_live_endpoint_blocks_stale_takeover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    identity = read_repository_identity(repo)
    assert identity is not None
    domain = RuntimeDomain.from_identity(identity, mode="production")
    old_process = ProcessIdentity(11111, "start-a")
    verifier = AuthorityLivenessVerifier(domain)
    manager = RuntimeLeaseManager(
        domain,
        process_identity=old_process,
        liveness_verifier=verifier,
    )
    old_lease = manager.acquire()
    foreign_endpoint = LiveEndpoint(
        "127.0.0.1",
        43211,
        "00" * 32,
        pid=22222,
        repo_id=identity.repo_id,
        root_path=str(repo.resolve()),
        runtime_domain_id=domain.domain_id,
        service_instance_id="service-b",
        lease_generation=old_lease.lease_generation,
        process_start_identity="start-b",
    )

    def fake_process_identity(pid):
        if pid == old_lease.service_pid:
            return "old", "start-a", False
        return "new", "start-b", True

    class ForeignClient:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def authority_status(self):
            return {
                "status": "ok",
                "protocol_version": 3,
                "repo_id": foreign_endpoint.repo_id,
                "root_path": foreign_endpoint.root_path,
                "runtime_domain_id": foreign_endpoint.runtime_domain_id,
                "service_instance_id": foreign_endpoint.service_instance_id,
                "lease_generation": foreign_endpoint.lease_generation,
                "service_pid": foreign_endpoint.pid,
                "process_start_identity": foreign_endpoint.process_start_identity,
                "endpoint_fingerprint": foreign_endpoint.fingerprint(),
            }

    monkeypatch.setattr(runtime_module, "_process_identity", fake_process_identity)
    monkeypatch.setattr(runtime_module, "_read_endpoint", lambda *_args, **_kwargs: foreign_endpoint)
    monkeypatch.setattr(runtime_module, "LiveStateClient", ForeignClient)

    result = verifier.verify(old_lease)
    assert result.status is LivenessStatus.FOREIGN_LIVE
    assert result.confirmed_stale is False
    with pytest.raises(LeaseLivenessUnknown):
        manager.acquire()
    assert manager.read_generation().last_lease_generation == old_lease.lease_generation


def test_desktop_claim_replaces_dead_owner_and_rejects_unknown_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    service = connect_or_start(repo, client_kind="protocol")
    try:
        identity = read_repository_identity(repo)
        assert identity is not None
        domain = RuntimeDomain.from_identity(identity, mode="production")
        manager = RuntimeLeaseManager(domain)
        lease = manager.read_live_lease()
        assert lease is not None
        old_desktop = ProcessIdentity(999991, "desktop-old-start")
        new_desktop = ProcessIdentity.current()
        manager.claim_desktop(lease, "desktop-old", old_desktop)

        import contextor.core.live_state.runtime_lease as lease_module

        original_probe = lease_module._process_identity
        monkeypatch.setattr(
            lease_module,
            "_process_identity",
            lambda pid: ("old", old_desktop.process_start_identity, False)
            if pid == old_desktop.pid
            else original_probe(pid),
        )
        replacement = manager.claim_desktop(lease, "desktop-new", new_desktop)
        assert replacement["desktop_instance_id"] == "desktop-new"
        assert replacement["desktop_pid"] == new_desktop.pid
        with pytest.raises(LeaseNotOwner):
            manager.release_desktop_claim(lease, "desktop-old", old_desktop)

        monkeypatch.setattr(
            lease_module,
            "_process_identity",
            lambda _pid: (_ for _ in ()).throw(OSError("probe unavailable")),
        )
        with pytest.raises(LeaseLivenessUnknown):
            manager.claim_desktop(lease, "desktop-third", ProcessIdentity(999992, "third-start"))
        monkeypatch.setattr(lease_module, "_process_identity", original_probe)
    finally:
        _stop(service)


def test_acquire_liveness_probe_runs_outside_domain_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _repo(tmp_path, monkeypatch)
    service = connect_or_start(repo, client_kind="protocol")
    try:
        identity = read_repository_identity(repo)
        assert identity is not None
        domain = RuntimeDomain.from_identity(identity, mode="production")
        manager = RuntimeLeaseManager(domain)

        class ReentrantProbe:
            def verify(self, lease):
                assert manager.read_generation().last_lease_generation == lease.lease_generation
                return LivenessResult.live("probe completed outside domain lock")

        manager.liveness_verifier = ReentrantProbe()
        with pytest.raises(LeaseAlreadyHeld):
            manager.acquire()
    finally:
        _stop(service)
