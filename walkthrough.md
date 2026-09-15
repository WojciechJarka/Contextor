## CPA10J_WARM_ANALYSIS_RESIDUAL_LATENCY_DISCOVERY

STATUS=PARTIAL_WITH_WARM_CLASSIFICATION_COMPLETE
HEAD=974d4bebef697a64d225e19fdfb130d0a8401cf3
WORKTREE=clean_before_and_after; production/test files unchanged
RUNTIME_FRESHNESS=PASS; canonical_state=fresh; workspace_sync=verified; canonical_revision=1218; provenance=live; all queried canonical families=fresh
RUNTIME_ADVISORY_WARNING=Contextor get_module_context reported: "The last analysis job was failed. Canonical state reflects revision 1218." This does not invalidate current LIVE state. Later symbol-level responses returned advisory_warning=null for the same revision; this inconsistency is an observability gap and is reported explicitly.
CONTEXTOR_FIRST_VERIFICATION=PASS; deferred mcp__contextor__* tools were present and used: get_mcp_documentation, get_analysis_status, get_live_events, describe_canonical_state, query_canonical_projection, get_project_architecture, get_module_context, get_symbol_implementation, get_symbol_call_context and get_source_range.

KNOWN_EVIDENCE_USED=Canonical warm profile total_ms=45297; indexing=11875; identity_and_setup=8000; authoritative_state_resolution=7922; canonical_materialization=7829; lineage_materialization=6156; persistence=3828; snapshot_save=3812; reports=3671; live_publish=8312. Warm counters: 398/398 cache hits; source_parse_calls=0; lineage_extract_calls=0; materialize_sources=0; reresolve_sources=0; reuse_sources=398; cache_get_sum_ms=2077 aggregate non-critical-path. Certified Desktop run: total_ms=48563, analysis_ms=48531, indexing=10141, cache_hits=398/398.
CONTROLLED_NO_CODEX_BASELINE=43 s and 42 s are the stable warm baseline; 56 s is warm-up/system noise. Codex contention can add seconds but does not explain the main 42-43 s cost.
NO_PROFILE_RERUN=YES; the user-requested analyze_project retry was not used as a performance profile.

## PRECHECK_AND_RETRY_OBSERVATION

Historical job `331b4b4db5c549f6abead1ca92f9429a` failed with `PermissionError: [WinError 5] Access is denied` while `_write_analysis_job` performed atomic `os.replace` of the job JSON. Owner: `contextor/mcp/analysis_jobs.py:_write_analysis_job` lines 43-57.

User-requested retry `bd08bd1a52a04176abff3ac2b8ab9596` was accepted and entered `running`, but after more than two minutes its durable file still reported `Step 1/8: Initializing repository identity`, with unchanged `updated_at=2026-09-15T14:44:17.692531+00:00`. `owner_pid=4612` was alive and was `contextor.mcp_server`. Waiting was stopped per user instruction. `WinError 5` was therefore not independently reproduced or cleared.

This is a separate MCP job lifecycle/observability anomaly, not evidence of CPA10I warm-cache regression. Missing evidence: active worker phase and last successful job-state write after Step 1. Classification: `OBSERVABILITY_INSUFFICIENT/UNKNOWN`, not a warm optimization target.

## COST_CLASSIFICATION_MAP

### indexing

measured_ms=11875; share_of_warm_analysis=26.22%; exact_owner_files=contextor/core/api/facade.py:557-1271 and contextor/core/symbol_engine/indexer.py:723-972; exact_owner_symbols=ContextorFacade.analyze_project, index_repository, _process_single_file; direct_callers=facade -> index_repository, indexer build_index -> index_repository; work_done_on_warm=root_path.rglob("*.py"), filtering, ProcessPoolExecutor submission, future collection, per-file cache validation, Module/side-table reconstruction, checkpoints; contractual_purpose=current RepositoryIndex and downstream facts; classification=JUSTIFIED_COST; problem_evidence=398/398 cache hits, zero source parsing/extraction, no redundant work proven; optimization_hypothesis_if_any=NONE; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=HIGH; evidence_type=DIRECT_TIMING+DIRECT_COUNTER+DIRECT_CODE_PATH; observability_gap=no critical-path split for enumeration, pool/IPC, result collection, sorting/assembly or post-worker work.

### authoritative_state_resolution

