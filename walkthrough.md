# PY315-R4C-1 — Windows process identity classification

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `c1f3f8c3decb80c49ec457e37f22cc205838fc26`; pre-edit Git status was clean. Contextor MCP reported revision 924, provenance live, and `workspace_sync=verified` for `contextor.mcp_process_registry` and `contextor.core.live_state.runtime`. The literal SEARCH block occurred exactly once; the target test file did not exist.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: The architect's insertion was applied once with `apply_patch`, after `record_matches_process()`. The legacy matcher and Windows termination implementation were not changed. The new test file matches the supplied exact content apart from final newline formatting.

## WINDOWS_CLASSIFICATION_CONTRACT
CODE_PATH_PROVED: `classify_registered_windows_process()` returns one of DEAD, ALIVE_MATCH, IDENTITY_MISMATCH, UNKNOWN. It reads a Windows process probe and compares exact creation identity and normalized full executable path; it does not terminate a process. Non-Windows calls return UNKNOWN.

## PID_REUSE_EVIDENCE
The deterministic test with a live probe at the same PID but a different creation time passed and returned IDENTITY_MISMATCH. A different full executable path also returns IDENTITY_MISMATCH in the supplied tests. These are code/test results, not a real PID reuse experiment.

## UNKNOWN_FAIL_CLOSED
Invalid PID, absent or malformed record identity, absent actual identity fields, unconfirmed probe state, probe error, and non-Windows use return UNKNOWN. The supplied tests cover these cases. No cleanup caller was changed to use the classifier in this task.

## TARGETED_TEST_RESULTS
`py_compile contextor/mcp_process_registry.py tests/test_mcp_registered_process_classification.py`: PASS.
`tests/test_mcp_registered_process_classification.py tests/test_mcp_process_registry.py tests/test_mcp_process_registry_identity_termination.py -q`: 77 passed.
`tests/test_mcp_backend_job_guard.py tests/test_mcp_backend_job_process_scope.py -q`: 18 passed, 1 AuthlibDeprecationWarning.
No full pytest or actual process termination.

## MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: Initial post-edit `contextor.mcp_process_registry` reads at revision 924 showed `workspace_sync=out_of_sync` and `status=stale_source`. A later module read at revision 925 showed `workspace_sync=verified`; `get_symbol_implementation` at revision 926 returned `status=resolved`, `workspace_sync=verified`, and the new classifier implementation. Source implementation visibility is verified. The reread of `contextor.core.live_state.runtime` at revision 924 returned `workspace_sync=verified`; its earlier out_of_sync status cleared naturally. No manual `update_file` or restart occurred. Active loaded-code adoption is UNKNOWN.

## FILES_CHANGED
- `contextor/mcp_process_registry.py`
- `tests/test_mcp_registered_process_classification.py`

