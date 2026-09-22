HEAD=967750558c6550e4f5928fcb2c93cb601626e1f1
WORKTREE_STATUS=CLEAN_BEFORE_REPORT_WRITE
LIVE_REVISION=1329
WORKSPACE_SYNC=verified

# CPA10K7G0 — persistent shared backend ownership discovery

STATUS=COMPLETED_DISCOVERY_ONLY
SCOPE=DISCOVERY_RETRIEVAL_ONLY
REPORT_TIME=2026-09-22
REPOSITORY=C:\Temp\Contextor_Repo

## BASELINE

K7_BASELINE=ACCEPTED_AS_CONTRACT

The previously established K7A–K7F facts were accepted and not re-measured. No additional Codex session, process fan-out, teardown, restart, or runtime experiment was performed. Current source and LIVE evidence did not contradict the accepted baseline; therefore SOURCE_DRIFT_FROM_K7_BASELINE=NO.

Evidence discipline:

- DIRECT_EVIDENCE: current source ranges, current local Codex help/config, current FastMCP runtime introspection, and Contextor LIVE revision/event state.
- CODE_PATH_PROVED: behavior established from the exact canonical implementation path named below.
- CONTRACT_PROVED: behavior established from the supplied CPA10K7G0 contract.
- INFERENCE: bounded interpretation explicitly marked as such.
- UNKNOWN: not claimed where the behavior belongs to Codex host lifecycle, external deployment, or an uninspected library boundary.

Current freshness evidence:

- Contextor get_live_events(repo_path=C:\Temp\Contextor_Repo, limit=5) returned revision=1329, latest_revision=1329, resync_required=false.
- The current LIVE event stream includes RUNTIME_AUTHORITY_READY with status=READY, service PID 3940, lease generation 88, and reason endpoint, lease and authority identity parity verified.
- Contextor source retrieval returned canonical_revision=1329, canonical_state=fresh, workspace_sync=verified, and provenance=live for the inspected symbols.
- git status --short was empty before this report was written.

## MCP_SERVER_LIFECYCLE

Canonical entry and ownership path:

- C:\Temp\Contextor_Repo\contextor\mcp_main.py:4-7, contextor.mcp_main::main, imports contextor.mcp_server.main and calls it.
- C:\Temp\Contextor_Repo\contextor\mcp_main.py:10-12 invokes multiprocessing.freeze_support() and main() under __main__.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:451-453 creates the module-level FastMCP("Contextor") object and adds the input-boundary middleware.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:812-890, contextor.mcp_server::main, owns the server process lifecycle.

Current transport branch:

- C:\Temp\Contextor_Repo\contextor\mcp_server.py:864-868 reads CONTEXTOR_MCP_TRANSPORT, defaulting to stdio.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:869-884 selects HTTP/Streamable HTTP, reads CONTEXTOR_MCP_HOST default 127.0.0.1, reads CONTEXTOR_MCP_PORT default 8765, and awaits mcp.run_http_async(transport="streamable-http", host=host, port=port, show_banner=False).
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:886 awaits mcp.run_stdio_async() for the default path.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:887-890 wraps asyncio.run(_run()) in finally: _shutdown_cleanup().

Current Codex configuration selects the stdio path:

- Local file: C:\Users\DafoO\.codex\config.toml.
- Confirmed Contextor fields: command='C:\Temp\Contextor_Repo\.venv\Scripts\python.exe', args=["-u","-X","utf8","-m","contextor.mcp_server"], cwd='C:\Temp\Contextor_Repo', env with UTF-8/unbuffered settings, required=true, startup_timeout_sec=120, enabled=true.
- No url, bearer_token_env_var, or HTTP header field is present in the current Contextor server block.

Shutdown boundary:

- C:\Temp\Contextor_Repo\contextor\mcp_server.py:840-862 installs the guarded shutdown callback and registers it with atexit; the callback removes the mcp-server record after owned cleanup.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:496-518 performs mcp-owned analysis shutdown, process-pool termination, owned-record cleanup, and orphan-record cleanup.
- The current MCP root is therefore a foreground server process whose lifetime ends with its main() process; current Codex stdio ownership is host-launched and host-associated.