measured_ms=7922 nested in identity_and_setup=8000; share_of_warm_analysis=17.66% wide-stage share; exact_owner_files=contextor/core/api/facade.py:557-1271 and contextor/core/live_state/hydration.py:29-82; exact_owner_symbols=ContextorFacade.analyze_project, _initialize_repository_identity, resolve_authoritative_repository_state; direct_callers=facade -> resolver; hydrate_repository_engine -> resolver; work_done=repository identity, legacy snapshot migration, LIVE connect/ping/snapshot, validated metadata/load_engine_state fallback, cache reset and filters; contractual_purpose=LIVE-first authority/freshness; classification=JUSTIFIED_COST; problem_evidence=no duplicate/avoidable work proven; optimization_hypothesis_if_any=NONE; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=HIGH; evidence_type=DIRECT_TIMING+DIRECT_CODE_PATH; observability_gap=no sub-timing for identity, migration, connect, ping, snapshot or fallback.

### lineage_materialization/reuse

measured_ms=6156 nested in canonical_materialization=7829; share_of_warm_analysis=13.59%; exact_owner_files=contextor/core/api/facade.py:264-478 and :780-1055; contextor/core/analysis/lineage_materialization.py:528-815; contextor/core/reference/module_usage_reuse.py:35-46; exact_owner_symbols=_materialize_full_analysis_lineage, materialize_lineage_source_facts, reresolve_materialized_lineage_source_facts, build_module_usage_baseline_with_reuse; direct_callers=ContextorFacade.analyze_project -> _materialize_full_analysis_lineage -> per-source reuse gate; work_done=topology/collision/artifact validation, active identity checks, fingerprint/semantic-version/ownership/descriptor checks, reuse and canonical index/state construction; contractual_purpose=revision-correct canonical lineage; classification=JUSTIFIED_COST; problem_evidence=398 reuse, 0 reresolve, 0 materialize, with a correctness gate still executed; optimization_hypothesis_if_any=NONE; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=HIGH; evidence_type=DIRECT_TIMING+DIRECT_COUNTER+DIRECT_CODE_PATH; observability_gap=known evidence does not split reuse_gate_ms from state construction/index building.

### live_publish

measured_ms=8312; share_of_warm_analysis=18.35%; exact_owner_files=contextor/core/api/facade.py:1025-1190 and contextor/core/live_state/ipc.py:1207-1258, :1516-1743; exact_owner_symbols=facade publish block, CanonicalLiveServer._dispatch, CanonicalLiveServer._execute_publish; direct_callers=facade -> connect/client.publish -> IPC dispatch -> _execute_publish; work_done=connect, canonical state transfer, status/revision validation, provenance binding and event recording; contractual_purpose=publish canonical LIVE revision; classification=JUSTIFIED_COST_WITH_OBSERVABILITY_GAP; problem_evidence=no redundant publish evidence; optimization_hypothesis_if_any=NONE; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=HIGH; evidence_type=DIRECT_TIMING+DIRECT_CODE_PATH; observability_gap=source has connect/publish/status timers but known profile has only stage total, not payload/IPC/subscriber components.

### snapshot_save

measured_ms=3812 of persistence=3828; share_of_warm_analysis=8.41% for snapshot_save; exact_owner_files=contextor/core/api/facade.py:1080-1110, contextor/core/analysis/state_manager.py:416-442, contextor/core/live_state/store.py:471-583; exact_owner_symbols=facade persistence block, save_engine_state, save_snapshot; direct_callers=facade -> save_engine_state -> save_snapshot; work_done=complete state serialization, file-state/metadata JSON, flush+fsync, atomic replace and lock release; contractual_purpose=durable revision-monotonic crash-safe recovery; classification=JUSTIFIED_COST; problem_evidence=no redundant persistence proven; optimization_hypothesis_if_any=NONE; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=VERY_HIGH; evidence_type=DIRECT_TIMING+DIRECT_CODE_PATH; observability_gap=no split for pickle, JSON, fsync, replace or lock time.

### reports

