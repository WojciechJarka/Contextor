# L32H2F3C_EXACT_ADMISSION_BOUNDARY_HANDOFF

## FILES_CHANGED

FILES_CHANGED: C:\Temp\Contextor_Repo\walkthrough.md (requested report only). No production, test, or documentation source file was edited. The report is excluded from source/test diff accounting.

## ACTUAL_DIFF

DIFFS=NONE

Read-only Git inspection returned empty git status --short, git diff --name-only, and git diff --cached --name-only. HEAD/SHA are omitted per task instruction.

## COMPLETE_MIGRATION_CALLER_MATRIX

Evidence labels: DIRECT_EVIDENCE = current Contextor source/range, workspace_sync=verified, revision 266. CODE_PATH_PROVED = source control flow permits the branch, but no runtime migration was triggered or snapshot inspected. UNKNOWN = not established by these sources.

Migration owner: C:\Temp\Contextor_Repo\contextor\core\live_state\store.py, migrate_legacy_snapshot(repo_root: str | Path) -> Path, lines 2419-2450. Full implementation:

~~~python
def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
    """Copy a verified path-keyed snapshot into its repo-ID cache directory."""

    from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    root = Path(repo_root).expanduser().resolve()
    identity = require_repository_identity(root)
    target = repo_cache_dir(root)
    if read_metadata(target) is not None:
        return target

    legacy = legacy_repo_cache_dir(root)
    if legacy == target:
        return target
    loaded = load_snapshot(legacy)
    if loaded is None:
        return target

    state, metadata = loaded
    save_snapshot(
        state,
        target,
        metadata.state_id,
        writer=f"migration:{metadata.writer}",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        revision_floor=metadata.revision,
        migration_file_state_source=legacy / "file_state.json",
        migration_only_if_absent=True,
    )
    return target
~~~

The store writer is reached only if target metadata is absent, legacy and target differ, and the legacy snapshot loads. The early target-metadata return performs no migration write.

| Caller | Held locks at call | Write reachability | Error/nesting |
|---|---|---|---|
| C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py::resolve_authoritative_repository_state, line 44 | No full-analysis lease, MCP cache RLock, or RuntimeLeaseManager domain lock in resolver itself. | CODE_PATH_PROVED under the store conditions above. | Errors propagate. Called from facade project, layer, and single-file paths below. |
| C:\Temp\Contextor_Repo\contextor\mcp\runtime.py::get_or_init_engine, line 388 | Its own per-repository MCP cache RLock is held. No full-analysis or LIVE domain lock. Three outer callers also already hold the same reentrant cache lock. | CODE_PATH_PROVED when no engine remains and repository identity exists, subject to store conditions. | Migration errors escape getter. threading.RLock permits same-thread nested entry. |
| C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py::run_service, line 1431 | Persistent LIVE lease object exists. RuntimeLeaseManager.acquire has returned and all its with-self._lock domain-lock scopes have exited. No full-analysis or MCP cache lock. | CODE_PATH_PROVED under store conditions. | Startup exception is emitted/re-raised; finally closes/drains service then tries release and fences if release fails. Acquire failure prevents reaching migration. |
| C:\Temp\Contextor_Repo\contextor\ui\gui.py::_start_live_watcher_blocking, line 1709 | connect_or_start returned; its short-lived domain lock is gone. No full-analysis or MCP cache lock. Persistent authority ownership is not an OS lock hold. | CODE_PATH_PROVED on the new-watcher path under store conditions. | SecondDesktopActive returns. OSError, EOFError, RuntimeError, TimeoutError, RepositoryIdentityError schedule bounded retries; other exceptions are not covered by that retry tuple. startup_publish lease is attempted later only in the revision-mismatch branch. |

Focused source search found those three direct production call expressions plus the resolver call. Contextor blast radius also lists contextor.core.live_state.__init__ as a direct static consumer/re-export; focused source search did not find another invocation there.

Indirect facade paths:
- ContextorFacade.analyze_project calls resolve_authoritative_repository_state at facade.py:652. Its only in-repository production direct caller is run_full_analysis_exclusive, so the resolver/migration executes under that full lease.
- _analyze_layer_uncoordinated calls resolver at facade.py:1366. Confirmed production callers invoke public analyze_layer, whose scoped lease covers the internal call.
- _analyze_single_file_uncoordinated calls resolver at facade.py:1608 and may call hydrate_repository_engine at 1660. Its public analyze_single_file wrapper owns scoped_analysis through the internal call. hydrate_repository_engine calls resolver again.
- No lease/token is passed into resolver, hydrator, or migrator. Ownership is lexical around facade calls.

