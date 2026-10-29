# CONTEXTOR P1D3-D2B-EXIT-S2 — Windows test process cleanup hardening

## PREFLIGHT

DIRECT_EVIDENCE: Current checkout at task start matched both named anchors. `tests/test_live_job_object.py::test_real_windows_job_object_breakaway_integration` created a Windows Job Object, configured flags `0x2000 | 0x0800`, spawned a helper, asserted assignment, then blocked on `helper.stdout.readline()` before entering cleanup `try/finally`. `tests/test_live_state_ipc.py::test_connect_or_start_replaces_proven_orphan_with_dead_owner` spawned a real runtime process, polled `connect(repo)` before cleanup, assigned `client` inside `try`, and called `client.request("shutdown")` before `proc.kill()` in `finally`. Contextor MCP resolved both test modules before edit; direct local source confirmed exact anchors. No source drift or preflight mismatch.

## INITIAL / FINAL HEAD

DIRECT_EVIDENCE: Initial and final HEAD `b8c982d2693797ac6f4f1c8d9901bc20e0368155`. No Git mutation.

## INITIAL / FINAL WORKTREE

DIRECT_EVIDENCE: Initial worktree had only pre-existing modified `walkthrough.md`. Final worktree has modified `tests/test_live_job_object.py`, `tests/test_live_state_ipc.py`, and `walkthrough.md`. The initial report was preserved until the final S2 report overwrite; no other files were edited.

## ROOT CAUSE A

CODE_PATH_PROVED: A failed `AssignProcessToJobObject` assertion or helper readiness failure occurred before cleanup, allowing test-created helper/Job resources to survive. `stdout.readline()` had no deadline. This concerned a temporary test repo; no interaction with the active user service was demonstrated.

## ROOT CAUSE B

CODE_PATH_PROVED: A readiness-loop exception occurred before the `try/finally`. A failed `connect_or_start` left `client` unbound, making cleanup raise `UnboundLocalError`; a shutdown exception could skip process kill/reap. The subprocess used a temporary repo/cache/state root.

## EXACT IMPLEMENTATION

DIRECT_EVIDENCE: In the Job Object test, `helper` and `live_client` are initialized immediately after successful Job creation; configuration, spawn, assignment and readiness are inside outer `try/finally`. The helper writes its returned service PID to `tmp_path/live-helper-ready`; the parent polls this file with `time.monotonic()` and a 15-second deadline, aborting on helper exit. The existing Job flags, owner identity and LIVE survival assertions remain. Cleanup closes the Job handle, attempts shutdown through the existing client or a single isolated-repo `connect(repo)`, then terminates and reaps the helper with finite waits. Shutdown failure cannot skip helper cleanup. No broad process-name termination was added.

DIRECT_EVIDENCE: In the orphan replacement test, `client = None` precedes `try`; the readiness loop and replacement call are protected. Cleanup attempts isolated client resolution only if needed, shuts down if available, then independently kills and waits for the originally spawned process. It records whether the body had already failed, so a reaping timeout cannot mask that original exception. Production code, endpoint schema, ownership and IPC contracts were not changed.

## FAILURE-PATH REGRESSION EVIDENCE

DIRECT_EVIDENCE: Five controlled-double cases passed after final edits: Job assignment failure enters cleanup; Job readiness timeout is finite; Job shutdown exception still permits helper cleanup; orphan failure before client assignment preserves its original exception and reaps the process; orphan shutdown exception does not mask a body assertion and does not skip process cleanup. These regressions launch no additional real LIVE service.

DIRECT_EVIDENCE: The first attempted regression run was interrupted with exit 1 because the initial fake monotonic clock stopped advancing after two values, causing the controlled timeout case to hang. The fake clock was changed to a monotonically increasing counter. The next run passed 5 tests in 26.46 s (outer stopwatch 28.1291439 s), and the final post-edit run passed 5 tests in 1.77 s (outer 3.5106132 s), exit 0. No claim is based on the interrupted run.

## REAL WINDOWS TEST RESULTS

DIRECT_EVIDENCE: On Windows, the two existing real integration tests ran by exact node ID after focused regressions and passed: 2 passed in 16.98 s (outer 18.7997029 s), exit 0. After the final cleanup refinement, both ran again and passed: 2 passed in 11.62 s (outer 12.9719745 s), exit 0. The Job Object test still verifies LIVE survives closing the helper Job; the orphan test still verifies replacement ownership. No full modules or global pytest were run.

## PROCESS CLEANUP EVIDENCE

