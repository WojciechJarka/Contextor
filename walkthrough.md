# L37/L38 publication contract evidence

## CURRENT_HEAD

- Repository: C:\Temp\Contextor_Repo
- Git HEAD: 2bf9c6ab1216d87e4c0602c51a887c1f052398a9
- Pre-report git status was clean. No tests were run.
- Contextor MCP discovery used deferred symbol-lineage, symbol-call-context, module-blast-radius, source-range, symbol-implementation, fact-lineage, and centralized-documentation tools before literal source verification. The Contextor live canonical revision was 1639 and canonical state was fresh. Broad module blast-radius and lineage projections reported workspace_sync=unverified; the fetched build_state_freshness implementation reported workspace_sync=verified for its own target. These are different query scopes and are not treated as proof that disk snapshot revision equals daemon revision.
- Evidence labels: CODE_PATH_PROVED means directly visible control/data flow in source; CONTRACT_PROVED means an explicit API/documentation/test contract; DIRECT_EVIDENCE means a current tool or repository observation; INFERENCE means a conclusion derived from proved steps; UNKNOWN means source/tool scope cannot establish the claim.

## EXACT_PUBLICATION_IMPLEMENTATIONS

### FULL analysis publication

Source: C:\Temp\Contextor_Repo\contextor\core\api\facade.py

- ContextorFacade.analyze_project signature and owner contract: lines 556-612. It accepts owner, default desktop_analysis.
- Revision/origin preparation: lines 1056-1088. It maps writer to mcp when owner contains “mcp”, otherwise desktop. Origin is passed through only for desktop_analysis, mcp_analysis, cli_analysis; other owner strings fall back to desktop_analysis.
- Complete publication section: lines 1075-1291. Current ordering:
  1. Read disk metadata in the caller process at line 1079.
  2. Compute target_revision as metadata.revision + 1, or 1 when metadata is absent, lines 1080-1084.
  3. Build FileState payload for that revision, lines 1091-1099.
  4. Call save_engine_state with exact_revision=target_revision and repository identity, lines 1107-1116.
  5. Only when save_engine_state returned metadata (meta is not None), connect to an existing LIVE service and call client.publish(state, origin=origin), lines 1134-1148.
  6. Interpret a dict with status=ok and non-null revision as success; error response dicts become failed; missing client becomes not_attempted; exceptions become timed_out only for TimeoutError and otherwise failed, lines 1151-1179.
  7. Attach live_publish_status/revision/warning to the analysis result and summary, lines 1269-1277; return at line 1291.
- save_engine_state catches any Exception and returns None rather than re-raising: C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:457-483. Therefore a failed durable save does not enter the facade's meta-is-not-None publication block. The facade initializes status to not_attempted at facade.py:1058-1060. No rollback of a previously committed snapshot appears in the post-save publication error handling.
- CODE_PATH_PROVED: FULL facade persistence precedes publication. Publish failure does not undo the successful snapshot write.

### Scoped single-file publication

Source: C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1483-1745 (complete method); publication/update segment: lines 1530-1603.

- It resolves canonical state, then hydrates an IncrementalAnalysisEngine and calls engine.update_file. If status is UPDATED and a hydrated client exists, it calls hydrated.client.publish(analysis_state, origin="scoped_analysis", timeout=5.0), lines 1564-1593.
- The returned dict is not assigned or inspected. Only selected raised transport/runtime exceptions are caught at lines 1594-1596, and those exceptions only produce a log warning. The method has no live_publish_status result; its documented return is a report output path (signature/docstring lines 1484-1492).
- There is no save_engine_state/save_snapshot call in this publication branch. The incremental engine constructor assigns self.state = state at C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:88-104; update_file begins at lines 453-524. Literal revision search across that incremental engine package found no revision assignment. INFERENCE: an ordinary hydrated state with revision R is passed after a content update still carrying R, and the server rejects it as stale. This is not a runtime execution or test result. Regardless of that inferred rejection, the caller ignores a returned error dict.

