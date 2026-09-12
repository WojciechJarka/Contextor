## FINAL_ATTRIBUTION_PROBE

## DISCOVERY_STATUS

TEMPORARY_DIAGNOSTIC PROBE IMPLEMENTED; CONTROL DESKTOP RUN NOT MEASURED.

No optimization, cache-semantic change, ProcessPoolExecutor change, lineage disablement, representation change, LIVE IPC change, watcher change, or runtime change was made.

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/symbol_engine/indexer.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 4f80382..279fd3b 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -263,6 +263,7 @@ def _initialize_repository_identity(repo_root: str | Path) -> PersistentIdentity

 def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
     """Materialize current index lineage from finalized active identities."""
+    lineage_materialization_started = time.monotonic()
     from contextor.core.analysis.lineage_materialization import (
         LineageResolutionContext,
         materialize_lineage_source_facts,
@@ -321,17 +322,28 @@ def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
         interface_descriptors={},
     )
     materialized_by_source = {}
+    materialize_calls_ms = 0.0
+    anchor_count = 0
+    flow_count = 0
+    surface_count = 0
+    descriptor_count = 0
     for source_key in sorted(extracted_by_source):
         extracted = extracted_by_source[source_key]
         if extracted.source_key != source_key:
             raise ValueError("Extracted lineage mapping key does not match its source key.")
+        materialize_started = time.monotonic()
         materialized = materialize_lineage_source_facts(extracted, resolution)
+        materialize_calls_ms += (time.monotonic() - materialize_started) * 1000.0
         if (
             materialized.manifest.source_key != extracted.source_key
             or materialized.manifest.source_fingerprint != extracted.source_fingerprint
         ):
             raise ValueError("Materialized lineage manifest does not match extracted source.")
         materialized_by_source[source_key] = materialized
+        anchor_count += len(materialized.anchors)
+        flow_count += len(materialized.flows)
+        surface_count += len(materialized.surfaces)
+        descriptor_count += len(materialized.interface_descriptors)

     missing_source_keys = eligible_source_keys - set(materialized_by_source)
     if missing_source_keys or getattr(index, "skipped", ()):
@@ -344,6 +356,21 @@ def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
     else:
         family_state = LineageFamilyStatus.FRESH.value

