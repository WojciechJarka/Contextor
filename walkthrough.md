# Contextor LIVE flapping diagnosis — discovery only

## CURRENT_LIVE_STATE

The last reachable canonical state was revision 603: continuous from cursor 600, `resync_required=false`, watcher events 601–603, and fresh syntax/collision/cycle facts. The post-603 calls returned `transient_connection_failure`. This status is deliberately narrower than a state-corruption result: it means the endpoint PID still existed while ownership validation could not complete.

## LOG_LOCATIONS

* `C:\\Temp\\Contextor_Repo\\logs\\contextor_runtime_*.jsonl` — Desktop/LIVE trace sink. Latest file is 2026-09-07, so it contains no 2026-09-10 revisions 586/592/600/603.
* `C:\\Users\\DafoO\\AppData\\Local\\Contextor\\cache\\repositories\\ctx_8efc50d8\\live_endpoint.json` — current TCP endpoint metadata.
* Same directory: `authority_lease.*` and `authority_generation.*` — durable owner/lease state; other hashed JSON files are persisted analysis state.
* `C:\\Temp\\Contextor_Repo\\.contextor\\mcp_processes\\*.json` — MCP process registry; `analysis_jobs\\*.json` and repository registries are MCP persistence, not a runtime error log.
* MCP runtime stdout/stderr are not retained: `runtime._spawn_runtime_subprocess` uses `DEVNULL` for both. No distinct transport/client error sink was found.

## CODE_PATH_FROM_GET_LIVE_EVENTS_TO_FAILURE

`contextor.mcp.tools.get_live_events.get_live_events` calls `runtime.connect_existing_with_status`; a missing client plus `transient_connection_failure` becomes the exact public JSON and wording. `connect_existing_with_status` reads `live_endpoint.json`, validates domain/PID/lease identity, runs `_verified_existing_client` three times with 0.05 s delay, and returns transient only when the endpoint has not changed and its PID remains alive. `_verified_existing_client` rejects an authority-status `OSError`, `EOFError`, `ConnectionError`, `TimeoutError`, or `RuntimeError`, lease/generation mismatch, or failed process identity. IPC is authenticated `multiprocessing.connection` over `Listener((127.0.0.1, 0), family="AF_INET")`.

## INCIDENT_TIMELINE

* Revisions 586, 592, 600 and post-603: no timestamped log record exists in the available sink; each is `UNKNOWN` beyond the public transient classification.
* 2026-09-06 16:21:18–16:24:15 UTC is an independently timestamped matching incident: repeated watcher “connection lost; recovering”, recovery rejected as “Canonical LIVE service is busy”, then `[WinError 10061] No connection could be made`. Attempts recur roughly every 4–7 seconds; each recovery attempt lasts roughly 2.0–3.7 seconds.
* Revision 603 later proved recovery without source repair, but the journal does not retain a cause event for the earlier failures.

## PROCESS_PID_EVIDENCE

Current MCP processes are alive: `codex.exe` PID 15976 started 2026-09-10 22:03:28 local, parent of MCP launcher PID 5680 (22:08:02), parent of served MCP PID 15044 (22:08:02). Registry has historical server PIDs 1180, 12408, 15044, 8444; only 15044 was observed alive in the focused current query. No current LIVE-owner PID/end-point sample was captured during a failure, so its death/restart cannot be established.

## TRANSPORT_EVIDENCE

CONFIRMED for the 2026-09-06 incident: `WinError 10061` is TCP connection refusal, not a Python analysis failure. Its client had a durable/claimed service it regarded as busy, yet no listener accepted the connection. This fits an alive stale owner/lease record, a service that stopped listening, or an endpoint race. It does not prove which one.

## TIMEOUT_RETRY_EVIDENCE

`connect_existing_with_status`: three attempts, 0.05 s delay (about 0.10 s retry window). `DEFAULT_CONNECT_TIMEOUT=10.0`; cold start is 60.0; watcher recovery explicitly calls `connect_or_start(... timeout=10.0)`. The 2026-09-06 2–4 s recovery duration is not the 0.10 s MCP reconnect window and does not demonstrate timeout starvation.

## LOCK_LEASE_EVIDENCE

The lease stores service PID, process-start identity, endpoint fingerprint, generation, and heartbeat; each refresh acquires the domain file lock. `AuthorityLivenessVerifier` treats a failed authority-status call with an alive endpoint process as UNKNOWN rather than stale. Takeover is fail-closed for UNKNOWN, hence the observed “service is busy” while `WinError 10061` repeats. This is CONFIRMED behavior, but no current incident lease-content snapshot is available to prove contention or a stale-record transition.

## RESOURCE_CORRELATION

No timestamped log evidence connects the named 2026-09-10 failures to pytest, indexing, persistence, a lock hold, CPU pressure, or file-change burst. The sole detailed incident is unrelated in time. Correlation is UNPROVEN.

## AUTOMATIC_RECOVERY_PATH

Desktop watcher polls every 0.75 s. A ping transport error invokes `_recover_client`, which calls `connect_or_start` (desktop timeout 10 s); recovery can reconnect to a verified existing endpoint or start a new owner only when lease liveness permits. Thus later reachability can be automatic reconnect or a later owner/endpoint replacement; the available evidence cannot distinguish them.

## ROOT_CAUSE_RANKING

1. LIKELY — transport/listener unavailable while durable ownership still reports live/unknown. Evidence: repeated `WinError 10061` plus “service busy” and the fail-closed liveness design.
2. POSSIBLE — owner process alive but IPC listener stopped/unresponsive. This exactly produces the public transient status when PID identity remains alive.
3. POSSIBLE — stale endpoint/lease or endpoint replacement race. Strict endpoint equality and identity checks intentionally surface transient/identity failures during such a transition.
4. UNPROVEN — owner process died/respawned. No process sample exists for revisions 586/592/600/post-603.
5. NOT EVIDENCED — LIVE canonical-state corruption, Stage 1E.1 code, pytest/indexing burst, lock contention, or timeout starvation.

## LOGGING_GAPS

Add design-only structured events at: `runtime._verified_existing_client` for each rejection reason and exception type/WinError; `connect_existing_with_status` for expected/current endpoint fingerprint, PID liveness, attempt number and elapsed time; `AuthorityLivenessVerifier.verify` for process/endpoint/status predicates; watcher `_recover_client` for selected recovery branch and owner/generation; IPC accept/request failure for endpoint and request type. Include service PID/start identity, lease generation, endpoint fingerprint, listener port, exception class/errno, duration, and whether endpoint changed. Persist/rotate these in the active 2026-09-10 runtime sink rather than DEVNULL.

## MINIMAL_FIX_DIRECTION

Design only: retain fail-closed lease safety, but make reconnect diagnosis observable and distinguish “PID alive, listener refused” from status timeout/identity mismatch/lease contention. If evidence confirms a stale alive lease with a dead listener, add a fenced recovery path only after an independent listener/identity proof; do not weaken UNKNOWN-owner protection.

IS_LIVE_CANONICAL_STATE_CORRUPTED=NO evidence of corruption; historical-state continuity/freshness was healthy. Absolute proof is unavailable while owner is unreachable.

IS_STAGE_1E1_CODE_IMPLICATED=NO evidence. The same signature predates Stage 1E.1 and the direct-subscript change is outside runtime/IPC/lease paths.

FILES_CHANGED=NONE

DIFFS=NONE
