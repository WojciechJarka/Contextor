STATUS=O1B_IMPLEMENTED_FOCUSED_TESTS_PASS
HEAD=68d0a504dc02eb195242ed9e49f2001b9178891c

FILES_CHANGED:
- contextor/mcp_backend_state.py
- contextor/mcp_backend_control.py
- tests/test_mcp_backend_owner.py
- tests/test_mcp_process_registry.py
walkthrough.md is this report and is not listed as a source/test change.

CONTEXTOR_PRE_EDIT:
- get_file_edit_context at canonical_revision=1609: contextor.mcp_backend_state module 405/1, workspace_sync=verified, syntax clean; contextor.mcp_backend_control module 409/1, workspace_sync=verified, syntax clean.
- Artifact blast radius: PersistentBackendRecord direct consumers are contextor.mcp_backend_control and tests.test_mcp_backend_control; read_backend_record direct consumers are control plus tests.test_mcp_backend_state and tests.test_mcp_shared_backend_server_mode.
- get_backend_status direct consumers include contextor.mcp_backend_cli, contextor.ui.gui, and tests.test_mcp_backend_control. Existing _BackendControlLock is the canonical transaction lock.
- get_symbol_lineage previews for PersistentBackendRecord, _BackendControlLock.__enter__, and get_backend_status resolved with complete metadata and fresh lineage / lineage_query_index at revision 1609.
- Existing state test module exists; no owner-claim test module existed, so tests/test_mcp_backend_owner.py was added.

OWNER_CLAIM_SCHEMA:
- BackendHostOwnerClaim is frozen and slotted; schema_version=1 and exact fields: backend_instance_id, host_owner_identity, host_kind, host_pid, host_executable, host_creation_time, owner_token, claimed_at.
- backend_instance_id is set from the authenticated-ready PersistentBackendRecord.instance_id.
- Required strings are non-empty and have no surrounding whitespace; PID and optional creation time are positive integers; claimed_at is finite and non-negative.
- BackendOwnerClaimError derives from BackendStateError. Exact-field from_dict rejects missing or extra fields.
- backend_owner_claim_path() resolves to %CONTEXTOR_STATE_DIR%\mcp_backend\owner.json. Owner state uses a separate file; backend.json schema is unchanged.
- _write_backend_owner_claim writes a unique temp file, json.dump, flush, fsync, then os.replace. Malformed owner.json fails closed through BackendOwnerClaimError.

OWNER_PROCESS_CLASSIFICATION:
- BackendHostOwnerProcessState is Literal["match", "stale", "unknown"].
- classify_backend_owner_process uses only probe_process_identity(claim.host_pid), never the legacy bool process_identity API.
- Probe dead -> stale; probe unknown -> unknown.
- Alive with missing/invalid claim or probe process-start identity -> unknown; valid creation mismatch -> stale.
- Exact creation identity plus an available executable filename mismatch -> stale; unavailable probe image does not prevent exact creation identity from matching.
- Exact required identity otherwise -> match. PID alone never yields match; no takeover policy is inside the classifier.

CLAIM_TRANSACTION:
- claim_backend_owner runs its complete operation under the existing _BackendControlLock.
- It first calls get_backend_status(probe_timeout=...). Only state=running, ready=True, record!=None proceeds; other status combinations raise BackendControlError.
- No current claim -> build current-process candidate, atomically write, return.
- Same backend instance: match plus equal host_owner_identity/host_kind/owner_token returns the existing claim without rewriting claimed_at; a different logical owner raises BackendOwnerAlreadyClaimed; unknown classification raises BackendOwnerLivenessUnknown without writing.
- BackendOwnerAlreadyClaimed and BackendOwnerLivenessUnknown both derive from BackendControlError.

TAKEOVER_SEMANTICS:
- Claim for another backend_instance_id is treated as stale metadata for the authenticated-ready current backend and replaced without probing old-owner liveness.
- For the same backend instance, only stale classification permits replacement. Unknown fails closed with the owner file unchanged. Match by a different logical owner is rejected.
- Candidate creation uses probe_process_identity(os.getpid()); liveness must be alive and process-start identity must be present. On this Windows host the claim contains host_creation_time. Probe image is preferred; sys.executable is only the image fallback and does not replace the required creation identity.
- No PID-only match, bearer/client identity, multi-client behavior, takeover lifecycle, watchdog, backend shutdown, GUI, autostart, server, or transport change was added.

RELEASE_SEMANTICS:
- release_backend_owner(expected) runs under _BackendControlLock and delegates to exact dataclass equality removal.
- Exact current claim -> removed and True; missing or different claim -> False.
- Release does not query backend status, classify liveness, stop the backend, or remove a newer claim.

