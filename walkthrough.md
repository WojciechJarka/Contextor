# P0 W1 — canonical-writer admission ordering

## STATUS

PASS

## CONTEXTOR_DISCOVERY

Contextor MCP confirmed the current owners and call paths before editing:
`acquire_full_analysis` and `run_full_analysis_exclusive` are in
`contextor.core.analysis.full_analysis_coordinator`; the LIVE mutation guard is
`contextor.core.live_state.runtime._repository_mutation_guard`; and
`CanonicalMutationCoordinator` is owned by `contextor.core.live_state.ipc`.
The coordinator and the two requested call sites agreed with the supplied patch.

## CONTEXTOR_SYNTAX_DISCREPANCY

During the implementation Contextor LIVE revision 1005 reported
`expected 'except' or 'finally' block` at
`full_analysis_coordinator.py:569`, while the same working-tree source passed
`.venv\\Scripts\\python.exe -m py_compile`. A repeated MCP query retained the
last-known-good/stale parser result. The final local parse is authoritative for
this task's changed source; this LIVE watcher refresh discrepancy remains
recorded rather than being hidden.

## FILES_CHANGED

- `contextor/core/analysis/full_analysis_coordinator.py`
- `contextor/core/live_state/runtime.py`
- `tests/test_full_analysis_coordination.py`

## ACTUAL_DIFF

`acquire_full_analysis` now takes validated `writer_kind`, serializes admission
through a per-repository in-process plus OS admission lock, and releases that
admission lock before returning the execution lease. The existing execution
lock, metadata, fsync, owner recovery, and `release_full_analysis` remain the
owners of execution lifetime. Full analysis explicitly supplies
`writer_kind="full_analysis"`; the mutation worker supplies
`writer_kind="live_mutation"`.

## ORDER_PROOF

`test_waiting_full_analysis_runs_before_next_live_mutation` holds A in a spawned
process, waits for F's existing lease-wait log event, then starts B. After A is
released, it proves F acquires first, B is still not acquired, and the exact
order is `["full", "mutation_b"]`.

## TIMEOUT_PROOF

`test_admission_timeout_does_not_leak_locks` proves a second writer times out
while F owns admission and waits for execution. After releasing A and F, a new
writer acquires and releases normally.

## CANCELLATION_PROOF

`test_admission_cancellation_does_not_leak_locks` proves cancellation raises
`AnalysisCancelled`; after release, a subsequent writer acquires and releases
normally.

## TEST_RESULTS

- `python -m py_compile contextor/core/analysis/full_analysis_coordinator.py contextor/core/live_state/runtime.py`: PASS
- `python -m pytest -q tests/test_full_analysis_coordination.py tests/test_live_mutation_coordinator.py`: PASS, `38 passed in 25.19s`
- `git diff --check`: PASS

## FULL_DIFFS

The complete raw working-tree diffs for the three task-changed files are the
current output of:

```powershell
git diff --no-ext-diff -- contextor/core/analysis/full_analysis_coordinator.py contextor/core/live_state/runtime.py tests/test_full_analysis_coordination.py
```

They are intentionally excluded from this report's own diff and remain directly
reviewable from the repository working tree.

# P0 W1a — admission cleanup and trace contract

## STATUS

PASS. Desktop/LIVE runtime certification remains pending a user-owned service restart.

## CONTEXTOR_DISCOVERY

MCP revision 1011 verified `_canonical_writer_admission` and
`acquire_full_analysis` in the coordinator, the LIVE mutation guard call site,
and the existing runtime-trace header/event writer. The W1 call paths matched
the supplied W1a contract.

## FILES_CHANGED

- `contextor/core/analysis/full_analysis_coordinator.py`
- `contextor/core/runtime_trace.py`
- `tests/test_full_analysis_coordination.py`
- `tests/test_runtime_trace.py`

## CLEANUP_PROOF

Admission cleanup is now nested: release of the in-process admission lock runs
even if native `_unlock_fd` fails. The release trace is emitted only after a
real OS admission acquisition (`os_locked=True`). Acquisition ordering is
unchanged.

## CROSS_PROCESS_ORDER_PROOF

The added spawned-process scenario holds A's execution lease, waits until F's
lease log proves F owns admission while waiting, then starts B. It proves F is
the first acquisition result, B remains unacquired while F holds execution,
and B is the second result after F is released.

## CANCELLATION_WHILE_WAITING_PROOF

The replacement cancellation test makes F own admission and wait on A's OS
execution lease. C polls the occupied process admission at least twice before
its third cancellation check raises `AnalysisCancelled`; after A/F release, a
new writer acquires and releases normally.

