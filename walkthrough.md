# Stage 5B1 — partial handoff

## STATUS

PARTIAL / NOT CERTIFIED. Do not treat this worktree as a completed Stage 5B1 implementation.

## IMPLEMENTATION

The current diff adds the queued-worker mutation guard, drain-aware server close, and watcher-side submit/status handoff. `DesktopLiveWatcher` no longer acquires `FullAnalysisLease` directly.

## LOCK_ORDER

Queued execution enters the repository mutation guard before `_execute_update_file`, which retains ownership of `_mutation_execution_lock` and then `CanonicalLiveServer._lock`.

## FULL_ANALYSIS_LEASE_OWNERSHIP

The runtime guard acquires `FullAnalysisLease` with owner `live_mutation_worker` and releases that exact lease in `finally`.

## WATCHER_HANDOFF

Watcher paths are submitted through `submit_update_file`; completion is consumed from `mutation_status` and only terminal successful responses advance `_snapshot`.

## INFLIGHT_JOB_SEMANTICS

Jobs are insertion ordered by job id. Queued/running jobs remain inflight; transport failures retain known jobs; failed jobs are requeued; unknown jobs become ambiguous.

## AMBIGUITY_AND_RECONNECT

Submission transport errors add ambiguous state and defer revalidation. This area has not yet received the full required test matrix.

## SHUTDOWN_SAFETY

Coordinator close now returns whether its worker drained. Runtime leaves authority ownership unresolved if the worker did not drain.

## TEST_RESULTS

- `py_compile` for `ipc.py`, `runtime.py`, and `watcher.py`: PASS.
- `tests/test_live_watcher_watchdog.py`: `11 passed`.
- `tests/test_live_watcher_startup_reconciliation.py -x`: FAIL. Startup reconciliation currently exposes only `added.py` rather than the expected add/modify/delete batch; certification remains blocked.
- `git diff --check`: PASS (only CRLF informational warnings).

## FILES_CHANGED

- `contextor/core/live_state/ipc.py`
- `contextor/core/live_state/runtime.py`
- `contextor/core/live_state/watcher.py`
- `tests/test_live_watcher_watchdog.py`
- `tests/test_live_watcher_startup_reconciliation.py`

## PREEXISTING_WORKTREE_CHANGES

Stage 5A changes were present when this Stage 5B1 attempt started. This report supersedes the previous report but excludes its own diff.

## RAW_DIFFS