## FULL_DIFFS
```diff
diff --git a/contextor/mcp_process_registry.py b/contextor/mcp_process_registry.py
index b0f715c..4a63ec2 100644
--- a/contextor/mcp_process_registry.py
+++ b/contextor/mcp_process_registry.py
@@ -297,6 +297,88 @@ def record_matches_process(record: dict[str, Any]) -> bool:
     return True
 
 
+WindowsRegisteredProcessState = Literal[
+    "DEAD",
+    "ALIVE_MATCH",
+    "IDENTITY_MISMATCH",
+    "UNKNOWN",
+]
+
+
+def classify_registered_windows_process(
+    record: dict[str, Any],
+) -> WindowsRegisteredProcessState:
+    """Classify a registry record without changing process state.
+
+    This is a point-in-time observation, not authorization
+    to terminate a process. Termination must independently
+    verify identity on its own bound Windows process handle.
+    """
+    if not sys_platform_is_windows():
+        return "UNKNOWN"
+
+    if not isinstance(record, dict):
+        return "UNKNOWN"
+
+    pid = record.get("pid")
+
+    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
+        return "UNKNOWN"
+
+    try:
+        probe = probe_process_identity(pid)
+    except (OSError, AttributeError, TypeError, ValueError):
+        return "UNKNOWN"
+
+    if probe.state == "dead":
+        return "DEAD"
+
+    if probe.state != "alive":
+        return "UNKNOWN"
+
+    expected_creation = record.get("creation_time")
+
+    if (
+        type(expected_creation) is not int
+        or not 0 < expected_creation <= 0xFFFFFFFFFFFFFFFF
+        or type(probe.creation_time) is not int
+        or not 0 < probe.creation_time <= 0xFFFFFFFFFFFFFFFF
+    ):
+        return "UNKNOWN"
+
+    if probe.creation_time != expected_creation:
+        return "IDENTITY_MISMATCH"
+
+    expected_image = record.get("executable")
+
+    if (
+        not isinstance(expected_image, str)
+        or not expected_image
+        or not ntpath.isabs(expected_image)
+        or not ntpath.splitdrive(expected_image)[0]
+    ):
+        return "UNKNOWN"
+
+    actual_image = probe.image
+
+    if (
+        not isinstance(actual_image, str)
+        or not actual_image
+        or not ntpath.isabs(actual_image)
+        or not ntpath.splitdrive(actual_image)[0]
+    ):
+        return "UNKNOWN"
+
+    if ntpath.normcase(
+        ntpath.normpath(actual_image)
+    ) != ntpath.normcase(
+        ntpath.normpath(expected_image)
+    ):
+        return "IDENTITY_MISMATCH"
+
+    return "ALIVE_MATCH"
+
+
 def _terminate_windows_record_identity_bound(
     record: dict[str, Any],
 ) -> bool:
diff --git a/tests/test_mcp_registered_process_classification.py b/tests/test_mcp_registered_process_classification.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_registered_process_classification.py
@@ -0,0 +1,254 @@
+from __future__ import annotations
+
+import pytest
+
+from contextor import mcp_process_registry as registry
+
+
+IMAGE = r"C:\Contextor\.venv\Scripts\python.exe"
+
+RECORD = {
+    "pid": 2500,
+    "creation_time": 123456789,
+    "executable": IMAGE,
+}
+
+
+@pytest.fixture
+def windows_probe(monkeypatch):
+    monkeypatch.setattr(
+        registry,
+        "sys_platform_is_windows",
+        lambda: True,
+    )
+
+    def set_probe(state, image=IMAGE, creation=123456789):
+        monkeypatch.setattr(
+            registry,
+            "probe_process_identity",
+            lambda _pid: registry.ProcessIdentityProbe(
+                state,
+                image,
+                creation,
+            ),
+        )
+
+    return set_probe
+
+
+def test_exact_live_identity_is_match(windows_probe):
+    windows_probe("alive")
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "ALIVE_MATCH"
+
+
+def test_case_and_separator_normalization(windows_probe):
+    windows_probe(
+        "alive",
+        image="c:/CONTEXTOR/.venv/SCRIPTS/PYTHON.EXE",
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "ALIVE_MATCH"
+
+
+def test_dead_process_is_dead(windows_probe):
+    windows_probe("dead", None, None)
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "DEAD"
+
+
+def test_reused_pid_is_identity_mismatch(windows_probe):
+    windows_probe(
+        "alive",
+        creation=123456790,
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "IDENTITY_MISMATCH"
+
+
+def test_different_full_executable_is_mismatch(windows_probe):
+    windows_probe(
+        "alive",
+        image=r"C:\Other\.venv315\Scripts\python.exe",
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "IDENTITY_MISMATCH"
+
+
+@pytest.mark.parametrize(
+    "state",
+    ["unknown", "unexpected"],
+)
+def test_unconfirmed_liveness_is_unknown(
+    windows_probe,
+    state,
+):
+    windows_probe(state, None, None)
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    "creation",
+    [None, 0, False, -1, "123456789"],
+)
+def test_missing_or_invalid_actual_creation(
+    windows_probe,
+    creation,
+):
+    windows_probe(
+        "alive",
+        creation=creation,
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    "image",
+    [None, "", "python.exe", r"\Contextor\python.exe"],
+)
+def test_missing_or_invalid_actual_image(
+    windows_probe,
+    image,
+):
+    windows_probe(
+        "alive",
+        image=image,
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    ("field", "value"),
+    [
+        ("creation_time", None),
+        ("creation_time", False),
+        ("creation_time", 0),
+        ("creation_time", "123456789"),
+        ("executable", ""),
+        ("executable", None),
+        ("executable", "python.exe"),
+        ("executable", r"\Contextor\python.exe"),
+    ],
+)
+def test_invalid_record_identity_is_unknown(
+    windows_probe,
+    field,
+    value,
+):
+    windows_probe("alive")
+
+    candidate = {
+        **RECORD,
+        field: value,
+    }
+
+    assert registry.classify_registered_windows_process(
+        candidate
+    ) == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    "pid",
+    [None, False, True, 0, -1, "2500", 0x100000000],
+)
+def test_invalid_pid_never_probes(
+    windows_probe,
+    monkeypatch,
+    pid,
+):
+    def forbidden_probe(_pid):
+        pytest.fail(
+            "invalid PID was probed"
+        )
+
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        forbidden_probe,
+    )
+
+    candidate = {
+        **RECORD,
+        "pid": pid,
+    }
+
+    assert registry.classify_registered_windows_process(
+        candidate
+    ) == "UNKNOWN"
+
+
+def test_unknown_windows_probe_failure_is_closed(
+    windows_probe,
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda _pid: (_ for _ in ()).throw(
+            OSError("query unavailable")
+        ),
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "UNKNOWN"
+
+
+def test_nonwindows_does_not_claim_windows_identity(
+    monkeypatch,
+):
+    monkeypatch.setattr(
+        registry,
+        "sys_platform_is_windows",
+        lambda: False,
+    )
+
+    monkeypatch.setattr(
+        registry,
+        "probe_process_identity",
+        lambda _pid: pytest.fail(
+            "Windows identity probe used on another platform"
+        ),
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "UNKNOWN"
+
+
+def test_classifier_does_not_terminate_process(
+    windows_probe,
+    monkeypatch,
+):
+    windows_probe("alive")
+
+    monkeypatch.setattr(
+        registry,
+        "terminate_registered_process",
+        lambda _record: pytest.fail(
+            "classifier attempted process termination"
+        ),
+    )
+
+    assert registry.classify_registered_windows_process(
+        RECORD
+    ) == "ALIVE_MATCH"
```

## REMAINING_UNKNOWN
Active backend loaded-code adoption and real Windows process behavior. Cleanup callers remain unchanged, the legacy `/T` gate remains open, and Python 3.15 launcher work was not resumed.

## FINAL_VERDICT
PASS_CLASSIFIER_IMPLEMENTED_CLEANUP_PENDING for the exact source/test contract. Canonical MCP source visibility is verified; runtime adoption remains unverified.
