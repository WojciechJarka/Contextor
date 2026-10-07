STATUS=IMPLEMENTED_FOCUSED_TESTS_PASS
HEAD=cf9e8c42ac653b647568a9714f8ee50f6a17c421

FILES_CHANGED:
- contextor/mcp_process_registry.py
- tests/test_mcp_process_registry.py
(walkthrough.md is this report and excluded from the source/test file list.)

CONTEXTOR_PRE_EDIT:
- get_file_edit_context for contextor.mcp_process_registry: module 266/1; direct_count=13; transitive_count=209; risk=0.0663.
- Blast-radius lookup confirmed existing consumers for the legacy APIs; the change does not redirect any production caller.
- Existing tests/test_mcp_process_registry.py was not found, so a dedicated focused test module was added.

NEW_API:
- Added frozen, slotted ProcessIdentityProbe(state, image, creation_time).
- Added probe_process_identity(pid) and private _windows_process_identity_probe(pid).
- Existing production callers remain on the legacy API; no caller was switched.

WINDOWS_TRI_STATE_SEMANTICS:
- Requests SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION.
- OpenProcess success: WAIT_OBJECT_0 -> dead; WAIT_TIMEOUT -> alive; wait failure or other value -> unknown.
- OpenProcess ERROR_INVALID_PARAMETER (87) -> dead; other open failures, including access denied, -> unknown.
- Image and FILETIME creation-time reads are best-effort; missing values do not change alive.
- The handle is closed in finally on every successfully opened handle path.

POSIX_TRI_STATE_SEMANTICS:
- os.kill(pid, 0) success -> alive; ProcessLookupError/ESRCH -> dead; PermissionError/EPERM -> alive; other OSError -> unknown.
- For alive, /proc/<pid>/exe is best-effort and creation_time is None.
- Invalid/non-positive or boolean PID input returns unknown. No owner match, PID reuse, or takeover policy was added.

EXISTING_API_UNCHANGED=YES
Evidence: source diff is additive only; bodies of _windows_process_identity, process_identity, record_matches_process, terminate_registered_process, and register_process are unchanged. No existing production caller was redirected.

TARGETED_TESTS:
Command:
& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_process_registry.py tests/test_mcp_regressions.py::test_registry_rejects_reused_pid tests/test_mcp_regressions.py::test_startup_cleanup_stops_only_orphaned_registered_processes
Run 1 (before final source correction): 13 passed, 1 third-party AuthlibDeprecationWarning, 4.74s.
Run 2 (after the final source correction): 13 passed, same warning, 3.58s. No full pytest suite was run.
CONTEXTOR_POST_EDIT:
- New symbols fetched through get_symbol_implementation: ProcessIdentityProbe, probe_process_identity, _windows_process_identity_probe.
- canonical_state=fresh
- canonical_revision=1609
- workspace_sync=verified
- provenance=live
- diagnostics: syntax_errors=0, name_collisions=0, cycles=0; all fresh.
- get_live_events(after_revision=1606): revision/latest_revision=1609, continuity=continuous, resync_required=false.
- Desktop watcher update_file events observed for both source and test files; no manual update_file call.

IMPLEMENTATION_RESULT=PASS
- No runtime lifecycle, owner claim, desktop, watchdog, backend shutdown, or other requested-for-later feature was implemented.
- No files besides the listed source and focused test module were changed.
- git diff --check passed.