measured_ms=3671; share_of_warm_analysis=8.10%; exact_owner_files=contextor/core/api/facade.py:735-785, contextor/core/reporting_engine/pipeline.py:34-708, contextor/core/reporting_layer/artifact_usage_report.py:701-887; exact_owner_symbols=ContextorFacade.analyze_project, execute_global_pipeline, generate_artifact_usage_report; direct_callers=facade -> execute_global_pipeline; work_done=architectural reports from modules/graph/metrics/cycles/debt/collisions/reference/symbol/test facts; contractual_purpose=report output consumed by canonical materialization and diagnostics; classification=OBSERVABILITY_INSUFFICIENT; problem_evidence=stage total alone does not prove redundant recalculation; optimization_hypothesis_if_any=NONE_UNTIL_COMPONENT_TIMING_EXISTS; expected_saving_bound_if_any=NONE_EVIDENCE_BACKED; correctness_risk=MEDIUM_TO_HIGH; evidence_type=DIRECT_TIMING+DIRECT_CODE_PATH; observability_gap=no measured report-substage split.

## CROSS_STAGE_DUPLICATION

RESULT=NO_CONFIRMED_REDUNDANT_WORK. Indexing has zero source parsing/extraction on warm; lineage has 398 validated reuses and zero reresolve/materialize; persistence serializes for recovery; LIVE publish transfers the state for a separate LIVE contract. Same state touched by persistence and publish is not proof of duplication. Remaining unproven copies/traversals are an observability gap, not a problem finding.

## CONFIRMED_PROBLEMS

WARM_ANALYSIS=NONE_CONFIRMED. No REDUNDANT_WORK or AVOIDABLE_WARM_WORK candidate is evidence-backed.
SEPARATE_MCP_JOB_ANOMALY=CONFIRMED_OBSERVABILITY_OR_LIFECYCLE_ANOMALY. Historical `_write_analysis_job` WinError 5 is direct evidence; retry stuck at Step 1/8 is direct state evidence, but its exact root cause is unproven because waiting stopped and no active-phase span exists.

## JUSTIFIED_COSTS

Indexing file enumeration/ProcessPool/result assembly; LIVE-first authoritative resolution; canonical materialization/reuse validation; report generation required for canonical state; complete snapshot serialization/fsync/atomicity; LIVE publish/revision/event publication.

## OBSERVABILITY_GAPS

No new instrumentation was added. Missing: indexing critical-path subspans; identity-resolution subspans; reuse-gate versus state-construction timing; live connect/publish/status and payload/IPC/subscriber breakdown; report substage timings; MCP job heartbeat/active worker phase/last successful `_write_analysis_job`; and consistent advisory-warning projection across Contextor query surfaces.

## NEXT_TARGET

NEXT_TARGET=NONE
NEXT_TARGET_OWNER=NONE
NEXT_TARGET_RATIONALE=No confirmed REDUNDANT_WORK or AVOIDABLE_WARM_WORK. Selecting by measured_ms alone would violate the evidence rule. The MCP retry anomaly is a separate lifecycle/observability follow-up, not a warm-analysis optimization target.
EXPECTED_SAVING_BOUND=NONE_EVIDENCE_BACKED
LIKELY_FILES=NONE_FOR_WARM_OPTIMIZATION; separate MCP follow-up would center on contextor/mcp/analysis_jobs.py:_write_analysis_job and _execute_analysis_job.
LIKELY_TESTS=NONE_RUN; no tests changed or run.
INSTRUMENTATION_NEEDED_BEFORE_IMPLEMENTATION=Existing fields must first be surfaced/correlated for the listed gaps; no instrumentation added.

IMPLEMENTATION_PERFORMED=NO
TESTS_RUN=NO; NO_FULL_PYTEST=YES
SOURCE_TEST_DIFFS=NONE
ACTUAL_DIFF=DIFFS=NONE (excluding this required walkthrough report)

## CPA10K_MCP_ANALYZE_PROJECT_STUCK_JOB_DISCOVERY

STATUS=ROOT_CAUSE_PROVED_FOR_RETRY; DURABLE_STATUS_STALE_CONFIRMED; WINDOWS_REPLACE_ACTOR_UNKNOWN
HEAD=974d4bebef697a64d225e19fdfb130d0a8401cf3
WORKTREE=only walkthrough.md modified; production/source/test files unchanged; no implementation, test change, documentation change outside this report, or new analyze_project run performed

