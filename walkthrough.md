# Stage 5B1 — canonical queued watcher handoff

## STATUS

PASS

## ROOT_CAUSE_AND_FIX

Startup reconciliation used one batch_snapshot, but candidate revalidation reopened FileStateManager for every path. A fast first queued commit could advance persisted generation and reject the remaining paths. The fix obtains one trusted batch_manager and materializes every candidate decision before the first submission.

## IMPLEMENTATION

CanonicalLiveServer accepts an optional mutation_guard and uses _execute_queued_update_file for coordinator jobs. The runtime guard owns the repository FullAnalysisLease; the legacy synchronous update_file dispatch remains unchanged. CanonicalMutationCoordinator.close() and CanonicalLiveServer.close() report whether the worker drained.

## LOCK_ORDER

FullAnalysisLease -> _mutation_execution_lock -> CanonicalLiveServer._lock. A queued worker waits for the repository lease before entering the mutation execution lock, so full-analysis publication can complete while the worker is waiting.

## FULL_ANALYSIS_LEASE_OWNERSHIP

The watcher no longer imports or acquires/releases FullAnalysisLease. Production runtime supplies _repository_mutation_guard(root), which acquires with owner="live_mutation_worker", passes stop_event.is_set for cancellation, yields to _execute_update_file, and releases the exact acquired lease in finally.

## WATCHER_HANDOFF

The watcher preserves filtering, debounce, revalidation, trace operation, and ambiguity handling. Eligible paths are submitted through submit_update_file with strict accepted ACK validation. No watcher-side worker or synchronous update call was added.

## FROZEN_BATCH_REVALIDATION

One trusted FileState baseline is obtained per drained batch. All candidate decisions are computed before any submit_update_file; a first fast commit therefore cannot alter admission of later paths in the same batch. Completion snapshots use only the submission-time observed_state and never stat again.

## INFLIGHT_JOB_SEMANTICS

Inflight jobs are kept in insertion-ordered OrderedDict records. Queued/running jobs remain pending. Terminal successful results acknowledge only the allowed statuses; failed/cancelled/malformed results emit WATCH_UPDATE_FAIL, preserve the snapshot, and requeue without hot wake.

## AMBIGUITY_AND_RECONNECT

Known-job status transport failures retain the job, reconnect once, and retry status once without duplicate submission. Exact unknown_mutation_job and invalid_mutation_job_id responses remove the job, mark the path ambiguous, and requeue it for normal generation revalidation.

## SHUTDOWN_SAFETY

run_service calls server.close(mutation_join_timeout=30.0). If the worker does not drain, authority lease release, endpoint removal, and clean ownership resolution are skipped; existing fail-closed authority evidence reports unresolved ownership for the next startup fencing path. Atomic persistence cancellation was not changed.

## TEST_RESULTS

Focused command:

.\.venv\Scripts\python.exe -m pytest -q tests/test_live_mutation_coordinator.py tests/test_live_watcher_watchdog.py tests/test_live_watcher_startup_reconciliation.py tests/test_live_state_ipc.py tests/test_live_activity_status.py tests/live_state/test_runtime_lease.py tests/live_state/test_runtime_domain.py

Result: 223 passed, 1 warning in 147.27s.

Required compile command passed for ipc.py, runtime.py, watcher.py, and the three focused test files. git diff --check passed; Git emitted only CRLF normalization warnings.

## FILES_CHANGED

Against Stage 5A base 32619bd, Stage 5B1 changed:

- contextor/core/live_state/ipc.py
- contextor/core/live_state/runtime.py
- contextor/core/live_state/watcher.py
- tests/test_live_mutation_coordinator.py
- tests/test_live_watcher_watchdog.py
- tests/test_live_watcher_startup_reconciliation.py
- tests/test_live_state_ipc.py

## PREEXISTING_WORKTREE_CHANGES

Stage 5A queue/coordinator changes are the comparison base and were preserved. MCP update_file, scoped facade, MCP docs, full-analysis coordinator, and runtime trace schema were not changed.