FULL_DIFFS:
```diff
--- a/contextor/mcp_process_registry.py
+++ b/contextor/mcp_process_registry.py
@@ -6,0 +7,2 @@
+from dataclasses import dataclass
+import errno
@@ -13 +15,8 @@
-from typing import Any
+from typing import Any, Literal
+
+
+@dataclass(frozen=True, slots=True)
+class ProcessIdentityProbe:
+    state: Literal["alive", "dead", "unknown"]
+    image: str | None
+    creation_time: int | None
@@ -78,0 +88,94 @@
+def _windows_process_identity_probe(pid: int) -> ProcessIdentityProbe:
+    unknown = ProcessIdentityProbe("unknown", None, None)
+    try:
+        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
+        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
+        kernel32.OpenProcess.restype = wintypes.HANDLE
+        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
+        kernel32.WaitForSingleObject.restype = wintypes.DWORD
+        kernel32.QueryFullProcessImageNameW.argtypes = [
+            wintypes.HANDLE,
+            wintypes.DWORD,
+            wintypes.LPWSTR,
+            wintypes.PDWORD,
+        ]
+        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
+        kernel32.GetProcessTimes.argtypes = [
+            wintypes.HANDLE,
+            ctypes.POINTER(wintypes.FILETIME),
+            ctypes.POINTER(wintypes.FILETIME),
+            ctypes.POINTER(wintypes.FILETIME),
+            ctypes.POINTER(wintypes.FILETIME),
+        ]
+        kernel32.GetProcessTimes.restype = wintypes.BOOL
+        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
+        kernel32.CloseHandle.restype = wintypes.BOOL
+    except (OSError, AttributeError, TypeError, ValueError):
+        return unknown
+
+    process_query_limited_information = 0x1000
+    synchronize = 0x00100000
+    try:
+        handle = kernel32.OpenProcess(
+            process_query_limited_information | synchronize,
+            False,
+            pid,
+        )
+    except OSError:
+        return unknown
+
+    if not handle:
+        if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER
+            return ProcessIdentityProbe("dead", None, None)
+        return unknown
+
+    try:
+        try:
+            wait_result = kernel32.WaitForSingleObject(handle, 0)
+        except OSError:
+            return unknown
+
+        if wait_result == 0:  # WAIT_OBJECT_0
+            return ProcessIdentityProbe("dead", None, None)
+        if wait_result != 258:  # WAIT_TIMEOUT
+            return unknown
+
+        image = None
+        try:
+            size = ctypes.c_ulong(32768)
+            buffer = ctypes.create_unicode_buffer(size.value)
+            if kernel32.QueryFullProcessImageNameW(
+                handle,
+                0,
+                buffer,
+                ctypes.byref(size),
+            ):
+                image = buffer.value
+        except (OSError, TypeError, ValueError):
+            pass
+
+        created = None
+        try:
+            creation = wintypes.FILETIME()
+            exit_time = wintypes.FILETIME()
+            kernel = wintypes.FILETIME()
+            user = wintypes.FILETIME()
+            if kernel32.GetProcessTimes(
+                handle,
+                ctypes.byref(creation),
+                ctypes.byref(exit_time),
+                ctypes.byref(kernel),
+                ctypes.byref(user),
+            ):
+                created = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
+        except (OSError, TypeError, ValueError):
+            pass
+
+        return ProcessIdentityProbe("alive", image, created)
+    finally:
+        try:
+            kernel32.CloseHandle(handle)
+        except OSError:
+            pass
+
+
@@ -91,0 +195,28 @@
+
+
+def probe_process_identity(pid: int) -> ProcessIdentityProbe:
+    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
+        return ProcessIdentityProbe("unknown", None, None)
+
+    if sys_platform_is_windows():
+        return _windows_process_identity_probe(pid)
+
+    try:
+        os.kill(pid, 0)
+    except ProcessLookupError:
+        return ProcessIdentityProbe("dead", None, None)
+    except PermissionError:
+        return ProcessIdentityProbe("alive", None, None)
+    except OSError as exc:
+        if exc.errno == errno.ESRCH:
+            return ProcessIdentityProbe("dead", None, None)
+        if exc.errno == errno.EPERM:
+            return ProcessIdentityProbe("alive", None, None)
+        return ProcessIdentityProbe("unknown", None, None)
+
+    image = None
+    try:
+        image = str(Path(f"/proc/{pid}/exe").resolve(strict=True))
+    except (OSError, RuntimeError):
+        pass
+    return ProcessIdentityProbe("alive", image, None)

--- /dev/null
+++ b/tests/test_mcp_process_registry.py
@@ -0,0 +1,226 @@
+from __future__ import annotations
+
+import errno
+import os
+from ctypes import wintypes
+
+import pytest
+
+from contextor import mcp_process_registry as registry
+
+
+class _FakeWinApiFunction:
+    def __init__(self, callback):
+        self.callback = callback
+
+    def __call__(self, *args):
+        return self.callback(*args)
+
+
+class _FakeKernel32:
+    def __init__(
+        self,
+        *,
+        open_result=1,
+        wait_result=258,
+        image_result=0,
+        times_result=0,
+    ):
+        self.closed_handles = []
+        self.OpenProcess = _FakeWinApiFunction(lambda *_args: open_result)
+        self.WaitForSingleObject = _FakeWinApiFunction(lambda *_args: wait_result)
+        self.QueryFullProcessImageNameW = _FakeWinApiFunction(
+            lambda *_args: image_result
+        )
+        self.GetProcessTimes = _FakeWinApiFunction(lambda *_args: times_result)
+        self.CloseHandle = _FakeWinApiFunction(
+            lambda handle: self.closed_handles.append(handle) or 1
+        )
+
+
+def _patch_windows_probe(monkeypatch, kernel32, *, last_error=0):
+    monkeypatch.setattr(registry.ctypes, "WinDLL", lambda *_args, **_kwargs: kernel32, raising=False)
+    monkeypatch.setattr(
+        registry.ctypes,
+        "get_last_error",
+        lambda: last_error,
+        raising=False,
+    )
+
+
+def test_probe_current_process_is_alive():
+    result = registry.probe_process_identity(os.getpid())
+
+    assert result.state == "alive"
+
+
+def test_windows_invalid_process_error_is_dead(monkeypatch):
+    kernel32 = _FakeKernel32(open_result=0)
+    _patch_windows_probe(monkeypatch, kernel32, last_error=87)
+
+    result = registry._windows_process_identity_probe(987654321)
+
+    assert result.state == "dead"
+    assert result.image is None
+    assert result.creation_time is None
+    assert kernel32.closed_handles == []
+
+
+def test_windows_open_process_access_denied_is_unknown(monkeypatch):
+    kernel32 = _FakeKernel32(open_result=0)
+    _patch_windows_probe(monkeypatch, kernel32, last_error=5)
+
+    result = registry._windows_process_identity_probe(1234)
+
+    assert result.state == "unknown"
+    assert kernel32.closed_handles == []
+
+
+def test_windows_wait_failure_is_unknown_and_closes_handle(monkeypatch):
+    kernel32 = _FakeKernel32(wait_result=0xFFFFFFFF)
+    _patch_windows_probe(monkeypatch, kernel32)
+
+    result = registry._windows_process_identity_probe(1234)
+
+    assert result.state == "unknown"
+    assert kernel32.closed_handles == [1]
+
+
+@pytest.mark.parametrize(
+    ("image_result", "times_result", "expected_image", "expected_creation_time"),
+    [
+        (0, 1, None, 123456789),
+        (1, 0, "C:/Contextor/python.exe", None),
+    ],
+)
+def test_windows_auxiliary_identity_failure_preserves_alive(
+    monkeypatch,
+    image_result,
+    times_result,
+    expected_image,
+    expected_creation_time,
+):
+    kernel32 = _FakeKernel32(
+        image_result=image_result,
+        times_result=times_result,
+    )
+    if image_result:
+        def set_image(_handle, _flags, buffer, _size):
+            buffer.value = "C:/Contextor/python.exe"
+            return 1
+
+        kernel32.QueryFullProcessImageNameW = _FakeWinApiFunction(set_image)
+    if times_result:
+        def set_times(_handle, creation, _exit_time, _kernel, _user):
+            filetime = registry.ctypes.cast(
+                creation,
+                registry.ctypes.POINTER(wintypes.FILETIME),
+            ).contents
+            filetime.dwHighDateTime = 0
+            filetime.dwLowDateTime = 123456789
+            return 1
+
+        kernel32.GetProcessTimes = _FakeWinApiFunction(set_times)
+    _patch_windows_probe(monkeypatch, kernel32)
+
+    result = registry._windows_process_identity_probe(1234)
+
+    assert result.state == "alive"
+    assert result.image == expected_image
+    assert result.creation_time == expected_creation_time
+    assert kernel32.closed_handles == [1]
+
+
+def test_posix_esrch_is_dead(monkeypatch):
+    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)
+
+    def missing_process(_pid, _signal):
+        raise ProcessLookupError(errno.ESRCH, "no such process")
+
+    monkeypatch.setattr(registry.os, "kill", missing_process)
+
+    result = registry.probe_process_identity(987654321)
+
+    assert result.state == "dead"
+    assert result.image is None
+    assert result.creation_time is None
+
+
+def test_posix_eperm_is_alive(monkeypatch):
+    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)
+
+    def denied(_pid, _signal):
+        raise PermissionError(errno.EPERM, "operation not permitted")
+
+    monkeypatch.setattr(registry.os, "kill", denied)
+
+    result = registry.probe_process_identity(987654321)
+
+    assert result.state == "alive"
+    assert result.creation_time is None
+
+
+def test_ambiguous_posix_error_is_unknown(monkeypatch):
+    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: False)
+
+    def ambiguous(_pid, _signal):
+        raise OSError(errno.EIO, "indeterminate process probe")
+
+    monkeypatch.setattr(registry.os, "kill", ambiguous)
+
+    result = registry.probe_process_identity(987654321)
+
+    assert result.state == "unknown"
+
+
+def test_legacy_process_identity_tuple_contract_is_unchanged(monkeypatch):
+    expected = ("C:/Contextor/python.exe", 123456789, True)
+    monkeypatch.setattr(registry, "sys_platform_is_windows", lambda: True)
+    monkeypatch.setattr(
+        registry,
+        "_windows_process_identity",
+        lambda _pid: expected,
+    )
+
+    assert registry.process_identity(1234) == expected
+
+
+def test_legacy_record_match_semantics_are_unchanged(monkeypatch):
+    monkeypatch.setattr(
+        registry,
+        "process_identity",
+        lambda _pid: ("C:/Git/bin/GIT.EXE", 100, True),
+    )
+    assert registry.record_matches_process(
+        {
+            "pid": 1234,
+            "executable": "C:/Other/git.exe",
+            "creation_time": 100,
+        }
+    )
+
+    monkeypatch.setattr(
+        registry,
+        "process_identity",
+        lambda _pid: (None, None, True),
+    )
+    assert registry.record_matches_process(
+        {
+            "pid": 1234,
+            "executable": "git.exe",
+            "creation_time": 999,
+        }
+    )
+
+    monkeypatch.setattr(
+        registry,
+        "process_identity",
+        lambda _pid: ("C:/Git/bin/git.exe", 101, True),
+    )
+    assert not registry.record_matches_process(
+        {
+            "pid": 1234,
+            "executable": "C:/Other/git.exe",
+            "creation_time": 100,
+        }
+    )
```