### Generic LIVE publish and transport

Source: C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py

- Complete CanonicalLiveServer._execute_publish: lines 1203-1259.
- It serializes with _mutation_execution_lock and _lock, reads only self._revision, and sets expected_revision=self._revision+1. A candidate lower than expected returns non_monotonic_canonical_revision; a candidate greater than expected returns canonical_revision_discontinuity; absent revision is bound to expected_revision. It then marks provenance, replaces self._state, updates self._revision, records a publish event, and returns {status, revision, seq}. There is no persister call, disk metadata read, FileState validation, or writer-admission acquisition in this implementation.
- Revision parser/binder: lines 406-445. Boolean, non-integer, or negative revisions are invalid; missing/None revision is represented as absent and can be bound.
- Provenance marker: lines 448-460. It sets state.provenance="live"; it does not verify persistence.
- _dispatch publication branches: lines 1528-1540; operation=publish calls _execute_publish directly at line 1537. The direct update_file branch at line 1535 calls _execute_update_file.
- LiveStateClient.publish signature and complete implementation: lines 1879-1888. The public method accepts state, origin, timeout and forwards a publish request. It has no persistence token/revision parameter or local durable verification.
- Server snapshot/ping reads: _dispatch lines 1580-1613 returns the daemon's self._revision and self._state under the server lock. LiveStateClient.snapshot at lines 1860-1861 is only an IPC request wrapper.
- In serve_forever, _dispatch completes before connection.send(response), lines 1175-1189. A send/connection failure after the publish handler has committed is not rolled back by that transport code. CODE_PATH_PROVED; no claim that a particular production failure did occur.

### Scoped update_file server commit

Source: C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1271-1514 (complete method); relevant validation/persist/commit: lines 1350-1448.

- _execute_update_file holds _mutation_execution_lock, captures previous LIVE state/revision, and derives expected_revision=previous_revision+1 (method start, lines 1271-1285).
- It validates the candidate revision and final revision parity before persistence, then calls configured persister(candidate_state, expected_revision), lines 1370-1398.
- Persistence exceptions return canonical_persistence_revision_conflict or canonical_persistence_failed without replacing LIVE state. If the exception carries current_revision, the response includes persisted_revision and resync_required=true, lines 1399-1418.
- After successful persister return, it rechecks prior state/revision. It then commits candidate state and expected revision at the explicit ATOMIC COMMIT BOUNDARY, lines 1420-1442, and records update event lines 1443-1465.
- The production service supplies _repository_updater, _repository_persister and _repository_mutation_guard when constructing the server: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1499-1517.
- The direct update_file dispatch at ipc.py:1534-1535 bypasses _execute_queued_update_file. Queued execution wraps the update in _mutation_guard at ipc.py:1261-1270.

### Durable snapshot and load

Source: C:\Temp\Contextor_Repo\contextor\core\live_state\store.py

- LiveStateMetadata identity/revision/generation fields: lines 469-480.
- read_metadata reads the metadata pointer without unpickling the state: lines 1410-1438.
- save_snapshot revision and identity validation: lines 1490-1592. It obtains the disk lock before reading current metadata; checks existing repo_id and normalized root; exact_revision must be a nonnegative int, must be 1 for a new snapshot, and otherwise must equal current metadata revision + 1. Exact generations use revision-specific engine_state and file_state names.
- Metadata records state_id, revision, writer, repo_id, root_path, state_file, file_state_file and lineage_manifest_file: lines 1610-1655.
- Snapshot/file-state payload and temporary files are written and fsynced before metadata pointer replacement; metadata pointer replacement is the final commit step: lines 1695-1797 (the commit and os.replace lines are 1768-1797). This is the disk-side generation commit; it is not a LIVE publication transaction.
- load_snapshot complete implementation: lines 1866-2273. The metadata selection and identity/revision checks are at lines 1866-1945: it validates requested state_id/repo_id/root, selects metadata.state_file when present, loads that generation, and rejects embedded metadata whose revision or lineage-manifest pointer disagrees with the selected metadata.
- _repository_persister: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1147-1254. It calls save_snapshot with writer=live-service and exact_revision, verifies returned metadata revision, and rolls back its registry checkpoint if snapshot persistence raises. This rollback is scoped to failed persistence, not later generic publish failure.