CONTEXTOR_FIRST_VERIFICATION=PASS [DIRECT_EVIDENCE]. Deferred Contextor MCP tools were available and used first. `get_analysis_status(job_id=bd08bd1a52a04176abff3ac2b8ab9596)` read the durable record as `running`, with `updated_at=2026-09-15T14:44:17.692531+00:00`, message `Step 1/8: Initializing repository identity`, and `owner_pid=4612` in the durable file. `get_live_events(repo_path, after_revision=1218)` returned `continuity=continuous`, `latest_revision=1218`, and no events. Therefore no retry LIVE publication or revision advance was observed.

PROFILE_VS_ANALYZE_PROJECT_FAULT_DOMAIN=

Both paths share the core full-analysis ownership path: `run_full_analysis_exclusive`, `owner="mcp_analysis"`, the full-analysis lease, `ContextorFacade.analyze_project`, staged progress/log callbacks, and the canonical analysis pipeline. The profiler path additionally runs through `contextor_profile_analysis` -> `profile_worker` in a separate subprocess, captures runtime trace events, and has no durable MCP job JSON or per-progress `_write_analysis_job` callback. `analyze_project` uniquely adds `_start_analysis_job`, a daemon thread named `contextor-analysis-<job_id>`, `_analysis_lock`, durable JSON writes for every progress message, outer async job handling, and post-publish engine reload/validation.

The successful profiler narrows the fault domain: the shared full-analysis path can acquire the lease and execute successfully under its profiler invocation. It does not prove that the MCP durable-job wrapper is safe. The retry evidence places the failure in the analyze_project durable progress-write path after the shared core had already started.

RETRY_JOB_FORENSICS=

The durable target `C:\Temp\Contextor_Repo\.contextor\analysis_jobs\bd08bd1a52a04176abff3ac2b8ab9596.json` remained unchanged at:

- `status=running`
- `message=[PROGRESS] Step 1/8: Initializing repository identity`
- `updated_at=2026-09-15T14:44:17.692531+00:00`
- `completed_at=null`, `error=null`, `live_publish_status=pending`
- `owner_pid=4612`

The retry's leftover temporary files are decisive direct evidence. At `2026-09-15T14:44:27.085063+00:00`, `bd08...json.d1c584e0c7004d45b01e615b00274d9f.tmp` contained a newer `status=running` payload with `message=Starting directory indexing...`. At `2026-09-15T14:44:27.088067+00:00`, `bd08...json.b8170e9114734380b051840060b933c0.tmp` contained a terminal `status=failed` payload whose error was `PermissionError: [WinError 5] Access is denied` for the first temporary file -> durable target `os.replace`. Both temporary files remained while the durable target stayed at the earlier Step 1 payload.

This sequence proves that the retry did not merely stop emitting progress. It attempted the next job-log persistence, that persistence failed, the handler constructed a failed status, and the failed-status persistence also failed. No completed payload exists for this job.

THREAD_TASK_STATE=

`owner_pid=4612` was the live `contextor.mcp_server` process, but that is not evidence that `contextor-analysis-bd08bd1a52a04176abff3ac2b8ab9596` was still alive. The public status path only converts queued/running jobs to `interrupted` when `owner_pid != os.getpid()`; it does not inspect same-process `_analysis_tasks[job_id].is_alive()`. No safe public in-memory snapshot of `_analysis_tasks`, `_analysis_jobs_by_repo`, or the Python thread's final exception was available. Direct thread-state classification is therefore `UNKNOWN`.

The code path makes cleanup behavior deterministic after the observed failure: `_execute_analysis_job` has a `finally` that pops the job from both in-memory maps even when the failed-status `_write_analysis_job` raises. This is `CODE_PATH_PROVED`, not direct in-memory observation. The stale JSON is consequently compatible with a terminated worker plus stale durable state, but the observed and proved initiating mechanism is the durable write failure.

FULL_ANALYSIS_TRACE_EVIDENCE=

The current runtime trace contains the retry's `pid=4612`, worker `tid=6500`, and `owner=mcp_analysis` events:

- `FULL_ANALYSIS_LEASE_ACQUIRED` at approximately `16:44:17`, with `wait_ms=109`.
- `FULL_ANALYSIS_STAGE_COMPONENT_END` for `progress_setup` at `0 ms`.
- `FULL_ANALYSIS_STAGE_COMPONENT_END` for `repository_identity` at `110 ms`.
- `FULL_ANALYSIS_STAGE_COMPONENT_END` for `authoritative_state_resolution` at `9266 ms`.
- `FULL_ANALYSIS_STAGE_COMPONENT_END` for `cache_reset` at `0 ms`.
- `FULL_ANALYSIS_END` at approximately `16:44:27`, `total_ms=9500`.

