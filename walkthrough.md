## CPA10K1_ANALYSIS_JOB_PERSISTENCE_AND_RECONCILIATION

STATUS=DISCOVERY_COMPLETE_WAITING_FOR_PROCEDUJ
TASK=CPA10K1_ANALYSIS_JOB_PERSISTENCE_AND_RECONCILIATION
MODE=IMPLEMENT
REPO=C:\\Temp\\Contextor_Repo
STOP_GATE=DISCOVERY_DONE_WAIT_FOR_USER_COMMAND_PROCEDUJ

### HEAD

`git rev-parse HEAD` returned `1d32c7639ed645e1494401988e2194cb60ff781b`.

`git status --short` before this report rewrite showed only `walkthrough.md` modified. No production, test, or documentation source file has been changed in this task.

### SOURCE_DRIFT

SOURCE_DRIFT=NONE_FOR_REQUESTED_OWNER_CONTRACT.

Current Contextor discovery confirms the requested ownership remains split as expected:

- Durable job writing, task ownership, worker execution, and in-memory active-job filtering are owned by `contextor/mcp/analysis_jobs.py`.
- Public status selection and reconciliation are owned by `contextor/mcp/tools/get_analysis_status.py`.
- `contextor/mcp/tools/analyze_project.py` was not identified as the persistence/reconciliation owner; no reason was found to edit it.
- Current implementations are the pre-change versions described by the task: one direct `os.replace`, durable active filtering without same-process task liveness, strict persistence from `_execute_analysis_job`, and only `owner_process_changed` reconciliation in `get_analysis_status`.

Exact current implementations from Contextor:

- `analysis_jobs._write_analysis_job`: lines 43-54; temporary JSON write followed by one `os.replace(temporary, target)`.
- `analysis_jobs._active_analysis_jobs`: lines 84-120; includes every readable durable `queued`/`running` job and sorts by mtime/job ID.
- `analysis_jobs._execute_analysis_job`: lines 237-340; initial, progress, completed, and failed persistence calls are not isolated from the analysis exception path.
- `analysis_jobs._start_analysis_job`: lines 343-379; existing initial accepted/queued `_write_analysis_job` at line 370 remains the strict pre-start write owner.
- `get_analysis_status`: lines 14-123; only a different `owner_pid` is reconciled and reconciliation persistence is currently strict.

### CONTEXTOR_OWNER_AND_LINEAGE_EVIDENCE

Evidence source: Contextor MCP, queried before any textual verification or edit. Canonical response revision was `1234`, `canonical_state=fresh`, `provenance=live`, and target files reported `workspace_sync=verified`.

Direct owner/context evidence:

- `get_file_edit_context(contextor/mcp/analysis_jobs.py)` resolved module `contextor.mcp.analysis_jobs`, module ID `34/1`, adapter layer, 12 static consumers, and 49 reachable covering tests. Imports include runtime, full-analysis coordinator, and facade boundaries.
- `get_file_edit_context(contextor/mcp/tools/get_analysis_status.py)` resolved module ID `60/1`, public symbol `get_analysis_status` (`A1731/1`), five static consumers, and 29 reachable covering tests. Its direct imports include `contextor.mcp.analysis_jobs`.
- `get_file_edit_context` for both requested test files resolved fresh syntax diagnostics with zero errors. `test_analysis_status_concurrency.py` directly imports both production owners; `test_analysis_trigger_docs.py` validates documentation/signatures through the MCP server and documentation index.

Lineage/call-context evidence:

- `get_symbol_lineage` resolved `_write_analysis_job` (`A607/1`), `_execute_analysis_job` (`A1585/1`), and `get_analysis_status` (`A1731/1`) as exact canonical symbols. The selected lineage state was available, metadata-consistent, and semantically anchored.
- `_execute_analysis_job` lineage/call context confirms the persistence edges at current lines 247, 324, and 335, plus the core `_run_analysis_worker` call. The current static call context reports no intra-module caller for the async worker, so cross-module/thread admission is retained as a dynamic/runtime boundary rather than guessed.
- `_start_analysis_job` call context confirms the strict queued write at line 370 and the existing `is_alive()` reuse check at lines 351-353.
- `_active_analysis_jobs` call context confirms its current durable-directory/read path; it has no task-liveness filter yet.
- `contextor_fact_lineage(family="symbol_calls", direction="both", depth=2)` confirms the canonical core-analysis path remains `ContextorFacade.analyze_project` materializing `RepositoryAnalysisState.module_usages[*].symbol_calls`; this is core-analysis ownership evidence, not evidence that the job-persistence owner moved.

Contract boundary established for implementation:

- `_write_analysis_job` may retry only final `PermissionError` from `os.replace`, reusing the already-written temporary file.
- `_start_analysis_job` initial durable acceptance remains strict.
- `_execute_analysis_job` needs phase-specific best-effort persistence for `initial_running`, `progress`, `completed`, and `failed`, while preserving the primary analysis exception and always cleaning in-memory ownership.
- Same-process durable `queued`/`running` jobs require an existing task in `_analysis_tasks` whose `is_alive()` is true; a missing/dead task must be treated as `worker_not_active`.
- Different-process `owner_pid` reconciliation remains `owner_process_changed`.
- Reconciliation persistence failure must not change the returned interrupted response back to stale `queued`/`running`.

### CURRENT_TEST_AND_DOC_EVIDENCE

Existing focused tests currently prove:

- ambiguity for multiple durable active jobs;
- explicit `job_id` bypassing ambiguity;
- deterministic newest-first ordering and five-item response bounding;
- preserving latest terminal selection;
- no mutation from ambiguity enumeration;
- different-process interruption with persisted `owner_process_changed`;
- runtime documentation index/signature behavior.

The requested regression cases A-G are not present in the current focused test files. `test_analysis_trigger_docs.py` currently checks parameter documentation and unchanged trigger signatures; it does not yet assert lifecycle persistence/reconciliation semantics.

Current docs state that a prior process-owned queued/running job becomes `interrupted`, but do not yet describe same-process `worker_not_active` reconciliation or best-effort reconciliation persistence. `analyze_project.json` describes asynchronous acceptance/progress polling but does not yet state the strict pre-start acceptance and best-effort post-start metadata semantics. These are candidate documentation updates after implementation, limited to the material public lifecycle changes.

### IMPLEMENTATION_CONTRACT_VERIFICATION

STATUS=PENDING_IMPLEMENTATION_AFTER_PROCEDUJ.

Planned exact scoped changes after the user releases the gate:

1. `contextor/mcp/analysis_jobs.py`: add `time`, retry constants, bounded `PermissionError` replace retry, `_is_current_process_analysis_task_active`, same-process active filtering, and phase-aware best-effort persistence without changing the core-analysis owner.
2. `contextor/mcp/tools/get_analysis_status.py`: retain cross-process reconciliation and add current-process `worker_not_active`; catch reconciliation `OSError` while returning the interrupted runtime response and diagnostic context.
3. `tests/mcp/tools/test_analysis_status_concurrency.py`: add focused persistence/reconciliation regression coverage A-H using deterministic mocks; no sleep-based ordering oracle.
4. `contextor/mcp/docs/get_analysis_status.json` and `contextor/mcp/docs/analyze_project.json`: update only materially changed public lifecycle/reconciliation semantics.
5. Do not edit `contextor/mcp/tools/analyze_project.py` unless a later exact discovery proves the owner moved; current discovery does not prove that.

### FOCUSED_TESTS

NOT_RUN. No implementation has been performed; the required focused command is reserved for the post-edit gate:

```text
& .\\.venv\\Scripts\\python.exe -m py_compile contextor/mcp/analysis_jobs.py contextor/mcp/tools/get_analysis_status.py tests/mcp/tools/test_analysis_status_concurrency.py tests/mcp/tools/test_analysis_trigger_docs.py
& .\\.venv\\Scripts\\python.exe -m pytest tests/mcp/tools/test_analysis_status_concurrency.py tests/mcp/tools/test_analysis_trigger_docs.py -q
```

NO_FULL_PYTEST=YES.

### RESTART_REQUIREMENTS

No restart was performed at discovery stage. After production MCP source changes, `MCP_SERVER_RESTART_REQUIRED=YES` is expected before any post-implementation runtime certification. No production `analyze_project` runtime validation or manual production job-state mutation is authorized before focused tests pass.

### FILES_CHANGED

Production/test/docs source files changed: NONE at discovery stage.

`walkthrough.md` is the mandatory report channel and is excluded from the task source/test/docs change set.

### ACTUAL_DIFF

ACTUAL_DIFF=DIFFS=NONE for every production, test, and documentation source file at discovery stage.

### EVIDENCE_CLASSIFICATION

- `DIRECT_EVIDENCE`: current HEAD/status, exact Contextor symbol implementations, current module context, current tests/docs, and current MCP documentation contracts.
- `CODE_PATH_PROVED`: current persistence/reconciliation owners and call boundaries listed above.
- `CONTRACT_PROVED`: requested retry scope, strict initial acceptance, phase names, exception precedence, active-task reconciliation, and focused-test scope are taken from the supplied task contract and checked against the current owner paths.
- `INFERENCE`: documentation files are expected to need updates because the requested lifecycle semantics are public; exact wording remains pending implementation.
- `UNKNOWN`: post-change focused test result, runtime restart freshness, and live certification are intentionally not established yet.

### NEXT_STEP

STOP. Await the explicit user command: `proceduj`.
