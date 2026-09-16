# CPA10K5A_DESKTOP_PROCESS_POOL_OWNERSHIP_AND_FORCED_SHUTDOWN

MODE=IMPLEMENT_EXACT_AUDITOR_DESIGN
REPO=C:\\Temp\\Contextor_Repo
SCOPE=DESKTOP_OWNED_PROCESS_POOL_WORKERS_ONLY
IMPLEMENTATION_RESULT=PASS
FULL_ANALYSIS=NOT_RUN
LIVE_MCP_RESTART=NOT_PERFORMED
UPDATE_FILE=NOT_USED
RUNTIME_TRACE_TOUCHED=NO
MCP_PROCESS_CLEANUP_TOUCHED=NO

## EXACT_ANCHORS_VERIFIED

Before edit, Contextor verified with `workspace_sync=verified`, canonical revision 1281:

- `index_repository`: exact existing `ProcessPoolExecutor()` call and existing `executor.shutdown(wait=False, cancel_futures=True)` cancellation path.
- `collect_module_artifacts`: exact local `ProcessPoolExecutor, as_completed` import, existing pool, and existing cancellation path.
- `ContextorGUI.on_closing`: existing cooperative `FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS=1.5` wait before LIVE shutdown and `root.destroy`.

Literal source verification found exactly two production ProcessPoolExecutor creation call sites. `contextor/__main__.py` contains only a Windows comment, not a creation site.

After edit, Contextor verified the new lifecycle functions with `status=resolved`, `workspace_sync=verified`, canonical revision 1282:

- `managed_process_pool`: lines 44-56.
- `terminate_process_pool`: lines 88-146.
- `terminate_active_process_pools`: lines 149-163.

The modified existing files were verified with fresh Contextor source ranges because their symbol fetches reported `workspace_sync=out_of_sync` after local edits:

- indexer managed pool/cancellation range: status `ok`, lines 900-968.
- artifact managed pool/cancellation range: status `ok`, lines 245-306.
- GUI import range: status `ok`, lines 15-34.
- GUI close order range: status `ok`, lines 1247-1305.
- GUI close tail/root destroy range: status `ok`, lines 1348-1365.

All Contextor results reported fresh syntax diagnostics with no collisions, cycles, or diagnostic attention. No `update_file` or full analysis was used.

## FILES_CHANGED

- `contextor/core/analysis/process_pool_lifecycle.py`
- `contextor/core/symbol_engine/indexer.py`
- `contextor/core/reporting_layer/artifact_usage_report.py`
- `contextor/ui/gui.py`
- `tests/test_process_pool_lifecycle.py`
- `walkthrough.md` report artifact only and excluded from production/test diff accounting

No file outside FILES_CHANGED_EXPECTED changed in this step. No MCP file was changed.

## PROCESS_LOCAL_OWNERSHIP_MODEL

The registry is process-local in memory:

- `_active_executors` stores executor objects by `id(executor)`.
- `_registry_pid` detects a changed process identity and clears inherited registry state after fork.
- `managed_process_pool` registers before entering the executor context and unregisters in `finally`.
- No file registry, owner token, MCP registry, or cross-process ownership mechanism was added.
- External Antigravity/Codex MCP root processes cannot appear in this registry because they are not executor objects registered in this Python process.

## PROCESS_POOL_CALL_SITES

Exactly two production ProcessPoolExecutor creation sites remain:

1. `contextor/core/symbol_engine/indexer.py`
   - retains `from concurrent.futures import ProcessPoolExecutor, as_completed`;
   - wraps `ProcessPoolExecutor` with `managed_process_pool`;
   - replaces cancellation shutdown with `terminate_process_pool(executor)`.

2. `contextor/core/reporting_layer/artifact_usage_report.py`
   - retains the local `from concurrent.futures import ProcessPoolExecutor, as_completed` import required by existing monkeypatch contracts;
   - wraps the initializer/configured pool with `managed_process_pool`;
   - replaces cancellation shutdown with `terminate_process_pool(executor)`.

No other production ProcessPoolExecutor creation call site exists.

