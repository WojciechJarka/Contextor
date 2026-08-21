# LIVE STARTUP RECONCILIATION - REAL IDEMPOTENCE FIX

## EXACT_FALSE_CANDIDATE_CAUSE

`tests/test_live_watcher_startup_reconciliation.py` was canonically present, but absent from persisted `FileStateManager`. Startup selection therefore correctly treated it as changed. Later, `IncrementalAnalysisEngine` parsed it and found an empty semantic refresh plan, returning `UNCHANGED`.

The no-op branch did not acknowledge the current fingerprint. Consequently, the file remained absent from persisted file state and was queued again on every restart.

## STARTUP_ORDERING

Observed ordering:

1. Watcher constructs startup queue from canonical membership and persisted fingerprints.
2. Desktop publishes hydrated canonical state.
3. First poll consumes the previously built queue.
4. Candidate may become stale before consumption.
5. IPC `update_file` increments revision even when the engine eventually returns `UNCHANGED`.

The real incident was primarily missing fingerprint acknowledgement; stale queue ordering was an additional uncovered race.

## FIX_OWNER

- `IncrementalAnalysisEngine.update_file`: semantic no-op parsing now acknowledges the current file fingerprint before returning `UNCHANGED`.
- `DesktopLiveWatcher.poll_once`: startup-only candidates are revalidated against fresh canonical membership and persisted fingerprints immediately before IPC dispatch.

Normal filesystem events are not filtered by this startup revalidation.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py`
- `C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py`

## REVALIDATION_OR_SELECTION_RULE

- Canonical module absent: ADD remains required regardless of fingerprint.
- Persisted fingerprint differs: MODIFY remains required.
- Tracked path absent on disk: DELETE remains required.
- Canonical module present and persisted fingerprint equals current file: stale startup candidate is discarded before `client.update_file`.
- Excluded paths remain outside scan and reconciliation.
- No time/debounce heuristic or duplicated fingerprint algorithm was introduced.

## REGRESSION_REPRODUCTION

Added ordering regression:

`persisted canonical state + missing fingerprint -> watcher startup queue -> fingerprint/state refresh -> first poll`

Expected and observed:

- candidate exists in initial queue;
- revalidation proves it current;
- `update_file` is never called;
- no revision-producing operation occurs.

Added engine regression proves a semantic `UNCHANGED` result records the previously missing fingerprint.

## TARGETED_TEST_RESULT

```text
7 passed in 6.37s
```

Scope:

- all startup reconciliation regressions;
- existing watcher create/modify/delete behavior;
- first-run no-snapshot behavior;
- watcher reconnect behavior.

No Full Analysis, full suite or S2D test rerun was performed.

## REAL_RESTART_PROOF

Pending one LIVE restart. Before restart, persisted fingerprints are present for:

- `tests/test_live_watcher_startup_reconciliation.py`
- `contextor/core/live_state/watcher.py`
- `contextor/core/analysis/incremental/engine.py`

This removes the previous missing-fingerprint precondition. Final proof requires comparing the journal revision immediately after restart and confirming that only expected desktop publication occurs, with no startup `UNCHANGED update_file`.

## ADD_MODIFY_DELETE_INVARIANTS

- ADD absent from canonical remains queued.
- Offline MODIFY remains fingerprint-driven.
- Offline DELETE remains tracked-domain-driven.
- Exclusions remain authoritative.
- All candidates still use the existing incremental COW/refresh/publication pipeline.

## S2D_STATUS

S2D architecture remains unchanged and canonical. No S2D tool implementation was modified.

## FINAL_VERDICT

`FIX_REQUIRED` until the requested real restart sanity confirms zero reconciliation revision churn.

RESTART LIVE