### Authoritative state resolver and startup

- resolve_authoritative_repository_state complete implementation: C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py:29-82. It first connects to LIVE and takes ping/snapshot. If that succeeds, it returns that state; it does not read/compare snapshot metadata. Disk metadata/load is fallback only when LIVE state is absent or transport fails.
- hydrate_repository_engine: hydration.py:84-107 creates IncrementalAnalysisEngine from the resolved state and returns the client/revision/source.
- Service startup: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1380-1517 loads snapshot using expected repository identity, reads metadata revision, then constructs CanonicalLiveServer(state, revision=revision, persister=..., mutation_guard=...). For a valid snapshot, restart initialization is disk-snapshot based.
- Desktop startup comparison: C:\Temp\Contextor_Repo\contextor\ui\gui.py:1363-1424 loads disk state and obtains client.snapshot(), compares state revision and state_id, and only after a mismatch acquires startup_publish writer admission and calls publish. The two reads/comparison occur before acquire_full_analysis at lines 1386-1395. The later publish is under that lease, but the earlier comparison is not protected across the interval.
- The exact disk-vs-canonical freshness helper is C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py:302-483; generation mismatch helper is lines 486-555. It checks canonical state/FileState state_id and revision, and reads metadata.file_state_file raw generation metadata. For a resolved target file it compares SHA-256 when present; if no hash exists, matching mtime+size yields metadata_match, not content proof. It is a query freshness check, not invoked by _execute_publish and does not acquire the repository writer lease.
- Public docs: C:\Temp\Contextor_Repo\contextor\mcp\docs\get_symbol_implementation.json:26-31 and get_module_context.json:21 describe workspace_sync as disk-file versus canonical-source freshness; canonical_revision is hydration-bound, and provenance is live or snapshot. The values verified, metadata_match, out_of_sync and unverified are not a durable-versus-LIVE publication admission status.

## COMPLETE_CALLER_INVENTORY

Contextor discovery was performed before literal verification:

- get_symbol_call_context documents its graph as intra-module only. It confirmed the direct _dispatch -> _execute_publish edge at ipc.py:1537 and serve_forever -> _dispatch at ipc.py:1178. The same tool returned zero intra-module caller edges for LiveStateClient.publish, ContextorFacade.analyze_single_file and save_engine_state; this is not evidence that cross-module callers do not exist.
- get_module_blast_radius returned direct module-consumer projections for facade (38 modules), ipc (18), state_manager (85), store (26) and runtime (19). These are module/artifact reachability facts, not function-level Python callers. The facade list includes cli, full_analysis_coordinator, mcp.analysis_jobs, mcp_worker and ui.gui; the state_manager list includes facade, live_state.runtime, and mcp.tools.update_file.
- get_symbol_lineage resolved the exact identities for analyze_project, analyze_single_file, save_engine_state and _execute_publish. It is semantic value lineage, not a complete dynamic Python call graph.
- Literal production-source verification at HEAD 2bf9c6a found:

| Requested symbol | Static production call sites verified |
|---|---|
| LiveStateClient.publish | C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1147 (FULL after save); facade.py:1589-1593 (single-file incremental caller); C:\Temp\Contextor_Repo\contextor\ui\gui.py:1402-1405 (publish state loaded from disk during startup). |
| CanonicalLiveServer._execute_publish | C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1537 through _dispatch. Its server request handler call is serve_forever -> _dispatch at ipc.py:1175-1186. |
| ContextorFacade.analyze_single_file | C:\Temp\Contextor_Repo\contextor\cli.py:113; C:\Temp\Contextor_Repo\contextor\mcp_worker.py:46; C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:283-286; C:\Temp\Contextor_Repo\contextor\ui\gui.py:1630-1632. MCP tool entry C:\Temp\Contextor_Repo\contextor\mcp\tools\analyze_single_file.py:7-24 queues operation=single_file through analysis_jobs._start_analysis_job at lines 20-22. |
| save_engine_state | C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1107-1116; C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:82-89, called only by the local/no-LIVE _persist_live_engine fallback at update_file.py:73-104. |