Confirmed production facade callers:
- contextor/cli.py: project 95, layer 104, single-file 113.
- contextor/mcp_worker.py: project 32, layer 42, single-file 46.
- contextor/mcp/analysis_jobs.py: project 244, layer 278, single-file 283.
- contextor/ui/gui.py: project 1309, layer 2025, single-file 2088.
- contextor/core/analysis/profile_runner.py: project 25.
Focused search found no other production direct call to ContextorFacade.analyze_project.

## ALREADY_HELD_LEASE_BOUNDARIES

run_full_analysis_exclusive, full_analysis_coordinator.py:41-128, acquires writer_kind="full_analysis" before calling analysis_fn or ContextorFacade.analyze_project and releases in finally. Its project resolver therefore runs under the full lease.

Current public scoped wrappers, complete AST implementations, workspace_sync=verified:

~~~python
@staticmethod
def analyze_layer(
    root_dir: str,
    layer_dir: str,
    log=None,
    progress_callback=None,
    additional_excludes: list[str] | None = None,
) -> str:
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )

    root_resolved, _ = _resolve_repository_target(
        root_dir, layer_dir, target_kind="layer"
    )
    lease = acquire_full_analysis(
        root_resolved,
        owner="scoped_layer_analysis",
        writer_kind="scoped_analysis",
        timeout=10.0,
    )
    try:
        return ContextorFacade._analyze_layer_uncoordinated(
            root_dir, layer_dir, log=log,
            progress_callback=progress_callback,
            additional_excludes=additional_excludes,
        )
    finally:
        release_full_analysis(lease)
~~~

~~~python
@staticmethod
def analyze_single_file(
    file_path: str,
    repo_root: str,
    log=None,
    progress_callback=None,
    additional_excludes: list[str] | None = None,
    publication_result: dict[str, Any] | None = None,
) -> str:
    if publication_result is not None:
        publication_result.update(status="not_attempted", revision=None, warning=None)
    from contextor.core.analysis.full_analysis_lease import (
        acquire_full_analysis,
        release_full_analysis,
    )
    root_resolved, target = _resolve_repository_target(
        repo_root, file_path, target_kind="file"
    )
    if target.suffix.lower() != ".py":
        raise ValueError(f"Selected file is not a Python file: {target}")
    lease = acquire_full_analysis(
        root_resolved,
        owner="scoped_single_file_analysis",
        writer_kind="scoped_analysis",
        timeout=10.0,
    )
    try:
        return ContextorFacade._analyze_single_file_uncoordinated(
            file_path, repo_root, log=log,
            progress_callback=progress_callback,
            additional_excludes=additional_excludes,
            publication_result=publication_result,
        )
    finally:
        release_full_analysis(lease)
~~~

Path/scope validation in each wrapper precedes lease acquisition; migration-bearing internals follow lease acquisition.

## MCP_NESTED_CACHE_CALLERS

Current cache transaction, mcp/runtime.py:286-295:

~~~python
@contextmanager
def _engine_cache_transaction(root: Path | str) -> Iterator[str]:
    root_key = _engine_cache_key(root)
    with _engine_cache_locks_guard:
        lock = _engine_cache_locks.get(root_key)
        if lock is None:
            lock = threading.RLock()
            _engine_cache_locks[root_key] = lock
    with lock:
        yield root_key
~~~

get_or_init_engine, mcp/runtime.py:311-419, holds this transaction across LIVE cache refresh, optional legacy migration, snapshot hydration, and engine/revision/provenance cache publication. It enters migration fallback only if no engine exists after attempting the LIVE client snapshot. Complete AST implementation was fetched and verified, no partial source. Its migration call is line 388.

Three production callers enter an outer cache transaction and then invoke the getter:
1. mcp/runtime.py::_get_or_init_engine_snapshot, lines 303-308. Complete body:
   ~~~python
   def _get_or_init_engine_snapshot(root: Path | str):
       root = Path(root).expanduser().resolve()
       with _engine_cache_transaction(root) as root_key:
           engine = get_or_init_engine(root)
           revision = _live_engine_revisions.get(root_key)
           return engine, revision
   ~~~
   It returns an engine/revision pair to the get_file_edit_context read path.
2. mcp/analysis_jobs.py::_execute_analysis_job, complete function lines 303-424; outer transaction lines 355-359. After the project worker returns success/publication revision, it clears cached engine/revision, reloads via getter and checks loaded canonical revision. The worker's run_full_analysis_exclusive has ended before this reload.
3. mcp/tools/update_file.py::update_file, complete function lines 491-602; initial getter line 504 and post-remote-success outer lock/getter lines 521-523. It sets cached revision to remote revision minus one, then reloads. The initial getter precedes the update branch.

The cache RLock is process-local and distinct from full_analysis.lock and RuntimeLeaseManager's domain lock. It permits the same-thread nested getter. Source proves the current lock encloses migration fallback and cache hydration/publication. It does not prove migration can be moved outside without changing cache-refresh atomicity. Successful LIVE snapshot refresh is a separate branch that ordinarily bypasses migration and does not publish LIVE state itself.

