# PY315-R4D — legacy test replacement and isolated Windows Job tree integration

## PREFLIGHT
DIRECT_EVIDENCE: HEAD `c472c26d1b9e1400342de6096666fd7836d06bb7`; pre-edit Git status was clean. Contextor MCP module contexts for `contextor.mcp_process_registry`, `contextor.mcp_backend_job`, and `contextor.mcp_server` returned revision 936, provenance live, and `workspace_sync=verified`. The exact SEARCH occurred once and the new test file was absent. The existing LIVE integration test uses a private tmp_path repo/cache/state and a helper process created by that test.

## EXACT_SEARCH_REPLACE_RESULTS
CONTRACT_PROVED: The obsolete taskkill assertion was replaced at the single exact anchor with `apply_patch`; every other test in that file was left unchanged. The new isolated Windows test file matches the supplied content apart from final newline formatting. No production source was changed.

## LEGACY_TEST_REPLACEMENT
The replacement test now checks that Windows `terminate_registered_process` delegates to the identity-bound helper without invoking the legacy PID-only matcher. It passed in the targeted run.

## JOB_OBJECT_NORMAL_EXIT
FAIL: The isolated test stopped before triggering normal owner exit. At `tests/test_mcp_job_tree_isolated_windows.py:200`, `ready.json` reported owner PID 9992 while `Popen.pid` was 12256. The assertion failed before `stop.owner` was written. Job closure behavior in this scenario is UNKNOWN.

## JOB_OBJECT_FORCED_EXIT
FAIL: The same early assertion failed before forced termination. `ready.json` reported owner PID 13256 while `Popen.pid` was 7432. Forced Job closure behavior is UNKNOWN.

## UNREGISTERED_CHILD_AND_GRANDCHILD
UNKNOWN: The new test created a child/grandchild chain but failed before its post-shutdown liveness assertions. The observed PID mismatch is consistent with a Windows venv redirector process boundary, but no root cause is claimed from this test alone.

## BREAKAWAY_LIVE_ANALOGUE
UNKNOWN for the new isolated scenario because it failed before the survival assertion. Its breakaway leaf is a LIVE analogue, not the production Contextor LIVE service. The separate existing LIVE Job Object integration suite passed (10 tests).

## UNRELATED_PROCESS_SURVIVAL
UNKNOWN for the new isolated scenario because the sentinel survival assertion was not reached.

## TEST_PROCESS_CLEANUP
The new test's `finally` block executed on both assertion failures. A read-only Win32_Process command-line census after the failures found no matching process command lines for either test-private tmp_path. This is a bounded observation; it does not prove every recorded PID's creation identity exited. No existing Contextor, Codex, Desktop, or LIVE process was intentionally targeted.

## REAL_WINDOWS_INTEGRATION_RESULTS
`tests/test_mcp_child_process_cleanup.py tests/test_mcp_job_tree_isolated_windows.py -q`: 4 passed, 2 failed, 1 warning. Normal and forced isolated scenarios both FAIL at the owner PID assertion, before their Job tree assertions. This is an open Windows integration regression gate.

## EXISTING_LIVE_INTEGRATION_RESULTS
`tests/test_live_job_object.py -q`: 10 passed. This includes the existing real Windows LIVE Job Object integration and its cleanup regressions; it is separate from the new breakaway analogue test.

## TARGETED_TEST_RESULTS
`py_compile` for both edited/new test files: PASS.
Identity and cleanup regressions: 78 passed, 1 warning.
No full pytest, launcher, backend restart, or production LIVE restart.

## MCP_POST_CHANGE_AUDIT
Initial MCP reads encountered one transient `[Errno 36] Resource deadlock avoided` and an `unverified` generation-proof result. Sequential module reads at revision 938 returned `workspace_sync=verified` for `contextor.mcp_process_registry`, `contextor.mcp_backend_job`, and `contextor.mcp_server`. These are unchanged production modules in this task. Canonical source synchronization does not establish active loaded-code adoption. No manual `update_file` or restart occurred.