## DESKTOP_CLOSE_ORDER

`ContextorGUI.on_closing` now executes:

1. existing cooperative cancellation signal;
2. existing first bounded wait of 1.5 seconds;
3. `terminate_active_process_pools(timeout=1.5)` for the current Desktop process registry only;
4. second bounded wait of 1.5 seconds;
5. existing watcher/feed/client/LIVE shutdown;
6. existing state save and `root.destroy()`.

The value `FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS = 1.5` and all existing LIVE shutdown logic remain unchanged.

## REAL_WORKER_TERMINATION_EVIDENCE

`test_real_process_pool_workers_are_force_terminated` creates a real `ProcessPoolExecutor(max_workers=2)`, starts two long-running workers, confirms both workers are alive and registered, invokes `terminate_active_process_pools(timeout=2.0)`, and confirms both worker processes are no longer alive. This test passed.

The fake-process test also confirms the exact sequence: executor shutdown with `wait=False, cancel_futures=True`, terminate, bounded join, kill survivor, bounded join.

## EXTERNAL_MCP_EXCLUSION_EVIDENCE

- Registry storage is only module memory guarded by `_registry_lock`.
- Registry state is keyed to the current OS process through `_registry_pid`.
- No import or call to `mcp_process_registry`, `terminate_pid_tree`, or MCP shutdown was added.
- No file under `contextor/mcp*` changed.
- Certification is limited to Desktop-owned ProcessPoolExecutor workers; external MCP roots are explicitly outside this mechanism.

## PY_COMPILE

Command:

`& .\\.venv\\Scripts\\python.exe -m py_compile contextor/core/analysis/process_pool_lifecycle.py contextor/core/symbol_engine/indexer.py contextor/core/reporting_layer/artifact_usage_report.py contextor/ui/gui.py`

Result: PASS

## TESTS

Authorized command:

`& .\\.venv\\Scripts\\python.exe -m pytest tests/test_process_pool_lifecycle.py tests/test_artifact_adaptive_execution.py tests/test_cancellation.py -q`

Result: `22 passed in 10.92s`

No broad/full pytest suite was run.

## CERTIFICATION

PROCESS_POOL_REGISTRY_PROCESS_LOCAL=YES
INDEXER_POOL_MANAGED=YES
ARTIFACT_POOL_MANAGED=YES
CANCELLATION_FORCE_TERMINATES_RUNNING_WORKERS=YES
DESKTOP_CLOSE_FORCE_TERMINATES_ACTIVE_POOLS=YES
REAL_PROCESSPOOL_WORKERS_GONE_AFTER_FORCE_SHUTDOWN=YES
EXTERNAL_MCP_ROOT_CAN_BE_TERMINATED_BY_DESKTOP=NO
MCP_PROCESS_CLEANUP_TOUCHED=NO
PY_COMPILE=PASS
FOCUSED_TESTS=PASS

## COMPLETE_DIFFS

The following is the complete diff for every production/test file changed in this step. New files are represented as full new-file diffs. `walkthrough.md` is excluded.

diff --git a/contextor/core/reporting_layer/artifact_usage_report.py b/contextor/core/reporting_layer/artifact_usage_report.py
index 44f7466..8648edf 100644
--- a/contextor/core/reporting_layer/artifact_usage_report.py
+++ b/contextor/core/reporting_layer/artifact_usage_report.py
@@ -49,6 +49,10 @@ from contextor.core.analysis.test_context import (
     build_test_context_index,
     discover_test_dirs,
 )
