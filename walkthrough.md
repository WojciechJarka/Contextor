# CONTEXTOR PY315-R4E — discovery

## PREFLIGHT

HEAD `af528d8dc5dfc05a80489c35cbf5d5e2198b975f`; Git worktree clean before probes. Contextor MCP used first for implementations and call context (revision 939); lineage preview was fresh but `workspace_sync=unverified`, so exact source was checked locally. No repo source/test edits, production restart, LIVE switch, or full pytest.

## EXACT_SOURCE_EVIDENCE

- `contextor/mcp_backend_control.py:514-539`: `_backend_python()` selects `.venv/Scripts/python.exe` on Windows.
- `:582-654`: `_spawn_backend_process()` launches `-u -m contextor.mcp_main`, first with `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`, falling back to `CREATE_NO_WINDOW` on WinError 5.
- `:657-680`: `_spawn_identity_record()` takes identity from `process.pid` (Popen PID).
- `:683-691`: `_cleanup_spawned_process()` calls `terminate_registered_process(identity_record)` without checking its result.
- `:706-765`: readiness polls authenticated backend status; `process.poll()` watches Popen PID.
- `:768-863`: `start_backend()` uses that Popen identity record for exception cleanup.
- `:1011-1094`: `stop_backend()` terminates the backend record owner by creation identity, waits for owner exit, then cleans registered children.
- `contextor/mcp_main.py:6-20`: only role `persistent-backend` invokes `protect_persistent_backend()`.
- `contextor/mcp_backend_job.py:104-168`: protection assigns current process to a Job with kill-on-close and breakaway allowed.
- `contextor/mcp_server.py:1092-1104,1122-1135`: default role is `host-owned`; its server root is registered, while persistent backend root is not.
- `contextor/mcp_server.py:776-798`: shutdown terminates pools, then cleans owned and orphaned registry processes.
- `contextor/mcp_process_registry.py:669-687`: Windows termination invokes one identity-bound handle termination; no `/T` equivalent.
- `contextor/core/live_state/runtime.py:765-857`: LIVE subprocess requests breakaway and guarded backend Job checks it is outside the Job.

## WINDOWS_VENV_REDIRECTOR_PID_MAP

DIRECT_EVIDENCE, private Python 3.10 probe: venv Popen PID 13076 (`.venv\Scripts\python.exe`, creation 134378744512960938) spawned actual Python PID 13376 (base `python.exe`, creation 134378744513547395), whose parent was 13076. Popen remained waiting while actual Python ran. Both exited 0. Base executable control: Popen PID = actual PID = 624, creation 134378744545772205. Thus `_spawn_identity_record()` identifies redirector on this machine.

## VENV_ISOLATION_EVIDENCE

Venv child: `sys.executable=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, `sys._base_executable=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe`, `sys.prefix=C:\Temp\Contextor_Repo\.venv`; `fastmcp` and `orjson` import specs were present. Base executable control reported `sys.prefix=sys.base_prefix` at the base installation. This proves interpreter identity and two dependency lookups, not full dependency isolation.

## NESTED_JOB_NORMAL_EXIT

DIRECT_EVIDENCE, isolated scripts reused from `tests/test_mcp_job_tree_isolated_windows.py`, owner launched via actual venv redirector: redirector 8564, Job owner 8604, child 6332, grandchild 10352, breakaway LIVE analogue 12560. Creation identities captured. On normal owner exit: owner, redirector, child and grandchild DEAD; LIVE analogue ALIVE.

## NESTED_JOB_FORCED_EXIT

DIRECT_EVIDENCE: redirector 988, Job owner 2200, child 15164, grandchild 7948, LIVE analogue 11084. Creation-bound termination of **actual owner 2200** returned true. Owner, redirector, child and grandchild DEAD; LIVE analogue ALIVE. This does not establish the effect of terminating only the redirector.

## LIVE_ANALOGUE_SURVIVAL

Both isolated variants verified the breakaway process ALIVE after owner exit, then terminated it by captured creation identity. Production LIVE was not started.

## HOST_OWNED_MCP_TREE_COVERAGE

CODE_PATH_PROVED: host-owned role does not install the backend Job. Its root is registered. Windows registry termination targets one identity-bound process handle. Shutdown handles registered owned children/orphans and pools; no blanket cleanup of an unregistered grandchild after root loss was demonstrated. Runtime coverage of all host-owned spawn paths is UNKNOWN. Legacy `/F /T /PID` descendant parity is not established.

## PRIVATE_PROBE_CLEANUP

All owner, redirector, child and grandchild records resolved; `cleanup_unresolved=[]` in both Job variants. Both LIVE analogues were creation-bound terminated after survival checks. Boundary-A children exited 0. Private files remain under `%LOCALAPPDATA%\Temp\contextor_r4e_probe_874447f4836a47d19f300e053897ba45`; no production process was targeted.

## PRODUCTION_STARTUP_IMPLICATIONS

CODE_PATH_PROVED plus DIRECT_EVIDENCE: production launch records the venv redirector PID, while the backend Job belongs to the actual interpreter. Startup exception cleanup terminates only the recorded redirector and ignores the result. Whether that also ends the actual owner and Job tree is UNKNOWN. Separate backend status may record actual owner, but no production restart was performed.

## MCP_AUDIT

MCP call context confirmed `_spawn_backend_process` caller `start_backend`, `_spawn_runtime_subprocess` caller `connect_or_start`, and shutdown helper dependencies. Lineage preview returned complete but `workspace_sync=unverified`; exact source was cross-checked. No MCP `update_file`.

## REMAINING_UNKNOWN

- Effect of terminating redirector only on actual owner and Job tree during failed startup.
- Whether production backend status publishes actual interpreter PID and creation identity under this venv redirector.
- Exhaustive host-owned unregistered grandchild coverage after abnormal exit/restart.
- Fresh restarted MCP/Desktop adoption and production backend/LIVE behavior.

## FINAL_VERDICT

`BLOCKED_MULTIPLE_BOUNDARIES` — redirector/actual-owner startup cleanup boundary and host-owned unregistered descendant tree parity remain unverified. Isolated actual-owner Job termination passed normal and forced exit probes, without certifying those production boundaries.

## FILES_CHANGED

None (source/test/docs). `walkthrough.md` overwritten for this report.

## ACTUAL_DIFF / FULL_DIFF

DIFFS=NONE (source/test/docs).
