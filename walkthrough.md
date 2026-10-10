# L32H2F1_DIRECT_LIVE_IPC_WRITER_ADMISSION

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
- C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py

No production or test files outside the authorized allowlist changed. walkthrough.md is the requested report and is excluded from this source/test list.

## SOURCE_PREFLIGHT_REUSED

The task's completed preflight was reused. It had verified the insertion anchors and relevant consumers before this patch. Immediately before editing, source assertions were still true: direct _dispatch update_file lacked the mutation guard; queued execution already had its own guard; the production server supplied _repository_mutation_guard(root); acquire_full_analysis accepted timeout=0.0. No F2 or F3 work was authorized or performed.

The source/test working tree was clean before this task's edits; walkthrough.md already contained the prior task report. No HEAD or commit comparison was used.

Contextor post-edit retrieval returned complete implementations for CanonicalLiveServer._dispatch and _repository_mutation_guard, both workspace_sync=verified at canonical revision 254. The symbol response showed the new guards. Call context connected _serve_requests to _dispatch. The blast-radius tool reported zero direct consumers for dispatch; this is a static direct-consumer limitation because dispatch is entered through request serving/dynamic dispatch. The retrieved call context and current source establish that route.

## F1_RED_RESULT

Before either production edit, the three focused regressions were run against the old code. Result: 4 failed, 0 passed (the callback-exception regression is parametrized into two cases).

- test_direct_live_update_enters_guard_before_updater_and_persister: expected guard entry before callbacks; observed only updater then persister.
- test_direct_live_update_fails_fast_behind_cross_process_writer: the direct request returned status=ok while another process held the actual full-analysis OS lease.
- test_direct_live_update_releases_guard_after_callback_failure[updater] and [persister]: no guard enter/exit was observed.

These failures prove the direct synchronous route bypassed writer admission before the patch.

## F1_GREEN_RESULT

All new F1 regressions passed after the exact production changes. The focused existing compatibility, queueing, lease-exclusion, IPC, cancellation, persistence, and trace-field regressions passed. One additional compatibility test for a generic CanonicalLiveServer with no mutation_guard was run after reviewing the requested invariant; it passed.

Total targeted green executions reported below: 22 passed, 0 failed. No full repository suite was run.

## DIRECT_IPC_ADMISSION

CanonicalLiveServer._dispatch now uses the configured mutation guard around the direct update_file execution. When a server has no mutation guard, the previous direct execution path remains in place. _execute_update_file, _execute_queued_update_file, and CanonicalMutationCoordinator were not changed.

The runtime guard passes timeout=0.0 only for request.operation == "update_file". All other guarded operations pass timeout=None, retaining their prior waiting/cancellation behavior. The writer kind, cancellation callback, trace fields, and lease release implementation are unchanged.

## DIRECT_FAIL_FAST

The cross-process regression starts a second process that acquires the real full-analysis lease. While that OS lease is held, the real LiveStateClient.update_file request returns status=error in under one second. The updater and persister are not called; snapshot state and LIVE revision remain at their pre-request values. The request does not wait for the client timeout.

## DIRECT_IPC_RESPONSE_COMPATIBILITY

The post-release direct update succeeds over LiveStateClient.update_file. The test checks status=ok, revision, result, and seq fields and observes the updater and persister exactly once. The legacy activity_epoch field is also checked by the separate generic-server contract test. The contention test asserts the error status; it does not assert every error payload field, so only the tested status and the server's existing exception-to-error response handling are claimed here.

## QUEUED_MUTATION_COMPATIBILITY

The queued route remains independently guarded at its existing execution boundary. The existing queued admission tests verify guard entry before canonical execution and preservation of job identity/trace operation. The _repository_mutation_guard trace-fields test now explicitly checks timeout=None, so queued admission keeps its existing wait behavior. The changed direct _dispatch branch does not add a second queued guard.

## NO_DOUBLE_ACQUISITION

The successful direct update after contention uses the real production _repository_mutation_guard, which acquires the existing repository full-analysis lease. It completes the updater and persister and returns successfully. This exercises the direct path without a nested full-analysis acquisition or self-deadlock. The queued route remains covered by its existing single-boundary guard tests.

## CROSS_PROCESS_EXCLUSION

The exclusion regression uses multiprocessing spawn and an independently held OS lease, not an in-process mock. The competing lease causes immediate direct admission rejection. Once the holder releases the lease, a new direct request succeeds. No competing-process lease state was manipulated outside the isolated temporary repository.

## NO_DELAYED_MUTATION

