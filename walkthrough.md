# CPA10K7G2B1 — PERSISTENT BACKEND DURABLE OWNER LEASE

STATUS=FINAL_PASS
HEAD_BEFORE=9221a7877df4404f2702af2fb6f670f46f232e0e
HEAD_AFTER=9221a7877df4404f2702af2fb6f670f46f232e0e
LIVE_REVISION_BEFORE=1335
LIVE_REVISION_AFTER=1342
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\mcp_backend_state.py; C:\Temp\Contextor_Repo\contextor\mcp_server.py; C:\Temp\Contextor_Repo\tests\test_mcp_backend_state.py; C:\Temp\Contextor_Repo\tests\test_mcp_shared_backend_server_mode.py; C:\Temp\Contextor_Repo\walkthrough.md (report artifact only)
IMPLEMENTATION_RESULT=PASS
DURABLE_RECORD_CONTRACT=PASS — per-user state_dir()/mcp_backend/backend.json; atomic replace; schema-validated metadata; no auth credential field
LIFETIME_LOCK_CONTRACT=PASS — OS-backed lock held through lease lifetime; focused cross-process test passed
SINGLETON_CONTRACT=PASS — same-process and cross-process duplicate acquisition rejected
EXACT_OWNER_REMOVAL=PASS — mismatch preserved, exact record removed
HOST_OWNED_REGRESSION=PASS — focused server-mode suite passed
PERSISTENT_BACKEND_REGRESSION=PASS — active record in HTTP branch; no host-owned root; duplicate rejected before orphan cleanup
TARGETED_TEST_RESULTS=PASS
CANONICAL_VERIFICATION=PASS — all four source/test files workspace_sync=verified; latest canonical revision 1342; exact main implementation fetched
CANONICAL_RESYNC_REQUIRED=NO
PROCESS_BASELINE_INITIAL=48
PROCESS_OBSERVED_DURING_G2B_DISCOVERY=53
PROCESS_REDUCTION_EXPECTED_THIS_STAGE=NO
FINAL_TARGET=LT_20_UNDER_CONTINUOUS_LOAD (future target; not measured in this implementation stage)
MCP_SERVER_RESTART_REQUIRED=YES (restart not performed)

## Zakres i wynik

Zrealizowano literalny etap durable owner lease. Nie uruchamiano persistent backendu, nie wykonywano detached startu, nie modyfikowano CLI, mcp_process_registry.py, LIVE runtime ani konfiguracji klienta. Zmiany źródłowe/testowe ograniczają się do czterech ścieżek wymienionych w FILES_CHANGED; walkthrough.md jest wyłącznie artefaktem raportowym. HEAD pozostał bez zmian.

Lease jest nabywany przed _cleanup_orphaned_processes, rejestracją procesów i uruchomieniem runnera. Release występuje po zakończeniu runnera, a ścieżka atexit jest idempotentna. Host-owned stdio pozostaje bez lease i zachowuje dotychczasową rejestrację root.

## DIRECT_EVIDENCE

- Contextor Desktop LIVE watcher opublikował: revision 1336 mcp_backend_state.py; 1337 mcp_server.py; 1338 test_mcp_backend_state.py; 1339 test_mcp_shared_backend_server_mode.py. Dalsze zdarzenia 1340–1342 były powtórnymi UPDATED/UNCHANGED dla testów. Latest revision=1342, continuity=continuous, resync_required=false.
- Contextor file edit context: canonical_state=fresh i workspace_sync=verified dla wszystkich czterech plików; syntax_diagnostics checked_and_none; warnings puste. Dla mcp_backend_state direct consumers=3 (mcp_server i dwa moduły testowe), transitive consumers=34; imports: contextor.core.paths i contextor.mcp_process_registry.
- Contextor pobrał kompletną implementację mcp_server::main na revision 1340 z workspace_sync=verified; aktualny file context mcp_server jest verified na revision 1342. Kod pokazuje acquire przed cleanup oraz release w finally.
- Contextor lineage rozwiązał dokładnie contextor.mcp_backend_state::PersistentBackendLease.acquire; lineage families i semantic anchor bindings były fresh/complete na revision 1342.
- LIVE diagnostics na revision 1342: syntax_errors=0, name_collisions=0, cycles=0, attention_required=false. Layer guard dla adapter modułów: 0 violations; outbound rules nie są zdefiniowane. Testowe moduły są w layer=tests.
- Git status po testach wskazał wyłącznie cztery dozwolone pliki źródłowe/testowe; HEAD=9221a7877df4404f2702af2fb6f670f46f232e0e.

