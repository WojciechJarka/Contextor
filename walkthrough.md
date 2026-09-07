FAILURE_TIMELINE=
- 2026-09-07T14:50:51.989Z: LIVE op=u-6724-76 commits and persists lineage_facts.py, rev0=196 -> rev1=197; UPDATE_PUBLISHED rev=197. This is the last confirmed healthy canonical/LIVE convergence.
- 2026-09-07T14:50:54.212Z: op=u-6724-77 begins the __init__.py update against rev=197.
- 2026-09-07T14:51:25.017Z: WATCH_UPDATE_AMBIGUOUS for u-6724-77, followed by repeated connection-loss/recovery failures (WinError 10061). This is the first visible loss of a verifiable current generation.
- 2026-09-07T14:53:40.896Z: updater itself reports INCREMENTAL_END status=UPDATED and starts persistence at candidate rev=198.
- 2026-09-07T14:53:40.959Z: UPDATE_FAIL for u-6724-77: canonical_persistence_revision_conflict, server-reported rev=197, error "current=198, requested=198". Persistent generation has already advanced to 198 while the serving CanonicalLiveServer remains at 197.
- 2026-09-07T14:54:19.120Z: resync/full-analysis publication p-3364-4 is rejected: canonical_revision_discontinuity, server rev=197, candidate_rev=199.
- 2026-09-07T14:54:20.725Z: first emitted "startup resync baseline remains untrusted".
- 2026-09-07T14:55:03.774Z: later full-analysis publication p-3364-5 is again rejected: server rev=197, candidate_rev=200.
- 2026-09-07T14:57:57.554Z: old service exits at rev=197.
- 2026-09-07T14:58:14.109Z: restarted service starts at rev=200; GUI attaches shared state. Subsequent incremental commits rev=201 then rev=202 succeed.

LAST_TRUSTED_EVENT=
2026-09-07T14:50:51.989Z, LIVE CANONICAL_COMMIT op=u-6724-76, rev0=196, rev1=197, followed by PERSIST_END and UPDATE_PUBLISHED rev=197.

FIRST_UNTRUSTED_EVENT=
First direct latch write is not trace-instrumented. The earliest causally sufficient runtime record is 2026-09-07T14:53:40.959Z, LIVE UPDATE_FAIL op=u-6724-77, status=canonical_persistence_revision_conflict, server rev=197, persistent current/requested=198. The first explicit untrusted-status record is 2026-09-07T14:54:20.725Z, GUI STATUS_QUEUED, "startup resync baseline remains untrusted".

FULL_ANALYSIS_EVENT=
- p-3364-4 at 2026-09-07T14:54:19.119Z: publication attempt candidate_rev=199; rejected one millisecond later.
- p-3364-5 at 2026-09-07T14:55:03.774Z: publication attempt candidate_rev=200; rejected in the same trace record.
The runtime trace has no FULL_START/FULL_END event, so successful analysis computation is not independently logged; the attempted candidate states and the later hydrated rev=200 are the available chronology evidence.

FULL_ANALYSIS_CANONICAL_RESULT=
Running server canonical revision remains 197 throughout p-3364-4 and p-3364-5. Persisted candidate generations advance at least 197 -> 198 -> 199 -> 200; restart SERVICE_START=200 confirms rev=200 was durable. No CANONICAL_PUBLISH exists for either p-3364-4 or p-3364-5.

FULL_ANALYSIS_TRUST_RESULT=
NO recovery in the old process. DesktopLiveWatcher calls the full-analysis callback, then checks a fresh LiveStateClient.snapshot against FileStateManager. Snapshot remains state revision 197 while the persisted file-state generation is ahead; _trusted_file_state returns None, so the watcher emits the untrusted baseline status. A later full analysis cannot repair this while CanonicalLiveServer rejects every candidate greater than expected 198.

PRE_RESTART_PERSISTED_STATE=
Durably usable generation rev=200. Evidence: p-3364-5 submitted candidate_rev=200; after no intervening successful server publication, the new process starts with SERVICE_START rev=200. The old server's in-memory revision remains 197. The log does not expose the pre-restart state_id, so its exact value is not asserted.