+    lineage_materialization_ms = (
+        time.monotonic() - lineage_materialization_started
+    ) * 1000.0
+    trace_event(
+        "ANALYSIS",
+        "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
+        elapsed_ms=lineage_materialization_ms,
+        operation="lineage_materialization",
+        result=(
+            f"materialize_calls_ms={materialize_calls_ms:.3f};"
+            f"sources={len(materialized_by_source)};anchors={anchor_count};"
+            f"flows={flow_count};surfaces={surface_count};"
+            f"descriptors={descriptor_count}"
+        ),
+    )
     return (
         dict(sorted(materialized_by_source.items())),
         family_state,
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 8735dc8..df741c0 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -14,6 +14,7 @@ import ast
 import dataclasses
 import os
 import re
+import time
 from concurrent.futures import ProcessPoolExecutor, as_completed
 from pathlib import Path

@@ -33,6 +34,7 @@ from contextor.core.domain.module import (
 from contextor.core.errors import AnalysisCancelled, checkpoint
 from contextor.core.paths import DEFAULT_IGNORED_DIRS
 from contextor.core.reference.index import extract_compact_reference_facts
+from contextor.core.runtime_trace import trace_event
 from contextor.core.source import (
     SourceError,
     parse_source,
@@ -328,6 +330,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             "test_facts": None,
             "test_facts_status": None,
             "lineage_facts": None,
+            "lineage_extract_ms": 0.0,
             "automatic_test_context_directory": (
                 str(path.parent)
                 if is_test_context_candidate(root_str, path)
@@ -336,11 +339,13 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             ),
         }
     tree = parsed_input.tree
+    lineage_extract_started = time.monotonic()
     lineage_facts = extract_lineage_source_facts(
         tree,
         source_key=source_key,
         source_fingerprint=parsed_input.source_fingerprint,
     )
+    lineage_extract_ms = (time.monotonic() - lineage_extract_started) * 1000.0

     # Próba odczytu z cache
     cache = _cache_manager(root_str)
@@ -536,6 +541,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
         "test_facts": test_facts,
         "test_facts_status": test_facts_status,
         "lineage_facts": lineage_facts,
+        "lineage_extract_ms": lineage_extract_ms,
         "automatic_test_context_directory": (
             str(path.parent)
             if test_candidate or path.parent == Path(root_str)
@@ -619,6 +625,8 @@ def index_repository(
     symbol_facts_by_module: dict[str, dict] = {}
     reference_facts_by_module: dict[str, dict] = {}
     lineage_facts_by_source: dict[str, ExtractedLineageSourceFacts] = {}
+    lineage_extract_sum_ms = 0.0
+    lineage_extract_slowest: list[tuple[float, str]] = []
     collision_facts_by_module: dict[str, list[dict]] = {}
     test_facts_by_path: dict[str, dict] = {}
     automatic_test_dir_entries: dict[Path, set[str]] = {root_path: set()}
@@ -636,6 +644,27 @@ def index_repository(
             for directory in sorted(automatic_test_dir_entries)
         }

+    def record_lineage_extract_timing(result: dict) -> None:
+        nonlocal lineage_extract_sum_ms
+        elapsed_ms = float(result.get("lineage_extract_ms", 0.0))
+        lineage_extract_sum_ms += elapsed_ms
+        lineage_extract_slowest.append((elapsed_ms, result["path"]))
+
+    def emit_lineage_extract_timing() -> None:
+        slowest = sorted(lineage_extract_slowest, reverse=True)[:10]
+        max_ms = slowest[0][0] if slowest else 0.0
+        top10 = ",".join(f"{path}:{elapsed_ms:.3f}" for elapsed_ms, path in slowest)
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_LINEAGE_EXTRACTION",
+            elapsed_ms=lineage_extract_sum_ms,
+            operation="lineage_extraction",
+            result=(
+                f"sum_ms={lineage_extract_sum_ms:.3f};max_ms={max_ms:.3f};"
+                f"files={len(lineage_extract_slowest)};top10={top10}"
+            ),
+        )
+
     ignored_dirs = set(DEFAULT_IGNORED_DIRS)

     if extra_ignored_dirs:
@@ -670,6 +699,7 @@ def index_repository(
     if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
         for path in files_to_process:
             res = _process_single_file(str(path), str(root_path))
+            record_lineage_extract_timing(res)
             if res["error"]:
                 line_number, column_number = _syntax_error_location(res["error"])
                 skipped.append(
@@ -702,6 +732,7 @@ def index_repository(
                 record_automatic_test_context_path(res)
             completed += 1
             checkpoint(progress_callback, res["filename"], completed, total_files)
+        emit_lineage_extract_timing()
         return RepositoryIndex(
             modules=modules,
             skipped=sorted(skipped, key=lambda item: item.path),
@@ -721,6 +752,7 @@ def index_repository(

         for future in as_completed(futures):
             res = future.result()
+            record_lineage_extract_timing(res)

             if res["error"]:
                 line_number, column_number = _syntax_error_location(res["error"])
@@ -760,6 +792,8 @@ def index_repository(
                 executor.shutdown(wait=False, cancel_futures=True)
                 raise

+    emit_lineage_extract_timing()
+
     return RepositoryIndex(
         modules=modules,
         skipped=sorted(skipped, key=lambda item: item.path),
```

## TEST_RESULT

```text
.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py contextor/core/api/facade.py
PASS

.\.venv\Scripts\python.exe -m pytest -q tests/test_full_analysis_lineage_materialization.py tests/analysis/test_lineage_materialization.py
18 passed in 4.15s

Initial attempted focused test path: tests/test_indexer.py
NOT FOUND — no test executed in that attempt.

git diff --check
Code changes: PASS.
```

## CONTROL_RUN_STATUS

BLOCKED BY DESKTOP AVAILABILITY.

The available desktop-control surface enumerated no native apps (apps=[]). No launcher path was assumed and no substitute CLI analysis was run, because the requested control is exactly one warmed Desktop full analysis after restart.

The code is ready for that one run. After Desktop is restarted and a single warmed full analysis completes, read these ANALYSIS events:

1. FULL_ANALYSIS_STAGE_END where stage=indexing
2. FULL_ANALYSIS_LINEAGE_EXTRACTION
3. FULL_ANALYSIS_STAGE_END where stage=canonical_materialization
4. FULL_ANALYSIS_LINEAGE_MATERIALIZATION
5. FULL_ANALYSIS_FACADE_END

## EVENT_READOUT

### FULL_ANALYSIS_LINEAGE_EXTRACTION

Fields:

- elapsed_ms: sum of worker-local extract_lineage_source_facts(...) durations.
- operation=lineage_extraction.
- result=sum_ms=...;max_ms=...;files=...;top10=path:ms,...

Interpretation: sum_ms is aggregate worker work, not parent indexing wall time under ProcessPoolExecutor. Compare it to FULL_ANALYSIS_STAGE_END(stage=indexing).elapsed_ms, but do not subtract it or treat it as a sequential share of indexing wall time. max_ms and top10 identify the longest individual extraction paths.

### FULL_ANALYSIS_LINEAGE_MATERIALIZATION

Fields:

- elapsed_ms: total wall time of _materialize_full_analysis_lineage.
- operation=lineage_materialization.
- result=materialize_calls_ms=...;sources=...;anchors=...;flows=...;surfaces=...;descriptors=...

Interpretation: materialize_calls_ms is the sum of only calls to materialize_lineage_source_facts; helper elapsed_ms minus materialize_calls_ms is attributable to helper setup, validation, and registry work. Both are contained inside existing canonical_materialization wall time and must not be added to it.

## REQUESTED_MEASUREMENT_OUTPUT

| Field | Status until the one Desktop run |
|---|---|
| INDEXING_TOTAL_MS | NOT_MEASURED — read FULL_ANALYSIS_STAGE_END(stage=indexing) |
| LINEAGE_EXTRACTION_WORKER_SUM_MS | NOT_MEASURED — read lineage extraction elapsed_ms |
| LINEAGE_EXTRACTION_MAX_MS | NOT_MEASURED — parse lineage extraction result.max_ms |
| LINEAGE_EXTRACTION_TOP10 | NOT_MEASURED — parse lineage extraction result.top10 |
| CANONICAL_MATERIALIZATION_TOTAL_MS | NOT_MEASURED — read FULL_ANALYSIS_STAGE_END(stage=canonical_materialization) |
| LINEAGE_MATERIALIZATION_HELPER_MS | NOT_MEASURED — read lineage materialization elapsed_ms |
| LINEAGE_MATERIALIZATION_CALLS_MS | NOT_MEASURED — parse materialize_calls_ms |
| LINEAGE_COUNTS | NOT_MEASURED — parse sources/anchors/flows/surfaces/descriptors |
| KNOWN_IPC_PAYLOAD_PENALTY_MS | ~13000 |

## ATTRIBUTION_RULES_AFTER_CONTROL_RUN

- Direct lineage materialization wall contribution is exactly FULL_ANALYSIS_LINEAGE_MATERIALIZATION.elapsed_ms; it is already within canonical materialization.
- Lineage extraction is reported as worker aggregate and per-file distribution. It cannot be converted to parent wall contribution from aggregate CPU/wall durations alone.
- The proven ~13000 ms payload penalty is independent wall cost across snapshot and publish transfers.
- Defensible lower-bound attribution after the run is: proven IPC payload penalty (~13000 ms) + direct materialization helper wall time. Do not add worker sum_ms to this bound.
- Remaining historical ~28 s unexplained is: ~28000 ms minus that lower bound, subject to historical baseline not having stage-level timing.

## NO_OPTIMIZATION_YET

The probe adds timing evidence only. Do not design a fix until the one Desktop run supplies the event values above.

## DIFFS

Only these production files changed for the temporary diagnostic probe:

- contextor/core/symbol_engine/indexer.py
- contextor/core/api/facade.py

walkthrough.md was updated as the report artifact.