FULL analysis wrappers found in production: run_full_analysis_exclusive is called by cli.py:95, gui.py:1091 and 1463, mcp_worker.py:32-35, mcp/analysis_jobs.py:244-251, and core/analysis/profile_runner.py:25-28. The wrapper invokes ContextorFacade.analyze_project at full_analysis_coordinator.py:656 and releases its lease in finally at lines 681-682. The facade itself does not acquire that lease internally.

The source scan found no additional explicit production .publish(...) calls. This does not prove there are no reflective, injected, monkeypatched or alias-based dynamic calls; those remain UNKNOWN. The Contextor call graph’s documented intra-module scope has the same limitation.

## REVISION_AND_DURABILITY_CONTRACT

### Publication response and monotonicity

- CODE_PATH_PROVED: generic publish validates candidate revision against daemon memory, expected=current LIVE revision + 1; it rejects lower/equal as non_monotonic_canonical_revision and greater as canonical_revision_discontinuity. Missing revision is bound to expected. Success returns canonical revision and a separate event sequence number (ipc.py:1203-1259; revision helper ipc.py:406-445).
- The event origin is request metadata recorded in the publish event/trace (ipc.py:1257-1259); state provenance is separately set to live (ipc.py:448-460). The publish response itself has no origin, persistence identity, persisted_revision or durable-generation field.
- The public status response carries live_publish_status, live_publish_revision and live_publish_warning for project jobs. Source mapping: facade.py:1151-1179 and mcp/analysis_jobs.py:340-352. A project with unsuccessful publication can still have job status completed and an explanatory message, analysis_jobs.py:392-404.
- Direct update_file responses differ: persistence conflict responses can carry persisted_revision and resync_required, ipc.py:1399-1418. Generic publish failures do not carry that durable comparison.

### Durable identity and generation

- Disk exact-revision sequence is checked independently under snapshot lock by save_snapshot: first exact revision 1; then current disk revision + 1 (store.py:1497-1574).
- Snapshot identity consists of state_id, repo_id, normalized root_path, writer and generation references. load_snapshot checks supplied state/repository/root identity and embedded revision/lineage pointer consistency (store.py:1610-1655, 1866-1945).
- FULL reads metadata and saves target revision in the analysis caller process, then contacts LIVE. _repository_persister performs save_snapshot from the LIVE service process on update_file. Generic publish performs no disk access in either process path.
- Active LIVE revision is owned/read by the server process through ping/snapshot under its lock (ipc.py:1587-1611); the client process only transports the RPC (ipc.py:1748-1808, 1859-1861). Durable metadata is read by whichever process calls read_metadata/save_snapshot. In FULL that is the analysis caller; in server update persistence it is the LIVE service process; at startup it is the service process.
- The source-level comparison mechanisms are:
  1. GUI startup loads disk generation and reads active LIVE snapshot then compares revision/state_id; this occurs before startup writer admission (gui.py:1363-1407).
  2. build_state_freshness compares the supplied canonical state's revision/state_id with FileState generation metadata and optionally hashes the target file (query_helpers.py:302-483, 486-555). It is not a publisher gate.
  3. Normal server update derives expected revision from its active LIVE revision and calls save_snapshot(exact_revision=expected_revision), which verifies that the committed disk metadata is exactly the predecessor revision before LIVE commit (ipc.py:1271-1448; runtime.py:1147-1222; store.py:1497-1574).
  4. Generic publish has no corresponding comparison.
