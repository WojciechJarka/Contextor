FILES_CHANGED=
contextor/core/live_state/__init__.py
contextor/core/live_state/ipc.py
contextor/core/live_state/runtime.py
contextor/core/live_state/runtime_lease.py
contextor/core/live_state/watcher.py
contextor/ui/gui.py
tests/live_state/test_runtime_lease.py
tests/test_live_state_ipc.py
tests/test_live_authority_bootstrap.py

TESTS_RUN=
& '.\\.venv\\Scripts\\python.exe' -m pytest -q tests/test_live_authority_bootstrap.py tests/live_state/test_runtime_lease.py tests/live_state/test_runtime_domain.py tests/test_gui_live_startup.py tests/test_live_desktop_integration.py tests/test_live_job_object.py

TEST_RESULTS=
78 passed, 1 skipped in 31.61s

RUNTIME_RESTART_REQUIRED=YES

EVIDENCE=
- Contextor LIVE canonical_revision=234; canonical_state= fresh; workspace_sync=verified; provenance=live.
- Ownership call-flow: runtime.connect_or_start and runtime.run_service; ipc.LiveEndpoint and CanonicalLiveServer; GUI ContextorGUI._refresh_repo_identity -> _start_live_watcher; watcher._recover_client.

ACTUAL_DIFF=
```diff
diff --git a/contextor/core/live_state/__init__.py b/contextor/core/live_state/__init__.py
index d5bef6b..6660e00 100644
--- a/contextor/core/live_state/__init__.py
+++ b/contextor/core/live_state/__init__.py
@@ -9,7 +9,13 @@ from .store import (
     save_snapshot,
 )
 from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LiveEndpoint, LiveStateClient
-from .runtime import connect, connect_or_start
+from .runtime import (
+    AuthorityLivenessVerifier,
+    EndpointSchemaError,
+    SecondDesktopActive,
+    connect,
+    connect_or_start,
+)
 from .watcher import DesktopLiveEventFeed, DesktopLiveWatcher
 from .hydration import (
     AuthoritativeRepositoryState,
@@ -31,6 +37,9 @@ __all__ = [
     "AuthoritativeRepositoryState",
     "connect",
     "connect_or_start",
+    "AuthorityLivenessVerifier",
+    "EndpointSchemaError",
+    "SecondDesktopActive",
     "hydrate_repository_engine",
     "resolve_authoritative_repository_state",
     "load_snapshot",

diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 25e3592..d8e549f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -4,16 +4,19 @@ from __future__ import annotations
 
 import copy
 from contextlib import contextmanager
+import hashlib
+import json
 import secrets
 import threading
 import time
 import uuid
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
-from typing import Any, Callable
+from typing import Any, Callable, Mapping
 
 
 LIVE_PROTOCOL_VERSION = 3
+LIVE_ENDPOINT_SCHEMA_VERSION = 2
 
 
 @dataclass(frozen=True)
@@ -22,10 +25,25 @@ class LiveEndpoint:
     port: int
     authkey_hex: str
     pid: int | None = None
+    service_pid: int | None = None
     owner_pid: int | None = None
     owner_token: str | None = None
     repo_id: str | None = None
     root_path: str | None = None
+    runtime_domain_id: str | None = None
+    service_instance_id: str | None = None
+    lease_generation: int | None = None
+    process_start_identity: str | None = None
+    desktop_instance_id: str | None = None
+    schema_version: int = LIVE_ENDPOINT_SCHEMA_VERSION
+
+    def __post_init__(self) -> None:
+        if self.service_pid is None:
+            object.__setattr__(self, "service_pid", self.pid)
+        elif self.pid is None:
+            object.__setattr__(self, "pid", self.service_pid)
+        elif self.pid != self.service_pid:
+            raise ValueError("LIVE endpoint pid and service_pid disagree")
 
     @property
     def address(self) -> tuple[str, int]:
@@ -35,6 +53,36 @@ class LiveEndpoint:
     def authkey(self) -> bytes:
         return bytes.fromhex(self.authkey_hex)
 
+    def identity_payload(self) -> dict[str, Any]:
+        return {
+            "schema_version": self.schema_version,
+            "host": self.host,
+            "port": self.port,
+            "authkey_hex": self.authkey_hex,
+            "pid": self.pid,
+            "service_pid": self.service_pid,
+            "repo_id": self.repo_id,
+            "root_path": self.root_path,
+            "runtime_domain_id": self.runtime_domain_id,
+            "service_instance_id": self.service_instance_id,
+            "lease_generation": self.lease_generation,
+            "process_start_identity": self.process_start_identity,
+        }
+
+    def fingerprint(self) -> str:
+        encoded = json.dumps(
+            self.identity_payload(), sort_keys=True, separators=(",", ":")
+        ).encode("utf-8")
+        return hashlib.sha256(encoded).hexdigest()
+
+    def to_dict(self) -> dict[str, Any]:
+        return {
+            **self.identity_payload(),
+            "owner_pid": self.owner_pid,
+            "owner_token": self.owner_token,
+            "desktop_instance_id": self.desktop_instance_id,
+        }
+
 
 ACTIVITY_EVENT_RETENTION = 10_000
 
@@ -188,6 +236,7 @@ class CanonicalLiveServer:
         persister: Callable[[Any, int], Any] | None = None,
         authkey: bytes | None = None,
         retention: int = ACTIVITY_EVENT_RETENTION,
+        authority_identity: Mapping[str, Any] | None = None,
     ):
         if revision is not None and (
             isinstance(revision, bool)
@@ -231,9 +280,24 @@ class CanonicalLiveServer:
         self._lock = threading.RLock()
         self._stop = threading.Event()
         self._authkey = authkey or secrets.token_bytes(32)
+        self._authority_identity = dict(authority_identity or {})
         self._listener = Listener(("127.0.0.1", 0), family="AF_INET", authkey=self._authkey)
         host, port = self._listener.address
-        self.endpoint = LiveEndpoint(str(host), int(port), self._authkey.hex())
+        self.endpoint = LiveEndpoint(
+            str(host),
+            int(port),
+            self._authkey.hex(),
+            pid=self._authority_identity.get("service_pid"),
+            owner_pid=self._authority_identity.get("owner_pid"),
+            owner_token=self._authority_identity.get("owner_token"),
+            repo_id=self._authority_identity.get("repo_id"),
+            root_path=self._authority_identity.get("root_path"),
+            runtime_domain_id=self._authority_identity.get("runtime_domain_id"),
+            service_instance_id=self._authority_identity.get("service_instance_id"),
+            lease_generation=self._authority_identity.get("lease_generation"),
+            process_start_identity=self._authority_identity.get("process_start_identity"),
+            desktop_instance_id=self._authority_identity.get("desktop_instance_id"),
+        )
 
     def _record_event(
         self,
@@ -348,6 +412,22 @@ class CanonicalLiveServer:
                     "revision": self._revision,
                     "available": self._state is not None,
                 }
+            if operation == "authority_status":
+                if not self._authority_identity:
+                    return {"status": "error", "error": "authority_identity_unavailable"}
+                return {
+                    "status": "ok",
+                    "protocol_version": LIVE_PROTOCOL_VERSION,
+                    "revision": self._revision,
+                    "repo_id": self._authority_identity.get("repo_id"),
+                    "root_path": self._authority_identity.get("root_path"),
+                    "runtime_domain_id": self._authority_identity.get("runtime_domain_id"),
+                    "service_instance_id": self._authority_identity.get("service_instance_id"),
+                    "lease_generation": self._authority_identity.get("lease_generation"),
+                    "service_pid": self._authority_identity.get("service_pid"),
+                    "process_start_identity": self._authority_identity.get("process_start_identity"),
+                    "endpoint_fingerprint": self.endpoint.fingerprint(),
+                }
             if operation == "snapshot":
                 return {"status": "ok", "revision": self._revision, "state": self._state}
             if operation == "publish":
@@ -735,6 +815,7 @@ class LiveStateClient:
         self.service_pid = service_pid if service_pid is not None else getattr(endpoint, "pid", None)
         self.owner_pid = owner_pid if owner_pid is not None else getattr(endpoint, "owner_pid", None)
         self.owner_token = owner_token if owner_token is not None else getattr(endpoint, "owner_token", None)
+        self.desktop_instance_id = getattr(endpoint, "desktop_instance_id", None)
 
     def request(
         self, operation: str, *, timeout: float = 30.0, **payload: Any
@@ -763,6 +844,9 @@ class LiveStateClient:
     def ping(self) -> dict[str, Any]:
         return self.request("ping")
 
+    def authority_status(self) -> dict[str, Any]:
+        return self.request("authority_status")
+
     def snapshot(self) -> dict[str, Any]:
         return self.request("snapshot")
 

diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 0bcc089..e9f829b 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -10,17 +10,46 @@ import sys
 import threading
 import time
 from pathlib import Path
+from typing import Any
 
 from contextor.core.paths import repo_cache_dir
 from contextor.core.repository_identity import (
     read_repository_identity,
     require_repository_identity,
 )
+from contextor.mcp_process_registry import process_identity as _process_identity
+from contextor.core.live_state.runtime_domain import RuntimeDomain
+from contextor.core.live_state.runtime_lease import (
+    LeaseRecoveryRequired,
+    LivenessResult,
+    LivenessStatus,
+    RuntimeLease,
+    RuntimeLeaseManager,
+)
 
-from .ipc import CanonicalLiveServer, CanonicalPersistenceConflict, LIVE_PROTOCOL_VERSION, LiveEndpoint, LiveStateClient
+from .ipc import (
+    CanonicalLiveServer,
+    CanonicalPersistenceConflict,
+    LIVE_ENDPOINT_SCHEMA_VERSION,
+    LIVE_PROTOCOL_VERSION,
+    LiveEndpoint,
+    LiveStateClient,
+)
 from .store import load_snapshot, migrate_legacy_snapshot, read_metadata, save_snapshot
 
 
+class EndpointSchemaError(RuntimeError):
+    """Endpoint metadata is malformed or belongs to another authority domain."""
+
+
+class SecondDesktopActive(RuntimeError):
+    """The repository is already active in a different Contextor Desktop."""
+
+
+def _canonical_root(value: str | Path) -> str:
+    return str(Path(value).expanduser().resolve())
+
+
 def _safe_current_trace_operation() -> str | None:
     try:
         from contextor.core.runtime_trace import current_trace_operation
@@ -154,42 +183,318 @@ def endpoint_file(repo_path: str | Path) -> Path:
     return repo_cache_dir(repo_path) / "live_endpoint.json"
 
 
-def _read_endpoint(repo_path: str | Path) -> LiveEndpoint | None:
+def _read_endpoint(repo_path: str | Path, *, strict: bool = False) -> LiveEndpoint | None:
+    path = endpoint_file(repo_path)
     try:
-        payload = json.loads(endpoint_file(repo_path).read_text(encoding="utf-8"))
-        pid = int(payload["pid"]) if "pid" in payload and payload["pid"] is not None else None
-        owner_pid = int(payload["owner_pid"]) if "owner_pid" in payload and payload["owner_pid"] is not None else None
-        owner_token = str(payload["owner_token"]) if "owner_token" in payload and payload["owner_token"] is not None else None
-        repo_id = str(payload["repo_id"]) if payload.get("repo_id") else None
-        root_path = str(payload["root_path"]) if payload.get("root_path") else None
-        return LiveEndpoint(
-            payload["host"],
-            int(payload["port"]),
-            payload["authkey_hex"],
+        payload = json.loads(path.read_text(encoding="utf-8"))
+        if not isinstance(payload, dict):
+            raise EndpointSchemaError("LIVE endpoint payload must be an object")
+        required = {
+            "schema_version",
+            "host",
+            "port",
+            "authkey_hex",
+            "pid",
+            "service_pid",
+            "repo_id",
+            "root_path",
+            "runtime_domain_id",
+            "service_instance_id",
+            "lease_generation",
+            "process_start_identity",
+        }
+        if not required.issubset(payload):
+            raise EndpointSchemaError("LIVE endpoint is missing required authority identity")
+        if int(payload["schema_version"]) != LIVE_ENDPOINT_SCHEMA_VERSION:
+            raise EndpointSchemaError("unsupported LIVE endpoint schema_version")
+        pid = int(payload["pid"])
+        service_pid = int(payload["service_pid"])
+        if service_pid != pid:
+            raise EndpointSchemaError("LIVE endpoint pid and service_pid disagree")
+        lease_generation = int(payload["lease_generation"])
+        port = int(payload["port"])
+        owner_pid_value = payload.get("owner_pid")
+        owner_pid = int(owner_pid_value) if owner_pid_value is not None else None
+        if pid <= 0 or lease_generation <= 0 or not (1 <= port <= 65535):
+            raise EndpointSchemaError("LIVE endpoint pid and lease_generation must be positive")
+        if owner_pid is not None and owner_pid <= 0:
+            raise EndpointSchemaError("LIVE endpoint owner_pid must be positive")
+        root_path = _canonical_root(payload["root_path"])
+        if not str(payload["repo_id"]).strip() or not str(payload["runtime_domain_id"]).strip():
+            raise EndpointSchemaError("LIVE endpoint identity fields must be non-empty")
+        if not str(payload["service_instance_id"]).strip() or not str(payload["process_start_identity"]).strip():
+            raise EndpointSchemaError("LIVE endpoint service identity fields must be non-empty")
+        endpoint = LiveEndpoint(
+            str(payload["host"]),
+            port,
+            str(payload["authkey_hex"]),
             pid=pid,
+            service_pid=service_pid,
             owner_pid=owner_pid,
-            owner_token=owner_token,
-            repo_id=repo_id,
+            owner_token=(str(payload["owner_token"]) if payload.get("owner_token") is not None else None),
+            repo_id=str(payload["repo_id"]),
             root_path=root_path,
+            runtime_domain_id=str(payload["runtime_domain_id"]),
+            service_instance_id=str(payload["service_instance_id"]),
+            lease_generation=lease_generation,
+            process_start_identity=str(payload["process_start_identity"]),
+            desktop_instance_id=(
+                str(payload["desktop_instance_id"])
+                if payload.get("desktop_instance_id") is not None
+                else None
+            ),
+            schema_version=int(payload["schema_version"]),
         )
-    except (OSError, ValueError, KeyError, TypeError):
+        endpoint.authkey
+        return endpoint
+    except FileNotFoundError:
         return None
+    except (OSError, ValueError, KeyError, TypeError, EndpointSchemaError) as exc:
+        if strict:
+            if isinstance(exc, EndpointSchemaError):
+                raise
+            raise EndpointSchemaError("LIVE endpoint metadata is malformed") from exc
+        return None
+
+
+def _production_domain(identity) -> RuntimeDomain:
+    return RuntimeDomain.from_identity(identity, mode="production")
+
+
+def _endpoint_matches_domain(endpoint: LiveEndpoint, domain: RuntimeDomain) -> bool:
+    return (
+        endpoint.schema_version == LIVE_ENDPOINT_SCHEMA_VERSION
+        and endpoint.repo_id == domain.repo_id
+        and endpoint.root_path == _canonical_root(domain.repo_root)
+        and endpoint.runtime_domain_id == domain.domain_id
+        and endpoint.service_instance_id is not None
+        and endpoint.lease_generation is not None
+        and endpoint.pid is not None
+        and endpoint.process_start_identity is not None
+    )
+
+
+def _status_matches_endpoint(status: dict[str, Any], endpoint: LiveEndpoint) -> bool:
+    return (
+        status.get("status") == "ok"
+        and status.get("protocol_version") == LIVE_PROTOCOL_VERSION
+        and status.get("repo_id") == endpoint.repo_id
+        and status.get("root_path") == endpoint.root_path
+        and status.get("runtime_domain_id") == endpoint.runtime_domain_id
+        and status.get("service_instance_id") == endpoint.service_instance_id
+        and status.get("lease_generation") == endpoint.lease_generation
+        and status.get("service_pid") == endpoint.pid
+        and status.get("process_start_identity") == endpoint.process_start_identity
+        and status.get("endpoint_fingerprint") == endpoint.fingerprint()
+    )
+
+
+class AuthorityLivenessVerifier:
+    """Composite process-start and authenticated authority-status verifier."""
+
+    def __init__(self, domain: RuntimeDomain):
+        self.domain = domain
+
+    def verify(self, lease: RuntimeLease) -> LivenessResult:
+        try:
+            _image, creation_time, alive = _process_identity(lease.service_pid)
+        except Exception as exc:  # pragma: no cover - platform probe boundary
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
+                None,
+                None,
+                None,
+                None,
+                f"process identity probe failed: {exc}",
+            )
+        process_matches = bool(alive and creation_time is not None and str(creation_time) == lease.process_start_identity)
+        process_stale = (not alive) or (creation_time is not None and not process_matches)
+        try:
+            endpoint = _read_endpoint(self.domain.repo_root, strict=True)
+        except EndpointSchemaError as exc:
+            endpoint = None
+            endpoint_reason = str(exc)
+        else:
+            endpoint_reason = "endpoint metadata unavailable"
+
+        if endpoint is None:
+            if process_stale:
+                return LivenessResult.stale(
+                    process_alive=bool(alive),
+                    process_identity_matches=process_matches,
+                    endpoint_available=False,
+                    endpoint_matches=False,
+                    reason=f"process is stale and authority endpoint is unavailable: {endpoint_reason}",
+                    endpoint_evidence_verified=True,
+                )
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
+                bool(alive),
+                process_matches,
+                False,
+                None,
+                f"authority endpoint is unavailable: {endpoint_reason}",
+            )
+
+        endpoint_matches = _endpoint_matches_domain(endpoint, self.domain) and (
+            endpoint.service_instance_id == lease.service_instance_id
+            and endpoint.lease_generation == lease.lease_generation
+            and endpoint.pid == lease.service_pid
+            and endpoint.process_start_identity == lease.process_start_identity
+        )
+        if not endpoint_matches:
+            if process_stale:
+                return LivenessResult.stale(
+                    process_alive=bool(alive),
+                    process_identity_matches=process_matches,
+                    endpoint_available=True,
+                    endpoint_matches=False,
+                    reason="stale process and mismatched authority endpoint identity",
+                    endpoint_evidence_verified=True,
+                )
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
+                bool(alive),
+                process_matches,
+                True,
+                False,
+                "authority endpoint identity does not match the lease",
+            )
+
+        try:
+            status = LiveStateClient(endpoint).authority_status()
+        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
+            if process_stale:
+                return LivenessResult.stale(
+                    process_alive=bool(alive),
+                    process_identity_matches=process_matches,
+                    endpoint_available=False,
+                    endpoint_matches=None,
+                    reason=f"stale process and unavailable authority status: {exc}",
+                    endpoint_evidence_verified=True,
+                )
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
+                bool(alive),
+                process_matches,
+                False,
+                None,
+                f"authority status unavailable: {exc}",
+            )
+
+        status_matches = _status_matches_endpoint(status, endpoint)
+        if process_matches and status_matches:
+            return LivenessResult.live("exact process identity and authority status match")
+        if process_stale and not status_matches:
+            return LivenessResult.stale(
+                process_alive=bool(alive),
+                process_identity_matches=process_matches,
+                endpoint_available=True,
+                endpoint_matches=False,
+                reason="stale process and mismatched authority status",
+                endpoint_evidence_verified=True,
+            )
+        return LivenessResult(
+            LivenessStatus.UNKNOWN,
+            bool(alive),
+            process_matches,
+            True,
+            status_matches,
+            "authority status did not prove the exact live owner",
+        )
+
+
+def _verified_existing_client(
+    root: Path,
+    identity,
+    domain: RuntimeDomain,
+    manager: RuntimeLeaseManager,
+    *,
+    desktop_instance_id: str | None = None,
+    owner_token: str | None = None,
+) -> LiveStateClient | None:
+    endpoint = _read_endpoint(root, strict=True)
+    if endpoint is None or not _endpoint_matches_domain(endpoint, domain):
+        return None
+    try:
+        live = manager.read_live_lease()
+        record = manager.read_generation()
+        if (
+            live is not None
+            and record.status == "active"
+            and live.service_instance_id == endpoint.service_instance_id
+            and live.lease_generation == endpoint.lease_generation
+            and live.service_pid == endpoint.pid
+            and live.process_start_identity == endpoint.process_start_identity
+            and live.endpoint_fingerprint == endpoint.fingerprint()
+            and record.endpoint_fingerprint is None
+        ):
+            manager.reconcile_endpoint_binding(live, endpoint.fingerprint())
+    except Exception:
+        return None
+    try:
+        image, creation_time, alive = _process_identity(endpoint.pid)
+    except Exception:
+        return None
+    if not alive or creation_time is None or str(creation_time) != endpoint.process_start_identity:
+        return None
+    try:
+        status = LiveStateClient(endpoint).authority_status()
+    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+        return None
+    if not _status_matches_endpoint(status, endpoint):
+        return None
+    try:
+        lease = manager.read_live_lease()
+        record = manager.read_generation()
+    except Exception:
+        return None
+    if lease is None or record.status != "active":
+        return None
+    if (
+        lease.service_instance_id != endpoint.service_instance_id
+        or lease.lease_generation != endpoint.lease_generation
+        or lease.service_pid != endpoint.pid
+        or lease.process_start_identity != endpoint.process_start_identity
+        or lease.endpoint_fingerprint != endpoint.fingerprint()
+        or record.last_service_instance_id != lease.service_instance_id
+        or record.last_lease_generation != lease.lease_generation
+        or record.endpoint_fingerprint != endpoint.fingerprint()
+    ):
+        return None
+    client = LiveStateClient(
+        endpoint,
+        is_owner=(
+            (
+                desktop_instance_id is not None
+                and endpoint.desktop_instance_id == desktop_instance_id
+            )
+            or (
+                desktop_instance_id is None
+                and endpoint.owner_token is not None
+                and endpoint.owner_token == owner_token
+            )
+        ),
+        service_pid=endpoint.pid,
+        owner_pid=endpoint.owner_pid,
+        owner_token=endpoint.owner_token,
+    )
+    return client
 
 
 def connect(repo_path: str | Path) -> LiveStateClient | None:
-    endpoint = _read_endpoint(repo_path)
-    if endpoint is None:
+    root = Path(repo_path).resolve()
+    identity = read_repository_identity(root)
+    if identity is None:
         return None
-    client = LiveStateClient(endpoint)
+    domain = _production_domain(identity)
+    manager = RuntimeLeaseManager(
+        domain,
+        liveness_verifier=AuthorityLivenessVerifier(domain),
+    )
     try:
-        status = client.ping()
-        return (
-            client
-            if status.get("status") == "ok"
-            and status.get("protocol_version") == LIVE_PROTOCOL_VERSION
-            else None
-        )
-    except (OSError, EOFError, ConnectionError):
+        return _verified_existing_client(root, identity, domain, manager)
+    except EndpointSchemaError:
         return None
 
 
@@ -201,30 +506,38 @@ def connect_existing_with_status(
 ) -> tuple[LiveStateClient | None, str]:
     """Reconnect briefly to an existing owner without starting a service."""
     root = Path(repo_path).resolve()
-    expected = _read_endpoint(root)
+    identity = read_repository_identity(root)
+    if identity is None:
+        return None, "endpoint_identity_unverified"
+    domain = _production_domain(identity)
+    manager = RuntimeLeaseManager(
+        domain,
+        liveness_verifier=AuthorityLivenessVerifier(domain),
+    )
+    try:
+        expected = _read_endpoint(root, strict=True)
+    except EndpointSchemaError:
+        return None, "endpoint_identity_unverified"
     if expected is None:
         return None, "no_live_service"
-    identity = read_repository_identity(root)
-    if (
-        identity is None
-        or expected.repo_id != identity.repo_id
-        or not expected.root_path
-        or Path(expected.root_path).expanduser().resolve() != root
-    ):
+    if not _endpoint_matches_domain(expected, domain):
         return None, "endpoint_identity_unverified"
 
     total_attempts = max(1, attempts)
     for attempt in range(total_attempts):
-        client = connect(root)
+        client = _verified_existing_client(root, identity, domain, manager)
         if client is not None:
-            current = _read_endpoint(root)
+            current = _read_endpoint(root, strict=True)
             if current != expected or client.endpoint != expected:
                 return None, "owner_identity_changed"
             return client, "connected"
         if attempt + 1 < total_attempts:
             time.sleep(max(0.0, retry_delay))
 
-    endpoint = _read_endpoint(root)
+    try:
+        endpoint = _read_endpoint(root, strict=True)
+    except EndpointSchemaError:
+        return None, "endpoint_identity_unverified"
     if endpoint != expected:
         return None, "owner_identity_changed"
     if (
@@ -305,93 +618,104 @@ NORMAL_CONNECT_TIMEOUT = DEFAULT_CONNECT_TIMEOUT
 COLD_START_INITIALIZATION_TIMEOUT = DEFAULT_COLD_START_TIMEOUT
 
 
+def _write_endpoint_atomic(endpoint: LiveEndpoint, root: Path) -> None:
+    target = endpoint_file(root)
+    target.parent.mkdir(parents=True, exist_ok=True)
+    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
+    payload = endpoint.to_dict()
+    try:
+        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
+            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
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
+def _remove_endpoint_if_exact(root: Path, endpoint: LiveEndpoint) -> None:
+    try:
+        current = _read_endpoint(root, strict=True)
+        if current is not None and current == endpoint:
+            endpoint_file(root).unlink()
+    except (OSError, FileNotFoundError, EndpointSchemaError):
+        pass
+
+
+def _authority_endpoint_from_server(server: CanonicalLiveServer, identity, domain: RuntimeDomain, lease: RuntimeLease, *, owner_pid: int | None, owner_token: str | None, desktop_instance_id: str | None) -> LiveEndpoint:
+    endpoint = server.endpoint
+    return LiveEndpoint(
+        endpoint.host,
+        endpoint.port,
+        endpoint.authkey_hex,
+        pid=lease.service_pid,
+        owner_pid=owner_pid,
+        owner_token=owner_token,
+        repo_id=identity.repo_id,
+        root_path=_canonical_root(identity.root_path),
+        runtime_domain_id=domain.domain_id,
+        service_instance_id=lease.service_instance_id,
+        lease_generation=lease.lease_generation,
+        process_start_identity=lease.process_start_identity,
+        desktop_instance_id=desktop_instance_id,
+    )
+
+
 def connect_or_start(
     repo_path: str | Path,
     *,
     owner_pid: int | None = None,
     owner_token: str | None = None,
+    desktop_instance_id: str | None = None,
+    client_kind: str = "protocol",
     timeout: float = DEFAULT_CONNECT_TIMEOUT,
     cold_start_timeout: float = DEFAULT_COLD_START_TIMEOUT,
 ) -> LiveStateClient:
-    root = Path(repo_path).resolve()
-    existing_ep = _read_endpoint(root)
-    existing = connect(root)
-    if existing is not None and existing_ep is not None:
-        # A. Matching owner token: same owner process reconnecting
+    root = Path(repo_path).expanduser().resolve()
+    identity = require_repository_identity(root)
+    domain = _production_domain(identity)
+    manager = RuntimeLeaseManager(
+        domain,
+        liveness_verifier=AuthorityLivenessVerifier(domain),
+    )
+    try:
+        endpoint = _read_endpoint(root, strict=True)
+    except EndpointSchemaError:
+        if endpoint_file(root).exists():
+            raise
+        endpoint = None
+    if endpoint is not None and not _endpoint_matches_domain(endpoint, domain):
+        raise EndpointSchemaError("LIVE endpoint belongs to another repository or runtime domain")
+
+    existing = _verified_existing_client(
+        root,
+        identity,
+        domain,
+        manager,
+        desktop_instance_id=desktop_instance_id,
+        owner_token=owner_token,
+    )
+    if existing is not None:
         if (
-            existing_ep.owner_token is not None
-            and owner_token is not None
-            and existing_ep.owner_token == owner_token
+            client_kind == "desktop"
+            and endpoint is not None
+            and endpoint.desktop_instance_id is not None
+            and endpoint.desktop_instance_id != desktop_instance_id
         ):
-            return LiveStateClient(
-                existing_ep,
-                is_owner=True,
-                service_pid=existing_ep.pid,
-                owner_pid=existing_ep.owner_pid,
-                owner_token=existing_ep.owner_token,
-            )
-        # B. Responsive endpoint with an owner_token (different or caller has none) -> unowned client
-        if existing_ep.owner_token is not None:
-            return LiveStateClient(
-                existing_ep,
-                is_owner=False,
-                service_pid=existing_ep.pid,
-                owner_pid=existing_ep.owner_pid,
-                owner_token=existing_ep.owner_token,
+            raise SecondDesktopActive(
+                "repository already active in another Contextor Desktop"
             )
-        # C. Responsive endpoint without owner_token:
-        # If owner_pid is present and alive -> unowned client
-        if existing_ep.owner_pid is not None and _is_pid_alive(existing_ep.owner_pid):
-            return LiveStateClient(
-                existing_ep,
-                is_owner=False,
-                service_pid=existing_ep.pid,
-                owner_pid=existing_ep.owner_pid,
-                owner_token=None,
-            )
-        # If owner_pid is None (legacy endpoint without token/pid) -> unowned client
-        if existing_ep.owner_pid is None:
-            return LiveStateClient(
-                existing_ep,
-                is_owner=False,
-                service_pid=existing_ep.pid,
-                owner_pid=None,
-                owner_token=None,
-            )
-        # D. Proven orphan (owner_pid recorded and known dead, and no owner_token): stop orphan and clean up
-        if existing_ep.owner_pid is not None and not _is_pid_alive(existing_ep.owner_pid):
-            try:
-                existing.request("shutdown", timeout=1.5)
-            except (OSError, EOFError, ConnectionError, RuntimeError, TimeoutError):
-                pass
-            if existing_ep.pid and _is_pid_alive(existing_ep.pid):
-                time.sleep(0.1)
-                if _is_pid_alive(existing_ep.pid):
-                    _terminate_pid_tree(existing_ep.pid)
-            try:
-                target = endpoint_file(root)
-                current = _read_endpoint(root)
-                if current is not None and current.pid == existing_ep.pid:
-                    target.unlink()
-            except (OSError, FileNotFoundError):
-                pass
+        return existing
 
-    # Clean up any stale unresponsive endpoint
-    stale_endpoint = _read_endpoint(root)
-    if stale_endpoint is not None:
-        # A live owner that is temporarily unable to answer (for example while
-        # executing a long update) is not a proven-dead service.  Never replace
-        # it or send a competing mutation merely because the liveness ping
-        # timed out; the caller must observe and retry later.
-        if stale_endpoint.pid is not None and _is_pid_alive(stale_endpoint.pid):
-            raise TimeoutError(
-                "Canonical LIVE service is busy but still owned by a live "
-                f"process (pid={stale_endpoint.pid}); replacement is unsafe."
-            )
-        try:
-            LiveStateClient(stale_endpoint).request("shutdown", timeout=1.5)
-        except (OSError, EOFError, ConnectionError, RuntimeError, TimeoutError):
-            pass
+    record = manager.read_generation()
+    live = manager.read_live_lease()
+    if live is None and record.status == "active":
+        raise LeaseRecoveryRequired(
+            "active durable authority has no live lease; recovery is required before startup"
+        )
 
     target = endpoint_file(root)
     target.parent.mkdir(parents=True, exist_ok=True)
@@ -400,22 +724,26 @@ def connect_or_start(
     deadline = time.monotonic() + effective_startup_budget
     lock_fd = None
     while time.monotonic() < deadline:
-        existing = connect(root)
-        if existing:
-            ep = _read_endpoint(root)
-            is_owner = (
-                owner_token is not None
+        existing = _verified_existing_client(
+            root,
+            identity,
+            domain,
+            manager,
+            desktop_instance_id=desktop_instance_id,
+            owner_token=owner_token,
+        )
+        if existing is not None:
+            ep = _read_endpoint(root, strict=True)
+            if (
+                client_kind == "desktop"
                 and ep is not None
-                and ep.owner_token is not None
-                and ep.owner_token == owner_token
-            )
-            return LiveStateClient(
-                ep or existing.endpoint,
-                is_owner=is_owner,
-                service_pid=ep.pid if ep else None,
-                owner_pid=ep.owner_pid if ep else None,
-                owner_token=ep.owner_token if ep else None,
-            )
+                and ep.desktop_instance_id is not None
+                and ep.desktop_instance_id != desktop_instance_id
+            ):
+                raise SecondDesktopActive(
+                    "repository already active in another Contextor Desktop"
+                )
+            return existing
         try:
             lock_fd = os.open(start_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
             break
@@ -426,34 +754,29 @@ def connect_or_start(
             except FileNotFoundError:
                 pass
             time.sleep(0.05)
-
     if lock_fd is None:
         raise TimeoutError(f"Could not claim Canonical LIVE startup lock for {root}")
 
+    proc = None
     try:
-        # Re-check connect right after acquiring the startup lock
-        existing = connect(root)
-        if existing:
-            ep = _read_endpoint(root)
-            is_owner = (
-                owner_token is not None
-                and ep is not None
-                and ep.owner_token is not None
-                and ep.owner_token == owner_token
-            )
-            return LiveStateClient(
-                ep or existing.endpoint,
-                is_owner=is_owner,
-                service_pid=ep.pid if ep else None,
-                owner_pid=ep.owner_pid if ep else None,
-                owner_token=ep.owner_token if ep else None,
-            )
+        existing = _verified_existing_client(
+            root,
+            identity,
+            domain,
+            manager,
+            desktop_instance_id=desktop_instance_id,
+            owner_token=owner_token,
+        )
+        if existing is not None:
+            return existing
 
         cmd = [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(root)]
         if owner_pid is not None:
             cmd.extend(["--owner-pid", str(owner_pid)])
         if owner_token is not None:
             cmd.extend(["--owner-token", str(owner_token)])
+        if desktop_instance_id is not None:
+            cmd.extend(["--desktop-instance-id", str(desktop_instance_id)])
 
         from contextor.core.paths import package_root
 
@@ -466,57 +789,39 @@ def connect_or_start(
             env["PYTHONPATH"] = pkg_root
 
         proc = _spawn_runtime_subprocess(cmd, root, env)
-
         spawn_deadline = time.monotonic() + effective_startup_budget
         while time.monotonic() < spawn_deadline:
-            client = connect(root)
-            if client:
-                ep = _read_endpoint(root)
-                if ep is not None:
-                    is_exact_proc = _is_same_or_descendant_pid(ep.pid, proc.pid)
-                    is_token_match = (
-                        owner_token is not None
-                        and ep.owner_token is not None
-                        and ep.owner_token == owner_token
-                    )
-                    if is_exact_proc and is_token_match:
-                        return LiveStateClient(
-                            ep,
-                            is_owner=True,
-                            service_pid=ep.pid,
-                            owner_pid=ep.owner_pid,
-                            owner_token=ep.owner_token,
-                        )
-                    if not is_exact_proc:
-                        if _is_pid_alive(proc.pid):
-                            _terminate_pid_tree(proc.pid)
-                        return LiveStateClient(
-                            ep,
-                            is_owner=False,
-                            service_pid=ep.pid,
-                            owner_pid=ep.owner_pid,
-                            owner_token=ep.owner_token,
-                        )
-                    return LiveStateClient(
-                        ep,
-                        is_owner=False,
-                        service_pid=ep.pid,
-                        owner_pid=ep.owner_pid,
-                        owner_token=ep.owner_token,
+            client = _verified_existing_client(
+                root,
+                identity,
+                domain,
+                manager,
+                desktop_instance_id=desktop_instance_id,
+                owner_token=owner_token,
+            )
+            if client is not None:
+                endpoint = _read_endpoint(root, strict=True)
+                if (
+                    client_kind == "desktop"
+                    and endpoint is not None
+                    and endpoint.desktop_instance_id is not None
+                    and endpoint.desktop_instance_id != desktop_instance_id
+                ):
+                    if proc is not None and _is_pid_alive(proc.pid):
+                        _terminate_pid_tree(proc.pid)
+                    raise SecondDesktopActive(
+                        "repository already active in another Contextor Desktop"
                     )
-
-            ret = proc.poll()
-            if ret is not None:
+                return client
+            if proc.poll() is not None:
                 raise RuntimeError(
-                    f"Canonical LIVE service process exited prematurely with code {ret} for {root}"
+                    f"Canonical LIVE service process exited prematurely with code {proc.returncode} for {root}"
                 )
-
             time.sleep(0.05)
-
-        if _is_pid_alive(proc.pid):
+        if proc is not None and _is_pid_alive(proc.pid):
             _terminate_pid_tree(proc.pid)
         raise TimeoutError(
-            f"Canonical LIVE service startup and canonical initialization timed out after {effective_startup_budget}s for {root}"
+            f"Canonical LIVE service startup and authority bootstrap timed out after {effective_startup_budget}s for {root}"
         )
     finally:
         try:
@@ -603,116 +908,173 @@ def run_service(
     repo_path: str | Path,
     owner_pid: int | None = None,
     owner_token: str | None = None,
+    desktop_instance_id: str | None = None,
 ) -> None:
-    root = Path(repo_path).resolve()
+    root = Path(repo_path).expanduser().resolve()
     identity = require_repository_identity(root)
-    cache = migrate_legacy_snapshot(root)
-    loaded = load_snapshot(
-        cache,
-        expected_repo_id=identity.repo_id,
-        expected_root_path=identity.root_path,
+    domain = _production_domain(identity)
+    manager = RuntimeLeaseManager(
+        domain,
+        liveness_verifier=AuthorityLivenessVerifier(domain),
     )
-    state = loaded[0] if loaded else None
-    if state is not None:
-        from contextor.core.analysis.incremental.materialization import (
-            ensure_module_usages,
-            module_usages_require_materialization,
+    lease = None
+    server = None
+    published_endpoint = None
+    try:
+        lease = manager.acquire()
+        cache = migrate_legacy_snapshot(root)
+        loaded = load_snapshot(
+            cache,
+            expected_repo_id=identity.repo_id,
+            expected_root_path=identity.root_path,
         )
-
-        if module_usages_require_materialization(state):
-            loaded_metadata = loaded[1]
-            from contextor.core.analysis.state_manager import FileStateManager
-            file_state_manager = FileStateManager(str(cache))
-            ensure_module_usages(state)
-            target_revision = loaded_metadata.revision + 1
-            file_state_payload = file_state_manager.build_payload(
-                loaded_metadata.state_id,
-                target_revision,
-            )
-            backfill_metadata = save_snapshot(
-                state,
-                cache,
-                loaded_metadata.state_id,
-                writer="live-service-symbol-calls-backfill",
-                repo_id=identity.repo_id,
-                root_path=identity.root_path,
-                exact_revision=target_revision,
-                file_state_payload=file_state_payload,
+        state = loaded[0] if loaded else None
+        if state is not None:
+            from contextor.core.analysis.incremental.materialization import (
+                ensure_module_usages,
+                module_usages_require_materialization,
             )
-    revision = (read_metadata(cache).revision if read_metadata(cache) else 0)
-    adapter_holder: dict[str, object] = {}
-    server = CanonicalLiveServer(
-        state,
-        revision=revision,
-        updater=_repository_updater(root, adapter_holder),
-        persister=_repository_persister(root, adapter_holder),
-    )
-    _safe_trace_event("LIVE", "SERVICE_START", repo=str(root), rev=server._revision)
-
-    if owner_pid is not None and owner_pid > 0:
-        if sys.platform == "win32":
-            import ctypes
-            SYNCHRONIZE = 0x00100000
-            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
-            owner_handle = ctypes.windll.kernel32.OpenProcess(
-                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, int(owner_pid)
-            )
-            if not owner_handle:
-                # Owner already exited before service began
-                server.close()
-                return
 
-            def _owner_watchdog() -> None:
-                try:
+            if module_usages_require_materialization(state):
+                loaded_metadata = loaded[1]
+                from contextor.core.analysis.state_manager import FileStateManager
+
+                file_state_manager = FileStateManager(str(cache))
+                ensure_module_usages(state)
+                target_revision = loaded_metadata.revision + 1
+                file_state_payload = file_state_manager.build_payload(
+                    loaded_metadata.state_id,
+                    target_revision,
+                )
+                save_snapshot(
+                    state,
+                    cache,
+                    loaded_metadata.state_id,
+                    writer="live-service-symbol-calls-backfill",
+                    repo_id=identity.repo_id,
+                    root_path=identity.root_path,
+                    exact_revision=target_revision,
+                    file_state_payload=file_state_payload,
+                )
+        revision = read_metadata(cache).revision if read_metadata(cache) else 0
+        adapter_holder: dict[str, object] = {}
+        authority_identity = {
+            "repo_id": identity.repo_id,
+            "root_path": _canonical_root(identity.root_path),
+            "runtime_domain_id": domain.domain_id,
+            "service_instance_id": lease.service_instance_id,
+            "lease_generation": lease.lease_generation,
+            "service_pid": lease.service_pid,
+            "process_start_identity": lease.process_start_identity,
+            "owner_pid": owner_pid,
+            "owner_token": owner_token,
+            "desktop_instance_id": desktop_instance_id,
+        }
+        server = CanonicalLiveServer(
+            state,
+            revision=revision,
+            updater=_repository_updater(root, adapter_holder),
+            persister=_repository_persister(root, adapter_holder),
+            authority_identity=authority_identity,
+        )
+        published_endpoint = _authority_endpoint_from_server(
+            server,
+            identity,
+            domain,
+            lease,
+            owner_pid=owner_pid,
+            owner_token=owner_token,
+            desktop_instance_id=desktop_instance_id,
+        )
+        server.endpoint = published_endpoint
+        _write_endpoint_atomic(published_endpoint, root)
+        manager.bind_endpoint(lease, published_endpoint.fingerprint())
+        current_endpoint = _read_endpoint(root, strict=True)
+        current_lease = manager.read_live_lease()
+        current_record = manager.read_generation()
+        if (
+            current_endpoint != published_endpoint
+            or current_lease is None
+            or current_lease.service_instance_id != published_endpoint.service_instance_id
+            or current_lease.lease_generation != published_endpoint.lease_generation
+            or current_lease.endpoint_fingerprint != published_endpoint.fingerprint()
+            or current_record.status != "active"
+            or current_record.endpoint_fingerprint != published_endpoint.fingerprint()
+        ):
+            raise RuntimeError("LIVE endpoint and RuntimeLease identity parity verification failed")
+        _safe_trace_event(
+            "LIVE",
+            "AUTHORITY_READY",
+            repo=str(root),
+            domain_id=domain.domain_id,
+            service_instance_id=lease.service_instance_id,
+            lease_generation=lease.lease_generation,
+        )
+
+        if owner_pid is not None and owner_pid > 0:
+            if sys.platform == "win32":
+                import ctypes
+
+                SYNCHRONIZE = 0x00100000
+                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
+                owner_handle = ctypes.windll.kernel32.OpenProcess(
+                    SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION,
+                    False,
+                    int(owner_pid),
+                )
+                if not owner_handle:
+                    return
+
+                def _owner_watchdog() -> None:
+                    try:
+                        while not server._stop.wait(0.75):
+                            res = ctypes.windll.kernel32.WaitForSingleObject(owner_handle, 0)
+                            if res == 0:
+                                server.close()
+                                break
+                    finally:
+                        ctypes.windll.kernel32.CloseHandle(owner_handle)
+            else:
+
+                def _owner_watchdog() -> None:
                     while not server._stop.wait(0.75):
-                        res = ctypes.windll.kernel32.WaitForSingleObject(owner_handle, 0)
-                        if res == 0:  # WAIT_OBJECT_0: owner process terminated
+                        if not _is_pid_alive(owner_pid):
                             server.close()
                             break
-                finally:
-                    ctypes.windll.kernel32.CloseHandle(owner_handle)
-        else:
-            def _owner_watchdog() -> None:
-                while not server._stop.wait(0.75):
-                    if not _is_pid_alive(owner_pid):
-                        server.close()
-                        break
-
-        watchdog = threading.Thread(
-            target=_owner_watchdog,
-            name=f"contextor-live-watchdog-{owner_pid}",
-            daemon=True,
-        )
-        watchdog.start()
 
-    target = endpoint_file(root)
-    target.parent.mkdir(parents=True, exist_ok=True)
-    temporary = target.with_suffix(f".{os.getpid()}.tmp")
-    payload: dict[str, Any] = {
-        "host": server.endpoint.host,
-        "port": server.endpoint.port,
-        "authkey_hex": server.endpoint.authkey_hex,
-        "pid": os.getpid(),
-        "repo_id": identity.repo_id,
-        "root_path": identity.root_path,
-    }
-    if owner_pid is not None:
-        payload["owner_pid"] = int(owner_pid)
-    if owner_token is not None:
-        payload["owner_token"] = str(owner_token)
-    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
-    os.replace(temporary, target)
-    try:
+            threading.Thread(
+                target=_owner_watchdog,
+                name=f"contextor-live-watchdog-{owner_pid}",
+                daemon=True,
+            ).start()
         server.serve_forever()
+    except Exception as exc:
+        _safe_trace_event(
+            "LIVE",
+            "AUTHORITY_BOOTSTRAP_FAIL",
+            repo=str(root),
+            error=str(exc),
+            service_instance_id=getattr(lease, "service_instance_id", None),
+            lease_generation=getattr(lease, "lease_generation", None),
+        )
+        raise
     finally:
-        _safe_trace_event("LIVE", "SERVICE_END", repo=str(root), rev=server._revision)
-        server.close()
-        try:
-            current_ep = _read_endpoint(root)
-            if current_ep is not None and current_ep.pid == os.getpid():
-                target.unlink()
-        except (OSError, FileNotFoundError):
-            pass
+        if server is not None:
+            server.close()
+        if lease is not None:
+            try:
+                manager.release(lease)
+            except Exception as exc:
+                _safe_trace_event(
+                    "LIVE",
+                    "AUTHORITY_RELEASE_FAIL",
+                    repo=str(root),
+                    error=str(exc),
+                    service_instance_id=lease.service_instance_id,
+                    lease_generation=lease.lease_generation,
+                )
+        if published_endpoint is not None:
+            _remove_endpoint_if_exact(root, published_endpoint)
 
 
 def main() -> None:
@@ -720,8 +1082,14 @@ def main() -> None:
     parser.add_argument("--repo", required=True)
     parser.add_argument("--owner-pid", type=int, default=None)
     parser.add_argument("--owner-token", type=str, default=None)
+    parser.add_argument("--desktop-instance-id", type=str, default=None)
     args = parser.parse_args()
-    run_service(args.repo, owner_pid=args.owner_pid, owner_token=args.owner_token)
+    run_service(
+        args.repo,
+        owner_pid=args.owner_pid,
+        owner_token=args.owner_token,
+        desktop_instance_id=args.desktop_instance_id,
+    )
 
 
 if __name__ == "__main__":

diff --git a/contextor/core/live_state/runtime_lease.py b/contextor/core/live_state/runtime_lease.py
index 3f02e09..0940052 100644
--- a/contextor/core/live_state/runtime_lease.py
+++ b/contextor/core/live_state/runtime_lease.py
@@ -32,7 +32,7 @@ from contextor.mcp_process_registry import process_identity as _process_identity
 
 RUNTIME_LEASE_SCHEMA_VERSION = 1
 AUTHORITY_GENERATION_SCHEMA_VERSION = 1
-GenerationStatus = Literal["never_acquired", "allocated", "released", "fenced"]
+GenerationStatus = Literal["never_acquired", "reserved", "active", "released", "fenced"]
 
 _RESOURCE_KEYS = (
     "repo_root",
@@ -67,6 +67,9 @@ _GENERATION_FIELDS = {
     "repo_root_fingerprint",
     "last_lease_generation",
     "last_service_instance_id",
+    "service_pid",
+    "process_start_identity",
+    "endpoint_fingerprint",
     "status",
     "fenced_service_instance_id",
     "fenced_lease_generation",
@@ -87,6 +90,10 @@ class LeaseLivenessUnknown(RuntimeLeaseError):
     """Liveness was not strong enough to permit a takeover."""
 
 
+class LeaseRecoveryRequired(RuntimeLeaseError):
+    """Durable authority state requires recovery before another owner may start."""
+
+
 class LeaseNotOwner(RuntimeLeaseError):
     """The supplied service instance/generation is not the current owner."""
 
@@ -242,6 +249,7 @@ class LivenessResult:
     endpoint_available: bool | None
     endpoint_matches: bool | None
     reason: str
+    endpoint_evidence_verified: bool = False
 
     def __post_init__(self) -> None:
         if not isinstance(self.status, LivenessStatus):
@@ -251,7 +259,9 @@ class LivenessResult:
     @property
     def confirmed_stale(self) -> bool:
         process_evidence = self.process_alive is False or self.process_identity_matches is False
-        endpoint_evidence = self.endpoint_available is False or self.endpoint_matches is False
+        endpoint_evidence = self.endpoint_evidence_verified and (
+            self.endpoint_available is False or self.endpoint_matches is False
+        )
         return self.status is LivenessStatus.STALE and process_evidence and endpoint_evidence
 
     @classmethod
@@ -267,6 +277,7 @@ class LivenessResult:
         endpoint_available: bool | None,
         endpoint_matches: bool | None,
         reason: str,
+        endpoint_evidence_verified: bool = False,
     ) -> "LivenessResult":
         return cls(
             LivenessStatus.STALE,
@@ -275,6 +286,7 @@ class LivenessResult:
             endpoint_available,
             endpoint_matches,
             reason,
+            endpoint_evidence_verified,
         )
 
 
@@ -299,12 +311,13 @@ class DefaultLivenessVerifier:
                 f"process identity probe failed: {exc}",
             )
         if not alive:
-            return LivenessResult.stale(
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
                 process_alive=False,
                 process_identity_matches=False,
-                endpoint_available=False,
-                endpoint_matches=False,
-                reason="recorded service process is confirmed dead",
+                endpoint_available=None,
+                endpoint_matches=None,
+                reason="recorded service process is dead; authority endpoint was not probed",
             )
         if creation_time is None:
             return LivenessResult(
@@ -317,12 +330,13 @@ class DefaultLivenessVerifier:
             )
         matches = str(creation_time) == lease.process_start_identity
         if not matches:
-            return LivenessResult.stale(
+            return LivenessResult(
+                LivenessStatus.UNKNOWN,
                 process_alive=True,
                 process_identity_matches=False,
-                endpoint_available=False,
-                endpoint_matches=False,
-                reason="PID is live but process-start identity does not match",
+                endpoint_available=None,
+                endpoint_matches=None,
+                reason="PID start identity does not match; authority endpoint was not probed",
             )
         if lease.endpoint_fingerprint is not None:
             return LivenessResult(
@@ -337,7 +351,7 @@ class DefaultLivenessVerifier:
             LivenessStatus.LIVE,
             True,
             True,
-            False,
+            None,
             None,
             "process-start identity matches; endpoint is not yet bound",
         )
@@ -484,6 +498,9 @@ class AuthorityGenerationRecord:
     repo_root_fingerprint: str
     last_lease_generation: int
     last_service_instance_id: str | None
+    service_pid: int | None
+    process_start_identity: str | None
+    endpoint_fingerprint: str | None
     status: GenerationStatus
     fenced_service_instance_id: str | None
     fenced_lease_generation: int | None
@@ -508,24 +525,59 @@ class AuthorityGenerationRecord:
             "last_lease_generation",
             _positive_int(self.last_lease_generation, field="last_lease_generation", allow_zero=True),
         )
-        if self.status not in ("never_acquired", "allocated", "released", "fenced"):
+        if self.status not in ("never_acquired", "reserved", "active", "released", "fenced"):
             raise RuntimeLeaseError("invalid authority-generation status")
-        if self.status == "never_acquired" and self.last_lease_generation != 0:
-            raise RuntimeLeaseError("never_acquired generation must be zero")
-        if self.last_lease_generation == 0 and self.last_service_instance_id is not None:
-            raise RuntimeLeaseError("generation zero cannot have a service instance")
-        for field in ("last_service_instance_id", "fenced_service_instance_id"):
+        for field in ("last_service_instance_id", "fenced_service_instance_id", "process_start_identity"):
             value = getattr(self, field)
             if value is not None:
                 object.__setattr__(self, field, _non_empty_text(value, field=field))
+        if self.service_pid is not None:
+            object.__setattr__(self, "service_pid", _positive_int(self.service_pid, field="service_pid"))
+        if self.endpoint_fingerprint is not None:
+            object.__setattr__(
+                self,
+                "endpoint_fingerprint",
+                _non_empty_text(self.endpoint_fingerprint, field="endpoint_fingerprint"),
+            )
+        current_identity_complete = (
+            self.last_service_instance_id is not None
+            and self.service_pid is not None
+            and self.process_start_identity is not None
+        )
+        if self.status == "never_acquired":
+            if self.last_lease_generation != 0 or any(
+                value is not None
+                for value in (
+                    self.last_service_instance_id,
+                    self.service_pid,
+                    self.process_start_identity,
+                    self.endpoint_fingerprint,
+                    self.fenced_service_instance_id,
+                    self.fenced_lease_generation,
+                )
+            ):
+                raise RuntimeLeaseError("never_acquired generation must have no owner or fence identity")
+        else:
+            if self.last_lease_generation == 0 or not current_identity_complete:
+                raise RuntimeLeaseError("generation status requires complete current owner identity")
+        fence_pair_complete = self.fenced_service_instance_id is not None and self.fenced_lease_generation is not None
+        if self.status in ("reserved", "active") and (
+            self.fenced_service_instance_id is not None or self.fenced_lease_generation is not None
+        ):
+            raise RuntimeLeaseError("reserved/active generation cannot carry a fence pair")
+        if self.status in ("released", "fenced") and not fence_pair_complete:
+            raise RuntimeLeaseError("released/fenced generation requires a complete fence pair")
+        if fence_pair_complete and (
+            self.fenced_service_instance_id != self.last_service_instance_id
+            or self.fenced_lease_generation != self.last_lease_generation
+        ):
+            raise RuntimeLeaseError("fence pair must match the durable owner generation")
         if self.fenced_lease_generation is not None:
             object.__setattr__(
                 self,
                 "fenced_lease_generation",
                 _positive_int(self.fenced_lease_generation, field="fenced_lease_generation"),
             )
-            if self.fenced_service_instance_id is None:
-                raise RuntimeLeaseError("fenced generation requires a fenced service instance")
         object.__setattr__(self, "updated_at", _timestamp(self.updated_at, field="updated_at"))
         fingerprints = tuple(self.resource_root_fingerprints)
         if tuple(name for name, _ in fingerprints) != _RESOURCE_KEYS:
@@ -553,6 +605,9 @@ class AuthorityGenerationRecord:
             repo_root_fingerprint=dict(fingerprints)["repo_root"],
             last_lease_generation=0,
             last_service_instance_id=None,
+            service_pid=None,
+            process_start_identity=None,
+            endpoint_fingerprint=None,
             status="never_acquired",
             fenced_service_instance_id=None,
             fenced_lease_generation=None,
@@ -579,6 +634,9 @@ class AuthorityGenerationRecord:
             "repo_root_fingerprint": self.repo_root_fingerprint,
             "last_lease_generation": self.last_lease_generation,
             "last_service_instance_id": self.last_service_instance_id,
+            "service_pid": self.service_pid,
+            "process_start_identity": self.process_start_identity,
+            "endpoint_fingerprint": self.endpoint_fingerprint,
             "status": self.status,
             "fenced_service_instance_id": self.fenced_service_instance_id,
             "fenced_lease_generation": self.fenced_lease_generation,
@@ -602,6 +660,9 @@ class AuthorityGenerationRecord:
             repo_root_fingerprint=payload["repo_root_fingerprint"],
             last_lease_generation=payload["last_lease_generation"],
             last_service_instance_id=payload["last_service_instance_id"],
+            service_pid=payload["service_pid"],
+            process_start_identity=payload["process_start_identity"],
+            endpoint_fingerprint=payload["endpoint_fingerprint"],
             status=payload["status"],
             fenced_service_instance_id=payload["fenced_service_instance_id"],
             fenced_lease_generation=payload["fenced_lease_generation"],
@@ -909,16 +970,26 @@ class RuntimeLeaseManager:
                         record.last_service_instance_id == live.service_instance_id
                         and record.last_lease_generation == live.lease_generation
                     )
-                    if not (same_fenced or same_released):
+                    same_identity = (
+                        record.service_pid == live.service_pid
+                        and record.process_start_identity == live.process_start_identity
+                        and record.endpoint_fingerprint == live.endpoint_fingerprint
+                    )
+                    if not (same_fenced or same_released) or not same_identity:
                         raise ForeignLeaseError("fenced/released live lease does not match durable record")
                     self._remove_live_lease()
                     live = None
                 else:
+                    if record.status not in {"reserved", "active"}:
+                        raise ForeignLeaseError("live lease is present for a non-owning generation status")
                     if (
                         record.last_lease_generation != live.lease_generation
                         or record.last_service_instance_id != live.service_instance_id
+                        or record.service_pid != live.service_pid
+                        or record.process_start_identity != live.process_start_identity
+                        or record.endpoint_fingerprint != live.endpoint_fingerprint
                     ):
-                        raise ForeignLeaseError("live lease and generation metadata disagree")
+                        raise ForeignLeaseError("live lease and durable owner identity disagree")
                     evidence = self.liveness_verifier.verify(live)
                     if evidence.status is LivenessStatus.LIVE:
                         raise LeaseAlreadyHeld(evidence.reason)
@@ -932,22 +1003,32 @@ class RuntimeLeaseManager:
                         raise LeaseLivenessUnknown("lease changed during stale verification")
                     record = self._fence_stale_lease(record, live)
                     live = None
+            elif record.status == "active":
+                raise LeaseRecoveryRequired(
+                    "active durable authority has no live lease; recovery is required before takeover"
+                )
 
             next_generation = record.last_lease_generation + 1
             lease = self._new_lease(next_generation)
-            allocated = replace(
+            reserved = replace(
                 record,
                 last_lease_generation=next_generation,
                 last_service_instance_id=lease.service_instance_id,
-                status="allocated",
+                service_pid=lease.service_pid,
+                process_start_identity=lease.process_start_identity,
+                endpoint_fingerprint=lease.endpoint_fingerprint,
+                status="reserved",
                 fenced_service_instance_id=None,
                 fenced_lease_generation=None,
                 updated_at=self._now(),
             )
-            self._write_generation(allocated)
-            self._inject("after_generation_persist")
+            self._write_generation(reserved)
+            self._inject("after_generation_reservation")
             self._write_live_lease(lease)
             self._inject("after_live_lease_persist")
+            active = replace(reserved, status="active", updated_at=self._now())
+            self._write_generation(active)
+            self._inject("after_generation_activation")
             return lease
 
     def _assert_current_owner(self, lease: RuntimeLease) -> tuple[RuntimeLease, AuthorityGenerationRecord]:
@@ -958,9 +1039,12 @@ class RuntimeLeaseManager:
         if current is None or not self._same_owner(current, lease):
             raise LeaseNotOwner("service instance/generation is not the current live owner")
         if (
-            record.status != "allocated"
+            record.status != "active"
             or record.last_lease_generation != lease.lease_generation
             or record.last_service_instance_id != lease.service_instance_id
+            or record.service_pid != current.service_pid
+            or record.process_start_identity != current.process_start_identity
+            or record.endpoint_fingerprint != current.endpoint_fingerprint
         ):
             raise LeaseNotOwner("service instance/generation has been durably fenced")
         return current, record
@@ -977,13 +1061,34 @@ class RuntimeLeaseManager:
     def bind_endpoint(self, lease: RuntimeLease, endpoint_fingerprint: str) -> RuntimeLease:
         endpoint = _non_empty_text(endpoint_fingerprint, field="endpoint_fingerprint")
         with self._lock():
-            current, _record = self._assert_current_owner(lease)
+            current, record = self._assert_current_owner(lease)
             if current.endpoint_fingerprint is not None and current.endpoint_fingerprint != endpoint:
                 raise EndpointBindingError("endpoint fingerprint is already bound")
             bound = replace(current, endpoint_fingerprint=endpoint)
             self._write_live_lease(bound)
+            self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
             return bound
 
+    def reconcile_endpoint_binding(self, lease: RuntimeLease, endpoint_fingerprint: str) -> RuntimeLease:
+        """Complete a durable bind after a crash between live and generation writes."""
+        endpoint = _non_empty_text(endpoint_fingerprint, field="endpoint_fingerprint")
+        with self._lock():
+            if not isinstance(lease, RuntimeLease) or not lease.matches_domain(self.domain):
+                raise LeaseNotOwner("lease does not belong to this runtime domain")
+            current = self._read_live_lease()
+            record = self._read_generation()
+            if current is None or not self._same_owner(current, lease):
+                raise LeaseNotOwner("service instance/generation is not the current live owner")
+            if record.status != "active" or record.last_lease_generation != lease.lease_generation:
+                raise LeaseNotOwner("service instance/generation is not active")
+            if current.endpoint_fingerprint != endpoint:
+                raise EndpointBindingError("live lease endpoint binding does not match reconciliation")
+            if record.endpoint_fingerprint not in (None, endpoint):
+                raise EndpointBindingError("durable generation endpoint binding conflicts")
+            if record.endpoint_fingerprint is None:
+                self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
+            return current
+
     def release(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
         with self._lock():
             current, record = self._assert_current_owner(lease)
@@ -1011,6 +1116,7 @@ __all__ = [
     "LeaseBusyError",
     "LeaseLivenessUnknown",
     "LeaseNotOwner",
+    "LeaseRecoveryRequired",
     "LivenessResult",
     "LivenessStatus",
     "LivenessVerifier",

diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 1a5dfbd..391621d 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -60,6 +60,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         *,
         owner_pid: int | None = None,
         owner_token: str | None = None,
+        desktop_instance_id: str | None = None,
         interval: float = 0.75,
         on_status: Callable[[str], None] | None = None,
         on_reconnect: Callable[[LiveStateClient], None] | None = None,
@@ -69,6 +70,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         self.client = client
         self.owner_pid = owner_pid
         self.owner_token = owner_token
+        self.desktop_instance_id = desktop_instance_id
         super().__init__(interval=interval, thread_name="contextor-live-watcher")
         self.on_status = on_status
         self.on_reconnect = on_reconnect
@@ -94,6 +96,8 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 self.root,
                 owner_pid=self.owner_pid,
                 owner_token=self.owner_token,
+                desktop_instance_id=self.desktop_instance_id,
+                client_kind="desktop" if self.desktop_instance_id is not None else "protocol",
                 timeout=10.0,
             )
             self.client = new_client

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index bc3c272..2a8757a 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -17,7 +17,12 @@ from tkinter import filedialog, messagebox, ttk
 
 from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
 from contextor.core.api.facade import ContextorFacade
-from contextor.core.live_state import DesktopLiveEventFeed, DesktopLiveWatcher, connect_or_start
+from contextor.core.live_state import (
+    DesktopLiveEventFeed,
+    DesktopLiveWatcher,
+    SecondDesktopActive,
+    connect_or_start,
+)
 from contextor.core.repository_identity import (
     RepositoryIdentityError,
     read_repository_identity,
@@ -90,6 +95,7 @@ class ContextorGUI:
         self.repo_builder_win = None
         self.parser_win = None
         self.owner_token = uuid.uuid4().hex
+        self.desktop_instance_id = uuid.uuid4().hex
         self.live_client = None
         self.live_clients = {}
         self.live_watcher = None
@@ -839,11 +845,18 @@ class ContextorGUI:
             from contextor.core.paths import repo_cache_dir
 
             cache = migrate_legacy_snapshot(path)
-            client = connect_or_start(
-                path,
-                owner_pid=os.getpid(),
-                owner_token=getattr(self, "owner_token", None),
-            )
+            connect_kwargs = {
+                "owner_pid": os.getpid(),
+                "owner_token": getattr(self, "owner_token", None),
+            }
+            import inspect
+
+            parameters = inspect.signature(connect_or_start).parameters
+            if "desktop_instance_id" in parameters:
+                connect_kwargs["desktop_instance_id"] = getattr(self, "desktop_instance_id", None)
+            if "client_kind" in parameters:
+                connect_kwargs["client_kind"] = "desktop"
+            client = connect_or_start(path, **connect_kwargs)
             self.live_client = client
             clients[identity.repo_id] = client
             if getattr(self, "_live_start_retry_after_id", None) is not None:
@@ -854,6 +867,11 @@ class ContextorGUI:
                         pass
                 self._live_start_retry_after_id = None
             self._live_start_retry_attempt = 0
+        except SecondDesktopActive as exc:
+            self._live_start_retry_attempt = 0
+            self._live_start_retry_after_id = None
+            self._set_live_status(f"LIVE: {exc}")
+            return
         except (OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError) as exc:
             current_attempt = getattr(self, "_live_start_retry_attempt", 0) + 1
             self._live_start_retry_attempt = current_attempt
@@ -941,6 +959,7 @@ class ContextorGUI:
             client,
             owner_pid=os.getpid(),
             owner_token=getattr(self, "owner_token", None),
+            desktop_instance_id=getattr(self, "desktop_instance_id", None),
             on_status=status_callback,
             on_reconnect=on_reconnect,
             on_resync=on_resync,

diff --git a/tests/live_state/test_runtime_lease.py b/tests/live_state/test_runtime_lease.py
index 8de99da..97bcb47 100644
--- a/tests/live_state/test_runtime_lease.py
+++ b/tests/live_state/test_runtime_lease.py
@@ -9,14 +9,17 @@ from typing import Any
 
 import pytest
 
+import contextor.core.live_state.runtime_lease as runtime_lease_module
 from contextor.core.live_state.runtime_domain import RuntimeDomain
 from contextor.core.live_state.runtime_lease import (
     AuthorityGenerationRecord,
+    DefaultLivenessVerifier,
     EndpointBindingError,
     ForeignLeaseError,
     LeaseAlreadyHeld,
     LeaseLivenessUnknown,
     LeaseNotOwner,
+    LeaseRecoveryRequired,
     LivenessResult,
     LivenessStatus,
     ProcessIdentity,
@@ -102,6 +105,7 @@ def _stale_result(*, pid_reuse: bool = False) -> LivenessResult:
         endpoint_available=False,
         endpoint_matches=False,
         reason="fake confirmed stale authority",
+        endpoint_evidence_verified=True,
     )
 
 
@@ -181,12 +185,13 @@ def test_pid_reuse_with_same_pid_but_different_start_identity_is_stale(tmp_path:
 
 def test_generation_gap_after_crash_before_live_write_is_never_reused(tmp_path: Path):
     domain = _domain(tmp_path)
-    crashed = _manager(domain, failure_injector=CrashAt("after_generation_persist"))
-    with pytest.raises(RuntimeError, match="after_generation_persist"):
+    crashed = _manager(domain, failure_injector=CrashAt("after_generation_reservation"))
+    with pytest.raises(RuntimeError, match="after_generation_reservation"):
         crashed.acquire()
 
     assert generation_metadata_path(domain).is_file()
     assert not live_lease_path(domain).exists()
+    assert crashed.read_generation().status == "reserved"
     next_lease = _manager(domain).acquire()
     assert next_lease.lease_generation == 2
 
@@ -203,6 +208,23 @@ def test_crash_after_live_write_leaves_existing_authority_for_normal_liveness_ch
 
     existing = RuntimeLease.from_dict(json.loads(live_lease_path(domain).read_text()))
     assert existing.lease_generation == 1
+    assert _manager(domain).read_generation().status == "reserved"
+    with pytest.raises(LeaseAlreadyHeld):
+        _manager(domain, verifier=ScriptedVerifier(_live_result())).acquire()
+
+
+def test_crash_after_generation_activation_leaves_active_authority(tmp_path: Path):
+    domain = _domain(tmp_path)
+    crashed = _manager(
+        domain,
+        verifier=ScriptedVerifier(_live_result()),
+        failure_injector=CrashAt("after_generation_activation"),
+    )
+    with pytest.raises(RuntimeError, match="after_generation_activation"):
+        crashed.acquire()
+
+    assert crashed.read_generation().status == "active"
+    assert live_lease_path(domain).exists()
     with pytest.raises(LeaseAlreadyHeld):
         _manager(domain, verifier=ScriptedVerifier(_live_result())).acquire()
 
@@ -235,6 +257,56 @@ def test_confirmed_dead_process_and_unavailable_endpoint_allow_stale_takeover(tm
     assert second.lease_generation == first.lease_generation + 1
 
 
+def test_default_liveness_does_not_fabricate_endpoint_stale_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
+    domain = _domain(tmp_path)
+    lease = _manager(domain).acquire()
+    verifier = DefaultLivenessVerifier()
+
+    monkeypatch.setattr(runtime_lease_module, "_process_identity", lambda _pid: (None, None, False))
+    dead = verifier.verify(lease)
+    assert dead.status is LivenessStatus.UNKNOWN
+    assert dead.endpoint_evidence_verified is False
+    assert not dead.confirmed_stale
+
+    monkeypatch.setattr(runtime_lease_module, "_process_identity", lambda _pid: (None, "different", True))
+    pid_reuse = verifier.verify(lease)
+    assert pid_reuse.status is LivenessStatus.UNKNOWN
+    assert pid_reuse.endpoint_evidence_verified is False
+    assert not pid_reuse.confirmed_stale
+
+
+def test_impossible_generation_record_combinations_fail_closed(tmp_path: Path):
+    domain = _domain(tmp_path)
+    initial = AuthorityGenerationRecord.initial(domain)
+
+    active_zero = initial.to_dict()
+    active_zero["status"] = "active"
+    with pytest.raises(RuntimeLeaseError):
+        AuthorityGenerationRecord.from_dict(active_zero)
+
+    reserved_without_identity = initial.to_dict()
+    reserved_without_identity.update(
+        status="reserved",
+        last_lease_generation=1,
+        last_service_instance_id="service-a",
+    )
+    with pytest.raises(RuntimeLeaseError):
+        AuthorityGenerationRecord.from_dict(reserved_without_identity)
+
+    half_fence = initial.to_dict()
+    half_fence.update(
+        status="released",
+        last_lease_generation=1,
+        last_service_instance_id="service-a",
+        service_pid=os.getpid(),
+        process_start_identity="process-a",
+        fenced_service_instance_id="service-a",
+        fenced_lease_generation=None,
+    )
+    with pytest.raises(RuntimeLeaseError):
+        AuthorityGenerationRecord.from_dict(half_fence)
+
+
 def test_crash_during_release_durable_fence_prevents_old_lease_resurrection(tmp_path: Path):
     domain = _domain(tmp_path)
     first_manager = _manager(domain)
@@ -374,15 +446,16 @@ def test_cross_process_acquisitions_have_exactly_one_winner(tmp_path: Path):
     assert [result[0] for result in results].count("LeaseAlreadyHeld") == 1
 
 
-def test_generation_survives_live_lease_file_deletion_and_release(tmp_path: Path):
+def test_active_generation_with_missing_live_lease_fails_closed(tmp_path: Path):
     domain = _domain(tmp_path)
     manager = _manager(domain)
     first = manager.acquire()
     live_lease_path(domain).unlink()
-    second = _manager(domain).acquire()
-    assert second.lease_generation == first.lease_generation + 1
-    _manager(domain).release(second)
-    assert manager.read_generation().last_lease_generation == 2
+    with pytest.raises(LeaseRecoveryRequired):
+        _manager(domain).acquire()
+    record = manager.read_generation()
+    assert record.status == "active"
+    assert record.last_lease_generation == first.lease_generation
 
 
 def test_runtime_lease_serialization_round_trip_and_test_root_isolation(tmp_path: Path):

diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index f510e7a..aa4f58b 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -17,7 +17,7 @@ from contextor.core.live_state import (
 )
 from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
 from contextor.core.live_state import ipc as ipc_module
-from contextor.core.live_state.runtime import connect_or_start, endpoint_file
+from contextor.core.live_state.runtime import EndpointSchemaError, connect_or_start, endpoint_file
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.analysis.state_manager import FileStateManager
 from contextor.core.paths import repo_cache_dir

diff --git a/tests/test_live_authority_bootstrap.py b/tests/test_live_authority_bootstrap.py
new file mode 100644
index 0000000..24abbd3
--- /dev/null
+++ b/tests/test_live_authority_bootstrap.py
@@ -0,0 +1,207 @@
+from __future__ import annotations
+
+import json
+import os
+import time
+from pathlib import Path
+
+import pytest
+
+from contextor.core.live_state import (
+    CanonicalLiveServer,
+    EndpointSchemaError,
+    LiveEndpoint,
+    SecondDesktopActive,
+    connect,
+    connect_or_start,
+)
+from contextor.core.live_state.runtime import endpoint_file
+from contextor.core.live_state.runtime_domain import RuntimeDomain
+from contextor.core.live_state.runtime_lease import RuntimeLeaseManager
+from contextor.core.repository_identity import read_repository_identity
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+
+def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "repo") -> Path:
+    repo = tmp_path / name
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    return repo
+
+
+def _stop(client) -> None:
+    try:
+        client.request("shutdown", timeout=1.0)
+    except Exception:
+        pass
+    deadline = time.monotonic() + 3.0
+    while time.monotonic() < deadline:
+        if connect(client.endpoint.root_path) is None:
+            return
+        time.sleep(0.05)
+
+
+def test_bootstrap_publishes_exact_lease_endpoint_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
+    repo = _repo(tmp_path, monkeypatch)
+    client = connect_or_start(
+        repo,
+        owner_pid=os.getpid(),
+        owner_token="owner-a",
+        desktop_instance_id="desktop-a",
+        client_kind="desktop",
+    )
+    try:
+        identity = read_repository_identity(repo)
+        assert identity is not None
+        domain = RuntimeDomain.from_identity(identity, mode="production")
+        manager = RuntimeLeaseManager(domain)
+        lease = manager.read_live_lease()
+        record = manager.read_generation()
+        status = client.authority_status()
+        assert lease is not None
+        assert record.status == "active"
+        assert client.endpoint.repo_id == identity.repo_id
+        assert client.endpoint.root_path == str(repo.resolve())
+        assert client.endpoint.runtime_domain_id == domain.domain_id
+        assert client.endpoint.service_instance_id == lease.service_instance_id
+        assert client.endpoint.lease_generation == lease.lease_generation
+        assert client.endpoint.service_pid == lease.service_pid
+        assert client.endpoint.process_start_identity == lease.process_start_identity
+        assert lease.endpoint_fingerprint == client.endpoint.fingerprint()
+        assert record.endpoint_fingerprint == client.endpoint.fingerprint()
+        assert status["service_instance_id"] == lease.service_instance_id
+        assert status["lease_generation"] == lease.lease_generation
+        assert status["endpoint_fingerprint"] == client.endpoint.fingerprint()
+    finally:
+        _stop(client)
+
+
+def test_verified_existing_authority_attaches_and_second_desktop_is_rejected(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    repo = _repo(tmp_path, monkeypatch)
+    first = connect_or_start(
+        repo,
+        owner_pid=os.getpid(),
+        owner_token="owner-a",
+        desktop_instance_id="desktop-a",
+        client_kind="desktop",
+    )
+    try:
+        protocol = connect_or_start(repo, client_kind="protocol")
+        assert protocol.service_pid == first.service_pid
+        assert protocol.is_owner is False
+        with pytest.raises(SecondDesktopActive, match="already active"):
+            connect_or_start(
+                repo,
+                owner_pid=os.getpid(),
+                owner_token="owner-b",
+                desktop_instance_id="desktop-b",
+                client_kind="desktop",
+            )
+    finally:
+        _stop(first)
+
+
+def test_different_repositories_may_have_independent_authorities(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    first_repo = _repo(tmp_path, monkeypatch, "first")
+    second_repo = _repo(tmp_path, monkeypatch, "second")
+    first = connect_or_start(first_repo, client_kind="protocol")
+    second = connect_or_start(second_repo, client_kind="protocol")
+    try:
+        assert first.service_pid != second.service_pid
+        assert first.endpoint.runtime_domain_id != second.endpoint.runtime_domain_id
+    finally:
+        _stop(first)
+        _stop(second)
+
+
+def test_clean_restart_fences_old_endpoint_and_allocates_next_generation(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    repo = _repo(tmp_path, monkeypatch)
+    first = connect_or_start(repo, client_kind="protocol")
+    old_endpoint = first.endpoint
+    identity = read_repository_identity(repo)
+    assert identity is not None
+    domain = RuntimeDomain.from_identity(identity, mode="production")
+    first_generation = RuntimeLeaseManager(domain).read_generation().last_lease_generation
+    _stop(first)
+
+    second = connect_or_start(repo, client_kind="protocol")
+    try:
+        assert second.endpoint.lease_generation == first_generation + 1
+        assert second.endpoint.service_instance_id != old_endpoint.service_instance_id
+        with pytest.raises((OSError, EOFError, ConnectionError, TimeoutError, RuntimeError)):
+            from contextor.core.live_state import LiveStateClient
+
+            LiveStateClient(old_endpoint).ping()
+    finally:
+        _stop(second)
+
+
+def test_malformed_or_foreign_endpoint_is_rejected_without_attach_or_spawn(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    repo = _repo(tmp_path, monkeypatch)
+    path = endpoint_file(repo)
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text(json.dumps({"host": "127.0.0.1"}), encoding="utf-8")
+    with pytest.raises(EndpointSchemaError):
+        connect_or_start(repo)
+
+
+def test_foreign_endpoint_identity_is_rejected_without_attach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
+    repo = _repo(tmp_path, monkeypatch)
+    client = connect_or_start(repo, client_kind="protocol")
+    path = endpoint_file(repo)
+    original = json.loads(path.read_text(encoding="utf-8"))
+    payload = dict(original)
+    payload["repo_id"] = "ctx_foreign"
+    path.write_text(json.dumps(payload), encoding="utf-8")
+    try:
+        with pytest.raises(EndpointSchemaError):
+            connect_or_start(repo)
+    finally:
+        path.write_text(json.dumps(original), encoding="utf-8")
+        _stop(client)
+
+
+def test_bind_crash_between_live_and_generation_writes_is_reconciled(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    repo = _repo(tmp_path, monkeypatch)
+    identity = read_repository_identity(repo)
+    assert identity is not None
+    domain = RuntimeDomain.from_identity(identity, mode="production")
+    manager = RuntimeLeaseManager(domain)
+    lease = manager.acquire()
+    endpoint = LiveEndpoint(
+        "127.0.0.1",
+        43210,
+        "00" * 32,
+        pid=lease.service_pid,
+        repo_id=identity.repo_id,
+        root_path=str(repo.resolve()),
+        runtime_domain_id=domain.domain_id,
+        service_instance_id=lease.service_instance_id,
+        lease_generation=lease.lease_generation,
+        process_start_identity=lease.process_start_identity,
+    )
+    original_write = manager._write_generation
+
+    def crash_after_live_write(_record):
+        raise RuntimeError("simulated generation write crash")
+
+    manager._write_generation = crash_after_live_write
+    with pytest.raises(RuntimeError, match="generation write crash"):
+        manager.bind_endpoint(lease, endpoint.fingerprint())
+    manager._write_generation = original_write
+    assert manager.read_live_lease().endpoint_fingerprint == endpoint.fingerprint()
+    assert manager.read_generation().endpoint_fingerprint is None
+    manager.reconcile_endpoint_binding(lease, endpoint.fingerprint())
+    assert manager.read_generation().endpoint_fingerprint == endpoint.fingerprint()
+    manager.release(lease)
```

