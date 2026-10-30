# PY315-R4C-2 — registered process cleanup resolution

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `54d71a56354b19f8ebd00a27cfc0e285a61ab31c`; pre-edit Git status was clean. Contextor MCP returned revision 926, provenance live, and `workspace_sync=verified` for `contextor.mcp_process_registry` and `contextor.mcp_backend_control`. All six literal SEARCH blocks occurred exactly once; the new test file was absent.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: All six architect-supplied replacements were applied at the exact anchors using `apply_patch`. The new test file matches the supplied content aside from final newline formatting. `mcp_server.py`, the legacy `/T` test, and launcher code were not changed.

## ALREADY_DEAD_HANDLING
CODE_PATH_PROVED: On Windows, `terminate_or_confirm_registered_process` returns true for a classifier result of DEAD without calling termination. The deterministic test covers this branch. This is a point-in-time cleanup resolution, not proof of full descendant-tree parity.

## PID_REUSE_HANDLING
CODE_PATH PROVED: For IDENTITY_MISMATCH, `_registered_windows_identity_gone` re-probes and accepts only a live process with a different positive creation identity. A same-creation image mismatch remains unresolved. Tests cover both cases and a race where the PID changes after failed identity-bound termination.

## UNKNOWN_FAIL_CLOSED
UNKNOWN or invalid classification returns false without termination. An unconfirmed re-probe after failed termination also returns false. The new tests cover these branches. A false result retains registry evidence in the updated backend child path.

## BACKEND_CHILD_CLEANUP
`_cleanup_owned_registry_children` now uses the central terminate-or-confirm helper. It removes a child record only after confirmed termination, confirmed prior death, or creation-time proof that the prior identity no longer owns its PID. Failed resolution raises `BackendControlError` and keeps the child record. The backend's independent `stop_backend` termination mock was preserved.

## TARGETED_TEST_RESULTS
`py_compile` for the five changed/new Python files: PASS.
`tests/test_mcp_registered_process_cleanup.py tests/test_mcp_registered_process_classification.py tests/test_mcp_process_registry.py tests/test_mcp_process_registry_identity_termination.py tests/test_mcp_backend_control.py tests/test_mcp_child_cleanup_failure_evidence.py -q`: 114 passed, 1 AuthlibDeprecationWarning.
`tests/test_mcp_backend_job_guard.py tests/test_mcp_backend_job_process_scope.py -q`: 18 passed, 1 AuthlibDeprecationWarning.
No full pytest or real process termination.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Initial post-edit reads at revision 926 reported `workspace_sync=out_of_sync` for both changed production modules, and symbol fetches returned `status=stale_source`. Intermediate reads at revisions 926–930 were `unverified` for at least one target with a generation-proof warning. Later `get_symbol_implementation` reads at revision 931 returned `status=resolved`, `workspace_sync=verified`, and complete implementations for `terminate_or_confirm_registered_process` and `_cleanup_owned_registry_children`. Canonical source synchronization and changed symbol visibility are verified for both modules at revision 931. No manual `update_file` or restart occurred. Active backend loaded-code adoption is UNKNOWN.

## FILES_CHANGED
- `contextor/mcp_process_registry.py`
- `contextor/mcp_backend_control.py`
- `tests/test_mcp_backend_control.py`
- `tests/test_mcp_child_cleanup_failure_evidence.py`
- `tests/test_mcp_registered_process_cleanup.py`

