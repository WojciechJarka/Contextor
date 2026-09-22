# CPA10K7G2B — PERSISTENT BACKEND OWNER DISCOVERY

STATUS=DISCOVERY_COMPLETE
HEAD=a382c6aa342f8a8df54f0e3a863cfd29ae70fcb7
FILES_CHANGED=C:\Temp\Contextor_Repo\walkthrough.md
REPOSITORY=C:\Temp\Contextor_Repo
CANONICAL_LIVE_REVISION=1335
CANONICAL_STATE=FRESH
WORKSPACE_SYNC=VERIFIED_FOR_FETCHED_SOURCE_SYMBOLS

## Scope and integrity

Discovery only. No production, test, config, or documentation source was edited. No pytest command, persistent backend launch, process start/stop, or full repository analysis was performed.

At discovery start, `git status --short` returned ` M walkthrough.md`; that was the prior CPA10K7G2A report. This task overwrites that report as requested. `git rev-parse HEAD` returned the HEAD above.

Contextor LIVE poll after revision 1335 returned latest_revision=1335, continuous continuity, resync_required=false, and fresh diagnostics (0 syntax errors, 0 collisions, 0 cycles). Contextor file contexts for the relevant modules also resolved at revision 1335. Exact symbol fetches were fresh, workspace_sync=verified, provenance=live. Local `rg` was used afterward only to confirm source anchors, test names, config text, and security API literals.

`contextor_fact_lineage` was considered and its current documentation read. Its only v1 families are `artifact_consumption`, `syntax_diagnostics`, and `symbol_calls`; none is a process/backend lifecycle fact family, so no unsupported family was queried. Symbol lineage and call-context were queried for the process registry, cleanup, CLI, and LIVE startup owners.

## CURRENT_OWNERS

| Owner / absolute path | Responsibility and direct consumers | Contextor blast radius / tests | Reuse assessment |
|---|---|---|---|
| `C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py` | Process record directory, process identity, JSON registration/removal, record matching, termination. `register_process` and `remove_record` direct consumers: `contextor.core.analysis.git_context`, `contextor.core.analysis.process_pool_lifecycle`, `contextor.mcp.tools.contextor_profile_analysis`, `contextor.mcp_server`. Termination direct consumers: `contextor.mcp_server`, `tests.test_mcp_child_process_cleanup`. | Module context: 11 direct consumers, 194 transitive consumers, 128 covering test modules. | Process facts and record primitives are reusable in their current scope; parent-owned cleanup and Windows termination do not provide persistent-backend ownership or a race-free stop guarantee. |
| `C:\Temp\Contextor_Repo\contextor\mcp_server.py` | MCP transport/auth construction, server role, registry selection, root registration, startup orphan cleanup, atexit/shutdown cleanup, HTTP run. `main` is called through `contextor.mcp_main`. | 32 direct/transitive consumers in module context; 31 covering test modules. | Correct owner for current MCP server lifecycle and G2A behavior; it contains no backend management command API. |
| `C:\Temp\Contextor_Repo\contextor\mcp_main.py` | Dedicated `contextor-mcp` entrypoint imports and calls `contextor.mcp_server.main`. | Project script entrypoint; module context reports no static consumers/tests. | Separate MCP-server entrypoint, not the top-level `contextor` CLI router. |
| `C:\Temp\Contextor_Repo\contextor\__main__.py` | Top-level application entrypoint; `--gui` selects GUI, all other args route to `contextor.cli.main`. | 2 direct module consumers; 1 covering test module (`tests.test_gui_single_instance`). | Existing top-level routing seam. |
| `C:\Temp\Contextor_Repo\contextor\cli.py` | `argparse` CLI parser and analysis dispatch. Current parser has positional repository path and `--layer`, `--file`, `--output`, `--quiet`, `--version`; no backend subcommands. | 1 direct consumer (`contextor.__main__`), 3 transitive; module context lists 1 covering test module. | Current CLI owner, but no existing backend command contract/parser. |
| `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py` | Canonical LIVE service startup coordinator, LIVE-specific startup lock, Windows spawn helper, service owner watchdog. `connect_or_start` direct consumers include LIVE package/watcher/UI and its focused tests. | 14 direct / 65 transitive consumers; 55 covering test modules. | Useful evidence/reference for singleton startup and Windows spawn; its service is explicitly owner-scoped and is not a persistent MCP backend primitive as-is. |
| `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py` | Canonical LIVE authority lease, cross-process domain file lock, atomic JSON writer. | 5 direct / 70 transitive consumers; 58 covering test modules. | General OS-lock mechanics exist, but the owner/contract is LIVE authority lease, not backend start coordination. |
| `C:\Temp\Contextor_Repo\contextor\core\paths.py` | General path utilities including atomic sibling-temp replacement. | 45 direct / 241 transitive consumers; 146 covering test modules. | Atomicity only; no secret ACL/storage contract. |
| `C:\Temp\Contextor_Repo\contextor\core\repository_identity.py` | Durable repository identity creation/lookup; record has schema_version, repo_id, repo_name, root_path, created_at. | Queried canonical implementation; this identity is repository-scoped, not process/backend-scoped. | Not a backend process record or secret store. |