EXISTING_BACKEND_BEHAVIOR_UNCHANGED=YES
Evidence: PersistentBackendRecord schema and existing process_identity/lease behavior are unchanged. start_backend, stop_backend, get_backend_status, mcp_server, bearer/auth, autostart, and GUI lifecycle bodies were not changed; only additive imports, new owner symbols/functions, and __all__ entries were added in the two allowed production files.

TARGETED_TESTS:
Command:
& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_owner.py tests/test_mcp_backend_state.py tests/test_mcp_process_registry.py tests/test_mcp_backend_control.py::test_status_without_record_is_stopped tests/test_mcp_backend_control.py::test_status_stale_record_never_probes_http tests/test_mcp_backend_control.py::test_status_live_owner_requires_authenticated_readiness tests/test_mcp_backend_control.py::test_start_returns_existing_ready_backend_without_spawn tests/test_mcp_backend_control.py::test_stop_without_record_is_idempotent tests/test_mcp_backend_control.py::test_control_lock_same_process_is_exclusive
Result: 75 passed, 1 third-party AuthlibDeprecationWarning, 6.23s. No full repository pytest suite was run.

CONTEXTOR_POST_EDIT:
- New/changed symbols fetched: BackendHostOwnerClaim, BackendOwnerClaimError, backend_owner_claim_path, _write_backend_owner_claim, read_backend_owner_claim, remove_backend_owner_claim_if_exact, classify_backend_owner_process, BackendOwnerAlreadyClaimed, BackendOwnerLivenessUnknown, claim_backend_owner, release_backend_owner.
- Final Contextor module/source freshness: canonical_state=fresh, canonical_revision=1619, workspace_sync=verified for mcp_backend_state.py and mcp_backend_control.py; test module also available, fresh and verified.
- LIVE events observed for both production files and both changed test files from desktop_watcher. Latest event cursor continuity=continuous, resync_required=false.
- Contextor reports syntax_errors=0, name_collisions=0, cycles=0, all fresh. No manual update_file call was made.

IMPLEMENTATION_RESULT=PASS
- Only the four listed source/test files were changed. No production changes were made outside the two allowed modules.
- git diff --check passed.

