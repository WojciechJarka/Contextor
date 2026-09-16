# CPA10K5B1_MCP_CHILD_REGISTRY_AND_PROCESSPOOL_ORPHAN_CLEANUP

MODE=IMPLEMENT_EXACT_AUDITOR_DESIGN
REPO=C:\Temp\Contextor_Repo
SCOPE=MCP_SERVER_OWNED_PROCESSPOOL_AND_REGISTERED_CHILD_INFRASTRUCTURE_ONLY
IMPLEMENTATION_RESULT=PASS
FULL_ANALYSIS=NOT_RUN
LIVE_MCP_RESTART=NOT_PERFORMED
DESKTOP_K5A_PATH=NOT_TOUCHED

## EXACT_ANCHORS_VERIFIED

Contextor-first implementation verification was performed for the canonical owners:

- `contextor/core/analysis/process_pool_lifecycle.py`: `managed_process_pool`, `terminate_active_process_pools`, and the new worker initializer.
- `contextor/mcp_process_registry.py`: `register_process`, `terminate_registered_process`, and `terminate_registered_record`.
- `contextor/mcp/analysis_jobs.py`: `_run_analysis_worker`, `_start_analysis_job`, and the cooperative analysis shutdown helpers.
- `contextor/mcp_server.py`: `_cleanup_orphaned_processes`, `_cleanup_owned_processes`, `_shutdown_mcp_owned_processes`, and `main`.

Fresh source ranges reported `status=ok` with fresh diagnostics and no syntax, collision, cycle, or attention diagnostics. The current source contains the requested exact contract.

Literal verification found the two production `ProcessPoolExecutor` creation sites using `managed_process_pool`:

- `contextor/core/symbol_engine/indexer.py`
- `contextor/core/reporting_layer/artifact_usage_report.py`

No additional production ProcessPool creation path was introduced or changed. `contextor/__main__.py` contains only a comment reference.

## CENTRAL_REGISTRY_CONTRACT

`mcp_server.main` now computes one central registry directory from `registry_dir(Path.cwd().resolve())`, removes stale orphan records before serving, preserves the previous `CONTEXTOR_MCP_PROCESS_REGISTRY` value, and sets the central registry environment for the server lifetime.

The MCP server registers its own server record in that directory. The cleanup is idempotent, removes the server record, and restores the previous environment value. The MCP root process is never terminated by the child cleanup path.

The analysis worker preserves a preconfigured `CONTEXTOR_MCP_PROCESS_REGISTRY`; it only supplies the repository fallback when no value existed. Existing restoration and removal behavior remains in the worker `finally` path.

## PROCESSPOOL_WORKER_DURABLE_REGISTRATION

When `managed_process_pool` receives the canonical `ProcessPoolExecutor` factory and the central registry environment is present, it wraps the original initializer. Each worker registers itself as:

`kind=process-pool-worker`, `parent_pid=<MCP owner PID>`, `executable=sys.executable`.

The worker installs `multiprocessing.util.Finalize(..., exitpriority=0)` to remove its record at normal worker exit, then invokes the original initializer and original initializer arguments unchanged. Other executor factories and calls without the registry environment preserve the existing behavior.

## WINDOWS_TREE_TERMINATION

`terminate_registered_process` first validates the registry identity (`pid` and optional `create_time`), then on Windows invokes:

`taskkill /F /T /PID <pid>`

with output suppressed, `check=False`, and a five-second timeout. Identity is rechecked afterwards. If the registered PID is still alive, the existing root-only kernel32 `TerminateProcess` fallback is used. POSIX retains root `SIGTERM` behavior.

`terminate_registered_record` reads one record, removes malformed or unreadable records, delegates valid records to `terminate_registered_process`, and removes the registry record in `finally`.

## MCP_SHUTDOWN_ORDER

The exact server cleanup order is:

1. `analysis_jobs.request_analysis_shutdown(timeout=1.5)` for cooperative task cancellation and bounded joins.
2. `terminate_active_process_pools(timeout=1.5)` for graceful executor shutdown and forced fallback owned by the existing pool lifecycle owner.
3. A second bounded `request_analysis_shutdown(timeout=1.5)` to join tasks that were released by pool shutdown.
4. `_cleanup_owned_processes(directory, owner_pid, timeout=1.5)` for registered MCP-owned children, including tree termination on Windows.
5. `_cleanup_orphaned_processes(directory, timeout=1.5)` for recoverable stale records at the next startup.

The server record is removed and the previous registry environment value is restored after this sequence. `atexit` is registered against the same idempotent cleanup function, and the transport remains wrapped by `try asyncio.run(_run()) finally _shutdown_cleanup()`.

## GIT_CHILD_INHERITANCE_EVIDENCE