## HTTP_CAPABILITIES

DIRECT_HTTP_SERVER_ALREADY_EXISTS=YES

Code path:

- Contextor already branches to mcp.run_http_async(transport="streamable-http", ...) in contextor/mcp_server.py:869-884.
- The project pins fastmcp==2.12.4 in C:\Temp\Contextor_Repo\pyproject.toml.
- The active virtual environment reports FAST_MCP_VERSION=2.12.4.
- The active FastMCP method signature includes transport, host, port, path, and stateless_http in run_http_async.

Direct local runtime facts:

- CURRENT_CONTEXTOR_HTTP_TRANSPORT=streamable-http.
- CURRENT_CONTEXTOR_HTTP_BIND_ADDRESS=127.0.0.1.
- CURRENT_CONTEXTOR_HTTP_PORT=8765.
- CURRENT_CONTEXTOR_HTTP_ENDPOINT_PATH=/mcp: FastMCP 2.12.4 default; Contextor does not pass a custom path.
- CURRENT_CONTEXTOR_HTTP_STATEFUL_SESSIONS=YES: FastMCP 2.12.4 defaults stateless_http=False; its Streamable HTTP app owns a session manager and supports multiple session IDs in one server process.
- CURRENT_CONTEXTOR_HTTP_AUTH_ENABLED=NO: the active FastMCP object has auth=None; no Contextor auth provider or bearer configuration is passed.
- CURRENT_CONTEXTOR_HTTP_SERVER_PROCESS_LIFETIME=FOREGROUND_MCP_PROCESS: run_http_async is awaited by contextor.mcp_server::main and has no detached-server handoff.

The package implementation was inspected only for capability confirmation. It shows StreamableHTTPSessionManager behind the /mcp route with stateful sessions. This proves that one HTTP server process can serve multiple HTTP sessions; it does not prove a persistent detached Contextor MCP backend exists.

## CODEX_HTTP_CAPABILITIES

DIRECT_CODEX_HTTP_CLIENT_SUPPORTED=YES

Local CLI confirmation:

- codex mcp --help exposes mcp add [OPTIONS] <NAME> (--url <URL> | -- <COMMAND>...).
- The same local help exposes --url as the Streamable HTTP MCP server URL.
- The local help exposes --bearer-token-env-var, restricted to Streamable HTTP.
- The current Contextor configuration does not use this path and was not changed.

Locally confirmed HTTP configuration fields:

CODEX_HTTP_CONFIG_FIELDS_LOCAL_CONFIRMED=url,bearer_token_env_var,enabled,required,startup_timeout_sec

The current local config confirms enabled, required, and startup_timeout_sec for the existing Contextor block. The local CLI confirms url and bearer_token_env_var for HTTP registration. The official Codex MCP documentation also describes http_headers, env_http_headers, and http_headers_helper, but those fields were not present in the current Contextor block and were not treated as locally confirmed schema by this discovery:

CODEX_HTTP_CONFIG_FIELDS_OFFICIAL_DOCS_ONLY=http_headers,env_http_headers,http_headers_helper

Reference used for the Codex HTTP capability boundary: https://learn.chatgpt.com/docs/extend/mcp?surface=cli

Codex local capability conclusion:

- A direct Streamable HTTP client path exists in the installed local Codex CLI.
- The current Contextor configuration does not use it.
- No local evidence was found that Codex requires a local process command when a URL is supplied.
- No claim is made about Codex's external process-disconnect policy; that boundary is outside the repository and current local config.

## PROCESS_OWNERSHIP

The process registry is implemented by C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py:

- registry_dir(root) at lines 16-17 resolves <root>/.contextor/mcp_processes.
- process_identity(pid) at lines 79-91 records executable identity, creation/start time, and liveness.
- register_process(...) at lines 98-122 writes PID, parent PID, kind, executable, creation time, parent creation time, and registration time using a temporary file plus os.replace.
- record_matches_process(...) at lines 150-166 verifies liveness, executable basename, and creation time.
- terminate_registered_process(...) at lines 169-245 uses identity checks before Windows tree termination and bounded fallback termination.

