# CPA10K5B1_AUDIT_EVIDENCE_RECOVERY

STATUS=COMPLETE_AUDIT_STOP_AND_WAIT_FOR_PROCEDUJ
TASK=CPA10K5B1_AUDIT_EVIDENCE_RECOVERY
MODE=READ_ONLY_EXACT_AUDITOR_VERIFICATION
SCOPE=CPA10K5B1_ONLY
REPO=C:\Temp\Contextor_Repo

## CURRENT_HEAD

CURRENT_HEAD=4a7169ce61f0192c13d4b185bd1310092f76e48d
HEAD_DECORATION=main, origin/main, origin/HEAD

## GIT_STATUS

git status --short returned no lines.

GIT_STATUS=clean

Required current log:
4a7169c (HEAD -> main, origin/main, origin/HEAD) Auto-commit: Cleanup and update
0794394 Auto-commit: Cleanup and update
e76f638 Auto-commit: Cleanup and update
0689451 Auto-commit: Cleanup and update
0f354be Auto-commit: Cleanup and update
bb1c8f1 Auto-commit: Cleanup and update
77eab44 Auto-commit: Cleanup and update
539d123 Auto-commit: Cleanup and update
2a05bf3 Auto-commit: Cleanup and update
a329086 Auto-commit: Cleanup and update
9fef891 Auto-commit: Cleanup and update
6768630 Auto-commit: Cleanup and update

## K5B1_HISTORY

The required literal history searches all identified the same introducing commit:

_initialize_mcp_managed_worker              0794394 Auto-commit: Cleanup and update
_shutdown_mcp_owned_processes              0794394 Auto-commit: Cleanup and update
terminate_registered_record                 0794394 Auto-commit: Cleanup and update
request_analysis_shutdown                   0794394 Auto-commit: Cleanup and update
test_mcp_managed_pool_worker_is_durably_registered 0794394 Auto-commit: Cleanup and update
tests/test_mcp_child_process_cleanup.py    0794394 Auto-commit: Cleanup and update

K5B1_BASE=e76f63801834a57e96dc6de609622a0730e807f9
K5B1_HEAD=07943943140a2603f109eb20c880e6c84fb5d261
K5B1_COMMIT_PARENT_CONFIRMED=YES
K5B1_HEAD_REMAINS_CURRENT_EXPECTED_FILE_STATE=YES
LATER_COMMITS_TOUCHING_EXPECTED_FILES=NONE
HISTORY_RANGE_CONTAMINATED=NO
DIFF_RECOVERY=PASS

COMMIT_PROVENANCE=UNATTRIBUTED
COMMIT_OWNERSHIP_NOTE=The repository is shared and the Auto-commit messages are not attributed to this agent. K5B1_BASE/K5B1_HEAD are content-based Git boundaries only; this audit does not claim who created, committed, or pushed them.
AGENT_GIT_MUTATIONS_THIS_STEP=NONE

## CONTEXTOR_EXACT_SYMBOL_VERIFICATION

Contextor documentation was read before retrieval. Exact implementation fetches returned status=resolved, workspace_sync=verified, canonical_revision=1293, provenance=live, fresh module/graph/topology/artifact-consumption/cycles/collisions/lineage families, zero syntax errors, zero name collisions, zero cycles, and attention_required=false.

Exact symbol ranges:

- contextor/core/analysis/process_pool_lifecycle.py::_initialize_mcp_managed_worker lines 48-75.
- contextor/core/analysis/process_pool_lifecycle.py::managed_process_pool lines 78-116.
- contextor/core/analysis/process_pool_lifecycle.py::terminate_active_process_pools lines 209-223.
- contextor/mcp_process_registry.py::terminate_registered_process lines 169-245.
- contextor/mcp_process_registry.py::terminate_registered_record lines 248-266.
- contextor/mcp/analysis_jobs.py::request_analysis_shutdown lines 37-61.
- contextor/mcp/analysis_jobs.py::_run_analysis_worker lines 224-300.
- contextor/mcp_server.py::_cleanup_orphaned_processes lines 458-481.
- contextor/mcp_server.py::_cleanup_owned_processes lines 484-493.
- contextor/mcp_server.py::_shutdown_mcp_owned_processes lines 496-518.
- contextor/mcp_server.py::main lines 812-890.

