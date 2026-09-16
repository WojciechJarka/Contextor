# TASK=CPA10K5B2_PROFILE_WORKER_OWNERSHIP_AND_CANCELLATION_CLEANUP

## IMPLEMENTATION_RESULT

PASS

## FILES_CHANGED

- contextor/mcp/tools/contextor_profile_analysis.py
- tests/test_mcp_profile_worker_lifecycle.py
- walkthrough.md (report only; excluded from source/test diff accounting)

OTHER_SOURCE_TEST_FILES_CHANGED=NONE
K5B1_FILES_UNCHANGED=YES

## LITERAL_CONTENT_MATCH

YES

The production file and test file match CONTENT_1 and CONTENT_2 literally. No implementation or test adaptation was made after validation.

## CERTIFICATION

PROFILE_WORKER_REGISTERED=YES
PROFILE_WORKER_PARENT_IS_MCP=YES
PROFILE_WORKER_NORMAL_RECORD_REMOVAL=YES
PROFILE_WORKER_CANCELLATION_TREE_CLEANUP=YES
PROFILE_WORKER_EXCEPTION_TREE_CLEANUP=YES
PROFILE_WORKER_HARD_ROOT_ORPHAN_RECOVERABLE=YES
PROFILE_DESCENDANT_POOLS_INHERIT_CENTRAL_REGISTRY=YES
PUBLIC_PROFILE_TOOL_CONTRACT_UNCHANGED=YES
PY_COMPILE=PASS
FOCUSED_TESTS=PASS

## EXACT_ANCHORS_VERIFIED

Contextor read-only source-range verification returned status=ok for the literal result:

- _wait_profile_process: lines 17-40
- _terminate_profile_subprocess: lines 41-67
- _run_profile_subprocess: lines 68-154
- contextor_profile_analysis: lines 155-173
- source_total_lines=178

Verified literal lifecycle anchors:

- The central CONTEXTOR_MCP_PROCESS_REGISTRY environment value controls registration.
- register_process receives pid=process.pid, parent_pid=os.getpid(), kind="profile-worker", and executable=sys.executable.
- Normal completion removes record_path in finally.
- BaseException from process.communicate enters _terminate_profile_subprocess and re-raises the original exception.
- Registered cancellation/exception cleanup calls terminate_registered_record through asyncio.shield and asyncio.to_thread.
- Fallback process.terminate and bounded _wait_profile_process/process.kill behavior are present with timeout 2.0 seconds.
- contextor_profile_analysis signature, invalid-path response, profile invocation, and JSON response shape remain unchanged.
- profile_worker.py and profile_runner.py were not modified.
- mcp_server.py, mcp_process_registry.py, analysis_jobs.py, and process_pool_lifecycle.py were not modified.

## PROFILE_WORKER_OWNER

The MCP profile subprocess is registered as a direct child of the MCP process through the existing central registry. The durable record parent_pid is os.getpid() from the MCP tool process.

## NORMAL_EXIT_LIFECYCLE

The worker is registered only when CONTEXTOR_MCP_PROCESS_REGISTRY is present. After communicate completes, the existing JSON/error/result semantics run unchanged and finally calls remove_record(record_path), including when no registry record exists.

## CANCELLATION_LIFECYCLE

Any BaseException escaping communicate, including asyncio.CancelledError, invokes _terminate_profile_subprocess. A registered record is first sent through terminate_registered_record in a shielded thread call, then the direct process termination fallback and bounded wait/kill path are applied as required. The original cancellation or exception is re-raised.

## HARD_MCP_DEATH_MODEL

If the MCP root dies before Python cleanup executes, the durable profile-worker record remains with parent_pid pointing to the dead MCP root. Existing _cleanup_orphaned_processes can recover the stale profile-worker record on the next MCP startup. No second registry or orphan scanner was added.

## DESCENDANT_PROCESSPOOL_INHERITANCE

The existing profile worker environment inherits CONTEXTOR_MCP_PROCESS_REGISTRY. Existing _initialize_mcp_managed_worker registers process-pool descendants with parent_pid equal to the profile-worker PID, allowing the existing two-pass orphan cleanup to terminate the tree.

## PROFILE_TOOL_PUBLIC_CONTRACT

UNCHANGED. The public contextor_profile_analysis(repo_path, exclude_paths=None) signature and current invalid-path, profile-payload, and JSON serialization behavior remain unchanged.

## EVIDENCE

### DIRECT_EVIDENCE

- The requested exact production replacement was applied.
- The requested exact test file was created.
- py_compile exited with code 0.
- pytest output was:
  .....                                                                    [100%]
  5 passed in 0.30s