There is no `FULL_ANALYSIS_BODY_END`, no index component completion, no later full-analysis stage, no `FULL_ANALYSIS_START` event in the inspected implementation, and no LIVE publish event for this retry. In `full_analysis_coordinator.py`, `FULL_ANALYSIS_BODY_END` is emitted only after `ContextorFacade.analyze_project` returns, while `FULL_ANALYSIS_END` is emitted from the coordinator `finally`. The trace therefore proves that the shared core entered full analysis, progressed through identity/setup and cache reset, then exited through the failure/finally path before returning a result. It does not support classification C (a still-running block before the next progress event).

The facade source matches the temporary payload exactly: after `cache_reset`, it calls `log("Starting directory indexing...")` before `_analysis_filters` and before `progress.begin("Indexing repository files")`. The observed failed progress payload therefore identifies the failure boundary before directory indexing, not an unexplained two-minute stall.

WRITE_FAILURE_CONTROL_FLOW=

`contextor/mcp/analysis_jobs.py` proves the following control flow:

1. `_execute_analysis_job` writes the initial `running` payload before entering its `try` block (`analysis_jobs.py:243-247`). This initial write was not the observed failure because the durable running file was created and the retry entered the core trace.
2. `job_log` logs to stderr, updates the in-memory job message, and calls `_write_analysis_job` inside the `try` path (`analysis_jobs.py:249-253`). The first leftover retry temp is direct evidence that this call failed while writing `Starting directory indexing...`; its exception propagates out of `_run_analysis_worker`, so it interrupts the underlying full analysis.
3. The outer `except` converts the in-memory job to `status=failed` and calls `_write_analysis_job` again (`analysis_jobs.py:325-335`). The second leftover temp is direct evidence that this failed-status write also hit `WinError 5`.
4. The normal completed write (`analysis_jobs.py:320-324`) was never reached because the worker exception escaped before an analysis outcome existed.

Classification: `D=PROVED`. The retry was interrupted by a durable job write failure; the failure write itself also failed, leaving the prior durable JSON falsely running. `A=DISPROVED_FOR_THIS_RETRY` because there is no completed payload or body-end event. `C=DISPROVED_FOR_THIS_RETRY` because the trace has `FULL_ANALYSIS_END` after 9500 ms. `B=COMPATIBLE_AS_A_SECONDARY_EFFECT` but not the primary root cause: worker termination and in-memory cleanup are code-path-proved/likely, while direct same-process thread observation is unavailable.

FINALLY_CLEANUP_BEHAVIOR=

The `finally` block at `analysis_jobs.py:336-340` executes after the `except` body raises from the second `_write_analysis_job`; it removes the job from `_analysis_tasks` and, if matching, `_analysis_jobs_by_repo`. The `_analysis_job_lock` is an `RLock`, and `_write_analysis_job` exits its own lock context when `os.replace` raises. Thus the source control flow proves that cleanup is attempted despite the failed terminal write. No direct API exposed the post-failure dictionaries, so the exact in-memory state is `UNKNOWN`, not inferred from the live MCP server PID.

WINDOWS_REPLACE_EVIDENCE=

`WinError 5` is `DIRECT_EVIDENCE` for `os.replace(temporary, target)` denial in both the historical job `331b4b4db5c549f6abead1ca92f9429a` and the retry's failed-status temp payload. The retry also leaves both temporary files, which is consistent with the replace operation failing before the temp files were moved.

The actor/reason is `UNKNOWN`: no evidence identifies an open target/temp handle, concurrent process writer, antivirus/indexer, ACL/permission change, or other ownership condition. The in-process `RLock` does not establish cross-process exclusion. No Windows handle/ACL/AV investigation was performed or assumed. Therefore the report proves the lifecycle mechanism, not the underlying Windows reason for access denial.

