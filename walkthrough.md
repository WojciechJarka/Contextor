# PY315-R4C-3-R1 — Windows parent identity and multilevel registered cleanup

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `113040a0351ef541de69785465b37253a0a4d66f`; only the prior `walkthrough.md` report was modified before this task. Contextor MCP reported revision 931, provenance live, and `workspace_sync=verified` for `contextor.mcp_process_registry`, `contextor.mcp_server`, and `contextor.mcp_backend_control`. Original edits 1–5 and EDIT 6 searches 1–3 each occurred once; EDIT 6 search 4 occurred twice as specified. The corrected successful owned-child SEARCH occurred exactly once. Both new test files were absent.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: All original R4C-3 edits were applied with the single corrected anchor from R1. The independent `control.terminate_registered_process` mock in `stop_backend` remained unchanged. Both new test files match the architect's supplied content apart from final newline formatting. No launcher or LIVE ownership code was changed.

## PARENT_IDENTITY_CLASSIFICATION
CODE_PATH_PROVED: On Windows, the new parent classifier requires a valid parent PID and recorded creation time. A dead parent or a live PID with different creation time is ORPHAN; matching creation time is PARENT_ALIVE; missing or uncertain evidence is UNKNOWN. It does not terminate processes.

## REGISTERED_TREE_DEPTH
CODE_PATH_PROVED: Windows orphan cleanup now performs at most `len(read_records(directory)) + 1` passes. It resolves DEAD and proven identity mismatch records, terminates confirmed orphans through the existing resolver, leaves children with confirmed live parents, and raises on UNKNOWN. The four-level registered-tree fake test passed. This is registered-depth behavior, not full `/T` parity for unregistered descendants.

## OWNED_PROCESS_GENERATION_CHECK
Windows owned-child cleanup requires a valid owner PID and confirmed parent generation. It skips records whose parent is an ORPHAN for the separate sweep, fails on UNKNOWN, and removes a matching direct-child record only after terminate-or-confirm returns true.

## DEAD_AND_UNKNOWN_HANDLING
DEAD registered orphan records are removed without a termination call. UNKNOWN child or parent state raises and retains the record. Identity mismatch requires the central safe-resolution helper. Supplied fake tests cover these branches.

## TARGETED_TEST_RESULTS
`py_compile` for the five changed/new Python files: PASS.
First specified suite: 47 passed, 1 deselected, 1 AuthlibDeprecationWarning.
Second specified suite: 108 passed, 1 warning.
Third specified suite: 32 passed, 1 warning.
No full pytest, real process termination, runtime switch, or launcher execution.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Initial post-edit reads returned generation-proof warnings and one transient `[Errno 36] Resource deadlock avoided` error. Sequential module reads at revision 934 returned `workspace_sync=verified` for registry, server, and backend control. `get_symbol_implementation` at revision 936 returned `status=resolved`, `workspace_sync=verified`, and implementations for `classify_registered_windows_parent`, `_cleanup_orphaned_processes_windows`, and `_cleanup_owned_processes_windows`. These observations verify canonical source visibility, not active loaded-code adoption. No `update_file` or restart occurred.

## FILES_CHANGED
- `contextor/mcp_process_registry.py`
- `contextor/mcp_server.py`
- `tests/test_mcp_child_cleanup_failure_evidence.py`
- `tests/test_mcp_registered_parent_classification.py`
- `tests/test_mcp_server_cleanup_windows.py`