The fetched implementations are reproduced by the recovered Git diff in FULL_DIFFS below; no source was reconstructed from memory.

## CLEANUP_SIGNATURE_DRIFT

Expected auditor-owned signatures:

_cleanup_orphaned_processes(directory: Path) -> None
_cleanup_owned_processes(directory: Path, owner_pid: int) -> None

Current Contextor source confirms exactly those signatures at lines 458 and 484. Current _shutdown_mcp_owned_processes calls exactly:

_cleanup_owned_processes(directory, owner_pid)
_cleanup_orphaned_processes(directory)

No timeout is passed to either existing cleanup helper.

CLEANUP_SIGNATURE_DRIFT=NO

## CANONICAL_GIT_OWNER_PATH

Canonical production owner verified by Contextor and literal source inspection:

contextor/core/analysis/git_context.py::_run_git, lines 17-61.

Confirmed:

- This file is the production owner of _run_git.
- It remains outside the K5B1 range and unchanged.
- It reads CONTEXTOR_MCP_PROCESS_REGISTRY.
- register_process uses parent_pid=os.getpid().
- remove_record(record_path) is executed in finally.

The earlier K5B1 report's contextor/mcp/git_context.py and contextor/core/git_context.py paths were report-only path errors, not source changes.

CANONICAL_GIT_OWNER_VERIFIED=YES

## WORKER_WRAPPER_CONTRACT

Current exact implementation confirms:

- The wrapper is installed only when executor_factory is ProcessPoolExecutor and CONTEXTOR_MCP_PROCESS_REGISTRY is present.
- Original initializer and original initargs are popped, normalized, and passed through the wrapper.
- Worker registration uses kind="process-pool-worker", parent_pid=owner_pid, and executable=sys.executable.
- Finalize(None, remove_record, args=(record_path,), exitpriority=0) removes the record at normal worker exit.
- Without the registry environment, the K5A Desktop behavior remains unchanged because the wrapper branch is not entered.
- terminate_active_process_pools remains the existing active-executor owner and was not redesigned.

PROCESSPOOL_WRAPPER_EXACT=YES

## SERVER_ROOT_BOUNDARY

Current exact main implementation confirms:

- One central process_directory=registry_dir(Path.cwd().resolve()) is selected for the MCP lifetime.
- CONTEXTOR_MCP_PROCESS_REGISTRY is set to that directory and the previous environment value is restored in cleanup.
- server_record is removed with remove_record(server_record); it is never passed to terminate_registered_process.
- _shutdown_mcp_owned_processes receives the server PID only as owner_pid for child-record matching; it does not target os.getpid() as a child record.
- An external Codex/Antigravity parent PID is not selected as an owned child target. Only records in the central registry whose recorded parent_pid matches the MCP server owner are passed to owned cleanup.
- The transport is enclosed in try/finally, and atexit uses the same idempotent _shutdown_cleanup guarded by cleanup_done.
- The external MCP root process remains externally owned.

SERVER_ROOT_EXTERNALLY_OWNED=YES

## ANALYSIS_SHUTDOWN_CONTRACT

Current exact implementation confirms:

- Global _analysis_shutdown_event exists.
- request_analysis_shutdown sets the event, snapshots _analysis_tasks, excludes the current thread, performs bounded joins against one deadline, and returns surviving-task count.
- Project run_full_analysis_exclusive receives progress_callback=_analysis_progress_callback and is_cancelled=_analysis_shutdown_requested.
- The worker preserves a preconfigured CONTEXTOR_MCP_PROCESS_REGISTRY and supplies the repository fallback only when the variable was previously absent.
- Existing environment restoration remains in finally.
- No analysis-job status model or persistence semantics were redesigned by K5B1.

PROJECT_ANALYSIS_COOPERATIVE_SHUTDOWN=YES

## WINDOWS_TREE_TERMINATION_CONTRACT

Current exact implementation confirms:

- terminate_registered_process begins with record_matches_process(record).
- Windows invokes taskkill /F /T /PID <exact registered pid>.
- Identity/liveness is rechecked after taskkill.
- Root-only kernel32 TerminateProcess is the fallback if the registered root remains alive.
- POSIX retains os.kill(pid, signal.SIGTERM).
- No kill-by-name path and no enumeration of all python.exe processes exists. Literal termination surface contains only taskkill, root-only TerminateProcess, and PID-directed os.kill.

WINDOWS_TREE_KILL_IDENTITY_GATED=YES

## TEST_NAME_AND_BODY_CONTRACT

Current test names are:

- test_mcp_managed_pool_worker_is_durably_registered — exact durable ProcessPool worker registration name and body.
- test_windows_registered_process_termination_uses_tree_kill — body matches the Windows taskkill-tree contract, but differs from the earlier auditor prompt's shorter expected name.
- test_analysis_worker_preserves_preconfigured_server_registry — body matches central-registry preservation, but differs from the earlier auditor prompt's expected name.
- test_request_analysis_shutdown_cooperatively_joins_task — exact cooperative join name and body.
- test_mcp_shutdown_order_is_analysis_pool_owned_orphan — body asserts analysis -> pools -> analysis -> owned -> orphaned, but differs from the earlier auditor prompt's expected name.

For all five bodies, the full literal source is recoverable in FULL_DIFFS: the first test is an addition to tests/test_process_pool_lifecycle.py, and the other four are the complete added tests/test_mcp_child_process_cleanup.py.

The bodies establish:

- Durable worker record: registry env, real ProcessPool worker PID, kind=process-pool-worker, matching parent_pid, active-pool registration, and post-context pool cleanup.
- Windows tree kill: Windows branch, identity sequence alive -> dead, exact taskkill command list ["taskkill", "/F", "/T", "/PID", "1234"].
- Central registry preservation: preconfigured registry is observed by the worker and remains in the caller environment after worker completion.
- Cooperative shutdown: event-driven worker exits, bounded join returns zero survivors, and the task is no longer alive.
- Shutdown order: exact calls analysis, pools, analysis, owned, orphaned with the same timeout.

TEST_NAME_DRIFT=YES
TEST_BODY_CONTRACT=YES
TEST_CONTRACT_EXACT=NO

## FILES_CHANGED_BY_K5B1_RANGE

git diff --name-status --find-renames K5B1_BASE K5B1_HEAD returned exactly:

M contextor/core/analysis/process_pool_lifecycle.py
M contextor/mcp/analysis_jobs.py
M contextor/mcp_process_registry.py
M contextor/mcp_server.py
A tests/test_mcp_child_process_cleanup.py
M tests/test_process_pool_lifecycle.py

No file outside EXPECTED_K5B1_FILES is in the range.

## FULL_DIFFS

The following is the complete unabridged output of:
git diff --find-renames e76f63801834a57e96dc6de609622a0730e807f9 07943943140a2603f109eb20c880e6c84fb5d261 -- contextor/core/analysis/process_pool_lifecycle.py contextor/mcp_process_registry.py contextor/mcp/analysis_jobs.py contextor/mcp_server.py tests/test_process_pool_lifecycle.py tests/test_mcp_child_process_cleanup.py

diff --git a/contextor/core/analysis/process_pool_lifecycle.py b/contextor/core/analysis/process_pool_lifecycle.py
index 8aec777..5c269cc 100644
--- a/contextor/core/analysis/process_pool_lifecycle.py
+++ b/contextor/core/analysis/process_pool_lifecycle.py
@@ -3,7 +3,11 @@ from __future__ import annotations
 import os
 import threading
 import time
+from concurrent.futures import ProcessPoolExecutor
 from contextlib import contextmanager
+from multiprocessing.util import Finalize
+from pathlib import Path
+import sys
 from typing import Any, Callable, Iterator
 
 
@@ -38,7 +42,37 @@ def _unregister_executor(executor: Any) -> None:
 def active_process_pool_count() -> int:
     with _registry_lock:
         _ensure_process_local_registry_locked()