## CODE_PATH_PROVED

- PersistentBackendLease.acquire tworzy rekord z identity bieżącego procesu, canonical process registry path i metadanymi host/port/transport; plik tymczasowy jest fsync, a rekord publikowany przez os.replace.
- Blokada używa msvcrt.locking na Windows albo fcntl.flock na POSIX; thread lock jest dodatkowo utrzymywany lokalnie. Lease release usuwa rekord wyłącznie przy dokładnej zgodności i zawsze zwalnia OS lock.
- main nabywa lease tylko dla persistent-backend, po sprawdzeniu transportu/roli i przed lifecycle side effects. Host-owned root nadal rozstrzyga _register_server_root; persistent-backend zwraca None.

## CONTRACT_PROVED

- Testy bezpośrednio potwierdziły zapis/odczyt rekordu, wymagane pola, brak pola token, release, singleton lokalny i międzyprocesowy, malformed record fail-closed oraz exact-owner removal.
- Test serwera potwierdził obecność rekordu podczas fake HTTP, usunięcie po main(), brak host-owned root i odrzucenie drugiego backendu przed cleanup.
- Testy regresyjne host-owned stdio/process lifecycle przeszły.

## INFERENCE_AND_UNKNOWN

- Wnioskiem z testu helpera jest działanie OS-backed singleton gate na tym środowisku Windows; test nie uruchamiał rzeczywistego MCP HTTP backendu.
- Liczby PROCESS_BASELINE_INITIAL i PROCESS_OBSERVED_DURING_G2B_DISCOVERY są przeniesione z wartości wymaganych dla tego etapu; nie wykonywano pomiaru procesów ani obciążenia. Cel LT_20_UNDER_CONTINUOUS_LOAD pozostaje niezweryfikowany na późniejszy etap.
- Kod serwera MCP zmienił się, zatem wymagany jest ręczny restart przed certyfikacją runtime. Restart nie był częścią tego zadania i nie został wykonany.

## Wykonane komendy i wyniki

