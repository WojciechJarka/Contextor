from __future__ import annotations

import json
import math
import os
import sys

import pytest

import contextor.mcp_backend_control as control
import contextor.mcp_backend_state as state
from contextor.mcp_process_registry import ProcessIdentityProbe


def _claim(**changes) -> state.BackendHostOwnerClaim:
    values = {
        "schema_version": 1,
        "backend_instance_id": "backend-current",
        "host_owner_identity": "host-instance-1",
        "host_kind": "desktop",
        "host_pid": os.getpid(),
        "host_executable": sys.executable,
        "host_creation_time": 123456789,
        "owner_token": "opaque-owner-token",
        "claimed_at": 123.5,
    }
    values.update(changes)
    return state.BackendHostOwnerClaim(**values)


def _backend_record(tmp_path, instance_id="backend-current"):
    return state.PersistentBackendRecord(
        schema_version=1,
        instance_id=instance_id,
        server_role=state.BACKEND_SERVER_ROLE,
        transport=state.BACKEND_TRANSPORT,
        host="127.0.0.1",
        port=8765,
        pid=os.getpid(),
        executable=sys.executable,
        creation_time=123456789,
        process_registry=str((tmp_path / "registry").resolve()),
        started_at=1.0,
    )


def _install_ready_backend(monkeypatch, tmp_path, instance_id="backend-current"):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    record = _backend_record(tmp_path, instance_id)
    status = control.BackendStatus(
        state="running",
        ready=True,
        detail="authenticated and ready",
        record=record,
    )
    monkeypatch.setattr(
        control,
        "get_backend_status",
        lambda *, probe_timeout: status,
    )
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 777),
    )
    return record


def test_owner_claim_round_trip():
    expected = _claim()

    actual = state.BackendHostOwnerClaim.from_dict(expected.to_dict())

    assert actual == expected
    assert actual.claimed_at == 123.5


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(extra="field"),
        lambda payload: payload.pop("owner_token"),
    ],
)
def test_owner_claim_rejects_non_exact_field_set(mutate):
    payload = _claim().to_dict()
    mutate(payload)

    with pytest.raises(state.BackendOwnerClaimError):
        state.BackendHostOwnerClaim.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("backend_instance_id", ""),
        ("host_owner_identity", " "),
        ("host_kind", "desktop "),
        ("host_pid", 0),
        ("host_pid", True),
        ("host_executable", ""),
        ("host_creation_time", 0),
        ("host_creation_time", True),
        ("owner_token", "  "),
        ("claimed_at", True),
        ("claimed_at", math.inf),
        ("claimed_at", math.nan),
        ("claimed_at", -0.01),
    ],
)
def test_owner_claim_validates_fields(field, value):
    with pytest.raises(state.BackendOwnerClaimError):
        _claim(**{field: value})


def test_owner_claim_atomic_read_write_uses_owner_json(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(state_dir))
    original_fsync = state.os.fsync
    original_replace = state.os.replace
    operations = []

    def record_fsync(fd):
        operations.append("fsync")
        return original_fsync(fd)

    def record_replace(source, target):
        assert source.exists()
        operations.append("replace")
        return original_replace(source, target)

    monkeypatch.setattr(state.os, "fsync", record_fsync)
    monkeypatch.setattr(state.os, "replace", record_replace)
    expected = _claim()

    state._write_backend_owner_claim(expected)

    path = state.backend_owner_claim_path()
    assert path == state_dir / "mcp_backend" / "owner.json"
    assert operations == ["fsync", "replace"]
    assert state.read_backend_owner_claim() == expected
    assert json.loads(path.read_text(encoding="utf-8")) == expected.to_dict()
    assert list(path.parent.glob("*.tmp")) == []


def test_malformed_owner_claim_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    path = state.backend_owner_claim_path()
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(state.BackendOwnerClaimError):
        state.read_backend_owner_claim()


def test_exact_owner_claim_removal_and_stale_expected_protection(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    old = _claim()
    newer = _claim(owner_token="new-owner-token", claimed_at=456.0)
    state._write_backend_owner_claim(newer)

    assert state.remove_backend_owner_claim_if_exact(old) is False
    assert state.read_backend_owner_claim() == newer
    assert state.remove_backend_owner_claim_if_exact(newer) is True
    assert state.read_backend_owner_claim() is None


def test_current_process_factory_uses_complete_probe_identity(monkeypatch):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda pid: ProcessIdentityProbe("alive", "C:/Host/contextor.exe", 987654321),
    )

    claim = state.BackendHostOwnerClaim.for_current_process(
        backend_instance_id="backend-1",
        host_owner_identity="host-1",
        host_kind="desktop",
        owner_token="token-1",
    )

    assert claim.host_pid == os.getpid()
    assert claim.host_executable == "C:/Host/contextor.exe"
    assert claim.host_creation_time == 987654321
    assert claim.backend_instance_id == "backend-1"