Process-kind inventory:

1. mcp-server

   - Creation owner: contextor.mcp_server::main, mcp_server.py:829-836.
   - Parent identity: parent PID and parent creation time captured by register_process.
   - Lifetime: the MCP stdio or HTTP transport process.
   - Registry owner: mcp_process_registry, selected through CONTEXTOR_MCP_PROCESS_REGISTRY.
   - Normal cleanup: mcp_server.py:840-862 removes the server record after owned cleanup.
   - Orphan cleanup: mcp_server.py:458-481 verifies parent identity and terminates records whose owner is no longer live.
   - Shared-backend assessment: PARTIAL; identity protection is strong, but owned/orphan cleanup is process/parent scoped rather than client-session scoped.

2. git subprocess

   - Creation owner: contextor.core.analysis.git_context::collect_git_context, exact implementation git_context.py:64-131.
   - The function runs a bounded ThreadPoolExecutor of Git commands; the registry registration path is at git_context.py:47-53.
   - Lifetime: command completion and explicit record removal in the surrounding helper path.
   - Registry owner: mcp_process_registry; parent is the current analysis process.
   - Identity/liveness: provided by register_process and process_identity.
   - Shared-backend assessment: YES for this short-lived child utility when the existing parent-owned cleanup contract remains in force.

3. process-pool-worker

   - Creation owner: contextor.core.analysis.process_pool_lifecycle::_initialize_mcp_managed_worker, process_pool_lifecycle.py:48-75.
   - Registry registration: CONTEXTOR_MCP_PROCESS_REGISTRY, parent PID owner_pid, kind process-pool-worker.
   - Lifetime: the worker is attached to the executor; Finalize(remove_record, ...) removes its record at worker exit.
   - Normal cleanup: executor context/finalization and terminate_active_process_pools, process_pool_lifecycle.py:148-223.
   - Identity/liveness: the common registry records PID and process-start identity.
   - Shared-backend assessment: PARTIAL; child ownership is explicit, but the active-executor map and shutdown action are process-local/process-wide.

4. profile-worker

   - Creation owner: contextor.mcp.tools.contextor_profile_analysis::_run_profile_subprocess, registration block contextor_profile_analysis.py:100-122, public wrapper contextor_profile_analysis.py:175-193.
   - Registry registration: kind profile-worker, parent PID os.getpid(), executable sys.executable.
   - Lifetime: the profiling subprocess and the worker tool's cleanup/finally path.
   - Identity/liveness: common registry identity checks.
   - Shared-backend assessment: PARTIAL; safe as an owned child, but the current registry/shutdown boundary is MCP-process scoped.

5. LIVE authority service

   - Creation owner: contextor.core.live_state.runtime::connect_or_start, runtime.py:856-1033.
   - Launcher: _spawn_runtime_subprocess, runtime.py:744-809.
   - Registry: not CONTEXTOR_MCP_PROCESS_REGISTRY; ownership is represented by the RuntimeDomain/RuntimeLease/LiveEndpoint durable surfaces.
   - Identity/liveness: ProcessIdentity and endpoint/lease parity include process-start identity.
   - Cleanup: service shutdown releases or fences the lease and removes the exact owned endpoint; owner watchdog closes the service when an explicit owner PID dies.
   - Shared-backend assessment: PARTIAL; the primitives are durable and detached-capable, but their semantics are specifically the LIVE authority domain.

Conclusion:

PROCESS_REGISTRY_SAFE_FOR_SHARED_BACKEND_AS_IS=PARTIAL

The registry itself is identity-aware and robust for owned children. It is not, as-is, a complete session-independent shared-backend ownership model because mcp-server cleanup is tied to the server process/parent and the registry directory is derived from the server working root.

## LIVE_RUNTIME_PRIMITIVES

