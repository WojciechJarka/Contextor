## ACTUAL_DIFF

Changed file: `contextor/core/analysis/full_analysis_coordinator.py`

```diff
diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index 6487d72..6d0cd31 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -20,6 +20,7 @@ from typing import Any, Callable
 from contextor.core.errors import AnalysisCancelled
 from contextor.core.paths import repo_cache_dir, repo_key
 from contextor.core.repository_identity import read_repository_identity
+from contextor.core.runtime_trace import trace_event


 @dataclass(frozen=True, slots=True)
@@ -294,6 +295,9 @@ def run_full_analysis_exclusive(
     Execute full repository analysis while holding an exclusive repository lease.
     Guarantees single-writer execution across Desktop, MCP, and CLI.
     """
+    repo = str(Path(path).resolve())
+    full_started = time.monotonic()
+    lease_wait_started = full_started
     lease = acquire_full_analysis(
         path,
         owner=owner,
@@ -302,8 +306,16 @@ def run_full_analysis_exclusive(
         log=log,
     )
     try:
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_LEASE_ACQUIRED",
+            owner=owner,
+            repo=repo,
+            wait_ms=(time.monotonic() - lease_wait_started) * 1000.0,
+        )
         if analysis_fn is not None:
-            return analysis_fn(
+            analysis_started = time.monotonic()
+            analysis_result = analysis_fn(
                 str(path),
                 log=log,
                 progress_callback=progress_callback,
@@ -311,14 +323,43 @@ def run_full_analysis_exclusive(
                 owner=owner,
                 **kwargs,
             )
-        from contextor.core.api.facade import ContextorFacade
-        return ContextorFacade.analyze_project(
-            str(path),
-            log=log,
-            progress_callback=progress_callback,
-            additional_excludes=additional_excludes,
+        else:
+            from contextor.core.api.facade import ContextorFacade
+
+            analysis_started = time.monotonic()
+            analysis_result = ContextorFacade.analyze_project(
+                str(path),
+                log=log,
+                progress_callback=progress_callback,
+                additional_excludes=additional_excludes,
+                owner=owner,
+                **kwargs,
+            )
+        analysis_ms = (time.monotonic() - analysis_started) * 1000.0
+        total_before_release_ms = (time.monotonic() - full_started) * 1000.0
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_BODY_END",
             owner=owner,
-            **kwargs,
+            repo=repo,
+            analysis_ms=analysis_ms,
+            total_before_release_ms=total_before_release_ms,
+            elapsed_ms=analysis_ms,
+            result=(
+                f"analysis_ms={analysis_ms:.3f};"
+                f"total_before_release_ms={total_before_release_ms:.3f}"
+            ),
         )
+        return analysis_result
     finally:
         release_full_analysis(lease)
+        total_ms = (time.monotonic() - full_started) * 1000.0
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_END",
+            owner=owner,
+            repo=repo,
+            total_ms=total_ms,
+            elapsed_ms=total_ms,
+            result=f"total_ms={total_ms:.3f}",
+        )
```

No changes were made to `watcher.py`, `ipc.py`, `runtime.py`, or `facade.py`.

## TEST_RESULT

```text
.\.venv\Scripts\python.exe -m py_compile contextor/core/analysis/full_analysis_coordinator.py
PASS

.\.venv\Scripts\python.exe -m pytest -q tests/test_full_analysis_coordination.py
8 passed in 9.29s

git diff --check
PASS
```

## MANUAL_TRACE_READOUT

After one Desktop full analysis, read these three `ANALYSIS` events from the active runtime JSONL:

1. `FULL_ANALYSIS_LEASE_ACQUIRED`: `wait_ms`.
2. `FULL_ANALYSIS_BODY_END`: `analysis_ms` and `total_before_release_ms` (also preserved in `result`; `elapsed_ms` equals `analysis_ms`).
3. `FULL_ANALYSIS_END`: `total_ms` (also preserved in `result`; `elapsed_ms` equals `total_ms`).

Interpretation:

- `wait_ms` near 28,000 ms with normal `analysis_ms` near 16,000 ms: delay occurs before facade, while acquiring `FullAnalysisLease`.
- `wait_ms` near zero with `analysis_ms` near 44,000 ms: delay occurs inside `ContextorFacade.analyze_project`.
- `total_ms - total_before_release_ms`: release/finalization time; it should remain small.