## FILES_CHANGED
- `tests/test_mcp_child_process_cleanup.py`
- `tests/test_mcp_job_tree_isolated_windows.py`

## FULL_DIFFS
```diff
diff --git a/tests/test_mcp_child_process_cleanup.py b/tests/test_mcp_child_process_cleanup.py
index 5054d1a..f832878 100644
--- a/tests/test_mcp_child_process_cleanup.py
+++ b/tests/test_mcp_child_process_cleanup.py
@@ -10,56 +10,44 @@ import contextor.mcp_server as mcp_server
 from contextor.mcp import analysis_jobs
 
 
-def test_windows_registered_process_termination_uses_tree_kill(
+def test_windows_registered_process_uses_identity_bound_termination(
     monkeypatch,
 ):
+    record = {
+        "pid": 1234,
+        "executable": r"C:\Python\python.exe",
+        "creation_time": 100,
+    }
     calls = []
-    identities = iter(
-        [
-            ("C:/Python/python.exe", 100, True),
-            (None, None, False),
-        ]
-    )
+
     monkeypatch.setattr(
         registry,
         "sys_platform_is_windows",
         lambda: True,
     )
+
+    def forbid_legacy_match(_record):
+        raise AssertionError(
+            "Windows termination used the old PID-only matcher"
+        )
+
     monkeypatch.setattr(
         registry,
-        "process_identity",
-        lambda _pid: next(identities),
+        "record_matches_process",
+        forbid_legacy_match,
     )
 
-    class _Result:
-        returncode = 0
-
     monkeypatch.setattr(
-        registry.subprocess,
-        "run",
-        lambda command, **_kwargs: (
-            calls.append(command)
-            or _Result()
-        ),
+        registry,
+        "_terminate_windows_record_identity_bound",
+        lambda value: calls.append(value) or True,
     )
-    record = {
-        "pid": 1234,
-        "executable": "C:/Python/python.exe",
-        "creation_time": 100,
-    }
+
     assert registry.terminate_registered_process(
         record
     ) is True
-    assert calls == [
-        [
-            "taskkill",
-            "/F",
-            "/T",
-            "/PID",
-            "1234",
-        ]
-    ]
 
+    assert calls == [record]
 
 def test_analysis_worker_preserves_preconfigured_server_registry(
     tmp_path,
diff --git a/tests/test_mcp_job_tree_isolated_windows.py b/tests/test_mcp_job_tree_isolated_windows.py
new file mode 100644
--- /dev/null
+++ b/tests/test_mcp_job_tree_isolated_windows.py
@@ -0,0 +1,263 @@
+"""Isolated Windows process-tree regression for backend-owned Job Objects."""
+
+from __future__ import annotations
+
+import json
+import os
+import subprocess
+import sys
+import time
+from pathlib import Path
+
+import pytest
+
+from contextor import mcp_process_registry as registry
+
+
+pytestmark = pytest.mark.skipif(
+    sys.platform != "win32",
+    reason="Real Windows Job Object integration test",
+)
+
+
+LEAF_CODE = """
+import os
+import sys
+import time
+from pathlib import Path
+
+Path(sys.argv[1]).write_text(str(os.getpid()), encoding="ascii")
+time.sleep(120)
+"""
+
+
+CHILD_CODE = """
+import json
+import os
+import subprocess
+import sys
+import time
+from pathlib import Path
+
+root = Path(sys.argv[1])
+flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+grandchild = subprocess.Popen(
+    [sys.executable, str(root / "leaf.py"), str(root / "grandchild.pid")],
+    stdin=subprocess.DEVNULL,
+    stdout=subprocess.DEVNULL,
+    stderr=subprocess.DEVNULL,
+    creationflags=flags,
+)
+(root / "child.json").write_text(
+    json.dumps({"pid": os.getpid(), "grandchild_pid": grandchild.pid}),
+    encoding="utf-8",
+)
+time.sleep(120)
+"""
+
+
+OWNER_CODE = """
+import json
+import os
+import subprocess
+import sys
+import time
+from pathlib import Path
+from contextor.mcp_backend_job import (
+    protect_persistent_backend,
+    require_live_outside_backend_job,
+)
+
+root = Path(sys.argv[1])
+protect_persistent_backend()
+flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+child = subprocess.Popen(
+    [sys.executable, str(root / "child.py"), str(root)],
+    stdin=subprocess.DEVNULL,
+    stdout=subprocess.DEVNULL,
+    stderr=subprocess.DEVNULL,
+    creationflags=flags,
+)
+limit = time.monotonic() + 15
+while not (root / "grandchild.pid").exists():
+    if child.poll() is not None:
+        raise RuntimeError("child exited before grandchild startup")
+    if time.monotonic() > limit:
+        raise RuntimeError("grandchild did not start")
+    time.sleep(0.05)
+
+live = subprocess.Popen(
+    [sys.executable, str(root / "leaf.py"), str(root / "live.pid")],
+    stdin=subprocess.DEVNULL,
+    stdout=subprocess.DEVNULL,
+    stderr=subprocess.DEVNULL,
+    creationflags=flags | 0x01000000,
+)
+(root / "live_spawned.pid").write_text(str(live.pid), encoding="ascii")
+require_live_outside_backend_job(live)
+(root / "ready.json").write_text(
+    json.dumps({"owner": os.getpid(), "child": child.pid,
+                "grandchild": int((root / "grandchild.pid").read_text()),
+                "live": live.pid}),
+    encoding="utf-8",
+)
+limit = time.monotonic() + 120
+while time.monotonic() < limit and not (root / "stop.owner").exists():
+    time.sleep(0.05)
+"""
+
+
+def _wait_until(predicate, timeout=15.0):
+    deadline = time.monotonic() + timeout
+    while time.monotonic() < deadline:
+        if predicate():
+            return True
+        time.sleep(0.05)
+    return predicate()
+
+
+def _identity_record(pid):
+    probe = registry.probe_process_identity(pid)
+    assert probe.state == "alive", f"test process {pid}: {probe.state}"
+    assert isinstance(probe.creation_time, int) and probe.creation_time > 0
+    assert isinstance(probe.image, str) and probe.image
+    return {
+        "pid": pid,
+        "creation_time": probe.creation_time,
+        "executable": probe.image,
+    }
+
+
+def _recorded_identity_alive(record):
+    probe = registry.probe_process_identity(record["pid"])
+    return probe.state == "alive" and probe.creation_time == record["creation_time"]
+
+
+def _recorded_identity_gone(record):
+    probe = registry.probe_process_identity(record["pid"])
+    return probe.state == "dead" or (
+        probe.state == "alive"
+        and isinstance(probe.creation_time, int)
+        and probe.creation_time != record["creation_time"]
+    )
+
+
+def _read_pid(path):
+    if not path.is_file():
+        return None
+    try:
+        return int(path.read_text(encoding="ascii"))
+    except (OSError, ValueError):
+        return None
+
+
+@pytest.mark.parametrize("shutdown", ["normal", "forced"])
+def test_isolated_backend_job_kills_unregistered_child_and_grandchild_but_not_live_or_unrelated(
+    tmp_path: Path, shutdown: str,
+):
+    for name, code in (
+        ("leaf.py", LEAF_CODE),
+        ("child.py", CHILD_CODE),
+        ("owner.py", OWNER_CODE),
+    ):
+        (tmp_path / name).write_text(code, encoding="utf-8")
+
+    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
+    repo_root = Path(__file__).resolve().parents[1]
+    env = os.environ.copy()
+    env["PYTHONPATH"] = os.pathsep.join(
+        filter(None, (str(repo_root), env.get("PYTHONPATH", "")))
+    )
+    sentinel = subprocess.Popen(
+        [sys.executable, str(tmp_path / "leaf.py"), str(tmp_path / "sentinel.pid")],
+        stdin=subprocess.DEVNULL,
+        stdout=subprocess.DEVNULL,
+        stderr=subprocess.DEVNULL,
+        creationflags=flags,
+    )
+    owner = None
+    identities = {}
+    try:
+        owner = subprocess.Popen(
+            [sys.executable, str(tmp_path / "owner.py"), str(tmp_path)],
+            cwd=str(repo_root),
+            env=env,
+            stdin=subprocess.DEVNULL,
+            stdout=subprocess.DEVNULL,
+            stderr=subprocess.PIPE,
+            creationflags=flags,
+        )
+
+        def ready_or_exited():
+            return (tmp_path / "ready.json").is_file() or owner.poll() is not None
+
+        assert _wait_until(ready_or_exited), "isolated Job owner readiness timeout"
+        if owner.poll() is not None:
+            detail = owner.stderr.read().decode("utf-8", errors="replace")
+            pytest.fail(f"isolated Job owner startup failed: {detail}")
+
+        identifiers = json.loads((tmp_path / "ready.json").read_text(encoding="utf-8"))
+        assert identifiers["owner"] == owner.pid
+        assert identifiers["child"] != identifiers["grandchild"]
+        assert identifiers["live"] not in (
+            identifiers["owner"], identifiers["child"], identifiers["grandchild"]
+        )
+        assert _wait_until(lambda: (tmp_path / "live.pid").is_file())
+        assert _wait_until(lambda: (tmp_path / "sentinel.pid").is_file())
+
+        for key in ("child", "grandchild", "live"):
+            identities[key] = _identity_record(identifiers[key])
+        identities["sentinel"] = _identity_record(sentinel.pid)
+
+        assert all(_recorded_identity_alive(r) for r in identities.values())
+        if shutdown == "normal":
+            (tmp_path / "stop.owner").write_text("1", encoding="ascii")
+        else:
+            owner.terminate()
+        owner.wait(timeout=8)
+
+        assert _wait_until(
+            lambda: _recorded_identity_gone(identities["child"])
+            and _recorded_identity_gone(identities["grandchild"]),
+            timeout=8,
+        ), "backend Job Object left child or grandchild alive"
+        assert _recorded_identity_alive(identities["live"]), "breakaway LIVE died"
+        assert _recorded_identity_alive(identities["sentinel"]), "unrelated process died"
+    finally:
+        if owner is not None:
+            if owner.poll() is None:
+                owner.terminate()
+            try:
+                owner.wait(timeout=5)
+            except subprocess.TimeoutExpired:
+                owner.kill()
+                owner.wait(timeout=5)
+            if owner.stderr is not None:
+                owner.stderr.close()
+
+        if "live" not in identities:
+            pid = _read_pid(tmp_path / "live_spawned.pid") or _read_pid(tmp_path / "live.pid")
+            if pid is not None:
+                probe = registry.probe_process_identity(pid)
+                if probe.state == "alive" and probe.creation_time and probe.image:
+                    identities["live"] = {
+                        "pid": pid,
+                        "creation_time": probe.creation_time,
+                        "executable": probe.image,
+                    }
+
+        unresolved = []
+        for key in ("live", "grandchild", "child"):
+            record = identities.get(key)
+            if record is not None and not registry.terminate_or_confirm_registered_process(record):
+                unresolved.append(key)
+
+        if sentinel.poll() is None:
+            sentinel.terminate()
+        try:
+            sentinel.wait(timeout=5)
+        except subprocess.TimeoutExpired:
+            sentinel.kill()
+            sentinel.wait(timeout=5)
+        if unresolved:
+            pytest.fail(f"isolated test-owned processes unresolved: {unresolved}")
```

## REMAINING_UNKNOWN
Whether the new isolated Job Object closes child and grandchild on normal or forced owner exit, whether its breakaway analogue and unrelated sentinel survive, the exact cause of the owner PID discrepancy, and whether all test-created PIDs exited after cleanup. The dual launchers remain paused.

## FINAL_VERDICT
FAIL_WINDOWS_INTEGRATION. Both new isolated real-Windows scenarios failed before their intended Job tree assertions; no expectations or code were altered to force a pass.
