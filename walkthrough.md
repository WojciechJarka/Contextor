# L37 / L38 Durable and LIVE Authority Discovery

## CURRENT_HEAD

- Repository: C:\Temp\Contextor_Repo
- HEAD: c23692a38eea6c2cdc2be2e74d9f51238ee72907
- Contextor-first discovery: deferred Contextor tools were located; current MCP source evidence was read with workspace_sync=verified at canonical revision 1639. Discovery used get_symbol_lineage, contextor_fact_lineage, get_symbol_implementation and get_source_range for the full-analysis facade/coordinator, Live server update/publication, runtime persistence and hydration paths. Git/source inspection below is literal verification, not the architecture source of record.
- No tests were run. No production or test file was edited.

Evidence labels:
- CODE_PATH_PROVED: control flow in the checked-out implementation establishes the statement.
- DIRECT_EVIDENCE: an existing focused test asserts the stated behavior; tests were not executed in this task.
- CONTRACT_PROVED: documented/exposed call contract establishes the behavior.
- INFERENCE: consequence derived from source ordering, not an executed process-crash observation.
- UNKNOWN: source/contract does not establish the claim.

## L37_FULL_ANALYSIS_CHAIN

### Entry, lease, candidate and identity

1. MCP project analysis enters _start_analysis_job through C:\Temp\Contextor_Repo\contextor\mcp\tools\analyze_project.py:7-18; the project job calls run_full_analysis_exclusive in C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:230-300. GUI and CLI also call the exclusive coordinator (C:\Temp\Contextor_Repo\contextor\ui\gui.py:1091-1097; C:\Temp\Contextor_Repo\contextor\cli.py:95). CODE_PATH_PROVED.
2. acquire_full_analysis in C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:410-581 takes the canonical writer admission gate, process lock and OS lock and returns a lease. run_full_analysis_exclusive at :606-693 calls ContextorFacade.analyze_project while holding that lease and releases it in finally at :681-682. Admission gate cleanup is in _canonical_writer_admission at :122-205; OS/process lock cleanup is in release_full_analysis at :584-603. CODE_PATH_PROVED.
3. ContextorFacade.analyze_project spans C:\Temp\Contextor_Repo\contextor\core\api\facade.py:557-1291. It initializes repository identity through _initialize_repository_identity at :252-261; then indexes and constructs the full candidate through the indexing/pipeline sections at :675-1050. The candidate RepositoryAnalysisState includes modules, artifacts, graph, canonical artifact-consumption, module usages, lineage and other full-analysis state before persistence. CODE_PATH_PROVED.
4. Full analysis does not wrap candidate construction in a persistent identity-registry write transaction. _initialize_repository_identity calls ensure_initialized; PersistentIdentityRegistry.ensure_initialized at C:\Temp\Contextor_Repo\contextor\core\reporting_engine\persistent_registry.py:121-127 enters a write transaction only when required registry files are absent. Lineage materialization uses a registry read_transaction in facade.py:264-478 (read scope at :304). The full method itself has no registry transaction() call; the two facade write-transaction call sites found are facade.py:1420 and :1643, outside analyze_project. CODE_PATH_PROVED.
5. Registry transactions are their own durable unit. PersistentIdentityRegistry.transaction at persistent_registry.py:200-263 writes temp registry files and a committing journal, replaces registry files, removes the journal and releases its lock. _recover_transaction at :172-197 recovers that registry journal only. It does not encompass the engine snapshot pointer or LIVE server state. CODE_PATH_PROVED.

### Snapshot then publication

