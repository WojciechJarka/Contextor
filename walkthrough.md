# PY315-R4B-FIX — process-local Job ownership

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `5ce14c50770957fd32c401765728c44c650e2748`; pre-edit Git status was clean. Contextor MCP returned revision 920, provenance live, `workspace_sync=verified` for `contextor.mcp_backend_job` and `contextor.core.live_state.runtime`. Exact SEARCH occurrence counts were 1, 1, 1, 2, 1, 3 for edits 1–6; the new test file was absent.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: All six replacements were applied at the specified counts with `apply_patch`. The new test file matches the architect's supplied content aside from final newline formatting. No other source/test changes were made.

## PROCESS_LOCAL_JOB_AUTHORITY
CODE_PATH_PROVED: The successful Job installation no longer sets an inheritable environment marker. `backend_job_active_for_current_process()` returns true only with an active handle owned by the current Windows PID, returns false for an unset guard, and raises for inconsistent or foreign process state.

## LIVE_BREAKAWAY_BEHAVIOR
CODE_PATH_PROVED: Windows LIVE spawn consults process-local Job ownership before spawning. A true guard requires membership verification and refuses the legacy access-denied fallback; an inherited environment marker alone cannot activate those restrictions. The supplied fake-process tests exercise both paths. No real Windows process was started or terminated.

## REGRESSION_RESULTS
`py_compile` of the four changed/new Python files: PASS.
`tests/test_mcp_backend_job_guard.py tests/test_mcp_backend_job_process_scope.py -q`: 18 passed, 1 warning.
`tests/test_live_job_object.py -q -k "not real_windows_job_object_breakaway_integration and not windows_job_object_cleanup_regression"`: 6 passed, 4 deselected.
`tests/test_mcp_shared_backend_server_mode.py tests/test_mcp_backend_control.py -q`: 34 passed, 1 warning.
The legacy tree-kill regression gate remains open; it was not modified or rerun in this task.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Initial post-edit Contextor MCP reads for both changed production modules at revisions 920–921 reported `workspace_sync=out_of_sync`. A later read for `contextor.mcp_backend_job` at revision 921 reported `workspace_sync=verified`. The corresponding read for `contextor.core.live_state.runtime` at revision 921 remained `out_of_sync`, with the advisory that disk content changed since the canonical revision. Source synchronization is verified for the Job module and unverified for the LIVE runtime module. No `update_file` or restart was performed. Active backend loaded-code adoption is UNKNOWN.

## FILES_CHANGED
- `contextor/mcp_backend_job.py`
- `contextor/core/live_state/runtime.py`
- `tests/test_mcp_backend_job_guard.py`
- `tests/test_mcp_backend_job_process_scope.py`