1. `& .\.venv\Scripts\python.exe -m py_compile contextor/mcp_backend_state.py contextor/mcp_server.py tests/test_mcp_backend_state.py tests/test_mcp_shared_backend_server_mode.py` — exit 0.
2. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_state.py` — 5 passed in 1.55s.
3. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_shared_backend_server_mode.py` — 14 passed, 1 AuthlibDeprecationWarning, 3.94s.
4. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_child_process_cleanup.py` — 4 passed, 1 AuthlibDeprecationWarning, 3.76s.
5. `& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_regressions.py::test_registry_rejects_reused_pid tests/test_mcp_regressions.py::test_startup_cleanup_stops_only_orphaned_registered_processes tests/test_mcp_regressions.py::test_shutdown_cleanup_stops_only_children_owned_by_server` — 3 passed, 1 AuthlibDeprecationWarning, 3.45s.
6. `git diff --check -- contextor/mcp_server.py tests/test_mcp_shared_backend_server_mode.py` — exit 0; no whitespace errors, only LF-to-CRLF notices. `git diff --no-index --check -- /dev/null contextor/mcp_backend_state.py` and the corresponding command for `tests/test_mcp_backend_state.py` returned exit 1 because the files differ from `/dev/null`; neither emitted whitespace diagnostics, only LF-to-CRLF notices.
7. Whole-worktree `git diff --check` after creating this report returned exit 1 for 23 `+ ` blank-context lines inside the required raw unified diffs embedded in walkthrough.md. These preserve the actual diff formatting; the source/test-only check above is clean.

Pełny repository pytest nie był uruchamiany. Test cross-process zwolnił helper w finally; wynik 5/5 potwierdza poprawne zakończenie helpera i możliwość ponownego przejęcia lease.

## FULL_DIFFS

### contextor/mcp_backend_state.py

```diff
diff --git a/contextor/mcp_backend_state.py b/contextor/mcp_backend_state.py
new file mode 100644
index 0000000..17b9e0c
--- /dev/null
+++ b/contextor/mcp_backend_state.py
@@ -0,0 +1,704 @@
+"""Durable ownership state for one shared persistent Contextor MCP backend."""
+
+from __future__ import annotations
+
+import json
+import math
+import os
+import sys
+import threading
+import time
+import uuid
+from contextlib import AbstractContextManager
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any, Mapping
+
+from contextor.core.paths import state_dir
+from contextor.mcp_process_registry import process_identity
+
+
+BACKEND_RECORD_SCHEMA_VERSION = 1
+BACKEND_SERVER_ROLE = "persistent-backend"
+BACKEND_TRANSPORT = "streamable-http"
+
+_RECORD_FIELDS = {
+    "schema_version",
+    "instance_id",
+    "server_role",
+    "transport",
+    "host",
+    "port",
+    "pid",
+    "executable",
+    "creation_time",
+    "process_registry",
+    "started_at",
+}
+
+
+class BackendStateError(RuntimeError):
+    """Base error for persistent MCP backend ownership state."""
+
+
+class BackendAlreadyRunning(BackendStateError):
+    """Another process owns the persistent backend lifetime lock."""
+
+
+class BackendRecordError(BackendStateError):
+    """The durable backend record is malformed or violates its schema."""
+
+
+def _text(value: Any, field: str) -> str:
+    if not isinstance(value, str) or not value.strip() or value != value.strip():
+        raise BackendRecordError(
+            f"{field} must be non-empty without surrounding whitespace"
+        )
+    return value
+
+
+def _positive_int(value: Any, field: str) -> int:
+    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
+        raise BackendRecordError(
+            f"{field} must be a positive integer"
+        )
+    return value
+
+
+def _canonical_path(value: Any, field: str) -> str:
+    if not isinstance(value, (str, Path)) or not str(value).strip():
+        raise BackendRecordError(
+            f"{field} must be a non-empty path"
+        )
+
+    try:
+        resolved = Path(value).expanduser().resolve(
+            strict=False
+        )
+    except (
+        OSError,
+        RuntimeError,
+        ValueError,
+    ) as exc:
+        raise BackendRecordError(
+            f"{field} cannot be canonicalized"
+        ) from exc
+
+    if not resolved.is_absolute():
+        raise BackendRecordError(
+            f"{field} must be absolute"
+        )
+
+    return os.path.normcase(
+        str(resolved)
+    )
+
+
+@dataclass(
+    frozen=True,
+    slots=True,
+)
+class PersistentBackendRecord:
+    schema_version: int
+    instance_id: str
+    server_role: str
+    transport: str
+    host: str
+    port: int
+    pid: int
+    executable: str
+    creation_time: int | None
+    process_registry: str
+    started_at: float
+
+    def __post_init__(self) -> None:
+        if (
+            self.schema_version
+            != BACKEND_RECORD_SCHEMA_VERSION
+        ):
+            raise BackendRecordError(
+                "unsupported backend record schema_version"
+            )
+
+        object.__setattr__(
+            self,
+            "instance_id",
+            _text(
+                self.instance_id,
+                "instance_id",
+            ),
+        )
+
+        if self.server_role != BACKEND_SERVER_ROLE:
+            raise BackendRecordError(
+                "backend record server_role is invalid"
+            )
+
+        if self.transport != BACKEND_TRANSPORT:
+            raise BackendRecordError(
+                "backend record transport is invalid"
+            )
+
+        object.__setattr__(
+            self,
+            "host",
+            _text(
+                self.host,
+                "host",
+            ),
+        )
+
+        port = _positive_int(
+            self.port,
+            "port",
+        )
+
+        if port > 65535:
+            raise BackendRecordError(
+                "port must be at most 65535"
+            )
+
+        object.__setattr__(
+            self,
+            "pid",
+            _positive_int(
+                self.pid,
+                "pid",
+            ),
+        )
+
+        object.__setattr__(
+            self,
+            "executable",
+            _text(
+                self.executable,
+                "executable",
+            ),
+        )
+
+        if self.creation_time is not None:
+            object.__setattr__(
+                self,
+                "creation_time",
+                _positive_int(
+                    self.creation_time,
+                    "creation_time",
+                ),
+            )
+
+        object.__setattr__(
+            self,
+            "process_registry",
+            _canonical_path(
+                self.process_registry,
+                "process_registry",
+            ),
+        )
+
+        if (
+            isinstance(
+                self.started_at,
+                bool,
+            )
+            or not isinstance(
+                self.started_at,
+                (int, float),
+            )
+        ):
+            raise BackendRecordError(
+                "started_at must be a timestamp"
+            )
+
+        started_at = float(
+            self.started_at
+        )
+
+        if (
+            not math.isfinite(
+                started_at
+            )
+            or started_at < 0
+        ):
+            raise BackendRecordError(
+                "started_at must be a finite non-negative timestamp"
+            )
+
+        object.__setattr__(
+            self,
+            "started_at",
+            started_at,
+        )
+
+    def to_dict(
+        self,
+    ) -> dict[str, Any]:
+        return {
+            "schema_version": self.schema_version,
+            "instance_id": self.instance_id,
+            "server_role": self.server_role,
+            "transport": self.transport,
+            "host": self.host,
+            "port": self.port,
+            "pid": self.pid,
+            "executable": self.executable,
+            "creation_time": self.creation_time,
+            "process_registry": self.process_registry,
+            "started_at": self.started_at,
+        }
+
+    @classmethod
+    def from_dict(
+        cls,
+        payload: Mapping[str, Any],
+    ) -> "PersistentBackendRecord":
+        if (
+            not isinstance(
+                payload,
+                Mapping,
+            )
+            or set(payload)
+            != _RECORD_FIELDS
+        ):
+            raise BackendRecordError(
+                "backend record fields do not match schema"
+            )
+
+        return cls(
+            **dict(payload)
+        )
+
+
+def backend_state_dir() -> Path:
+    return (
+        state_dir()
+        / "mcp_backend"
+    )
+
+
+def backend_record_path() -> Path:
+    return (
+        backend_state_dir()
+        / "backend.json"
+    )
+
+
+def backend_lock_path() -> Path:
+    return (
+        backend_state_dir()
+        / "backend.lock"
+    )
+
+
+def _write_record(
+    record: PersistentBackendRecord,
+) -> None:
+    target = backend_record_path()
+
+    target.parent.mkdir(
+        parents=True,
+        exist_ok=True,
+    )
+
+    temporary = target.with_name(
+        f".{target.name}.{uuid.uuid4().hex}.tmp"
+    )
+
+    try:
+        with temporary.open(
+            "w",
+            encoding="utf-8",
+            newline="\n",
+        ) as stream:
+            json.dump(
+                record.to_dict(),
+                stream,
+                sort_keys=True,
+                separators=(",", ":"),
+            )
+
+            stream.flush()
+
+            os.fsync(
+                stream.fileno()
+            )
+
+        os.replace(
+            temporary,
+            target,
+        )
+
+    finally:
+        try:
+            temporary.unlink()
+        except FileNotFoundError:
+            pass
+
+
+def read_backend_record(
+) -> PersistentBackendRecord | None:
+    try:
+        payload = json.loads(
+            backend_record_path().read_text(
+                encoding="utf-8"
+            )
+        )
+
+    except FileNotFoundError:
+        return None
+
+    except (
+        OSError,
+        TypeError,
+        ValueError,
+    ) as exc:
+        raise BackendRecordError(
+            "persistent backend record is malformed"
+        ) from exc
+
+    if not isinstance(
+        payload,
+        Mapping,
+    ):
+        raise BackendRecordError(
+            "persistent backend record must be an object"
+        )
+
+    return (
+        PersistentBackendRecord
+        .from_dict(
+            payload
+        )
+    )
+
+
+def remove_backend_record_if_exact(
+    expected: PersistentBackendRecord,
+) -> bool:
+    try:
+        current = (
+            read_backend_record()
+        )
+    except BackendRecordError:
+        return False
+
+    if current != expected:
+        return False
+
+    try:
+        backend_record_path().unlink()
+    except FileNotFoundError:
+        return False
+
+    return True
+
+
+_THREAD_LOCKS: dict[
+    str,
+    threading.Lock,
+] = {}
+
+_THREAD_LOCKS_GUARD = (
+    threading.Lock()
+)
+
+
+def _thread_lock_for(
+    path: Path,
+) -> threading.Lock:
+    key = os.path.normcase(
+        str(path)
+    )
+
+    with _THREAD_LOCKS_GUARD:
+        return (
+            _THREAD_LOCKS
+            .setdefault(
+                key,
+                threading.Lock(),
+            )
+        )
+
+
+class _BackendLifetimeLock(
+    AbstractContextManager[
+        "_BackendLifetimeLock"
+    ]
+):
+    def __init__(
+        self,
+        path: Path,
+        *,
+        timeout: float,
+    ) -> None:
+        self.path = path
+        self.timeout = max(
+            0.0,
+            float(timeout),
+        )
+        self._thread_lock = (
+            _thread_lock_for(
+                path
+            )
+        )
+        self._file: Any = None
+
+    def __enter__(
+        self,
+    ) -> "_BackendLifetimeLock":
+        if not self._thread_lock.acquire(
+            timeout=self.timeout
+        ):
+            raise BackendAlreadyRunning(
+                "persistent backend lifetime lock is already held"
+            )
+
+        try:
+            self.path.parent.mkdir(
+                parents=True,
+                exist_ok=True,
+            )
+
+            self._file = (
+                self.path.open(
+                    "a+b"
+                )
+            )
+
+            if (
+                self.path.stat().st_size
+                == 0
+            ):
+                self._file.write(
+                    b"0"
+                )
+                self._file.flush()
+
+            deadline = (
+                time.monotonic()
+                + self.timeout
+            )
+
+            while True:
+                try:
+                    self._file.seek(0)
+
+                    if os.name == "nt":
+                        import msvcrt
+
+                        msvcrt.locking(
+                            self._file.fileno(),
+                            msvcrt.LK_NBLCK,
+                            1,
+                        )
+
+                    else:
+                        import fcntl
+
+                        fcntl.flock(
+                            self._file.fileno(),
+                            fcntl.LOCK_EX
+                            | fcntl.LOCK_NB,
+                        )
+
+                    return self
+
+                except (
+                    OSError,
+                    BlockingIOError,
+                ) as exc:
+                    if (
+                        time.monotonic()
+                        >= deadline
+                    ):
+                        raise BackendAlreadyRunning(
+                            "persistent backend lifetime lock is already held"
+                        ) from exc
+
+                    time.sleep(
+                        0.01
+                    )
+
+        except Exception:
+            self._close()
+            self._thread_lock.release()
+            raise
+
+    def _close(
+        self,
+    ) -> None:
+        if self._file is None:
+            return
+
+        try:
+            self._file.seek(0)
+
+            if os.name == "nt":
+                import msvcrt
+
+                msvcrt.locking(
+                    self._file.fileno(),
+                    msvcrt.LK_UNLCK,
+                    1,
+                )
+
+            else:
+                import fcntl
+
+                fcntl.flock(
+                    self._file.fileno(),
+                    fcntl.LOCK_UN,
+                )
+
+        except OSError:
+            pass
+
+        try:
+            self._file.close()
+        finally:
+            self._file = None
+
+    def __exit__(
+        self,
+        exc_type: Any,
+        exc: Any,
+        tb: Any,
+    ) -> None:
+        try:
+            self._close()
+        finally:
+            self._thread_lock.release()
+
+
+class PersistentBackendLease:
+    def __init__(
+        self,
+        record: PersistentBackendRecord,
+        lifetime_lock: _BackendLifetimeLock,
+    ) -> None:
+        self.record = record
+        self._lifetime_lock = (
+            lifetime_lock
+        )
+        self._released = False
+
+    @classmethod
+    def acquire(
+        cls,
+        *,
+        host: str,
+        port: int,
+        transport: str,
+        process_registry: str | Path,
+        timeout: float = 0.0,
+    ) -> "PersistentBackendLease":
+        lifetime_lock = (
+            _BackendLifetimeLock(
+                backend_lock_path(),
+                timeout=timeout,
+            )
+        )
+
+        lifetime_lock.__enter__()
+
+        try:
+            (
+                image,
+                creation_time,
+                alive,
+            ) = process_identity(
+                os.getpid()
+            )
+
+            if not alive:
+                raise BackendStateError(
+                    "current persistent backend process identity is unavailable"
+                )
+
+            record = PersistentBackendRecord(
+                schema_version=(
+                    BACKEND_RECORD_SCHEMA_VERSION
+                ),
+                instance_id=(
+                    uuid.uuid4().hex
+                ),
+                server_role=(
+                    BACKEND_SERVER_ROLE
+                ),
+                transport=transport,
+                host=host,
+                port=port,
+                pid=os.getpid(),
+                executable=(
+                    image
+                    or sys.executable
+                ),
+                creation_time=(
+                    int(creation_time)
+                    if creation_time
+                    is not None
+                    else None
+                ),
+                process_registry=str(
+                    Path(
+                        process_registry
+                    )
+                    .expanduser()
+                    .resolve(
+                        strict=False
+                    )
+                ),
+                started_at=time.time(),
+            )
+
+            _write_record(
+                record
+            )
+
+            return cls(
+                record,
+                lifetime_lock,
+            )
+
+        except BaseException:
+            lifetime_lock.__exit__(
+                None,
+                None,
+                None,
+            )
+            raise
+
+    def release(
+        self,
+    ) -> None:
+        if self._released:
+            return
+
+        self._released = True
+
+        try:
+            remove_backend_record_if_exact(
+                self.record
+            )
+        finally:
+            self._lifetime_lock.__exit__(
+                None,
+                None,
+                None,
+            )
+
+
+__all__ = [
+    "BACKEND_RECORD_SCHEMA_VERSION",
+    "BACKEND_SERVER_ROLE",
+    "BACKEND_TRANSPORT",
+    "BackendAlreadyRunning",
+    "BackendRecordError",
+    "BackendStateError",
+    "PersistentBackendLease",
+    "PersistentBackendRecord",
+    "backend_lock_path",
+    "backend_record_path",
+    "backend_state_dir",
+    "read_backend_record",
+    "remove_backend_record_if_exact",
+]
```

### contextor/mcp_server.py

```diff
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 1f6cc4d..6cd3df4 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -189,6 +189,9 @@ from contextor.mcp_process_registry import (
     remove_record,
     terminate_registered_process,
 )