6. analyze_project computes target revision and a FileState payload at facade.py:1080-1105, then calls save_engine_state(... exact_revision=target_revision, file_state_payload=file_state_payload) at :1106-1116. The publication branch is explicitly guarded by if meta is not None at :1134. CODE_PATH_PROVED.
7. save_engine_state in C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:457-483 wraps save_snapshot, catches exceptions and returns None. Consequently a returned None skips FULL publication at the facade gate; failure is reflected in status, not rolled back through a cross-store transaction. CODE_PATH_PROVED.
8. save_snapshot in C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1462-1835 writes the engine generation and associated FileState/lineage material, flushes/fsyncs files, writes/fsyncs metadata temp, then commits metadata with os.replace(meta_tmp, meta_file) at :1768-1797. FULL passes exact_revision, so committed metadata points at a versioned state generation; the default no-exact-revision path has a separate base-pickle replacement at :1784-1793. The FileState payload must match exact_revision (:1729-1752). CODE_PATH_PROVED.
9. Only after save_engine_state returns non-None does analyze_project connect and call client.publish(state, origin=origin) (facade.py:1130-1147). A non-ok response becomes failed at :1151-1167; thrown exceptions are caught at :1172-1179 and recorded failed/timed_out. There is no disk rollback or LIVE rollback in this exception handler. The facade proceeds to return its analysis result. CODE_PATH_PROVED.
10. LiveStateClient.publish at C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1879-1888 only sends the publish request. CanonicalLiveServer._execute_publish at :1203-1259 validates candidate revision, marks provenance and assigns self._state and self._revision at :1254-1257; it calls no snapshot persister. _dispatch routes publish straight to this method at :1536-1537. CODE_PATH_PROVED.
11. IPC server ordering is dispatch then response send: CanonicalLiveServer.serve_forever, ipc.py:1175-1186. If dispatch commits and response send then fails, caller may report a transport error after server memory already changed. This is a possible lost-response boundary, not an observed runtime event. CODE_PATH_PROVED for order; INFERENCE for the concrete transport outcome.

### FULL failure boundary

- Save failure before metadata commit: save_engine_state catches and returns None; FULL does not invoke publish because of the meta is not None guard. A partially written generation can be orphaned, but exact-revision metadata still points to the previous generation until pointer replacement. CODE_PATH_PROVED.
- Metadata pointer commit succeeds, connect fails / no client / publish returns error / publish raises: durable authority is the new snapshot; current LIVE server can remain on its previous state. There is no cross-authority rollback. Focused tests test_h3a_case_u_active_daemon_publish_raises_failure_semantics and test_h3a_case_v_active_daemon_publish_failure_response_dict assert disk/FileState at new revision while daemon remains at old revision (details in EXISTING_TEST_EVIDENCE). DIRECT_EVIDENCE.
- Publication dispatch succeeds but response delivery fails: in-memory server may be new while caller records failure. Since the snapshot was already committed in the FULL path, disk is still new. CODE_PATH_PROVED/INFERENCE.
- Writer lease release is in run_full_analysis_exclusive.finally (full_analysis_coordinator.py:681-682). It serializes cooperating writers; it is not a rollback or atomic commit spanning snapshot and daemon state. CODE_PATH_PROVED.

## L38_SCOPED_LIVE_CHAIN

### Normal canonical service update