- CONTRACT_PROVED from get_live_events docs: latest_revision is the authoritative canonical revision; its journal is an ephemeral in-RAM feed, not durable history. Source/API doc: C:\Temp\Contextor_Repo\contextor\mcp\docs\get_live_events.json:12-22.
- No active daemon: runtime.connect only returns a verified existing client or None; it does not start one (runtime.py:616-631). FULL still saves first and reports not_attempted when connect returns None (facade.py:1134-1171). Scoped analysis resolves disk fallback and its publish condition requires hydrated.client not None (hydration.py:29-82; facade.py:1564-1596).
- Persistence-before-publication is true in the FULL facade path and the GUI startup path (snapshot is loaded from disk before startup publish). It is not enforced by LiveStateClient.publish or _execute_publish. The API accepts a missing revision by binding it, and a next revision by assigning LIVE state without calling the configured persister. No public documentation states a generic publish durability precondition.

## WRITER_ADMISSION_BOUNDARIES

- FULL analysis through run_full_analysis_exclusive acquires writer_kind=full_analysis before calling the facade and releases in finally (C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:606-693).
- The facade method itself has no writer acquisition. Current standard FULL production wrappers use the coordinator listed above; direct facade calls also exist in tests.
- Generic publish admission is only the per-server _mutation_execution_lock and state lock. _dispatch publish has no mutation guard and _execute_publish has no configured persister (ipc.py:1203-1259, 1528-1537).
- Queued update_file goes through _execute_queued_update_file and the configured mutation guard (ipc.py:1261-1270); runtime guard acquires/releases the shared full-analysis coordinator lease with writer_kind=live_mutation (runtime.py:1257-1292).
- Direct update_file dispatches straight to _execute_update_file (ipc.py:1534-1535), so it uses server mutation serialization and persistence-before-live-commit but bypasses that queued shared writer guard. The MCP update_file tool uses LiveStateClient.update_file in its connected-service path (mcp/tools/update_file.py:212-228; ipc.py:1890-1892).
- GUI startup publication acquires startup_publish admission only after loading/reading disk and LIVE values (gui.py:1363-1407). Scoped analyze_single_file has no visible shared writer admission in the method; its callers include CLI/MCP worker/GUI paths that invoke it directly.

## FULL_FAILURE_TEST_EVIDENCE

No tests were run. The following complete test functions and fixture/setup ranges were retrieved and inspected through Contextor source-range calls.

- Shared H3A setup: C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py:1-77. The module is marked live; an autouse fixture isolates CONTEXTOR_CACHE_DIR and CONTEXTOR_STATE_DIR under tmp_path. _setup_repo creates pkg.mod_a.compute_data and pkg.mod_b.run, initializes repository identity. _start_authoritative_live verifies endpoint schema/domain/service instance/lease/process identity; _stop_authoritative_live shuts down and waits for endpoint removal.
- Complete test_h3a_case_u_active_daemon_publish_raises_failure_semantics: same file, lines 1012-1078. It creates durable baseline P0, starts LIVE at P0, edits mod_a, monkeypatches LiveStateClient.publish to raise ConnectionResetError, runs full analysis, and asserts disk snapshot/FileState P1 while daemon stays P0; facade result is failed with revision=None and warning containing exception. The monkeypatch raises instead of invoking the server, so it does not test post-commit response loss.
- Complete test_h3a_case_v_active_daemon_publish_failure_response_dict: lines 1081-1143. It uses the same setup but returns a synthetic error dict. It asserts disk/FileState P1, daemon P0, status failed, revision=None and warning=daemon_busy_rejecting_publish. It also does not execute the real server's publish handler.
- Normal update persistence tests in C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py:
  - test_persister_runs_after_validation_before_canonical_exposure, lines 942-962: the persister observes old server state/revision/event sequence; after it returns the candidate is exposed at revision 1.
  - test_persistence_conflict_fails_closed_without_live_event, lines 965-991: a SnapshotRevisionConflict yields canonical_persistence_revision_conflict/resync_required and leaves state, revision, event sequence, events and diagnostics unchanged.
  - test_real_repository_persister_disk_ahead_fails_closed, lines 994-1037: real metadata is at revision 11 while server is at 10; update returns conflict with persisted_revision=11 and resync_required, retains LIVE revision/state 10, retains disk 11, and emits no update event.
