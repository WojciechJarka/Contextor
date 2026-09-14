# CPA3_STRUCTURED_LINEAGE_MATERIALIZATION_EVIDENCE

## STATUS

SUCCESS. Added structured fields to the existing FULL_ANALYSIS_LINEAGE_MATERIALIZATION event without changing materialization/reuse/reresolve logic or its existing result string.

## FILES_CHANGED

- contextor/core/api/facade.py
- contextor/core/runtime_trace.py
- tests/test_full_analysis_lineage_materialization.py
- tests/test_runtime_trace.py
- walkthrough.md (this report)

## IMPLEMENTATION

The existing event now has timing_semantics=critical_path_subphase_with_nested_components and structured reuse/reresolve/materialize counts, nested component timings, and materialized source/anchor/flow/surface/descriptor counts.

elapsed_ms remains full synchronous materialization-subphase wall time. reuse_gate_ms, reresolve_calls_ms, and materialize_calls_ms are nested components only and are not extra wall contributions. The pre-existing result string was not edited.

runtime_trace header and whitelist contain all structured fields; header ANALYSIS events now declares FULL_ANALYSIS_LINEAGE_MATERIALIZATION alongside FULL_ANALYSIS_INDEX_EVIDENCE.

## TESTS

Specified nodeids: 3 passed in 2.23s.

py_compile passed for facade.py, runtime_trace.py, and both changed test modules. git diff --check passed. No full analysis, benchmark, or full pytest ran.

## STRUCTURED_EVIDENCE

The focused reuse test verifies one captured event with:

- operation=lineage_materialization
- timing_semantics=critical_path_subphase_with_nested_components
- reuse_sources=1 and reresolve/materialize/fallback counts zero
- materialized counts matching the reused slice
- elapsed_ms and reuse_gate_ms non-negative
- reresolve_calls_ms and materialize_calls_ms zero

No result-string parsing is used by the test.

## CONTEXTOR_FLOW_VERIFY

Contextor shows _materialize_full_analysis_lineage has exactly one listed caller: ContextorFacade.analyze_project (direct, line 774). trace_event remains the canonical ordinary runtime-event append owner, with its existing indexed call graph. No parallel profiler/event lifecycle or altered materialize/reuse/reresolve path was introduced.

Contextor state reports canonical revision 1099 with workspace_sync=out_of_sync because the locally edited files diverge from its source snapshot. No analysis refresh was run.

## FULL_DIFFS

### contextor/core/api/facade.py

```diff
@@ FULL_ANALYSIS_LINEAGE_MATERIALIZATION
+        timing_semantics="critical_path_subphase_with_nested_components",
+        reuse_sources=reuse_sources,
+        reresolve_sources=reresolve_sources,
+        materialize_sources=materialize_sources,
+        reresolve_fallback_sources=reresolve_fallback_sources,
+        reuse_gate_ms=reuse_gate_ms,
+        reresolve_calls_ms=reresolve_calls_ms,
+        materialize_calls_ms=materialize_calls_ms,
+        lineage_sources=len(materialized_by_source),
+        lineage_anchors=anchor_count,
+        lineage_flows=flow_count,
+        lineage_surfaces=surface_count,
+        lineage_descriptors=descriptor_count,
```

### contextor/core/runtime_trace.py

```diff
@@ trace header fields
+ reuse_sources, reresolve_sources, materialize_sources,
+ reresolve_fallback_sources, reuse_gate_ms, reresolve_calls_ms,
+ materialize_calls_ms, lineage_sources, lineage_anchors, lineage_flows,
+ lineage_surfaces, lineage_descriptors
@@ ANALYSIS header events
+ FULL_ANALYSIS_LINEAGE_MATERIALIZATION
@@ trace_event whitelist
+ corresponding structured field mappings
```

### tests/test_full_analysis_lineage_materialization.py

```diff
+from contextor.core.runtime_trace import capture_trace_events
+def test_full_analysis_lineage_materialization_emits_structured_reuse_evidence():
+    # captures reused-slice event and asserts structured fields/counts/timings
```

### tests/test_runtime_trace.py

```diff
+    # requires all lineage materialization structured fields in header
+    # requires FULL_ANALYSIS_LINEAGE_MATERIALIZATION in ANALYSIS events
```

## COMMIT_SHA

d1e256eee5db641db3d4f9965666c0e0a71e169f (existing HEAD; no commit created).

## RUNTIME_RESTART_REQUIRED

YES. Reload active MCP only before later real CPA use. No MCP, Desktop, or LIVE restart was performed.

Awaiting proceduj.