+from contextor.mcp_backend_state import (
+    PersistentBackendLease,
+)
 from contextor.mcp.documentation import short_description
 from contextor.mcp.tools.get_artifact_blast_radius import (
     get_artifact_blast_radius as _get_artifact_blast_radius_impl,
@@ -1015,87 +1018,112 @@ def main():
         _process_directory_from_environment()
     )
 
-    _cleanup_orphaned_processes(
-        process_directory
-    )
+    http_host = None
+    http_port = None
 
-    previous_registry = os.environ.get(
-        "CONTEXTOR_MCP_PROCESS_REGISTRY"
-    )
+    if transport in _HTTP_TRANSPORTS:
+        http_host = os.environ.get(
+            "CONTEXTOR_MCP_HOST",
+            "127.0.0.1",
+        )
 
-    os.environ[
-        "CONTEXTOR_MCP_PROCESS_REGISTRY"
-    ] = str(process_directory)
+        http_port = int(
+            os.environ.get(
+                "CONTEXTOR_MCP_PORT",
+                "8765",
+            )
+        )
 
-    server_record = _register_server_root(
-        process_directory,
-        role,
-    )
+    backend_lease = None
 
-    cleanup_done = False
+    if role == "persistent-backend":
+        backend_lease = (
+            PersistentBackendLease.acquire(
+                host=http_host,
+                port=http_port,
+                transport="streamable-http",
+                process_registry=process_directory,
+            )
+        )
 
