# PY315-R4D-R1 — Windows venv redirector PID correction

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `d43d5fd36b533b3497ee516da3890eb072339714`; pre-edit Git status was clean. Contextor MCP reported revision 938, provenance live, and `workspace_sync=verified` for the changed test module and the related registry, Job guard, and server modules. Exact SEARCH counts were EDIT 1 = 5, EDIT 2 = 1, EDIT 3 = 1. No other source or test change was required.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: All five `sys.executable` occurrences were replaced with `sys._base_executable`; the base executable existence check and PID self-report assertions were inserted at their exact anchors using `apply_patch`. The file now has zero `sys.executable` occurrences and six `sys._base_executable` occurrences, including the new existence check. No production file changed.

## VENV_REDIRECTOR_PID_CAUSE
The prior R4D test observed `Popen.pid` differing from the PID written by the Python owner process. The corrected test bypasses the venv executable and both scenarios pass. This supports the venv redirector explanation for the prior discrepancy; the current test does not independently trace the redirector implementation.

## OWNER_PID_ATTESTATION
CONTRACT_PROVED: Both scenarios passed the unchanged assertion `identifiers["owner"] == owner.pid`. The Popen PID was not separately persisted, so the numeric owner PIDs below are from `ready.json`, with equality established by the passing assertion. Normal: owner 11308. Forced: owner 5272.

## CHILD_AND_GRANDCHILD_PID_ATTESTATION
DIRECT_EVIDENCE: In pytest run `pytest-1022`, normal `ready.json` reported child 4708, grandchild 5888, LIVE analogue 2764; `child.json` self-reported child 4708 and grandchild 5888; `grandchild.pid` and `live.pid` matched. Forced `ready.json` reported child 8988, grandchild 15084, LIVE analogue 10496; `child.json` and PID files matched. Normal sentinel self-report was 8892; forced sentinel self-report was 8120. The passing assertions also bound sentinel self-report to `Popen.pid`.

## NORMAL_EXIT_RESULT
PASS: The normal scenario reached `stop.owner`, owner exit, and the post-shutdown liveness assertions. The recorded child and grandchild identities were confirmed gone within the test timeout.

## FORCED_EXIT_RESULT
PASS: The forced scenario reached `owner.terminate()`, owner exit, and the post-shutdown liveness assertions. The recorded child and grandchild identities were confirmed gone within the test timeout.

## LIVE_ANALOGUE_SURVIVAL
PASS in both isolated scenarios: the breakaway leaf's recorded identity was alive after owner exit. This is a LIVE analogue, not the production Contextor LIVE service.

## SENTINEL_SURVIVAL
PASS in both isolated scenarios: the unrelated test-created sentinel's recorded identity was alive after owner exit.

## TEST_PROCESS_CLEANUP
The test `finally` block used identity-bound cleanup for its breakaway leaf and bounded cleanup for its owner/sentinel. A read-only Win32_Process command-line census after the run found zero processes referencing the `pytest-1022` private test root. The test emitted no unresolved-process failure. The census does not substitute for a retained creation-identity audit of every PID after cleanup.

## TARGETED_TEST_RESULTS
`py_compile tests/test_mcp_job_tree_isolated_windows.py`: PASS.
`tests/test_mcp_child_process_cleanup.py tests/test_mcp_job_tree_isolated_windows.py -q`: 6 passed, 1 AuthlibDeprecationWarning.
`tests/test_live_job_object.py -q`: 10 passed.
`tests/test_mcp_process_registry_identity_termination.py tests/test_mcp_registered_process_cleanup.py tests/test_mcp_server_cleanup_windows.py tests/test_mcp_backend_job_guard.py tests/test_mcp_backend_job_process_scope.py -q`: 78 passed, 1 warning.
No full suite, Contextor restart, or launcher execution.

## MCP_POST_CHANGE_AUDIT
Contextor MCP at revision 939 reported `workspace_sync=verified` for the changed test module and unchanged `contextor.mcp_backend_job`, `contextor.mcp_process_registry`, and `contextor.mcp_server`. This is canonical source synchronization, not evidence of active backend loaded-code adoption. No manual `update_file` or restart occurred.

## FILES_CHANGED
- `tests/test_mcp_job_tree_isolated_windows.py`

