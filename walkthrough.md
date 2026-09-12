# Stage 5B1 — final stale pending-intent fix

## STATUS

PASS

## TEST_BEFORE_FIX_RESULT

The new regression failed before the production replacement. The stale `old-job` response created `_pending_intents[path]` for `old-k1`/S1, while the known `current-job` for S2 entered exact-state suppression without clearing that stale intent.

## IMPLEMENTATION

Applied only the specified watcher branch replacement. The branch now derives `current_state`, finds the exact matching inflight job, and, when present, clears any stale pending intent and `_ambiguous_updates` before suppressing the path. No coordinator, IPC, runtime, lease, shutdown, or FIFO code was changed.

## SUPERSESSION_PROOF

The real-server regression verifies that an unknown old job cannot leave K1 pending when a newer known inflight job owns S2. After S2 completes, a later S3 change submits a fresh key, produces a job with `observed_state=S3`, and reaches the final S3 watcher snapshot.

## TEST_RESULTS

Required command:

`.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_live_watcher_startup_reconciliation.py`

Result: `35 passed in 31.04s`.

Additional checks passed:

`.\\.venv\\Scripts\\python.exe -m py_compile contextor/core/live_state/watcher.py tests/test_live_watcher_startup_reconciliation.py`

`git diff --check`

## FILES_CHANGED

- `contextor/core/live_state/watcher.py`
- `tests/test_live_watcher_startup_reconciliation.py`

`ipc.py` and `runtime.py` were inspected and not changed.

## COMPLETE_FULL_DIFF

The following is the complete raw diff for every changed file in this task. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 182d382..90bb554 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -758,18 +758,28 @@ class DesktopLiveWatcher:
                         self._snapshot.pop(path, None)
                     reconciled.append(path)
                     continue
-                if any(
-                    job.path == path and job.observed_state == current.get(path)
-                    for job in self._inflight_updates.values()
-                ):
-                    continue
+                current_state = current.get(path)
                 pending_intent = self._pending_intents.get(path)
+                current_inflight = next(
+                    (
+                        job
+                        for job in self._inflight_updates.values()
+                        if job.path == path
+                        and job.observed_state == current_state
+                    ),
+                    None,
+                )
+                if current_inflight is not None:
+                    if pending_intent is not None:
+                        self._pending_intents.pop(path, None)
+                        self._ambiguous_updates.discard(path)
+                    continue
                 if pending_intent is None:
                     pending_intent = _PendingMutationIntent(
                         idempotency_key=uuid.uuid4().hex,
                         path=path,
                         trace_op=op,
-                        observed_state=current.get(path),
+                        observed_state=current_state,
                         started_at=update_started,
                     )
                     self._pending_intents[path] = pending_intent
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 8dcdd86..5258ab0 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -20,7 +20,11 @@ from contextor.core.live_state.runtime import (
     endpoint_file,
 )
 from contextor.core.live_state.store import save_snapshot
-from contextor.core.live_state.watcher import DesktopLiveWatcher
+from contextor.core.live_state.watcher import (
+    DesktopLiveWatcher,
+    _PendingMutationIntent,
+    _WatcherMutationJob,
+)
 from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
     PersistentIdentityRegistry,
@@ -1062,6 +1066,149 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(tmp_path):
         thread.join(timeout=2)


