# Walkthrough

VERDICT=FINAL_STATIC_PASS

CONTEXTOR_EVIDENCE

- Canonical LIVE revision 5468/5469 identified `DesktopLiveWatcher` at `contextor.core.live_state.watcher::DesktopLiveWatcher` and `connect_or_start` at `contextor.core.live_state.runtime::connect_or_start`; both were fresh and workspace-synchronized when fetched.
- `DesktopLiveWatcher.poll_once` retains candidate-local `update_attempted`, marks ambiguity only after dispatched-update transport loss, and preserves the established ambiguous-revalidation flow.
- `connect_or_start` remained unchanged. No canonical revision, activity epoch/sequence, FileState trust, or full-analysis reset contract was changed.

EXACT_TEST_1=PASS
COMMAND=pytest -q tests/test_live_watcher_startup_reconciliation.py::test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker -vv
RESULT=1 passed

EXACT_TEST_2=PASS
COMMAND=pytest -q tests/test_live_watcher_startup_reconciliation.py::test_update_attempted_flag_is_path_local_for_multiple_candidates -vv
RESULT=1 passed

IMMEDIATE_RECOVERY_AFTER_PRESEND=FAILED_ONCE
UPDATE_COUNT_AFTER_FAILED_POLL=0
NEXT_AUTOMATIC_POLL_RECONCILES=YES
FIRST_DONE_AFTER_REAL_UPDATE_RETURN=YES
SECOND_DONE_AFTER_REAL_UPDATE_RETURN=YES
FIRST_UPDATE_COUNT=1
SECOND_UPDATE_COUNT=2
POST_SECOND_AUTOMATIC_POLL_DUPLICATE=0

PATH_A_BASELINE_ADVANCED_AFTER_FIRST_POLL=YES
PATH_B_BASELINE_RETAINED_AFTER_FAILURE=YES
PATH_B_FALSE_AMBIGUOUS=0
PATH_A_REPLAY_AFTER_B_FAILURE=0
PATH_B_FINAL_UPDATE_COUNT=1
FINAL_QUIESCENT_POLL=PASS

PATH_LOCAL_PROOF

- Baseline snapshots: `a.py=(mtime_ns, 5)`, `b.py=(mtime_ns, 5)` for `A=1\n` and `B=1\n`.
- Edited scan snapshots: `a.py=(mtime_ns, 9)`, `b.py=(mtime_ns, 9)` for `A=22222\n` and `B=22222\n`.
- The test asserts the byte-size field differs before polling, A advances to the edited scan after its acknowledged update, B retains its complete old baseline after its pre-send failure, then B alone advances on the recovered second poll.
- The production fix persists `next_snapshot` before propagating an unrecoverable later pre-send failure, so an earlier acknowledged sibling is not replayed.

WATCHER_GATE=ALL_PASS
COMMAND=pytest -q tests/test_live_watcher_startup_reconciliation.py
RESULT=31 passed

FULL_IPC_GATE=ALL_PASS
COMMAND=pytest -q tests/test_live_state_ipc.py
RESULT=42 passed

H3A_RESULT=27_PASSED
COMMAND=pytest -q tests/test_h3a_workspace_canonical_freshness.py
RESULT=27 passed

PRODUCTION_CODE_CHANGED=YES
FILES_CHANGED

- contextor/core/live_state/watcher.py
- tests/test_live_watcher_startup_reconciliation.py

```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index ae728c0..1a5dfbd 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -375,6 +375,11 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     continue
                 self._emit("LIVE: connection lost during update; recovering...")
                 if self._recover_client() is None:
+                    # Earlier candidates in this poll may already have received
+                    # an acknowledged canonical response.  Preserve those
+                    # per-path advances before surfacing the later pre-send
+                    # transport failure.
+                    self._snapshot = next_snapshot
                     raise
                 try:
                     recovered_snapshot = self.client.snapshot()
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 0f6f8d3..854d476 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -952,8 +952,12 @@ def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(t
     watcher._recover_client = recover_once
     def update(path, **kwargs):
         update_calls.append(path)
-        (first_done if len(update_calls) == 1 else second_done).set()
-        return original_update(path, **kwargs)
+        result = original_update(path, **kwargs)
+        if len(update_calls) == 1:
+            first_done.set()
+        elif len(update_calls) == 2:
+            second_done.set()
+        return result
     client.update_file = update
     source.write_text("VALUE=2\\n", encoding="utf-8")
@@ -991,10 +995,10 @@ def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
         return path == str(a) and candidate_calls[path] == 1 or path == str(b)
     watcher._candidate_requires_update = candidate
     watcher._recover_client = lambda: None
-    a.write_text("A=2\\n", encoding="utf-8"); b.write_text("B=2\\n", encoding="utf-8")
+    a.write_text("A=22222\\n", encoding="utf-8"); b.write_text("B=22222\\n", encoding="utf-8")
     edited_scan = watcher._scan()
-    assert edited_scan[str(a)] != baseline[str(a)]
-    assert edited_scan[str(b)] != baseline[str(b)]
+    assert baseline[str(a)][1] != edited_scan[str(a)][1]
+    assert baseline[str(b)][1] != edited_scan[str(b)][1]
     with pytest.raises(ConnectionError, match="B presend failure"):
         watcher.poll_once()
     assert b_failure.is_set(); assert counts[str(a)] == 1; assert counts[str(b)] == 0
```