- Queued persistence regressions in C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py:
  - Complete common setup/helpers lines 1-92: live marker; _running_server starts serve_forever and guarantees close/join; _wait_for_terminal polls mutation status.
  - test_candidate_is_invisible_during_slow_persistence, lines 493-525: a blocked persister leaves snapshot/revision/event sequence on the previous generation until release, then exposes revision 1.
  - test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged, lines 528-564: queued conflict ends failed while old state/revision/event journal/diagnostic trace remain unchanged.
- The same test file's test_publish_and_queued_update_are_single_writer_serialized, lines 734-785, constructs CanonicalLiveServer without a persister, completes a queued update to revision 1, then directly publishes a state with no revision; generic publish binds it to revision 2 and returns success. This is direct test evidence that generic in-memory publish accepts an unpersisted successor when no persistence hook is configured.
- Existing source/test evidence distinguishes pre-commit persistence failure from FULL post-save publication failure. No retrieved test simulates the server committing publish and then losing its response, or abrupt process termination at the publication boundary.

## SCOPED_CALLER_EVIDENCE

- The scoped facade's state comes from resolve_authoritative_repository_state, which prefers LIVE and falls back to disk only when no usable LIVE state is returned (hydration.py:29-82). It constructs an incremental engine from that exact state/client (hydration.py:84-107), updates the selected file, and then attempts generic publish only for UPDATED and a non-null client (facade.py:1564-1596).
- No canonical snapshot save is in that scoped publication branch. Literal source search found no save_engine_state/save_snapshot call in the incremental engine update implementation; engine.py constructor stores the supplied state and no revision write appears in the engine package. INFERENCE: with an ordinary LIVE candidate already carrying revision R, the unchanged revision is below server expected R+1, so generic publish returns non_monotonic_canonical_revision. The facade ignores that response dictionary, so it cannot surface that error through its return value.
- The MCP job runner calls ContextorFacade.analyze_single_file and discards its return, then returns an empty analysis outcome for the single_file branch (analysis_jobs.py:282-289). Job initialization sets publication status to not_applicable for non-project operations (analysis_jobs.py:440-446).
- Public MCP wrapper C:\Temp\Contextor_Repo\contextor\mcp\tools\analyze_single_file.py:7-24 enqueues a single_file job. Direct production callers are listed in COMPLETE_CALLER_INVENTORY.
- Separate from analyze_single_file, MCP update_file connected-service path calls LiveStateClient.update_file, whose configured server path persists before canonical LIVE commit; its local no-service fallback calls _persist_live_engine/save_engine_state and updates the local cache revision only after non-None persistence (mcp/tools/update_file.py:73-104, 212-245). This separate API does not call generic publish.

## MINIMUM_CHANGE_SURFACES

Ownership/source inventory only; no design or edit proposal.

A. Publication admission behavior is owned by LiveStateClient.publish and the publish dispatch/handler: C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1203-1259, 1528-1537, 1879-1888. Current production call sites are facade.py:1147, facade.py:1589-1593 and ui/gui.py:1402-1405.

B. Durable revision comparison and FULL durable-new/LIVE-old reporting/recovery boundaries are the FULL facade write/publish section C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1079-1179; snapshot metadata commit and loader C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1497-1592, 1610-1655, 1760-1802, 1866-1945; service startup C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1380-1517; LIVE-first resolution C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py:29-82; GUI comparison C:\Temp\Contextor_Repo\contextor\ui\gui.py:1363-1407; generation freshness/status projection C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py:302-555 and mcp/analysis_jobs.py:320-425.