@pytest.mark.skipif(os.name != "nt", reason="Windows exposes process start identity")
def test_current_windows_process_factory_has_start_identity():
    claim = state.BackendHostOwnerClaim.for_current_process(
        backend_instance_id="backend-1",
        host_owner_identity="host-1",
        host_kind="desktop",
        owner_token="token-1",
    )

    assert claim.host_pid == os.getpid()
    assert claim.host_creation_time is not None
    assert claim.host_creation_time > 0


def test_current_process_factory_falls_back_only_for_image(monkeypatch):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", None, 987654321),
    )

    claim = state.BackendHostOwnerClaim.for_current_process(
        backend_instance_id="backend-1",
        host_owner_identity="host-1",
        host_kind="desktop",
        owner_token="token-1",
    )

    assert claim.host_executable == sys.executable
    assert claim.host_creation_time == 987654321


def test_current_process_factory_fails_closed_for_unknown_liveness(monkeypatch):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("unknown", None, None),
    )

    with pytest.raises(state.BackendOwnerClaimError, match="liveness"):
        state.BackendHostOwnerClaim.for_current_process(
            backend_instance_id="backend-1",
            host_owner_identity="host-1",
            host_kind="desktop",
            owner_token="token-1",
        )


def test_current_process_factory_fails_closed_without_start_identity(monkeypatch):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, None),
    )

    with pytest.raises(state.BackendOwnerClaimError, match="start identity"):
        state.BackendHostOwnerClaim.for_current_process(
            backend_instance_id="backend-1",
            host_owner_identity="host-1",
            host_kind="desktop",
            owner_token="token-1",
        )


@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        (ProcessIdentityProbe("dead", None, None), "stale"),
        (ProcessIdentityProbe("unknown", None, None), "unknown"),
        (ProcessIdentityProbe("alive", sys.executable, 321), "stale"),
    ],
)
def test_owner_process_classification_dead_unknown_or_creation_mismatch(
    monkeypatch,
    probe,
    expected,
):
    claim = _claim(host_creation_time=123)
    monkeypatch.setattr(state, "probe_process_identity", lambda _pid: probe)

    assert state.classify_backend_owner_process(claim) == expected


def test_owner_process_classification_missing_start_identity_is_unknown(
    monkeypatch,
):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123),
    )

    assert state.classify_backend_owner_process(
        _claim(host_creation_time=None)
    ) == "unknown"


@pytest.mark.parametrize("creation_time", [None, 0, True])
def test_owner_process_classification_missing_probe_start_identity_is_unknown(
    monkeypatch,
    creation_time,
):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, creation_time),
    )

    assert state.classify_backend_owner_process(_claim()) == "unknown"


def test_owner_process_classification_exact_creation_is_match(monkeypatch):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
    )

    assert state.classify_backend_owner_process(_claim()) == "match"


def test_owner_process_classification_executable_filename_mismatch_is_stale(
    monkeypatch,
):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", "C:/Other/host.exe", 123456789),
    )

    assert state.classify_backend_owner_process(
        _claim(host_executable="C:/Contextor/contextor.exe")
    ) == "stale"


@pytest.mark.parametrize("image", [None, ""])
def test_owner_process_classification_missing_probe_image_can_match(monkeypatch, image):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", image, 123456789),
    )

    assert state.classify_backend_owner_process(_claim()) == "match"


def test_owner_process_classification_compares_executable_filename_only(
    monkeypatch,
):
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", "C:/Other/python.exe", 123456789),
    )

    assert state.classify_backend_owner_process(
        _claim(host_executable="D:/Host/PYTHON.EXE")
    ) == "match"


def test_claim_backend_owner_acquires_when_no_claim_exists(
    tmp_path,
    monkeypatch,
):
    record = _install_ready_backend(monkeypatch, tmp_path)

    claim = control.claim_backend_owner(
        host_owner_identity="host-1",
        host_kind="desktop",
        owner_token="token-1",
    )

    assert claim.backend_instance_id == record.instance_id
    assert claim.host_pid == os.getpid()
    assert state.read_backend_owner_claim() == claim


def test_claim_backend_owner_is_idempotent_for_same_logical_owner(
    tmp_path,
    monkeypatch,
):
    _install_ready_backend(monkeypatch, tmp_path)
    existing = _claim(claimed_at=123.5)
    state._write_backend_owner_claim(existing)
    before = state.backend_owner_claim_path().read_bytes()
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
    )
    monkeypatch.setattr(
        control,
        "_write_backend_owner_claim",
        lambda _claim: pytest.fail("idempotent claim must not be rewritten"),
    )

    result = control.claim_backend_owner(
        host_owner_identity=existing.host_owner_identity,
        host_kind=existing.host_kind,
        owner_token=existing.owner_token,
    )

    assert result == existing
    assert result.claimed_at == existing.claimed_at
    assert state.backend_owner_claim_path().read_bytes() == before