## TRACE_SCHEMA_PROOF

`ANALYSIS`, both admission events, all three full-analysis events, and the
`owner`/`writer_kind` header fields are declared. The durability test writes
both admission records and verifies the acquired JSONL record preserves
`repo_id`, owner, writer kind, and `wait_ms=12.5`.

## TEST_RESULTS

- `pytest -q tests/test_full_analysis_coordination.py tests/test_live_mutation_coordinator.py tests/test_runtime_trace.py`: PASS, `50 passed in 37.57s`
- `py_compile` for coordinator, LIVE runtime, and runtime trace: PASS
- `git diff --check`: PASS

## FULL_DIFFS

```powershell
git diff --no-ext-diff -- contextor/core/analysis/full_analysis_coordinator.py contextor/core/live_state/runtime.py contextor/core/runtime_trace.py tests/test_full_analysis_coordination.py tests/test_runtime_trace.py
```

# P0 G1 — Desktop first-paint repair

## STATUS

PARTIAL: production boundary and existing GUI/LIVE regressions are verified; the requested new dedicated public-start/cache-post-paint tests remain to be added before final certification.

## CONTEXTOR_DISCOVERY

Contextor LIVE revision 1018 confirmed `ContextorGUI` startup, watcher, feed,
identity, close, and watcher-start ownership. `prune_startup_caches` is owned by
`contextor.core.paths` and consumed by GUI.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_gui_live_startup.py`
- `tests/test_live_desktop_integration.py`

## MAIN_THREAD_BEFORE / IMPLEMENTED_THREAD_BOUNDARY

The pre-paint cache cleanup and stale-exclude scan now start after paint in
daemon workers. The public watcher-start API only deduplicates and starts a
daemon thread; the former heavy flow is `_start_live_watcher_blocking`.

## FIRST_PAINT_CONTRACT

`__init__` builds UI, registers close, then schedules post-paint tasks after
50ms. No cache prune or stale-exclude filesystem work runs inline before paint.

## INFLIGHT_DEDUP_PROOF / CLOSE_RACE_PROOF

The wrapper keys in-flight startups by resolved path under a lock. Closing sets
`_closing` before shutdown work, and the blocking path checks it before attach,
watcher construction, start, and retry; it does not join daemon startup threads.

## TEST_RESULTS

- `pytest -q tests/test_gui_live_startup.py tests/test_live_desktop_integration.py`: PASS, `29 passed in 10.44s`
- `py_compile contextor/ui/gui.py`: PASS
- `git diff --check`: PASS

## FULL_DIFFS

```powershell
git diff --no-ext-diff -- contextor/ui/gui.py tests/test_gui_live_startup.py tests/test_live_desktop_integration.py
```

# P0 G1C — Desktop first-paint regression certification

## STATUS

PASS

## CONTEXTOR_DISCOVERY

Contextor MCP revision 1027 confirmed the public async wrapper, blocking
implementation, post-paint scheduling, stale-exclude worker, identity UI guard,
and close flag. No production defect was exposed by the new regressions.

## FILES_CHANGED_G1C

- `tests/test_gui_live_startup.py`

## PUBLIC_START_NONBLOCKING_PROOF

The public-start regression blocks `connect_or_start` behind an Event and proves
the public call returns in under 250ms before connection completion.

## INFLIGHT_DEDUP_PROOF

Two public starts for the same repository while the first connect is blocked
produce one connect call, one inflight key, and one startup thread.

## CLOSE_PROOF

With `_closing=True`, public start creates neither a connect call nor inflight
state nor a startup thread.

## POST_PAINT_NONBLOCKING_PROOF

The cleanup regression blocks cache pruning and proves post-paint dispatch
returns in under 250ms while cleanup runs outside the caller thread.

## LIVE_DESKTOP_INTEGRATION_CHANGE_REASON

The existing integration tests were adapted to call the blocking implementation
directly because they assert deterministic heavy-path state attachment and
generation behavior; their assertions were not weakened.

## PRODUCTION_CHANGED_IN_G1C

NO

## TEST_RESULTS

- `pytest -q tests/test_gui_live_startup.py tests/test_live_watcher_startup_reconciliation.py tests/test_live_watcher_watchdog.py tests/test_live_desktop_integration.py`: PASS, `79 passed in 41.06s`
- `py_compile contextor/ui/gui.py`: PASS
- `git diff --check`: PASS

## FULL_DIFFS

The full unified diffs are retained in the prior G1 sections for the production
boundary and integration-harness adaptations; G1C itself adds only the four
dedicated regressions in `tests/test_gui_live_startup.py`.