ROOT_CAUSE=The retry's `job_log` call attempted to persist `Starting directory indexing...` and failed at atomic `os.replace` with `PermissionError [WinError 5]`. That exception propagated into `_execute_analysis_job`, which attempted to persist `status=failed`; that write failed as well. The durable target consequently remained at the previous `status=running` Step 1 record although the full-analysis lease had already ended. `PROVED` for the retry lifecycle; the OS-level cause of `WinError 5` remains `UNKNOWN`.
ROOT_CAUSE_CONFIDENCE=HIGH for D / stale durable status mechanism; HIGH that core analysis started and exited before completion; UNKNOWN for the Windows replace denial actor/cause; UNKNOWN for a direct post-failure Python thread snapshot.

PROVED_FACTS=

- `DIRECT_EVIDENCE`: retry durable JSON is stale `running` at Step 1 with unchanged `updated_at`; two retry-specific `.tmp` payloads remain.
- `DIRECT_EVIDENCE`: first retry temp contains the next progress message `Starting directory indexing...`.
- `DIRECT_EVIDENCE`: second retry temp contains `status=failed` and the first temp -> target `WinError 5`.
- `DIRECT_EVIDENCE`: retry trace has lease acquisition, identity/setup component events, and `FULL_ANALYSIS_END` at `9500 ms`.
- `CODE_PATH_PROVED`: job-log write exceptions propagate into the outer failure path; failed-status write exceptions can escape after the failed payload is constructed.
- `CODE_PATH_PROVED`: the full-analysis coordinator releases its lease and emits `FULL_ANALYSIS_END` in `finally`.
- `CODE_PATH_PROVED`: the MCP job handler attempts in-memory cleanup in its own `finally`.
- `UNKNOWN`: direct in-memory task/thread state after the cleanup path.
- `UNKNOWN`: specific Windows actor behind `os.replace` access denial.

INFERENCES=

- `INFERENCE`: after the second write failure, the daemon worker would normally terminate through the uncaught exception from `asyncio.run`, after the handler's `finally`; this is strongly implied by the code but was not directly observed through an in-memory thread API.
- `INFERENCE`: the shared analysis body would have proceeded to indexing if the progress persistence exception had not aborted it; this is a counterfactual, not a claim about an unobserved successful run.

UNKNOWNS=

- Whether the Python worker thread was alive at any later wall-clock observation; the server PID cannot answer this.
- Which Windows handle/process/security component caused each `os.replace` denial.
- Whether stderr captured an uncaught worker exception; no matching error record was present in the inspected runtime event stream, and the process log did not provide a usable correlated record.
- Whether a same-process status poll after worker termination would have returned stale running (the current code path indicates yes because only cross-process owner change is reconciled).

MINIMAL_FIX_CONTRACT_IF_PROVED=

1. A progress/job-log persistence failure must not leave the only durable representation as `status=running`; the handler must either continue core analysis with an explicit persistence-degraded flag or publish a terminal failure through a guaranteed fallback path.
2. A failed-status persistence failure must never escape without preserving an observable terminal/persistence-failure outcome and without completing in-memory cleanup.
3. `get_analysis_status` must reconcile same-process jobs against task completion/exception state, not only compare `owner_pid` with the current MCP PID; a stale durable `running` record must not be reported as live solely because the server process is alive.
4. The implementation must retain write-phase identity (`initial_running`, `job_log`, `completed`, `failed`) and preserve the original write exception separately from any later failure-write exception.

INSTRUMENTATION_IF_NOT_PROVED=N/A for the retry lifecycle mechanism, which is proved. To prove the remaining Windows-specific cause on one future controlled retry only, capture per-write phase, PID/TID, target/temp paths, exception type/WinError, and whether the temp remained; capture worker start/end/exception and task `is_alive()` transitions; and correlate those records with the job ID. No additional retry is authorized by this task.

LIKELY_FILES=contextor/mcp/analysis_jobs.py:43-54, 84-120, 163-234, 237-340, 343-379; contextor/mcp/tools/get_analysis_status.py:14-80; contextor/mcp/tools/analyze_project.py:7-18; contextor/core/api/facade.py:630-676; contextor/core/analysis/full_analysis_coordinator.py:606-693; profiler comparison paths contextor/mcp/tools/contextor_profile_analysis.py, contextor/core/analysis/profile_worker.py, contextor/core/analysis/profile_runner.py.
LIKELY_TESTS=focused analysis-job lifecycle tests for (a) job-log replace failure with successful failed-status write, (b) job-log replace failure followed by failed-status replace failure leaving no falsely-live in-memory task, (c) same-process dead/finished task reconciliation in get_analysis_status, (d) preservation of the original and secondary write exceptions, and (e) full-analysis lease release/trace behavior on callback failure. No tests were run or changed under DISCOVERY_ONLY.

