# TASK=CPA10K5B2_PROFILE_WORKER_FINAL_LIFECYCLE_CORRECTIONS

## IMPLEMENTATION_RESULT

PASS

## FILES_CHANGED

- contextor/mcp/tools/contextor_profile_analysis.py
- tests/test_mcp_profile_worker_lifecycle.py
- walkthrough.md (report only; excluded from source/test diff accounting)

OTHER_PRODUCTION_FILES_CHANGED=NONE
EXISTING_K5B2_CONTRACT_UNCHANGED=YES

## REGISTRATION_FAILURE_CLEANUP

REGISTRATION_FAILURE_CANNOT_LEAK_PROFILE_WORKER=YES

_register_process is now inside the existing try/except BaseException boundary. If durable register_process raises after subprocess creation, record_path remains None, _terminate_profile_subprocess uses the direct process.terminate fallback, bounded cleanup runs, the original OSError is re-raised, and finally calls remove_record(None).

## POST_KILL_WAIT_BOUND

FIRST_WAIT_BOUNDED=YES
POST_KILL_WAIT_BOUNDED=YES

_wait_profile_process normalizes timeout once as bounded_timeout. Both process.wait calls use asyncio.wait_for with that same bounded timeout. After kill, the second wait is bounded and catches asyncio.TimeoutError and ProcessLookupError without an unbounded await.

## CERTIFICATION

EXISTING_CANCELLATION_TREE_CLEANUP_UNCHANGED=YES
OTHER_PRODUCTION_FILES_UNCHANGED=YES
PY_COMPILE=PASS
FOCUSED_TESTS=PASS

## EXACT_ANCHORS_VERIFIED

Contextor read-only source-range verification returned status=ok for all requested current functions:

- _wait_profile_process: lines 17-59
- _terminate_profile_subprocess: lines 60-86
- _run_profile_subprocess: lines 87-174
- contextor_profile_analysis: lines 175-193
- source_total_lines=198

The verified source confirms:

- registration failure is inside the BaseException cleanup boundary;
- both process.wait calls are bounded by asyncio.wait_for;
- _terminate_profile_subprocess is unchanged;
- contextor_profile_analysis is unchanged;
- no other production file was modified.

## EXISTING_K5B2_CONTRACT

The existing tree-termination contract remains unchanged. Registered cancellation and exception paths still call _terminate_profile_subprocess, which uses terminate_registered_record through asyncio.shield and asyncio.to_thread, then falls back to process.terminate and bounded wait/kill handling. Only the requested registration-boundary and post-kill wait corrections were applied.

## TESTS

VALIDATION_1:
& .\.venv\Scripts\python.exe -m py_compile contextor/mcp/tools/contextor_profile_analysis.py

RESULT_1:
PASS, exit_code=0

VALIDATION_2:
& .\.venv\Scripts\python.exe -m pytest tests/test_mcp_profile_worker_lifecycle.py -q

RESULT_2:
PASS
.......                                                                  [100%]
7 passed in 0.33s

No other tests were run.

## EVIDENCE

### DIRECT_EVIDENCE

- The two requested production functions were replaced literally.
- The two requested tests were appended literally.
- py_compile exited with code 0.
- The focused lifecycle test command passed all 7 tests.
- Contextor returned status=ok for all four requested source ranges.
- git status after implementation listed only contextor/mcp/tools/contextor_profile_analysis.py, tests/test_mcp_profile_worker_lifecycle.py, and walkthrough.md.

### CODE_PATH_PROVED

- _run_profile_subprocess creates the subprocess before entering try, then performs registry lookup, registration, request construction, and communicate inside the BaseException cleanup boundary.
- Registration failure reaches the existing fallback cleanup owner with record_path=None.
- _wait_profile_process has bounded waits both before and after process.kill.
- _terminate_profile_subprocess and contextor_profile_analysis were not changed by this task.

### CONTRACT_PROVED

- Allowed source/test scope contains exactly the two requested files.
- No profile_worker.py, profile_runner.py, mcp_server.py, mcp_process_registry.py, analysis_jobs.py, process_pool_lifecycle.py, Desktop, LIVE, or runtime_trace file was changed.
- No implementation redesign or post-failure fix was performed.

### INFERENCE

- The registration-failure test proves the direct fallback invocation in the isolated fake-process path. Full OS process-tree behavior remains governed by the unchanged registry implementation and was not runtime-certified in this task.

### UNKNOWN

- Runtime/Desktop certification was not requested and was not performed.
- No claim is made about live process-tree execution beyond the focused unit-contract evidence.

## COMPLETE_DIFFS

The following is the complete current git diff for every source/test file changed by this task. walkthrough.md is excluded.