-    def _shutdown_cleanup() -> None:
-        nonlocal cleanup_done
+        atexit.register(
+            backend_lease.release
+        )
 
-        if cleanup_done:
-            return
+    try:
+        _cleanup_orphaned_processes(
+            process_directory
+        )
 
-        cleanup_done = True
+        previous_registry = os.environ.get(
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        )
 
-        try:
-            _shutdown_mcp_owned_processes(
-                process_directory,
-                os.getpid(),
-            )
-        finally:
-            if server_record is not None:
-                remove_record(
-                    server_record
-                )
+        os.environ[
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        ] = str(process_directory)
+
+        server_record = _register_server_root(
+            process_directory,
+            role,
+        )
+
+        cleanup_done = False
+
+        def _shutdown_cleanup() -> None:
+            nonlocal cleanup_done
 
-            if previous_registry is None:
-                os.environ.pop(
-                    "CONTEXTOR_MCP_PROCESS_REGISTRY",
-                    None,
+            if cleanup_done:
+                return
+
+            cleanup_done = True
+
+            try:
+                _shutdown_mcp_owned_processes(
+                    process_directory,
+                    os.getpid(),
                 )
-            else:
-                os.environ[
-                    "CONTEXTOR_MCP_PROCESS_REGISTRY"
-                ] = previous_registry
+            finally:
+                if server_record is not None:
+                    remove_record(
+                        server_record
+                    )
 
-    atexit.register(
-        _shutdown_cleanup
-    )
+                if previous_registry is None:
+                    os.environ.pop(
+                        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+                        None,
+                    )
+                else:
+                    os.environ[
+                        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+                    ] = previous_registry
 
-    async def _run():
-        if transport in _HTTP_TRANSPORTS:
-            host = os.environ.get(
-                "CONTEXTOR_MCP_HOST",
-                "127.0.0.1",
-            )
+        atexit.register(
+            _shutdown_cleanup
+        )
 
-            port = int(
-                os.environ.get(
-                    "CONTEXTOR_MCP_PORT",
-                    "8765",
+        async def _run():
+            if transport in _HTTP_TRANSPORTS:
+                await mcp.run_http_async(
+                    transport="streamable-http",
+                    host=http_host,
+                    port=http_port,
+                    show_banner=False,
                 )
-            )
+            else:
+                await mcp.run_stdio_async()
 
-            await mcp.run_http_async(
-                transport="streamable-http",
-                host=host,
-                port=port,
-                show_banner=False,
+        try:
+            asyncio.run(
+                _run()
             )
-        else:
-            await mcp.run_stdio_async()
+        finally:
+            _shutdown_cleanup()
 
-    try:
-        asyncio.run(
-            _run()
-        )
     finally:
-        _shutdown_cleanup()
+        if backend_lease is not None:
+            backend_lease.release()
 
 
 if __name__ == "__main__":
```

### tests/test_mcp_backend_state.py

```diff
diff --git a/tests/test_mcp_backend_state.py b/tests/test_mcp_backend_state.py
new file mode 100644
index 0000000..11a654c
--- /dev/null
+++ b/tests/test_mcp_backend_state.py
@@ -0,0 +1,220 @@
+import dataclasses
+import os
+import queue
+import subprocess
+import sys
+import threading
+from pathlib import Path
+
+import pytest
+
+from contextor.mcp_backend_state import (
+    BackendAlreadyRunning,
+    BackendRecordError,
+    PersistentBackendLease,
+    backend_record_path,
+    read_backend_record,
+    remove_backend_record_if_exact,
+)
+
+
+def _acquire_backend(registry: Path) -> PersistentBackendLease:
+    return PersistentBackendLease.acquire(
+        host="127.0.0.1",
+        port=8765,
+        transport="streamable-http",
+        process_registry=registry,
+    )
+
+
+def test_acquire_writes_durable_record_and_release_removes_it(
+    tmp_path,
+    monkeypatch,
+):
+    state_dir = tmp_path / "state"
+    registry = tmp_path / "registry"
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(state_dir),
+    )
+
+    lease = _acquire_backend(registry)
+
+    try:
+        record = read_backend_record()
+
+        assert backend_record_path() == (
+            state_dir
+            / "mcp_backend"
+            / "backend.json"
+        )
+        assert record is not None
+        assert record.schema_version == 1
+        assert record.server_role == "persistent-backend"
+        assert record.transport == "streamable-http"
+        assert record.host == "127.0.0.1"
+        assert record.port == 8765
+        assert record.pid == os.getpid()
+        assert Path(record.process_registry) == registry.resolve()
+        assert record.instance_id
+        assert record.started_at >= 0
+        assert "token" not in record.to_dict()
+    finally:
+        lease.release()
+
+    assert read_backend_record() is None
+
+
+def test_same_process_backend_lease_is_singleton(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
+    registry = tmp_path / "registry"
+    first = _acquire_backend(registry)
+
+    try:
+        with pytest.raises(BackendAlreadyRunning):
+            _acquire_backend(registry)
+    finally:
+        first.release()
+
+    second = _acquire_backend(registry)
+    second.release()
+
+
+def test_cross_process_backend_lease_is_singleton_and_helper_is_cleaned_up(
+    tmp_path,
+    monkeypatch,
+):
+    state_dir = tmp_path / "state"
+    registry = tmp_path / "registry"
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(state_dir),
+    )
+
+    helper_code = "\n".join(
+        (
+            "import sys",
+            "from contextor.mcp_backend_state import PersistentBackendLease",
+            "lease = PersistentBackendLease.acquire(",
+            "    host='127.0.0.1',",
+            "    port=8765,",
+            "    transport='streamable-http',",
+            "    process_registry=sys.argv[1],",
+            ")",
+            "try:",
+            "    print('READY', flush=True)",
+            "    sys.stdin.readline()",
+            "finally:",
+            "    lease.release()",
+        )
+    )
+    child_env = os.environ.copy()
+    child_env["CONTEXTOR_STATE_DIR"] = str(state_dir)
+    helper = subprocess.Popen(
+        [sys.executable, "-c", helper_code, str(registry)],
+        cwd=Path(__file__).resolve().parents[1],
+        env=child_env,
+        stdin=subprocess.PIPE,
+        stdout=subprocess.PIPE,
+        stderr=subprocess.PIPE,
+        text=True,
+        bufsize=1,
+    )
+    ready_line = queue.Queue()
+
+    def read_helper_stdout():
+        assert helper.stdout is not None
+        ready_line.put(helper.stdout.readline())
+        for _line in helper.stdout:
+            pass
+
+    stdout_reader = threading.Thread(
+        target=read_helper_stdout,
+        daemon=True,
+    )
+    stdout_reader.start()
+
+    try:
+        assert ready_line.get(timeout=5) == "READY\n"
+
+        with pytest.raises(BackendAlreadyRunning):
+            _acquire_backend(registry)
+    finally:
+        if helper.poll() is None:
+            assert helper.stdin is not None
+            helper.stdin.write("\n")
+            helper.stdin.flush()
+
+        try:
+            helper.wait(timeout=5)
+        except subprocess.TimeoutExpired:
+            helper.terminate()
+            try:
+                helper.wait(timeout=5)
+            except subprocess.TimeoutExpired:
+                helper.kill()
+                helper.wait(timeout=5)
+
+        stdout_reader.join(timeout=1)
+        helper_stderr = (
+            helper.stderr.read()
+            if helper.stderr is not None
+            else ""
+        )
+        helper_result = {
+            "stdout_reader_alive": stdout_reader.is_alive(),
+            "stderr": helper_stderr,
+        }
+
+    assert helper.returncode == 0, helper_result
+    assert read_backend_record() is None
+
+    parent_lease = _acquire_backend(registry)
+    parent_lease.release()
+
+
+def test_malformed_backend_record_is_rejected(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
+    path = backend_record_path()
+    path.parent.mkdir(parents=True)
+    path.write_text("not-json", encoding="utf-8")
+
+    with pytest.raises(BackendRecordError):
+        read_backend_record()
+
+
+def test_backend_record_removal_requires_exact_owner(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
+    lease = _acquire_backend(tmp_path / "registry")
+
+    try:
+        expected = lease.record
+        other_owner = dataclasses.replace(
+            expected,
+            instance_id=f"{expected.instance_id}-other",
+        )
+
+        assert remove_backend_record_if_exact(other_owner) is False
+        assert read_backend_record() == expected
+        assert remove_backend_record_if_exact(expected) is True
+        assert read_backend_record() is None
+    finally:
+        lease.release()
```

### tests/test_mcp_shared_backend_server_mode.py

```diff
diff --git a/tests/test_mcp_shared_backend_server_mode.py b/tests/test_mcp_shared_backend_server_mode.py
index 296f112..d2bc63c 100644
--- a/tests/test_mcp_shared_backend_server_mode.py
+++ b/tests/test_mcp_shared_backend_server_mode.py
@@ -1,9 +1,15 @@
 import asyncio
+import os
 from pathlib import Path
 
 import pytest
 
 from contextor import mcp_server
+from contextor.mcp_backend_state import (
+    BackendAlreadyRunning,
+    PersistentBackendLease,
+    read_backend_record,
+)
 
 
 def test_stdio_transport_does_not_require_auth(
@@ -500,6 +506,10 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         "CONTEXTOR_MCP_PROCESS_REGISTRY",
         str(registry),
     )
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
     monkeypatch.setenv(
         "CONTEXTOR_MCP_HOST",
         "127.0.0.1",
@@ -565,6 +575,14 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         )
 
     async def fake_http(**kwargs):
+        record = read_backend_record()
+        assert record is not None
+        assert record.pid == os.getpid()
+        assert record.server_role == "persistent-backend"
+        assert record.transport == "streamable-http"
+        assert record.host == "127.0.0.1"
+        assert record.port == 8765
+        assert Path(record.process_registry) == registry.resolve()
         events.append(
             (
                 "http",
@@ -609,3 +627,66 @@ def test_persistent_http_main_uses_shared_registry_without_root_registration(
         "shutdown",
         registry.resolve(),
     ) in events
+    assert read_backend_record() is None
+
+
+def test_second_persistent_backend_is_rejected_before_lifecycle_side_effects(
+    tmp_path,
+    monkeypatch,
+):
+    registry = tmp_path / "registry"
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(tmp_path / "state"),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "streamable-http",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "persistent-backend",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_HOST",
+        "127.0.0.1",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PORT",
+        "8765",
+    )
+    monkeypatch.setattr(
+        mcp_server.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_MCP_BOOTSTRAP_TRANSPORT",
+        "streamable-http",
+    )
+
+    lease = PersistentBackendLease.acquire(
+        host="127.0.0.1",
+        port=8765,
+        transport="streamable-http",
+        process_registry=registry,
+    )
+
+    try:
+        monkeypatch.setattr(
+            mcp_server,
+            "_cleanup_orphaned_processes",
+            lambda *_args, **_kwargs: pytest.fail(
+                "lifecycle side effect occurred"
+            ),
+        )
+
+        with pytest.raises(BackendAlreadyRunning):
+            mcp_server.main()
+    finally:
+        lease.release()
```
