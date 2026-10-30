# PY315-R4A — child cleanup failure evidence

## PREFLIGHT
DIRECT_EVIDENCE: Contextor MCP module contexts for the four edited Python modules reported canonical revision 911, provenance live, and workspace_sync verified before edits. Exact SEARCH blocks 1–5 each occurred exactly once in their specified files; the new test file was absent. Existing R3 modifications to `contextor/mcp_process_registry.py` and its new test were preserved. No commit or runtime restart occurred.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: All five specified replacements were applied literally once. `tests/test_mcp_child_cleanup_failure_evidence.py` was created from the supplied exact content. No other source or test file was changed in this task.

## PROCESS_REGISTRY_EVIDENCE_RETENTION
CODE_PATH_PROVED: Backend child, MCP orphan, and MCP owned-child cleanup now raise when `terminate_registered_process()` returns false and remove the registry record only after true. Backend stop cannot report success when `_cleanup_owned_registry_children` raises. Profile worker `finally` removes its record only when `process.returncode` is known; Git cleanup removes only when `record_path` exists and `process.poll()` is non-None. These changes preserve evidence for the specified failed termination paths. They do not establish descendant-tree termination.

## TARGETED_TEST_RESULTS
`py_compile` for the four edited production modules and new test file: PASS.
Specified focused suite: `76 passed, 1 AuthlibDeprecationWarning in 7.20s`.
Separate legacy gate: `tests/test_mcp_child_process_cleanup.py::test_windows_registered_process_termination_uses_tree_kill` FAILED at line 38 with `AttributeError: module 'contextor.mcp_process_registry' has no attribute 'subprocess'`. The test stopped before any process API call. It was not modified. No full pytest or actual process termination occurred.

## REMAINING_CHILD_TREE_REGRESSION
OPEN REGRESSION GATE: R3 removed the Windows `taskkill /F /T /PID` path. The current identity-bound helper terminates one process handle; it does not implement `/T` child-tree semantics. R4A does not restore tree-level termination or certify descendant cleanup.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Initial post-edit module reads at revision 912 were mixed (`verified`, `out_of_sync`, and `unverified`). Subsequent Contextor MCP module contexts for all four edited modules reported revision 916, provenance live, canonical_state fresh, and workspace_sync verified. This supports current canonical source synchronization only. The attempted batched `get_symbol_implementation` audit returned a tool error for at least one call and was not treated as implementation visibility evidence. No manual `update_file`, backend restart, or loaded-code verification occurred; active LIVE code-byte adoption remains UNKNOWN.

## FILES_CHANGED
- `contextor/mcp_backend_control.py`
- `contextor/mcp_server.py`
- `contextor/mcp/tools/contextor_profile_analysis.py`
- `contextor/core/analysis/git_context.py`
- `tests/test_mcp_child_cleanup_failure_evidence.py`

## FULL_DIFFS
### contextor/mcp_backend_control.py
```diff
--- a/contextor/mcp_backend_control.py
+++ b/contextor/mcp_backend_control.py
@@ -960,9 +960,14 @@
             ):
                 continue
 
-        terminate_registered_process(
+        if not terminate_registered_process(
             child
-        )
+        ):
+            raise BackendControlError(
+                "registered backend child termination "
+                "was not confirmed; "
+                f"pid={child.get('pid')!r}"
+            )
 
         remove_record(
             record_path
```

### contextor/mcp_server.py
```diff
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -606,7 +606,13 @@
             if expected_parent_creation is not None and parent_creation_time is not None:
                 parent_alive = int(expected_parent_creation) == parent_creation_time
             if not parent_alive:
-                stopped_process = terminate_registered_process(record) or stopped_process
+                if not terminate_registered_process(record):
+                    raise RuntimeError(
+                        "registered orphan process termination "
+                        "was not confirmed; "
+                        f"pid={record.get('pid')!r}"
+                    )
+                stopped_process = True
                 remove_record(record_path)
         if not stopped_process:
             break
@@ -620,7 +626,12 @@
         except (TypeError, ValueError):
             is_child = False
         if is_child:
-            terminate_registered_process(record)
+            if not terminate_registered_process(record):
+                raise RuntimeError(
+                    "registered MCP child termination "
+                    "was not confirmed; "
+                    f"pid={record.get('pid')!r}"
+                )
             remove_record(record_path)
 
 
```

### contextor/mcp/tools/contextor_profile_analysis.py
```diff
--- a/contextor/mcp/tools/contextor_profile_analysis.py
+++ b/contextor/mcp/tools/contextor_profile_analysis.py
@@ -142,7 +142,8 @@
         )
         raise
     finally:
-        remove_record(record_path)
+        if process.returncode is not None:
+            remove_record(record_path)
 
     if process.returncode != 0:
         error = stderr.decode(
```

### contextor/core/analysis/git_context.py
```diff
--- a/contextor/core/analysis/git_context.py
+++ b/contextor/core/analysis/git_context.py
@@ -58,7 +58,8 @@
     except Exception:
         return None
     finally:
-        remove_record(record_path)
+        if record_path is not None and process.poll() is not None:
+            remove_record(record_path)
 
 
 def collect_git_context(file_path: str, root_path: str) -> dict:
```