## FULL_DIFFS
```diff
diff --git a/tests/test_mcp_job_tree_isolated_windows.py b/tests/test_mcp_job_tree_isolated_windows.py
index 71a9553..b63a4bb 100644
--- a/tests/test_mcp_job_tree_isolated_windows.py
+++ b/tests/test_mcp_job_tree_isolated_windows.py
@@ -42,7 +42,7 @@ from pathlib import Path
 root = Path(sys.argv[1])
 flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
 grandchild = subprocess.Popen(
-    [sys.executable, str(root / "leaf.py"), str(root / "grandchild.pid")],
+    [sys._base_executable, str(root / "leaf.py"), str(root / "grandchild.pid")],
     stdin=subprocess.DEVNULL,
     stdout=subprocess.DEVNULL,
     stderr=subprocess.DEVNULL,
@@ -72,7 +72,7 @@ root = Path(sys.argv[1])
 protect_persistent_backend()
 flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
 child = subprocess.Popen(
-    [sys.executable, str(root / "child.py"), str(root)],
+    [sys._base_executable, str(root / "child.py"), str(root)],
     stdin=subprocess.DEVNULL,
     stdout=subprocess.DEVNULL,
     stderr=subprocess.DEVNULL,
@@ -87,7 +87,7 @@ while not (root / "grandchild.pid").exists():
     time.sleep(0.05)
 
 live = subprocess.Popen(
-    [sys.executable, str(root / "leaf.py"), str(root / "live.pid")],
+    [sys._base_executable, str(root / "leaf.py"), str(root / "live.pid")],
     stdin=subprocess.DEVNULL,
     stdout=subprocess.DEVNULL,
     stderr=subprocess.DEVNULL,
@@ -163,13 +163,17 @@ def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_li
         (tmp_path / name).write_text(code, encoding="utf-8")
 
     flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+    base_python = Path(sys._base_executable)
+    assert base_python.is_file(), (
+        "Windows base Python executable is unavailable"
+    )
     repo_root = Path(__file__).resolve().parents[1]
     env = os.environ.copy()
     env["PYTHONPATH"] = os.pathsep.join(
         filter(None, (str(repo_root), env.get("PYTHONPATH", "")))
     )
     sentinel = subprocess.Popen(
-        [sys.executable, str(tmp_path / "leaf.py"), str(tmp_path / "sentinel.pid")],
+        [sys._base_executable, str(tmp_path / "leaf.py"), str(tmp_path / "sentinel.pid")],
         stdin=subprocess.DEVNULL,
         stdout=subprocess.DEVNULL,
         stderr=subprocess.DEVNULL,
@@ -179,7 +183,7 @@ def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_li
     identities = {}
     try:
         owner = subprocess.Popen(
-            [sys.executable, str(tmp_path / "owner.py"), str(tmp_path)],
+            [sys._base_executable, str(tmp_path / "owner.py"), str(tmp_path)],
             cwd=str(repo_root),
             env=env,
             stdin=subprocess.DEVNULL,
@@ -204,6 +208,16 @@ def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_li
         )
         assert _wait_until(lambda: (tmp_path / "live.pid").is_file())
         assert _wait_until(lambda: (tmp_path / "sentinel.pid").is_file())
+        assert _wait_until(lambda: (tmp_path / "child.json").is_file())
+
+        child_report = json.loads(
+            (tmp_path / "child.json").read_text(encoding="utf-8")
+        )
+        assert child_report["pid"] == identifiers["child"]
+        assert child_report["grandchild_pid"] == identifiers["grandchild"]
+        assert _read_pid(tmp_path / "grandchild.pid") == identifiers["grandchild"]
+        assert _read_pid(tmp_path / "live.pid") == identifiers["live"]
+        assert _read_pid(tmp_path / "sentinel.pid") == sentinel.pid
 
         for key in ("child", "grandchild", "live"):
             identities[key] = _identity_record(identifiers[key])
```

## REMAINING_UNKNOWN
Production persistent backend and production LIVE runtime adoption remain untested; full suite and user restart checkpoint remain outstanding. The isolated breakaway leaf verifies a LIVE analogue. PID numeric mappings are from test artifacts, while Popen equality and post-shutdown identity checks are evidenced by passing assertions.

## FINAL_VERDICT
PASS_R4D_READY_FOR_USER_RESTART_AND_FULL_SUITE for this R4D-R1 test checkpoint. No runtime restart or full suite was performed.