After the rejected request, the test sends ping as a server-thread barrier, confirms the updater/persister call list is empty, releases the competing process, sends another ping barrier, and confirms the call list is still empty. A separate new request is then accepted. Thus the rejected synchronous request does not turn into delayed work after contention ends.

## FAILURE_AND_ROLLBACK_COMPATIBILITY

Updater and persister exception cases both return status=error, leave the observed LIVE revision at 0, and record guard enter followed by guard exit. Each case then reacquires and releases the repository lease, proving the lock was released. Existing selected persistence-failure and snapshot-conflict tests also passed. This report does not infer broader rollback guarantees beyond those assertions and the existing selected tests.

## TARGETED_TEST_RESULTS

All commands used the repository .venv Python. No full pytest run occurred.

RED command, before production edits:
tests/test_live_mutation_coordinator.py::test_direct_live_update_enters_guard_before_updater_and_persister
tests/test_live_mutation_coordinator.py::test_direct_live_update_fails_fast_behind_cross_process_writer
tests/test_live_mutation_coordinator.py::test_direct_live_update_releases_guard_after_callback_failure
Result: 4 failed as described under F1_RED_RESULT.

GREEN main focused command group: 18 passed:
- tests/test_live_mutation_coordinator.py::test_direct_live_update_enters_guard_before_updater_and_persister
- tests/test_live_mutation_coordinator.py::test_direct_live_update_fails_fast_behind_cross_process_writer
- tests/test_live_mutation_coordinator.py::test_direct_live_update_releases_guard_after_callback_failure (2 parametrized cases)
- tests/test_live_mutation_coordinator.py::test_queued_mutation_guard_receives_job_identity_and_trace_operation
- tests/test_live_mutation_coordinator.py::test_repository_mutation_guard_forwards_exact_admission_trace_fields
- tests/test_live_mutation_coordinator.py::test_generic_snapshot_failure_restores_committed_registry_and_old_canonical_state
- tests/test_live_mutation_coordinator.py::test_queued_executor_enters_mutation_guard_before_canonical_execution
- tests/test_live_mutation_coordinator.py::test_real_full_analysis_lease_blocks_worker_until_released
- tests/test_live_mutation_coordinator.py::test_coordinator_close_cancels_queued_not_active_job
- tests/test_live_mutation_coordinator.py::test_coordinator_close_reports_undrained_active_worker_then_drains
- tests/test_live_mutation_coordinator.py::test_publish_and_queued_update_are_single_writer_serialized
- tests/test_live_state_ipc.py::test_client_request_timeout_closes_connection
- tests/test_live_state_ipc.py::test_persistence_conflict_fails_closed_without_live_event
- tests/test_live_state_ipc.py::test_updater_failure_does_not_kill_the_service
- tests/test_live_state_ipc.py::test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients
- tests/test_full_analysis_coordination.py::test_live_mutation_admission_trace_fields_are_correlated_and_whitelisted
- tests/test_full_analysis_coordination.py::test_admission_cancellation_does_not_leak_locks

Additional focused command group: 3 passed:
- tests/test_live_mutation_coordinator.py::test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged
- tests/test_live_state_ipc.py::test_real_repository_persister_disk_ahead_fails_closed
- tests/test_full_analysis_coordination.py::test_cross_process_waiting_full_analysis_precedes_later_live_mutation

Additional generic-server compatibility test: 1 passed:
- tests/test_live_mutation_coordinator.py::test_legacy_update_file_contract_remains_synchronous_and_unchanged

Total: 22 passed, 0 failed across the targeted green commands.

py_compile passed for contextor/core/live_state/ipc.py, contextor/core/live_state/runtime.py, and tests/test_live_mutation_coordinator.py. git diff --check for those files passed. Git emitted only LF-to-CRLF advisory warnings for these working files; diff check found no whitespace errors.

No test was weakened. The new tests assert guard ordering, actual cross-process fail-fast, unchanged LIVE state on rejection, no delayed execution, callback exception release, and post-release success.

## ARCHITECTURAL_CYCLE_CHECK

Contextor's post-edit architecture summary reported cycles.count=0. The updated symbol retrieval was complete and workspace_sync=verified. No full repository analysis was run.

## SOURCE_SYNC

Contextor source retrieval marked both edited production owners workspace_sync=verified at revision 254. The watcher event query from revision 248 returned continuous events through revision 254 with resync_required=false and the same activity epoch 9e9a2a2edcb046bba00df0850244ad36:
- 249-251: test_live_mutation_coordinator.py watcher updates during test editing.
- 252: contextor/core/live_state/ipc.py UPDATED.
- 253: contextor/core/live_state/runtime.py UPDATED.
- 254: tests/test_live_mutation_coordinator.py UPDATED.