## MINIMUM_PRE_CACHE_ADMISSION_BOUNDARY

Literal boundaries established by source:
- getter's own cache entry: mcp/runtime.py:317;
- outer cache entries preceding nested getter: mcp/runtime.py:305, analysis_jobs.py:355, update_file.py:521.

A gate inside the getter after an outer caller took the cache lock is too late to establish full-analysis-before-cache order for those three call paths. Current source has no pre-cache migration-needed predicate, lease token, or explicit ownership parameter. The target-metadata test is inside migrate_legacy_snapshot, after entering the cache transaction. When metadata exists, migration returns immediately without loading legacy data or writing. Whether a check moved outside the lock remains race-safe is UNKNOWN from current code.

No source evidence proves moving migration out of the cache transaction preserves atomicity: current RLock encloses migration, load, engine construction, and cache-map updates. migrate_legacy_snapshot itself performs no LIVE client.publish; the LIVE client.snapshot branch supplies live state before the fallback when available.

## REENTRANCY_HAZARDS

- Cache same-thread reentry is supported by threading.RLock and is used by the three outer callers.
- acquire_full_analysis holds a process/thread lock plus repository OS lock; non-reentrant behavior is covered by tests/test_full_analysis_coordination.py::test_in_process_non_reentrant_lock_exclusion. An inner full-lease attempt from a coordinated facade chain would be nested, but current migration APIs receive no lease ownership marker.
- At current MCP outer callers, order is cache RLock -> nested getter cache RLock -> possible migration/store lock. Acquiring full_analysis from inside that getter would occur after outer cache acquisition.
- Existing facade paths are full/scoped lease -> resolver -> optional migration; no lease is passed down.
- analysis_jobs reacquires the cache only after its full-analysis worker returns.
- Runtime and GUI obtain/release short domain-lock scopes before migration. No current inspected getter path acquires full_analysis.
- Dynamic external callbacks outside the inspected in-repository calls: UNKNOWN.

## MIGRATION_SIGNATURE_COMPATIBILITY

Current signatures:
- migrate_legacy_snapshot(repo_root: str | Path) -> Path.
- resolve_authoritative_repository_state(repo_path: str | Path) -> AuthoritativeRepositoryState | None.
- hydrate_repository_engine(repo_path: str | Path) -> HydratedRepositoryEngine | None.
- get_or_init_engine(root: Path).

Existing one-positional test fixtures:
- tests/test_mcp_incremental_hydration.py::test_legacy_migration_writer_admission_precedes_mcp_cache_lock uses pause_migration(_root).
- tests/test_layer_state_only_hydration.py patches migration, resolver, and hydrator with one-argument lambdas.
- tests/test_live_single_file_reuse.py wraps resolver/hydrator with one-argument functions.
- tests/test_mcp_regressions.py has one-argument getter stubs and a one-argument package-exported migration lambda.
- tests/test_full_analysis_coordination.py::test_mcp_single_publication_root_cause_regression uses a one-argument getter stub.
No signature change is proposed.

## LIVE_STARTUP_LOCK_CONTEXT

run_service current ranges: runtime.py:1329-1822. At 1412-1431 it creates RuntimeLeaseManager, calls manager.acquire(), optionally claims Desktop ownership, then migrates. Current complete RuntimeLeaseManager.acquire, runtime_lease.py:1363-1441, scopes record operations inside with self._lock(); returning from acquire exits that domain-lock scope. Persistent lease ownership remains; the domain OS lock is not held at migration. run_service has no full-analysis lease acquisition.

If acquire fails, migration is not reached. Later bootstrap failure emits RUNTIME_AUTHORITY_BOOTSTRAP_FAIL and re-raises. Finally closes/drains server state; when lease exists and worker drain succeeds it attempts manager.release, then manager.fence_owner on release failure. Migration/backfill source range is 1412-1510; outer error/cleanup is 1724-1817. Backfill is conditional on module_usages_require_materialization and saves at line 1495; no full-analysis lock surrounds it. The prior snapshot-writer handoff supplies save_snapshot's migration-only contract; it is not repeated here.

## GUI_STARTUP_LOCK_CONTEXT

Complete _start_live_watcher_blocking source: gui.py:1641-1962. New watcher path returns from connect_or_start at 1703, then calls migration at 1709. Retry handling starts at 1718. Only later, when disk and LIVE revisions differ, GUI attempts startup_publish full lease at 1781-1787, publishes at 1795, and releases at 1800. Equal revisions skip that branch. Thus the later publish lease does not cover migration; another full/scoped writer can own full_analysis.lock while migration reaches its conditional store-write path.

## RACE_A_C_TEST_INSTRUMENTATION

