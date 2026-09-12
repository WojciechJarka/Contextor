## ACTUAL_DIFF

```diff
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 0ccbddc..a28f113 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -1004,14 +1004,14 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
     original_submit = client.submit_update_file
     attempts = []

-    def lose_first_ack(file_path, **kwargs):
+    def lose_first_two_acks(file_path, **kwargs):
         attempts.append((kwargs["idempotency_key"], kwargs["trace_op"]))
         response = original_submit(file_path, **kwargs)
-        if len(attempts) == 1:
+        if len(attempts) <= 2:
             raise ConnectionError("accepted response lost")
         return response

-    client.submit_update_file = lose_first_ack
+    client.submit_update_file = lose_first_two_acks

     trace_events = []

@@ -1028,13 +1028,6 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
         s1 = watcher._scan()[path]
         watcher._enqueue_path(path)
         assert watcher.poll_once() == []
-        ambiguous_events = [
-            fields
-            for component, event, fields in trace_events
-            if component == "LIVE" and event == "WATCH_UPDATE_AMBIGUOUS"
-        ]
-        assert len(ambiguous_events) == 1
-        assert ambiguous_events[0]["op"] == watcher._pending_intents[path].trace_op
         assert update_started.wait(timeout=2)

         intent = watcher._pending_intents[path]
@@ -1043,20 +1036,47 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
         assert len(server._mutation_coordinator._jobs) == 1
         assert not watcher._inflight_updates

+        frozen_retry_op = "FROZEN_RETRY_TRACE_OP"
+        assert frozen_retry_op != intent.trace_op
+
+        watcher._pending_intents[path] = _PendingMutationIntent(
+            idempotency_key=intent.idempotency_key,
+            path=intent.path,
+            trace_op=frozen_retry_op,
+            observed_state=intent.observed_state,
+            started_at=intent.started_at,
+        )
+        frozen_intent = watcher._pending_intents[path]
+
         source.write_text("VALUE = 3\n", encoding="utf-8")
         s2 = watcher._scan()[path]
         watcher._enqueue_path(path)
-        assert watcher._pending_intents[path] is intent
+        assert watcher._pending_intents[path] is frozen_intent
+        assert watcher.poll_once() == []

+        ambiguous_events = [
+            fields
+            for component, event, fields in trace_events
+            if component == "LIVE" and event == "WATCH_UPDATE_AMBIGUOUS"
+        ]
+        assert len(ambiguous_events) == 2
+        assert ambiguous_events[-1]["op"] == frozen_retry_op
+        assert ambiguous_events[-1]["op"] != intent.trace_op
+        assert attempts[1][0] == intent.idempotency_key
+        assert attempts[1][1] == frozen_retry_op
+
         assert watcher.poll_once() == []

-        assert attempts[1] == attempts[0]
+        assert attempts[0][0] == attempts[1][0] == attempts[2][0]
+        assert attempts[1][1] == frozen_retry_op
+        assert attempts[2][1] == frozen_retry_op
         assert len(server._mutation_coordinator._jobs) == 1
         job_id = server._mutation_coordinator._idempotency_jobs[attempts[0][0]]
         recovered_job = watcher._inflight_updates[job_id]
         assert recovered_job.observed_state == s1
         assert recovered_job.observed_state != s2
-        assert recovered_job.trace_op == intent.trace_op
-        assert recovered_job.started_at == intent.started_at
+        assert recovered_job.trace_op == frozen_retry_op
+        assert recovered_job.started_at == frozen_intent.started_at
         assert watcher._pending_intents.get(path) is None
         assert watcher._has_pending_paths()

@@ -1076,8 +1096,8 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
         assert len(update_calls) == 2
         assert watcher._snapshot[path] == s2
         assert len(server._mutation_coordinator._jobs) == 2
-        assert len(attempts) == 3
-        assert attempts[2][0] != attempts[0][0]
+        assert len(attempts) == 4
+        assert attempts[3][0] != attempts[0][0]
         assert len({key for key, _trace_op in attempts}) == 2
```

## TEST_RESULT

`.\.venv\Scripts\python.exe -m pytest -q tests/test_live_watcher_startup_reconciliation.py -k "lost_queued_update_ack_does_not_relabel_overlapping_edit"`

`1 passed, 34 deselected in 2.70s`

`.\.venv\Scripts\python.exe -m py_compile tests/test_live_watcher_startup_reconciliation.py` — PASS