POST_RESTART_HYDRATED_STATE=
2026-09-07T14:58:14.109Z SERVICE_START rev=200, then GUI "shared state attached; watcher active" at 14:58:14.693Z. The next two changes persist/commit 200->201 and 201->202 normally. Current Contextor canonical projection reports revision=202, provenance=live, resync_required=false.

RUNTIME_ONLY_STATE_DIFFERENCE=
Old process: CanonicalLiveServer._revision=197 and its in-memory snapshot remained revision 197 while persisted metadata/file-state had progressed to 198/199/200. New process: run_service loads the persisted snapshot, derives server revision from persisted metadata, and begins at 200. The decisive discrepancy is process-local server state versus durable generation, not an untrusted durable generation.

TRUST_STATE_OWNER=
- Durable baseline: contextor.core.analysis.state_manager::FileStateManager; its _load initializes baseline_status=untrusted and marks trusted only after valid revision/state_id metadata and engine/file-state generation agreement.
- Runtime gate: contextor.core.live_state.watcher::DesktopLiveWatcher._trusted_file_state; it requires FileStateManager.baseline_status=trusted and manager revision/state_id equal to LiveStateClient.snapshot state revision/state_id.

TRUST_STATE_WRITERS=
- contextor.core.live_state.runtime::_repository_persister writes the coupled snapshot plus FileStateManager.build_payload at exact_revision through save_snapshot.
- contextor.core.analysis.state_manager::FileStateManager._load derives baseline_status from persisted metadata and file-state, rather than persisting a separate boolean.
- Full canonical materialization owner is contextor.core.api.facade::ContextorFacade.analyze_project; Contextor fact lineage confirms persistence through state_manager.save_engine_state/live_snapshot and hydration through live_state.hydration::hydrate_repository_engine.

TRUST_STATE_CLEARERS=
There is no separate durable "clear" operation. A fresh FileStateManager instance re-evaluates trust from matching persisted metadata/file-state and LIVE snapshot. DesktopLiveWatcher clears _startup_requires_resync only after its post-resync snapshot passes _trusted_file_state.

RESYNC_STATE_OWNER=
contextor.core.live_state.watcher::DesktopLiveWatcher: _startup_requires_resync, _startup_resync_attempted, _startup_pending, and _snapshot are process-local instance fields.

STARTUP_BASELINE_OWNER=
contextor.core.live_state.watcher::DesktopLiveWatcher.poll_once plus _trusted_file_state. GUI wiring in contextor.ui.gui constructs on_resync as run_full_analysis_exclusive(path, owner="desktop_analysis", timeout=30.0).

STUCK_LATCH_POSSIBLE=YES
Evidence: _startup_requires_resync is set when _trusted_file_state returns None; poll_once sets _startup_resync_attempted=True before running on_resync. On failed/unverifiable post-resync baseline it returns without clearing either field. There is no retry/clear path in that branch. In this incident the underlying server revision was also stuck at 197, so the latch is persistent process-local amplification of the revision split, not the original divergence.

TEST_CONTAMINATION_POSSIBLE=NO
Evidence: the focused test file is only a pure domain-contract test and has no LIVE/runtime/cache/service imports; it was successfully watcher-persisted at rev=193 and rev=196 before the failure. The failure begins on u-6724-77 for contextor/core/domain/__init__.py with an IPC persistence revision conflict. The trace contains no test-run lifecycle, child-service, lock, cache, or environment event attributable to tests/domain/test_lineage_facts.py. Test-file edits do produce ordinary watcher revisions, but no shared singleton/process side effect is evidenced.

NEW_FILE_RECOVERY_DEFECT_POSSIBLE=NO FOR THIS INCIDENT
Evidence: lineage_facts.py new-file lifecycle completed normally at rev=190 and then again at rev=192, 194, and 197. The failing operation is the existing __init__.py update; no syntax error, RECOVERED event, deletion, or new-file-specific failure occurs between the last trusted commit and the divergence. The generic watcher path can latch on any failed trusted-file-state verification, but the supplied chronology does not implicate new-file recovery.

PERSISTED_STATE_CORRUPTION_POSSIBLE=NO
Evidence: a corrupt or mismatched durable generation would remain untrusted after restart. Instead, the restart reads rev=200 directly and accepts it, then commits rev=201 and 202. FileStateManager trust conditions therefore passed for the persisted rev=200 state. The old process alone held stale rev=197.