1. run_service loads a snapshot, reads metadata/revision, and creates CanonicalLiveServer with _repository_updater, _repository_persister, and _repository_mutation_guard (C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1395-1410, :1480-1515). CODE_PATH_PROVED.
2. Desktop queued update dispatch goes through submit_update_file and mutation coordinator (C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1530-1533); _execute_queued_update_file acquires the configured mutation guard (:1261-1269). _repository_mutation_guard at runtime.py:1257-1292 acquires/releases the same canonical writer lease with writer_kind=live_mutation.
3. Direct LiveStateClient.update_file goes to operation=update_file (ipc.py:1890-1891, dispatch at :1534-1535) and bypasses _execute_queued_update_file's cross-process writer guard. It still enters _execute_update_file and its persistence-before-commit order. CODE_PATH_PROVED.
4. _repository_updater at runtime.py:1102-1144 checkpoints registry state, runs engine.update_file, and restores checkpoint on updater exception. _repository_persister at :1147-1254 calls save_snapshot with exact_revision, matching FileState payload and previous persisted state at :1183-1199. Persistence exceptions restore the registry checkpoint and re-raise (:1200-1220); success clears the checkpoint and advances its remembered persisted state (:1222-1230).
5. _execute_update_file at ipc.py:1271-1512 clones the old state and invokes updater against the candidate. If persister exists, it runs before canonical self._state / self._revision assignment (:~1370-1442); persistence errors return failure without replacing the old state (:1390-1418); successful persistence is followed by a state/revision concurrency check and canonical assignment (:1421-1442). The normal runtime always supplies this persister. Thus the normal service update_file operation cannot publish its candidate before its exact-revision snapshot succeeds. CODE_PATH_PROVED.
6. The persister's exact-revision snapshot uses the versioned metadata-pointer commit order described above. A process death before pointer commit leaves old selected generation; after successful pointer commit but before server-state assignment, restart can select the new durable candidate even though the old server had not exposed it yet. The latter is an INFERENCE from commit order and startup loader.

### Other scoped routes and boundary qualification

7. ContextorFacade.analyze_single_file (C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1484-1601) reuses/hydrates state, calls hydrated.engine.update_file at :1564-1585, then calls hydrated.client.publish(... origin="scoped_analysis") at :1587-1593. There is no snapshot save in this method. It ignores the returned publish response and only catches a small set of transport exceptions at :1594-1596. CODE_PATH_PROVED.
8. The ordinary hydrated candidate retains the loaded canonical revision: the incremental engine update path in C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:453-~720 does not assign or increment state.revision; _apply_delta_and_commit is at :760-1018. A canonical server with current revision r rejects a candidate carrying r, because _execute_publish requires at least r+1 (ipc.py:1222-1233). Therefore the current in-repository analyze_single_file route issues an unpersisted publish attempt but source does not show it successfully changing server authority; it is rejected as non-monotonic when hydrated state has its normal revision. CODE_PATH_PROVED. No test establishes this exact rejection.
9. Separate from scoped update, LiveStateClient.publish is a production method and publish is a server dispatch operation. A caller can send a state carrying exactly current revision+1; _execute_publish accepts it and assigns canonical Live memory with no persister/snapshot call (ipc.py:1203-1259, :1536-1537, client method :1879-1888). Concrete source sequence: durable snapshot P0/revision r and Live P0/r; caller sends P1/revision r+1 via publish; server accepts P1/r+1; process restarts and snapshot loader still selects P0/r because publish wrote no snapshot. This proves an unguarded persistence-free LIVE publication capability. It does not prove that the current analyze_single_file call succeeds, and it is distinct from the normal update_file mutation path. CODE_PATH_PROVED for the accepted branch and missing persistence call; INFERENCE for restart result.
10. Offline MCP update_file fallback is a third state boundary, not a shared Live server commit. C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:212-228 uses live_client.update_file when connected; otherwise it calls engine.update_file first and _persist_live_engine afterward. _persist_live_engine at :73-104 calls save_engine_state without exact_revision/FileState payload and returns False on persistence failure; fallback caller does not restore engine state. C:\Temp\Contextor_Repo\contextor\mcp\runtime.py:311-419 keeps the engine in process cache or hydrates from disk on a fresh process. A failed save can therefore leave that MCP process's engine changed while restart rehydrates old durable state. This is a separate proved local-cache loss path; it is not evidence that the shared CanonicalLiveServer accepted an unpersisted update_file. CODE_PATH_PROVED.
11. The fallback uses default non-exact snapshot mode. save_snapshot replaces the base engine pickle before metadata (store.py:1784-1793); loader checks embedded metadata revision equals external metadata revision and returns None on mismatch (:1928-1929). Abrupt termination between those replacements may make the referenced snapshot unloadable. This is an INFERENCE about the crash window, supported by ordering/validation code; no kill-at-boundary test was found.