The following existing primitives were retrieved through Contextor canonical source/lineage and verified against current LIVE revision 1329.

1. RuntimeDomain

   - File: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_domain.py.
   - Owner: RuntimeDomain.create / RuntimeDomain.from_identity.
   - Scope: one production or test runtime domain.
   - Identity: domain ID derived from repository identity, mode, repository root, cache/log/lock/IPC/test roots and resource fingerprints.
   - Persistence: serialized identity fields only; no independent authority file.
   - Locking/liveness/stale takeover/cleanup: none intrinsic.

2. RuntimeLeaseManager

   - File: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py.
   - Lock: _DomainFileLock plus the manager's thread lock; domain lock path is domain.lock_root / authority.<domain_id>.lock, lines 705-706.
   - Durable surfaces: authority_generation.<domain_id>.json, authority_lease.<domain_id>.json, and desktop claim metadata under the domain cache root.
   - Identity: repository/domain, service instance, lease generation, service PID, process-start identity, endpoint fingerprint.
   - Acquisition: RuntimeLeaseManager.acquire, lines 1363-1441, rejects live ownership, rejects ambiguous liveness, and takes over only after confirmed stale evidence.
   - Reconciliation: reconcile_endpoint_binding, lines 1489-1515, requires exact current ownership and endpoint parity.
   - Release: release, lines 1574-1596, writes the released/fenced durable record, removes desktop claim/live lease, and emits release evidence.

3. LiveEndpoint

   - File: C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py, LiveEndpoint lines 26-88.
   - Durable endpoint: repo_cache_dir(root)/live_endpoint.json, runtime.py:211-212.
   - Identity: host/port/authkey, service PID, owner PID/token, repository/domain, service instance, lease generation, process-start identity, schema version; endpoint fingerprint is derived from identity payload.
   - Write/remove: atomic temporary-file replace and exact-ownership removal.
   - Liveness: AuthorityLivenessVerifier checks endpoint, lease, process identity and authenticated authority status.

4. connect_or_start

   - File: C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:856-1033.
   - Startup lock: endpoint sibling live_service_start.lock, claimed by O_CREAT|O_EXCL.
   - Admission: strict repository/domain endpoint validation, verified existing client first, then RuntimeLease admission.
   - Launcher: _spawn_runtime_subprocess requests Windows CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW; it falls back once if breakaway is rejected.
   - Timeout cleanup: terminates the spawned PID tree and removes the startup lock.

5. Runtime endpoint reconciliation and service shutdown

   - File: runtime.py:1395-1566 and runtime_lease.py:1489-1515.
   - Ready is emitted only after endpoint, lease, generation and authority identity parity is verified.
   - Shutdown closes the service, drains the mutation worker, reconciles endpoint binding, releases or fences the lease, emits shutdown, and removes the endpoint only when exact ownership is resolved.
   - An explicit owner PID receives a watchdog; on owner death the service closes. Without an owner PID, this particular watchdog path is absent.

Reuse classification:

- EXISTING_PRIMITIVES_CAN_BE_REUSED_OUTSIDE_LIVE_DOMAIN=PARTIAL.
- Generic-looking structural pieces already present: path identity, ProcessIdentity, liveness/status tuple, cross-process file lock, atomic JSON replacement, endpoint fingerprinting, and O_EXCL startup admission.
- LIVE-specific semantics that are not generic by proof: authority-generation/lease schema, authenticated LiveState IPC endpoint, Desktop claim/watchdog, authority event stream, and LIVE endpoint/lease reconciliation.
- This is an inventory classification only; no design or extraction decision was made.

## STORAGE_SURFACES

User/global surfaces:

- app_cache_dir() in C:\Temp\Contextor_Repo\contextor\core\paths.py:152-167: Windows %LOCALAPPDATA%\Contextor/cache unless CONTEXTOR_CACHE_DIR is set.
- state_dir() in paths.py:310-324: Windows %APPDATA%\Contextor unless CONTEXTOR_STATE_DIR is set.
- runtime_logs_dir() in paths.py:37-40: state directory logs.
- repository_registry_root() in C:\Temp\Contextor_Repo\contextor\core\repository_storage.py:9-16: CONTEXTOR_REGISTRY_DIR or installation-root .contextor/repositories.

