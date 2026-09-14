# CPA4_CRITICAL_PATH_STRUCTURED_EVIDENCE

## STATUS

SUCCESS. Existing critical-path events now carry structured timing semantics, and focused evidence proves one trace_operation scopes coordinator-side ANALYSIS events. No profiler or event lifecycle was added.

## FILES_CHANGED

- contextor/core/api/facade.py
- contextor/core/analysis/full_analysis_coordinator.py
- contextor/core/runtime_trace.py
- tests/test_runtime_trace.py
- tests/test_full_analysis_coordination.py
- walkthrough.md (this report)

## IMPLEMENTATION

- FULL_ANALYSIS_STAGE_END now has timing_semantics=critical_path_stage.
- FULL_ANALYSIS_LEASE_ACQUIRED now has timing_semantics=critical_path_lease_wait.
- FULL_ANALYSIS_BODY_END now has timing_semantics=critical_path_analysis_body.
- FULL_ANALYSIS_END now has timing_semantics=critical_path_total.
- runtime_trace header/whitelist now supports stage, analysis_ms, total_before_release_ms, and total_ms. Header documents overlap/non-additivity of coordinator totals.
- Header ANALYSIS events now declares FULL_ANALYSIS_STAGE_END.
- Existing result strings and coordinator acquire/release ordering are unchanged.

## TESTS

Specified nodeids: 3 passed in 2.04s.

py_compile passed for all five changed Python files. git diff --check passed. No full analysis, benchmark, or full pytest ran.

## CRITICAL_PATH_CONTRACT

| Event / fields | Meaning |
| --- | --- |
| FULL_ANALYSIS_STAGE_END.elapsed_ms | one synchronous facade stage wall; critical_path_stage |
| FULL_ANALYSIS_LEASE_ACQUIRED.wait_ms | lease wait; critical_path_lease_wait |
| FULL_ANALYSIS_BODY_END.analysis_ms and elapsed_ms | same analysis-body interval; critical_path_analysis_body |
| FULL_ANALYSIS_BODY_END.total_before_release_ms | overlapping coordinator total through body end; includes wait; not additive |
| FULL_ANALYSIS_END.total_ms and elapsed_ms | same full coordinator interval; critical_path_total; not additive |

## OP_CORRELATION

The focused coordinator test runs run_full_analysis_exclusive under trace_operation("profile-test") and capture_trace_events(). All captured ANALYSIS events have op=profile-test. It verifies lease/body/end timing semantics and equality relationships without introducing a coordinator/facade run-id parameter.

## CONTEXTOR_FLOW_VERIFY

Contextor confirms run_full_analysis_exclusive retains direct acquire_full_analysis and release_full_analysis callees only; no second coordinator exists. ContextorFacade.analyze_project retains its existing facade call graph including _materialize_full_analysis_lineage. trace_event remains the one canonical ordinary-event owner (existing indexed graph, 2 callers and 7 callees). No parallel trace lifecycle was created.

Canonical revision was 1103 with workspace_sync=out_of_sync because edited local files diverge from Contextor source state. No analysis refresh was run.

## FULL_DIFFS

### contextor/core/api/facade.py

```diff
@@ FULL_ANALYSIS_STAGE_END
+ timing_semantics="critical_path_stage",
```

### contextor/core/analysis/full_analysis_coordinator.py

```diff
@@ FULL_ANALYSIS_LEASE_ACQUIRED
+ timing_semantics="critical_path_lease_wait",
@@ FULL_ANALYSIS_BODY_END
+ timing_semantics="critical_path_analysis_body",
@@ FULL_ANALYSIS_END
+ timing_semantics="critical_path_total",
```

### contextor/core/runtime_trace.py

```diff
+ header fields: stage, analysis_ms, total_before_release_ms, total_ms
+ ANALYSIS header event: FULL_ANALYSIS_STAGE_END
+ trace_event whitelist mappings for all four fields
```

### tests/test_runtime_trace.py

```diff
+ header field/event assertions for stage and coordinator timing fields
+ test_full_analysis_stage_evidence_is_structured_in_memory
```

### tests/test_full_analysis_coordination.py

```diff
+ imports capture_trace_events, trace_operation
+ test_profile_operation_scopes_full_analysis_coordinator_evidence
```

## COMMIT_SHA

6bd727f91c98d2f2928a4530f8ffb022a321a752 (existing HEAD; no commit created).

## RUNTIME_RESTART_REQUIRED

YES. Reload active MCP only before later real CPA usage. No MCP, Desktop, or LIVE restart was performed.

Awaiting proceduj.