MOST_LIKELY_ROOT_CAUSE=
Revision-split recovery defect: the old CanonicalLiveServer retains _revision=197 after another writer/persistence path advances the durable generation to 198. The u-6724-77 persister then reports the conflict, and full analysis independently creates durable candidates 199/200 but IPC publish correctly rejects them because the in-memory server expects 198. DesktopLiveWatcher uses the stale server snapshot for its trust check, sets its one-shot startup resync latch, and cannot converge. Restart reconstructs CanonicalLiveServer._revision from durable metadata (200), eliminating the split.

ALTERNATIVE_CAUSES=
- A concurrent full-analysis/persistence writer advanced the snapshot between u-6724-77 clone/update and its exact-revision persist. This is supported as the trigger shape but the trace lacks an explicit full-job start/end correlation.
- A service connection/recovery failure exposed an already-existing server/persistence revision split. It is temporally associated with the conflict but does not explain the durable/server mismatch by itself.
- Test contamination, new-file syntax/recovery, and persisted snapshot corruption are not supported by the event sequence.

MINIMAL_REPRO=
A. Runtime stuck latch:
1. Start trusted LIVE at revision R and verify FileStateManager revision/state_id matches the server snapshot.
2. In an isolated test harness, advance the coupled persisted snapshot/file-state to R+1 without advancing the already-running CanonicalLiveServer._revision.
3. Attempt an incremental update/publish whose candidate is R+2; assert canonical_revision_discontinuity or persistence conflict, server still R, durable metadata R+1/+2.
4. Run watcher poll/resync; assert _trusted_file_state fails against server R, _startup_requires_resync=true, _startup_resync_attempted=true; a successful compute whose publication remains rejected does not clear it.
5. Start a new service from the same cache; assert SERVICE_START-style revision R+2 and trusted baseline.
B. Test contamination control:
Run tests/domain/test_lineage_facts.py with an isolated CONTEXTOR_CACHE_DIR and no Desktop service; compare service PID/endpoint, repo cache metadata revision, and file-state generation before/after. No change distinguishes it from A.
C. New-file recovery:
From a trusted baseline create a valid new .py file, then introduce and repair syntax in that same file. Assert each recovery leaves server revision, metadata revision, FileStateManager state_id/revision, and watcher trust equal; restart must not be necessary.
D. Persistence/hydration:
Create a deliberately mismatched offline metadata/file-state generation. Assert FileStateManager reports untrusted and service does not attach it. Then restore a matched generation and assert hydration succeeds. This differentiates durable corruption from the observed stale-process split.

FIX_SCOPE_IF_CONFIRMED=
Narrow LIVE revision-coordination/recovery scope only:
- contextor.core.live_state.ipc::CanonicalLiveServer publish/update transaction and the persistence handoff must not leave durable exact_revision ahead of server _revision after a rejected request.
- contextor.core.live_state.runtime::_repository_persister/full-analysis publication path must reconcile or invalidate/restart the serving instance when an exact-revision conflict/discontinuity is observed.
- contextor.core.live_state.watcher::DesktopLiveWatcher must make failed post-resync verification retryable after a fresh reconnect/revision change; do not retain _startup_resync_attempted as a permanent recovery blocker.
No lineage Stage 1A file belongs in the fix.

TESTS_REQUIRED_FOR_FIX=
- Focused deterministic test for server revision R versus durable generation R+1, including rejected publish and no silent divergent persistence.
- Focused DesktopLiveWatcher test proving a failed post-resync trust check retries after server revision changes/reconnects and clears both startup fields only after matching file-state/state_id/revision.
- Full-analysis plus active-server integration test: successful full analysis either advances the active server atomically or returns a surfaced failure and leaves no durable/server split.
- Restart hydration parity test: matched persisted revision hydrates; mismatched metadata/file-state is rejected fail-closed.
- New-file syntax-error -> RECOVERED lifecycle regression to prove it does not leave the startup latch set.
- Focused pure-domain test isolation control with an isolated cache/service endpoint.

LINEAGE_STAGE_1A_CHANGED=NO
FILES_CHANGED=NONE
TESTS_RUN=NONE (existing runtime logs and bounded architectural discovery were sufficient; no service restart, full scan, or test execution was performed.)