+def test_stale_unknown_intent_is_superseded_by_newer_current_inflight_job(tmp_path):
+    submissions = []
+    update_started = threading.Event()
+    release_update = threading.Event()
+
+    def updater(_state, path):
+        update_started.set()
+        assert release_update.wait(timeout=5)
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    repo, server, thread, _endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path, updater
+    )
+    source = repo / "module.py"
+    path = str(source)
+
+    source.write_text("VALUE = 10\n", encoding="utf-8")
+    s1 = watcher._scan()[path]
+
+    source.write_text("VALUE = 200\n", encoding="utf-8")
+    s2 = watcher._scan()[path]
+    assert s2 != s1
+
+    watcher._snapshot = {path: s1}
+    watcher._startup_pending = []
+    watcher._candidate_requires_update = lambda *_args: True
+
+    started_at = time.monotonic()
+    watcher._inflight_updates["old-job"] = _WatcherMutationJob(
+        job_id="old-job",
+        path=path,
+        trace_op="WATCH_MODIFY",
+        idempotency_key="old-k1",
+        observed_state=s1,
+        started_at=started_at,
+    )
+    watcher._inflight_updates["current-job"] = _WatcherMutationJob(
+        job_id="current-job",
+        path=path,
+        trace_op="WATCH_MODIFY",
+        idempotency_key="current-k2",
+        observed_state=s2,
+        started_at=started_at,
+    )
+
+    original_status = client.mutation_status
+    current_job_state = {"value": "running"}
+
+    def mutation_status(job_id):
+        if job_id == "old-job":
+            return {
+                "status": "error",
+                "error": "unknown_mutation_job",
+                "job_id": job_id,
+            }
+        if job_id == "current-job":
+            if current_job_state["value"] == "running":
+                return {
+                    "status": "ok",
+                    "state": "running",
+                    "job_id": job_id,
+                }
+            return {
+                "status": "ok",
+                "state": "completed",
+                "job_id": job_id,
+                "response": {
+                    "status": "ok",
+                    "revision": 1,
+                    "seq": 1,
+                    "result": SimpleNamespace(
+                        status="UPDATED",
+                        file_path=path,
+                    ),
+                },
+            }
+        return original_status(job_id)
+
+    original_submit = client.submit_update_file
+
+    def capture_submit(file_path, **kwargs):
+        submissions.append((file_path, dict(kwargs)))
+        return original_submit(file_path, **kwargs)
+
+    client.mutation_status = mutation_status
+    client.submit_update_file = capture_submit
+
+    try:
+        watcher._enqueue_path(path)
+
+        assert watcher.poll_once() == []
+
+        assert "old-job" not in watcher._inflight_updates
+        assert "current-job" in watcher._inflight_updates
+        assert path not in watcher._pending_intents
+        assert path not in watcher._ambiguous_updates
+        assert submissions == []
+
+        current_job_state["value"] = "completed"
+
+        completed = watcher.poll_once()
+        assert completed == [path]
+        assert watcher._snapshot[path] == s2
+        assert path not in watcher._pending_intents
+        assert path not in watcher._ambiguous_updates
+        assert not watcher._inflight_updates
+
+        source.write_text("VALUE = 3000\n", encoding="utf-8")
+        s3 = watcher._scan()[path]
+        assert s3 != s2
+
+        watcher._enqueue_path(path)
+        assert watcher.poll_once() == []
+        assert update_started.wait(timeout=2)
+
+        assert len(submissions) == 1
+        submitted_path, submitted_kwargs = submissions[0]
+        assert submitted_path == path
+        assert submitted_kwargs["idempotency_key"] not in {
+            "old-k1",
+            "current-k2",
+        }
+
+        real_job_id = next(iter(watcher._inflight_updates))
+        real_job = watcher._inflight_updates[real_job_id]
+        assert real_job.observed_state == s3
+        assert real_job.idempotency_key == submitted_kwargs["idempotency_key"]
+        assert real_job.idempotency_key != "old-k1"
+
+        release_update.set()
+        deadline = time.monotonic() + 5
+        while time.monotonic() < deadline and watcher._inflight_updates:
+            watcher.poll_once()
+            time.sleep(0.01)
+
+        assert watcher._snapshot[path] == s3
+        assert path not in watcher._pending_intents
+    finally:
+        release_update.set()
+        server.close()
+        thread.join(timeout=2)


 def test_precommit_failure_retries_real_pending_change_once(tmp_path):
     update_count = []