`contextor/mcp/git_context.py` already reads `CONTEXTOR_MCP_PROCESS_REGISTRY`, registers the Git child with `parent_pid=os.getpid()` and `kind="git"`, and removes the record in `finally`. The central MCP environment now makes this existing registration path inherit the server-owned registry without changing `git_context.py`.

## HARD_ROOT_DEATH_RECOVERY_MODEL

The registry contract remains fail-safe for hard root death: a worker record survives until normal finalization or cleanup, and the next MCP startup can classify the stale record as orphaned and terminate its registered process tree. The cleanup path does not claim ownership of the external MCP root process.

## PROFILE_WORKER_BOUNDARY

Profile-worker ownership and Desktop-owned worker shutdown are explicitly deferred. This task does not change `profile_worker.py`, Desktop GUI close handling, `gui.py`, LIVE service shutdown, or the K5A process-pool lifecycle path.

## EXISTING_TEST_COVERAGE

Added/verified focused coverage:

- `tests/test_process_pool_lifecycle.py::test_mcp_managed_pool_worker_is_durably_registered`
- `tests/test_mcp_child_process_cleanup.py::test_windows_registered_process_uses_taskkill_tree`
- `tests/test_mcp_child_process_cleanup.py::test_analysis_worker_preserves_preconfigured_registry`
- `tests/test_mcp_child_process_cleanup.py::test_request_analysis_shutdown_cooperatively_joins_task`
- `tests/test_mcp_child_process_cleanup.py::test_shutdown_orders_pool_and_registry_cleanup`

Existing focused MCP regression anchors were also run for Git child unregistering and startup/server-owned cleanup behavior.

## VALIDATION

Read-only syntax validation:

`python -m py_compile contextor/core/analysis/process_pool_lifecycle.py contextor/mcp_process_registry.py contextor/mcp/analysis_jobs.py contextor/mcp_server.py`

Result: `PASS`.

Exact new focused tests:

`python -m pytest tests/test_process_pool_lifecycle.py tests/test_mcp_child_process_cleanup.py -q`

Result: `9 passed, 1 warning in 5.03s`.

Existing focused MCP regression anchors:

`python -m pytest tests/test_mcp_regressions.py::test_git_never_inherits_mcp_stdin_and_unregisters_after_exit tests/test_mcp_regressions.py::test_git_unregisters_even_when_communication_fails tests/test_mcp_regressions.py::test_startup_cleanup_stops_only_orphaned_registered_processes tests/test_mcp_regressions.py::test_shutdown_cleanup_stops_only_children_owned_by_server -q`

Result: `4 passed, 1 warning in 5.76s`.

No broad test suite, Desktop restart, MCP restart, process kill, output cleanup, or full analysis was performed.

## CERTIFICATION

MCP_ROOT_REMAINS_EXTERNALLY_OWNED=YES
MCP_CENTRAL_CHILD_REGISTRY=YES
MCP_ANALYSIS_PRESERVES_CENTRAL_REGISTRY=YES
MCP_PROCESSPOOL_WORKERS_DURABLY_REGISTERED=YES
MCP_PROCESSPOOL_GRACEFUL_SHUTDOWN=YES
WINDOWS_REGISTERED_CHILD_TREE_TERMINATION=YES
ORPHANED_POOL_WORKER_RECOVERABLE_NEXT_START=YES
GIT_CHILD_REGISTRATION_CENTRALIZED=YES
PROFILE_WORKER_OWNERSHIP_IMPLEMENTED=NO
DESKTOP_OWNERSHIP_TOUCHED=NO
PY_COMPILE=PASS
FOCUSED_TESTS=PASS

## FILES_CHANGED

The current worktree has no observable uncommitted diff for the implementation files when this report was regenerated. The implementation state was verified in these exact files:

- `contextor/core/analysis/process_pool_lifecycle.py`
- `contextor/mcp_process_registry.py`
- `contextor/mcp/analysis_jobs.py`
- `contextor/mcp_server.py`
- `tests/test_process_pool_lifecycle.py`
- `tests/test_mcp_child_process_cleanup.py`

`walkthrough.md` is the report file and is excluded from implementation-file diff accounting.

ACTUAL_DIFF=DIFFS=NONE_IN_CURRENT_WORKTREE
DIFF_NOTE=The requested implementation is present in the current repository state, but no uncommitted source/test diff was available at report time; no fabricated diff is reported.

## MUST_NOT_CHANGE_CONFIRMED

- Desktop `on_closing` and K5A Desktop process-pool ownership: unchanged.
- `profile_worker.py` ownership: unchanged.
- `contextor/core/git_context.py`: unchanged.
- External MCP root process ownership: preserved.
- `contextor/core/runtime_trace.py`: unchanged.
- LIVE authority/service shutdown semantics: unchanged.

## STOP

STATUS=STOP_AND_WAIT_FOR_PROCEDUJ
