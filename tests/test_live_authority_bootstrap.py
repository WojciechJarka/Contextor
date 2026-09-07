from __future__ import annotations

import json
import os
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
from contextor.core.live_state.runtime_domain import RuntimeDomain
from contextor.core.live_state.runtime_lease import RuntimeLeaseManager
from contextor.core.repository_identity import read_repository_identity
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
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