FULL_DIFFS:
```diff
--- a/contextor/mcp_backend_state.py
+++ b/contextor/mcp_backend_state.py
@@ -15 +15 @@
-from typing import Any, Mapping
+from typing import Any, Literal, Mapping
@@ -18 +18,4 @@
-from contextor.mcp_process_registry import process_identity
+from contextor.mcp_process_registry import (
+    probe_process_identity,
+    process_identity,
+)
@@ -21,0 +25 @@
+BACKEND_OWNER_CLAIM_SCHEMA_VERSION = 1
@@ -38,0 +43,12 @@
+_OWNER_CLAIM_FIELDS = {
+    "schema_version",
+    "backend_instance_id",
+    "host_owner_identity",
+    "host_kind",
+    "host_pid",
+    "host_executable",
+    "host_creation_time",
+    "owner_token",
+    "claimed_at",
+}
+
@@ -49,0 +66,4 @@
+
+
+class BackendOwnerClaimError(BackendStateError):
+    """The durable backend host-owner claim is malformed or unsafe."""
@@ -62,0 +83,16 @@
+            f"{field} must be a positive integer"
+        )
+    return value
+
+
+def _owner_text(value: Any, field: str) -> str:
+    if not isinstance(value, str) or not value.strip() or value != value.strip():
+        raise BackendOwnerClaimError(
+            f"{field} must be non-empty without surrounding whitespace"
+        )
+    return value
+
+
+def _owner_positive_int(value: Any, field: str) -> int:
+    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
+        raise BackendOwnerClaimError(
@@ -270,0 +307,171 @@
+@dataclass(
+    frozen=True,
+    slots=True,
+)
+class BackendHostOwnerClaim:
+    schema_version: int
+    backend_instance_id: str
+    host_owner_identity: str
+    host_kind: str
+    host_pid: int
+    host_executable: str
+    host_creation_time: int | None
+    owner_token: str
+    claimed_at: float
+
+    def __post_init__(self) -> None:
+        schema_version = _owner_positive_int(
+            self.schema_version,
+            "schema_version",
+        )
+        if schema_version != BACKEND_OWNER_CLAIM_SCHEMA_VERSION:
+            raise BackendOwnerClaimError(
+                "unsupported backend owner claim schema_version"
+            )
+
+        for field in (
+            "backend_instance_id",
+            "host_owner_identity",
+            "host_kind",
+            "host_executable",
+            "owner_token",
+        ):
+            object.__setattr__(
+                self,
+                field,
+                _owner_text(getattr(self, field), field),
+            )
+
+        object.__setattr__(
+            self,
+            "host_pid",
+            _owner_positive_int(self.host_pid, "host_pid"),
+        )
+
+        if self.host_creation_time is not None:
+            object.__setattr__(
+                self,
+                "host_creation_time",
+                _owner_positive_int(
+                    self.host_creation_time,
+                    "host_creation_time",
+                ),
+            )
+
+        if (
+            isinstance(self.claimed_at, bool)
+            or not isinstance(self.claimed_at, (int, float))
+        ):
+            raise BackendOwnerClaimError(
+                "claimed_at must be a timestamp"
+            )
+
+        try:
+            claimed_at = float(self.claimed_at)
+        except (OverflowError, ValueError) as exc:
+            raise BackendOwnerClaimError(
+                "claimed_at must be a finite non-negative timestamp"
+            ) from exc
+        if not math.isfinite(claimed_at) or claimed_at < 0:
+            raise BackendOwnerClaimError(
+                "claimed_at must be a finite non-negative timestamp"
+            )
+        object.__setattr__(self, "claimed_at", claimed_at)
+
+    def to_dict(self) -> dict[str, Any]:
+        return {
+            "schema_version": self.schema_version,
+            "backend_instance_id": self.backend_instance_id,
+            "host_owner_identity": self.host_owner_identity,
+            "host_kind": self.host_kind,
+            "host_pid": self.host_pid,
+            "host_executable": self.host_executable,
+            "host_creation_time": self.host_creation_time,
+            "owner_token": self.owner_token,
+            "claimed_at": self.claimed_at,
+        }
+
+    @classmethod
+    def from_dict(
+        cls,
+        payload: Mapping[str, Any],
+    ) -> "BackendHostOwnerClaim":
+        if (
+            not isinstance(payload, Mapping)
+            or set(payload) != _OWNER_CLAIM_FIELDS
+        ):
+            raise BackendOwnerClaimError(
+                "backend owner claim fields do not match schema"
+            )
+        return cls(**dict(payload))
+
+    @classmethod
+    def for_current_process(
+        cls,
+        *,
+        backend_instance_id: str,
+        host_owner_identity: str,
+        host_kind: str,
+        owner_token: str,
+    ) -> "BackendHostOwnerClaim":
+        probe = probe_process_identity(os.getpid())
+        if probe.state != "alive":
+            raise BackendOwnerClaimError(
+                "current host process liveness is not confirmed"
+            )
+        if probe.creation_time is None:
+            raise BackendOwnerClaimError(
+                "current host process start identity is unavailable"
+            )
+
+        executable = probe.image
+        if not isinstance(executable, str) or not executable.strip():
+            executable = sys.executable
+
+        return cls(
+            schema_version=BACKEND_OWNER_CLAIM_SCHEMA_VERSION,
+            backend_instance_id=backend_instance_id,
+            host_owner_identity=host_owner_identity,
+            host_kind=host_kind,
+            host_pid=os.getpid(),
+            host_executable=executable,
+            host_creation_time=probe.creation_time,
+            owner_token=owner_token,
+            claimed_at=time.time(),
+        )
+
+
+BackendHostOwnerProcessState = Literal[
+    "match",
+    "stale",
+    "unknown",
+]
+
+
+def classify_backend_owner_process(
+    claim: BackendHostOwnerClaim,
+) -> BackendHostOwnerProcessState:
+    probe = probe_process_identity(claim.host_pid)
+    if probe.state == "dead":
+        return "stale"
+    if probe.state != "alive":
+        return "unknown"
+    if (
+        claim.host_creation_time is None
+        or isinstance(probe.creation_time, bool)
+        or not isinstance(probe.creation_time, int)
+        or probe.creation_time <= 0
+    ):
+        return "unknown"
+    if claim.host_creation_time != probe.creation_time:
+        return "stale"
+    if (
+        isinstance(probe.image, str)
+        and probe.image.strip()
+        and os.path.basename(probe.image).casefold()
+        != os.path.basename(claim.host_executable).casefold()
+    ):
+        return "stale"
+    return "match"
+
+
@@ -281,0 +489,7 @@
+    )
+
+
+def backend_owner_claim_path() -> Path:
+    return (
+        backend_state_dir()
+        / "owner.json"
@@ -336,0 +551,31 @@
+def _write_backend_owner_claim(
+    claim: BackendHostOwnerClaim,
+) -> None:
+    if not isinstance(claim, BackendHostOwnerClaim):
+        raise BackendOwnerClaimError(
+            "backend owner claim must be a BackendHostOwnerClaim"
+        )
+
+    target = backend_owner_claim_path()
+    target.parent.mkdir(parents=True, exist_ok=True)
+    temporary = target.with_name(
+        f".{target.name}.{uuid.uuid4().hex}.tmp"
+    )
+    try:
+        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
+            json.dump(
+                claim.to_dict(),
+                stream,
+                sort_keys=True,
+                separators=(",", ":"),
+            )
+            stream.flush()
+            os.fsync(stream.fileno())
+        os.replace(temporary, target)
+    finally:
+        try:
+            temporary.unlink()
+        except FileNotFoundError:
+            pass
+
+
@@ -373,0 +619,19 @@
+def read_backend_owner_claim() -> BackendHostOwnerClaim | None:
+    try:
+        payload = json.loads(
+            backend_owner_claim_path().read_text(encoding="utf-8")
+        )
+    except FileNotFoundError:
+        return None
+    except (OSError, TypeError, ValueError) as exc:
+        raise BackendOwnerClaimError(
+            "persistent backend owner claim is malformed"
+        ) from exc
+
+    if not isinstance(payload, Mapping):
+        raise BackendOwnerClaimError(
+            "persistent backend owner claim must be an object"
+        )
+    return BackendHostOwnerClaim.from_dict(payload)
+
+
@@ -391,0 +656,13 @@
+    return True
+
+
+def remove_backend_owner_claim_if_exact(
+    expected: BackendHostOwnerClaim,
+) -> bool:
+    current = read_backend_owner_claim()
+    if current != expected:
+        return False
+    try:
+        backend_owner_claim_path().unlink()
+    except FileNotFoundError:
+        return False
@@ -690,0 +968 @@
+    "BACKEND_OWNER_CLAIM_SCHEMA_VERSION",
@@ -694,0 +973,3 @@
+    "BackendHostOwnerClaim",
+    "BackendOwnerClaimError",
+    "BackendHostOwnerProcessState",
@@ -698,0 +980 @@
+    "backend_owner_claim_path",
@@ -701,0 +984,2 @@
+    "classify_backend_owner_process",
+    "read_backend_owner_claim",
@@ -702,0 +987 @@
+    "remove_backend_owner_claim_if_exact",

--- a/contextor/mcp_backend_control.py
+++ b/contextor/mcp_backend_control.py
@@ -24,0 +25 @@
+    BackendHostOwnerClaim,
@@ -25,0 +27 @@
+    _write_backend_owner_claim,
@@ -26,0 +29 @@
+    classify_backend_owner_process,
@@ -27,0 +31,2 @@
+    read_backend_owner_claim,
+    remove_backend_owner_claim_if_exact,
@@ -54,0 +60,8 @@
+
+
+class BackendOwnerAlreadyClaimed(BackendControlError):
+    """Another live host owner already claims this backend instance."""
+
+
+class BackendOwnerLivenessUnknown(BackendControlError):
+    """The current backend host-owner process cannot be classified safely."""
@@ -246,0 +260,71 @@
+def claim_backend_owner(
+    *,
+    host_owner_identity: str,
+    host_kind: str,
+    owner_token: str,
+    probe_timeout: float = 2.0,
+    lock_timeout: float = 5.0,
+) -> BackendHostOwnerClaim:
+    with _BackendControlLock(
+        backend_control_lock_path(),
+        timeout=lock_timeout,
+    ):
+        status = get_backend_status(
+            probe_timeout=probe_timeout,
+        )
+        if (
+            status.state != "running"
+            or status.ready is not True
+            or status.record is None
+        ):
+            raise BackendControlError(
+                "backend owner claim requires an authenticated-ready backend"
+            )
+
+        current = read_backend_owner_claim()
+        if (
+            current is not None
+            and current.backend_instance_id == status.record.instance_id
+        ):
+            owner_state = classify_backend_owner_process(current)
+            if owner_state == "match":
+                if (
+                    current.host_owner_identity == host_owner_identity
+                    and current.host_kind == host_kind
+                    and current.owner_token == owner_token
+                ):
+                    return current
+                raise BackendOwnerAlreadyClaimed(
+                    "backend instance already has a live host owner"
+                )
+            if owner_state == "unknown":
+                raise BackendOwnerLivenessUnknown(
+                    "current backend host owner liveness is unknown"
+                )
+            if owner_state != "stale":
+                raise BackendOwnerLivenessUnknown(
+                    "current backend host owner state is invalid"
+                )
+
+        candidate = BackendHostOwnerClaim.for_current_process(
+            backend_instance_id=status.record.instance_id,
+            host_owner_identity=host_owner_identity,
+            host_kind=host_kind,
+            owner_token=owner_token,
+        )
+        _write_backend_owner_claim(candidate)
+        return candidate
+
+
+def release_backend_owner(
+    expected: BackendHostOwnerClaim,
+    *,
+    lock_timeout: float = 5.0,
+) -> bool:
+    with _BackendControlLock(
+        backend_control_lock_path(),
+        timeout=lock_timeout,
+    ):
+        return remove_backend_owner_claim_if_exact(expected)
+
+
@@ -1006,0 +1091,2 @@
+    "BackendOwnerAlreadyClaimed",
+    "BackendOwnerLivenessUnknown",
@@ -1009,0 +1096 @@
+    "claim_backend_owner",
@@ -1010,0 +1098 @@
+    "release_backend_owner",

--- /dev/null
+++ b/tests/test_mcp_backend_owner.py
@@ -0,0 +1,584 @@
+from __future__ import annotations
+
+import json
+import math
+import os
+import sys
+
+import pytest
+
+import contextor.mcp_backend_control as control
+import contextor.mcp_backend_state as state
+from contextor.mcp_process_registry import ProcessIdentityProbe
+
+
+def _claim(**changes) -> state.BackendHostOwnerClaim:
+    values = {
+        "schema_version": 1,
+        "backend_instance_id": "backend-current",
+        "host_owner_identity": "host-instance-1",
+        "host_kind": "desktop",
+        "host_pid": os.getpid(),
+        "host_executable": sys.executable,
+        "host_creation_time": 123456789,
+        "owner_token": "opaque-owner-token",
+        "claimed_at": 123.5,
+    }
+    values.update(changes)
+    return state.BackendHostOwnerClaim(**values)
+
+
+def _backend_record(tmp_path, instance_id="backend-current"):
+    return state.PersistentBackendRecord(
+        schema_version=1,
+        instance_id=instance_id,
+        server_role=state.BACKEND_SERVER_ROLE,
+        transport=state.BACKEND_TRANSPORT,
+        host="127.0.0.1",
+        port=8765,
+        pid=os.getpid(),
+        executable=sys.executable,
+        creation_time=123456789,
+        process_registry=str((tmp_path / "registry").resolve()),
+        started_at=1.0,
+    )
+
+
+def _install_ready_backend(monkeypatch, tmp_path, instance_id="backend-current"):
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    record = _backend_record(tmp_path, instance_id)
+    status = control.BackendStatus(
+        state="running",
+        ready=True,
+        detail="authenticated and ready",
+        record=record,
+    )
+    monkeypatch.setattr(
+        control,
+        "get_backend_status",
+        lambda *, probe_timeout: status,
+    )
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 777),
+    )
+    return record
+
+
+def test_owner_claim_round_trip():
+    expected = _claim()
+
+    actual = state.BackendHostOwnerClaim.from_dict(expected.to_dict())
+
+    assert actual == expected
+    assert actual.claimed_at == 123.5
+
+
+@pytest.mark.parametrize(
+    "mutate",
+    [
+        lambda payload: payload.update(extra="field"),
+        lambda payload: payload.pop("owner_token"),
+    ],
+)
+def test_owner_claim_rejects_non_exact_field_set(mutate):
+    payload = _claim().to_dict()
+    mutate(payload)
+
+    with pytest.raises(state.BackendOwnerClaimError):
+        state.BackendHostOwnerClaim.from_dict(payload)
+
+
+@pytest.mark.parametrize(
+    ("field", "value"),
+    [
+        ("schema_version", True),
+        ("schema_version", 1.0),
+        ("backend_instance_id", ""),
+        ("host_owner_identity", " "),
+        ("host_kind", "desktop "),
+        ("host_pid", 0),
+        ("host_pid", True),
+        ("host_executable", ""),
+        ("host_creation_time", 0),
+        ("host_creation_time", True),
+        ("owner_token", "  "),
+        ("claimed_at", True),
+        ("claimed_at", math.inf),
+        ("claimed_at", math.nan),
+        ("claimed_at", -0.01),
+    ],
+)
+def test_owner_claim_validates_fields(field, value):
+    with pytest.raises(state.BackendOwnerClaimError):
+        _claim(**{field: value})
+
+
+def test_owner_claim_atomic_read_write_uses_owner_json(tmp_path, monkeypatch):
+    state_dir = tmp_path / "state"
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(state_dir))
+    original_fsync = state.os.fsync
+    original_replace = state.os.replace
+    operations = []
+
+    def record_fsync(fd):
+        operations.append("fsync")
+        return original_fsync(fd)
+
+    def record_replace(source, target):
+        assert source.exists()
+        operations.append("replace")
+        return original_replace(source, target)
+
+    monkeypatch.setattr(state.os, "fsync", record_fsync)
+    monkeypatch.setattr(state.os, "replace", record_replace)
+    expected = _claim()
+
+    state._write_backend_owner_claim(expected)
+
+    path = state.backend_owner_claim_path()
+    assert path == state_dir / "mcp_backend" / "owner.json"
+    assert operations == ["fsync", "replace"]
+    assert state.read_backend_owner_claim() == expected
+    assert json.loads(path.read_text(encoding="utf-8")) == expected.to_dict()
+    assert list(path.parent.glob("*.tmp")) == []
+
+
+def test_malformed_owner_claim_fails_closed(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    path = state.backend_owner_claim_path()
+    path.parent.mkdir(parents=True)
+    path.write_text("not-json", encoding="utf-8")
+
+    with pytest.raises(state.BackendOwnerClaimError):
+        state.read_backend_owner_claim()
+
+
+def test_exact_owner_claim_removal_and_stale_expected_protection(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    old = _claim()
+    newer = _claim(owner_token="new-owner-token", claimed_at=456.0)
+    state._write_backend_owner_claim(newer)
+
+    assert state.remove_backend_owner_claim_if_exact(old) is False
+    assert state.read_backend_owner_claim() == newer
+    assert state.remove_backend_owner_claim_if_exact(newer) is True
+    assert state.read_backend_owner_claim() is None
+
+
+def test_current_process_factory_uses_complete_probe_identity(monkeypatch):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda pid: ProcessIdentityProbe("alive", "C:/Host/contextor.exe", 987654321),
+    )
+
+    claim = state.BackendHostOwnerClaim.for_current_process(
+        backend_instance_id="backend-1",
+        host_owner_identity="host-1",
+        host_kind="desktop",
+        owner_token="token-1",
+    )
+
+    assert claim.host_pid == os.getpid()
+    assert claim.host_executable == "C:/Host/contextor.exe"
+    assert claim.host_creation_time == 987654321
+    assert claim.backend_instance_id == "backend-1"
+
+
+@pytest.mark.skipif(os.name != "nt", reason="Windows exposes process start identity")
+def test_current_windows_process_factory_has_start_identity():
+    claim = state.BackendHostOwnerClaim.for_current_process(
+        backend_instance_id="backend-1",
+        host_owner_identity="host-1",
+        host_kind="desktop",
+        owner_token="token-1",
+    )
+
+    assert claim.host_pid == os.getpid()
+    assert claim.host_creation_time is not None
+    assert claim.host_creation_time > 0
+
+
+def test_current_process_factory_falls_back_only_for_image(monkeypatch):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", None, 987654321),
+    )
+
+    claim = state.BackendHostOwnerClaim.for_current_process(
+        backend_instance_id="backend-1",
+        host_owner_identity="host-1",
+        host_kind="desktop",
+        owner_token="token-1",
+    )
+
+    assert claim.host_executable == sys.executable
+    assert claim.host_creation_time == 987654321
+
+
+def test_current_process_factory_fails_closed_for_unknown_liveness(monkeypatch):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("unknown", None, None),
+    )
+
+    with pytest.raises(state.BackendOwnerClaimError, match="liveness"):
+        state.BackendHostOwnerClaim.for_current_process(
+            backend_instance_id="backend-1",
+            host_owner_identity="host-1",
+            host_kind="desktop",
+            owner_token="token-1",
+        )
+
+
+def test_current_process_factory_fails_closed_without_start_identity(monkeypatch):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, None),
+    )
+
+    with pytest.raises(state.BackendOwnerClaimError, match="start identity"):
+        state.BackendHostOwnerClaim.for_current_process(
+            backend_instance_id="backend-1",
+            host_owner_identity="host-1",
+            host_kind="desktop",
+            owner_token="token-1",
+        )
+
+
+@pytest.mark.parametrize(
+    ("probe", "expected"),
+    [
+        (ProcessIdentityProbe("dead", None, None), "stale"),
+        (ProcessIdentityProbe("unknown", None, None), "unknown"),
+        (ProcessIdentityProbe("alive", sys.executable, 321), "stale"),
+    ],
+)
+def test_owner_process_classification_dead_unknown_or_creation_mismatch(
+    monkeypatch,
+    probe,
+    expected,
+):
+    claim = _claim(host_creation_time=123)
+    monkeypatch.setattr(state, "probe_process_identity", lambda _pid: probe)
+
+    assert state.classify_backend_owner_process(claim) == expected
+
+
+def test_owner_process_classification_missing_start_identity_is_unknown(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123),
+    )
+
+    assert state.classify_backend_owner_process(
+        _claim(host_creation_time=None)
+    ) == "unknown"
+
+
+@pytest.mark.parametrize("creation_time", [None, 0, True])
+def test_owner_process_classification_missing_probe_start_identity_is_unknown(
+    monkeypatch,
+    creation_time,
+):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, creation_time),
+    )
+
+    assert state.classify_backend_owner_process(_claim()) == "unknown"
+
+
+def test_owner_process_classification_exact_creation_is_match(monkeypatch):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
+    )
+
+    assert state.classify_backend_owner_process(_claim()) == "match"
+
+
+def test_owner_process_classification_executable_filename_mismatch_is_stale(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", "C:/Other/host.exe", 123456789),
+    )
+
+    assert state.classify_backend_owner_process(
+        _claim(host_executable="C:/Contextor/contextor.exe")
+    ) == "stale"
+
+
+@pytest.mark.parametrize("image", [None, ""])
+def test_owner_process_classification_missing_probe_image_can_match(monkeypatch, image):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", image, 123456789),
+    )
+
+    assert state.classify_backend_owner_process(_claim()) == "match"
+
+
+def test_owner_process_classification_compares_executable_filename_only(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", "C:/Other/python.exe", 123456789),
+    )
+
+    assert state.classify_backend_owner_process(
+        _claim(host_executable="D:/Host/PYTHON.EXE")
+    ) == "match"
+
+
+def test_claim_backend_owner_acquires_when_no_claim_exists(
+    tmp_path,
+    monkeypatch,
+):
+    record = _install_ready_backend(monkeypatch, tmp_path)
+
+    claim = control.claim_backend_owner(
+        host_owner_identity="host-1",
+        host_kind="desktop",
+        owner_token="token-1",
+    )
+
+    assert claim.backend_instance_id == record.instance_id
+    assert claim.host_pid == os.getpid()
+    assert state.read_backend_owner_claim() == claim
+
+
+def test_claim_backend_owner_is_idempotent_for_same_logical_owner(
+    tmp_path,
+    monkeypatch,
+):
+    _install_ready_backend(monkeypatch, tmp_path)
+    existing = _claim(claimed_at=123.5)
+    state._write_backend_owner_claim(existing)
+    before = state.backend_owner_claim_path().read_bytes()
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
+    )
+    monkeypatch.setattr(
+        control,
+        "_write_backend_owner_claim",
+        lambda _claim: pytest.fail("idempotent claim must not be rewritten"),
+    )
+
+    result = control.claim_backend_owner(
+        host_owner_identity=existing.host_owner_identity,
+        host_kind=existing.host_kind,
+        owner_token=existing.owner_token,
+    )
+
+    assert result == existing
+    assert result.claimed_at == existing.claimed_at
+    assert state.backend_owner_claim_path().read_bytes() == before
+
+
+def test_claim_backend_owner_rejects_live_foreign_owner(
+    tmp_path,
+    monkeypatch,
+):
+    _install_ready_backend(monkeypatch, tmp_path)
+    existing = _claim(host_owner_identity="other-host", owner_token="other-token")
+    state._write_backend_owner_claim(existing)
+    before = state.backend_owner_claim_path().read_bytes()
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("alive", sys.executable, 123456789),
+    )
+
+    with pytest.raises(control.BackendOwnerAlreadyClaimed):
+        control.claim_backend_owner(
+            host_owner_identity="host-requester",
+            host_kind="desktop",
+            owner_token="new-token",
+        )
+
+    assert state.backend_owner_claim_path().read_bytes() == before
+
+
+@pytest.mark.parametrize(
+    "probe_for_existing",
+    [
+        ProcessIdentityProbe("dead", None, None),
+        ProcessIdentityProbe("alive", sys.executable, 333),
+    ],
+)
+def test_claim_backend_owner_takes_over_stale_owner(
+    tmp_path,
+    monkeypatch,
+    probe_for_existing,
+):
+    record = _install_ready_backend(monkeypatch, tmp_path)
+    existing = _claim(host_pid=876543, host_creation_time=222)
+    state._write_backend_owner_claim(existing)
+
+    def probe(pid):
+        if pid == existing.host_pid:
+            return probe_for_existing
+        return ProcessIdentityProbe("alive", sys.executable, 123456789)
+
+    monkeypatch.setattr(state, "probe_process_identity", probe)
+
+    replacement = control.claim_backend_owner(
+        host_owner_identity="replacement-host",
+        host_kind="desktop",
+        owner_token="replacement-token",
+    )
+
+    assert replacement.backend_instance_id == record.instance_id
+    assert replacement.host_owner_identity == "replacement-host"
+    assert replacement != existing
+    assert state.read_backend_owner_claim() == replacement
+
+
+def test_claim_backend_owner_unknown_liveness_fails_without_write(
+    tmp_path,
+    monkeypatch,
+):
+    _install_ready_backend(monkeypatch, tmp_path)
+    existing = _claim(host_pid=876543)
+    state._write_backend_owner_claim(existing)
+    before = state.backend_owner_claim_path().read_bytes()
+    monkeypatch.setattr(
+        state,
+        "probe_process_identity",
+        lambda _pid: ProcessIdentityProbe("unknown", None, None),
+    )
+
+    with pytest.raises(control.BackendOwnerLivenessUnknown):
+        control.claim_backend_owner(
+            host_owner_identity="replacement-host",
+            host_kind="desktop",
+            owner_token="replacement-token",
+        )
+
+    assert state.backend_owner_claim_path().read_bytes() == before
+
+
+def test_claim_backend_owner_replaces_claim_for_old_backend_instance(
+    tmp_path,
+    monkeypatch,
+):
+    record = _install_ready_backend(
+        monkeypatch,
+        tmp_path,
+        instance_id="backend-new",
+    )
+    existing = _claim(
+        backend_instance_id="backend-old",
+        host_pid=876543,
+    )
+    state._write_backend_owner_claim(existing)
+    probed_pids = []
+
+    def probe(pid):
+        probed_pids.append(pid)
+        return ProcessIdentityProbe("alive", sys.executable, 123456789)
+
+    monkeypatch.setattr(state, "probe_process_identity", probe)
+
+    replacement = control.claim_backend_owner(
+        host_owner_identity="host-new",
+        host_kind="desktop",
+        owner_token="token-new",
+    )
+
+    assert replacement.backend_instance_id == record.instance_id
+    assert replacement != existing
+    assert 876543 not in probed_pids
+    assert state.read_backend_owner_claim() == replacement
+
+
+@pytest.mark.parametrize(
+    ("state_name", "ready", "has_record"),
+    [
+        ("stopped", False, False),
+        ("unready", False, True),
+        ("running", False, True),
+        ("running", True, False),
+    ],
+)
+def test_claim_backend_owner_requires_authenticated_ready_backend(
+    tmp_path,
+    monkeypatch,
+    state_name,
+    ready,
+    has_record,
+):
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    record = _backend_record(tmp_path)
+    status = control.BackendStatus(
+        state=state_name,
+        ready=ready,
+        detail=state_name,
+        record=record if has_record else None,
+    )
+    monkeypatch.setattr(
+        control,
+        "get_backend_status",
+        lambda *, probe_timeout: status,
+    )
+
+    with pytest.raises(control.BackendControlError):
+        control.claim_backend_owner(
+            host_owner_identity="host-1",
+            host_kind="desktop",
+            owner_token="token-1",
+        )
+
+    assert state.read_backend_owner_claim() is None
+
+
+def test_release_backend_owner_removes_only_exact_claim(tmp_path, monkeypatch):
+    _install_ready_backend(monkeypatch, tmp_path)
+    expected = _claim()
+    state._write_backend_owner_claim(expected)
+    monkeypatch.setattr(
+        control,
+        "get_backend_status",
+        lambda **_kwargs: pytest.fail("release must not probe backend status"),
+    )
+
+    assert control.release_backend_owner(expected) is True
+    assert state.read_backend_owner_claim() is None
+
+
+def test_release_backend_owner_cannot_remove_newer_claim(tmp_path, monkeypatch):
+    _install_ready_backend(monkeypatch, tmp_path)
+    expected = _claim(owner_token="old-token")
+    current = _claim(owner_token="new-token", claimed_at=456.0)
+    state._write_backend_owner_claim(current)
+
+    assert control.release_backend_owner(expected) is False
+    assert state.read_backend_owner_claim() == current
+
+
+def test_release_backend_owner_without_claim_returns_false(tmp_path, monkeypatch):
+    _install_ready_backend(monkeypatch, tmp_path)
+
+    assert control.release_backend_owner(_claim()) is False

--- a/tests/test_mcp_process_registry.py
+++ b/tests/test_mcp_process_registry.py
@@ -88,0 +89,10 @@
+def test_windows_signaled_process_is_dead_and_closes_handle(monkeypatch):
+    kernel32 = _FakeKernel32(wait_result=0)
+    _patch_windows_probe(monkeypatch, kernel32)
+
+    result = registry._windows_process_identity_probe(1234)
+
+    assert result.state == "dead"
+    assert kernel32.closed_handles == [1]
+
+
```