-        return len(_active_executors)
+    return len(_active_executors)
+
+
+def _initialize_mcp_managed_worker(
+    owner_pid: int,
+    original_initializer: Callable[..., Any] | None,
+    original_initargs: tuple[Any, ...],
+) -> None:
+    registry_value = os.environ.get(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    )
+    if registry_value:
+        from contextor.mcp_process_registry import (
+            register_process,
+            remove_record,
+        )
+        record_path = register_process(
+            Path(registry_value),
+            pid=os.getpid(),
+            parent_pid=owner_pid,
+            kind="process-pool-worker",
+            executable=sys.executable,
+        )
+        Finalize(
+            None,
+            remove_record,
+            args=(record_path,),
+            exitpriority=0,
+        )
+    if original_initializer is not None:
+        original_initializer(*original_initargs)
 
 
 @contextmanager
@@ -47,7 +81,33 @@ def managed_process_pool(
     *args: Any,
     **kwargs: Any,
 ) -> Iterator[Any]:
-    executor = executor_factory(*args, **kwargs)
+    factory_kwargs = dict(kwargs)
+    registry_value = os.environ.get(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    )
+    if (
+        executor_factory is ProcessPoolExecutor
+        and registry_value
+    ):
+        original_initializer = factory_kwargs.pop(
+            "initializer",
+            None,
+        )
+        original_initargs = tuple(
+            factory_kwargs.pop("initargs", ()) or ()
+        )
+        factory_kwargs["initializer"] = (
+            _initialize_mcp_managed_worker
+        )
+        factory_kwargs["initargs"] = (
+            os.getpid(),
+            original_initializer,
+            original_initargs,
+        )
+    executor = executor_factory(
+        *args,
+        **factory_kwargs,
+    )
     _register_executor(executor)
     try:
         with executor as entered:
diff --git a/contextor/mcp/analysis_jobs.py b/contextor/mcp/analysis_jobs.py
index b503805..84412c9 100644
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -19,10 +19,48 @@ _analysis_lock = threading.Lock()
 _analysis_job_lock = threading.RLock()
 _analysis_tasks: dict[str, threading.Thread] = {}
 _analysis_jobs_by_repo: dict[str, str] = {}
+_analysis_shutdown_event = threading.Event()
 _ANALYSIS_JOB_REPLACE_ATTEMPTS = 4
 _ANALYSIS_JOB_REPLACE_RETRY_SECONDS = 0.05
 
 
+def _analysis_shutdown_requested() -> bool:
+    return _analysis_shutdown_event.is_set()
+
+
+def _analysis_progress_callback(
+    *_args,
+) -> bool:
+    return not _analysis_shutdown_event.is_set()
+
+
+def request_analysis_shutdown(
+    *,
+    timeout: float = 1.5,
+) -> int:
+    _analysis_shutdown_event.set()
+    with _analysis_job_lock:
+        tasks = tuple(_analysis_tasks.values())
+    deadline = time.monotonic() + max(
+        0.0,
+        timeout,
+    )
+    current = threading.current_thread()
+    for task in tasks:
+        if task is current:
+            continue
+        remaining = max(
+            0.0,
+            deadline - time.monotonic(),
+        )
+        task.join(timeout=remaining)
+    return sum(
+        1
+        for task in tasks
+        if task is not current and task.is_alive()
+    )
+
+
 def _mcp_cache_root(root: Path) -> Path:
     from contextor.core.paths import app_cache_dir
 