## DURABLE_VS_LIVE_ORDERING

| Path | Durable commit | LIVE/in-memory commit | Consequence |
|---|---|---|---|
| FULL project analysis | Exact-revision snapshot and FileState metadata pointer first (facade.py:1106-1116; store.py:1768-1797) | Separate client.publish then server assignment (facade.py:1141-1147; ipc.py:1254-1257) | Publication failure leaves durable new / daemon old. |
| Canonical server update_file | _repository_persister exact snapshot first (runtime.py:1183-1199) | Candidate assignment after persister (ipc.py:1421-1442) | Persistence failure leaves server canonical old. |
| Canonical server queued update | Same as update_file, under mutation guard | Same server assignment after persistence | Cooperating writer exclusion plus persistence-before-exposure; no cross-store registry/snapshot transaction. |
| analyze_single_file | No snapshot call in method | Attempts generic publish; candidate retains old revision and normal server rejects it | No proved successful scoped commit via this caller. |
| Raw LiveStateClient.publish | No snapshot call | Accepts valid next-revision state and assigns server memory | Persistence-free publication can leave disk old across server restart. |
| MCP offline fallback | Update engine first; then best-effort snapshot save | MCP process-local engine changes before save | Save failure has no engine rollback; restart loads old disk snapshot. |

The normal FULL path and normal update_file path have different sequencing around LIVE exposure but neither has a single atomic transaction covering all authorities. The raw publication operation is not coupled to snapshot persistence.

## FAILURE_BOUNDARY_MATRIX

### A. Durable save succeeds; LIVE publication fails

- FULL: confirmed split. Disk snapshot and FileState are revision r+1; daemon may remain r. No rollback. Existing H3A U/V tests assert this state. DIRECT_EVIDENCE + CODE_PATH_PROVED.
- Scoped server update: not the normal sequence; persister occurs before exposure. If persister succeeds and a later canonical revision identity check fails, disk can be ahead of server; _execute_update_file returns canonical_revision_changed_during_update after persistence (ipc.py:1421-1435). CODE_PATH_PROVED.
- Startup usage backfill: exact save is performed before server construction (runtime.py:1433-1478); exception aborts startup. The previous selected generation stays authoritative for metadata-pointer failures; focused test below covers exception recovery. CODE_PATH_PROVED/DIRECT_EVIDENCE.

### B. LIVE publication succeeds; durable save fails

- FULL project chain: save failure returns meta=None, so publish is skipped (facade.py:1107-1116, :1134-1135). This combination is blocked in that chain. CODE_PATH_PROVED.
- Normal scoped update_file: durable save precedes state assignment; save exceptions return before the LIVE commit. This combination is blocked in this path. CODE_PATH_PROVED.
- Raw publish: it does not attempt a durable save, so there is no save exception boundary. It can make LIVE newer while disk remains old. This is the persistence-free capability described in L38_SCOPED_LIVE_CHAIN. CODE_PATH_PROVED.
- Offline MCP fallback: save can fail after process-local engine update; it reports live_state_persisted=False but does not undo the engine update. It is not a shared Live server publication. CODE_PATH_PROVED.

### C. Process terminates immediately after LIVE publication

- FULL: durable exact-revision snapshot was already committed. If daemon process is restarted, it can hydrate that committed revision. If only the publishing client process terminates and daemon survives, daemon memory remains the published revision. CODE_PATH_PROVED for ordering; restart consequence is INFERENCE from startup loader.
- Normal scoped update: exact snapshot commit precedes server assignment, so after assignment both are already at the new revision. CODE_PATH_PROVED; restart consequence INFERENCE.
- Raw publish: no snapshot precedes assignment. Server-process termination followed by restart returns to selected disk snapshot, potentially old revision. CODE_PATH_PROVED/INFERENCE.
- Offline MCP fallback: termination after successful save can recover the new snapshot; termination after failed save loses process-local state. CODE_PATH_PROVED/INFERENCE.