No manual Contextor update_file, restart, or full analysis was performed. Watcher/source synchronization does not establish that already-running MCP or LIVE processes imported the changed code.

## LIVE_REVISION_BEFORE_AFTER

Before patch: 248.
After the observed source/test watcher updates: 254.
Event history was continuous; resync_required=false. Activity epoch remained 9e9a2a2edcb046bba00df0850244ad36.

## REMAINING_F2_F3_RISKS

F2 registry-constructor synchronization and F3 migration coordination remain outside this authorization and were not changed or certified. This F1 result covers direct synchronous LIVE IPC update_file admission only.

## RESTART_REQUIRED

No process was restarted. For serving-process runtime certification of these MCP/LIVE code changes, a controlled manual restart/reload boundary remains required; source indexing and watcher events alone do not prove imported-code reload.

## FINAL_VERDICT

F1 exact patch and targeted regressions: PASS. Direct synchronous LIVE IPC update_file now enters the configured repository mutation guard and fails fast on full-analysis lease contention. Queued behavior and generic unguarded-server compatibility passed their targeted tests. No runtime reload certification is claimed. F2/F3 remain unresolved by scope.

## FULL_DIFFS

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py

diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 5f08eaf..ca89f1f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -2163,7 +2163,10 @@ class CanonicalLiveServer:
         if operation == "cancel_recovery_verification":
             return self._finish_recovery_verification(request, cancelled=True)
         if operation == "update_file":
-            return self._execute_update_file(request)
+            if self._mutation_guard is None:
+                return self._execute_update_file(request)
+            with self._mutation_guard(request, self._stop):
+                return self._execute_update_file(request)
         if operation == "publish":
             return self._execute_publish(request)

### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py

diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 992d25d..9cb2c40 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1287,6 +1287,11 @@ def _repository_mutation_guard(root: Path):
             root,
             owner="live_mutation_worker",
             writer_kind="live_mutation",
+            timeout=(
+                0.0
+                if request.get("operation") == "update_file"
+                else None
+            ),
             is_cancelled=stop_event.is_set,
             admission_trace_fields=admission_trace_fields,
         )

### C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py

diff --git a/tests/test_live_mutation_coordinator.py b/tests/test_live_mutation_coordinator.py
index 9f28934..4ec2e40 100644
--- a/tests/test_live_mutation_coordinator.py
+++ b/tests/test_live_mutation_coordinator.py
@@ -1,5 +1,6 @@
 import threading
 import time
+import multiprocessing
 from contextlib import contextmanager
 from types import SimpleNamespace
 
@@ -26,6 +27,32 @@ def _diagnostic_state():
     )
 
 
+def _hold_full_analysis_lease_process(repo_path, acquired, release, outcome):
+    from contextor.core.analysis.full_analysis_coordinator import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    lease = None
+    try:
+        lease = acquire_full_analysis(
+            repo_path,
+            owner="f1_cross_process_holder",
+            timeout=5.0,
+            poll_interval=0.01,
+        )
+        outcome.put("acquired")
+        acquired.set()
+        if not release.wait(timeout=10.0):
+            outcome.put("release_timeout")
+    except Exception as exc:
+        outcome.put(f"error:{type(exc).__name__}:{exc}")
+        acquired.set()
+    finally:
+        if lease is not None:
+            release_full_analysis(lease)
+
+
 @contextmanager
 def _running_server(server):
     thread = threading.Thread(target=server.serve_forever, daemon=True)