C. Surfacing scoped publish result is owned at the attempted call and response handling C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1587-1596, then propagated (or discarded) by the direct callers; MCP job outcome/status is C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:282-289, 340-412, 440-446 and public wrapper docs C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json:16-17.

## CONTRACT_CONFLICTS

1. Documentation/source mismatch — live_publish_revision meaning. get_analysis_status docs say it is the LIVE publish/event journal revision, “not canonical state publication revision” (C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json:16-17). Source sets it from published["revision"] (facade.py:1151-1158); _execute_publish returns self._revision as revision and a distinct evt["seq"] as seq (ipc.py:1254-1259). CODE_PATH_PROVED conflict with documented semantics.
2. Documentation/source mismatch — scoped single-file publication. The same docs say layer/single-file jobs are not_applicable because the facade updates incrementally “rather than publishing a new global baseline” (get_analysis_status.json:17). The facade actually calls hydrated.client.publish for an UPDATED file when a client exists (facade.py:1587-1596). The job runner still marks single-file publication not_applicable and discards the method result (analysis_jobs.py:282-289, 440-446). CODE_PATH_PROVED conflict.
3. Requirement A versus current generic publish capability. No persistence prerequisite appears in the public LiveStateClient.publish signature, dispatch, or handler. The handler accepts a missing revision by binding it and installs a valid next revision without persister or disk comparison; an existing test uses a server without a persister and asserts success (ipc.py:1203-1259, 1879-1888; test_live_mutation_coordinator.py:734-785). This is a verified capability mismatch with a requirement that generic publication reject unpersisted state. No retrieved public API documentation promises that persistence-free publication must be supported; therefore the existence of a contrary documented guarantee is UNKNOWN.
4. Requirement B versus current FULL API. Disk revision is chosen from snapshot metadata and committed before publish; LIVE validates only its own next revision. On publish failure there is no snapshot rollback or automatic reconciliation in the facade. If disk is already P1 and LIVE remains P0, a later FULL run chooses target P2 while the server expects P1 and rejects P2 as discontinuity. This is a source-derived INFERENCE from facade.py:1079-1116, ipc.py:1222-1242, and store.py:1540-1574; no test was run for this second-run sequence.
5. Requirement C versus current scoped API. analyze_single_file exposes only a report path, ignores returned error dictionaries, and MCP single-file job status remains not_applicable. This does not provide a scoped publication failure status contract. CODE_PATH_PROVED. The public docs currently describe no publication attempt for this job, which conflicts with the source path as item 2 records.
6. workspace_sync contract is about file-content freshness relative to canonical analysis state, not durable-vs-LIVE publication authority. It is therefore not an API contract for preventing or recovering an authority revision split.

## MISSING_EVIDENCE

- UNKNOWN: no static source search or intra-module call graph can rule out reflective, alias-based, monkeypatched or injected production calls to publish/analyze_single_file/save_engine_state. The verified inventory is the complete explicit lexical call-site set found at current HEAD.
- UNKNOWN: no public contract was found that states a generic publish must or may persist first; current source behavior and in-memory regression tests establish capability, but the intended external persistence precondition is not declared.
- UNKNOWN: whether a real production caller currently manages to publish an unpersisted next-revision state. The static scoped caller sends an incremental state without a visible revision increment; stale rejection is an inference and the response is discarded.
- No test evidence was found for response loss after server-side publish commit, abrupt process termination after commit, or restart recovery from those exact crash points. Source ordering proves commit precedes response send; it does not prove a crash occurred.
- Contextor module blast-radius and lineage projections were fresh canonical revision 1639 but workspace_sync=unverified at broad module scope. Literal implementation ranges were retrieved and checked against Git HEAD; do not treat broad MCP workspace_sync as a per-file source verification result.

## FILES_CHANGED

- Production files: NONE.
- Test files: NONE.
- Documentation files: NONE.
- walkthrough.md is the required report output only and is excluded from source/test change inventory.

## ACTUAL_DIFF

NONE for production, tests and documentation. No tests run.