## REUSABLE_PRIMITIVES

- `contextor.mcp_process_registry.registry_dir(root)` resolves to `root/.contextor/mcp_processes`. `CONTEXTOR_MCP_PROCESS_REGISTRY` can override that directory through the current MCP server environment.
- `register_process` writes one JSON record per kind/PID via a sibling temporary file and replace. Present fields: `pid`, `parent_pid`, `kind`, `executable`, `creation_time`, `parent_creation_time`, `registered_at`. This is durable process metadata, but has no host, HTTP port, transport, backend status, or token fields.
- On Windows, `process_identity(pid)` gets image path, alive state, and process creation FILETIME through `GetProcessTimes`. `record_matches_process` compares executable basename when available and compares creation time only when both recorded and current values are non-null.
- `connect_or_start` uses an exclusive-create LIVE startup lock; `RuntimeLeaseManager` also has a cross-process OS file-lock implementation. These prove analogous primitives for LIVE startup/lease only.
- `contextor.core.paths.atomic_write` and `runtime_lease._atomic_write_json` provide atomic-replacement patterns. Neither establishes secret-file permissions.
- The existing G2A HTTP verifier is constructed from `CONTEXTOR_MCP_TOKEN` and attached to FastMCP. `_create_mcp` removes that variable from the process environment after construction; the verifier retains the token in memory.
- `PersistentIdentityRegistry` / `ensure_repository_identity` atomically create repository identity metadata under a central identity directory; it does not record process identity or MCP endpoint/lifecycle state.

## MISSING_PRIMITIVES

Backend-specific gaps (not claims that no analogous generic mechanism exists):

- No durable persistent-backend root/endpoint lifecycle record is registered by the current server role.
- No backend-specific singleton/start lock or command owner; existing locks are scoped to LIVE service startup, LIVE authority leases, or repository identity creation.
- No backend start/status/stop commands or top-level CLI route for them.
- No MCP bearer-token generator plus durable protected secret store. No explicit Windows ACL/DACL, DPAPI, Credential Manager, or keyring primitive was found in `contextor`. Two unrelated modules pass POSIX-style `0o600` modes to file open; these are not a demonstrated Windows ACL abstraction.
- No backend-specific detached launcher with independent lifetime/cleanup contract. The existing LIVE spawn helper is owner-scoped and has a fallback without breakaway.
- Existing registry termination does not prove atomic identity-bound termination against PID reuse.
- Repository config examples contain stdio MCP stanzas only; no HTTP backend client stanza is present. The repo does not specify the exact FastMCP HTTP route path.

## BACKEND_IDENTITY_EVIDENCE

DIRECT_EVIDENCE — `contextor/mcp_process_registry.py:16-17, 79-122, 150-166`:

- Default path is `.contextor/mcp_processes` beneath the supplied root.
- The JSON schema fields are PID, parent PID, process kind, executable, process creation time, parent creation time, and registration timestamp.
- Windows process creation identity is obtained with `GetProcessTimes`; the persisted numeric value is the FILETIME creation value.
- Matching is conditional: if either stored creation time or current creation time is null, creation-time inequality is not rejected by that check. Executable comparison is basename-only when both image values are available.

CODE_PATH_PROVED — `contextor/mcp_server.py:963-976`:

- `_register_server_root(..., role="persistent-backend")` returns `None`; it does not create an `mcp-server` root record. For host-owned role it calls `register_process`.
- `test_persistent_backend_role_has_no_host_owned_root_record` covers this G2A contract.