def test_claim_backend_owner_rejects_live_foreign_owner(
    tmp_path,
    monkeypatch,
):
    _install_ready_backend(monkeypatch, tmp_path)
    existing = _claim(host_owner_identity="other-host", owner_token="other-token")
    state._write_backend_owner_claim(existing)
    before = state.backend_owner_claim_path().read_bytes()
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
    )

    with pytest.raises(control.BackendOwnerAlreadyClaimed):
        control.claim_backend_owner(
            host_owner_identity="host-requester",
            host_kind="desktop",
            owner_token="new-token",
        )

    assert state.backend_owner_claim_path().read_bytes() == before


@pytest.mark.parametrize(
    "probe_for_existing",
    [
        ProcessIdentityProbe("dead", None, None),
        ProcessIdentityProbe("alive", sys.executable, 333),
    ],
)
def test_claim_backend_owner_takes_over_stale_owner(
    tmp_path,
    monkeypatch,
    probe_for_existing,
):
    record = _install_ready_backend(monkeypatch, tmp_path)
    existing = _claim(host_pid=876543, host_creation_time=222)
    state._write_backend_owner_claim(existing)

    def probe(pid):
        if pid == existing.host_pid:
            return probe_for_existing
        return ProcessIdentityProbe("alive", sys.executable, 123456789)

    monkeypatch.setattr(state, "probe_process_identity", probe)

    replacement = control.claim_backend_owner(
        host_owner_identity="replacement-host",
        host_kind="desktop",
        owner_token="replacement-token",
    )

    assert replacement.backend_instance_id == record.instance_id
    assert replacement.host_owner_identity == "replacement-host"
    assert replacement != existing
    assert state.read_backend_owner_claim() == replacement


def test_claim_backend_owner_unknown_liveness_fails_without_write(
    tmp_path,
    monkeypatch,
):
    _install_ready_backend(monkeypatch, tmp_path)
    existing = _claim(host_pid=876543)
    state._write_backend_owner_claim(existing)
    before = state.backend_owner_claim_path().read_bytes()
    monkeypatch.setattr(
        state,
        "probe_process_identity",
        lambda _pid: ProcessIdentityProbe("unknown", None, None),
    )

    with pytest.raises(control.BackendOwnerLivenessUnknown):
        control.claim_backend_owner(
            host_owner_identity="replacement-host",
            host_kind="desktop",
            owner_token="replacement-token",
        )

    assert state.backend_owner_claim_path().read_bytes() == before


def test_claim_backend_owner_replaces_claim_for_old_backend_instance(
    tmp_path,
    monkeypatch,
):
    record = _install_ready_backend(
        monkeypatch,
        tmp_path,
        instance_id="backend-new",
    )
    existing = _claim(
        backend_instance_id="backend-old",
        host_pid=876543,
    )
    state._write_backend_owner_claim(existing)
    probed_pids = []

    def probe(pid):
        probed_pids.append(pid)
        return ProcessIdentityProbe("alive", sys.executable, 123456789)

    monkeypatch.setattr(state, "probe_process_identity", probe)

    replacement = control.claim_backend_owner(
        host_owner_identity="host-new",
        host_kind="desktop",
        owner_token="token-new",
    )

    assert replacement.backend_instance_id == record.instance_id
    assert replacement != existing
    assert 876543 not in probed_pids
    assert state.read_backend_owner_claim() == replacement


@pytest.mark.parametrize(
    ("state_name", "ready", "has_record"),
    [
        ("stopped", False, False),
        ("unready", False, True),
        ("running", False, True),
        ("running", True, False),
    ],
)
def test_claim_backend_owner_requires_authenticated_ready_backend(
    tmp_path,
    monkeypatch,
    state_name,
    ready,
    has_record,
):
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    record = _backend_record(tmp_path)
    status = control.BackendStatus(
        state=state_name,
        ready=ready,
        detail=state_name,
        record=record if has_record else None,
    )
    monkeypatch.setattr(
        control,
        "get_backend_status",
        lambda *, probe_timeout: status,
    )

    with pytest.raises(control.BackendControlError):
        control.claim_backend_owner(
            host_owner_identity="host-1",
            host_kind="desktop",
            owner_token="token-1",
        )

    assert state.read_backend_owner_claim() is None


def test_release_backend_owner_removes_only_exact_claim(tmp_path, monkeypatch):
    _install_ready_backend(monkeypatch, tmp_path)
    expected = _claim()
    state._write_backend_owner_claim(expected)
    monkeypatch.setattr(
        control,
        "get_backend_status",
        lambda **_kwargs: pytest.fail("release must not probe backend status"),
    )

    assert control.release_backend_owner(expected) is True
    assert state.read_backend_owner_claim() is None


def test_release_backend_owner_cannot_remove_newer_claim(tmp_path, monkeypatch):
    _install_ready_backend(monkeypatch, tmp_path)
    expected = _claim(owner_token="old-token")
    current = _claim(owner_token="new-token", claimed_at=456.0)
    state._write_backend_owner_claim(current)

    assert control.release_backend_owner(expected) is False
    assert state.read_backend_owner_claim() == current


def test_release_backend_owner_without_claim_returns_false(tmp_path, monkeypatch):
    _install_ready_backend(monkeypatch, tmp_path)

    assert control.release_backend_owner(_claim()) is False