### D. Restart after either partial transition

run_service uses load_snapshot and passes the loaded state/revision into CanonicalLiveServer (runtime.py:1403-1410, :1480-1515). It does not hydrate from the prior daemon's RAM. load_snapshot selects the state file named by current metadata (store.py:1898-1903), verifies embedded revision matches external metadata (:1928-1929) and returns None for rejected/missing state; no older-generation search is shown. Thus after L37 split, restart selects the new FULL snapshot. After raw persistence-free publish, restart selects the old snapshot. CODE_PATH_PROVED for selection; INFERENCE for authority consequence.

## ROLLBACK_AND_RECOVERY

- Snapshot: versioned exact-revision generation writes culminate in metadata-pointer replace (store.py:1768-1797). The old pointer remains until commit. Cleanup in :1799-1835 deletes temp files; it is not a multi-authority rollback.
- Identity registry: transaction journal recovery is limited to registry files (persistent_registry.py:172-197, :200-263). create_checkpoint/restore_checkpoint at :265-313 are in-process exception-recovery mechanisms. The LIVE updater takes a checkpoint and restores on caught updater/persistence exceptions (runtime.py:1102-1144, :1200-1220). Abrupt process termination cannot execute Python checkpoint restoration; registry journaling may independently recover a registry transaction.
- FULL publication: facade catches publication failures but has no code to restore previous metadata or previous daemon state (facade.py:1130-1179). A committed new durable snapshot is retained.
- Scoped server update: persistence exceptions are handled before canonical assignment; old server state/revision/event sequence remain. Registry checkpoint restoration is part of this exception path. CanonicalLiveServer._execute_update_file also rejects a revision/state change detected after persistence; that failure can leave disk ahead.
- Startup: load_snapshot validates the metadata-selected single generation and returns None on invalid/mismatched content; it does not walk backwards through generations (store.py:1866-1930+). load_engine_state wraps loader errors and returns None (state_manager.py:485-504). run_service continues from state=None unless a usage backfill condition applies; no automatic full reanalysis is part of the load itself.
- Workspace resync is a separate Desktop watcher layer. _startup_reconciliation_paths and trust checks are in C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:477-528; poll_once is at :640-718. A GUI-configured on_resync can request run_full_analysis_exclusive (C:\Temp\Contextor_Repo\contextor\ui\gui.py:1435-1485). This reconciliation is not a transaction rollback and depends on watcher startup/callback availability.
- Full writer lock death recovery only recovers admission, not data authority: tests/test_full_analysis_coordination.py::test_cross_process_os_lock_and_process_death_recovery at :399+ exercises lock recovery. It does not establish which snapshot/LIVE authority survives a kill at either commit boundary.

## STARTUP_HYDRATION

- resolve_authoritative_repository_state in C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py:29-82 first tries active LIVE ping/snapshot; on transport errors it uses metadata and load_engine_state. If LIVE snapshot succeeds, it returns that state without comparing it against disk metadata. hydrate_repository_engine at :85-112 wraps the resolved state in an incremental engine/registry/FileStateManager; it does not scan the repository.
- Service startup in runtime.py:1395-1410 calls load_snapshot; optional ensure_module_usages backfill is persisted as exact next revision before server construction (:1433-1478). A backfill exception exits startup; there is no catch-and-select-older-snapshot branch in that sequence.
- CanonicalLiveServer is constructed with loaded state and metadata revision (runtime.py:1480-1515). An invalid snapshot that load_snapshot rejects therefore does not reconstruct the old LIVE state from another generation at this layer.
- migrate_legacy_snapshot at store.py:2277-2311 migrates a legacy snapshot only when target metadata does not already exist. It is not fallback recovery for an existing invalid target snapshot.
- FileStateManager._load at C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:280-355 validates FileState generation identity/revision against engine metadata; mismatch or corruption means the baseline is untrusted.
- Desktop watcher startup reconciliation can detect added/modified/deleted paths with its trusted-file baseline and can invoke full resync when configured. Existing test coverage proves reconciliation of workspace edits after watcher startup, not recovery from forced termination between snapshot replacements or between FULL save and publication.