INFERENCE — the registry can physically encode PID/start identity for a process, but its present parent fields and parent-based cleanup semantics do not by themselves establish persistent backend ownership independent of the launching Codex session.

UNKNOWN — there is no current backend record schema for host/port/transport/status/lifecycle metadata.

## STARTUP_RACE_EVIDENCE

DIRECT_EVIDENCE — `contextor/core/live_state/runtime.py:856-1033`:

- LIVE `connect_or_start` checks for an existing service, creates sibling `live_service_start.lock` with `os.open(O_CREAT | O_EXCL | O_WRONLY)`, retries while another lock exists, and removes a lock whose mtime is older than the effective startup budget. It rechecks for a live service before spawning and removes its lock in `finally`.
- This is a concrete single-owner mechanism for Canonical LIVE service startup, not a backend manager contract. Its stale-lock deletion is age-based.

DIRECT_EVIDENCE — `contextor/core/live_state/runtime_lease.py:760-809`:

- `_DomainFileLock` combines a process-local thread lock with `msvcrt.locking(...LK_NBLCK...)` on Windows or `fcntl.flock(...LOCK_EX | LOCK_NB)` elsewhere, with a timeout.
- `_atomic_write_json` uses a temporary sibling, flush/fsync, and `os.replace`; `contextor.core.paths.atomic_write` also uses a temporary sibling and replace.
- Repository identity creation has its own O_EXCL lock in `contextor/core/repository_identity.py:118-167`.

CONCLUSION — no existing primitive is wired to guarantee one persistent MCP backend for concurrent `backend start` operations. Existing locks are scoped to separate owners/contracts; no alternative lock design is proposed here.

## DETACHED_SPAWN_EVIDENCE

DIRECT_EVIDENCE — `contextor/core/live_state/runtime.py:741-801, 856-1033, 1413-1447, 1546-1562`:

- The only identified reusable Windows spawn helper is `_spawn_runtime_subprocess`, called by LIVE `connect_or_start`.
- Primary Windows flags are `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`; on WinError 5 it retries once with `CREATE_NO_WINDOW` only. It passes explicit `cwd` and `env`, and sets stdin/stdout/stderr to `DEVNULL` on both branches. Non-Windows uses creationflags=0 and the same DEVNULL streams.
- It does not set `DETACHED_PROCESS` or `start_new_session`; process-group/session detachment is not established by this code.
- `connect_or_start` can pass `--owner-pid` to the child. LIVE `run_service` opens a handle to that owner on Windows and its watchdog closes the server when the owner process signals; non-Windows polls owner PID liveness.
- Therefore the primary breakaway branch is intended to avoid host Job Object termination when the launcher exits, but the LIVE service remains owner-scoped when an owner PID is supplied. The fallback does not break away. No actual detached launch was performed.

TEST/CODE LIMIT — `tests/test_live_job_object.py` asserts flags/fallback and contains a Windows-only Job Object integration test; these are LIVE-service tests, not MCP-backend lifecycle certification.

## DURABLE_RECORD_EVIDENCE

DIRECT_EVIDENCE:

- Current process registry path: `C:\Temp\Contextor_Repo\.contextor\mcp_processes` when the repo root is supplied and no environment override is set.
- Process registry JSON contains PID/process identity and parent ownership fields listed above, but not HTTP host, port, transport, endpoint, registry path reference, status, or backend lifecycle state.
- In persistent-backend role, server root registration returns no record; server atexit still runs `_shutdown_mcp_owned_processes`, which shuts down analysis work and cleans records owned by that server PID, then orphaned records.
- The repository identity registry stores repository identity metadata, not backend runtime metadata.

INFERENCE — current shutdown/orphan cleanup is session/server-process lifecycle logic, not a management plane for a persistent backend. Reusing the child registry for backend ownership without accounting for parent-based cleanup would preserve an ownership tie the persistent role is meant to avoid.

## TOKEN_STORAGE_EVIDENCE

DIRECT_EVIDENCE — `contextor/mcp_server.py:525-571`:

- HTTP bootstrap reads `CONTEXTOR_MCP_TOKEN`, rejects missing/shorter-than-32/surrounding-whitespace values, creates the bearer verifier, passes it as `FastMCP(..., auth=auth)`, then removes the environment variable.
- No token value is persisted by this path. The verifier retains its configured credential in process memory.

LITERAL_SOURCE_CHECK:

- `rg` found no explicit Windows ACL/DACL, DPAPI, Credential Manager, keyring, or `chmod` helper in `contextor`.
- The only `0o600` literals are in `contextor/core/runtime_trace.py` and `contextor/core/analysis/full_analysis_coordinator.py`; no Windows ACL semantics or reusable secret-storage contract is proved by those hits.
- `contextor/core/live_state/ipc.py` uses `secrets.token_bytes(32)` for an IPC auth key; that is not the MCP bearer-token lifecycle and no durable bearer secret store is shown.
- Current tests cover token validation/verifier behavior and environment removal; they do not cover persistent secret storage or Windows permissions.

## CLI_ROUTING_EVIDENCE

DIRECT_EVIDENCE:

- `pyproject.toml:21-23`: `contextor = contextor.__main__:main`; `contextor-mcp = contextor.mcp_main:main`.
- `contextor/__main__.py:78-92`: `--gui` selects GUI; otherwise arguments go to `contextor.cli.main`.
- `contextor/cli.py:23-69, 72-125`: current parser has no subparsers/backend actions and routes to repository analysis.
- `contextor/mcp_main.py:4-7`: dedicated MCP server entrypoint calls `contextor.mcp_server.main`.
- `config_jsons/mcp_config.json` and `config_jsons/config.toml` show stdio invocation of `contextor.mcp_server`; they contain no persistent HTTP backend client stanza.

CONCLUSION — existing top-level command seam is `contextor.cli.main` (reached through `contextor.__main__.main`). There are currently no `backend start/status/stop` routes or command-level tests identified.

## STOP_SAFETY_EVIDENCE

CODE_PATH_PROVED — `contextor/mcp_process_registry.py:150-245, 248-266`:

1. `terminate_registered_process` calls `record_matches_process` once before termination.
2. On Windows it then runs `taskkill /F /T /PID <pid>`.
3. If that command returns and the PID is still alive, fallback opens the PID and calls `TerminateProcess`; it does not re-check the opened process handle's creation time or image against the record.
4. `record_matches_process` itself only compares creation times when both are non-null.

INFERENCE — this is useful stale-record screening, but it is not a proven guarantee against a PID being recycled between the initial check and PID-based termination. It is not sufficient evidence for a strict “never kill a reused PID” backend stop guarantee.

TEST_COVERAGE — `tests/test_mcp_regressions.py::test_registry_rejects_reused_pid` covers a recorded/current creation-time mismatch before termination. `tests/test_mcp_child_process_cleanup.py::test_windows_registered_process_termination_uses_tree_kill` mocks a matching initial identity followed by a dead PID and asserts taskkill arguments; it does not exercise PID reuse during the kill window. No test of that race was found.

## CLIENT_CONNECTION_EVIDENCE

DIRECT_EVIDENCE — `contextor/mcp_server.py:525-571, 1073-1088` and `pyproject.toml`:

- Server transport is selected as Streamable HTTP; HTTP run receives host from `CONTEXTOR_MCP_HOST` (default `127.0.0.1`) and port from `CONTEXTOR_MCP_PORT` (default `8765`).
- Server construction receives the bearer verifier; the client must present the configured bearer credential through the HTTP auth contract.
- The repo’s checked-in MCP client examples configure stdio, not HTTP.

UNKNOWN — the repo does not set the Streamable HTTP URL path or provide a Codex HTTP stanza. The route path is delegated to pinned FastMCP (2.12.4) defaults, so this discovery does not assert an exact URL path or invent client configuration fields. Code-level connection requirements established here are host, port, Streamable HTTP transport, and bearer credential.

## TEST_COVERAGE

Static inspection only; no test was run.

Relevant existing tests:

- `tests/test_mcp_shared_backend_server_mode.py::test_http_transport_requires_bearer_token`
- `tests/test_mcp_shared_backend_server_mode.py::test_http_verifier_accepts_only_exact_token`
- `tests/test_mcp_shared_backend_server_mode.py::test_persistent_backend_role_has_no_host_owned_root_record`
- `tests/test_mcp_regressions.py::test_registry_rejects_reused_pid`
- `tests/test_mcp_regressions.py::test_startup_cleanup_stops_only_orphaned_registered_processes`
- `tests/test_mcp_regressions.py::test_shutdown_cleanup_stops_only_children_owned_by_server`
- `tests/test_mcp_child_process_cleanup.py::test_windows_registered_process_termination_uses_tree_kill`
- `tests/test_mcp_child_process_cleanup.py::test_mcp_shutdown_order_is_analysis_pool_owned_orphan`
- `tests/test_live_job_object.py::test_windows_primary_spawn_flags_contain_breakaway_and_no_window`
- `tests/test_live_job_object.py::test_breakaway_denied_creation_performs_exactly_one_legacy_fallback`
- `tests/test_live_state_ipc.py::test_real_process_busy_update_does_not_spawn_second_live_owner`