### tests/test_mcp_child_cleanup_failure_evidence.py
```diff
--- /dev/null
+++ b/tests/test_mcp_child_cleanup_failure_evidence.py
@@ -0,0 +1,255 @@
+from __future__ import annotations
+
+from contextlib import nullcontext
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import contextor.mcp_backend_control as control
+import contextor.mcp_server as server
+
+
+def _owner(tmp_path):
+    return SimpleNamespace(
+        pid=500,
+        creation_time=123456789,
+        process_registry=str(tmp_path),
+    )
+
+
+def _child():
+    return {
+        "pid": 501,
+        "parent_pid": 500,
+        "parent_creation_time": 123456789,
+        "executable": r"C:\Python\python.exe",
+        "creation_time": 123456790,
+    }
+
+
+def test_backend_failed_child_termination_retains_record(
+    tmp_path,
+    monkeypatch,
+):
+    owner = _owner(tmp_path)
+    path = tmp_path / "child.json"
+    child = _child()
+
+    monkeypatch.setattr(
+        control,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_record",
+        lambda path: pytest.fail(
+            "failed child termination erased evidence"
+        ),
+    )
+
+    with pytest.raises(
+        control.BackendControlError,
+        match="not confirmed",
+    ):
+        control._cleanup_owned_registry_children(owner)
+
+
+def test_backend_successful_child_termination_removes_record(
+    tmp_path,
+    monkeypatch,
+):
+    owner = _owner(tmp_path)
+    path = tmp_path / "child.json"
+    child = _child()
+    removed = []
+
+    monkeypatch.setattr(
+        control,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_record",
+        lambda target: removed.append(target),
+    )
+
+    control._cleanup_owned_registry_children(owner)
+
+    assert removed == [path]
+
+
+def test_mcp_server_failed_owned_child_retains_record(
+    tmp_path,
+    monkeypatch,
+):
+    path = tmp_path / "child.json"
+    child = _child()
+
+    monkeypatch.setattr(
+        server,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        server,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+    monkeypatch.setattr(
+        server,
+        "remove_record",
+        lambda target: pytest.fail(
+            "failed owned-child termination erased evidence"
+        ),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="not confirmed",
+    ):
+        server._cleanup_owned_processes(tmp_path, 500)
+
+
+def test_mcp_server_successful_owned_child_cleanup(
+    tmp_path,
+    monkeypatch,
+):
+    path = tmp_path / "child.json"
+    child = _child()
+    removed = []
+
+    monkeypatch.setattr(
+        server,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        server,
+        "terminate_registered_process",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        server,
+        "remove_record",
+        lambda target: removed.append(target),
+    )
+
+    server._cleanup_owned_processes(tmp_path, 500)
+
+    assert removed == [path]
+
+
+def test_mcp_server_failed_orphan_cleanup_retains_record(
+    tmp_path,
+    monkeypatch,
+):
+    path = tmp_path / "orphan.json"
+    child = _child()
+
+    monkeypatch.setattr(
+        server,
+        "read_records",
+        lambda directory: [(path, child)],
+    )
+    monkeypatch.setattr(
+        server,
+        "record_matches_process",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        server,
+        "process_identity",
+        lambda pid: (None, None, False),
+    )
+    monkeypatch.setattr(
+        server,
+        "terminate_registered_process",
+        lambda record: False,
+    )
+    monkeypatch.setattr(
+        server,
+        "remove_record",
+        lambda target: pytest.fail(
+            "failed orphan termination erased evidence"
+        ),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="not confirmed",
+    ):
+        server._cleanup_orphaned_processes(tmp_path)
+
+
+def test_failed_child_cleanup_blocks_backend_stop_success(
+    tmp_path,
+    monkeypatch,
+):
+    owner = _owner(tmp_path)
+    owner.to_dict = lambda: {
+        "pid": owner.pid,
+        "executable": r"C:\Python\python.exe",
+        "creation_time": owner.creation_time,
+    }
+
+    monkeypatch.setattr(
+        control,
+        "_BackendControlLock",
+        lambda *args, **kwargs: nullcontext(),
+    )
+    monkeypatch.setattr(
+        control,
+        "read_backend_record",
+        lambda: owner,
+    )
+    monkeypatch.setattr(
+        control,
+        "_backend_owner_identity_matches",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        control,
+        "terminate_registered_process",
+        lambda record: True,
+    )
+    monkeypatch.setattr(
+        control,
+        "_wait_for_owner_exit",
+        lambda record, *, timeout: True,
+    )
+    monkeypatch.setattr(
+        control,
+        "_cleanup_owned_registry_children",
+        lambda record: (_ for _ in ()).throw(
+            control.BackendControlError(
+                "child termination was not confirmed"
+            )
+        ),
+    )
+    monkeypatch.setattr(
+        control,
+        "remove_backend_record_if_exact",
+        lambda record: pytest.fail(
+            "backend stop discarded unresolved child evidence"
+        ),
+    )
+
+    with pytest.raises(
+        control.BackendControlError,
+        match="not confirmed",
+    ):
+        control.stop_backend()
+
```

## REMAINING_UNKNOWN
Actual child/grandchild survival and loaded-code adoption; tree-level parity; whether additional cleanup paths outside this literal R4A scope discard failed termination evidence. These were not certified or changed.

## FINAL_VERDICT
PARTIAL_FIX_TREE_REGRESSION_OPEN. R4A exact patch and focused tests passed, while the mandatory legacy tree-kill regression remains open.
