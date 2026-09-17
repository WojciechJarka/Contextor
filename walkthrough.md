# CPA10K6D1_WATCHER_IDENTITY_AUDIT_FIXES

STATUS=PASS

AUDIT_FIX_1=PASS
Restored `VALUE = 3\n` in `test_slow_inflight_update_does_not_spawn_competing_live_service` and changed only the second overlapping edit in `test_lost_queued_update_ack_does_not_relabel_overlapping_edit` to `VALUE = 33\n`. The existing `recovered_job.observed_state != s2` assertion is now deterministic at the stat-tuple level. The separate `test_same_stat_different_content_is_distinct_mutation_identity` remains unchanged and continues to use equal-size `VALUE = 2\n` / `VALUE = 3\n` with forced identical mtime.

AUDIT_FIX_2=PASS
After the existing SHA-bearing `get_current_file_state(path, compute_hash=True)` call, `poll_once` now performs a second stat-only `get_current_file_state(path, compute_hash=False)` call. The mutation identity is accepted only when both observations are present, the SHA is non-empty, and both stat tuples equal `current_state`; otherwise the existing defer/requeue path is used before any pending or inflight identity is created.

FILES_CHANGED=
- C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py
- C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py
- C:\Temp\Contextor_Repo\walkthrough.md

PRESERVED_PREEXISTING_UNCHANGED=
C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py was already modified by the preceding CPA10K6D task and was not modified in this correction, as explicitly required.

TARGETED_TESTS=
- `tests/test_live_watcher_startup_reconciliation.py::test_slow_inflight_update_does_not_spawn_competing_live_service`: PASS in the required targeted run.
- `tests/test_live_watcher_startup_reconciliation.py::test_lost_queued_update_ack_does_not_relabel_overlapping_edit`: PASS in the required targeted run.
- `tests/test_live_watcher_startup_reconciliation.py::test_same_stat_different_content_is_distinct_mutation_identity`: PASS in the required targeted run.
- `tests/test_live_watcher_startup_reconciliation.py::test_unstable_mutation_identity_capture_is_deferred`: PASS in the required targeted run.
- Targeted four-node invocation: `4 passed`.
- `tests/test_live_watcher_startup_reconciliation.py`: `37 passed`.

REPEATED_REGRESSIONS=
- Original overlap test: 5 fresh pytest invocations, PASS/PASS/PASS/PASS/PASS.
- Same-stat collision test: 5 fresh pytest invocations, PASS/PASS/PASS/PASS/PASS.
- The unstable-capture regression uses a deterministic manager double: the hash-bearing read returns generation A, the immediate stat-only read returns generation B, no submit occurs, `_pending_intents` and `_inflight_updates` remain empty, and the path is requeued.

FULL_SUITE_RUN=NO

MCP_SERVER_RESTART_REQUIRED=NO
No MCP server source was changed and no MCP restart or `update_file` was performed.

DESKTOP_RUNTIME_RESTART_REQUIRED=YES
`watcher.py` is production Desktop watcher code; a fresh Desktop watcher/runtime process is required to load this correction. No Desktop runtime restart was performed.

CONTEXTOR_FIRST_DISCOVERY=
- Before editing, `get_file_edit_context` resolved `contextor/core/live_state/watcher.py` as module `contextor.core.live_state.watcher`, module id `13/1`, and `tests/test_live_watcher_startup_reconciliation.py` as module id `98/1`; both had fresh syntax diagnostics with no errors.
- Before editing, Contextor blast-radius/consumer discovery identified the watcher module's direct consumers, including `contextor.core.live_state.__init__`, Desktop integration, startup reconciliation, watchdog, and runtime-authority tests.
- `get_symbol_call_context` confirmed `DesktopLiveWatcher._run_event_worker -> DesktopLiveWatcher.poll_once`, with `poll_once` calling `_scan`, `_candidate_requires_update`, `_poll_inflight_updates`, `_drain_pending`, `_requeue_paths`, `_trusted_file_state`, and the mutation submit path.
- `get_symbol_lineage` resolved `contextor.core.live_state.watcher::DesktopLiveWatcher.poll_once` as active artifact `A737/1` with complete canonical lineage sections.
- Contextor lookup confirmed the exact test identities for the slow-inflight, overlap, and same-stat collision regressions before editing.

