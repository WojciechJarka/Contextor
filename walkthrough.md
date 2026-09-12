## ACTUAL_DIFF

Changed file: `contextor/core/api/facade.py`

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index c2ce409..4f80382 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -10,0 +11 @@ import os
+import time
@@ -21,0 +23 @@ from contextor.core.reference.index import assemble_reference_index_or_fallback
+from contextor.core.runtime_trace import trace_event
@@ -448,0 +451,14 @@ class ContextorFacade:
+        facade_started = time.monotonic()
+
+        def emit_stage_end(stage: str, started: float) -> None:
+            elapsed_ms = (time.monotonic() - started) * 1000.0
+            trace_event(
+                "ANALYSIS",
+                "FULL_ANALYSIS_STAGE_END",
+                stage=stage,
+                operation=stage,
+                elapsed_ms=elapsed_ms,
+                result=f"stage={stage};elapsed_ms={elapsed_ms:.3f}",
+            )
+
+        identity_and_setup_started = facade_started
@@ -459,0 +476,3 @@ class ContextorFacade:
+        emit_stage_end("identity_and_setup", identity_and_setup_started)
+
+        indexing_started = time.monotonic()
@@ -466,0 +486,4 @@ class ContextorFacade:
+
+        emit_stage_end("indexing", indexing_started)
+
+        reference_and_collision_started = time.monotonic()
@@ -481,0 +505,2 @@ class ContextorFacade:
+        emit_stage_end("reference_and_collision", reference_and_collision_started)
+
@@ -486,0 +512,2 @@ class ContextorFacade:
+
+        graph_started = time.monotonic()
@@ -496,0 +524,2 @@ class ContextorFacade:
+        emit_stage_end("graph", graph_started)
+
@@ -499,0 +529,2 @@ class ContextorFacade:
+
+        validation_started = time.monotonic()
@@ -507,0 +539,2 @@ class ContextorFacade:
+        emit_stage_end("validation", validation_started)
+
@@ -510,0 +544,2 @@ class ContextorFacade:
+
+        metrics_started = time.monotonic()
@@ -518,0 +554,2 @@ class ContextorFacade:
+        emit_stage_end("metrics", metrics_started)
+
@@ -522,0 +560,2 @@ class ContextorFacade:
+
+        reports_started = time.monotonic()
@@ -545,0 +585,2 @@ class ContextorFacade:
+        emit_stage_end("reports", reports_started)
+
@@ -550 +591 @@ class ContextorFacade:
-
+        canonical_materialization_started = time.monotonic()
@@ -552 +593 @@ class ContextorFacade:
-        [whitespace-only blank line]
+
@@ -709,0 +751,5 @@ class ContextorFacade:
+
+            emit_stage_end(
+                "canonical_materialization", canonical_materialization_started
+            )
+            persistence_started = time.monotonic()
@@ -726,0 +773,4 @@ class ContextorFacade:
+
+            emit_stage_end("persistence", persistence_started)
+
+            live_publish_started = time.monotonic()
@@ -759,8 +809,19 @@ class ContextorFacade:
-            if analysis_result is not None:
-                analysis_result.live_publish_status = live_publish_status
-                analysis_result.live_publish_revision = live_publish_revision
-                analysis_result.live_publish_warning = live_publish_warning
-                if hasattr(analysis_result, "summary_data") and isinstance(analysis_result.summary_data, dict):
-                    analysis_result.summary_data["live_publish_status"] = live_publish_status
-                    analysis_result.summary_data["live_publish_revision"] = live_publish_revision
-                    analysis_result.summary_data["live_publish_warning"] = live_publish_warning
+            emit_stage_end("live_publish", live_publish_started)
+
+        else:
+            emit_stage_end(
+                "canonical_materialization", canonical_materialization_started
+            )
+            skipped_stage_started = time.monotonic()
+            emit_stage_end("persistence", skipped_stage_started)
+            emit_stage_end("live_publish", time.monotonic())
+
+        finalize_started = time.monotonic()
+        if analysis_result:
+            analysis_result.live_publish_status = live_publish_status
+            analysis_result.live_publish_revision = live_publish_revision
+            analysis_result.live_publish_warning = live_publish_warning
+            if hasattr(analysis_result, "summary_data") and isinstance(analysis_result.summary_data, dict):
+                analysis_result.summary_data["live_publish_status"] = live_publish_status
+                analysis_result.summary_data["live_publish_revision"] = live_publish_revision
+                analysis_result.summary_data["live_publish_warning"] = live_publish_warning
@@ -769,0 +831,10 @@ class ContextorFacade:
+        emit_stage_end("finalize", finalize_started)
+
+        total_ms = (time.monotonic() - facade_started) * 1000.0
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_FACADE_END",
+            total_ms=total_ms,
+            elapsed_ms=total_ms,
+            result=f"total_ms={total_ms:.3f}",
+        )
```

No changes were made to watcher, IPC, runtime, or the full-analysis coordinator in this second probe.

## TEST_RESULT

```text
.\.venv\Scripts\python.exe -m py_compile contextor/core/api/facade.py
PASS

.\.venv\Scripts\python.exe -m pytest -q tests/test_facade_progress_staging.py tests/test_full_analysis_coordination.py
11 passed in 12.02s

git diff --check
PASS
```

## MANUAL_TRACE_READOUT

After one Desktop full analysis, collect all `ANALYSIS/FULL_ANALYSIS_STAGE_END` events and the final `ANALYSIS/FULL_ANALYSIS_FACADE_END` event.

`runtime_trace.trace_event` currently records the stage name in `operation` and in `result`; `elapsed_ms` is the stage duration. It records facade total in `FULL_ANALYSIS_FACADE_END.elapsed_ms` and `result=total_ms=...`.

Use the eleven stage names in this order:

1. `identity_and_setup`
2. `indexing`
3. `reference_and_collision`
4. `graph`
5. `validation`
6. `metrics`
7. `reports`
8. `canonical_materialization`
9. `persistence`
10. `live_publish`
11. `finalize`

Sum the eleven `elapsed_ms` values and compare against `FULL_ANALYSIS_FACADE_END.total_ms`. The small remainder is uninstrumented glue between stage boundaries and trace overhead. Any one stage above 50% of facade total is `NEXT_DRILLDOWN_TARGET`.
