# PY315-R4B — backend-owned Windows Job Object

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `74e9b026a5b904f93af7d6704f80b8dcacab7aea`; pre-edit Git status was clean. Contextor MCP reported `workspace_sync=verified` for `contextor.mcp_main` and `contextor.core.live_state.runtime` at revision 916. Both exact SEARCH blocks occurred once; the two target files did not exist. R3/R4A were already in local HEAD.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: Edits 2 and 3 were applied at their exact anchors with `apply_patch`. The two new files match the architect's supplied content, aside from final newline formatting. No additional source or test edits were made.

## BACKEND_JOB_CREATION
CODE_PATH_PROVED: On Windows, the persistent-backend entry creates a Job Object, sets `KILL_ON_JOB_CLOSE | BREAKAWAY_OK`, and assigns the current backend process before importing `mcp_server`. Failed setup raises `BackendJobError` and closes the unowned handle.

## JOB_LIFETIME
CODE_PATH_PROVED: The successful Job handle is retained in module state for the backend process lifetime and a guard marker is set only afterward. No Desktop or host-owned MCP path installs this Job.

## DESCENDANT_OWNERSHIP
The Job guards processes assigned to it until final handle close. Explicit breakaway descendants are not Job-owned. This patch does not yet certify full `/T` parity.

## LIVE_BREAKAWAY
CODE_PATH_PROVED: When the backend guard marker is set, LIVE spawn verifies that the new process is outside the backend Job before return. Membership verification failure attempts bounded termination and propagates the failure. Access-denied breakaway does not enter the legacy fallback while the guard is active. For non-backend callers, the legacy fallback remains.

## GUARD_INSTALL_FAILURES
The supplied fake-kernel tests cover failed assignment and failed limit configuration, and confirm the MCP server does not start after a guard installation failure. Real Windows integration has not been executed.

## TARGETED_TEST_RESULTS
`py_compile` on the four specified files: PASS.
`tests/test_mcp_backend_job_guard.py -q`: 13 passed, 1 warning.
`tests/test_live_job_object.py -q -k "not real_windows_job_object_breakaway_integration and not windows_job_object_cleanup_regression"`: 6 passed, 4 deselected.
`tests/test_mcp_shared_backend_server_mode.py tests/test_mcp_backend_control.py -q`: 34 passed, 1 warning.
No full pytest, real process termination, or launcher execution.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Post-change Contextor MCP reports `workspace_sync=verified` for `contextor.mcp_backend_job` and `contextor.mcp_main` at revision 918. The later `contextor.core.live_state.runtime` read at revision 919 reports `workspace_sync=unverified` with a generation-proof warning, so source synchronization for that file is not certified. This does not prove active loaded-code adoption. Existing active backend has not been restarted.

## FILES_CHANGED
- `contextor/mcp_backend_job.py`
- `contextor/mcp_main.py`
- `contextor/core/live_state/runtime.py`
- `tests/test_mcp_backend_job_guard.py`