- Contextor source-range reads returned status=ok for all four requested functions.
- git status after implementation listed only the requested production file, requested test file, and walkthrough.md.
- The required git diff command showed only the requested production diff; the untracked test file was separately captured as a complete /dev/null diff below.

### CODE_PATH_PROVED

- contextor_profile_analysis directly calls _run_profile_subprocess.
- _run_profile_subprocess creates the profile_worker subprocess, conditionally registers it, communicates, cleans the record in finally, and routes BaseException through tree cleanup.
- Existing registry termination, MCP orphan cleanup, and process-pool child registration are unchanged and are the lifecycle owners used by this patch.

### CONTRACT_PROVED

- Only the two allowed source/test files were changed.
- No forbidden helper, timeout, function-name, public-contract, profile-worker, profile-runner, server, registry, analysis-job, process-pool, Desktop, LIVE, runtime-trace, schema, or documentation changes were made.
- No additional tests were run.

### INFERENCE

- Hard-root orphan recovery and descendant tree recovery are inferred from the unchanged existing registry/orphan/process-pool code path plus the new durable profile-worker record. Runtime certification was not performed.

### UNKNOWN

- Runtime/Desktop certification was not requested and was not performed.
- The report does not claim live process-tree execution evidence.

## TESTS

VALIDATION_1:
& .\.venv\Scripts\python.exe -m py_compile contextor/mcp/tools/contextor_profile_analysis.py

RESULT_1:
PASS, exit_code=0

VALIDATION_2:
& .\.venv\Scripts\python.exe -m pytest tests/test_mcp_profile_worker_lifecycle.py -q

RESULT_2:
PASS
.....                                                                    [100%]
5 passed in 0.30s

## COMPLETE_DIFFS

The following are the complete current source/test diffs. walkthrough.md is excluded.

--- contextor/mcp/tools/contextor_profile_analysis.py
diff --git a/contextor/mcp/tools/contextor_profile_analysis.py b/contextor/mcp/tools/contextor_profile_analysis.py
index f57b8d3..da4f8d4 100644
--- a/contextor/mcp/tools/contextor_profile_analysis.py
+++ b/contextor/mcp/tools/contextor_profile_analysis.py
@@ -1,26 +1,178 @@
 import asyncio
 import json
+import os
 import sys
 from pathlib import Path
 
+from contextor.mcp_process_registry import (
+    register_process,
+    remove_record,
+    terminate_registered_record,
+)
+
+
+_PROFILE_PROCESS_WAIT_SECONDS = 2.0
+
+
+async def _wait_profile_process(
+    process: asyncio.subprocess.Process,
+    *,
+    timeout: float = _PROFILE_PROCESS_WAIT_SECONDS,
+) -> None:
+    if process.returncode is not None:
+        return
+    try:
+        await asyncio.wait_for(
+            process.wait(),
+            timeout=max(0.0, timeout),
+        )
+    except asyncio.TimeoutError:
+        if process.returncode is None:
+            try:
+                process.kill()
+            except ProcessLookupError:
+                pass
+        try:
+            await process.wait()
+        except ProcessLookupError:
+            pass
+
+
+async def _terminate_profile_subprocess(
+    process: asyncio.subprocess.Process,
+    record_path: Path | None,
+) -> None:
+    if process.returncode is not None:
+        return
+
+    if record_path is not None:
+        try:
+            await asyncio.shield(
+                asyncio.to_thread(
+                    terminate_registered_record,
+                    record_path,
+                )
+            )
+        except Exception:
+            pass
+
+    if process.returncode is None:
+        try:
+            process.terminate()
+        except ProcessLookupError:
+            pass
+
+    await _wait_profile_process(process)
+
+
+async def _run_profile_subprocess(
+    root: Path,
+    *,
+    exclude_paths: list[str] | None,
+) -> dict[str, object]:
+    process = await asyncio.create_subprocess_exec(
+        sys.executable,
+        "-u",
+        "-m",
+        "contextor.core.analysis.profile_worker",
+        stdin=asyncio.subprocess.PIPE,
+        stdout=asyncio.subprocess.PIPE,
+        stderr=asyncio.subprocess.PIPE,
+    )
+
+    record_path: Path | None = None
+    registry_value = os.environ.get(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    )
+
+    if registry_value:
+        record_path = register_process(
+            Path(registry_value),
+            pid=process.pid,
+            parent_pid=os.getpid(),
+            kind="profile-worker",
+            executable=sys.executable,
+        )
+
+    request = json.dumps(
+        {
+            "repo_path": str(root),
+            "exclude_paths": exclude_paths,
+        },
+        ensure_ascii=False,
+        separators=(",", ":"),
+    ).encode("utf-8")
+
+    try:
+        stdout, stderr = await process.communicate(
+            request
+        )
+    except BaseException:
+        await _terminate_profile_subprocess(
+            process,
+            record_path,
+        )
+        raise
+    finally:
+        remove_record(record_path)
 