DIRECT_EVIDENCE: Controlled doubles recorded helper `terminate`/`wait` and orphan `kill`/`wait` even on injected failures. The real tests completed without fixture errors. A post-run read-only Win32_Process query found 0 command lines matching both `contextor.core.live_state.runtime` and `pytest-of-DafoO`. This query cannot identify every possible test-created process and is not proof of active service state. No user process was terminated by this agent.

## PY_COMPILE / DIFF CHECK

DIRECT_EVIDENCE: `& .\.venv\Scripts\python.exe -m py_compile tests/test_live_job_object.py tests/test_live_state_ipc.py` exited 0; final run 0.3004999 s. `git diff --check -- tests/test_live_job_object.py tests/test_live_state_ipc.py` exited 0. Git emitted only LF-to-CRLF advisory warnings; no whitespace errors.

## EXACT EXECUTION COMMANDS

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs tests/test_live_job_object.py::test_windows_job_object_cleanup_regression tests/test_live_state_ipc.py::test_orphan_replacement_cleanup_regression
# final: exit 0; 5 passed in 1.77s; outer 3.5106132s

.\.venv\Scripts\python.exe -m pytest -q -rs tests/test_live_job_object.py::test_real_windows_job_object_breakaway_integration tests/test_live_state_ipc.py::test_connect_or_start_replaces_proven_orphan_with_dead_owner
# final: exit 0; 2 passed in 11.62s; outer 12.9719745s

.\.venv\Scripts\python.exe -m py_compile tests/test_live_job_object.py tests/test_live_state_ipc.py
# exit 0; 0.3004999s

git diff --check -- tests/test_live_job_object.py tests/test_live_state_ipc.py
# exit 0
```

## POST-CHANGE MCP AUDIT

DIRECT_EVIDENCE: Contextor `get_file_edit_context` after final edits resolved `tests.test_live_job_object` and `tests.test_live_state_ipc`, each at canonical revision 816, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified`, with no warnings. Module/graph/topology facts were fresh; `cycle_semantics` family was stale. This confirms source/workspace alignment of these test files, not active loaded-code adoption or LIVE runtime certification.

## FILES_CHANGED

`tests/test_live_job_object.py`; `tests/test_live_state_ipc.py`. `walkthrough.md` is the report and excluded from production/test changed-file inventory.

## FULL_DIFFS

DIRECT_EVIDENCE: Complete, unabridged `git -c core.safecrlf=false diff --no-color -- tests/test_live_job_object.py tests/test_live_state_ipc.py` follows:

```diff
diff --git a/tests/test_live_job_object.py b/tests/test_live_job_object.py
index 6c27601..6f8c7d6 100644
--- a/tests/test_live_job_object.py
+++ b/tests/test_live_job_object.py
@@ -8,6 +8,7 @@ import sys
 import threading
 import time
 from pathlib import Path
+from types import SimpleNamespace
 from unittest.mock import MagicMock
 
 import pytest
@@ -193,14 +194,17 @@ def test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch):
     # Create Windows Job Object with KILL_ON_JOB_CLOSE (0x2000) and BREAKAWAY_OK (0x0800)
     hJob = kernel32.CreateJobObjectW(None, None)
     assert hJob, f"Failed to create Job Object: {ctypes.GetLastError()}"
+    helper = None
+    live_client = None
+    ready_path = tmp_path / "live-helper-ready"
+    try:
+        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
+        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0800
+        res = kernel32.SetInformationJobObject(hJob, 9, ctypes.byref(info), ctypes.sizeof(info))
+        assert res != 0, f"Failed to set Job Object info: {ctypes.GetLastError()}"
 
-    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
-    info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0800
-    res = kernel32.SetInformationJobObject(hJob, 9, ctypes.byref(info), ctypes.sizeof(info))
-    assert res != 0, f"Failed to set Job Object info: {ctypes.GetLastError()}"
-
-    # Helper process assigned to that Job Object
-    helper_code = f"""
+        # Helper process assigned to that Job Object
+        helper_code = f"""
 import os, sys, time
 from pathlib import Path
 from contextor.core.live_state.runtime import connect_or_start
@@ -208,25 +212,28 @@ from contextor.core.live_state.runtime import connect_or_start
 os.environ["CONTEXTOR_CACHE_DIR"] = {repr(str(cache))}
 repo = Path({repr(str(repo))})
 client = connect_or_start(repo, owner_pid={keeper_pid}, owner_token={repr(keeper_token)})
-print("HELPER_DONE", client.service_pid, flush=True)
+Path({repr(str(ready_path))}).write_text(str(client.service_pid), encoding="ascii")
 time.sleep(60)
 """
 
-    helper = subprocess.Popen(
-        [sys.executable, "-c", helper_code],
-        stdout=subprocess.PIPE,
-        stderr=subprocess.PIPE,
-        text=True,
-    )
-    assigned = kernel32.AssignProcessToJobObject(hJob, int(helper._handle))
-    assert assigned != 0, f"Failed to assign helper to Job Object: {ctypes.GetLastError()}"
-
-    # Read output from helper confirming connect_or_start completed
-    line = helper.stdout.readline()
-    assert "HELPER_DONE" in line
+        helper = subprocess.Popen(
+            [sys.executable, "-c", helper_code],
+            stdout=subprocess.DEVNULL,
+            stderr=subprocess.DEVNULL,
+            text=True,
+        )
+        assigned = kernel32.AssignProcessToJobObject(hJob, int(helper._handle))
+        assert assigned != 0, f"Failed to assign helper to Job Object: {ctypes.GetLastError()}"
+
+        deadline = time.monotonic() + 15.0
+        while not ready_path.is_file():
+            if helper.poll() is not None:
+                pytest.fail("LIVE helper exited before readiness")
+            if time.monotonic() >= deadline:
+                pytest.fail("LIVE helper readiness timed out after 15 seconds")
+            time.sleep(0.05)
+        service_pid = int(ready_path.read_text(encoding="ascii"))
 
-    live_client = None
-    try:
         # Close the Job Object handle and terminate the helper process
         kernel32.CloseHandle(hJob)
         hJob = None
@@ -244,17 +251,111 @@ time.sleep(60)
         assert live_client is not None, "LIVE process died when helper Job Object closed!"
         status = live_client.ping()
         assert status.get("status") == "ok"
+        assert live_client.service_pid == service_pid
         assert live_client.owner_token == keeper_token
         assert live_client.owner_pid == keeper_pid
     finally:
-        if hJob is not None:
-            kernel32.CloseHandle(hJob)
-        if live_client is not None:
-            try:
-                live_client.request("shutdown")
-            except Exception:
-                pass
         try:
-            helper.kill()
-        except Exception:
-            pass
+            if hJob is not None:
+                kernel32.CloseHandle(hJob)
+        finally:
+            try:
+                if live_client is None:
+                    from contextor.core.live_state.runtime import connect
+
+                    try:
+                        live_client = connect(repo)
+                    except Exception:
+                        pass
+                if live_client is not None:
+                    try:
+                        live_client.request("shutdown", timeout=2.0)
+                    except Exception:
+                        pass
+            finally:
+                if helper is not None:
+                    try:
+                        if helper.poll() is None:
+                            helper.terminate()
+                    except Exception:
+                        pass
+                    try:
+                        helper.wait(timeout=5.0)
+                    except subprocess.TimeoutExpired:
+                        if helper.poll() is None:
+                            helper.kill()
+                        helper.wait(timeout=5.0)
+
+
+@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object cleanup regression")
+@pytest.mark.parametrize("failure", ["assignment", "readiness_timeout", "shutdown"])
+def test_windows_job_object_cleanup_regression(tmp_path, monkeypatch, failure):
+    import ctypes
+    import contextor.core.live_state.runtime as runtime
+
+    events = []
+
+    class Helper:
+        _handle = 123
+        alive = True
+
+        def poll(self):
+            return None if self.alive else 0
+
+        def terminate(self):
+            events.append("terminate")
+            self.alive = False
+
+        def wait(self, timeout):
+            events.append(("wait", timeout))
+            return 0
+
+        def kill(self):
+            events.append("kill")
+            self.alive = False
+
+    helper = Helper()
+    kernel32 = SimpleNamespace(
+        CreateJobObjectW=lambda *_: 77,
+        SetInformationJobObject=lambda *_: 1,
+        AssignProcessToJobObject=lambda *_: 0 if failure == "assignment" else 1,
+        CloseHandle=lambda handle: events.append(("close", handle)),
+    )
+    monkeypatch.setattr(ctypes.windll, "kernel32", kernel32)
+
+    def fake_popen(*_args, **_kwargs):
+        if failure == "shutdown":
+            (tmp_path / "live-helper-ready").write_text("456", encoding="ascii")
+        return helper
+
+    monkeypatch.setattr(subprocess, "Popen", fake_popen)
+    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
+
+    client = SimpleNamespace(
+        service_pid=456,
+        owner_token="job-keeper-token-123",
+        owner_pid=os.getpid(),
+        ping=lambda: {"status": "ok"},
+        request=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shutdown failed")),
+    )
+    monkeypatch.setattr(runtime, "connect", lambda root: client if failure == "shutdown" else None)
+
+    if failure == "readiness_timeout":
+        import itertools
+
+        ticks = itertools.count()
+        monkeypatch.setattr(time, "monotonic", lambda: next(ticks) * 20.0)
+
+    if failure == "assignment":
+        with pytest.raises(AssertionError, match="Failed to assign helper"):
+            test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)
+    elif failure == "readiness_timeout":
+        with pytest.raises(pytest.fail.Exception, match="readiness timed out"):
+            test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)
+    else:
+        test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)
+
+    assert ("close", 77) in events
+    assert "terminate" in events
+    assert ("wait", 5.0) in events or ("wait", 2) in events
+    assert helper.poll() is not None
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 89bf9e3..7f4b660 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -2618,13 +2618,14 @@ def test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monke
         stderr=subprocess.DEVNULL,
     )
     from contextor.core.live_state.runtime import connect
-    deadline = time.monotonic() + 5.0
-    while time.monotonic() < deadline:
-        if connect(repo):
-            break
-        time.sleep(0.05)
-    orphan_pid = proc.pid
+    client = None
     try:
+        deadline = time.monotonic() + 5.0
+        while time.monotonic() < deadline:
+            if connect(repo):
+                break
+            time.sleep(0.05)
+        orphan_pid = proc.pid
         # connect_or_start detects owner 99999999 is dead -> stops orphan and spawns fresh owned runtime
         client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="orphan-replacer")
         assert client.is_owner is False
@@ -2632,11 +2633,79 @@ def test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monke
         assert client.owner_pid == os.getpid()
         assert client.service_pid != orphan_pid
     finally:
-        client.request("shutdown")
+        body_failed = sys.exc_info()[0] is not None
         try:
-            proc.kill()
-        except OSError:
-            pass
+            if client is None:
+                try:
+                    client = connect(repo)
+                except Exception:
+                    pass
+            if client is not None:
+                try:
+                    client.request("shutdown", timeout=2.0)
+                except Exception:
+                    pass
+        finally:
+            if proc.poll() is None:
+                try:
+                    proc.kill()
+                except OSError:
+                    pass
+            try:
+                proc.wait(timeout=5.0)
+            except subprocess.TimeoutExpired:
+                if not body_failed:
+                    raise
+
+
+@pytest.mark.parametrize("failure", ["before_assignment", "shutdown"])
+def test_orphan_replacement_cleanup_regression(tmp_path, monkeypatch, failure):
+    import contextor.core.live_state.runtime as runtime
+
+    events = []
+
+    class Process:
+        pid = 123456
+        alive = True
+
+        def poll(self):
+            return None if self.alive else 0
+
+        def kill(self):
+            events.append("kill")
+            self.alive = False
+
+        def wait(self, timeout):
+            events.append(("wait", timeout))
+            return 0
+
+    process = Process()
+    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
+
+    if failure == "before_assignment":
+        def failed_connect(_root):
+            raise RuntimeError("probe failed")
+
+        monkeypatch.setattr(runtime, "connect", failed_connect)
+        with pytest.raises(RuntimeError, match="probe failed"):
+            test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monkeypatch)
+    else:
+        client = SimpleNamespace(
+            is_owner=False,
+            owner_token="unexpected-token",
+            owner_pid=os.getpid(),
+            service_pid=654321,
+            request=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shutdown failed")),
+        )
+        monkeypatch.setattr(runtime, "connect", lambda _root: client)
+        monkeypatch.setattr(
+            sys.modules[__name__], "connect_or_start", lambda *_args, **_kwargs: client,
+        )
+        with pytest.raises(AssertionError):
+            test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monkeypatch)
+
+    assert events == ["kill", ("wait", 5.0)]
+    assert process.poll() is not None
 
 
 def test_connect_or_start_rejects_legacy_endpoint_without_owner_pid(tmp_path, monkeypatch):
```

## CONTRACT_CONFLICTS

DIRECT_EVIDENCE: None encountered for the two specified test fixes. No production or shared API changes.

## REMAINING UNKNOWN

UNKNOWN: Global pytest safety and results; all other S1-unverified test modules; exact identity of any process that may not expose the queried command-line pattern; behavior if OS process termination/reaping itself fails or hangs beyond the finite timeout; active Desktop/MCP/LIVE code adoption. Focused test success is not architectural GO.

## FINAL IMPLEMENTER OBSERVATION

DIRECT_EVIDENCE: Both bounded test lifecycle defects were corrected and focused/real Windows checks passed. Stop after S2; architectural acceptance remains with ChatGPT.