diff --git a/contextor/mcp/tools/contextor_profile_analysis.py b/contextor/mcp/tools/contextor_profile_analysis.py
index da4f8d4..73f7653 100644
--- a/contextor/mcp/tools/contextor_profile_analysis.py
+++ b/contextor/mcp/tools/contextor_profile_analysis.py
@@ -21,22 +21,41 @@ async def _wait_profile_process(
 ) -> None:
     if process.returncode is not None:
         return
+
+    bounded_timeout = max(
+        0.0,
+        timeout,
+    )
+
     try:
         await asyncio.wait_for(
             process.wait(),
-            timeout=max(0.0, timeout),
+            timeout=bounded_timeout,
         )
+        return
     except asyncio.TimeoutError:
-        if process.returncode is None:
-            try:
-                process.kill()
-            except ProcessLookupError:
-                pass
+        pass
+
+    if process.returncode is None:
         try:
-            await process.wait()
+            process.kill()
         except ProcessLookupError:
             pass
 
+    if process.returncode is not None:
+        return
+
+    try:
+        await asyncio.wait_for(
+            process.wait(),
+            timeout=bounded_timeout,
+        )
+    except (
+        asyncio.TimeoutError,
+        ProcessLookupError,
+    ):
+        pass
+
 
 async def _terminate_profile_subprocess(
     process: asyncio.subprocess.Process,
@@ -81,29 +100,30 @@ async def _run_profile_subprocess(
     )
 
     record_path: Path | None = None
-    registry_value = os.environ.get(
-        "CONTEXTOR_MCP_PROCESS_REGISTRY"
-    )
 
-    if registry_value:
-        record_path = register_process(
-            Path(registry_value),
-            pid=process.pid,
-            parent_pid=os.getpid(),
-            kind="profile-worker",
-            executable=sys.executable,
+    try:
+        registry_value = os.environ.get(
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
         )
 
-    request = json.dumps(
-        {
-            "repo_path": str(root),
-            "exclude_paths": exclude_paths,
-        },
-        ensure_ascii=False,
-        separators=(",", ":"),
-    ).encode("utf-8")
+        if registry_value:
+            record_path = register_process(
+                Path(registry_value),
+                pid=process.pid,
+                parent_pid=os.getpid(),
+                kind="profile-worker",
+                executable=sys.executable,
+            )
+
+        request = json.dumps(
+            {
+                "repo_path": str(root),
+                "exclude_paths": exclude_paths,
+            },
+            ensure_ascii=False,
+            separators=(",", ":"),
+        ).encode("utf-8")
 
-    try:
         stdout, stderr = await process.communicate(
             request
         )
diff --git a/tests/test_mcp_profile_worker_lifecycle.py b/tests/test_mcp_profile_worker_lifecycle.py
index ac282ff..3a2e0cf 100644
--- a/tests/test_mcp_profile_worker_lifecycle.py
+++ b/tests/test_mcp_profile_worker_lifecycle.py
@@ -316,3 +316,77 @@ def test_profile_worker_nonzero_exit_keeps_existing_error_contract(
                 exclude_paths=None,
             )
         )
+
+
+def test_profile_worker_registration_failure_terminates_spawned_process(
+    tmp_path,
+    monkeypatch,
+):
+    process = _FakeProcess()
+
+    async def fake_create(*_args, **_kwargs):
+        return process
+
+    monkeypatch.setattr(
+        profile_module.asyncio,
+        "create_subprocess_exec",
+        fake_create,
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "register_process",
+        lambda *_args, **_kwargs: (
+            _raise_registration_failure()
+        ),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(tmp_path / "mcp-processes"),
+    )
+
+    with pytest.raises(
+        OSError,
+        match="registry unavailable",
+    ):
+        asyncio.run(
+            profile_module._run_profile_subprocess(
+                tmp_path,
+                exclude_paths=None,
+            )
+        )
+
+    assert process.terminate_calls == 1
+
+
+def _raise_registration_failure():
+    raise OSError("registry unavailable")
+
+
+def test_profile_worker_post_kill_wait_is_bounded():
+    class _NeverExitsProcess:
+        pid = 1234
+        returncode = None
+
+        def __init__(self):
+            self.kill_calls = 0
+
+        async def wait(self):
+            await asyncio.sleep(60)
+
+        def kill(self):
+            self.kill_calls += 1
+
+    process = _NeverExitsProcess()
+
+    async def scenario():
+        await asyncio.wait_for(
+            profile_module._wait_profile_process(
+                process,
+                timeout=0.01,
+            ),
+            timeout=0.2,
+        )
+
+    asyncio.run(scenario())
+
+    assert process.kill_calls == 1