USER-PROVIDED baseline: F3B targeted pass; Race B green; Race A and C red; canonical revision 265; cycles.count=0. No tests were run.

Race A owner: tests/test_live_state_store.py::test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held, complete source lines 2597-2678. It starts Process A holding full_analysis lease and Process B migrating; it observes the real save_snapshot entry before releasing A. Required GREEN: no entry into real snapshot write while A owns the lease; after release migration reaches the writer and both processes complete with released/completed statuses. Current migration source has no such admission.

Race C owner: tests/test_mcp_incremental_hydration.py::test_legacy_migration_writer_admission_precedes_mcp_cache_lock, complete source lines 1378-1523. It monkeypatches the cache transaction, coordinator and full_analysis_lease acquire/release functions, and package-exported migration. One-argument pause_migration(_root) records same-thread lease ownership and blocks. A second thread probes the same cache lock. Required GREEN: lease event < cache acquisition < migration callback; callback sees lease held; second thread remains blocked until callback resumes; threads terminate and the intentional RuntimeError is observed. Current source reaches cache before migration and has no lease acquisition, contradicting these assertions. These are code-derived expectations, not executed results.

## EXACT_SOURCE_RANGES_FOR_LITERAL_PATCH

All listed Contextor source fetches/ranges at revision 266 report workspace_sync=verified. Complete AST fetches report implementation_is_complete=true and no_partial_symbol_source=true. Long functions were fetched in exact contiguous ranges; every chunk returned status=ok with its requested inclusive bounds.

Production boundaries:
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py: _engine_cache_transaction 286-295; _get_or_init_engine_snapshot 303-308; get_or_init_engine 311-419.
- C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py: _execute_analysis_job 303-424.
- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py: update_file 491-602.
- C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py: resolve_authoritative_repository_state 29-82; hydrate_repository_engine 85-112.
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py: analyze_project 558-1301 (complete contiguous range fetch); public analyze_layer 1301-1335; _analyze_layer_uncoordinated 1337-1525; public analyze_single_file 1527-1573; _analyze_single_file_uncoordinated 1575-1860.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py: run_full_analysis_exclusive 41-128.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py: acquire_full_analysis 410-588; release_full_analysis 591-610.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py: RuntimeLeaseManager.acquire 1363-1441.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py: run_service 1329-1822, complete contiguous range fetch.
- C:\Temp\Contextor_Repo\contextor\ui\gui.py: _start_live_watcher_blocking 1641-1962, complete contiguous range fetch.
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py: migrate_legacy_snapshot 2419-2450; save_snapshot migration-only lock details are in the preceding store handoff.

Test owners/compatibility evidence:
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py: Race A 2597-2678.
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py: Race C 1378-1523.
- C:\Temp\Contextor_Repo\tests\test_layer_state_only_hydration.py.
- C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py.
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py.
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py.

## SOURCE_SYNC

Contextor MCP was used first; deferred tools were actively enumerated. Current contexts for MCP runtime, hydration, facade, full-analysis coordinator/lease, LIVE runtime/lease, GUI, store, analysis_jobs, update_file, and the Race A/C test modules report canonical_state=fresh, workspace_sync=verified, revision 266.

get_symbol_call_context for get_or_init_engine found its in-module caller _get_or_init_engine_snapshot at line 306 and explicitly reports intra_module scope. Cross-module ownership was checked separately through migration blast radius and focused source searches. Migration lineage resolved exact artifact A3370/1 with complete, metadata-consistent semantic lineage at revision 266; its workspace_sync=unverified is documented behavior of the narrow lineage query, which does not hash source. Implementation fetch and blast-radius response report verified sync.

get_live_events(after_revision=265): revision/latest_revision 266; activity epoch 9e9a2a2edcb046bba00df0850244ad36; continuity=continuous; resync_required=false. One desktop_watcher UPDATED event at revision 266 names tests/test_live_state_store.py. Current canonical diagnostics show cycles count 0 and fresh. No tests, full analysis, update_file, restart, or repository mutation was performed.

## LIVE_REVISION

266 current Contextor revision; 265 is the user-provided baseline.

## BLOCKERS_AND_UNCERTAINTIES

- No missing lock-ownership source evidence blocks this bounded handoff.
- The conditional migration branch is source-proved; actual absence of target metadata and presence of a valid legacy snapshot were not inspected.
- No runtime occurrence of migration is claimed.
- Moving migration outside the current cache transaction is not proven to preserve refresh atomicity.
- Dynamic external callers/callbacks beyond inspected in-repository call sites remain UNKNOWN.
- Current resolver/hydrator/migrator signatures do not carry explicit lease ownership; this is a source fact, not a design proposal.

## FINAL_VERDICT

READY_FOR_F3C_LITERAL_PATCH

Source handoff only. No patch or runtime execution claim.