@@ -197,14 +235,19 @@ async def _run_analysis_worker(
             previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
             previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
             os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
-            os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = str(registry_dir(root))
+            if previous_registry is None:
+                os.environ[
+                    "CONTEXTOR_MCP_PROCESS_REGISTRY"
+                ] = str(registry_dir(root))
             try:
                 if operation == "project":
                     _, result = run_full_analysis_exclusive(
                         str(root),
                         owner="mcp_analysis",
                         log=effective_log,
+                        progress_callback=_analysis_progress_callback,
                         additional_excludes=exclude_paths,
+                        is_cancelled=_analysis_shutdown_requested,
                     )
                     if result is None:
                         raise RuntimeError("Analysis returned no canonical state.")
diff --git a/contextor/mcp_process_registry.py b/contextor/mcp_process_registry.py
index 5602db9..09038a1 100644
--- a/contextor/mcp_process_registry.py
+++ b/contextor/mcp_process_registry.py
@@ -7,6 +7,7 @@ from ctypes import wintypes
 import json
 import os
 import signal
+import subprocess
 import time
 from pathlib import Path
 from typing import Any
@@ -165,27 +166,75 @@ def record_matches_process(record: dict[str, Any]) -> bool:
     return True
 
 
-def terminate_registered_process(record: dict[str, Any]) -> bool:
+def terminate_registered_process(
+    record: dict[str, Any],
+) -> bool:
     if not record_matches_process(record):
         return False
     pid = int(record["pid"])
     if sys_platform_is_windows():
-        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
-        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
+        try:
+            subprocess.run(
+                [
+                    "taskkill",
+                    "/F",
+                    "/T",
+                    "/PID",
+                    str(pid),
+                ],
+                stdout=subprocess.DEVNULL,
+                stderr=subprocess.DEVNULL,
+                check=False,
+                timeout=5.0,
+            )
+        except Exception:
+            pass
+        _, _, alive = process_identity(pid)
+        if not alive:
+            return True
+        kernel32 = ctypes.WinDLL(
+            "kernel32",
+            use_last_error=True,
+        )
+        kernel32.OpenProcess.argtypes = [
+            wintypes.DWORD,
+            wintypes.BOOL,
+            wintypes.DWORD,
+        ]
         kernel32.OpenProcess.restype = wintypes.HANDLE
-        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
+        kernel32.TerminateProcess.argtypes = [
+            wintypes.HANDLE,
+            wintypes.UINT,
+        ]
         kernel32.TerminateProcess.restype = wintypes.BOOL
-        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
+        kernel32.WaitForSingleObject.argtypes = [
+            wintypes.HANDLE,
+            wintypes.DWORD,
+        ]
         kernel32.WaitForSingleObject.restype = wintypes.DWORD
-        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
+        kernel32.CloseHandle.argtypes = [
+            wintypes.HANDLE,
+        ]
         kernel32.CloseHandle.restype = wintypes.BOOL
-        handle = kernel32.OpenProcess(0x0001, False, pid)
+        handle = kernel32.OpenProcess(
+            0x0001,
+            False,
+            pid,
+        )
         if not handle:
             return False
         try:
-            terminated = bool(kernel32.TerminateProcess(handle, 1))
+            terminated = bool(
+                kernel32.TerminateProcess(
+                    handle,
+                    1,
+                )
+            )
             if terminated:
-                kernel32.WaitForSingleObject(handle, 2000)
+                kernel32.WaitForSingleObject(
+                    handle,
+                    2000,
+                )
             return terminated
         finally:
             kernel32.CloseHandle(handle)
@@ -194,3 +243,24 @@ def terminate_registered_process(record: dict[str, Any]) -> bool:
         return True
     except OSError:
         return False
+
+
+def terminate_registered_record(
+    path: Path | None,
+) -> bool:
+    if path is None:
+        return False
+    try:
+        value = json.loads(
+            path.read_text(encoding="utf-8")
+        )
+    except (OSError, ValueError, TypeError):
+        remove_record(path)
+        return False
+    if not isinstance(value, dict):
+        remove_record(path)
+        return False
+    try:
+        return terminate_registered_process(value)
+    finally:
+        remove_record(path)
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
index df85c03..b6636c7 100644
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -173,6 +173,9 @@ from fastmcp.exceptions import ToolError
 from fastmcp.server.middleware import Middleware, MiddlewareContext
 from fastmcp.tools.tool import ToolResult
 from pydantic_core import ValidationError as PydanticCoreValidationError
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
 from contextor.mcp import query_helpers
 from contextor.mcp_process_registry import (
     process_identity,
@@ -490,6 +493,31 @@ def _cleanup_owned_processes(directory: Path, owner_pid: int) -> None:
             remove_record(record_path)
 
 
+def _shutdown_mcp_owned_processes(
+    directory: Path,
+    owner_pid: int,
+    *,
+    timeout: float = 1.5,
+) -> None:
+    from contextor.mcp import analysis_jobs
+    analysis_jobs.request_analysis_shutdown(
+        timeout=timeout,
+    )
+    terminate_active_process_pools(
+        timeout=timeout,
+    )
+    analysis_jobs.request_analysis_shutdown(
+        timeout=timeout,
+    )
+    _cleanup_owned_processes(
+        directory,
+        owner_pid,
+    )
+    _cleanup_orphaned_processes(
+        directory,
+    )
+
+
 import inspect
 from typing import Any, Callable
 
@@ -783,15 +811,21 @@ contextor_profile_analysis = register_mcp_tool(
 
 def main():
     """Entry point for the MCP server."""
-    # Ensure Windows IO encoding is UTF-8 to prevent charmap errors in JSON-RPC
     if sys.platform == "win32":
-        sys.stdout.reconfigure(encoding='utf-8')
-        sys.stderr.reconfigure(encoding='utf-8')
-
+        sys.stdout.reconfigure(encoding="utf-8")
+        sys.stderr.reconfigure(encoding="utf-8")
     import asyncio
 
-    process_directory = registry_dir(Path.cwd().resolve())
+    process_directory = registry_dir(
+        Path.cwd().resolve()
+    )
     _cleanup_orphaned_processes(process_directory)
+    previous_registry = os.environ.get(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    )
+    os.environ[
+        "CONTEXTOR_MCP_PROCESS_REGISTRY"
+    ] = str(process_directory)
     server_record = register_process(
         process_directory,
         pid=os.getpid(),
@@ -799,19 +833,49 @@ def main():
         kind="mcp-server",
         executable=sys.executable,
     )
-
+    cleanup_done = False
     def _shutdown_cleanup() -> None:
-        _cleanup_owned_processes(process_directory, os.getpid())
-        remove_record(server_record)
+        nonlocal cleanup_done
+        if cleanup_done:
+            return
+        cleanup_done = True
+        try:
+            _shutdown_mcp_owned_processes(
+                process_directory,
+                os.getpid(),
+            )
+        finally:
+            remove_record(server_record)
+            if previous_registry is None:
+                os.environ.pop(
+                    "CONTEXTOR_MCP_PROCESS_REGISTRY",
+                    None,
+                )
+            else:
+                os.environ[
+                    "CONTEXTOR_MCP_PROCESS_REGISTRY"
+                ] = previous_registry
 
     atexit.register(_shutdown_cleanup)
-
-    transport = os.environ.get("CONTEXTOR_MCP_TRANSPORT", "stdio").lower()
-
+    transport = os.environ.get(
+        "CONTEXTOR_MCP_TRANSPORT",
+        "stdio",
+    ).lower()
     async def _run():
-        if transport in {"http", "streamable-http"}:
-            host = os.environ.get("CONTEXTOR_MCP_HOST", "127.0.0.1")
-            port = int(os.environ.get("CONTEXTOR_MCP_PORT", "8765"))
+        if transport in {
+            "http",
+            "streamable-http",
+        }:
+            host = os.environ.get(
+                "CONTEXTOR_MCP_HOST",
+                "127.0.0.1",
+            )
+            port = int(
+                os.environ.get(
+                    "CONTEXTOR_MCP_PORT",
+                    "8765",
+                )
+            )
             await mcp.run_http_async(
                 transport="streamable-http",
                 host=host,
@@ -820,8 +884,10 @@ def main():
             )
         else:
             await mcp.run_stdio_async()
-        
-    asyncio.run(_run())
+    try:
+        asyncio.run(_run())
+    finally:
+        _shutdown_cleanup()
 
 
 if __name__ == "__main__":
diff --git a/tests/test_mcp_child_process_cleanup.py b/tests/test_mcp_child_process_cleanup.py
new file mode 100644
index 0000000..5054d1a
--- /dev/null
+++ b/tests/test_mcp_child_process_cleanup.py
@@ -0,0 +1,207 @@
+import asyncio
+import os
+import threading
+import time
+from pathlib import Path
+from types import SimpleNamespace
+
+import contextor.mcp_process_registry as registry
+import contextor.mcp_server as mcp_server
+from contextor.mcp import analysis_jobs
+
+
+def test_windows_registered_process_termination_uses_tree_kill(
+    monkeypatch,
+):
+    calls = []
+    identities = iter(
+        [
+            ("C:/Python/python.exe", 100, True),
+            (None, None, False),
+        ]
+    )
+    monkeypatch.setattr(
+        registry,
+        "sys_platform_is_windows",
+        lambda: True,
+    )
+    monkeypatch.setattr(
+        registry,
+        "process_identity",
+        lambda _pid: next(identities),
+    )
+
+    class _Result:
+        returncode = 0
+
+    monkeypatch.setattr(
+        registry.subprocess,
+        "run",
+        lambda command, **_kwargs: (
+            calls.append(command)
+            or _Result()
+        ),
+    )
+    record = {
+        "pid": 1234,
+        "executable": "C:/Python/python.exe",
+        "creation_time": 100,
+    }
+    assert registry.terminate_registered_process(
+        record
+    ) is True
+    assert calls == [
+        [
+            "taskkill",
+            "/F",
+            "/T",
+            "/PID",
+            "1234",
+        ]
+    ]
+
+
+def test_analysis_worker_preserves_preconfigured_server_registry(
+    tmp_path,
+    monkeypatch,
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / "module.py"
+    target.write_text(
+        "x = 1\n",
+        encoding="utf-8",
+    )
+    central = tmp_path / "central-registry"
+    seen = []
+
+    def fake_analysis(
+        file_path,
+        repo_root,
+        log=None,
+        progress_callback=None,
+        additional_excludes=None,
+    ):
+        seen.append(
+            os.environ.get(
+                "CONTEXTOR_MCP_PROCESS_REGISTRY"
+            )
+        )
+        return None
+
+    monkeypatch.setattr(
+        analysis_jobs.ContextorFacade,
+        "analyze_single_file",
+        staticmethod(fake_analysis),
+    )
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(central),
+    )
+    asyncio.run(
+        analysis_jobs._run_analysis_worker(
+            "single_file",
+            repo,
+            target,
+        )
+    )
+    assert seen == [str(central)]
+    assert (
+        os.environ[
+            "CONTEXTOR_MCP_PROCESS_REGISTRY"
+        ]
+        == str(central)
+    )
+
+
+def test_request_analysis_shutdown_cooperatively_joins_task():
+    analysis_jobs._analysis_shutdown_event.clear()
+    analysis_jobs._analysis_tasks.clear()
+    analysis_jobs._analysis_jobs_by_repo.clear()
+    exited = threading.Event()
+
+    def worker():
+        while (
+            not analysis_jobs
+            ._analysis_shutdown_event
+            .is_set()
+        ):
+            time.sleep(0.01)
+        exited.set()
+
+    task = threading.Thread(
+        target=worker,
+        daemon=True,
+    )
+    task.start()
+    analysis_jobs._analysis_tasks["test"] = task
+    try:
+        survivors = (
+            analysis_jobs.request_analysis_shutdown(
+                timeout=1.0,
+            )
+        )
+        assert survivors == 0
+        assert exited.is_set()
+        assert not task.is_alive()
+    finally:
+        analysis_jobs._analysis_shutdown_event.clear()
+        analysis_jobs._analysis_tasks.clear()
+        analysis_jobs._analysis_jobs_by_repo.clear()
+
+
+def test_mcp_shutdown_order_is_analysis_pool_owned_orphan(
+    tmp_path,
+    monkeypatch,
+):
+    calls = []
+    monkeypatch.setattr(
+        analysis_jobs,
+        "request_analysis_shutdown",
+        lambda *, timeout: (
+            calls.append(("analysis", timeout))
+            or 0
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "terminate_active_process_pools",
+        lambda *, timeout: (
+            calls.append(("pools", timeout))
+            or 0
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_owned_processes",
+        lambda directory, owner_pid: calls.append(
+            (
+                "owned",
+                Path(directory),
+                owner_pid,
+            )
+        ),
+    )
+    monkeypatch.setattr(
+        mcp_server,
+        "_cleanup_orphaned_processes",
+        lambda directory: calls.append(
+            (
+                "orphaned",
+                Path(directory),
+            )
+        ),
+    )
+    directory = tmp_path / "registry"
+    mcp_server._shutdown_mcp_owned_processes(
+        directory,
+        777,
+        timeout=0.25,
+    )
+    assert calls == [
+        ("analysis", 0.25),
+        ("pools", 0.25),
+        ("analysis", 0.25),
+        ("owned", directory, 777),
+        ("orphaned", directory),
+    ]
diff --git a/tests/test_process_pool_lifecycle.py b/tests/test_process_pool_lifecycle.py
index d14f072..d0ba52b 100644
--- a/tests/test_process_pool_lifecycle.py
+++ b/tests/test_process_pool_lifecycle.py
@@ -1,8 +1,10 @@
 from concurrent.futures import ProcessPoolExecutor
+import os
 from types import SimpleNamespace
 import threading
 import time
 
+from contextor import mcp_process_registry
 import contextor.core.analysis.process_pool_lifecycle as lifecycle
 import contextor.ui.gui as gui_module
 
@@ -67,6 +69,46 @@ def test_managed_process_pool_registry_is_process_local():
     assert lifecycle.active_process_pool_count() == 0
 
 
+def test_mcp_managed_pool_worker_is_durably_registered(
+    tmp_path,
+    monkeypatch,
+):
+    registry = tmp_path / "mcp-processes"
+    monkeypatch.setenv(
+        "CONTEXTOR_MCP_PROCESS_REGISTRY",
+        str(registry),
+    )
+    with lifecycle.managed_process_pool(
+        ProcessPoolExecutor,
+        max_workers=1,
+    ) as executor:
+        worker_pid = executor.submit(
+            os.getpid
+        ).result(timeout=10)
+        deadline = time.monotonic() + 5.0
+        worker_record = None
+        while time.monotonic() < deadline:
+            records = mcp_process_registry.read_records(
+                registry
+            )
+            matches = [
+                record
+                for _path, record in records
+                if record.get("kind")
+                == "process-pool-worker"
+                and int(record.get("pid", 0))
+                == worker_pid
+            ]
+            if matches:
+                worker_record = matches[0]
+                break
+            time.sleep(0.02)
+        assert worker_record is not None
+        assert worker_record["parent_pid"] == os.getpid()
+        assert lifecycle.active_process_pool_count() == 1
+    assert lifecycle.active_process_pool_count() == 0
+
+
 def test_force_shutdown_terminates_then_kills_survivors():
     normal = _FakeProcess()
     stubborn = _FakeProcess(survive_terminate=True)


## NO_SOURCE_EDITS_CONFIRMATION

SOURCE_TEST_FILES_MODIFIED_THIS_STEP=NO
WALKTHROUGH_ONLY_FILE_OVERWRITTEN=YES
NO_TEST_RERUN=YES
NO_SOURCE_EDITS=YES
NO_TEST_EDITS=YES
NO_COMMIT_AMEND_RESET_REVERT_CHECKOUT=YES
NO_UPDATE_FILE=YES
NO_FULL_ANALYSIS=YES
NO_DESKTOP_OR_MCP_RESTART=YES

## CERTIFICATION

DIFF_RECOVERY=PASS
HISTORY_RANGE_CONTAMINATED=NO
CLEANUP_SIGNATURE_DRIFT=NO
CANONICAL_GIT_OWNER_VERIFIED=YES
PROCESSPOOL_WRAPPER_EXACT=YES
SERVER_ROOT_EXTERNALLY_OWNED=YES
PROJECT_ANALYSIS_COOPERATIVE_SHUTDOWN=YES
WINDOWS_TREE_KILL_IDENTITY_GATED=YES
TEST_CONTRACT_EXACT=NO
TEST_NAME_DRIFT=YES
TEST_BODY_CONTRACT=YES
SOURCE_TEST_FILES_MODIFIED_THIS_STEP=NO

## STOP

STOP_CONDITION=Evidence recovery complete, walkthrough.md overwritten, wait for proceduj.
