## ACTUAL_DIFF

```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 90bb554..438ff44 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -794,7 +794,7 @@ class DesktopLiveWatcher:
                 )
             except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                 self._ambiguous_updates.add(path)
-                trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
+                trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
                 deferred.append(path)
                 continue
             job_id = response.get("job_id") if isinstance(response, dict) else None
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 5258ab0..0ccbddc 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -979,7 +979,9 @@ def test_lost_queued_update_ack_reuses_idempotency_key_and_runs_once(tmp_path):
         thread.join(timeout=2)


-def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(tmp_path):
+def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(
+    tmp_path, monkeypatch
+):
     update_started = threading.Event()
     release_first_update = threading.Event()
     update_calls = []
@@ -1011,11 +1013,28 @@ def test_lost_queued_update_ack_does_not_relabel_overlapping_edit(tmp_path):

     client.submit_update_file = lose_first_ack

+    trace_events = []
+
+    def capture_trace_event(component, event, **fields):
+        trace_events.append((component, event, fields))
+
+    monkeypatch.setattr(
+        "contextor.core.runtime_trace.trace_event",
+        capture_trace_event,
+    )

     try:
         source.write_text("VALUE = 2\n", encoding="utf-8")
         s1 = watcher._scan()[path]
         watcher._enqueue_path(path)
         assert watcher.poll_once() == []
+        ambiguous_events = [
+            fields
+            for component, event, fields in trace_events
+            if component == "LIVE" and event == "WATCH_UPDATE_AMBIGUOUS"
+        ]
+        assert len(ambiguous_events) == 1
+        assert ambiguous_events[0]["op"] == watcher._pending_intents[path].trace_op
         assert update_started.wait(timeout=2)

         intent = watcher._pending_intents[path]
 ```

## TEST_RESULT

`.\.venv\Scripts\python.exe -m pytest -q tests/test_live_watcher_startup_reconciliation.py -k "lost_queued_update_ack_does_not_relabel_overlapping_edit"`

`1 passed, 34 deselected in 1.85s`

`.\.venv\Scripts\python.exe -m py_compile contextor/core/live_state/watcher.py tests/test_live_watcher_startup_reconciliation.py` — PASS

`git diff --check` — PASS