@@ -372,6 +399,7 @@ def test_repository_mutation_guard_forwards_exact_admission_trace_fields(
     assert repo_path == tmp_path
     assert kwargs["owner"] == "live_mutation_worker"
     assert kwargs["writer_kind"] == "live_mutation"
+    assert kwargs["timeout"] is None
     assert callable(kwargs["is_cancelled"])
     assert kwargs["is_cancelled"]() is False
     assert kwargs["admission_trace_fields"] == {
@@ -970,3 +998,168 @@ def test_coordinator_close_reports_undrained_active_worker_then_drains():
     release.set()
     assert coordinator.close(join_timeout=3.0) is True
     assert coordinator.status(accepted["job_id"])["state"] == "completed"
+
+
+def test_direct_live_update_enters_guard_before_updater_and_persister():
+    order = []
+
+    @contextmanager
+    def guard(request, _stop_event):
+        order.append(("guard_enter", request.get("operation")))
+        try:
+            yield
+        finally:
+            order.append(("guard_exit", request.get("operation")))
+
+    def updater(state, path):
+        order.append("updater")
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    def persister(_state, _revision):
+        order.append("persister")
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        persister=persister,
+        mutation_guard=guard,
+    )
+    with _running_server(server) as client:
+        response = client.update_file("guarded-direct.py", origin="test")
+
+    assert response["status"] == "ok"
+    assert order == [
+        ("guard_enter", "update_file"),
+        "updater",
+        "persister",
+        ("guard_exit", "update_file"),
+    ]
+
+
+def test_direct_live_update_fails_fast_behind_cross_process_writer(tmp_path):
+    import multiprocessing
+
+    from contextor.core.analysis.full_analysis_coordinator import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+    repo = tmp_path / "direct-live-repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+
+    context = multiprocessing.get_context("spawn")
+    acquired = context.Event()
+    release = context.Event()
+    outcome = context.Queue()
+    holder = context.Process(
+        target=_hold_full_analysis_lease_process,
+        args=(str(repo), acquired, release, outcome),
+    )
+    holder.start()
+    calls = []
+
+    def updater(state, path):
+        calls.append("updater")
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    def persister(_state, _revision):
+        calls.append("persister")
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        persister=persister,
+        mutation_guard=_repository_mutation_guard(repo),
+    )
+    try:
+        assert acquired.wait(timeout=8.0)
+        assert outcome.get(timeout=1.0) == "acquired"
+        with _running_server(server) as client:
+            started = time.monotonic()
+            rejected = client.update_file("blocked-direct.py", origin="mcp")
+            elapsed = time.monotonic() - started
+
+            assert rejected["status"] == "error"
+            assert elapsed < 1.0
+            assert calls == []
+            assert client.request("ping")["status"] == "ok"
+            before_release = client.snapshot()
+            assert before_release["revision"] == 0
+            assert before_release["state"].files == []
+
+            release.set()
+            holder.join(timeout=5.0)
+            assert not holder.is_alive()
+            assert holder.exitcode == 0
+
+            # A rejected synchronous call has no queued work to run after the
+            # competing process releases its OS lease; the subsequent ping is
+            # a server-thread barrier before this assertion.
+            assert client.request("ping")["status"] == "ok"
+            assert calls == []
+            after_release = client.update_file("allowed-direct.py", origin="mcp")
+            assert after_release["status"] == "ok"
+            assert after_release["revision"] == 1
+            assert set(after_release) >= {"status", "revision", "result", "seq"}
+            assert calls == ["updater", "persister"]
+    finally:
+        release.set()
+        holder.join(timeout=5.0)
+        if holder.is_alive():
+            holder.terminate()
+            holder.join(timeout=2.0)
+        server.close()
+
+
+@pytest.mark.parametrize("failure_stage", ["updater", "persister"])
+def test_direct_live_update_releases_guard_after_callback_failure(tmp_path, failure_stage):
+    from contextor.core.analysis.full_analysis_coordinator import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    repo = tmp_path / f"direct-failure-{failure_stage}"
+    repo.mkdir()
+    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+    PersistentIdentityRegistry(str(repo))
+    guard_calls = []
+    production_guard = _repository_mutation_guard(repo)
+
+    @contextmanager
+    def tracked_guard(request, stop_event):
+        guard_calls.append(("enter", request.get("operation")))
+        try:
+            with production_guard(request, stop_event):
+                yield
+        finally:
+            guard_calls.append(("exit", request.get("operation")))
+
+    def updater(state, path):
+        if failure_stage == "updater":
+            raise RuntimeError("updater failure")
+        state.files.append(path)
+        return {"status": "UPDATED", "file_path": path}
+
+    def persister(_state, _revision):
+        if failure_stage == "persister":
+            raise RuntimeError("persister failure")
+
+    server = CanonicalLiveServer(
+        SimpleNamespace(files=[], revision=0),
+        updater=updater,
+        persister=persister,
+        mutation_guard=tracked_guard,
+    )
+    with _running_server(server) as client:
+        response = client.update_file("callback-failure.py", origin="test")
+        assert response["status"] == "error"
+        assert client.snapshot()["revision"] == 0
+
+    assert guard_calls == [("enter", "update_file"), ("exit", "update_file")]
+    lease = acquire_full_analysis(repo, owner="after-direct-failure", timeout=0.5)
+    release_full_analysis(lease)
+