## EXISTING_TEST_EVIDENCE

Existing tests were inspected, not run.

### FULL save/publication split

- tests/test_h3a_workspace_canonical_freshness.py::test_h3a_case_t_active_daemon_successful_publish (:953-1010): successful FULL save then successful LIVE publish.
- tests/test_h3a_workspace_canonical_freshness.py::test_h3a_case_u_active_daemon_publish_raises_failure_semantics (:1012-1079): publication raises before dispatch; asserts durable snapshot/FileState revision advances and active daemon remains at prior state; status reports publish failure. Direct regression for L37 divergence.
- tests/test_h3a_workspace_canonical_freshness.py::test_h3a_case_v_active_daemon_publish_failure_response_dict (:1081-1139): error response, same durable-new/LIVE-old assertion.
- tests/test_h3a_workspace_canonical_freshness.py::test_h3a_case_i_crash_window_false_verified_prevented (:316-374): injects a T0/T1 disk metadata mismatch and verifies freshness is untrusted; it does not terminate a process during the real save/publish sequence.

### Scoped update persistence order and rollback

- tests/test_live_state_ipc.py::test_persister_runs_after_validation_before_canonical_exposure (:942-962): persister observes old state/revision/event sequence and successful response exposes persisted candidate afterward.
- tests/test_live_state_ipc.py::test_persistence_conflict_fails_closed_without_live_event (:965-992): revision conflict leaves old state/revision and no event.
- tests/test_live_state_ipc.py::test_real_repository_persister_disk_ahead_fails_closed (:994-1035): disk already at r+1; attempted update fails closed and does not advance server state.
- tests/test_live_mutation_coordinator.py::test_candidate_is_invisible_during_slow_persistence (:493-525) and ::test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged (:528-564): candidate invisibility and exception rollback.
- tests/test_live_mutation_coordinator.py::test_generic_snapshot_failure_restores_committed_registry_and_old_canonical_state (:567-700+): injects snapshot exception after registry sync and checks checkpoint restoration / old canonical state; exception recovery, not process-kill recovery.
- tests/test_live_state_ipc.py::test_startup_backfill_failure_leaves_previous_generation_authoritative (:1383-~1445): injected startup metadata-replace failure leaves prior generation selected. Exception path only.
- tests/test_live_state_store.py::test_snapshot_roundtrip_increments_revision_and_records_writer (:89-99), ::test_default_snapshot_publishes_final_pickle_via_temp_replace (:101-111), ::test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock (:113-137), and ::test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite (:139-154) cover store behaviors but not abrupt power/process interruption at every replacement boundary.

### Restart and reconciliation

- tests/test_live_watcher_startup_reconciliation.py::test_startup_reconciles_offline_add_modify_delete_and_is_idempotent (:147-203) proves watcher reconciliation and repeated no-op after successful reconciliation.
- tests/test_mcp_regressions.py::test_incremental_live_state_persistence_roundtrips_for_restart (:2562-2594) proves successful local persistence/reload, not save-failure rollback.
- tests/test_live_single_file_reuse.py::test_single_file_changed_target_falls_back_to_incremental_engine (:57-85) proves the single-file incremental route is called; it does not assert durable snapshot publication or successful canonical Live revision transition.
- No inspected focused test proves an accepted persistence-free LiveStateClient.publish followed by a real backend subprocess restart. The missing test is an evidence gap, not needed to prove the no-persister source branch.
- Existing process-death test tests/test_full_analysis_coordination.py::test_cross_process_os_lock_and_process_death_recovery (:399+) proves lease recovery only. Abrupt termination at save/publish boundaries is untested in the focused inventory.