POST_EDIT_CONTEXTOR=
- After editing, `get_file_edit_context` reported live revision `1314`, fresh canonical state, `syntax_diagnostics=checked_and_none`, zero syntax errors, zero name collisions, and zero cycles for `watcher.py`.
- Post-edit `get_symbol_call_context` returned the same canonical owner and 31-edge intra-module call neighborhood; no new consumer or architectural owner was introduced.
- Post-edit `get_symbol_lineage` remained resolved and metadata-consistent for `DesktopLiveWatcher.poll_once`.

DIRECT_EVIDENCE=
- Current literal verification shows the slow-inflight edit is `VALUE = 3\n`, the overlap's second edit is `VALUE = 33\n`, and the collision regression remains `VALUE = 2\n` followed by `VALUE = 3\n` plus `os.utime` to force the first mtime.
- The new unstable-capture test records `compute_hash` calls as `[True, False]`, returns a stat mismatch only on the second observation, observes no submission, observes no pending intent, observes no inflight job, and observes pending work after `poll_once`.
- `git diff --check` passed; only expected LF-to-CRLF conversion warnings were emitted by Git.
- No full repository pytest command was run.

IDENTITY_TOCTOU_TRANSITION=
The production transition is: scan produces `current_state` -> candidate is true -> existing FileStateManager hash-bearing read returns `file_state` -> existing FileStateManager stat-only read returns `post_hash_state` -> both tuples are checked against `current_state` -> only then can the code compare/join pending or inflight identity and submit. A mismatch or unusable value appends the path to `deferred`, emits `LIVE: mutation identity capture unavailable; deferring watcher update`, and continues without creating/relabeling an intent.

IMPLEMENTATION_SCOPE=
No new hash implementation, no `_scan` change, no SHA in `_snapshot`, no behavior redesign, and no modification to `tests/test_live_state_ipc.py` were made in this correction.

FULL_DIFFS=

## C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py

```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 438ff44..a5047d9 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -24,6 +24,7 @@ class _PendingMutationIntent:
     trace_op: str
     observed_state: tuple[int, int] | None
     started_at: float
+    observed_sha256: str | None = None


 @dataclass(frozen=True)
@@ -34,6 +35,7 @@ class _WatcherMutationJob:
     idempotency_key: str
     observed_state: tuple[int, int] | None
     started_at: float
+    observed_sha256: str | None = None


 class _PollingLiveWorker:
@@ -618,6 +620,7 @@ class DesktopLiveWatcher:
                         trace_op=job.trace_op,
                         observed_state=job.observed_state,
                         started_at=job.started_at,
+                        observed_sha256=job.observed_sha256,
                     ),
                 )
             from contextor.core.runtime_trace import trace_event
@@ -759,6 +762,39 @@ class DesktopLiveWatcher:
                     reconciled.append(path)
                     continue
                 current_state = current.get(path)
+                current_sha256: str | None = None
+                if current_state is not None:
+                    try:
+                        file_state = batch_manager.get_current_file_state(
+                            path, compute_hash=True
+                        )
+                        post_hash_state = batch_manager.get_current_file_state(
+                            path, compute_hash=False
+                        )
+                    except OSError:
+                        file_state = None
+                        post_hash_state = None
+                    if (
+                        file_state is None
+                        or (
+                            file_state.mtime_ns,
+                            file_state.size,
+                        )
+                        != current_state
+                        or not file_state.sha256
+                        or post_hash_state is None
+                        or (
+                            post_hash_state.mtime_ns,
+                            post_hash_state.size,
+                        )
+                        != current_state
+                    ):
+                        deferred.append(path)
+                        self._emit(
+                            "LIVE: mutation identity capture unavailable; deferring watcher update"
+                        )
+                        continue
+                    current_sha256 = file_state.sha256
                 pending_intent = self._pending_intents.get(path)
                 current_inflight = next(
                     (
@@ -766,6 +802,7 @@ class DesktopLiveWatcher:
                         for job in self._inflight_updates.values()
                         if job.path == path
                         and job.observed_state == current_state
+                        and job.observed_sha256 == current_sha256
                     ),
                     None,
                 )
@@ -781,6 +818,7 @@ class DesktopLiveWatcher:
                         trace_op=op,
                         observed_state=current_state,
                         started_at=update_started,
+                        observed_sha256=current_sha256,
                     )
                     self._pending_intents[path] = pending_intent
                 if was_ambiguous:
@@ -816,8 +854,12 @@ class DesktopLiveWatcher:
                 pending_intent.idempotency_key,
                 pending_intent.observed_state,
                 pending_intent.started_at,
+                pending_intent.observed_sha256,
             )
-            if current.get(path) != pending_intent.observed_state:
+            if (
+                current.get(path) != pending_intent.observed_state
+                or current_sha256 != pending_intent.observed_sha256
+            ):
                 deferred.append(path)
         if deferred:
             self._requeue_paths(deferred)
```