IMPLEMENTATION_PERFORMED=NO
TESTS_RUN=NO; NO_NEW_ANALYSIS_RUN=YES
ACTUAL_DIFF=DIFFS=NONE for production/source/test files; walkthrough.md is report-only.

## CPA10K0_PRE_REFACTOR_BASELINE_TEST_CONTRACT_SYNC

STATUS=SUCCESS
HEAD_BEFORE=974d4bebef697a64d225e19fdfb130d0a8401cf3
HEAD_AFTER=974d4bebef697a64d225e19fdfb130d0a8401cf3
FILES_CHANGED=tests/mcp/tools/test_contextor_fact_lineage.py;tests/test_mcp_diagnostics.py;tests/test_mcp_split_s2a.py;tests/test_mcp_split_s2b.py;tests/test_mcp_split_s2c.py;tests/test_mcp_split_s2d.py;tests/test_mcp_split_s2e.py
CONTEXTOR_FIRST_VERIFICATION=PASS; active mcp__contextor__* tools were found and used first. get_source_range confirmed contextor/mcp_server.py:698-728 contains 29 registered names with contextor_fact_lineage followed by contextor_profile_analysis. get_symbol_implementation resolved contextor/mcp/tools/get_symbol_implementation.py:get_symbol_implementation with workspace_sync=verified and the documented parameter-contract behavior. search_source confirmed the fetch include error anchor and parameter_contract_error.
SOURCE_DRIFT_CHECK=PASS; expected HEAD matched; all requested test anchors matched current files; current production registration and get_symbol_implementation contract matched the task; no production, docs, tests/live_job_object.py, or other tests were changed.
FOCUSED_TESTS=PASS; py_compile passed; 9 focused tests passed in 6.22s; 1 existing FastMCP/Authlib deprecation warning.
WINDOWS_JOB_OBJECT_STATUS=UNCLASSIFIED_UNCHANGED

ACTUAL_DIFF=