```diff
warning: in the working copy of 'contextor/core/live_state/ipc.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/runtime.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/watcher.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_watcher_startup_reconciliation.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_watcher_watchdog.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 6d4217e..bde92a7 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -283 +283 @@ class CanonicalMutationCoordinator:
-    def close(self, *, join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT) -> None:
+    def close(self, *, join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT) -> bool:
@@ -304,0 +305 @@ class CanonicalMutationCoordinator:
+        return thread is None or not thread.is_alive()
@@ -664,0 +666 @@ class CanonicalLiveServer:
+        mutation_guard: Callable[[Mapping[str, Any], threading.Event], Any] | None = None,
@@ -707,0 +710 @@ class CanonicalLiveServer:
+        self._mutation_guard = mutation_guard
@@ -709 +712 @@ class CanonicalLiveServer:
-            self._execute_update_file,
+            self._execute_queued_update_file,
@@ -1201,0 +1205,6 @@ class CanonicalLiveServer:
+    def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
+        if self._mutation_guard is None:
+            return self._execute_update_file(request)
+        with self._mutation_guard(request, self._stop):
+            return self._execute_update_file(request)
+
@@ -1629,8 +1638,9 @@ class CanonicalLiveServer:
-    def close(self) -> None:
-        if not self._stop.is_set():
-            self._stop.set()
-            try:
-                self._listener.close()
-            except OSError:
-                pass
-        self._mutation_coordinator.close()
+    def close(
+        self, *, mutation_join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT
+    ) -> bool:
+        self._stop.set()
+        try:
+            self._listener.close()
+        except OSError:
+            pass
+        return self._mutation_coordinator.close(join_timeout=mutation_join_timeout)
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 3d9c0d4..111ef30 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -5,0 +6 @@ import argparse
+import contextlib
@@ -1101,0 +1103,21 @@ def _repository_persister(root: Path, holder: dict[str, object] | None = None):
+def _repository_mutation_guard(root: Path):
+    @contextlib.contextmanager
+    def guard(_request: Mapping[str, Any], stop_event: threading.Event):
+        from contextor.core.analysis.full_analysis_coordinator import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        lease = acquire_full_analysis(
+            root,
+            owner="live_mutation_worker",
+            is_cancelled=stop_event.is_set,
+        )
+        try:
+            yield
+        finally:
+            release_full_analysis(lease)
+
+    return guard
+
+
@@ -1251,0 +1274 @@ def run_service(
+            mutation_guard=_repository_mutation_guard(root),
@@ -1394,0 +1418 @@ def run_service(
+        mutation_worker_drained = True
@@ -1396 +1420 @@ def run_service(
-            server.close()
+            mutation_worker_drained = server.close(mutation_join_timeout=30.0)
@@ -1399 +1423 @@ def run_service(
-        if lease is not None:
+        if lease is not None and mutation_worker_drained:
@@ -1457 +1481,5 @@ def run_service(
-                        else "authority shutdown could not resolve exact ownership"
+                        else (
+                            "queued mutation worker did not drain; ownership left for fencing"
+                            if not mutation_worker_drained
+                            else "authority shutdown could not resolve exact ownership"
+                        )
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 03ac60e..c702909 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -7 +7 @@ import time
-from collections import deque
+from collections import OrderedDict, deque
@@ -8,0 +9 @@ from collections.abc import Callable
+from dataclasses import dataclass
@@ -17,0 +19,9 @@ from .ipc import LiveStateClient
+@dataclass(frozen=True)
+class _WatcherMutationJob:
+    job_id: str
+    path: str
+    trace_op: str
+    observed_state: tuple[int, int] | None
+    started_at: float
+
+
@@ -122,0 +133 @@ class DesktopLiveWatcher:
+        self._inflight_updates: OrderedDict[str, _WatcherMutationJob] = OrderedDict()
@@ -264 +275 @@ class DesktopLiveWatcher:
-            if self._has_pending_paths():
+            if self._has_pending_paths() or self._has_inflight_updates():
@@ -418,0 +430,3 @@ class DesktopLiveWatcher:
+    def _has_inflight_updates(self) -> bool:
+        return bool(self._inflight_updates)
+
@@ -540,0 +555,39 @@ class DesktopLiveWatcher:
+    def _poll_inflight_updates(self) -> list[str]:
+        completed: list[str] = []
+        for job_id, job in list(self._inflight_updates.items()):
+            try:
+                status = self.client.mutation_status(job_id)
+            except (OSError, EOFError, TimeoutError, ConnectionError):
+                continue
+            state = status.get("state") if isinstance(status, dict) else None
+            if state in {"queued", "running"}:
+                continue
+            self._inflight_updates.pop(job_id, None)
+            if state == "completed":
+                response = status.get("response")
+                result = response.get("result") if isinstance(response, dict) else None
+                result_status = getattr(result, "status", None)
+                if isinstance(response, dict) and response.get("status") == "ok" and result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}:
+                    if job.observed_state is None:
+                        self._snapshot.pop(job.path, None)
+                    else:
+                        self._snapshot[job.path] = job.observed_state
+                    completed.append(job.path)
+                    from contextor.core.runtime_trace import trace_event
+                    trace_event("LIVE", "WATCH_UPDATE_END", op=job.trace_op, repo=str(self.root), path=Path(job.path).name, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0)
+                    if result_status == "SYNTAX_ERROR":
+                        line = getattr(result, "line_number", None)
+                        column = getattr(result, "column_number", None)
+                        position = f" line {line}, column {column}" if line and column else ""
+                        self._emit(f"LIVE syntax error: {Path(job.path).name}{position}: {getattr(result, 'error', 'syntax error')}")
+                    elif result_status == "RECOVERED":
+                        self._emit(f"LIVE syntax recovery: {Path(job.path).name}")
+                    else:
+                        self._emit(f"LIVE update successful: {Path(job.path).name}")
+                    continue
+            if state in {"invalid", "unknown"} or (isinstance(status, dict) and status.get("error") in {"unknown_job_id", "invalid_job_id"}):
+                self._ambiguous_updates.add(job.path)
+            self._requeue_paths([job.path])
+            self._emit(f"LIVE update failed; deferring watcher update: {Path(job.path).name}")
+        return completed
+
@@ -541,0 +595 @@ class DesktopLiveWatcher:
+        reconciled = self._poll_inflight_updates()
@@ -542,0 +597,3 @@ class DesktopLiveWatcher:
+        if not changed and self._startup_pending:
+            changed = list(self._startup_pending)
+            self._startup_pending = []
@@ -544 +601 @@ class DesktopLiveWatcher:
-            return []
+            return reconciled
@@ -565 +622 @@ class DesktopLiveWatcher:
-            return []
+            return reconciled
@@ -568 +625 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -572 +629 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -580 +637 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -586 +643 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -594 +651 @@ class DesktopLiveWatcher:
-            return []
+            return reconciled
@@ -596,8 +653,10 @@ class DesktopLiveWatcher:
-        reconciled: list[str] = []
-        next_snapshot = dict(self._snapshot)
-
-        def acknowledge(path: str) -> None:
-            if path in current:
-                next_snapshot[path] = current[path]
-            else:
-                next_snapshot.pop(path, None)
+        try:
+            batch_snapshot = self.client.snapshot()
+        except (OSError, EOFError, TimeoutError, ConnectionError):
+            self._requeue_paths(changed)
+            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+            return reconciled
+        if self._trusted_file_state(batch_snapshot) is None:
+            self._requeue_paths(changed)
+            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+            return reconciled
@@ -626 +684,0 @@ class DesktopLiveWatcher:
-            lease = None
@@ -628 +685,0 @@ class DesktopLiveWatcher:
-            update_attempted = False
@@ -630,4 +687,2 @@ class DesktopLiveWatcher:
-                from contextor.core.analysis.full_analysis_coordinator import (
-                    FullAnalysisBusyError,
-                    acquire_full_analysis,
-                    release_full_analysis,
+                candidate_requires_update = self._candidate_requires_update(
+                    path, current, batch_snapshot
@@ -635,9 +689,0 @@ class DesktopLiveWatcher:
-                lease = acquire_full_analysis(self.root, owner="desktop_watcher", timeout=10.0)
-            except FullAnalysisBusyError:
-                deferred.append(path)
-                self._emit("LIVE: repository mutation busy; deferring watcher update")
-                continue
-            try:
-                # A full analysis may have completed while this watcher waited.
-                # Re-read its exact FileState generation before mutating LIVE.
-                candidate_requires_update = self._candidate_requires_update(path, current)
@@ -654 +700,5 @@ class DesktopLiveWatcher:
-                    acknowledge(path)
+                    if path in current:
+                        self._snapshot[path] = current[path]
+                    else:
+                        self._snapshot.pop(path, None)
+                    reconciled.append(path)
@@ -659,2 +709 @@ class DesktopLiveWatcher:
-                update_attempted = True
-                response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
+                response = self.client.submit_update_file(path, origin="desktop_watcher", trace_op=op)
@@ -662,70 +711,2 @@ class DesktopLiveWatcher:
-                if update_attempted:
-                    self._ambiguous_updates.add(path)
-                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
-                    deferred.append(path)
-                    self._emit("LIVE: update outcome ambiguous; deferring revalidation")
-                    continue
-                self._emit("LIVE: connection lost during update; recovering...")
-                if self._recover_client(exc) is None:
-                    # Earlier candidates in this poll may already have received
-                    # an acknowledged canonical response.  Preserve those
-                    # per-path advances before surfacing the later pre-send
-                    # transport failure.
-                    self._snapshot = next_snapshot
-                    raise
-                try:
-                    recovered_snapshot = self.client.snapshot()
-                except (OSError, EOFError, TimeoutError, ConnectionError):
-                    deferred.append(path)
-                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
-                    continue
-                if self._trusted_file_state(recovered_snapshot) is None:
-                    deferred.append(path)
-                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
-                    continue
-                candidate_requires_update = self._candidate_requires_update(
-                    path, current, recovered_snapshot
-                )
-                if candidate_requires_update is None:
-                    deferred.append(path)
-                    if was_ambiguous:
-                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
-                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
-                    continue
-                if candidate_requires_update is False:
-                    if was_ambiguous:
-                        self._ambiguous_updates.discard(path)
-                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=False)
-                    acknowledge(path)
-                    continue
-                if was_ambiguous:
-                    self._ambiguous_updates.discard(path)
-                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=True)
-                update_attempted = True
-                response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
-            finally:
-                if lease is not None:
-                    release_full_analysis(lease)
-
-            if not isinstance(response, dict) or response.get("status") != "ok":
-                error = response.get("error", "update failed") if isinstance(response, dict) else "malformed update response"
-                trace_event("LIVE", "WATCH_UPDATE_FAIL", op=op, repo=str(self.root), path=relative, elapsed_ms=(time.monotonic() - update_started) * 1000.0, err=error)
-                self._emit(f"LIVE connection error: {error}")
-                raise RuntimeError(f"LIVE update failed for {path}: {error}")
-            result = response.get("result")
-            result_status = getattr(result, "status", None)
-            trace_event("LIVE", "WATCH_UPDATE_END", op=op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - update_started) * 1000.0)
-            acknowledged = result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}
-            if result_status == "SYNTAX_ERROR":
-                line = getattr(result, "line_number", None)
-                column = getattr(result, "column_number", None)
-                error = getattr(result, "error", "syntax error")
-                position = f" line {line}, column {column}" if line and column else ""
-                self._emit(f"LIVE syntax error: {Path(path).name}{position}: {error}")
-            elif result_status == "RECOVERED":
-                self._emit(f"LIVE syntax recovery: {Path(path).name}")
-            elif result_status in {"UPDATED", "DELETED", "UNCHANGED"}:
-                self._emit(f"LIVE update successful: {Path(path).name}")
-            else:
-                self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
-            if not acknowledged:
+                self._ambiguous_updates.add(path)
+                trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
@@ -734,2 +715,6 @@ class DesktopLiveWatcher:
-            acknowledge(path)
-            reconciled.append(path)
+            job_id = response.get("job_id") if isinstance(response, dict) else None
+            if not isinstance(response, dict) or response.get("accepted") is not True or not isinstance(job_id, str) or not job_id:
+                deferred.append(path)
+                self._emit("LIVE: update submission was not accepted; deferring watcher update")
+                continue
+            self._inflight_updates[job_id] = _WatcherMutationJob(job_id, path, op, current.get(path), update_started)
@@ -737 +721,0 @@ class DesktopLiveWatcher:
-            self._snapshot = next_snapshot
@@ -739,2 +722,0 @@ class DesktopLiveWatcher:
-            return reconciled
-        self._snapshot = next_snapshot
@@ -742 +724 @@ class DesktopLiveWatcher:
-        return reconciled
+        return reconciled + self._poll_inflight_updates()
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 854d476..0fa7222 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -36,0 +37,10 @@ pytestmark = pytest.mark.live
+def _poll_until(watcher, expected, *, attempts=40):
+    observed = []
+    for _ in range(attempts):
+        observed.extend(watcher.poll_once())
+        if sorted(observed) == sorted(expected):
+            return observed
+        time.sleep(0.01)
+    return observed
+
+
@@ -128 +138 @@ def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path
-        changed = watcher.poll_once()
+        changed = _poll_until(watcher, [str(added), str(existing), str(removed)])
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
index 45401aa..873400e 100644
--- a/tests/test_live_watcher_watchdog.py
+++ b/tests/test_live_watcher_watchdog.py
@@ -37 +37 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
-        def update_file(self, path, **kwargs):
+        def submit_update_file(self, path, **kwargs):
@@ -38,0 +39,8 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
+            return {
+                "status": "accepted",
+                "accepted": True,
+                "job_id": str(len(updates)),
+            }
+
+        def mutation_status(self, job_id):
+            path, _kwargs = updates[int(job_id) - 1]
@@ -41,3 +49,7 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
-                "revision": len(updates) + 1,
-                "seq": len(updates),
-                "result": SimpleNamespace(status=result_status, file_path=path),
+                "state": "completed",
+                "response": {
+                    "status": "ok",
+                    "revision": int(job_id) + 1,
+                    "seq": int(job_id),
+                    "result": SimpleNamespace(status=result_status, file_path=path),
+                },
@@ -144 +156 @@ def test_move_enqueues_old_then_new(tmp_path):
-def test_event_path_routes_through_existing_client_update_file(tmp_path):
+def test_event_path_routes_through_queued_client_submission(tmp_path):

```