## FULL_DIFFS
```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 1904607..5053056 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -790,7 +790,7 @@ def _spawn_runtime_subprocess(
     primary_flags = base_flags | CREATE_BREAKAWAY_FROM_JOB
 
     try:
-        return subprocess.Popen(
+        process = subprocess.Popen(
             cmd,
             cwd=str(cwd),
             env=env,
@@ -799,9 +799,38 @@ def _spawn_runtime_subprocess(
             stderr=subprocess.DEVNULL,
             creationflags=primary_flags,
         )
+
+        if os.environ.get("CONTEXTOR_BACKEND_JOB_GUARD") == "1":
+            from contextor.mcp_backend_job import (
+                require_live_outside_backend_job,
+            )
+
+            try:
+                require_live_outside_backend_job(process)
+            except BaseException:
+                try:
+                    process.terminate()
+                    process.wait(timeout=2.0)
+                except Exception:
+                    try:
+                        process.kill()
+                        process.wait(timeout=2.0)
+                    except Exception:
+                        pass
+                raise
+
+        return process
+
     except OSError as exc:
         if getattr(exc, "winerror", None) != 5:
             raise
+
+        if os.environ.get("CONTEXTOR_BACKEND_JOB_GUARD") == "1":
+            raise RuntimeError(
+                "LIVE breakaway failed while persistent "
+                "backend Job Object protection is active"
+            ) from exc
+
         import logging
 
         logging.getLogger("contextor.core.live_state.runtime").info(
diff --git a/contextor/mcp_main.py b/contextor/mcp_main.py
index 8257437..86a90cd 100644
--- a/contextor/mcp_main.py
+++ b/contextor/mcp_main.py
@@ -1,7 +1,20 @@
 import multiprocessing
+import os
+import sys
 
 
 def main() -> None:
+    if (
+        sys.platform == "win32"
+        and os.environ.get("CONTEXTOR_MCP_SERVER_ROLE")
+        == "persistent-backend"
+    ):
+        from contextor.mcp_backend_job import (
+            protect_persistent_backend,
+        )
+
+        protect_persistent_backend()
+
     from contextor.mcp_server import main as run_server
 
     run_server()
diff --git a/contextor/mcp_backend_job.py b/contextor/mcp_backend_job.py
new file mode 100644
--- /dev/null
+++ b/contextor/mcp_backend_job.py
@@ -0,0 +1,226 @@
+"""Windows process-tree ownership for the persistent MCP backend."""
+
+from __future__ import annotations
+
+import ctypes
+import os
+import sys
+from ctypes import wintypes
+from typing import Any
+
+
+class BackendJobError(RuntimeError):
+    """The backend process tree cannot be safely owned or verified."""
+
+
+class _IO_COUNTERS(ctypes.Structure):
+    _fields_ = [
+        ("ReadOperationCount", ctypes.c_uint64),
+        ("WriteOperationCount", ctypes.c_uint64),
+        ("OtherOperationCount", ctypes.c_uint64),
+        ("ReadTransferCount", ctypes.c_uint64),
+        ("WriteTransferCount", ctypes.c_uint64),
+        ("OtherTransferCount", ctypes.c_uint64),
+    ]
+
+
+class _BASIC_LIMITS(ctypes.Structure):
+    _fields_ = [
+        ("PerProcessUserTimeLimit", ctypes.c_int64),
+        ("PerJobUserTimeLimit", ctypes.c_int64),
+        ("LimitFlags", wintypes.DWORD),
+        ("MinimumWorkingSetSize", ctypes.c_size_t),
+        ("MaximumWorkingSetSize", ctypes.c_size_t),
+        ("ActiveProcessLimit", wintypes.DWORD),
+        ("Affinity", ctypes.c_size_t),
+        ("PriorityClass", wintypes.DWORD),
+        ("SchedulingClass", wintypes.DWORD),
+    ]
+
+
+class _EXTENDED_LIMITS(ctypes.Structure):
+    _fields_ = [
+        ("BasicLimitInformation", _BASIC_LIMITS),
+        ("IoInfo", _IO_COUNTERS),
+        ("ProcessMemoryLimit", ctypes.c_size_t),
+        ("JobMemoryLimit", ctypes.c_size_t),
+        ("PeakProcessMemoryLimit", ctypes.c_size_t),
+        ("PeakJobMemoryLimit", ctypes.c_size_t),
+    ]
+
+
+_KILL_ON_JOB_CLOSE = 0x00002000
+_BREAKAWAY_OK = 0x00000800
+_EXTENDED_LIMIT_INFORMATION = 9
+
+_active_handle: Any = None
+_active_pid: int | None = None
+
+
+def _kernel32() -> Any:
+    kernel = ctypes.WinDLL(
+        "kernel32",
+        use_last_error=True,
+    )
+
+    kernel.CreateJobObjectW.argtypes = [
+        ctypes.c_void_p,
+        wintypes.LPCWSTR,
+    ]
+    kernel.CreateJobObjectW.restype = wintypes.HANDLE
+
+    kernel.SetInformationJobObject.argtypes = [
+        wintypes.HANDLE,
+        ctypes.c_int,
+        ctypes.c_void_p,
+        wintypes.DWORD,
+    ]
+    kernel.SetInformationJobObject.restype = wintypes.BOOL
+
+    kernel.GetCurrentProcess.argtypes = []
+    kernel.GetCurrentProcess.restype = wintypes.HANDLE
+
+    kernel.AssignProcessToJobObject.argtypes = [
+        wintypes.HANDLE,
+        wintypes.HANDLE,
+    ]
+    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
+
+    kernel.IsProcessInJob.argtypes = [
+        wintypes.HANDLE,
+        wintypes.HANDLE,
+        ctypes.POINTER(wintypes.BOOL),
+    ]
+    kernel.IsProcessInJob.restype = wintypes.BOOL
+
+    kernel.CloseHandle.argtypes = [
+        wintypes.HANDLE,
+    ]
+    kernel.CloseHandle.restype = wintypes.BOOL
+
+    return kernel
+
+
+def protect_persistent_backend() -> None:
+    """Own backend descendants until the backend process exits."""
+    global _active_handle
+    global _active_pid
+
+    if sys.platform != "win32":
+        return
+
+    current_pid = os.getpid()
+
+    if _active_handle is not None:
+        if _active_pid != current_pid:
+            raise BackendJobError(
+                "backend Job Object belongs to a different process"
+            )
+        return
+
+    kernel = _kernel32()
+
+    handle = kernel.CreateJobObjectW(None, None)
+
+    if not handle:
+        raise BackendJobError(
+            "CreateJobObjectW failed; "
+            f"winerror={ctypes.get_last_error()}"
+        )
+
+    try:
+        limits = _EXTENDED_LIMITS()
+
+        limits.BasicLimitInformation.LimitFlags = (
+            _KILL_ON_JOB_CLOSE | _BREAKAWAY_OK
+        )
+
+        if not kernel.SetInformationJobObject(
+            handle,
+            _EXTENDED_LIMIT_INFORMATION,
+            ctypes.byref(limits),
+            ctypes.sizeof(limits),
+        ):
+            raise BackendJobError(
+                "SetInformationJobObject failed; "
+                f"winerror={ctypes.get_last_error()}"
+            )
+
+        if not kernel.AssignProcessToJobObject(
+            handle,
+            kernel.GetCurrentProcess(),
+        ):
+            raise BackendJobError(
+                "AssignProcessToJobObject failed; "
+                f"winerror={ctypes.get_last_error()}"
+            )
+
+    except BaseException:
+        kernel.CloseHandle(handle)
+        raise
+
+    # Retain this non-inheritable Job Object handle for the
+    # entire backend lifetime. Do not close it while running.
+    #
+    # The final OS handle close terminates processes that
+    # remain assigned to this Job Object.
+    _active_handle = handle
+    _active_pid = current_pid
+
+    # This marker is set ONLY after successful installation.
+    os.environ["CONTEXTOR_BACKEND_JOB_GUARD"] = "1"
+
+
+def require_live_outside_backend_job(
+    process: Any,
+) -> None:
+    """Verify that an explicitly breaking-away LIVE process escaped."""
+    if sys.platform != "win32":
+        return
+
+    if (
+        _active_handle is None
+        or _active_pid != os.getpid()
+    ):
+        raise BackendJobError(
+            "backend Job Object is not installed"
+        )
+
+    process_handle = getattr(process, "_handle", None)
+
+    try:
+        child_handle = int(process_handle)
+    except (TypeError, ValueError):
+        raise BackendJobError(
+            "LIVE process handle is unavailable"
+        ) from None
+
+    if child_handle <= 0:
+        raise BackendJobError(
+            "LIVE process handle is invalid"
+        )
+
+    kernel = _kernel32()
+    belongs = wintypes.BOOL(0)
+
+    if not kernel.IsProcessInJob(
+        child_handle,
+        _active_handle,
+        ctypes.byref(belongs),
+    ):
+        raise BackendJobError(
+            "LIVE Job Object membership could not be verified; "
+            f"winerror={ctypes.get_last_error()}"
+        )
+
+    if belongs.value:
+        raise BackendJobError(
+            "LIVE did not break away from the backend Job Object"
+        )
+
+
+__all__ = [
+    "BackendJobError",
+    "protect_persistent_backend",
+    "require_live_outside_backend_job",
+]
diff --git a/tests/test_mcp_backend_job_guard.py b/tests/test_mcp_backend_job_guard.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_backend_job_guard.py
@@ -0,0 +1,443 @@
+from __future__ import annotations
+
+import ctypes
+import os
+from ctypes import wintypes
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.mcp_backend_job as guard
+import contextor.mcp_main as entry
+import contextor.mcp_server as server
+import contextor.core.live_state.runtime as live_runtime
+
+
+class _Function:
+    def __init__(self, callback):
+        self.callback = callback
+        self.calls = []
+
+    def __call__(self, *args):
+        self.calls.append(args)
+        return self.callback(*args)
+
+
+class _Kernel:
+    def __init__(self):
+        self.limits = None
+        self.member = False
+        self.assign_ok = True
+        self.set_ok = True
+
+        self.CreateJobObjectW = _Function(
+            lambda *_args: 71
+        )
+        self.SetInformationJobObject = _Function(
+            self._set_limits
+        )
+        self.GetCurrentProcess = _Function(
+            lambda: 333
+        )
+        self.AssignProcessToJobObject = _Function(
+            lambda *_args: int(self.assign_ok)
+        )
+        self.IsProcessInJob = _Function(
+            self._is_member
+        )
+        self.CloseHandle = _Function(
+            lambda *_args: 1
+        )
+
+    def _set_limits(
+        self,
+        handle,
+        info_class,
+        info_ptr,
+        size,
+    ):
+        self.limits = ctypes.cast(
+            info_ptr,
+            ctypes.POINTER(guard._EXTENDED_LIMITS),
+        ).contents.BasicLimitInformation.LimitFlags
+
+        return int(self.set_ok)
+
+    def _is_member(self, process, job, result):
+        value = ctypes.cast(
+            result,
+            ctypes.POINTER(wintypes.BOOL),
+        )
+        value.contents.value = int(self.member)
+        return 1
+
+
+@pytest.fixture
+def fake_job(monkeypatch):
+    kernel = _Kernel()
+
+    monkeypatch.setattr(
+        guard.ctypes,
+        "WinDLL",
+        lambda *_args, **_kwargs: kernel,
+        raising=False,
+    )
+    monkeypatch.setattr(
+        guard.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(
+        guard,
+        "_active_handle",
+        None,
+    )
+    monkeypatch.setattr(
+        guard,
+        "_active_pid",
+        None,
+    )
+    monkeypatch.delenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        raising=False,
+    )
+
+    return kernel
+
+
+def test_backend_job_owns_descendant_lifetime(
+    fake_job,
+):
+    guard.protect_persistent_backend()
+
+    assert fake_job.limits == 0x2800
+    assert fake_job.CreateJobObjectW.calls == [
+        (None, None)
+    ]
+    assert fake_job.AssignProcessToJobObject.calls == [
+        (71, 333)
+    ]
+    assert fake_job.CloseHandle.calls == []
+    assert guard._active_handle == 71
+    assert guard._active_pid == os.getpid()
+    assert os.environ["CONTEXTOR_BACKEND_JOB_GUARD"] == "1"
+
+
+def test_guard_install_is_idempotent(fake_job):
+    guard.protect_persistent_backend()
+    guard.protect_persistent_backend()
+
+    assert len(fake_job.CreateJobObjectW.calls) == 1
+    assert len(
+        fake_job.AssignProcessToJobObject.calls
+    ) == 1
+
+
+def test_assignment_failure_closes_unowned_job(
+    fake_job,
+):
+    fake_job.assign_ok = False
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="AssignProcessToJobObject",
+    ):
+        guard.protect_persistent_backend()
+
+    assert fake_job.CloseHandle.calls == [(71,)]
+    assert guard._active_handle is None
+    assert (
+        "CONTEXTOR_BACKEND_JOB_GUARD"
+        not in os.environ
+    )
+
+
+def test_limit_failure_blocks_assignment(fake_job):
+    fake_job.set_ok = False
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="SetInformationJobObject",
+    ):
+        guard.protect_persistent_backend()
+
+    assert fake_job.AssignProcessToJobObject.calls == []
+    assert fake_job.CloseHandle.calls == [(71,)]
+
+
+def test_missing_guard_refuses_live_verification(
+    fake_job,
+):
+    with pytest.raises(
+        guard.BackendJobError,
+        match="not installed",
+    ):
+        guard.require_live_outside_backend_job(
+            SimpleNamespace(_handle=99)
+        )
+
+
+def test_live_outside_job_is_accepted(fake_job):
+    guard.protect_persistent_backend()
+    fake_job.member = False
+
+    guard.require_live_outside_backend_job(
+        SimpleNamespace(_handle=99)
+    )
+
+    assert fake_job.IsProcessInJob.calls
+    assert fake_job.IsProcessInJob.calls[0][:2] == (
+        99,
+        71,
+    )
+
+
+def test_live_inside_job_is_rejected(fake_job):
+    guard.protect_persistent_backend()
+    fake_job.member = True
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="did not break away",
+    ):
+        guard.require_live_outside_backend_job(
+            SimpleNamespace(_handle=99)
+        )
+
+
+def test_mcp_entry_installs_guard_before_server(
+    monkeypatch,
+):
+    events = []
+
+    monkeypatch.setattr(
+        entry.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "persistent-backend",
+    )
+    monkeypatch.setattr(
+        guard,
+        "protect_persistent_backend",
+        lambda: events.append("guard"),
+    )
+    monkeypatch.setattr(
+        server,
+        "main",
+        lambda: events.append("server"),
+    )
+
+    entry.main()
+
+    assert events == ["guard", "server"]
+
+
+def test_mcp_entry_refuses_server_after_guard_failure(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        entry.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "persistent-backend",
+    )
+
+    def fail_guard():
+        raise guard.BackendJobError(
+            "assignment unavailable"
+        )
+
+    monkeypatch.setattr(
+        guard,
+        "protect_persistent_backend",
+        fail_guard,
+    )
+    monkeypatch.setattr(
+        server,
+        "main",
+        lambda: pytest.fail(
+            "unprotected server startup"
+        ),
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="assignment unavailable",
+    ):
+        entry.main()
+
+
+def test_nonpersistent_mcp_skips_guard(
+    monkeypatch,
+):
+    events = []
+
+    monkeypatch.setattr(
+        entry.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_SERVER_ROLE",
+        "host-owned",
+    )
+    monkeypatch.setattr(
+        guard,
+        "protect_persistent_backend",
+        lambda: pytest.fail(
+            "nonpersistent MCP entered backend job"
+        ),
+    )
+    monkeypatch.setattr(
+        server,
+        "main",
+        lambda: events.append("server"),
+    )
+
+    entry.main()
+
+    assert events == ["server"]
+
+
+def test_guarded_live_refuses_breakaway_fallback(
+    monkeypatch,
+):
+    calls = []
+
+    def denied(*_args, **_kwargs):
+        calls.append("spawn")
+        error = PermissionError(
+            "Access is denied"
+        )
+        error.winerror = 5
+        raise error
+
+    monkeypatch.setattr(
+        live_runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        "1",
+    )
+    monkeypatch.setattr(
+        live_runtime.subprocess,
+        "Popen",
+        denied,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="LIVE breakaway failed",
+    ):
+        live_runtime._spawn_runtime_subprocess(
+            ["python.exe"],
+            Path("."),
+            {},
+        )
+
+    assert calls == ["spawn"]
+
+
+def test_guarded_live_verifies_spawn_before_return(
+    monkeypatch,
+):
+    process = SimpleNamespace(_handle=99)
+    verified = []
+
+    monkeypatch.setattr(
+        live_runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        "1",
+    )
+    monkeypatch.setattr(
+        live_runtime.subprocess,
+        "Popen",
+        lambda *_args, **_kwargs: process,
+    )
+    monkeypatch.setattr(
+        guard,
+        "require_live_outside_backend_job",
+        lambda actual: verified.append(actual),
+    )
+
+    result = live_runtime._spawn_runtime_subprocess(
+        ["python.exe"],
+        Path("."),
+        {},
+    )
+
+    assert result is process
+    assert verified == [process]
+
+
+def test_guarded_live_rejects_membership_and_terminates(
+    monkeypatch,
+):
+    calls = []
+
+    class _Process:
+        _handle = 99
+
+        def terminate(self):
+            calls.append("terminate")
+
+        def wait(self, timeout):
+            calls.append(("wait", timeout))
+            return 1
+
+    process = _Process()
+
+    monkeypatch.setattr(
+        live_runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        "1",
+    )
+    monkeypatch.setattr(
+        live_runtime.subprocess,
+        "Popen",
+        lambda *_args, **_kwargs: process,
+    )
+
+    def fail_membership(actual):
+        assert actual is process
+        raise guard.BackendJobError(
+            "LIVE did not break away"
+        )
+
+    monkeypatch.setattr(
+        guard,
+        "require_live_outside_backend_job",
+        fail_membership,
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="did not break away",
+    ):
+        live_runtime._spawn_runtime_subprocess(
+            ["python.exe"],
+            Path("."),
+            {},
+        )
+
+    assert calls == [
+        "terminate",
+        ("wait", 2.0),
+    ]
```

## REMAINING_UNKNOWN
The legacy tree-kill test remains an open gate. Registry DEAD/UNKNOWN/MISMATCH cleanup requires R4C. Real Windows Job Object integration, descendant-tree parity, active backend code adoption, and synchronization of `contextor.core.live_state.runtime` remain unverified.

## FINAL_VERDICT
PARTIAL_JOB_GUARD_IMPLEMENTED_TREE_GATE_OPEN.
