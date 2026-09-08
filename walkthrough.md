EXACT_TEST_BODY=
`test_connect_or_start_dead_child_fast_failure` creates an isolated repo/cache/state root, replaces `_spawn_runtime_subprocess` with a real Python child that immediately exits with code 42, calls `connect_or_start(repo, timeout=0.05, cold_start_timeout=10.0)`, and requires `RuntimeError`.  Before this correction it measured the entire call with `time.monotonic()` and asserted `< 1.0s`; that elapsed interval included repository/domain/lease setup, authority START durable logging, Windows process creation/scheduling, first polling interval, and finally-lock cleanup.

PRODUCTION_FAILURE_BRANCH=
`contextor.core.live_state.runtime.connect_or_start` enters its post-spawn loop, checks `_verified_existing_client`, then executes `if proc.poll() is not None: raise RuntimeError("... exited prematurely with code ...")`.  The timeout branch is separate and only executes after `spawn_deadline` exhaustion, raising `TimeoutError("startup and authority bootstrap timed out after ...")`.  The observed failure and isolated runs use the `proc.poll()` premature-exit branch, never the timeout branch.

TIMING_CONTRACT=
The surrounding test explicitly describes the contract as reporting a dead child by exit code rather than waiting for timeout.  Its adjacent true-startup-hang test covers the distinct hard `cold_start_timeout` behavior, and the slow-healthy-startup test covers waiting past the short normal-connect timeout.  No current runtime contract exposes a sub-one-second wall-clock SLA; `cold_start_timeout=10.0` is the actual normal-startup budget in this test.

CLASSIFICATION=BRITTLE_TIMING_TEST

ROOT_CAUSE=
The `< 1.0` assertion measured unrelated Windows process/fsync/scheduler and finally-cleanup latency in addition to child-death observation.  The full-suite 1.063s sample was still the expected premature-exit RuntimeError, so it did not show that production waited for the 10-second startup deadline.  Three independent isolated pytest invocations passed the old assertion; their total pytest durations were 1.45s, 1.24s, and 10.58s, illustrating why pytest/test-machine wall time is not a valid proof of this semantic contract.

FILES_CHANGED=
tests/test_live_state_ipc.py

IMPLEMENTATION=
Replaced only the arbitrary elapsed-time assertion with a deterministic proof: the fake process's real `poll()` is wrapped and must be called at least once; the raised message must identify premature exit code 42 and must not be the normal startup-timeout message.  The fake child, expected exception type/message, production code, timeouts, and normal timeout/slow-startup coverage remain unchanged.

FOCUSED_RESULT=
PASS — dead-child test: 1 passed in 2.09s.
PASS — dead-child, true-startup-hang, and slow-healthy-startup: 3 passed in 5.19s; 0 skipped.

PYTEST_EXIT_CODE=0

ACTUAL_DIFF=
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index bbd57b4..22af278 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1698,15 +1698,25 @@ def test_connect_or_start_dead_child_fast_failure(tmp_path, monkeypatch):
 
     from contextor.core.live_state import runtime as runtime_mod
     orig_spawn = runtime_mod._spawn_runtime_subprocess
+    poll_calls = 0
 
     # Mock subprocess that immediately exits with code 42
     def mock_spawn(cmd, cwd, env):
+        nonlocal poll_calls
         exit_cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
-        return orig_spawn(exit_cmd, cwd, env)
+        process = orig_spawn(exit_cmd, cwd, env)
+        original_poll = process.poll
+
+        def tracked_poll():
+            nonlocal poll_calls
+            poll_calls += 1
+            return original_poll()
+
+        process.poll = tracked_poll
+        return process
 
     monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)
 
-    t0 = time.monotonic()
     import pytest
     with pytest.raises(RuntimeError) as exc_info:
         runtime_mod.connect_or_start(
@@ -1714,10 +1724,10 @@ def test_connect_or_start_dead_child_fast_failure(tmp_path, monkeypatch):
             timeout=0.05,
             cold_start_timeout=10.0,
         )
-    elapsed = time.monotonic() - t0
-
-    assert "exited prematurely with code 42" in str(exc_info.value)
-    assert elapsed < 1.0  # Fast failure (did not wait 10s)
+    message = str(exc_info.value)
+    assert poll_calls >= 1
+    assert "exited prematurely with code 42" in message
+    assert "startup and authority bootstrap timed out" not in message
 
 
 def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