No backend start/status/stop CLI tests, bearer secret persistence/ACL tests, backend concurrent-start tests, or identity-bound PID-reuse-during-termination tests were identified.

## BLAST_RADIUS

- Process registry is high fan-out: 11 direct / 194 transitive consumers and 128 test modules in Contextor file context. Changing its record/termination contract has broad process-management impact beyond MCP.
- MCP server file context reports 32 direct/transitive consumers and 31 covering test modules. Server startup/shutdown ownership changes cross MCP tools and lifecycle tests.
- CLI and top-level entrypoint are narrower: `contextor.cli` has 1 direct / 3 transitive consumers and 1 covering test module; `contextor.__main__` has 2 direct consumers and 1 covering test module.
- LIVE runtime/spawn is shared infrastructure: runtime has 14 direct / 65 transitive consumers and 55 covering test modules; runtime_lease has 5 direct / 70 transitive consumers and 58 covering test modules. Treat them as reference owners unless a later approved scope explicitly changes LIVE behavior.
- Repository path utilities have 45 direct / 241 transitive consumers and 146 covering test modules; a generic write helper change would have a broad blast radius.

## FILES_REQUIRED_FOR_IMPLEMENTATION

Candidate files directly implicated by the requested future backend lifecycle, with full absolute paths:

- `C:\Temp\Contextor_Repo\contextor\cli.py` — current parser and analysis dispatch; no backend subcommands exist.
- `C:\Temp\Contextor_Repo\contextor\__main__.py` — top-level executable routing path to the CLI.
- `C:\Temp\Contextor_Repo\contextor\mcp_server.py` — HTTP/auth construction, persistent role, server root registration, and shutdown hooks.
- `C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py` — current durable process record, identity matching, and termination contract.
- `C:\Temp\Contextor_Repo\tests\test_mcp_shared_backend_server_mode.py` — existing G2A transport/auth/role regression coverage.
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py` — process identity and startup/shutdown cleanup coverage.
- `C:\Temp\Contextor_Repo\tests\test_mcp_child_process_cleanup.py` — termination and MCP shutdown ordering coverage.

Reference-only files, not established as edit targets by this discovery:

- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py` — LIVE startup-lock, spawn, and owner-watchdog precedent.
- `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py` — LIVE OS file lock and atomic JSON write precedent.
- `C:\Temp\Contextor_Repo\contextor\core\paths.py` — general atomic replacement helper.
- `C:\Temp\Contextor_Repo\contextor\core\repository_identity.py` — repository identity metadata/creation lock, not backend identity.
- `C:\Temp\Contextor_Repo\tests\test_live_job_object.py` and `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py` — existing LIVE spawn/single-owner behavior, not backend lifecycle tests.
- `C:\Temp\Contextor_Repo\config_jsons\mcp_config.json`, `C:\Temp\Contextor_Repo\config_jsons\config.toml`, and `C:\Temp\Contextor_Repo\README.md` — inspect/update only if a later task explicitly includes client setup or CLI documentation. The current config files are stdio examples.
- `C:\Temp\Contextor_Repo\pyproject.toml` — current `contextor` and `contextor-mcp` scripts are already declared; no new executable is established as required here.

No full module was required to answer this discovery. Before a later implementation, read the complete contents of the source candidates and their focused tests above; this discovery fetched exact symbol bodies and targeted test bodies, not whole-file snapshots.

## Diff and next gate

PRODUCTION_TEST_CONFIG_DOC_FILES_CHANGED=NO
ACTUAL_DIFF=DIFFS=NONE
TESTS=NOT_RUN_BY_CONTRACT
PROCESSES_STARTED_OR_STOPPED=NO
FILES_CHANGED=C:\Temp\Contextor_Repo\walkthrough.md
NEXT_STEP=WAIT_FOR_USER_COMMAND_PROCEDUJ
