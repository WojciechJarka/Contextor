STATUS=BLOCKED_SOURCE_DRIFT
HEAD_BEFORE=14897b4821159c7c3a05697699b68a0ca6fe8071
HEAD_AFTER=14897b4821159c7c3a05697699b68a0ca6fe8071
LIVE_REVISION_BEFORE=1344
LIVE_REVISION_AFTER=1346

FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\mcp_backend_control.py
- C:\Temp\Contextor_Repo\tests\test_mcp_backend_control.py
- C:\Temp\Contextor_Repo\walkthrough.md

IMPLEMENTATION_RESULT=BLOCKED_SOURCE_DRIFT
CONTRACT_SOURCE_MATCH=YES (production block matches the supplied literal source; only the attachment's trailing document separator was excluded)
TEST_CASES=20
BLOCK_REASON=Post-edit Contextor diagnostics report two new IDENTICAL_DEFINITION_DUPLICATE warnings, so the required name_collisions=0 condition is not met. The literal implementation is not altered because the contract forbids adaptation.

READINESS_CONTRACT
AUTHENTICATED_READINESS_IMPLEMENTED=YES
TCP_ONLY_READINESS_USED=NO
Probe path requires MCP initialize identity serverInfo.name == "Contextor" and successful ping. Wrong identity, failed ping, and client exceptions fail closed. The tests use a fake FastMCP client; no HTTP request or endpoint was contacted.

START_CONTRACT
DETACHED_BACKEND_LAUNCH_IMPLEMENTED=YES
TOKEN_IN_ARGV=NO
The token is supplied via child environment, not argv. Ready existing owner is reused; stale metadata is removed before spawn; readiness failure cleanup targets the exact spawn identity. Windows breakaway fallback is limited to one retry for the specified denial.

STOP_CONTRACT
IDENTITY_SAFE_STOP_IMPLEMENTED=YES
Stop without a record is idempotent. Stale owner metadata is removed without termination. Windows termination requires creation identity and uses the exact backend record; owned registry child cleanup is scoped by parent identity.

PROCESS_OWNERSHIP_CONTRACT
INACTIVITY_SHUTDOWN_IMPLEMENTED=NO
Status/readiness paths do not terminate stale processes. Termination is identity-checked and explicit-stop/failure cleanup only. The tests exercise these decisions with fakes; no real process was spawned or terminated.

TEST_RESULTS
- `.venv\Scripts\python.exe -m py_compile contextor\mcp_backend_control.py tests\test_mcp_backend_control.py` — PASS.
- `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_control.py` — 20 passed, 1 Authlib deprecation warning.
- `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_state.py` — 5 passed.
- `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_backend_secret.py` — 7 passed, 1 skipped.
- `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_shared_backend_server_mode.py` — 14 passed, 1 Authlib deprecation warning.
- `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_child_process_cleanup.py` — 4 passed, 1 Authlib deprecation warning.
FULL_SUITE_RUN=NO
REAL_BACKEND_STARTED=NO
HTTP_ENDPOINT_REQUESTED=NO
GENERATED_IGNORED_BYTECODE_PRESENT_AFTER_VALIDATION
- C:\Temp\Contextor_Repo\contextor\__pycache__\mcp_backend_control.cpython-310.pyc
- C:\Temp\Contextor_Repo\tests\__pycache__\test_mcp_backend_control.cpython-310-pytest-9.1.1.pyc
- C:\Temp\Contextor_Repo\tests\__pycache__\test_mcp_backend_control.cpython-310.pyc
These are ignored Python validation caches, not source/test/docs changes; they are excluded from FILES_CHANGED and textual FULL_DIFFS.

CONTEXTOR_VERIFICATION
- Before edits: LIVE revision 1344; continuity continuous; resync_required=false. Baseline HEAD was 14897b4821159c7c3a05697699b68a0ca6fe8071.
- After edits: desktop_watcher reported UPDATED for contextor/mcp_backend_control.py at revision 1345 and tests/test_mcp_backend_control.py at revision 1346; continuity remained continuous and resync_required=false.
- get_file_edit_context at canonical revision 1346: both files exist; workspace_sync=verified; syntax diagnostics checked_and_none with 0 errors; cycles=0. New module context shows one direct consumer, tests.test_mcp_backend_control.
- get_module_blast_radius identifies 39 artifacts in contextor.mcp_backend_control and one direct consumer module (the new test), with no downstream consumers. That projection's workspace_sync field was unverified; the two file-edit contexts above independently report verified.
- get_name_collisions at fresh revision 1346 reports total=2, conflicting=0, identical=2, attention_required=true:
  1. BACKEND_TRANSPORT: identical assignment in contextor/mcp_backend_state.py:23 and contextor/mcp_backend_control.py:42.
  2. CREATE_BREAKAWAY_FROM_JOB: identical assignment in contextor/core/live_state/runtime.py:741 and contextor/mcp_backend_control.py:44.
- The get_live_events aggregate showed name_collisions.count=0, but its revision-1345 event explicitly listed both as ADDED; fresh get_file_edit_context reported count=2 and get_name_collisions returned both exact records. This projection inconsistency is recorded; the exact fresh collision records establish that the required zero-collision postcondition is not satisfied.
- These are identical-definition duplicate warnings, not conflicting definitions. Nevertheless, the supplied contract explicitly requires name_collisions=0 and says not to adapt its literal source. No source change or full analysis was attempted.

MCP_SERVER_RESTART_REQUIRED=NO
CONFIG_CHANGED=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

FULL_DIFFS
diff --git a/contextor/mcp_backend_control.py b/contextor/mcp_backend_control.py
new file mode 100644
--- /dev/null
+++ b/contextor/mcp_backend_control.py
@@ -0,0 +1,1021 @@
+"""Lifecycle control for the persistent shared Contextor MCP backend."""
+
+from __future__ import annotations
+
+import asyncio
+import os
+import subprocess
+import sys
+import threading
+import time
+from contextlib import AbstractContextManager
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any, Literal
+
+from fastmcp import Client
+
+from contextor.core.paths import package_root
+from contextor.mcp_backend_secret import (
+    get_or_create_backend_token,
+    read_backend_token,
+)
+from contextor.mcp_backend_state import (
+    PersistentBackendRecord,
+    backend_state_dir,
+    read_backend_record,
+    remove_backend_record_if_exact,
+)
+from contextor.mcp_process_registry import (
+    process_identity,
+    read_records,
+    record_matches_process,
+    remove_record,
+    terminate_registered_process,
+)
+
+
+BACKEND_HOST = "127.0.0.1"
+BACKEND_PORT = 8765
+BACKEND_MCP_PATH = "/mcp"
+BACKEND_SERVER_NAME = "Contextor"
+BACKEND_TRANSPORT = "streamable-http"
+
+CREATE_BREAKAWAY_FROM_JOB = 0x01000000
+
+BackendState = Literal[
+    "stopped",
+    "stale",
+    "unready",
+    "running",
+]
+
+
+class BackendControlError(RuntimeError):
+    """Persistent backend lifecycle control failed."""
+
+
+@dataclass(
+    frozen=True,
+    slots=True,
+)
+class BackendStatus:
+    state: BackendState
+    ready: bool
+    detail: str
+    record: PersistentBackendRecord | None
+
+    @property
+    def endpoint(
+        self,
+    ) -> str | None:
+        if self.record is None:
+            return None
+
+        return (
+            f"http://{self.record.host}:"
+            f"{self.record.port}"
+            f"{BACKEND_MCP_PATH}"
+        )
+
+    def to_dict(
+        self,
+    ) -> dict[str, Any]:
+        return {
+            "state": self.state,
+            "ready": self.ready,
+            "detail": self.detail,
+            "endpoint": self.endpoint,
+            "pid": (
+                None
+                if self.record is None
+                else self.record.pid
+            ),
+            "instance_id": (
+                None
+                if self.record is None
+                else self.record.instance_id
+            ),
+        }
+
+
+def backend_process_registry_dir() -> Path:
+    return (
+        backend_state_dir()
+        / "processes"
+    )
+
+
+def backend_control_lock_path() -> Path:
+    return (
+        backend_state_dir()
+        / "control.lock"
+    )
+
+
+def _backend_endpoint(
+    record: PersistentBackendRecord,
+) -> str:
+    return (
+        f"http://{record.host}:"
+        f"{record.port}"
+        f"{BACKEND_MCP_PATH}"
+    )
+
+
+def _record_process_matches(
+    record: PersistentBackendRecord,
+) -> bool:
+    return record_matches_process(
+        record.to_dict()
+    )
+
+
+async def _probe_backend_async(
+    record: PersistentBackendRecord,
+    token: str,
+    *,
+    timeout: float,
+) -> bool:
+    try:
+        async with Client(
+            _backend_endpoint(record),
+            auth=token,
+            timeout=timeout,
+            init_timeout=timeout,
+        ) as client:
+            initialized = (
+                client.initialize_result
+            )
+
+            if initialized is None:
+                return False
+
+            if (
+                initialized.serverInfo.name
+                != BACKEND_SERVER_NAME
+            ):
+                return False
+
+            return bool(
+                await client.ping()
+            )
+
+    except Exception:
+        return False
+
+
+def _probe_backend(
+    record: PersistentBackendRecord,
+    token: str,
+    *,
+    timeout: float,
+) -> bool:
+    return asyncio.run(
+        _probe_backend_async(
+            record,
+            token,
+            timeout=timeout,
+        )
+    )
+
+
+def get_backend_status(
+    *,
+    probe_timeout: float = 2.0,
+) -> BackendStatus:
+    record = read_backend_record()
+
+    if record is None:
+        return BackendStatus(
+            state="stopped",
+            ready=False,
+            detail="no persistent backend record",
+            record=None,
+        )
+
+    if not _record_process_matches(
+        record
+    ):
+        return BackendStatus(
+            state="stale",
+            ready=False,
+            detail=(
+                "persistent backend record does not "
+                "match a live process identity"
+            ),
+            record=record,
+        )
+
+    token = read_backend_token()
+
+    if token is None:
+        return BackendStatus(
+            state="unready",
+            ready=False,
+            detail=(
+                "backend owner is live but bearer "
+                "token is unavailable"
+            ),
+            record=record,
+        )
+
+    if not _probe_backend(
+        record,
+        token,
+        timeout=probe_timeout,
+    ):
+        return BackendStatus(
+            state="unready",
+            ready=False,
+            detail=(
+                "backend owner is live but authenticated "
+                "MCP readiness was not confirmed"
+            ),
+            record=record,
+        )
+
+    return BackendStatus(
+        state="running",
+        ready=True,
+        detail=(
+            "authenticated Contextor MCP backend is ready"
+        ),
+        record=record,
+    )
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
+class _BackendControlLock(
+    AbstractContextManager[
+        "_BackendControlLock"
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
+    ) -> "_BackendControlLock":
+        if not self._thread_lock.acquire(
+            timeout=self.timeout
+        ):
+            raise BackendControlError(
+                "persistent backend control lock is busy"
+            )
+
+        try:
+            self.path.parent.mkdir(
+                parents=True,
+                exist_ok=True,
+            )
+
+            self._file = self.path.open(
+                "a+b"
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
+                        raise BackendControlError(
+                            "persistent backend control lock is busy"
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
+def _backend_python() -> Path:
+    installation = package_root()
+
+    if sys.platform == "win32":
+        interpreter = (
+            installation
+            / ".venv"
+            / "Scripts"
+            / "python.exe"
+        )
+
+    else:
+        interpreter = (
+            installation
+            / ".venv"
+            / "bin"
+            / "python"
+        )
+
+    if not interpreter.is_file():
+        raise BackendControlError(
+            "Contextor backend interpreter was not found: "
+            f"{interpreter}"
+        )
+
+    return interpreter
+
+
+def _backend_environment(
+    token: str,
+) -> dict[str, str]:
+    env = dict(
+        os.environ
+    )
+
+    env[
+        "CONTEXTOR_MCP_TRANSPORT"
+    ] = BACKEND_TRANSPORT
+
+    env[
+        "CONTEXTOR_MCP_SERVER_ROLE"
+    ] = "persistent-backend"
+
+    env[
+        "CONTEXTOR_MCP_HOST"
+    ] = BACKEND_HOST
+
+    env[
+        "CONTEXTOR_MCP_PORT"
+    ] = str(
+        BACKEND_PORT
+    )
+
+    env[
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    ] = str(
+        backend_process_registry_dir()
+        .expanduser()
+        .resolve()
+    )
+
+    env[
+        "CONTEXTOR_MCP_TOKEN"
+    ] = token
+
+    return env
+
+
+def _spawn_backend_process(
+    token: str,
+) -> subprocess.Popen:
+    interpreter = (
+        _backend_python()
+    )
+
+    cmd = [
+        str(interpreter),
+        "-u",
+        "-m",
+        "contextor.mcp_main",
+    ]
+
+    kwargs = {
+        "cwd": str(
+            package_root()
+        ),
+        "env": (
+            _backend_environment(
+                token
+            )
+        ),
+        "stdin": subprocess.DEVNULL,
+        "stdout": subprocess.DEVNULL,
+        "stderr": subprocess.DEVNULL,
+    }
+
+    if sys.platform != "win32":
+        return subprocess.Popen(
+            cmd,
+            creationflags=0,
+            **kwargs,
+        )
+
+    base_flags = getattr(
+        subprocess,
+        "CREATE_NO_WINDOW",
+        0,
+    )
+
+    primary_flags = (
+        base_flags
+        | CREATE_BREAKAWAY_FROM_JOB
+    )
+
+    try:
+        return subprocess.Popen(
+            cmd,
+            creationflags=primary_flags,
+            **kwargs,
+        )
+
+    except OSError as exc:
+        if (
+            getattr(
+                exc,
+                "winerror",
+                None,
+            )
+            != 5
+        ):
+            raise
+
+        try:
+            return subprocess.Popen(
+                cmd,
+                creationflags=base_flags,
+                **kwargs,
+            )
+
+        except Exception as fallback_exc:
+            raise fallback_exc from exc
+
+
+def _spawn_identity_record(
+    process: subprocess.Popen,
+) -> dict[str, Any] | None:
+    (
+        image,
+        creation_time,
+        alive,
+    ) = process_identity(
+        process.pid
+    )
+
+    if not alive:
+        return None
+
+    return {
+        "pid": process.pid,
+        "executable": (
+            image
+            or str(
+                _backend_python()
+            )
+        ),
+        "creation_time": creation_time,
+    }
+
+
+def _cleanup_spawned_process(
+    identity_record: dict[str, Any] | None,
+) -> None:
+    if identity_record is None:
+        return
+
+    terminate_registered_process(
+        identity_record
+    )
+
+
+def _cleanup_stale_backend_record(
+    status: BackendStatus,
+) -> None:
+    if (
+        status.state == "stale"
+        and status.record is not None
+    ):
+        remove_backend_record_if_exact(
+            status.record
+        )
+
+
+def _wait_for_ready_backend(
+    process: subprocess.Popen,
+    *,
+    timeout: float,
+    probe_timeout: float,
+) -> BackendStatus:
+    deadline = (
+        time.monotonic()
+        + max(
+            0.0,
+            float(timeout),
+        )
+    )
+
+    last_status = BackendStatus(
+        state="stopped",
+        ready=False,
+        detail="backend startup has not published state yet",
+        record=None,
+    )
+
+    while (
+        time.monotonic()
+        < deadline
+    ):
+        last_status = (
+            get_backend_status(
+                probe_timeout=probe_timeout,
+            )
+        )
+
+        if last_status.ready:
+            return last_status
+
+        if (
+            process.poll()
+            is not None
+        ):
+            final_status = (
+                get_backend_status(
+                    probe_timeout=probe_timeout,
+                )
+            )
+
+            if final_status.ready:
+                return final_status
+
+            raise BackendControlError(
+                "persistent backend process exited "
+                "before authenticated readiness"
+            )
+
+        time.sleep(
+            0.05
+        )
+
+    raise BackendControlError(
+        "persistent backend did not become "
+        "authenticated and ready before timeout"
+    )
+
+
+def start_backend(
+    *,
+    timeout: float = 20.0,
+    probe_timeout: float = 2.0,
+) -> BackendStatus:
+    with _BackendControlLock(
+        backend_control_lock_path(),
+        timeout=timeout,
+    ):
+        token = (
+            get_or_create_backend_token()
+        )
+
+        current = (
+            get_backend_status(
+                probe_timeout=probe_timeout,
+            )
+        )
+
+        if current.ready:
+            return current
+
+        if (
+            current.state == "unready"
+            and current.record is not None
+        ):
+            deadline = (
+                time.monotonic()
+                + max(
+                    0.0,
+                    float(timeout),
+                )
+            )
+
+            while (
+                time.monotonic()
+                < deadline
+            ):
+                current = (
+                    get_backend_status(
+                        probe_timeout=probe_timeout,
+                    )
+                )
+
+                if current.ready:
+                    return current
+
+                if (
+                    current.state
+                    != "unready"
+                ):
+                    break
+
+                time.sleep(
+                    0.05
+                )
+
+            if (
+                current.state
+                == "unready"
+            ):
+                raise BackendControlError(
+                    "an existing persistent backend owner "
+                    "is alive but did not become ready"
+                )
+
+        _cleanup_stale_backend_record(
+            current
+        )
+
+        process = (
+            _spawn_backend_process(
+                token
+            )
+        )
+
+        identity_record = (
+            _spawn_identity_record(
+                process
+            )
+        )
+
+        try:
+            return (
+                _wait_for_ready_backend(
+                    process,
+                    timeout=timeout,
+                    probe_timeout=probe_timeout,
+                )
+            )
+
+        except BaseException:
+            _cleanup_spawned_process(
+                identity_record
+            )
+            raise
+
+
+def _backend_owner_identity_matches(
+    record: PersistentBackendRecord,
+) -> bool:
+    (
+        image,
+        creation_time,
+        alive,
+    ) = process_identity(
+        record.pid
+    )
+
+    if not alive:
+        return False
+
+    if (
+        sys.platform == "win32"
+        and record.creation_time is None
+    ):
+        return False
+
+    if (
+        record.creation_time is not None
+        and creation_time is not None
+        and int(
+            record.creation_time
+        )
+        != int(
+            creation_time
+        )
+    ):
+        return False
+
+    if (
+        image
+        and record.executable
+        and Path(image).name.casefold()
+        != Path(
+            record.executable
+        ).name.casefold()
+    ):
+        return False
+
+    return True
+
+
+def _cleanup_owned_registry_children(
+    record: PersistentBackendRecord,
+) -> None:
+    directory = Path(
+        record.process_registry
+    )
+
+    for (
+        record_path,
+        child,
+    ) in read_records(
+        directory
+    ):
+        try:
+            parent_pid = int(
+                child.get(
+                    "parent_pid"
+                )
+            )
+        except (
+            TypeError,
+            ValueError,
+        ):
+            continue
+
+        if parent_pid != record.pid:
+            continue
+
+        if (
+            record.creation_time
+            is not None
+        ):
+            expected_parent_creation = (
+                child.get(
+                    "parent_creation_time"
+                )
+            )
+
+            if (
+                expected_parent_creation
+                is None
+            ):
+                continue
+
+            try:
+                if int(
+                    expected_parent_creation
+                ) != int(
+                    record.creation_time
+                ):
+                    continue
+
+            except (
+                TypeError,
+                ValueError,
+            ):
+                continue
+
+        terminate_registered_process(
+            child
+        )
+
+        remove_record(
+            record_path
+        )
+
+
+def _wait_for_owner_exit(
+    record: PersistentBackendRecord,
+    *,
+    timeout: float,
+) -> bool:
+    deadline = (
+        time.monotonic()
+        + max(
+            0.0,
+            float(timeout),
+        )
+    )
+
+    while (
+        time.monotonic()
+        < deadline
+    ):
+        if not (
+            _backend_owner_identity_matches(
+                record
+            )
+        ):
+            return True
+
+        time.sleep(
+            0.05
+        )
+
+    return not (
+        _backend_owner_identity_matches(
+            record
+        )
+    )
+
+
+def stop_backend(
+    *,
+    timeout: float = 5.0,
+) -> BackendStatus:
+    with _BackendControlLock(
+        backend_control_lock_path(),
+        timeout=timeout,
+    ):
+        record = (
+            read_backend_record()
+        )
+
+        if record is None:
+            return BackendStatus(
+                state="stopped",
+                ready=False,
+                detail="no persistent backend record",
+                record=None,
+            )
+
+        if not (
+            _backend_owner_identity_matches(
+                record
+            )
+        ):
+            remove_backend_record_if_exact(
+                record
+            )
+
+            return BackendStatus(
+                state="stopped",
+                ready=False,
+                detail=(
+                    "stale persistent backend record "
+                    "was removed without terminating "
+                    "any process"
+                ),
+                record=None,
+            )
+
+        if (
+            sys.platform == "win32"
+            and record.creation_time is None
+        ):
+            raise BackendControlError(
+                "refusing to terminate backend without "
+                "Windows process creation identity"
+            )
+
+        terminated = (
+            terminate_registered_process(
+                record.to_dict()
+            )
+        )
+
+        if not terminated:
+            raise BackendControlError(
+                "identity-checked backend termination "
+                "was not accepted"
+            )
+
+        if not _wait_for_owner_exit(
+            record,
+            timeout=timeout,
+        ):
+            raise BackendControlError(
+                "persistent backend process remained "
+                "alive after identity-checked termination"
+            )
+
+        _cleanup_owned_registry_children(
+            record
+        )
+
+        remove_backend_record_if_exact(
+            record
+        )
+
+        return BackendStatus(
+            state="stopped",
+            ready=False,
+            detail="persistent backend stopped",
+            record=None,
+        )
+
+
+__all__ = [
+    "BACKEND_HOST",
+    "BACKEND_MCP_PATH",
+    "BACKEND_PORT",
+    "BACKEND_SERVER_NAME",
+    "BACKEND_TRANSPORT",
+    "BackendControlError",
+    "BackendStatus",
+    "backend_control_lock_path",
+    "backend_process_registry_dir",
+    "get_backend_status",
+    "start_backend",
+    "stop_backend",
+]

diff --git a/tests/test_mcp_backend_control.py b/tests/test_mcp_backend_control.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_backend_control.py
@@ -0,0 +1,644 @@
+from __future__ import annotations
+
+import subprocess
+import sys
+import threading
+from contextlib import nullcontext
+from dataclasses import replace
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.mcp_backend_control as control
+from contextor.mcp_backend_state import PersistentBackendRecord
+
+
+@pytest.fixture
+def backend_record(tmp_path: Path) -> PersistentBackendRecord:
+    return PersistentBackendRecord(
+        schema_version=1,
+        instance_id="test-backend-instance",
+        server_role="persistent-backend",
+        transport="streamable-http",
+        host="127.0.0.1",
+        port=8765,
+        pid=12345,
+        executable=sys.executable,
+        creation_time=987654321,
+        process_registry=str((tmp_path / "registry").resolve()),
+        started_at=1.0,
+    )
+
+
+def _status(
+    state: control.BackendState,
+    *,
+    ready: bool = False,
+    record: PersistentBackendRecord | None = None,
+) -> control.BackendStatus:
+    return control.BackendStatus(
+        state=state,
+        ready=ready,
+        detail=state,
+        record=record,
+    )
+
+
+class _FakeClient:
+    def __init__(
+        self,
+        url: str,
+        *,
+        auth: str,
+        timeout: float,
+        init_timeout: float,
+        server_name: str = "Contextor",
+        ping_result: bool = True,
+        enter_error: Exception | None = None,
+        ping_error: Exception | None = None,
+    ) -> None:
+        self.url = url
+        self.auth = auth
+        self.timeout = timeout
+        self.init_timeout = init_timeout
+        self.initialize_result = SimpleNamespace(
+            serverInfo=SimpleNamespace(name=server_name)
+        )
+        self.ping_result = ping_result
+        self.enter_error = enter_error
+        self.ping_error = ping_error
+        self.ping_called = False
+
+    async def __aenter__(self) -> _FakeClient:
+        if self.enter_error is not None:
+            raise self.enter_error
+        return self
+
+    async def __aexit__(self, exc_type, exc, tb) -> None:
+        return None
+
+    async def ping(self) -> bool:
+        self.ping_called = True
+        if self.ping_error is not None:
+            raise self.ping_error
+        return self.ping_result
+
+
+def test_authenticated_probe_accepts_contextor_identity_and_ping(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    token = "supplied-test-bearer-token"
+    clients: list[_FakeClient] = []
+
+    def make_client(url: str, **kwargs) -> _FakeClient:
+        client = _FakeClient(url, **kwargs)
+        clients.append(client)
+        return client
+
+    monkeypatch.setattr(control, "Client", make_client)
+
+    assert control._probe_backend(
+        backend_record,
+        token,
+        timeout=1.0,
+    ) is True
+    assert len(clients) == 1
+    assert clients[0].url == "http://127.0.0.1:8765/mcp"
+    assert clients[0].auth == token
+    assert clients[0].ping_called is True
+
+
+def test_authenticated_probe_rejects_wrong_server_identity(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    clients: list[_FakeClient] = []
+
+    def make_client(url: str, **kwargs) -> _FakeClient:
+        client = _FakeClient(
+            url,
+            **kwargs,
+            server_name="NotContextor",
+        )
+        clients.append(client)
+        return client
+
+    monkeypatch.setattr(control, "Client", make_client)
+
+    assert control._probe_backend(
+        backend_record,
+        "test-token",
+        timeout=1.0,
+    ) is False
+    assert clients[0].ping_called is False
+
+
+def test_authenticated_probe_rejects_failed_ping(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(
+        control,
+        "Client",
+        lambda url, **kwargs: _FakeClient(
+            url,
+            **kwargs,
+            ping_result=False,
+        ),
+    )
+
+    assert control._probe_backend(
+        backend_record,
+        "test-token",
+        timeout=1.0,
+    ) is False
+
+
+def test_authenticated_probe_fails_closed_on_client_exception(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(
+        control,
+        "Client",
+        lambda url, **kwargs: _FakeClient(
+            url,
+            **kwargs,
+            enter_error=RuntimeError("initialize failed"),
+        ),
+    )
+
+    assert control._probe_backend(
+        backend_record,
+        "test-token",
+        timeout=1.0,
+    ) is False
+
+
+def test_status_without_record_is_stopped(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(control, "read_backend_record", lambda: None)
+
+    result = control.get_backend_status()
+
+    assert result.state == "stopped"
+    assert result.ready is False
+    assert result.record is None
+
+
+def test_status_stale_record_never_probes_http(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(
+        control,
+        "read_backend_record",
+        lambda: backend_record,
+    )
+    monkeypatch.setattr(control, "_record_process_matches", lambda record: False)
+    monkeypatch.setattr(
+        control,
+        "_probe_backend",
+        lambda *args, **kwargs: pytest.fail("stale owner must not be probed"),
+    )
+
+    result = control.get_backend_status()
+
+    assert result.state == "stale"
+    assert result.ready is False
+
+
+def test_status_live_owner_requires_authenticated_readiness(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(
+        control,
+        "read_backend_record",
+        lambda: backend_record,
+    )
+    monkeypatch.setattr(control, "_record_process_matches", lambda record: True)
+    monkeypatch.setattr(control, "read_backend_token", lambda: "stored-token")
+    probe_results = iter((False, True))
+    monkeypatch.setattr(
+        control,
+        "_probe_backend",
+        lambda record, token, *, timeout: next(probe_results),
+    )
+
+    unready = control.get_backend_status()
+    ready = control.get_backend_status()
+
+    assert unready.state == "unready"
+    assert unready.ready is False
+    assert ready.state == "running"
+    assert ready.ready is True
+
+
+def test_backend_environment_contains_role_transport_registry_and_token(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    registry = tmp_path / "process-registry"
+    monkeypatch.setattr(
+        control,
+        "backend_process_registry_dir",
+        lambda: registry,
+    )
+
+    env = control._backend_environment("secret")
+
+    assert env["CONTEXTOR_MCP_TRANSPORT"] == "streamable-http"
+    assert env["CONTEXTOR_MCP_SERVER_ROLE"] == "persistent-backend"
+    assert env["CONTEXTOR_MCP_HOST"] == "127.0.0.1"
+    assert env["CONTEXTOR_MCP_PORT"] == "8765"
+    assert env["CONTEXTOR_MCP_PROCESS_REGISTRY"] == str(registry.resolve())
+    assert env["CONTEXTOR_MCP_TOKEN"] == "secret"
+
+
+def test_backend_spawn_never_places_token_in_argv(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    token = "unique-backend-token-sentinel"
+    calls: list[tuple[list[str], dict[str, object]]] = []
+    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
+    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
+    monkeypatch.setattr(
+        control,
+        "backend_process_registry_dir",
+        lambda: tmp_path / "registry",
+    )
+
+    def fake_popen(cmd: list[str], **kwargs) -> SimpleNamespace:
+        calls.append((cmd, kwargs))
+        return SimpleNamespace(pid=12345)
+
+    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)
+
+    control._spawn_backend_process(token)
+
+    assert len(calls) == 1
+    cmd, kwargs = calls[0]
+    assert token not in " ".join(cmd)
+    env = kwargs["env"]
+    assert isinstance(env, dict)
+    assert env["CONTEXTOR_MCP_TOKEN"] == token
+    assert all(
+        token not in value
+        for key, value in env.items()
+        if key != "CONTEXTOR_MCP_TOKEN"
+    )
+    assert kwargs["stdin"] == subprocess.DEVNULL
+    assert kwargs["stdout"] == subprocess.DEVNULL
+    assert kwargs["stderr"] == subprocess.DEVNULL
+
+
+def test_windows_backend_spawn_uses_breakaway_and_no_window(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    calls: list[dict[str, object]] = []
+    monkeypatch.setattr(control.sys, "platform", "win32")
+    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
+    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
+    monkeypatch.setattr(control, "backend_process_registry_dir", lambda: tmp_path)
+
+    def fake_popen(cmd: list[str], **kwargs) -> SimpleNamespace:
+        calls.append(kwargs)
+        return SimpleNamespace(pid=12345)
+
+    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)
+
+    control._spawn_backend_process("test-token")
+
+    assert len(calls) == 1
+    flags = calls[0]["creationflags"]
+    assert flags & control.CREATE_BREAKAWAY_FROM_JOB
+    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+    if create_no_window:
+        assert flags & create_no_window
+
+
+def test_windows_breakaway_denied_has_exactly_one_fallback(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    calls: list[dict[str, object]] = []
+    monkeypatch.setattr(control.sys, "platform", "win32")
+    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
+    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
+    monkeypatch.setattr(control, "backend_process_registry_dir", lambda: tmp_path)
+
+    def denied_then_succeed(cmd: list[str], **kwargs) -> SimpleNamespace:
+        calls.append(kwargs)
+        if len(calls) == 1:
+            exc = OSError("breakaway denied")
+            exc.winerror = 5
+            raise exc
+        return SimpleNamespace(pid=12345)
+
+    monkeypatch.setattr(control.subprocess, "Popen", denied_then_succeed)
+
+    control._spawn_backend_process("test-token")
+
+    assert len(calls) == 2
+    assert calls[0]["creationflags"] & control.CREATE_BREAKAWAY_FROM_JOB
+    assert not calls[1]["creationflags"] & control.CREATE_BREAKAWAY_FROM_JOB
+
+    other_error = OSError("unrelated process creation failure")
+    other_error.winerror = 87
+    other_calls = 0
+
+    def fail_unrelated(cmd: list[str], **kwargs) -> None:
+        nonlocal other_calls
+        other_calls += 1
+        raise other_error
+
+    monkeypatch.setattr(control.subprocess, "Popen", fail_unrelated)
+    with pytest.raises(OSError) as raised:
+        control._spawn_backend_process("test-token")
+
+    assert raised.value is other_error
+    assert other_calls == 1
+
+
+def test_start_returns_existing_ready_backend_without_spawn(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    ready = _status("running", ready=True, record=backend_record)
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "get_or_create_backend_token", lambda: "stored-token")
+    monkeypatch.setattr(control, "get_backend_status", lambda **kwargs: ready)
+    monkeypatch.setattr(
+        control,
+        "_spawn_backend_process",
+        lambda token: pytest.fail("ready backend must not be spawned again"),
+    )
+
+    assert control.start_backend() is ready
+
+
+def test_start_removes_stale_record_before_spawn(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    calls: list[object] = []
+    stale = _status("stale", record=backend_record)
+    ready = _status("running", ready=True, record=backend_record)
+    process = SimpleNamespace(pid=12345)
+    identity = {"pid": 12345, "executable": sys.executable, "creation_time": 1}
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(
+        control,
+        "get_or_create_backend_token",
+        lambda: calls.append("token") or "stored-token",
+    )
+    monkeypatch.setattr(
+        control,
+        "get_backend_status",
+        lambda **kwargs: calls.append("status") or stale,
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_backend_record_if_exact",
+        lambda record: calls.append(("remove", record)) or True,
+    )
+    monkeypatch.setattr(
+        control,
+        "_spawn_backend_process",
+        lambda token: calls.append(("spawn", token)) or process,
+    )
+    monkeypatch.setattr(
+        control,
+        "_spawn_identity_record",
+        lambda spawned: calls.append(("identity", spawned)) or identity,
+    )
+    monkeypatch.setattr(
+        control,
+        "_wait_for_ready_backend",
+        lambda spawned, **kwargs: calls.append(("wait", spawned)) or ready,
+    )
+
+    assert control.start_backend() is ready
+    names = [item if isinstance(item, str) else item[0] for item in calls]
+    assert names.index("remove") < names.index("spawn")
+    assert names == ["token", "status", "remove", "spawn", "identity", "wait"]
+
+
+def test_failed_start_terminates_only_exact_spawn_identity(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    process = SimpleNamespace(pid=54321)
+    identity = {
+        "pid": 54321,
+        "executable": r"C:\Contextor\.venv\Scripts\python.exe",
+        "creation_time": 123456789,
+    }
+    terminated: list[dict[str, object]] = []
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "get_or_create_backend_token", lambda: "stored-token")
+    monkeypatch.setattr(control, "get_backend_status", lambda **kwargs: _status("stopped"))
+    monkeypatch.setattr(control, "_spawn_backend_process", lambda token: process)
+    monkeypatch.setattr(control, "_spawn_identity_record", lambda spawned: identity)
+    monkeypatch.setattr(
+        control,
+        "_wait_for_ready_backend",
+        lambda *args, **kwargs: (_ for _ in ()).throw(
+            control.BackendControlError("cold start failed")
+        ),
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: terminated.append(record) or True,
+    )
+
+    with pytest.raises(control.BackendControlError, match="cold start failed"):
+        control.start_backend()
+
+    assert terminated == [identity]
+
+
+def test_stop_without_record_is_idempotent(
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "read_backend_record", lambda: None)
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: pytest.fail("no owner record means no termination"),
+    )
+
+    result = control.stop_backend()
+
+    assert result.state == "stopped"
+    assert result.ready is False
+
+
+def test_stop_stale_record_removes_metadata_without_termination(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    removed: list[PersistentBackendRecord] = []
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "read_backend_record", lambda: backend_record)
+    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda record: False)
+    monkeypatch.setattr(
+        control,
+        "remove_backend_record_if_exact",
+        lambda record: removed.append(record) or True,
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: pytest.fail("stale record must not terminate a process"),
+    )
+
+    result = control.stop_backend()
+
+    assert result.state == "stopped"
+    assert removed == [backend_record]
+
+
+def test_windows_stop_refuses_missing_creation_identity(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    record = replace(backend_record, creation_time=None)
+    monkeypatch.setattr(control.sys, "platform", "win32")
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "read_backend_record", lambda: record)
+    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda owner: True)
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda owner: pytest.fail("missing Windows creation identity forbids termination"),
+    )
+
+    with pytest.raises(control.BackendControlError, match="creation identity"):
+        control.stop_backend()
+
+
+def test_windows_stop_uses_exact_backend_record_for_termination(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    record = replace(backend_record, creation_time=555000111)
+    terminated: list[dict[str, object]] = []
+    cleaned: list[PersistentBackendRecord] = []
+    removed: list[PersistentBackendRecord] = []
+    monkeypatch.setattr(control.sys, "platform", "win32")
+    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
+    monkeypatch.setattr(control, "read_backend_record", lambda: record)
+    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda owner: True)
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda owner: terminated.append(owner) or True,
+    )
+    monkeypatch.setattr(control, "_wait_for_owner_exit", lambda owner, *, timeout: True)
+    monkeypatch.setattr(
+        control,
+        "_cleanup_owned_registry_children",
+        lambda owner: cleaned.append(owner),
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_backend_record_if_exact",
+        lambda owner: removed.append(owner) or True,
+    )
+
+    result = control.stop_backend()
+
+    assert result.state == "stopped"
+    assert terminated == [record.to_dict()]
+    assert terminated[0]["pid"] == record.pid
+    assert terminated[0]["executable"] == record.executable
+    assert terminated[0]["creation_time"] == record.creation_time
+    assert cleaned == [record]
+    assert removed == [record]
+
+
+def test_owned_registry_child_cleanup_is_parent_identity_scoped(
+    backend_record: PersistentBackendRecord,
+    monkeypatch: pytest.MonkeyPatch,
+) -> None:
+    good_path = Path(backend_record.process_registry) / "good.json"
+    wrong_creation_path = Path(backend_record.process_registry) / "wrong-creation.json"
+    other_parent_path = Path(backend_record.process_registry) / "other-parent.json"
+    good = {
+        "pid": 20001,
+        "parent_pid": backend_record.pid,
+        "parent_creation_time": backend_record.creation_time,
+    }
+    wrong_creation = {
+        "pid": 20002,
+        "parent_pid": backend_record.pid,
+        "parent_creation_time": backend_record.creation_time + 1,
+    }
+    other_parent = {
+        "pid": 20003,
+        "parent_pid": backend_record.pid + 1,
+        "parent_creation_time": backend_record.creation_time,
+    }
+    terminated: list[dict[str, object]] = []
+    removed: list[Path] = []
+    monkeypatch.setattr(
+        control,
+        "read_records",
+        lambda directory: [
+            (good_path, good),
+            (wrong_creation_path, wrong_creation),
+            (other_parent_path, other_parent),
+        ],
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda child: terminated.append(child) or True,
+    )
+    monkeypatch.setattr(control, "remove_record", lambda path: removed.append(path))
+
+    control._cleanup_owned_registry_children(backend_record)
+
+    assert terminated == [good]
+    assert removed == [good_path]
+
+
+def test_control_lock_same_process_is_exclusive(
+    tmp_path: Path,
+) -> None:
+    path = tmp_path / "control.lock"
+    holder_entered = threading.Event()
+    release_holder = threading.Event()
+    holder_errors: list[Exception] = []
+
+    def hold_lock() -> None:
+        try:
+            with control._BackendControlLock(path, timeout=2.0):
+                holder_entered.set()
+                if not release_holder.wait(timeout=2.0):
+                    holder_errors.append(TimeoutError("test release event was not set"))
+        except Exception as exc:  # pragma: no cover - asserted after joining
+            holder_errors.append(exc)
+
+    thread = threading.Thread(target=hold_lock)
+    thread.start()
+    try:
+        assert holder_entered.wait(timeout=2.0)
+        with pytest.raises(control.BackendControlError, match="lock is busy"):
+            with control._BackendControlLock(path, timeout=0.0):
+                pytest.fail("second same-process holder must not acquire the lock")
+    finally:
+        release_holder.set()
+        thread.join(timeout=2.0)
+
+    assert not thread.is_alive()
+    assert holder_errors == []