Repository-scoped surfaces:

- repo_cache_dir(root) in paths.py:185-198: registered repository cache under app cache repositories/<repo_id>, with a legacy repo-key fallback.
- PersistentIdentityRegistry in repository_storage.py:14-42: repository metadata, lock, transaction file, module/artifact slots, recovery/output references, and registry JSON surfaces.
- Repository-local analysis jobs: C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:70-71 uses <repo>/.contextor/analysis_jobs.
- Full-analysis lock and lease metadata: C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis.py:302-381,410-581; the lock is under the repository cache runtime area and the lease metadata is adjacent to the lock.

Current MCP process registry:

- registry_dir(Path.cwd().resolve()) in mcp_server.py selects <current server working root>/.contextor/mcp_processes.
- Under the current Codex config this resolves to C:\Temp\Contextor_Repo\.contextor\mcp_processes.
- This is a current process-registry fact, not a claim that future HTTP deployment must use the same location.

Current LIVE surfaces:

- Endpoint: repo_cache_dir(root)/live_endpoint.json.
- Startup lock: endpoint sibling live_service_start.lock.
- Authority lock: domain.lock_root/authority.<domain_id>.lock.
- Authority generation/live lease/desktop claim: domain cache root, using domain-qualified names.
- Full-analysis lock: repository cache runtime area, independent of the LIVE authority lock.

Storage conclusion:

GLOBAL_USER_SCOPED_STORAGE_AVAILABLE=YES

REPO_SCOPED_STORAGE_AVAILABLE=YES

Both scopes already exist. Their current ownership semantics are mixed: repository identity/cache/analysis surfaces are persistent, while the MCP process registry is rooted at the MCP process working directory and LIVE authority files are domain-specific.

## MULTIREPO_GLOBAL_STATE

Canonical owner and lineage:

- contextor_fact_lineage(family="artifact_consumption") identified RepositoryAnalysisState.artifact_consumption as the canonical owner. Producers/materializers include contextor.core.analysis.state_manager::build_canonical_artifact_consumption, ContextorFacade.analyze_project, incremental _rebuild_consumer_slice, and IncrementalAnalysisEngine._apply_delta_and_commit.
- contextor_fact_lineage(family="symbol_calls") identified RepositoryAnalysisState.module_usages[*].symbol_calls as the canonical owner. Producers include reference.engine::extract_module_usage_facts, reference.module_usage_reuse::build_module_usage_baseline_with_reuse, incremental preparation::prepare_source_update, and incremental materialization::ensure_module_usages; materialization/update is through the facade and incremental commit.
- Current canonical evidence reports 403 canonical modules, 403 symbol-call materializations, and zero missing/stale symbol-call entries at revision 1329.

Engine cache:

- File: C:\Temp\Contextor_Repo\contextor\mcp\runtime.py.
- Lines 11-19 hold process-local dictionaries for engines, revisions, provenance, sessions and journal revisions, plus a guard and per-root lock map.
- _engine_cache_transaction, runtime.py:113-123, resolves the repository root and creates an independent threading.RLock() keyed by the resolved root.
- _cached_engine, _get_or_init_engine_snapshot, and get_or_init_engine, runtime.py:126-190, operate inside the repository-keyed transaction. Hydration connects to the repository's LIVE authority and populates that repository's engine snapshot.
- No process-global current_repo state was found in the current MCP runtime path.

Analysis job state:

- File: C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py.
- Process-global _analysis_lock, _analysis_job_lock, _analysis_tasks, _analysis_jobs_by_repo, and _analysis_shutdown_event exist at lines 18-22.
- _start_analysis_job, lines 422-458, keys duplicate-job suppression by the resolved repository path and stores the worker thread/job handle in process-local maps.
- _run_analysis_worker, lines 224-300, uses the process-global analysis lock and temporarily sets CONTEXTOR_CACHE_DIR and CONTEXTOR_MCP_PROCESS_REGISTRY for the worker, restoring both in finally.
- request_analysis_shutdown, lines 37-61, sets one process-global shutdown event and joins all current analysis tasks in the process.

Other process-global state:

- _active_executors in process_pool_lifecycle.py is process-local and reset when a forked PID is detected. It tracks active executors, not all repositories globally.
- The MCP server shutdown callback terminates process-wide analysis tasks/pools and owned/orphan registry records.

Assessment:

ENGINE_CACHE_PER_REPO_LOCK=YES

DIFFERENT_REPO_ENGINE_LOCKS_INDEPENDENT=YES

PROCESS_GLOBAL_CURRENT_REPO=NO

MULTIREPO_ENGINE_CACHE_READY=YES

MULTIREPO_ANALYSIS_READY_AS_IS=PARTIAL

The engine cache is already repository-keyed with independent locks. Analysis admission is repository-keyed for duplicate suppression, but execution remains serialized by a process-global analysis lock and process-global environment/shutdown controls. This is a current-state classification, not a proposal to change it.

Global-state risk classification:

- _analysis_lock: correctness guard for current environment mutation and analysis exclusivity; throughput limitation across repositories; not safe to interpret as client/session ownership.
- _analysis_shutdown_event: process-wide cancellation boundary; safe when called only during process shutdown; unsafe as a per-client disconnect primitive.
- _analysis_tasks and _analysis_jobs_by_repo: process-local supervision maps; durable job files provide repository-local status, but the maps do not form a cross-process coordinator.
- _active_executors: process-local lifecycle registry; suitable for current process shutdown, not a shared multi-process authority registry.
- CONTEXTOR_CACHE_DIR and CONTEXTOR_MCP_PROCESS_REGISTRY: process environment surfaces temporarily changed under the global analysis lock; they are not per-thread state.
- mcp_server._shutdown_mcp_owned_processes: process-wide cleanup boundary, not repository/client/session scoped.

## STARTUP_SUPERVISION

Existing mechanisms:

1. Canonical LIVE authority launcher

   - runtime.py::_spawn_runtime_subprocess, lines 744-809, is a real detached-capable longer-lived subprocess launcher.
   - runtime.py::connect_or_start, lines 856-1033, performs endpoint discovery, strict domain validation, O_EXCL startup admission, RuntimeLease acquisition, spawn, readiness polling, timeout tree termination, and startup-lock cleanup.
   - Windows breakaway flags are requested so a launcher Job Object does not unintentionally own the LIVE service; an explicit owner PID may still install a runtime watchdog.
   - This is a LIVE authority launcher, not a persistent shared MCP backend launcher.

2. LIVE service entry

   - runtime.py::main, lines 1546-1566, parses repository/owner identity and calls run_service.
   - run_service owns the endpoint publication, authority readiness, watchdog, service close, lease release/fence, and exact endpoint removal.

3. Current MCP server entry

   - mcp_main.py::main and mcp_server.py::main are foreground entrypoints.
   - The current Codex config launches the MCP server through a local Python command.
   - HTTP mode is available in the same foreground process but is not detached and has no durable shared-backend endpoint record.

4. Desktop/UI entry

   - run_contextor.bat launches main.py --gui in the foreground.
   - Desktop singleton ownership is implemented by contextor.ui.single_instance::DesktopSingleInstance; the GUI uses connect_or_start to obtain the LIVE authority.
   - DesktopLiveWatcher uses daemon threads and LIVE reconnect/start logic; the watcher thread itself is not a detached backend process.

Required inventory:

EXISTING_DETACHED_BACKEND_LAUNCHER_EXISTS=YES

Qualifier: the existing detached-capable launcher is the LIVE authority launcher (runtime.py::_spawn_runtime_subprocess), not an already-detached persistent shared MCP HTTP backend launcher.

Per-mechanism dimensions:

- Detached: LIVE authority YES; MCP stdio/HTTP NO; GUI NO.
- Survives caller exit: LIVE service is conditional on whether owner_pid watchdog ownership was supplied; MCP and GUI are host/foreground owned; external Codex disconnect behavior is not locally proved.
- Singleton/election: LIVE uses O_EXCL startup lock plus RuntimeLease generation/lease; MCP has no equivalent durable shared-backend election; GUI has its own DesktopSingleInstance.
- Endpoint discovery: LIVE uses live_endpoint.json plus verified authority status; MCP HTTP has only the bound transport endpoint and no Contextor durable MCP endpoint record.
- Liveness: LIVE has process-start identity, endpoint, lease, and authenticated status checks; MCP process registry has process identity for registered children; current MCP HTTP transport has no Contextor-specific durable authority liveness layer.
- Shutdown: LIVE closes/releases/fences/removes exact endpoint; MCP runs mcp-owned cleanup on server process exit; GUI closes its own UI/lifecycle path.

## SHUTDOWN_SEMANTICS

MCP shutdown:

- The only production call path to request_analysis_shutdown is mcp_server::_shutdown_mcp_owned_processes, lines 496-518.
- It sets the process-global analysis shutdown event, joins all current process analysis threads, terminates all active process pools, repeats the analysis shutdown request, and cleans owned/orphan registry entries.
- mcp_server::_shutdown_cleanup is invoked from main() finally and atexit; it is not a request-scoped or repository-client-scoped disconnect callback.

Process-pool shutdown:

- terminate_active_process_pools, process_pool_lifecycle.py:209-223, snapshots all process-local active executors and terminates their children.
- terminate_process_pool, lines 148-206, performs nonblocking shutdown, terminates live children, waits, kills survivors when available, and waits again.
- The GUI also calls process-pool termination on its own close path; this is a separate process-wide pool lifecycle boundary, not an HTTP session boundary.

LIVE authority shutdown:

- run_service, runtime.py:1395-1566, starts the owner watchdog when an owner PID is provided.
- The watchdog closes the service on owner death.
- The finalization path closes/drains the service, reconciles endpoint binding, releases the lease or fences on release failure, emits shutdown status, and removes the endpoint only when ownership is resolved.

Client disconnect:

- No explicit Contextor MCP client-disconnect handler was found in the current source.
- The current FastMCP session manager can own HTTP sessions, but Contextor does not route a session-close event to _shutdown_mcp_owned_processes.
- The current process-exit cleanup is therefore distinct from a proven client-disconnect callback.
- Codex host behavior when a stdio client disconnects is outside the repository and was not inferred.

CLIENT_DISCONNECT_SIGNAL_VISIBLE_TO_CONTEXTOR=NO

CLIENT_DISCONNECT_PROCESS_SHUTDOWN_RISK=UNKNOWN

Reason for UNKNOWN: Contextor has no direct disconnect-to-shutdown path, but the final process lifetime of the current host-launched stdio root is external host behavior. The repository proves cleanup on process exit, not Codex's policy for terminating that process after a disconnect.

## IMPLEMENTATION_SURFACE_INVENTORY

No implementation was performed. The inventory below records current ownership and exact surfaces relevant to the requested discovery.

MCP and transport:

- C:\Temp\Contextor_Repo\contextor\mcp_main.py:1-12 — Python entrypoint and multiprocessing bootstrap.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:451-453 — FastMCP object creation.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:496-518 — mcp-owned shutdown.
- C:\Temp\Contextor_Repo\contextor\mcp_server.py:812-890 — stdio/HTTP transport selection and process lifetime.
- C:\Temp\Contextor_Repo\contextor\mcp_process_registry.py:16-245 — process registry, identity, records and termination.

Repository identity/storage:

- C:\Temp\Contextor_Repo\contextor\core\paths.py:37-40,152-167,185-204,310-324 — app cache, repository cache, logs and state roots.
- C:\Temp\Contextor_Repo\contextor\core\repository_storage.py:9-42 — repository registry and persistent identity files.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis.py:302-381,410-581 — full-analysis lock and lease state.
- C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:64-71 — MCP cache root and repo-local job directory.

