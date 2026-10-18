TASK: CONTEXTOR_C38E2Q_DURABLE_ASYNC_LIVE_PUBLICATION
STAGE: PRE_EDIT_DISCOVERY — stepwise gate; implementation not yet started.
HEAD_BEFORE: 1419e9f62cbf8d8abd55f3691dad57b2259c937e
HEAD_AFTER: 1419e9f62cbf8d8abd55f3691dad57b2259c937e
GIT_STATUS: clean before walkthrough overwrite; no source/test/docs change in this stage.

CONTEXTOR_DISCOVERY_COVERAGE:
DIRECT_EVIDENCE: Contextor get_file_edit_context resolved ipc.py, facade.py, analysis_jobs.py and get_analysis_status.py at LIVE revision 573 with fresh syntax. Exact Contextor symbol implementations/source ranges were inspected for CanonicalMutationCoordinator, _execute_publish, _execute_committed_publish, _execute_queued_update_file, LiveStateClient mutation_status, ContextorFacade.analyze_project and get_analysis_status. Contextor reports 17 direct consumers for ipc.py, 47 for facade.py, 15 for analysis_jobs.py, and 5 for get_analysis_status.py. Source was workspace_sync=verified in pre-edit symbol previews. Contextor get_live_events reported revision 573, resync_required=false.
CODE_PATH_PROVED: CanonicalMutationCoordinator owns one FIFO queue, condition, mutation worker, idempotency map, retained terminal jobs, and recovery verification fence. The server currently constructs it with _execute_queued_update_file as executor. submit currently requires file_path and idempotency_key, so approved operation-discriminated extension is necessary. The server dispatcher routes submit_update_file to coordinator.submit and mutation_status to coordinator.status. _execute_publish holds _mutation_execution_lock and routes committed-reader publication through _execute_committed_publish, which reads and validates the committed snapshot, exact state_id/revision and monotonicity before installation. Full facade currently calls client.publish(state, acknowledge_installed=True) after save_engine_state, then converts TimeoutError to live_publish_status=timed_out. analysis_jobs persists and projects the existing publication status/revision/warning; get_analysis_status currently reads durable jobs and has no receipt reconciliation.
CONTRACT_PROVED: Existing synchronous publish, queued update_file and mutation_status have separate routes. The new operation can use the existing coordinator without altering the legacy synchronous call.
INFERENCE: The approved design fits the current ownership boundaries. No conflicting invariant has been demonstrated in this discovery stage.
UNKNOWN: Exact status response metadata, service-instance binding surface, and all named test fixtures still require detailed pre-edit inspection before a literal patch.

PRE_EDIT_PLAN:
1. Add strict submit_committed_publish client and server request validation, then extend the existing coordinator submission and queued executor dispatch while preserving update_file response keys and validation.
2. Add deterministic committed-generation key and bounded receipt helper with 90-second wait, exact job/generation/authority verification, and shared classification.
3. Switch only FULL facade publication after durable save to the helper; persist correlation fields in analysis_jobs and reconcile explicit pending durable jobs in get_analysis_status without submission.
4. Update the two allowed docs and isolated focused tests; run only named focused tests; verify desktop_watcher events and workspace sync.

ABSOLUTE_FILES_TO_MODIFY (approved only):
C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py — new IPC admission, coordinator operation dispatch, bounded publish status data, client method.
C:\Temp\Contextor_Repo\contextor\core\live_state\publication_receipt.py — deterministic key, bounded wait, exact receipt classification.
C:\Temp\Contextor_Repo\contextor\core\api\facade.py — FULL durable publication helper and correlation fields.
C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py — durable publication metadata projection and cache state.
C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py — read-only exact terminal receipt reconciliation.
C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json — receipt reconciliation contract.
C:\Temp\Contextor_Repo\contextor\mcp\docs\analyze_project.json — queued publication contract.
C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py — coordinator compatibility and admission tests as needed.
C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py — committed-generation installation and receipt tests as needed.
C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py — client/server IPC contract tests as needed.
C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py — durable status reconciliation tests as needed.
C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py — facade/full orchestration regression as needed.
C:\Temp\Contextor_Repo\tests\test_async_publication_receipt.py — new isolated receipt/timeout tests as needed.

QUEUE_REUSE_PROOF: Existing CanonicalMutationCoordinator identified; no second queue planned.
SUBMISSION_CONTRACT: Approved design recorded; pending implementation.
IDEMPOTENCY_PROOF: Pending.
COMMITTED_GENERATION_VALIDATION: Existing _execute_committed_publish code path confirmed; new queued dispatch pending.
EXACT_TERMINAL_RECEIPT: Pending.
FACADE_INTEGRATION: Existing synchronous path confirmed; migration pending.
DURABLE_JOB_CORRELATION: Pending.
STATUS_RECONCILIATION: Pending.
LEGACY_BEHAVIOR: Current routes identified; regression pending.
TIMEOUT_REPRODUCTION: Historical evidence from task prompt; not reproduced in this stage.
CANONICAL_INVARIANTS: No production mutation invoked.
PROCESS_LIFECYCLE: Existing coordinator thread and close lifecycle identified; unchanged.
FILES_CHANGED=NONE (source/test/docs)
FULL_DIFFS=NONE
TARGETED_TEST_RESULTS: NOT_RUN — discovery-only stage.
WATCHER_EVENTS: No source edit; not applicable.
WORKSPACE_SYNC: Pre-edit inspected symbol source verified; no changed production file to verify.
LIVE_REVISION_BEFORE_AFTER: 573 / no source edit.
MCP_BACKEND_RESTART_REQUIRED=YES
LIVE_SERVICE_RESTART_REQUIRED=YES
RESTARTS_PERFORMED=NO
FINAL_VERDICT: C38E2Q_PARTIAL — pre-edit discovery complete; waiting for `proceduj` under STEPWISE_WORK.
