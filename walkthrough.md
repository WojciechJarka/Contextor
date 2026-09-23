# CPA10K7G2A_SHARED_BACKEND_SERVER_MODE_HARDENING

STATUS=BLOCKED_SOURCE_DRIFT

HEAD_BEFORE=13ece0c1a15720cf070b78c4b2148d43477fa52a
HEAD_AFTER=13ece0c1a15720cf070b78c4b2148d43477fa52a
LIVE_REVISION_BEFORE=1344
LIVE_REVISION_AFTER=1344

FILES_CHANGED=C:\Temp\Contextor_Repo\walkthrough.md

IMPLEMENTATION_RESULT=NOT_APPLIED; exact requested main() replacement conflicts with current source and would remove existing persistent-backend lease handling. Stopped without editing production or test files.

AUTH_CONTRACT=NOT_MODIFIED; implementation was not started because the literal main() replacement is source-drift blocked.
PROCESS_REGISTRY_CONTRACT=NOT_MODIFIED; implementation was not started.
PERSISTENT_ROLE_CONTRACT=BLOCKED_SOURCE_DRIFT; current source acquires/releases PersistentBackendLease, but the supplied exact main() replacement does not preserve that behavior.

## DIRECT_EVIDENCE

- Contextor `get_file_edit_context` for `contextor/mcp_server.py`: canonical revision 1344, provenance `live`, `workspace_sync=verified`; syntax diagnostics `checked_and_none`, zero errors; collision and cycle diagnostics fresh with zero counts.
- Contextor minimal edit projection: module `contextor.mcp_server`, ID `213/1`, adapter layer; 32 direct/transitive module consumers; 31 covering tests (static dependency reachability). Samples included `contextor.mcp_main` and MCP contract tests.
- Contextor `get_module_blast_radius`: 63 artifacts, fresh graph/topology/artifact-consumption/cycle/collision/lineage families at revision 1344; 28 direct artifact-consumer modules and zero additional downstream modules. This metric has artifact-consumer semantics, distinct from the 32-module import/dependency count above.
- Contextor `get_symbol_implementation` for `contextor.mcp_server::main`: complete implementation at lines 982-1126, canonical revision 1344, `workspace_sync=verified`.
- Contextor `get_symbol_lineage` for `main`: exact active artifact `A1484/1`; selected interface/connections were complete and metadata-consistent at revision 1344. Confirmed caller connection is `contextor.mcp_main`.
- Contextor `get_live_events` after revision 1344: `continuity=continuous`, `resync_required=false`, no newer canonical mutation events; latest revision remained 1344.

## CODE_PATH_PROVED

Contextor's fetched current `main()` contains all of the following:

1. It reads `CONTEXTOR_MCP_HOST` and `CONTEXTOR_MCP_PORT` for HTTP mode.
2. For role `persistent-backend`, it calls `PersistentBackendLease.acquire(host=http_host, port=http_port, transport="streamable-http", process_registry=process_directory)`.
3. It registers `backend_lease.release` with `atexit`.
4. An outer `finally` releases the lease after the server run.

The task's supplied literal replacement instead proceeds from `process_directory` directly to orphan cleanup and has no lease acquire/release path. Applying it verbatim would erase current lease lifecycle behavior. The contract explicitly forbids adapting the replacement or inventing a merge, so execution stopped at this mismatch.

## CONTRACT_PROVED

The pasted instructions say that if an anchor does not match current source, stop and report `BLOCKED_SOURCE_DRIFT`; they also require replacing the whole current `main()` literally. The current `main()` has the additional lease lifecycle described above. No alternative implementation was selected.

## LITERAL_TEXT_CONFIRMATION

After Contextor discovery, exact source confirmation was run:

```powershell
rg -n -C 3 'PersistentBackendLease|backend_lease|def main\(|_cleanup_orphaned_processes|run_http_async' contextor/mcp_server.py
```

Observed matches included:

```text
192- from contextor.mcp_backend_state import (
193:     PersistentBackendLease,
982: def main():
1037:     backend_lease = None
1039:     if role == "persistent-backend":
1041:             PersistentBackendLease.acquire(
1049:         atexit.register(
1050:             backend_lease.release
1124:     finally:
1125:         if backend_lease is not None:
1126:             backend_lease.release()
```

The prescribed test file `tests/test_mcp_shared_backend_server_mode.py` already exists in the working tree. Its contents were not inspected or modified after the blocking source drift was established.

## INFERENCE

Literal replacement would remove an existing persistent-backend ownership/lease lifecycle. This conclusion follows from comparing the fetched current implementation with the exact replacement body in the pasted contract; no test or runtime behavior was inferred.

## UNKNOWN

- Whether the user intends the literal G2A contract to be revised to preserve the lease behavior is not specified.
- No conclusion is made about test results because no tests were run.

## TEST_RESULTS

NOT_RUN=STOPPED_ON_BLOCKED_SOURCE_DRIFT
No `py_compile`, focused pytest, HTTP backend, detached process, MCP restart, or Desktop restart was run.

## CONTEXTOR_VERIFICATION

PRE_EDIT_REVISION=1344
POST_CHECK_REVISION=1344
WORKSPACE_SYNC=verified
SYNTAX_ERRORS=0
NAME_COLLISIONS=0
CYCLES=0
RESYNC_REQUIRED=NO
CONSUMER_AND_TEST_OWNERSHIP=VERIFIED_BY_CONTEXTOR

Relevant Contextor calls: `get_mcp_documentation` for the used tools; `get_live_events`; `get_file_edit_context` (full compact and minimal projections); `get_module_blast_radius`; `get_symbol_implementation`; and `get_symbol_lineage`.

## WORKTREE_OBSERVATION

At inspection, `git status --short` showed `walkthrough.md` modified and the unrelated-to-this-stage paths `contextor/mcp_backend_secret.py` and `tests/test_mcp_backend_secret.py` untracked. Those source/test paths were not edited by this task. `tests/test_mcp_shared_backend_server_mode.py` existed and was not changed. HEAD did not change.

MCP_SERVER_RESTART_REQUIRED=NO_SOURCE_CHANGED_THIS_TURN; YES_AFTER_A_FUTURE_APPROVED_MCP_SERVER_SOURCE_CHANGE

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE
No production, test, or documentation source file was changed. `walkthrough.md` is the report artifact and is excluded from source/test diffs.