Multirepo runtime:

- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py:11-19 — process-local engine/revision/session maps.
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py:113-190 — repository-keyed engine lock, cache access and LIVE hydration.
- C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:18-22,37-71,224-300,422-458 — analysis-global state, environment scope and repo-keyed job admission.
- C:\Temp\Contextor_Repo\contextor\core\analysis\process_pool_lifecycle.py:14-45,48-116,148-223 — process-local executor registry, worker registration and termination.

LIVE authority:

- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_domain.py — RuntimeDomain identity and scope.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py:693-706,856-891,1279-1361,1363-1445,1489-1515,1574-1596 — durable lease/generation paths, locking, stale takeover, reconciliation and release.
- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:26-88,211-321,384-512,661-738 — endpoint identity, endpoint path, liveness verifier and verified connection.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:744-809,856-1033,1173-1566 — detached-capable startup, existing endpoint connection, service lifecycle, watchdog and shutdown.

Canonical data ownership:

- RepositoryAnalysisState.artifact_consumption and RepositoryAnalysisState.module_usages[*].symbol_calls are the canonical state owners retrieved through Contextor fact lineage.
- ContextorFacade.analyze_project and IncrementalAnalysisEngine._apply_delta_and_commit are the canonical materialization/update boundaries retrieved through Contextor lineage.
- No alternate source/AST/engine/disk fallback was introduced or selected by this discovery.

## UNKNOWN

- Exact Codex host action on stdio MCP process when a user/session disconnects: UNKNOWN.
- Whether an external deployment supervisor already wraps HTTP mode outside this repository: UNKNOWN.
- Whether a future deployment supplies HTTP authentication middleware externally: UNKNOWN; current Contextor code has no auth configured.
- Whether the current FastMCP session manager emits a callback that Contextor could consume without additional integration: UNKNOWN; no such Contextor consumer is present.
- Whether process-global analysis serialization is an intentional performance policy or an unexamined shared-backend constraint: UNKNOWN as intent; its current code effect is directly proven.
- Current local HTTP header field schema beyond the fields listed in CODEX_HTTP_CONFIG_FIELDS_LOCAL_CONFIRMED: not locally confirmed in the current Config/CLI inspection.

No unknown was converted into a design decision. No alternative architecture was evaluated.

## FILES_CHANGED

FILES_CHANGED=walkthrough.md

The only requested write was the report itself. No production source, test, or documentation file was changed. The report file is excluded from its own diff requirement.

ACTUAL_DIFF=DIFFS=NONE

## REQUIRED_LITERALS

DIRECT_HTTP_SERVER_ALREADY_EXISTS=YES
DIRECT_CODEX_HTTP_CLIENT_SUPPORTED=YES
CURRENT_HTTP_AUTHENTICATED=NO
CURRENT_MCP_ROOT_LIFETIME_HOST_OWNED=YES
PERSISTENT_BACKEND_PRIMITIVES_ALREADY_EXIST=PARTIAL
LIVE_LEASE_PRIMITIVES_REUSABLE_IN_PART=YES
PROCESS_REGISTRY_SAFE_FOR_SHARED_BACKEND_AS_IS=PARTIAL
MULTIREPO_ENGINE_CACHE_READY=YES
MULTIREPO_ANALYSIS_READY_AS_IS=PARTIAL
CLIENT_DISCONNECT_PROCESS_SHUTDOWN_RISK=UNKNOWN
EXISTING_DETACHED_BACKEND_LAUNCHER_EXISTS=YES
SOURCE_DRIFT_FROM_K7_BASELINE=NO

DESIGN_DECISIONS=NONE
IMPLEMENTATION_PERFORMED=NO
TESTS_RUN=NO
PROCESS_EXPERIMENTS_RUN=NO
CONFIG_CHANGED=NO
PROCESSES_TERMINATED=NO