## SHARED_TRANSACTION_BOUNDARY

L37 and L38 do not share a single cross-authority transaction.

- FULL analysis: writer lease surrounds analyze_project; identity registry initialization/read transaction, snapshot/FileState generation commit, then daemon publication are separate operations. The lease serializes cooperating writers but does not undo committed snapshot state when later publication fails.
- Scoped server update_file: same writer lease is used for queued mutations; direct mutations may skip that outer lease, but both use server mutation lock and persistence-before-state assignment. Registry checkpoint and journal cover registry rollback/recovery only.
- Raw publish: no snapshot persistence or registry checkpoint is called.
- MCP offline fallback: updates MCP process-local engine, then attempts snapshot save without coupling cache engine rollback to disk transaction.
- These are independent ordering mechanisms around a shared snapshot store, not one atomic journal/generation transaction.

## PROVEN_DEFECTS

### L37 — durable/LIVE divergence after FULL publication failure

PROVED_DEFECT. analyze_project commits the exact-revision snapshot before client.publish, catches publish exceptions/errors without restoring the old disk generation or daemon, and existing H3A U/V tests assert disk r+1 alongside daemon r. The failure can leave two active authorities describing different revisions until daemon restart or a later publication. Evidence: facade.py:1106-1179; tests cited above. CODE_PATH_PROVED + DIRECT_EVIDENCE.

### L38 — persistence-free publication capability, with scoped-path boundary

PROVED_DEFECT at the publish operation boundary. Server dispatch exposes publish; _execute_publish accepts a candidate at the expected next revision and assigns canonical Live memory with no persister/snapshot call. A source-based P0/r -> P1/r+1 client.publish -> server restart sequence therefore selects disk P0/r. Evidence: ipc.py:1203-1259, :1536-1537, :1879-1888, and startup loading at runtime.py:1403-1410. CODE_PATH_PROVED for the unguarded accepting path; INFERENCE for the restart outcome. The current in-repository analyze_single_file scoped caller itself does not establish successful L38 publication because its candidate keeps the old revision and is rejected by the monotonicity check. The normal server update_file/queued mutation path persists first and is closed against this particular ordering defect (runtime.py:1183-1199; ipc.py:1421-1442). Offline MCP fallback separately has a process-local update-before-save loss path, but does not prove server LIVE publication.

## UNRESOLVED_EVIDENCE

- No focused test kills the backend after an accepted raw publish but before durable save/restart. Source establishes that publish has no persistence call; a runtime reproduction was not run because this is discovery-only.
- No process-kill test targets the interval after FULL metadata pointer replacement but before daemon receives/commits publication, or between default-mode base-pickle replace and metadata replace.
- No focused test asserts that analyze_single_file sees the non_monotonic_canonical_revision response. Source indicates the rejection when hydrated state carries its normal canonical revision; the method ignores the response.
- IPC response-loss after dispatch is established as ordering only. Whether a particular pipe failure occurs after server state assignment is runtime-dependent and not demonstrated.
- Scope distinction for L38: source proves the generic publication capability is persistence-free, while the normal scoped file mutation operation is persistence-before-exposure. No external API contract was found that states whether callers of LiveStateClient.publish are required to durably save candidates first. This missing contract affects whether the generic endpoint is considered an intended supported workflow; it does not change the source fact that it can commit memory without persisting.
- Workspace reconciliation after restart depends on watcher creation and configured resync callback; no evidence establishes that every service restart automatically starts a Desktop watcher or runs FULL reanalysis.

L37_STATUS=PROVED_DEFECT
L38_STATUS=PROVED_DEFECT
PRODUCTION_EDITS=NONE
TESTS_RUN=NONE

## FILES_CHANGED

NONE (walkthrough.md is the requested report artifact and is excluded from source/test change accounting).

## ACTUAL_DIFF

NONE