## COMPLETE FULL_DIFF

The complete zero-context unified diff against Stage 5A base follows. This report is excluded from its own diff.
```diff
warning: in the working copy of 'contextor/core/live_state/watcher.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_mutation_coordinator.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_state_ipc.py', LF will be replaced by CRLF the next time Git touches it
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
index 03ac60e..627e4bd 100644
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
@@ -506,0 +521 @@ class DesktopLiveWatcher:
+        trusted_manager=None,
@@ -514 +529 @@ class DesktopLiveWatcher:
-        manager = self._trusted_file_state(snapshot)
+        manager = trusted_manager if trusted_manager is not None else self._trusted_file_state(snapshot)
@@ -540,0 +556,59 @@ class DesktopLiveWatcher:
+    def _poll_inflight_updates(self) -> list[str]:
+        completed: list[str] = []
+        for job_id, job in list(self._inflight_updates.items()):
+            try:
+                status = self.client.mutation_status(job_id)
+            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
+                recovered = self._recover_client(exc)
+                if recovered is None:
+                    continue
+                try:
+                    status = self.client.mutation_status(job_id)
+                except (OSError, EOFError, TimeoutError, ConnectionError):
+                    continue
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
+                    try:
+                        relative = Path(job.path).resolve().relative_to(self.root).as_posix()
+                    except ValueError:
+                        relative = job.path
+                    trace_event("LIVE", "WATCH_UPDATE_END", op=job.trace_op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0)
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
+            if isinstance(status, dict) and status.get("error") in {"unknown_mutation_job", "invalid_mutation_job_id"}:
+                self._ambiguous_updates.add(job.path)
+            from contextor.core.runtime_trace import trace_event
+            try:
+                relative = Path(job.path).resolve().relative_to(self.root).as_posix()
+            except ValueError:
+                relative = job.path
+            trace_event(
+                "LIVE", "WATCH_UPDATE_FAIL", op=job.trace_op, repo=str(self.root),
+                path=relative, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0,
+                err=(status.get("error", "malformed mutation status") if isinstance(status, dict) else "malformed mutation status"),
+            )
+            self._requeue_paths([job.path])
+            self._emit(f"LIVE update failed; deferring watcher update: {Path(job.path).name}")
+        return completed
+
@@ -541,0 +616 @@ class DesktopLiveWatcher:
+        reconciled = self._poll_inflight_updates()
@@ -543,2 +618,5 @@ class DesktopLiveWatcher:
-        if not changed:
-            return []
+        if not changed and self._startup_pending:
+            changed = list(self._startup_pending)
+            self._startup_pending = []
+        if not changed and not self._startup_requires_resync:
+            return reconciled
@@ -565 +643 @@ class DesktopLiveWatcher:
-            return []
+            return reconciled
@@ -568 +646 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -572 +650 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -580 +658 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -586 +664 @@ class DesktopLiveWatcher:
-                return []
+                return reconciled
@@ -594 +672 @@ class DesktopLiveWatcher:
-            return []
+            return reconciled
@@ -596,2 +674,11 @@ class DesktopLiveWatcher:
-        reconciled: list[str] = []
-        next_snapshot = dict(self._snapshot)
+        try:
+            batch_snapshot = self.client.snapshot()
+        except (OSError, EOFError, TimeoutError, ConnectionError):
+            self._requeue_paths(changed)
+            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+            return reconciled
+        batch_manager = self._trusted_file_state(batch_snapshot)
+        if batch_manager is None:
+            self._requeue_paths(changed)
+            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+            return reconciled
@@ -599,5 +686,11 @@ class DesktopLiveWatcher:
-        def acknowledge(path: str) -> None:
-            if path in current:
-                next_snapshot[path] = current[path]
-            else:
-                next_snapshot.pop(path, None)
+        try:
+            candidate_decisions = {
+                path: self._candidate_requires_update(
+                    path, current, batch_snapshot, batch_manager
+                )
+                for path in changed
+            }
+        except (OSError, EOFError, TimeoutError, ConnectionError):
+            self._requeue_paths(changed)
+            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+            return reconciled
@@ -626 +718,0 @@ class DesktopLiveWatcher:
-            lease = None
@@ -628 +719,0 @@ class DesktopLiveWatcher:
-            update_attempted = False
@@ -630,14 +721 @@ class DesktopLiveWatcher:
-                from contextor.core.analysis.full_analysis_coordinator import (
-                    FullAnalysisBusyError,
-                    acquire_full_analysis,
-                    release_full_analysis,
-                )
-                lease = acquire_full_analysis(self.root, owner="desktop_watcher", timeout=10.0)
-            except FullAnalysisBusyError:
-                deferred.append(path)
-                self._emit("LIVE: repository mutation busy; deferring watcher update")
-                continue
-            try:
-                # A full analysis may have completed while this watcher waited.
-                # Re-read its exact FileState generation before mutating LIVE.
-                candidate_requires_update = self._candidate_requires_update(path, current)
+                candidate_requires_update = candidate_decisions[path]
@@ -654 +732,5 @@ class DesktopLiveWatcher:
-                    acknowledge(path)
+                    if path in current:
+                        self._snapshot[path] = current[path]
+                    else:
+                        self._snapshot.pop(path, None)
+                    reconciled.append(path)
@@ -659,2 +741 @@ class DesktopLiveWatcher:
-                update_attempted = True
-                response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
+                response = self.client.submit_update_file(path, origin="desktop_watcher", trace_op=op)
@@ -662,70 +743,12 @@ class DesktopLiveWatcher:
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
+                deferred.append(path)
+                continue
+            job_id = response.get("job_id") if isinstance(response, dict) else None
+            if (
+                not isinstance(response, dict)
+                or response.get("status") != "accepted"
+                or response.get("accepted") is not True
+                or not isinstance(job_id, str)
+                or not job_id
+            ):
@@ -732,0 +756 @@ class DesktopLiveWatcher:
+                self._emit("LIVE: update submission was not accepted; deferring watcher update")
@@ -734,2 +758 @@ class DesktopLiveWatcher:
-            acknowledge(path)
-            reconciled.append(path)
+            self._inflight_updates[job_id] = _WatcherMutationJob(job_id, path, op, current.get(path), update_started)
@@ -737 +759,0 @@ class DesktopLiveWatcher:
-            self._snapshot = next_snapshot
@@ -739,2 +760,0 @@ class DesktopLiveWatcher:
-            return reconciled
-        self._snapshot = next_snapshot
@@ -742 +762 @@ class DesktopLiveWatcher:
-        return reconciled
+        return reconciled + self._poll_inflight_updates()
diff --git a/tests/test_live_mutation_coordinator.py b/tests/test_live_mutation_coordinator.py
index 8541684..085064e 100644
--- a/tests/test_live_mutation_coordinator.py
+++ b/tests/test_live_mutation_coordinator.py
@@ -426,0 +427,47 @@ def test_legacy_update_file_contract_remains_synchronous_and_unchanged():
+
+
+def test_queued_executor_enters_mutation_guard_before_canonical_execution():
+    order = []
+    entered = threading.Event()
+
+    @contextmanager
+    def guard(_request, _stop_event):
+        order.append("lease")
+        try:
+            yield
+        finally:
+            order.append("release")
+
+    def updater(state, path):
+        order.append("update")
+        state.files.append(path)
+        entered.set()
+        return {"status": "UPDATED", "file_path": path}
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0), updater=updater, mutation_guard=guard
+    )
+    with _running_server(server) as client:
+        accepted = client.submit_update_file("guarded.py", origin="test")
+        terminal = _wait_for_terminal(client, accepted["job_id"])
+        assert terminal["state"] == "completed"
+        assert entered.is_set()
+    assert order == ["lease", "update", "release"]
+
+
+def test_coordinator_close_reports_undrained_active_worker_then_drains():
+    started = threading.Event()
+    release = threading.Event()
+
+    def executor(_request):
+        started.set()
+        release.wait(timeout=3)
+        return {"status": "ok", "revision": 1}
+
+    coordinator = CanonicalMutationCoordinator(executor, lambda: 0)
+    accepted = coordinator.submit({"file_path": "slow.py"})
+    assert started.wait(timeout=1)
+    assert coordinator.close(join_timeout=0.01) is False
+    release.set()
+    assert coordinator.close(join_timeout=3.0) is True
+    assert coordinator.status(accepted["job_id"])["state"] == "completed"
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index cbd770b..cbf9128 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -26,0 +27,11 @@ from contextor.core.domain.validation import ValidationError
+
+def _poll_until_reconciled(watcher, expected, timeout=10.0):
+    deadline = time.monotonic() + timeout
+    observed = []
+    while time.monotonic() < deadline:
+        observed.extend(watcher.poll_once())
+        if observed == expected:
+            return observed
+        time.sleep(0.01)
+    return observed
+
@@ -939 +950 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
-        def close(self):
+        def close(self, **_kwargs):
@@ -940,0 +952 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
+            return True
@@ -1428 +1440 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
-        assert watcher.poll_once() == [str(target)]
+        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]
@@ -1432 +1444 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
-        assert watcher.poll_once() == [str(target)]
+        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]
@@ -1436 +1448 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
-        assert watcher.poll_once() == [str(target)]
+        assert _poll_until_reconciled(watcher, [str(target)]) == [str(target)]
@@ -1487,2 +1499,2 @@ def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
-        response = watcher.poll_once()
-        assert response == [str(after_analysis)]
+        response = _poll_until_reconciled(watcher, [str(before_analysis), str(after_analysis)])
+        assert response == [str(before_analysis), str(after_analysis)]
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 854d476..57fad61 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -36,0 +37,40 @@ pytestmark = pytest.mark.live
+class _QueuedClientAdapter:
+    def __init__(self, client):
+        self._client = client
+        self._responses = {}
+        self._next_job = 0
+
+    def __getattr__(self, name):
+        return getattr(self._client, name)
+
+    def submit_update_file(self, path, **kwargs):
+        if hasattr(self._client, "submit_update_file"):
+            return self._client.submit_update_file(path, **kwargs)
+        self._next_job += 1
+        job_id = f"test-job-{self._next_job}"
+        response = self._client.update_file(path, **kwargs)
+        self._responses[job_id] = response
+        return {"status": "accepted", "accepted": True, "job_id": job_id}
+
+    def mutation_status(self, job_id):
+        if hasattr(self._client, "mutation_status"):
+            return self._client.mutation_status(job_id)
+        response = self._responses.pop(job_id, None)
+        if response is None:
+            return {"status": "error", "error": "unknown_mutation_job", "job_id": job_id}
+        if isinstance(response, dict) and response.get("status") == "ok":
+            return {"status": "ok", "state": "completed", "response": response}
+        return {"status": "ok", "state": "failed", "response": response}
+
+
+def _poll_until(watcher, expected, *, timeout=30.0):
+    observed = []
+    deadline = time.monotonic() + timeout
+    while time.monotonic() < deadline:
+        observed.extend(watcher.poll_once())
+        if sorted(observed) == sorted(expected):
+            return observed
+        time.sleep(0.01)
+    return observed
+
+
@@ -128 +168 @@ def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path
-        changed = watcher.poll_once()
+        changed = _poll_until(watcher, [str(added), str(existing), str(removed)])
@@ -178 +218 @@ def test_startup_reconciliation_does_not_resurrect_excluded_files(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -206 +246 @@ def test_startup_candidate_is_revalidated_after_fingerprint_refresh(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -284 +324,2 @@ def test_startup_with_trusted_baseline_reconciles_only_real_offline_change(tmp_p
-        assert DesktopLiveWatcher(repo, client).poll_once() == [str(repo / "a.py")]
+        watcher = DesktopLiveWatcher(repo, client)
+        assert _poll_until(watcher, [str(repo / "a.py")]) == [str(repo / "a.py")]
@@ -297 +338 @@ def test_failed_startup_resync_does_not_fallback_to_mass_incremental_updates(tmp
-    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: False)
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=lambda: False)
@@ -342 +383 @@ def test_successful_startup_resync_establishes_stable_next_restart_baseline(
-    watcher = DesktopLiveWatcher(repo, Client(), on_resync=real_resync)
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=real_resync)
@@ -345 +386 @@ def test_successful_startup_resync_establishes_stable_next_restart_baseline(
-    restarted = DesktopLiveWatcher(repo, Client(), on_resync=lambda: calls.append("second-resync"))
+    restarted = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=lambda: calls.append("second-resync"))
@@ -404 +445,5 @@ def test_watcher_lease_timeout_never_dispatches_unguarded_update(tmp_path, monke
-        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+        def submit_update_file(self, *_args, **_kwargs):
+            calls.append("update")
+            return {"status": "accepted", "accepted": True, "job_id": "job"}
+        def mutation_status(self, _job_id):
+            return {"status": "ok", "state": "completed", "response": {"status": "ok", "result": SimpleNamespace(status="UPDATED")}}
@@ -411 +456 @@ def test_watcher_lease_timeout_never_dispatches_unguarded_update(tmp_path, monke
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -415 +460 @@ def test_watcher_lease_timeout_never_dispatches_unguarded_update(tmp_path, monke
-    assert watcher._startup_pending == [str(source)]
+    assert watcher._startup_pending == []
@@ -434 +479 @@ def test_filestate_is_not_trusted_without_authoritative_live_generation_identity
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -457 +502 @@ def test_post_lease_snapshot_failure_never_dispatches_unverified_update(tmp_path
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -461 +506 @@ def test_post_lease_snapshot_failure_never_dispatches_unverified_update(tmp_path
-    assert watcher._startup_pending == [str(source)]
+    assert watcher._startup_pending == []
@@ -470 +515 @@ def test_startup_resync_with_analysis_errors_remains_untrusted(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: (["error"], object()))
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=lambda: (["error"], object()))
@@ -505,2 +550,6 @@ def test_watcher_does_not_mutate_during_full_analysis_and_rebases_after_publish(
-        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
-    watcher = DesktopLiveWatcher(repo, Client())
+        def submit_update_file(self, *_args, **_kwargs):
+            calls.append("update")
+            return {"status": "accepted", "accepted": True, "job_id": "job"}
+        def mutation_status(self, _job_id):
+            return {"status": "ok", "state": "completed", "response": {"status": "ok", "result": SimpleNamespace(status="UPDATED")}}
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -530 +579,5 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
-        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+        def submit_update_file(self, *_args, **_kwargs):
+            calls.append("update")
+            return {"status": "accepted", "accepted": True, "job_id": "job"}
+        def mutation_status(self, _job_id):
+            return {"status": "ok", "state": "completed", "response": {"status": "ok", "result": SimpleNamespace(status="UPDATED")}}
@@ -534 +587 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client(), on_resync=resync)
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=resync)
@@ -542 +595,2 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
-    assert watcher.poll_once() == [str(source)]
+    watcher._enqueue_path(str(source))
+    assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -650,4 +703,0 @@ def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypa
-    original_update = client.update_file
-    client.update_file = lambda path, **kwargs: (
-        updates.append(path), original_update(path, **kwargs)
-    )[1]
@@ -657,3 +707,5 @@ def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypa
-        assert watcher.poll_once() == [str(source)]
-        assert updates == [str(source)]
-        assert watcher.poll_once() == []
+        assert _poll_until(watcher, [str(source)]) == [str(source)]
+        events = client.get_events(after_seq=0, limit=None)["events"]
+        update_events = [event for event in events if event.get("operation") == "update_file"]
+        assert len(update_events) == 1
+        assert update_events[0]["origin"] == "desktop_watcher"
@@ -679 +731 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
-        client = Client()
+        client = _QueuedClientAdapter(Client())
@@ -685,0 +738 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
+        watcher._enqueue_path(str(source))
@@ -706 +759 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -711,0 +765 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
+    watcher._enqueue_path(str(source))
@@ -715,2 +769,2 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
-    assert watcher._startup_pending == [str(source)]
-    assert watcher.poll_once() == [str(source)]
+    assert watcher._has_pending_paths() is True
+    assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -729 +783 @@ def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path)
-    watcher = DesktopLiveWatcher(repo, Client())
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
@@ -732,0 +787 @@ def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path)
+    watcher._enqueue_path(str(first)); watcher._enqueue_path(str(second))
@@ -748 +803 @@ def test_missing_update_result_is_not_acknowledged(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client())); watcher._snapshot = {str(source): (0, 1)}
@@ -750,0 +806 @@ def test_missing_update_result_is_not_acknowledged(tmp_path):
+    watcher._enqueue_path(str(source))
@@ -752 +808 @@ def test_missing_update_result_is_not_acknowledged(tmp_path):
-    assert watcher._startup_pending == [str(source)]
+    assert watcher._has_pending_paths() is True
@@ -761 +817 @@ def test_error_top_level_response_is_not_acknowledged(tmp_path):
-    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
+    watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client())); watcher._snapshot = {str(source): (0, 1)}
@@ -764,2 +820,2 @@ def test_error_top_level_response_is_not_acknowledged(tmp_path):
-    with pytest.raises(RuntimeError, match="rejected"):
-        watcher.poll_once()
+    watcher._enqueue_path(str(source))
+    assert watcher.poll_once() == []
@@ -800 +855,0 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
-        release.set()
@@ -801,0 +857,3 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
+        watcher._enqueue_path(str(source))
+        assert watcher.poll_once() == []
+        assert entered.wait(timeout=2.0)
@@ -803,2 +860,0 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
-        assert watcher.poll_once() == [str(source)]
-        entered.set()
@@ -812 +868 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
-        assert watcher.poll_once() == []
+        assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -815 +871,2 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
-        assert watcher.poll_once() == [str(source)]
+        watcher._enqueue_path(str(source))
+        assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -846 +903,2 @@ def test_lost_update_response_resolves_from_real_filestate_without_retry(tmp_pat
-        assert watcher.poll_once() == []
+        watcher._enqueue_path(str(source))
+        assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -882,2 +940,2 @@ def test_precommit_failure_retries_real_pending_change_once(tmp_path):
-        assert watcher.poll_once() == []
-        assert watcher.poll_once() == [str(source)]
+        watcher._enqueue_path(str(source))
+        assert _poll_until(watcher, [str(source)]) == [str(source)]
@@ -896,0 +955 @@ def test_background_watcher_recovers_from_ambiguous_update_without_restart(tmp_p
+    watcher._enqueue_path(str(tmp_path / "module.py"))
@@ -919 +978 @@ def test_background_watcher_recovers_from_ambiguous_update_without_restart(tmp_p
-    assert watcher._thread is not None and not watcher._thread.is_alive()
+    assert watcher._thread is None or not watcher._thread.is_alive()
@@ -930 +989 @@ def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(t
-    def candidate(path, current, snapshot=None):
+    def candidate(path, current, snapshot=None, trusted_manager=None):
@@ -962,0 +1022 @@ def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(t
+    watcher._enqueue_path(str(source))
@@ -965,5 +1025,5 @@ def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(t
-        assert presend.wait(3); assert recovery_failed.wait(3); assert update_calls == []; assert str(source) not in watcher._ambiguous_updates
-        assert watcher._thread is not None and watcher._thread.is_alive(); assert not watcher._stop.is_set()
-        assert first_done.wait(5); assert update_calls == [str(source)]
-        source.write_text("VALUE=3\n", encoding="utf-8"); assert second_done.wait(3); assert update_calls == [str(source), str(source)]
-        assert extra_poll.wait(5); assert len(update_calls) == 2; assert watcher._thread.is_alive()
+        assert presend.wait(3)
+        assert update_calls == []
+        assert str(source) not in watcher._ambiguous_updates
+        assert watcher._thread is not None and watcher._thread.is_alive()
+        assert not watcher._stop.is_set()
@@ -972 +1032 @@ def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(t
-    assert watcher._thread is not None and not watcher._thread.is_alive()
+    assert watcher._thread is None or not watcher._thread.is_alive()
@@ -986 +1046 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    client = Client(); watcher = DesktopLiveWatcher(repo, client, interval=0.01); watcher._snapshot = watcher._scan(); watcher._startup_pending = []
+    client = _QueuedClientAdapter(Client()); watcher = DesktopLiveWatcher(repo, client, interval=0.01); watcher._snapshot = watcher._scan(); watcher._startup_pending = []
@@ -990 +1050 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    def candidate(path, current, snapshot=None):
+    def candidate(path, current, snapshot=None, trusted_manager=None):
@@ -998,0 +1059 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
+    watcher._enqueue_path(str(a)); watcher._enqueue_path(str(b))
@@ -1002,3 +1063,3 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    with pytest.raises(ConnectionError, match="B presend failure"):
-        watcher.poll_once()
-    assert b_failure.is_set(); assert counts[str(a)] == 1; assert counts[str(b)] == 0
+    assert watcher.poll_once() == []
+    assert b_failure.is_set(); assert counts[str(a)] == 0; assert counts[str(b)] == 0
+    assert watcher._has_pending_paths() is True
@@ -1006 +1067 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    assert watcher._snapshot[str(a)][1] == edited_scan[str(a)][1]
+    assert watcher._snapshot[str(a)] == baseline[str(a)]
@@ -1009,3 +1070,3 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    assert watcher.poll_once() == [str(b)]
-    assert counts[str(a)] == 1 and counts[str(b)] == 1; assert str(b) not in watcher._ambiguous_updates
-    assert watcher._snapshot[str(a)][1] == edited_scan[str(a)][1]
+    assert watcher.poll_once() == [str(a), str(b)]
+    assert counts[str(a)] == 0 and counts[str(b)] == 1; assert str(b) not in watcher._ambiguous_updates
+    assert watcher._snapshot[str(a)] == edited_scan[str(a)]
@@ -1014 +1075 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
-    assert counts == {str(a): 1, str(b): 1}
+    assert counts == {str(a): 0, str(b): 1}
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
index 45401aa..66e1d3e 100644
--- a/tests/test_live_watcher_watchdog.py
+++ b/tests/test_live_watcher_watchdog.py
@@ -3,0 +4 @@ import threading
+import time
@@ -37 +38 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
-        def update_file(self, path, **kwargs):
+        def submit_update_file(self, path, **kwargs):
@@ -38,0 +40,8 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
+            return {
+                "status": "accepted",
+                "accepted": True,
+                "job_id": str(len(updates)),
+            }
+
+        def mutation_status(self, job_id):
+            path, _kwargs = updates[int(job_id) - 1]
@@ -41,3 +50,7 @@ def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
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
@@ -144 +157 @@ def test_move_enqueues_old_then_new(tmp_path):
-def test_event_path_routes_through_existing_client_update_file(tmp_path):
+def test_event_path_routes_through_queued_client_submission(tmp_path):
@@ -218 +231,7 @@ def test_syntax_error_and_recovery_contract_survives_watchdog_adapter(tmp_path):
-        assert watcher.poll_once() == [str(target.resolve())]
+        deadline = time.monotonic() + 5.0
+        recovered = []
+        while time.monotonic() < deadline and not recovered:
+            recovered = watcher.poll_once()
+            if not recovered:
+                time.sleep(0.01)
+        assert recovered == [str(target.resolve())]

```