## FULL_DIFFS
```diff
diff --git a/contextor/mcp_process_registry.py b/contextor/mcp_process_registry.py
index 149692a..1016f53 100644
--- a/contextor/mcp_process_registry.py
+++ b/contextor/mcp_process_registry.py
@@ -379,6 +379,58 @@ def classify_registered_windows_process(
     return "ALIVE_MATCH"
 
 
+WindowsRegisteredParentState = Literal[
+    "PARENT_ALIVE",
+    "ORPHAN",
+    "UNKNOWN",
+]
+
+
+def classify_registered_windows_parent(
+    record: dict[str, Any],
+) -> WindowsRegisteredParentState:
+    """Classify the registered parent using PID and creation time."""
+    if not sys_platform_is_windows():
+        return "UNKNOWN"
+
+    if not isinstance(record, dict):
+        return "UNKNOWN"
+
+    parent_pid = record.get("parent_pid")
+    expected_creation = record.get("parent_creation_time")
+
+    if type(parent_pid) is not int or not 0 < parent_pid <= 0xFFFFFFFF:
+        return "UNKNOWN"
+
+    if (
+        type(expected_creation) is not int
+        or not 0 < expected_creation <= 0xFFFFFFFFFFFFFFFF
+    ):
+        return "UNKNOWN"
+
+    try:
+        probe = probe_process_identity(parent_pid)
+    except (OSError, AttributeError, TypeError, ValueError):
+        return "UNKNOWN"
+
+    if probe.state == "dead":
+        return "ORPHAN"
+
+    if probe.state != "alive":
+        return "UNKNOWN"
+
+    if (
+        type(probe.creation_time) is not int
+        or not 0 < probe.creation_time <= 0xFFFFFFFFFFFFFFFF
+    ):
+        return "UNKNOWN"
+
+    if probe.creation_time != expected_creation:
+        return "ORPHAN"
+
+    return "PARENT_ALIVE"
+
+
 def _registered_windows_identity_gone(
     record: dict[str, Any],
 ) -> bool:
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index 8ce08c4..c1ee7e5 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -184,12 +184,16 @@ from contextor.core.analysis.process_pool_lifecycle import (
 )
 from contextor.mcp import query_helpers
 from contextor.mcp_process_registry import (
+    classify_registered_windows_parent,
+    classify_registered_windows_process,
     process_identity,
     read_records,
     record_matches_process,
     register_process,
     registry_dir,
     remove_record,
+    sys_platform_is_windows,
+    terminate_or_confirm_registered_process,
     terminate_registered_process,
 )
 from contextor.mcp_backend_state import (
@@ -586,8 +590,138 @@ mcp = _create_mcp(
 )
 
 
+def _cleanup_orphaned_processes_windows(
+    directory: Path,
+) -> None:
+    """Resolve registered orphans with strict Windows identity proof.
+
+    Allow more than two passes so grandchildren and deeper
+    registered descendants are not dependent on file ordering.
+    """
+    max_passes = len(read_records(directory)) + 1
+
+    for _ in range(max_passes):
+        entries = read_records(directory)
+
+        if not entries:
+            return
+
+        progress = False
+
+        for record_path, record in entries:
+            state = classify_registered_windows_process(record)
+
+            if state == "DEAD":
+                remove_record(record_path)
+                progress = True
+                continue
+
+            if state == "IDENTITY_MISMATCH":
+                if not terminate_or_confirm_registered_process(
+                    record
+                ):
+                    raise RuntimeError(
+                        "registered process identity not confirmed; "
+                        f"pid={record.get('pid')!r}"
+                    )
+
+                remove_record(record_path)
+                progress = True
+                continue
+
+            if state != "ALIVE_MATCH":
+                raise RuntimeError(
+                    "registered process liveness not confirmed; "
+                    f"pid={record.get('pid')!r}"
+                )
+
+            parent_state = classify_registered_windows_parent(
+                record
+            )
+
+            if parent_state == "UNKNOWN":
+                raise RuntimeError(
+                    "registered parent identity not confirmed; "
+                    f"pid={record.get('pid')!r}"
+                )
+
+            if parent_state == "PARENT_ALIVE":
+                continue
+
+            if not terminate_or_confirm_registered_process(
+                record
+            ):
+                raise RuntimeError(
+                    "registered orphan process termination "
+                    "was not confirmed; "
+                    f"pid={record.get('pid')!r}"
+                )
+
+            remove_record(record_path)
+            progress = True
+
+        if not progress:
+            return
+
+    raise RuntimeError(
+        "registered Windows orphan cleanup exceeded "
+        "its bounded multilevel sweep"
+    )
+
+
+def _cleanup_owned_processes_windows(
+    directory: Path,
+    owner_pid: int,
+) -> None:
+    """Clean direct children only with confirmed owner identity."""
+    if type(owner_pid) is not int or not 0 < owner_pid <= 0xFFFFFFFF:
+        raise RuntimeError(
+            "registered MCP owner PID is invalid"
+        )
+
+    for record_path, record in read_records(directory):
+        if type(record.get("parent_pid")) is not int:
+            continue
+
+        if record["parent_pid"] != owner_pid:
+            continue
+
+        parent_state = classify_registered_windows_parent(
+            record
+        )
+
+        if parent_state == "UNKNOWN":
+            raise RuntimeError(
+                "registered MCP child parent identity "
+                "was not confirmed; "
+                f"pid={record.get('pid')!r}"
+            )
+
+        if parent_state == "ORPHAN":
+            # The record belongs to a different generation
+            # of this PID or its parent has already exited.
+            # The orphan sweep resolves it independently.
+            continue
+
+        if not terminate_or_confirm_registered_process(
+            record
+        ):
+            raise RuntimeError(
+                "registered MCP child termination "
+                "was not confirmed; "
+                f"pid={record.get('pid')!r}"
+            )
+
+        remove_record(record_path)
+
+
 def _cleanup_orphaned_processes(directory: Path) -> None:
     """Stop only registered MCP/Git processes whose recorded parent is gone."""
+    if sys_platform_is_windows():
+        _cleanup_orphaned_processes_windows(directory)
+        return
+
+    # Legacy non-Windows behavior.
     # Two passes handle a stale server and one of its Git children regardless
     # of filesystem iteration order: pass one stops the server, pass two the child.
     for _ in range(2):
@@ -620,6 +754,10 @@ def _cleanup_orphaned_processes(directory: Path) -> None:
 
 def _cleanup_owned_processes(directory: Path, owner_pid: int) -> None:
     """Stop registered child processes still owned by this server."""
+    if sys_platform_is_windows():
+        _cleanup_owned_processes_windows(directory, owner_pid)
+        return
+
     for record_path, record in read_records(directory):
         try:
             is_child = int(record.get("parent_pid")) == owner_pid
diff --git a/tests/test_mcp_child_cleanup_failure_evidence.py b/tests/test_mcp_child_cleanup_failure_evidence.py
index ef636fa..7fa7e76 100644
--- a/tests/test_mcp_child_cleanup_failure_evidence.py
+++ b/tests/test_mcp_child_cleanup_failure_evidence.py
@@ -98,6 +98,14 @@ def test_mcp_server_failed_owned_child_retains_record(
     path = tmp_path / "child.json"
     child = _child()
 
+    monkeypatch.setattr(
+        server, "sys_platform_is_windows", lambda: True
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_parent",
+        lambda record: "PARENT_ALIVE",
+    )
     monkeypatch.setattr(
         server,
         "read_records",
@@ -105,7 +113,7 @@ def test_mcp_server_failed_owned_child_retains_record(
     )
     monkeypatch.setattr(
         server,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: False,
     )
     monkeypatch.setattr(
@@ -129,6 +137,15 @@ def test_mcp_server_successful_owned_child_cleanup(
 ):
     path = tmp_path / "child.json"
     child = _child()
+
+    monkeypatch.setattr(
+        server, "sys_platform_is_windows", lambda: True
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_parent",
+        lambda record: "PARENT_ALIVE",
+    )
     removed = []
 
     monkeypatch.setattr(
@@ -138,7 +155,7 @@ def test_mcp_server_successful_owned_child_cleanup(
     )
     monkeypatch.setattr(
         server,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: True,
     )
     monkeypatch.setattr(
@@ -159,6 +176,19 @@ def test_mcp_server_failed_orphan_cleanup_retains_record(
     path = tmp_path / "orphan.json"
     child = _child()
 
+    monkeypatch.setattr(
+        server, "sys_platform_is_windows", lambda: True
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_process",
+        lambda record: "ALIVE_MATCH",
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_parent",
+        lambda record: "ORPHAN",
+    )
     monkeypatch.setattr(
         server,
         "read_records",
@@ -176,7 +206,7 @@ def test_mcp_server_failed_orphan_cleanup_retains_record(
     )
     monkeypatch.setattr(
         server,
-        "terminate_registered_process",
+        "terminate_or_confirm_registered_process",
         lambda record: False,
     )
     monkeypatch.setattr(
diff --git a/tests/test_mcp_registered_parent_classification.py b/tests/test_mcp_registered_parent_classification.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_registered_parent_classification.py
@@ -0,0 +1,129 @@
+from __future__ import annotations
+
+import pytest
+
+from contextor import mcp_process_registry as registry
+
+
+RECORD = {
+    "pid": 501,
+    "parent_pid": 500,
+    "parent_creation_time": 123456789,
+    "creation_time": 123456790,
+    "executable": r"C:\Python\python.exe",
+}
+
+
+@pytest.fixture
+def parent_probe(monkeypatch):
+    monkeypatch.setattr(
+        registry, "sys_platform_is_windows", lambda: True
+    )
+
+    def set_probe(state, creation=None):
+        monkeypatch.setattr(
+            registry,
+            "probe_process_identity",
+            lambda pid: registry.ProcessIdentityProbe(
+                state,
+                None,
+                creation,
+            ),
+        )
+
+    return set_probe
+
+
+def test_live_exact_parent(parent_probe):
+    parent_probe("alive", 123456789)
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "PARENT_ALIVE"
+
+
+def test_dead_parent_is_orphan(parent_probe):
+    parent_probe("dead")
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "ORPHAN"
+
+
+def test_reused_parent_pid_is_orphan(parent_probe):
+    parent_probe("alive", 123456791)
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "ORPHAN"
+
+
+@pytest.mark.parametrize(
+    "creation",
+    [None, False, 0, -1, "123456789"],
+)
+def test_unverified_actual_creation_is_unknown(
+    parent_probe,
+    creation,
+):
+    parent_probe("alive", creation)
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    ("field", "value"),
+    [
+        ("parent_pid", None),
+        ("parent_pid", False),
+        ("parent_pid", 0),
+        ("parent_pid", -1),
+        ("parent_pid", 0x100000000),
+        ("parent_creation_time", None),
+        ("parent_creation_time", False),
+        ("parent_creation_time", 0),
+        ("parent_creation_time", "123456789"),
+    ],
+)
+def test_invalid_parent_identity_is_unknown(
+    parent_probe,
+    field,
+    value,
+):
+    parent_probe("alive", 123456789)
+    record = {**RECORD, field: value}
+
+    assert registry.classify_registered_windows_parent(
+        record
+    ) == "UNKNOWN"
+
+
+def test_unknown_parent_probe_is_unknown(parent_probe):
+    parent_probe("unknown")
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "UNKNOWN"
+
+
+def test_probe_error_is_unknown(parent_probe, monkeypatch):
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda pid: (_ for _ in ()).throw(
+            OSError("access denied")
+        ),
+    )
+
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "UNKNOWN"
+
+
+def test_nonwindows_does_not_claim_parent_identity(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry, "sys_platform_is_windows", lambda: False
+    )
+
+    assert registry.classify_registered_windows_parent(
+        RECORD
+    ) == "UNKNOWN"
diff --git a/tests/test_mcp_server_cleanup_windows.py b/tests/test_mcp_server_cleanup_windows.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_server_cleanup_windows.py
@@ -0,0 +1,337 @@
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+import contextor.mcp_server as server
+
+
+def _record(pid, parent_pid=500, parent_creation=111):
+    return {
+        "pid": pid,
+        "parent_pid": parent_pid,
+        "parent_creation_time": parent_creation,
+        "creation_time": 100000 + pid,
+        "executable": r"C:\Contextor\python.exe",
+    }
+
+
+@pytest.fixture
+def cleanup(monkeypatch, tmp_path):
+    records = {}
+    removed = []
+    terminated = []
+    process_states = {}
+    parent_states = {}
+
+    monkeypatch.setattr(
+        server, "sys_platform_is_windows", lambda: True
+    )
+
+    monkeypatch.setattr(
+        server,
+        "read_records",
+        lambda directory: list(records.items()),
+    )
+    monkeypatch.setattr(
+        server,
+        "remove_record",
+        lambda path: (
+            removed.append(path),
+            records.pop(path, None),
+        ),
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_process",
+        lambda record: process_states.get(
+            record["pid"], "ALIVE_MATCH"
+        ),
+    )
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_parent",
+        lambda record: parent_states.get(
+            record["pid"], "ORPHAN"
+        ),
+    )
+    monkeypatch.setattr(
+        server,
+        "terminate_or_confirm_registered_process",
+        lambda record: (
+            terminated.append(record["pid"]) or True
+        ),
+    )
+
+    def add(pid, parent_pid=500, parent_creation=111):
+        path = tmp_path / f"{pid}.json"
+        records[path] = _record(
+            pid,
+            parent_pid,
+            parent_creation,
+        )
+        return path
+
+    return (
+        add,
+        records,
+        removed,
+        terminated,
+        process_states,
+        parent_states,
+    )
+
+
+def test_dead_orphan_record_is_removed_without_termination(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    states[501] = "DEAD"
+
+    server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in removed
+    assert records == {}
+    assert terminated == []
+
+
+def test_unknown_child_blocks_cleanup(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    states[501] = "UNKNOWN"
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in records
+    assert removed == []
+    assert terminated == []
+
+
+def test_parent_unknown_blocks_orphan_cleanup(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    parents[501] = "UNKNOWN"
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in records
+    assert terminated == []
+
+
+def test_live_parent_is_not_terminated(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    parents[501] = "PARENT_ALIVE"
+
+    server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in records
+    assert terminated == []
+    assert removed == []
+
+
+def test_orphan_is_terminated_and_removed(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+
+    server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in removed
+    assert terminated == [501]
+    assert records == {}
+
+
+def test_failed_orphan_resolution_retains_record(
+    cleanup,
+    monkeypatch,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+
+    monkeypatch.setattr(
+        server,
+        "terminate_or_confirm_registered_process",
+        lambda record: False,
+    )
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in records
+    assert removed == []
+
+
+def test_identity_mismatch_requires_safe_resolution(
+    cleanup,
+    monkeypatch,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    states[501] = "IDENTITY_MISMATCH"
+
+    monkeypatch.setattr(
+        server,
+        "terminate_or_confirm_registered_process",
+        lambda record: False,
+    )
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in records
+    assert removed == []
+
+
+def test_identity_mismatch_proven_gone_removes_record(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    states[501] = "IDENTITY_MISMATCH"
+
+    server._cleanup_orphaned_processes(tmp_path)
+
+    assert path in removed
+    assert terminated == [501]
+
+
+def test_four_level_registered_tree_is_fully_swept(
+    cleanup,
+    monkeypatch,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+
+    # Reverse ordering requires more than two passes.
+    for pid, parent in (
+        (504, 503),
+        (503, 502),
+        (502, 501),
+        (501, 500),
+    ):
+        add(pid, parent)
+
+    def parent_state(record):
+        if record["parent_pid"] in {
+            entry["pid"] for entry in records.values()
+        }:
+            return "PARENT_ALIVE"
+        return "ORPHAN"
+
+    monkeypatch.setattr(
+        server,
+        "classify_registered_windows_parent",
+        parent_state,
+    )
+
+    server._cleanup_orphaned_processes(tmp_path)
+
+    assert terminated == [501, 502, 503, 504]
+    assert records == {}
+    assert len(removed) == 4
+
+
+def test_owned_child_requires_exact_parent_generation(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    good = add(501)
+    stale = add(502)
+    other = add(503, parent_pid=800)
+
+    parents[501] = "PARENT_ALIVE"
+    parents[502] = "ORPHAN"
+
+    server._cleanup_owned_processes(tmp_path, 500)
+
+    assert terminated == [501]
+    assert good in removed
+    assert stale in records
+    assert other in records
+
+
+def test_owned_unknown_parent_blocks_cleanup(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    parents[501] = "UNKNOWN"
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_owned_processes(tmp_path, 500)
+
+    assert path in records
+    assert removed == []
+    assert terminated == []
+
+
+def test_owned_already_dead_child_is_resolved(
+    cleanup,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    states[501] = "DEAD"
+    parents[501] = "PARENT_ALIVE"
+
+    server._cleanup_owned_processes(tmp_path, 500)
+
+    assert path in removed
+    assert terminated == [501]
+
+
+def test_owned_failed_resolution_retains_record(
+    cleanup,
+    monkeypatch,
+    tmp_path,
+):
+    add, records, removed, terminated, states, parents = cleanup
+    path = add(501)
+    parents[501] = "PARENT_ALIVE"
+
+    monkeypatch.setattr(
+        server,
+        "terminate_or_confirm_registered_process",
+        lambda record: False,
+    )
+
+    with pytest.raises(RuntimeError, match="not confirmed"):
+        server._cleanup_owned_processes(tmp_path, 500)
+
+    assert path in records
+    assert removed == []
+
+
+@pytest.mark.parametrize(
+    "owner_pid",
+    [None, False, 0, -1, 0x100000000],
+)
+def test_invalid_owned_parent_pid_is_rejected(
+    cleanup,
+    tmp_path,
+    owner_pid,
+):
+    with pytest.raises(RuntimeError, match="invalid"):
+        server._cleanup_owned_processes(tmp_path, owner_pid)
```

## REMAINING_UNKNOWN
Active backend loaded-code adoption, real Windows process-tree behavior, and unregistered descendant cleanup remain uncertified. The legacy `/T` test remains an explicit open parity gate and was deselected only by the supplied test filter. Python 3.15 launchers were not resumed.

## FINAL_VERDICT
PASS_REGISTERED_TREE_CLEANUP_RUNTIME_GATE_OPEN.