```diff
diff --git a/tests/mcp/tools/test_contextor_fact_lineage.py b/tests/mcp/tools/test_contextor_fact_lineage.py
index d122f6f..b366507 100644
--- a/tests/mcp/tools/test_contextor_fact_lineage.py
+++ b/tests/mcp/tools/test_contextor_fact_lineage.py
@@ -736,7 +736,7 @@ def test_signature_docs_registration_and_public_contract_parity():
     assert str(inspect.signature(tool.fn)) == (
         "(repo_path: str, family: str, direction: str = 'both', depth: int = 3) -> str"
     )
-    assert list(mcp_server.REGISTERED_MCP_TOOL_NAMES)[-1] == "contextor_fact_lineage"
+    assert "contextor_fact_lineage" in mcp_server.REGISTERED_MCP_TOOL_NAMES
     document = load_tool_document("contextor_fact_lineage")
     assert document["tool"] == "contextor_fact_lineage"
     assert any(entry.startswith("family (string, required)") for entry in document["parameters"])
     source = inspect.getsource(contextor_fact_lineage)
     assert "ast.parse" not in source
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index f95301c..290108f 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -321,4 +321,4 @@ def test_cheap_filters_run_before_severity_and_severity_filter_survives(tmp_path
 
 def test_registered_name_collision_tool_and_shared_summary_wrapper():
     assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
-    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 28
+    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 29
diff --git a/tests/test_mcp_split_s2a.py b/tests/test_mcp_split_s2a.py
index 3a972db..a3cd7bd 100644
--- a/tests/test_mcp_split_s2a.py
+++ b/tests/test_mcp_split_s2a.py
@@ -48,6 +48,7 @@ _EXPECTED_ORDER = [
     "get_mcp_documentation",
     "get_module_blast_radius",
     "contextor_fact_lineage",
+    "contextor_profile_analysis",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2b.py b/tests/test_mcp_split_s2b.py
index 03ec2b6..496bfed 100644
--- a/tests/test_mcp_split_s2b.py
+++ b/tests/test_mcp_split_s2b.py
@@ -27,7 +27,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_symbol_lineage", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius", "contextor_fact_lineage",
+    "get_module_blast_radius", "contextor_fact_lineage", "contextor_profile_analysis",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2c.py b/tests/test_mcp_split_s2c.py
index 138c446..510cc53 100644
--- a/tests/test_mcp_split_s2c.py
+++ b/tests/test_mcp_split_s2c.py
@@ -26,6 +26,7 @@ _EXPECTED_ORDER = [
     "get_symbol_call_context", "get_symbol_lineage", "get_name_collisions",
     "get_mcp_documentation", "get_module_blast_radius",
     "contextor_fact_lineage",
+    "contextor_profile_analysis",
 ]
 
 _IMPLEMENTATIONS = {
diff --git a/tests/test_mcp_split_s2d.py b/tests/test_mcp_split_s2d.py
index c434a0f..df7f73c 100644
--- a/tests/test_mcp_split_s2d.py
+++ b/tests/test_mcp_split_s2d.py
@@ -22,7 +22,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_symbol_lineage", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius", "contextor_fact_lineage",
+    "get_module_blast_radius", "contextor_fact_lineage", "contextor_profile_analysis",
 ]
 
 _IMPLEMENTATIONS = {
@@ -183,7 +183,7 @@ def test_get_symbol_implementation_explicit_fetch_large_returns_implementation(t
     assert "auto_fetch" not in res
 
 
-def test_get_symbol_implementation_explicit_fetch_without_include_returns_selection_required(tmp_path):
+def test_get_symbol_implementation_explicit_fetch_without_include_returns_parameter_contract_documentation(tmp_path):
     import json
     src = tmp_path / "small_mod.py"
     src.write_text("def helper():\n    return 42\n", encoding="utf-8")
@@ -194,11 +194,18 @@ def test_get_symbol_implementation_explicit_fetch_without_include_returns_select
         mode="fetch",
     )
     res = json.loads(res_raw)
-    assert res["status"] == "selection_required"
-    assert "Fetch requires an explicit include selection" in res["message"]
-
-
-def test_get_symbol_implementation_invalid_mode(tmp_path):
+    assert res["tool"] == "get_symbol_implementation"
+    assert res["version"] == "1.0.0"
+    assert "parameters" in res
+    assert "behavior" in res
+    error = res["parameter_contract_error"]
+    assert error["parameter"] == "include"
+    assert error["invalid_value"] is None
+    assert "mode='fetch' requires a non-empty include list" in error["reason"]
+    assert "Do not repeat the same invalid call." in error["retry_instruction"]
 
 
+def test_get_symbol_implementation_invalid_mode_returns_parameter_contract_documentation(tmp_path):
     import json
     src = tmp_path / "small_mod.py"
     src.write_text("def helper():\n    return 42\n", encoding="utf-8")
@@ -209,8 +216,15 @@ def test_get_symbol_implementation_invalid_mode(tmp_path):
         mode="invalid_mode",
     )
     res = json.loads(res_raw)
-    assert res["status"] == "error"
-    assert "mode must be 'auto', 'preview', or 'fetch'." in res["error"]
+    assert res["tool"] == "get_symbol_implementation"
+    assert res["version"] == "1.0.0"
+    assert "parameters" in res
+    assert "behavior" in res
+    error = res["parameter_contract_error"]
+    assert error["parameter"] == "mode"
+    assert error["invalid_value"] == "invalid_mode"
+    assert "mode must be exactly one of: 'auto', 'preview', or 'fetch'" in error["reason"]
+    assert "Do not repeat the same invalid call." in error["retry_instruction"]
 
 
 def _generate_exact_candidate_source(target_bytes: int, tmp_path: Path, filename: str) -> Path:
diff --git a/tests/test_mcp_split_s2e.py b/tests/test_mcp_split_s2e.py
index 69b236c..77889e4 100644
--- a/tests/test_mcp_split_s2e.py
+++ b/tests/test_mcp_split_s2e.py
@@ -23,7 +23,7 @@ _EXPECTED_ORDER = [
     "lookup_index_entries", "get_artifacts_for_module",
     "lookup_artifact_by_symbol", "search_source", "get_source_range",
     "get_symbol_call_context", "get_symbol_lineage", "get_name_collisions", "get_mcp_documentation",
-    "get_module_blast_radius", "contextor_fact_lineage",
+    "get_module_blast_radius", "contextor_fact_lineage", "contextor_profile_analysis",
 ]
 
 _IMPLEMENTATIONS = {
```