+from contextor.core.analysis.process_pool_lifecycle import (
+    managed_process_pool,
+    terminate_process_pool,
+)
 from contextor.core.api.api_consumers import extract_api_consumers
 from contextor.core.errors import AnalysisCancelled, checkpoint
 from contextor.core.reference import (
@@ -251,7 +255,8 @@ def collect_module_artifacts(
             checkpoint(progress_callback, f"JSON: {module_id}", completed, total)
         return result, failures
 
-    with ProcessPoolExecutor(
+    with managed_process_pool(
+        ProcessPoolExecutor,
         initializer=_init_artifact_worker,
         initargs=(
             modules,
@@ -292,10 +297,7 @@ def collect_module_artifacts(
                     total,
                 )
             except AnalysisCancelled:
-                executor.shutdown(
-                    wait=False,
-                    cancel_futures=True,
-                )
+                terminate_process_pool(executor)
                 raise
 
     return result, failures
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 718d4b6..5ff9f4e 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -19,6 +19,10 @@ from concurrent.futures import ProcessPoolExecutor, as_completed
 from pathlib import Path
 
 from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.analysis.process_pool_lifecycle import (
+    managed_process_pool,
+    terminate_process_pool,
+)
 from contextor.core.analysis.lineage_extraction import (
     deserialize_extracted_lineage_source_facts,
     extract_lineage_source_facts,
@@ -909,7 +913,9 @@ def index_repository(
             automatic_test_dirs=automatic_test_dirs(),
         )
 
-    with ProcessPoolExecutor() as executor:
+    with managed_process_pool(
+        ProcessPoolExecutor,
+    ) as executor:
         futures = {
             executor.submit(_process_single_file, str(p), str(root_path)): p
             for p in files_to_process
@@ -954,7 +960,7 @@ def index_repository(
             try:
                 checkpoint(progress_callback, res["filename"], completed, total_files)
             except AnalysisCancelled:
-                executor.shutdown(wait=False, cancel_futures=True)
+                terminate_process_pool(executor)
                 raise
 
     emit_index_profile_evidence("process_pool")
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 0887237..eb5b708 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -21,6 +21,9 @@ from contextor.core.analysis.full_analysis_coordinator import (
     release_full_analysis,
     run_full_analysis_exclusive,
 )
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.live_state import (
     DesktopLiveEventFeed,
@@ -1261,6 +1264,18 @@ class ContextorGUI:
             # safe fallback for a task that ignores cooperative cancellation.
             full_analysis_done.wait(timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS)
 
+        terminate_active_process_pools(
+            timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS,
+        )
+
+        if (
+            full_analysis_done is not None
+            and not full_analysis_done.is_set()
+        ):
+            full_analysis_done.wait(
+                timeout=FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS
+            )
+
         if getattr(self, "_live_start_retry_after_id", None) is not None:
             if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                 try:
diff --git a/contextor/core/analysis/process_pool_lifecycle.py b/contextor/core/analysis/process_pool_lifecycle.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/analysis/process_pool_lifecycle.py
@@ -0,0 +1,172 @@
+from __future__ import annotations
+
+import os
+import threading
+import time
+from contextlib import contextmanager
+from typing import Any, Callable, Iterator
+
+
+_registry_lock = threading.RLock()
+_registry_pid = os.getpid()
+_active_executors: dict[int, Any] = {}
+
+
+def _ensure_process_local_registry_locked() -> None:
+    global _registry_pid
+
+    current_pid = os.getpid()
+    if current_pid == _registry_pid:
+        return
+
+    _active_executors.clear()
+    _registry_pid = current_pid
+
+
+def _register_executor(executor: Any) -> None:
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+        _active_executors[id(executor)] = executor
+
+
+def _unregister_executor(executor: Any) -> None:
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+        _active_executors.pop(id(executor), None)
+
+
+def active_process_pool_count() -> int:
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+        return len(_active_executors)
+
+
+@contextmanager
+def managed_process_pool(
+    executor_factory: Callable[..., Any],
+    *args: Any,
+    **kwargs: Any,
+) -> Iterator[Any]:
+    executor = executor_factory(*args, **kwargs)
+    _register_executor(executor)
+    try:
+        with executor as entered:
+            yield entered
+    finally:
+        _unregister_executor(executor)
+
+
+def _executor_processes(executor: Any) -> tuple[Any, ...]:
+    processes = getattr(executor, "_processes", None)
+    if not isinstance(processes, dict):
+        return ()
+    return tuple(
+        process
+        for process in processes.values()
+        if process is not None
+    )
+
+
+def _process_is_alive(process: Any) -> bool:
+    try:
+        return bool(process.is_alive())
+    except Exception:
+        return False
+
+
+def _join_process_until(
+    process: Any,
+    deadline: float,
+) -> None:
+    remaining = max(0.0, deadline - time.monotonic())
+    try:
+        process.join(timeout=remaining)
+    except Exception:
+        pass
+
+
+def terminate_process_pool(
+    executor: Any,
+    *,
+    timeout: float = 1.5,
+) -> int:
+    processes = _executor_processes(executor)
+
+    shutdown = getattr(executor, "shutdown", None)
+    if callable(shutdown):
+        try:
+            shutdown(
+                wait=False,
+                cancel_futures=True,
+            )
+        except TypeError:
+            try:
+                shutdown(wait=False)
+            except Exception:
+                pass
+        except Exception:
+            pass
+
+    targets = [
+        process
+        for process in processes
+        if _process_is_alive(process)
+    ]
+
+    for process in targets:
+        try:
+            process.terminate()
+        except Exception:
+            pass
+
+    deadline = time.monotonic() + max(0.0, timeout)
+    for process in targets:
+        _join_process_until(process, deadline)
+
+    survivors = [
+        process
+        for process in targets
+        if _process_is_alive(process)
+    ]
+
+    for process in survivors:
+        try:
+            kill = getattr(process, "kill", None)
+            if callable(kill):
+                kill()
+            else:
+                process.terminate()
+        except Exception:
+            pass
+
+    kill_deadline = time.monotonic() + max(0.0, timeout)
+    for process in survivors:
+        _join_process_until(process, kill_deadline)
+
+    return len(targets)
+
+
+def terminate_active_process_pools(
+    *,
+    timeout: float = 1.5,
+) -> int:
+    with _registry_lock:
+        _ensure_process_local_registry_locked()
+        executors = tuple(_active_executors.values())
+
+    terminated = 0
+    for executor in executors:
+        terminated += terminate_process_pool(
+            executor,
+            timeout=timeout,
+        )
+    return terminated
+
+
+__all__ = [
+    "active_process_pool_count",
+    "managed_process_pool",
+    "terminate_active_process_pools",
+    "terminate_process_pool",
+]
+
diff --git a/tests/test_process_pool_lifecycle.py b/tests/test_process_pool_lifecycle.py
new file mode 100644
--- /dev/null
+++ b/tests/test_process_pool_lifecycle.py
@@ -0,0 +1,188 @@
+from concurrent.futures import ProcessPoolExecutor
+from types import SimpleNamespace
+import threading
+import time
+
+import contextor.core.analysis.process_pool_lifecycle as lifecycle
+import contextor.ui.gui as gui_module
+
+
+def _sleep_worker(seconds):
+    time.sleep(seconds)
+    return seconds
+
+
+class _FakeProcess:
+    def __init__(self, *, survive_terminate=False):
+        self.alive = True
+        self.survive_terminate = survive_terminate
+        self.terminate_calls = 0
+        self.kill_calls = 0
+        self.join_calls = 0
+
+    def is_alive(self):
+        return self.alive
+
+    def terminate(self):
+        self.terminate_calls += 1
+        if not self.survive_terminate:
+            self.alive = False
+
+    def kill(self):
+        self.kill_calls += 1
+        self.alive = False
+
+    def join(self, timeout=None):
+        self.join_calls += 1
+
+
+class _FakeExecutor:
+    def __init__(self, processes=None):
+        self._processes = {
+            index: process
+            for index, process in enumerate(processes or ())
+        }
+        self.shutdown_calls = []
+
+    def __enter__(self):
+        return self
+
+    def __exit__(self, *_args):
+        return False
+
+    def shutdown(self, *, wait=True, cancel_futures=False):
+        self.shutdown_calls.append(
+            (wait, cancel_futures)
+        )
+
+
+def test_managed_process_pool_registry_is_process_local():
+    assert lifecycle.active_process_pool_count() == 0
+
+    with lifecycle.managed_process_pool(
+        _FakeExecutor,
+    ):
+        assert lifecycle.active_process_pool_count() == 1
+
+    assert lifecycle.active_process_pool_count() == 0
+
+
+def test_force_shutdown_terminates_then_kills_survivors():
+    normal = _FakeProcess()
+    stubborn = _FakeProcess(survive_terminate=True)
+    executor = _FakeExecutor([normal, stubborn])
+
+    terminated = lifecycle.terminate_process_pool(
+        executor,
+        timeout=0.01,
+    )
+
+    assert terminated == 2
+    assert executor.shutdown_calls == [
+        (False, True)
+    ]
+    assert normal.terminate_calls == 1
+    assert normal.kill_calls == 0
+    assert stubborn.terminate_calls == 1
+    assert stubborn.kill_calls == 1
+    assert not normal.is_alive()
+    assert not stubborn.is_alive()
+
+
+def test_real_process_pool_workers_are_force_terminated():
+    with lifecycle.managed_process_pool(
+        ProcessPoolExecutor,
+        max_workers=2,
+    ) as executor:
+        executor.submit(_sleep_worker, 60)
+        executor.submit(_sleep_worker, 60)
+
+        deadline = time.monotonic() + 5.0
+        processes = ()
+        while time.monotonic() < deadline:
+            raw = getattr(executor, "_processes", None)
+            if isinstance(raw, dict) and len(raw) == 2:
+                processes = tuple(raw.values())
+                if all(process.is_alive() for process in processes):
+                    break
+            time.sleep(0.02)
+
+        assert len(processes) == 2
+        assert all(
+            process.is_alive()
+            for process in processes
+        )
+        assert lifecycle.active_process_pool_count() == 1
+
+        terminated = lifecycle.terminate_active_process_pools(
+            timeout=2.0,
+        )
+
+        assert terminated == 2
+        assert all(
+            not process.is_alive()
+            for process in processes
+        )
+
+    assert lifecycle.active_process_pool_count() == 0
+
+
+def test_desktop_close_force_terminates_process_local_pools(
+    monkeypatch,
+):
+    calls = []
+    destroyed = []
+
+    monkeypatch.setattr(
+        gui_module,
+        "close_cmd_log",
+        lambda: None,
+    )
+    monkeypatch.setattr(
+        gui_module,
+        "save_state",
+        lambda **_kwargs: None,
+    )
+    monkeypatch.setattr(
+        gui_module,
+        "terminate_active_process_pools",
+        lambda *, timeout: calls.append(timeout) or 0,
+    )
+    monkeypatch.setattr(
+        gui_module,
+        "FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS",
+        0.01,
+    )
+
+    class _Root:
+        def geometry(self):
+            return "800x600+10+10"
+
+        def destroy(self):
+            destroyed.append(True)
+
+    class _Var:
+        def get(self):
+            return ""
+
+    controller = object.__new__(
+        gui_module.ContextorGUI
+    )
+    controller.root = _Root()
+    controller.theme_mode = "light"
+    controller.repo_path_var = _Var()
+    controller.layer_path_var = _Var()
+    controller.file_path_var = _Var()
+    controller.live_watchers = {}
+    controller.live_event_feeds = {}
+    controller.live_clients = {}
+    controller.live_client = None
+    controller._live_start_retry_after_id = None
+    controller._full_analysis_done = threading.Event()
+
+    gui_module.ContextorGUI.on_closing(controller)
+
+    assert calls == [0.01]
+    assert destroyed == [True]
+    assert controller._closing is True
+

## END_COMPLETE_DIFFS

## MUST_NOT_CHANGE_CONFIRMED

- `contextor/mcp_server.py`, `contextor/mcp_process_registry.py`, MCP analysis jobs/profile paths.
- LIVE authority/service shutdown, `_terminate_pid_tree`, external MCP roots, and runtime trace/recovery code.
- Any new MCP cleanup or LIVE service race design.

DIFFS=COMPLETE_CURRENT_WORKTREE_DIFF_INCLUDED
STATUS=STOP_AND_WAIT_FOR_PROCEDUJ