## FULL_DIFFS
```diff
diff --git a/contextor/mcp_backend_control.py b/contextor/mcp_backend_control.py
index 7c26b42..f83a8f5 100644
--- a/contextor/mcp_backend_control.py
+++ b/contextor/mcp_backend_control.py
@@ -37,10 +37,10 @@ from contextor.mcp_process_registry import (
     read_records,
     record_matches_process,
     remove_record,
+    terminate_or_confirm_registered_process,
     terminate_registered_process,
 )
 
-
 BACKEND_HOST = "127.0.0.1"
 BACKEND_PORT = 8765
 BACKEND_MCP_PATH = "/mcp"
@@ -960,15 +960,14 @@ def _cleanup_owned_registry_children(
             ):
                 continue
 
-        if not terminate_registered_process(
+        if not terminate_or_confirm_registered_process(
             child
         ):
             raise BackendControlError(
-                "registered backend child termination "
+                "registered backend child cleanup "
                 "was not confirmed; "
                 f"pid={child.get('pid')!r}"
             )
-
         remove_record(
             record_path
         )
diff --git a/contextor/mcp_process_registry.py b/contextor/mcp_process_registry.py
index 4a63ec2..149692a 100644
--- a/contextor/mcp_process_registry.py
+++ b/contextor/mcp_process_registry.py
@@ -379,6 +379,77 @@ def classify_registered_windows_process(
     return "ALIVE_MATCH"
 
 
+def _registered_windows_identity_gone(
+    record: dict[str, Any],
+) -> bool:
+    """Confirm that the recorded process no longer owns its PID.
+
+    A different creation time proves the recorded process
+    has exited. An image mismatch with the same creation
+    time is not sufficient to discard ownership evidence.
+    """
+    state = classify_registered_windows_process(record)
+
+    if state == "DEAD":
+        return True
+
+    if state != "IDENTITY_MISMATCH":
+        return False
+
+    try:
+        probe = probe_process_identity(record["pid"])
+    except (OSError, AttributeError, TypeError, ValueError):
+        return False
+
+    expected_creation = record.get("creation_time")
+
+    return (
+        probe.state == "alive"
+        and type(expected_creation) is int
+        and expected_creation > 0
+        and type(probe.creation_time) is int
+        and probe.creation_time > 0
+        and probe.creation_time != expected_creation
+    )
+
+
+def terminate_or_confirm_registered_process(
+    record: dict[str, Any],
+) -> bool:
+    """Terminate the recorded process or prove its absence.
+
+    True means that the registered identity was confirmed
+    terminated, already dead, or replaced at its former PID.
+
+    False means cleanup remains unresolved. No registry
+    record should be removed on False.
+
+    The strict Windows termination primitive independently
+    verifies identity on one process handle.
+    """
+    if not sys_platform_is_windows():
+        return terminate_registered_process(record)
+
+    state = classify_registered_windows_process(record)
+
+    if state == "DEAD":
+        return True
+
+    if state == "IDENTITY_MISMATCH":
+        return _registered_windows_identity_gone(record)
+
+    if state != "ALIVE_MATCH":
+        return False
+
+    if terminate_registered_process(record):
+        return True
+
+    # The process may have exited between classification
+    # and the identity-bound termination attempt.
+    # Never retry against an unverified PID.
+    return _registered_windows_identity_gone(record)
+
+
 def _terminate_windows_record_identity_bound(
     record: dict[str, Any],
 ) -> bool:
diff --git a/tests/test_mcp_backend_control.py b/tests/test_mcp_backend_control.py
index 78a7568..149c7dc 100644
--- a/tests/test_mcp_backend_control.py
+++ b/tests/test_mcp_backend_control.py
@@ -617,11 +617,10 @@ def test_owned_registry_child_cleanup_is_parent_identity_scoped(
     )
     monkeypatch.setattr(
         control,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda child: terminated.append(child) or True,
     )
     monkeypatch.setattr(control, "remove_record", lambda path: removed.append(path))
-
     control._cleanup_owned_registry_children(backend_record)
 
     assert terminated == [good]
diff --git a/tests/test_mcp_child_cleanup_failure_evidence.py b/tests/test_mcp_child_cleanup_failure_evidence.py
index a83ef83..ef636fa 100644
--- a/tests/test_mcp_child_cleanup_failure_evidence.py
+++ b/tests/test_mcp_child_cleanup_failure_evidence.py
@@ -43,7 +43,7 @@ def test_backend_failed_child_termination_retains_record(
     )
     monkeypatch.setattr(
         control,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: False,
     )
     monkeypatch.setattr(
@@ -77,7 +77,7 @@ def test_backend_successful_child_termination_removes_record(
     )
     monkeypatch.setattr(
         control,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: True,
     )
     monkeypatch.setattr(
diff --git a/tests/test_mcp_registered_process_cleanup.py b/tests/test_mcp_registered_process_cleanup.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_registered_process_cleanup.py
@@ -0,0 +1,314 @@
+from __future__ import annotations
+
+import pytest
+
+from contextor import mcp_process_registry as registry
+
+
+RECORD = {
+    "pid": 2500,
+    "creation_time": 123456789,
+    "executable": r"C:\Contextor\.venv\Scripts\python.exe",
+}
+
+
+@pytest.fixture
+def windows_cleanup(monkeypatch):
+    monkeypatch.setattr(
+        registry,
+        "sys_platform_is_windows",
+        lambda: True,
+    )
+
+
+def test_already_dead_requires_no_termination(
+    windows_cleanup,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "DEAD",
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: pytest.fail(
+            "dead process was terminated"
+        ),
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_live_matching_process_is_terminated(
+    windows_cleanup,
+    monkeypatch,
+):
+    calls = []
+
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "ALIVE_MATCH",
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: calls.append(record) or True,
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+    assert calls == [RECORD]
+
+
+def test_unknown_never_terminates(
+    windows_cleanup,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "UNKNOWN",
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: pytest.fail(
+            "unknown identity was terminated"
+        ),
+    )
+
+    assert not registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_live_process_exits_before_termination(
+    windows_cleanup,
+    monkeypatch,
+):
+    states = iter([
+        "ALIVE_MATCH",
+        "DEAD",
+    ])
+
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: next(states),
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_pid_reuse_clears_old_identity_without_killing_new(
+    windows_cleanup,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "IDENTITY_MISMATCH",
+    )
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda pid: registry.ProcessIdentityProbe(
+            "alive",
+            r"C:\Other\python.exe",
+            123456790,
+        ),
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: pytest.fail(
+            "replacement PID was targeted"
+        ),
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_same_creation_different_image_is_unresolved(
+    windows_cleanup,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "IDENTITY_MISMATCH",
+    )
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda pid: registry.ProcessIdentityProbe(
+            "alive",
+            r"C:\Other\python.exe",
+            RECORD["creation_time"],
+        ),
+    )
+
+    assert not registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_failed_termination_with_unknown_reprobe_is_unresolved(
+    windows_cleanup,
+    monkeypatch,
+):
+    states = iter([
+        "ALIVE_MATCH",
+        "UNKNOWN",
+    ])
+
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: next(states),
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+
+    assert not registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_failed_termination_with_reused_pid_is_safe(
+    windows_cleanup,
+    monkeypatch,
+):
+    states = iter([
+        "ALIVE_MATCH",
+        "IDENTITY_MISMATCH",
+    ])
+
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: next(states),
+    )
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda pid: registry.ProcessIdentityProbe(
+            "alive",
+            r"C:\Other\python.exe",
+            123456791,
+        ),
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_pid_reuse_without_creation_evidence_is_unresolved(
+    windows_cleanup,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "classify_registered_windows_process",
+        lambda record: "IDENTITY_MISMATCH",
+    )
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda pid: registry.ProcessIdentityProbe(
+            "alive",
+            r"C:\Other\python.exe",
+            None,
+        ),
+    )
+
+    assert not registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+
+
+def test_nonwindows_preserves_existing_termination(
+    monkeypatch,
+):
+    calls = []
+
+    monkeypatch.setattr(
+        registry,
+        "sys_platform_is_windows",
+        lambda: False,
+    )
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda record: calls.append(record) or True,
+    )
+
+    assert registry.terminate_or_confirm_registered_process(
+        RECORD
+    )
+    assert calls == [RECORD]
+
+
+def test_backend_cleanup_confirms_dead_child_without_termination(
+    monkeypatch,
+    tmp_path,
+):
+    import contextor.mcp_backend_control as control
+
+    child = {
+        **RECORD,
+        "parent_pid": 500,
+        "parent_creation_time": 123456788,
+    }
+    path = tmp_path / "child.json"
+
+    class Owner:
+        pid = 500
+        creation_time = 123456788
+        process_registry = str(tmp_path)
+
+    removed = []
+
+    monkeypatch.setattr(
+        control,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_or_confirm_registered_process",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_record",
+        lambda target: removed.append(target),
+    )
+
+    control._cleanup_owned_registry_children(Owner())
+
+    assert removed == [path]
```

## REMAINING_UNKNOWN
Active runtime adoption; real Windows process behavior; MCP server cleanup callers, which are pending; legacy `/T` tree parity. The dual launchers were not resumed.

## FINAL_VERDICT
PASS_BACKEND_CHILD_RESOLUTION_MCP_CLEANUP_PENDING for the exact source and targeted test contract; MCP canonical source visibility is verified, while runtime adoption remains unverified.