-async def _run_profile_subprocess(root: Path, *, exclude_paths: list[str] | None) -> dict[str, object]:
-    process = await asyncio.create_subprocess_exec(sys.executable, "-u", "-m", "contextor.core.analysis.profile_worker", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
-    request = json.dumps({"repo_path": str(root), "exclude_paths": exclude_paths}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
-    stdout, stderr = await process.communicate(request)
     if process.returncode != 0:
-        error = stderr.decode("utf-8", errors="replace").strip()
-        if len(error) > 4000: error = error[-4000:]
-        raise RuntimeError("Contextor profile worker failed" + (f": {error}" if error else "."))
-    try: payload = json.loads(stdout.decode("utf-8"))
-    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise RuntimeError("Contextor profile worker returned invalid JSON.") from exc
-    if not isinstance(payload, dict): raise RuntimeError("Contextor profile worker returned a non-object payload.")
+        error = stderr.decode(
+            "utf-8",
+            errors="replace",
+        ).strip()
+        if len(error) > 4000:
+            error = error[-4000:]
+        raise RuntimeError(
+            "Contextor profile worker failed"
+            + (
+                f": {error}"
+                if error
+                else "."
+            )
+        )
+
+    try:
+        payload = json.loads(
+            stdout.decode("utf-8")
+        )
+    except (
+        UnicodeDecodeError,
+        json.JSONDecodeError,
+    ) as exc:
+        raise RuntimeError(
+            "Contextor profile worker returned invalid JSON."
+        ) from exc
+
+    if not isinstance(payload, dict):
+        raise RuntimeError(
+            "Contextor profile worker returned a non-object payload."
+        )
+
     return payload
-async def contextor_profile_analysis(repo_path: str, exclude_paths: list[str] | None = None) -> str:
+
+
+async def contextor_profile_analysis(
+    repo_path: str,
+    exclude_paths: list[str] | None = None,
+) -> str:
     root = Path(repo_path).expanduser().resolve()
     if not root.is_dir():
-        return f"Error: Repository path '{root}' does not exist."
-    profile = await _run_profile_subprocess(root, exclude_paths=exclude_paths)
-    return json.dumps(profile, indent=2)
+        return (
+            f"Error: Repository path '{root}' "
+            "does not exist."
+        )
+
+    profile = await _run_profile_subprocess(
+        root,
+        exclude_paths=exclude_paths,
+    )
+    return json.dumps(
+        profile,
+        indent=2,
+    )
+
 
-__all__ = ["contextor_profile_analysis"]
+__all__ = [
+    "contextor_profile_analysis",
+]

--- tests/test_mcp_profile_worker_lifecycle.py
diff --git a/tests/test_mcp_profile_worker_lifecycle.py b/tests/test_mcp_profile_worker_lifecycle.py
new file mode 100644
index 0000000..ac282ff
--- /dev/null
+++ b/tests/test_mcp_profile_worker_lifecycle.py
@@ -0,0 +1,318 @@
+import asyncio
+import os
+from pathlib import Path
+
+import pytest
+
+from contextor.mcp.tools import (
+    contextor_profile_analysis as profile_module,
+)
+
+
+class _FakeProcess:
+    def __init__(
+        self,
+        *,
+        pid=1234,
+        returncode=None,
+        stdout=b'{"status":"ok"}',
+        stderr=b"",
+        communicate_error=None,
+    ):
+        self.pid = pid
+        self.returncode = returncode
+        self.stdout_payload = stdout
+        self.stderr_payload = stderr
+        self.communicate_error = communicate_error
+        self.terminate_calls = 0
+        self.kill_calls = 0
+        self.wait_calls = 0
+
+    async def communicate(self, _request):
+        if self.communicate_error is not None:
+            raise self.communicate_error
+        self.returncode = 0
+        return (
+            self.stdout_payload,
+            self.stderr_payload,
+        )
+
+    async def wait(self):
+        self.wait_calls += 1
+        if self.returncode is None:
+            self.returncode = -15
+        return self.returncode
+
+    def terminate(self):
+        self.terminate_calls += 1
+        self.returncode = -15
+
+    def kill(self):
+        self.kill_calls += 1
+        self.returncode = -9
+
+
+def test_profile_worker_registers_and_removes_record(
+    tmp_path,
+    monkeypatch,
+):
+    process = _FakeProcess()
+    central = tmp_path / "mcp-processes"
+    registered = []
+    removed = []
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
+        lambda directory, **kwargs: (
+            registered.append(
+                (Path(directory), kwargs)
+            )
+            or central / "profile-worker-1234.json"
+        ),
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "remove_record",
+        lambda path: removed.append(path),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(central),
+    )
+
+    result = asyncio.run(
+        profile_module._run_profile_subprocess(
+            tmp_path,
+            exclude_paths=None,
+        )
+    )
+
+    assert result == {"status": "ok"}
+    assert registered == [
+        (
+            central,
+            {
+                "pid": 1234,
+                "parent_pid": os.getpid(),
+                "kind": "profile-worker",
+                "executable": profile_module.sys.executable,
+            },
+        )
+    ]
+    assert removed == [
+        central / "profile-worker-1234.json"
+    ]
+
+
+def test_profile_worker_without_registry_keeps_normal_contract(
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
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "register_process",
+        lambda *_args, **_kwargs: (
+            pytest.fail(
+                "profile worker must not register "
+                "without registry environment"
+            )
+        ),
+    )
+
+    result = asyncio.run(
+        profile_module._run_profile_subprocess(
+            tmp_path,
+            exclude_paths=[],
+        )
+    )
+
+    assert result == {"status": "ok"}
+
+
+def test_profile_worker_exception_terminates_registered_tree(
+    tmp_path,
+    monkeypatch,
+):
+    process = _FakeProcess(
+        communicate_error=RuntimeError(
+            "communication failed"
+        )
+    )
+    central = tmp_path / "mcp-processes"
+    record = central / "profile-worker-1234.json"
+    terminated = []
+    removed = []
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
+        lambda *_args, **_kwargs: record,
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "terminate_registered_record",
+        lambda path: (
+            terminated.append(path)
+            or True
+        ),
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "remove_record",
+        lambda path: removed.append(path),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(central),
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="communication failed",
+    ):
+        asyncio.run(
+            profile_module._run_profile_subprocess(
+                tmp_path,
+                exclude_paths=None,
+            )
+        )
+
+    assert terminated == [record]
+    assert removed == [record]
+
+
+def test_profile_worker_cancellation_uses_same_cleanup_path(
+    tmp_path,
+    monkeypatch,
+):
+    started = asyncio.Event()
+    release = asyncio.Event()
+    central = tmp_path / "mcp-processes"
+    record = central / "profile-worker-1234.json"
+    terminated = []
+
+    class _BlockingProcess(_FakeProcess):
+        async def communicate(self, _request):
+            started.set()
+            await release.wait()
+            self.returncode = 0
+            return (
+                self.stdout_payload,
+                self.stderr_payload,
+            )
+
+    process = _BlockingProcess()
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
+        lambda *_args, **_kwargs: record,
+    )
+    monkeypatch.setattr(
+        profile_module,
+        "terminate_registered_record",
+        lambda path: (
+            terminated.append(path)
+            or True
+        ),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(central),
+    )
+
+    async def scenario():
+        task = asyncio.create_task(
+            profile_module._run_profile_subprocess(
+                tmp_path,
+                exclude_paths=None,
+            )
+        )
+        await started.wait()
+        task.cancel()
+        with pytest.raises(asyncio.CancelledError):
+            await task
+
+    asyncio.run(scenario())
+
+    assert terminated == [record]
+
+
+def test_profile_worker_nonzero_exit_keeps_existing_error_contract(
+    tmp_path,
+    monkeypatch,
+):
+    process = _FakeProcess(
+        returncode=1,
+        stderr=b"profile failed",
+    )
+
+    async def fake_create(*_args, **_kwargs):
+        return process
+
+    async def fake_communicate(_request):
+        return (
+            b"",
+            b"profile failed",
+        )
+
+    process.communicate = fake_communicate
+    monkeypatch.setattr(
+        profile_module.asyncio,
+        "create_subprocess_exec",
+        fake_create,
+    )
+    monkeypatch.delenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        raising=False,
+    )
+
+    with pytest.raises(
+        RuntimeError,
+        match="Contextor profile worker failed: profile failed",
+    ):
+        asyncio.run(
+            profile_module._run_profile_subprocess(
+                tmp_path,
+                exclude_paths=None,
+            )
+        )