## FULL_DIFFS
```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 5053056..64a4ff6 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -786,6 +786,12 @@ def _spawn_runtime_subprocess(
             creationflags=0,
         )
 
+    from contextor.mcp_backend_job import (
+        backend_job_active_for_current_process,
+    )
+
+    backend_job_guarded = backend_job_active_for_current_process()
+
     base_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
     primary_flags = base_flags | CREATE_BREAKAWAY_FROM_JOB
 
@@ -800,7 +806,7 @@ def _spawn_runtime_subprocess(
             creationflags=primary_flags,
         )
 
-        if os.environ.get("CONTEXTOR_BACKEND_JOB_GUARD") == "1":
+        if backend_job_guarded:
             from contextor.mcp_backend_job import (
                 require_live_outside_backend_job,
             )
@@ -825,7 +831,7 @@ def _spawn_runtime_subprocess(
         if getattr(exc, "winerror", None) != 5:
             raise
 
-        if os.environ.get("CONTEXTOR_BACKEND_JOB_GUARD") == "1":
+        if backend_job_guarded:
             raise RuntimeError(
                 "LIVE breakaway failed while persistent "
                 "backend Job Object protection is active"
diff --git a/contextor/mcp_backend_job.py b/contextor/mcp_backend_job.py
index 0d314da..ee78b31 100644
--- a/contextor/mcp_backend_job.py
+++ b/contextor/mcp_backend_job.py
@@ -167,8 +167,28 @@ def protect_persistent_backend() -> None:
     _active_handle = handle
     _active_pid = current_pid
 
-    # This marker is set ONLY after successful installation.
-    os.environ["CONTEXTOR_BACKEND_JOB_GUARD"] = "1"
+    # Environment variables can be inherited by unrelated children.
+    # Ownership authority remains exclusively in this process.
+
+
+def backend_job_active_for_current_process() -> bool:
+    """Return true only for the process holding the backend Job."""
+    if sys.platform != "win32":
+        return False
+
+    if _active_handle is None:
+        if _active_pid is not None:
+            raise BackendJobError(
+                "backend Job Object ownership state is inconsistent"
+            )
+        return False
+
+    if _active_pid != os.getpid():
+        raise BackendJobError(
+            "backend Job Object belongs to a different process"
+        )
+
+    return True
 
 
 def require_live_outside_backend_job(
@@ -221,6 +241,7 @@ def require_live_outside_backend_job(
 
 __all__ = [
     "BackendJobError",
+    "backend_job_active_for_current_process",
     "protect_persistent_backend",
     "require_live_outside_backend_job",
 ]
diff --git a/tests/test_mcp_backend_job_guard.py b/tests/test_mcp_backend_job_guard.py
index eeae701..7fc35f9 100644
--- a/tests/test_mcp_backend_job_guard.py
+++ b/tests/test_mcp_backend_job_guard.py
@@ -121,7 +121,8 @@ def test_backend_job_owns_descendant_lifetime(
     assert fake_job.CloseHandle.calls == []
     assert guard._active_handle == 71
     assert guard._active_pid == os.getpid()
-    assert os.environ["CONTEXTOR_BACKEND_JOB_GUARD"] == "1"
+    assert guard.backend_job_active_for_current_process()
+    assert "CONTEXTOR_BACKEND_JOB_GUARD" not in os.environ
 
 
 def test_guard_install_is_idempotent(fake_job):
@@ -324,9 +325,10 @@ def test_guarded_live_refuses_breakaway_fallback(
         "platform",
         "win32",
     )
-    monkeypatch.setenv(
-        "CONTEXTOR_BACKEND_JOB_GUARD",
-        "1",
+    monkeypatch.setattr(
+        guard,
+        "backend_job_active_for_current_process",
+        lambda: True,
     )
     monkeypatch.setattr(
         live_runtime.subprocess,
@@ -358,9 +360,10 @@ def test_guarded_live_verifies_spawn_before_return(
         "platform",
         "win32",
     )
-    monkeypatch.setenv(
-        "CONTEXTOR_BACKEND_JOB_GUARD",
-        "1",
+    monkeypatch.setattr(
+        guard,
+        "backend_job_active_for_current_process",
+        lambda: True,
     )
     monkeypatch.setattr(
         live_runtime.subprocess,
@@ -405,9 +408,10 @@ def test_guarded_live_rejects_membership_and_terminates(
         "platform",
         "win32",
     )
-    monkeypatch.setenv(
-        "CONTEXTOR_BACKEND_JOB_GUARD",
-        "1",
+    monkeypatch.setattr(
+        guard,
+        "backend_job_active_for_current_process",
+        lambda: True,
     )
     monkeypatch.setattr(
         live_runtime.subprocess,
diff --git a/tests/test_mcp_backend_job_process_scope.py b/tests/test_mcp_backend_job_process_scope.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_backend_job_process_scope.py
@@ -0,0 +1,168 @@
+from __future__ import annotations
+
+import os
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.mcp_backend_job as guard
+import contextor.core.live_state.runtime as runtime
+
+
+def test_inherited_environment_cannot_fake_job_guard(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(guard, "_active_handle", None)
+    monkeypatch.setattr(guard, "_active_pid", None)
+    monkeypatch.setenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        "1",
+    )
+
+    process = SimpleNamespace(_handle=42)
+
+    monkeypatch.setattr(
+        runtime.subprocess,
+        "Popen",
+        lambda *_args, **_kwargs: process,
+    )
+    monkeypatch.setattr(
+        guard,
+        "require_live_outside_backend_job",
+        lambda *_args: pytest.fail(
+            "inherited environment marker was trusted"
+        ),
+    )
+
+    result = runtime._spawn_runtime_subprocess(
+        ["python.exe"],
+        Path("."),
+        {},
+    )
+
+    assert result is process
+    assert not guard.backend_job_active_for_current_process()
+
+
+def test_stale_process_local_guard_refuses_spawn(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(guard, "_active_handle", 77)
+    monkeypatch.setattr(
+        guard,
+        "_active_pid",
+        os.getpid() + 1,
+    )
+
+    monkeypatch.setattr(
+        runtime.subprocess,
+        "Popen",
+        lambda *_args, **_kwargs: pytest.fail(
+            "spawn occurred with stale Job owner"
+        ),
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="different process",
+    ):
+        runtime._spawn_runtime_subprocess(
+            ["python.exe"],
+            Path("."),
+            {},
+        )
+
+
+def test_inconsistent_guard_state_is_rejected(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        guard.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(guard, "_active_handle", None)
+    monkeypatch.setattr(
+        guard,
+        "_active_pid",
+        os.getpid(),
+    )
+
+    with pytest.raises(
+        guard.BackendJobError,
+        match="inconsistent",
+    ):
+        guard.backend_job_active_for_current_process()
+
+
+def test_untrusted_marker_does_not_disable_legacy_fallback(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        runtime.sys,
+        "platform",
+        "win32",
+    )
+    monkeypatch.setattr(guard, "_active_handle", None)
+    monkeypatch.setattr(guard, "_active_pid", None)
+    monkeypatch.setenv(
+        "CONTEXTOR_BACKEND_JOB_GUARD",
+        "1",
+    )
+
+    calls = []
+    process = SimpleNamespace(_handle=92)
+
+    def fake_spawn(*_args, **kwargs):
+        calls.append(kwargs["creationflags"])
+        if len(calls) == 1:
+            error = PermissionError(
+                "Access denied"
+            )
+            error.winerror = 5
+            raise error
+        return process
+
+    monkeypatch.setattr(
+        runtime.subprocess,
+        "Popen",
+        fake_spawn,
+    )
+
+    result = runtime._spawn_runtime_subprocess(
+        ["python.exe"],
+        Path("."),
+        {},
+    )
+
+    assert result is process
+    assert len(calls) == 2
+    assert calls[0] & runtime.CREATE_BREAKAWAY_FROM_JOB
+    assert not (
+        calls[1] & runtime.CREATE_BREAKAWAY_FROM_JOB
+    )
+
+
+def test_non_windows_guard_is_inactive(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        guard.sys,
+        "platform",
+        "linux",
+    )
+    monkeypatch.setattr(guard, "_active_handle", None)
+    monkeypatch.setattr(guard, "_active_pid", None)
+
+    assert not guard.backend_job_active_for_current_process()
```

## REMAINING_UNKNOWN
Canonical synchronization of `contextor.core.live_state.runtime`; real Windows Job Object integration; active backend adoption; full descendant-tree parity. The legacy tree-kill regression remains open. Dual-launcher work and process cleanup classification were not resumed.

## FINAL_VERDICT
PASS_PROCESS_SCOPE_FIX_TREE_GATE_OPEN for the exact source and targeted test contract; canonical synchronization and runtime adoption remain unverified.