## C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py

```diff
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index a28f113..a209aaa 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -2,6 +2,7 @@ import json
 import os
 import threading
 import time
+from pathlib import Path
 from types import SimpleNamespace

 import pytest
@@ -590,7 +591,8 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
         return ([], object())
     watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()), on_resync=resync)
     watcher._startup_requires_resync = True
-    watcher._trusted_file_state = lambda _snapshot: object()
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager
     watcher._candidate_requires_update = lambda *_args: True
     assert watcher.poll_once() == []
     assert calls == []
@@ -736,7 +738,8 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
         watcher = DesktopLiveWatcher(repo, client)
         watcher._snapshot = {str(source): (0, 1)}
         source.write_text("VALUE = 2\n", encoding="utf-8")
-        watcher._trusted_file_state = lambda _snapshot: object()
+        manager = FileStateManager(str(repo_cache_dir(repo)))
+        watcher._trusted_file_state = lambda _snapshot: manager
         values = iter(candidate_values)
         watcher._candidate_requires_update = lambda *_args: next(values)
         watcher._enqueue_path(str(source))
@@ -764,7 +767,8 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
     watcher._snapshot = {str(source): (0, 1)}
     watcher._candidate_requires_update = lambda *_args: True
     source.write_text("VALUE = 2\n", encoding="utf-8")
-    watcher._trusted_file_state = lambda _snapshot: object()
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager
     watcher._candidate_requires_update = lambda *_args: True
     watcher._enqueue_path(str(source))

@@ -787,7 +791,8 @@ def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path)
     watcher._snapshot = {str(first): (0, 1), str(second): (0, 1)}
     first.write_text("A = 2\n", encoding="utf-8"); second.write_text("B = 2\n", encoding="utf-8")
-    watcher._trusted_file_state = lambda _snapshot: object()
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager
     watcher._enqueue_path(str(first)); watcher._enqueue_path(str(second))
     deferred = {str(second)}
     watcher._candidate_requires_update = lambda path, *_args: None if path in deferred else True
@@ -806,7 +811,8 @@ def test_missing_update_result_is_not_acknowledged(tmp_path)
     watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client())); watcher._snapshot = {str(source): (0, 1)}
     source.write_text("VALUE = 2\n", encoding="utf-8")
-    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager; watcher._candidate_requires_update = lambda *_args: True
     watcher._enqueue_path(str(source))
     assert watcher.poll_once() == []
     assert watcher._has_pending_paths() is True
@@ -820,7 +826,8 @@ def test_error_top_level_response_is_not_acknowledged(tmp_path)
     watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client())); watcher._snapshot = {str(source): (0, 1)}
     source.write_text("VALUE = 2\n", encoding="utf-8")
-    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: manager; watcher._candidate_requires_update = lambda *_args: True
     watcher._enqueue_path(str(source))
     assert watcher.poll_once() == []
     assert watcher._snapshot[str(source)] == (0, 1)
@@ -1045,10 +1052,11 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
             trace_op=frozen_retry_op,
             observed_state=intent.observed_state,
             started_at=intent.started_at,
+            observed_sha256=intent.observed_sha256,
         )
         frozen_intent = watcher._pending_intents[path]

-        source.write_text("VALUE = 3\n", encoding="utf-8")
+        source.write_text("VALUE = 33\n", encoding="utf-8")
         s2 = watcher._scan()[path]
         watcher._enqueue_path(path)
         assert watcher._pending_intents[path] is frozen_intent
@@ -1105,6 +1113,168 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
         thread.join(timeout=2)


+def test_same_stat_different_content_is_distinct_mutation_identity(
+    tmp_path,
+):
+    update_started = threading.Event()
+    release_first_update = threading.Event()
+    second_update_done = threading.Event()
+    update_contents = []
+    submitted_contents = {}
+    attempts = []
+
+    def updater(_state, path):
+        update_contents.append(Path(path).read_text(encoding="utf-8"))
+        if len(update_contents) == 1:
+            update_started.set()
+            assert release_first_update.wait(timeout=5)
+        else:
+            second_update_done.set()
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    repo, server, thread, _endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path, updater
+    )
+    source = repo / "module.py"
+    path = str(source)
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._snapshot = {path: (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: True
+    original_submit = client.submit_update_file
+
+    def capture_submit(file_path, **kwargs):
+        key = kwargs["idempotency_key"]
+        content = Path(file_path).read_text(encoding="utf-8")
+        attempts.append((key, content))
+        submitted_contents.setdefault(key, content)
+        response = original_submit(file_path, **kwargs)
+        if len(attempts) <= 2:
+            raise ConnectionError("accepted response lost")
+        return response
+
+    client.submit_update_file = capture_submit
+
+    try:
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        s1 = watcher._scan()[path]
+        state_manager = FileStateManager(str(repo_cache_dir(repo)))
+        sha1 = state_manager.get_current_file_state(
+            path, compute_hash=True
+        ).sha256
+
+        watcher._enqueue_path(path)
+        assert watcher.poll_once() == []
+        assert update_started.wait(timeout=2)
+        intent = watcher._pending_intents[path]
+        assert intent.observed_state == s1
+        assert intent.observed_sha256 == sha1
+
+        source.write_text("VALUE = 3\n", encoding="utf-8")
+        stat = source.stat()
+        os.utime(str(source), ns=(stat.st_atime_ns, s1[0]))
+        s2 = watcher._scan()[path]
+        sha2 = state_manager.get_current_file_state(
+            path, compute_hash=True
+        ).sha256
+
+        assert s2 == s1
+        assert sha2 != sha1
+        watcher._enqueue_path(path)
+        assert watcher.poll_once() == []
+        assert watcher._pending_intents[path] is intent
+        assert watcher._pending_intents[path].observed_state == s1
+        assert watcher._pending_intents[path].observed_sha256 == sha1
+
+        assert watcher.poll_once() == []
+        job_id = server._mutation_coordinator._idempotency_jobs[attempts[0][0]]
+        recovered_job = watcher._inflight_updates[job_id]
+        assert recovered_job.observed_state == s1 == s2
+        assert recovered_job.observed_sha256 == sha1
+        assert recovered_job.observed_sha256 != sha2
+        assert watcher._pending_intents.get(path) is None
+        assert watcher._has_pending_paths()
+
+        release_first_update.set()
+        deadline = time.monotonic() + 5
+        while time.monotonic() < deadline:
+            watcher.poll_once()
+            if (
+                len(submitted_contents) == 2
+                and second_update_done.is_set()
+                and not watcher._inflight_updates
+                and not watcher._has_pending_paths()
+            ):
+                break
+            threading.Event().wait(0.01)
+
+        assert len(submitted_contents) == 2
+        assert set(submitted_contents.values()) == {"VALUE = 2\n", "VALUE = 3\n"}
+        assert len(update_contents) == 2
+        assert not watcher._inflight_updates
+        assert not watcher._has_pending_paths()
+        assert watcher._snapshot[path] == s2
+    finally:
+        release_first_update.set()
+        server.close()
+        thread.join(timeout=2)


+def test_unstable_mutation_identity_capture_is_deferred(tmp_path, monkeypatch):
+    submissions = []
+
+    repo, server, thread, _endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path,
+        lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+    )
+    source = repo / "module.py"
+    path = str(source)
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    current_state = watcher._scan()[path]
+    generation_b = (current_state[0] + 1, current_state[1])
+    watcher._snapshot = {path: (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: True
+    state_manager = FileStateManager(str(repo_cache_dir(repo)))
+    watcher._trusted_file_state = lambda _snapshot: state_manager
+    state_reads = []
+
+    def unstable_state_read(file_path, compute_hash=False):
+        state_reads.append(compute_hash)
+        if compute_hash:
+            return SimpleNamespace(
+                mtime_ns=current_state[0],
+                size=current_state[1],
+                sha256="a" * 64,
+            )
+        return SimpleNamespace(
+            mtime_ns=generation_b[0],
+            size=generation_b[1],
+            sha256="",
+        )
+
+    def capture_submit(*args, **kwargs):
+        submissions.append((args, kwargs))
+        return {"status": "accepted", "accepted": True, "job_id": "unexpected"}
+
+    monkeypatch.setattr(
+        state_manager,
+        "get_current_file_state",
+        unstable_state_read,
+    )
+    monkeypatch.setattr(client, "submit_update_file", capture_submit)
+
+    try:
+        watcher._enqueue_path(path)
+        assert watcher.poll_once() == []
+        assert state_reads == [True, False]
+        assert submissions == []
+        assert watcher._pending_intents == {}
+        assert watcher._inflight_updates == {}
+        assert watcher._has_pending_paths()
+    finally:
+        server.close()
+        thread.join(timeout=2)


 def test_stale_unknown_intent_is_superseded_by_newer_current_inflight_job(tmp_path):
     submissions = []
     update_started = threading.Event()
@@ -1123,10 +1293,13 @@ def test_stale_unknown_intent_is_superseded_by_newer_current_inflight_job(tmp_pa

     source.write_text("VALUE = 10\n", encoding="utf-8")
     s1 = watcher._scan()[path]
+    state_manager = FileStateManager(str(repo_cache_dir(repo)))
+    sha1 = state_manager.get_current_file_state(path, compute_hash=True).sha256

     source.write_text("VALUE = 200\n", encoding="utf-8")
     s2 = watcher._scan()[path]
     assert s2 != s1
+    sha2 = state_manager.get_current_file_state(path, compute_hash=True).sha256

     watcher._snapshot = {path: s1}
     watcher._startup_pending = []
@@ -1140,6 +1313,7 @@ def test_stale_unknown_intent_is_superseded_by_newer_current_inflight_job(tmp_pa
         idempotency_key="old-k1",
         observed_state=s1,
         started_at=started_at,
+        observed_sha256=sha1,
     )
     watcher._inflight_updates["current-job"] = _WatcherMutationJob(
         job_id="current-job",
@@ -1148,6 +1322,7 @@ def test_stale_unknown_intent_is_superseded_by_newer_current_inflight_job(tmp_pa
         idempotency_key="current-k2",
         observed_state=s2,
         started_at=started_at,
+        observed_sha256=sha2,
     )

     original_status = client.mutation_status
```

The full diffs above are complete working-tree diffs for the two files changed in this correction scope; `tests/test_live_state_ipc.py` is intentionally excluded because it was not changed in CPA10K6D1.
