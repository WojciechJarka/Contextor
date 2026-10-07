# CPA_BACKEND_OWNER_O1_HOST_CLAIM_PRIMITIVES

STATUS=BLOCKED_SCOPE_GATE_ADDITIONAL_PRODUCTION_FILE_REQUIRED
HEAD=8d2dc6a65602c3e07dec3c949952bb57ba36c80d
CONTEXTOR_CANONICAL_REVISION=1606
CONTEXTOR_CANONICAL_STATE=fresh
CONTEXTOR_WORKSPACE_SYNC=verified

## SCOPE AND ACTIONS

- Contextor-first symbol, module-context, lineage, and blast-radius discovery completed.
- No source or test file was edited.
- No tests were run.
- The requested owner claim cannot yet be implemented safely within only the two preferred production files. The blocker is the existing process identity probe's inability to distinguish confirmed dead from unknown liveness. The specification explicitly requires this distinction and says to stop before changing an additional production file.
- Only this report, walkthrough.md, was overwritten.

## CONTEXTOR EVIDENCE

### Existing backend state owner

Canonical source context at revision 1606, fresh/verified:
- contextor/mcp_backend_state.py is the state owner; get_file_edit_context reports direct consumers including contextor.mcp_backend_control, contextor.mcp_backend_secret, contextor.mcp_server, tests.test_mcp_backend_control and tests.test_mcp_backend_state.
- PersistentBackendRecord is frozen/slotted. Its existing fields are instance_id, server_role, transport, host, port, pid, executable, creation_time, process_registry and started_at. Its from_dict requires the exact _RECORD_FIELDS set. It raises BackendRecordError for malformed values.
- backend_state_dir() returns state_dir() / "mcp_backend"; backend_record_path() returns backend.json.
- _write_record uses a uniquely named temp file, JSON serialization, flush, fsync and os.replace.
- read_backend_record treats a missing file as no record and wraps malformed/unreadable content as BackendRecordError.
- The existing _BackendLifetimeLock is for the backend lifetime and is not the requested host owner claim.

### Existing control plane

Canonical source context at revision 1606, fresh/verified:
- contextor/mcp_backend_control.py is the lifecycle/control owner; get_file_edit_context reports direct consumers from GUI, CLI, autostart and targeted tests.
- backend_control_lock_path() resolves to backend_state_dir() / "control.lock".
- _BackendControlLock is the existing cross-process control lock and is used by the public lifecycle operations.
- get_backend_status() returns state="running", ready=True, record=record only after the record process matches, a token exists, and authenticated MCP readiness succeeds.
- BackendControlError is the existing control exception; BackendRecordError derives from BackendStateError. No generic RuntimeError is needed to express the new API failures.
- get_backend_status's confirmed direct consumers include contextor.mcp_backend_cli, contextor.ui.gui and tests.test_mcp_backend_control.

### Process identity source: blocking limitation

Contextor fetched these exact implementations from contextor/mcp_process_registry.py at revision 1606, workspace_sync=verified:
- _windows_process_identity(pid), lines 20-76
- process_identity(pid), lines 79-91
- record_matches_process(record), lines 150-166

The Windows implementation returns (None, None, False) when OpenProcess fails, and also returns (None, None, False) when GetExitCodeProcess fails. Those outcomes do not establish whether the PID is dead or whether its identity could not be queried. It can also return alive=True with image=None and creation_time=None when the corresponding image/time queries fail.

record_matches_process() collapses its result to bool:
- alive=False -> False;
- if both executable names exist, it compares filename casefold values;
- if both creation times exist, it requires exact equality;
- otherwise it returns True.

That helper is adequate for the existing boolean “record matches a currently verifiable process” check, but does not expose the three states needed by owner takeover:
1. exact live match;
2. confirmed dead or stale identity;
3. unknown because process identity/liveness could not be established.

Treating False as dead would allow takeover when OpenProcess/GetExitCodeProcess merely failed. Treating every False as unknown would prevent the required confirmed-dead takeover. PID alone, heartbeat, and the current bool match result cannot resolve that ambiguity.

Contextor blast radius for process_identity:
- direct consumers: contextor.core.analysis.full_analysis_coordinator, contextor.core.live_state.runtime, contextor.core.live_state.runtime_lease, contextor.mcp_backend_control, contextor.mcp_backend_state, contextor.mcp_server;
- 129 downstream modules in canonical reachability.

Contextor blast radius for record_matches_process:
- direct consumers: contextor.mcp_backend_control, contextor.mcp_server, tests.test_mcp_regressions.

An additive tri-state result from the existing backend process identity source is necessary so the new owner control path can fail closed on unknown while allowing takeover only on confirmed dead/stale. That requires changing contextor/mcp_process_registry.py, which is outside the preferred production allowlist. This is the exact scope gate specified by the request; no such change has been made.

## OWNER_CLAIM_SCHEMA

NOT_IMPLEMENTED.

Required schema v1 remains as specified:
- frozen/slotted BackendHostOwnerClaim
- exact fields: schema_version, backend_instance_id, host_owner_identity, host_kind, host_pid, host_executable, host_creation_time, owner_token, claimed_at
- separate durable path: backend_owner_claim_path() => state_dir/mcp_backend/owner.json
- exact-field fail-closed parsing and atomic temp + flush + fsync + os.replace persistence
- exact removal compares the entire expected claim

## CLAIM_SEMANTICS

NOT_IMPLEMENTED.

The two preferred files have the canonical state/control owners needed for the rest of the contract:
- state schema and persistence belong in contextor/mcp_backend_state.py;
- claim/release transactions belong under _BackendControlLock in contextor/mcp_backend_control.py;
- claim creation must bind to the ready backend's exact PersistentBackendRecord.instance_id;
- release must remove only the exact expected claim;
- no bearer auth, client ID, lifecycle behavior, autostart, Desktop, or MCP request permissions are to change.

Implementation is stopped before edits because the specified unknown-liveness behavior cannot be implemented correctly with the current process identity result.

## TAKEOVER_SEMANTICS

NOT_IMPLEMENTED.

Required behavior remains:
- no existing claim: write candidate;
- exact same claim: idempotent success;
- claim tied to another backend instance: replace under control lock;
- same backend instance with exact live owner: reject as already owned;
- same backend instance with confirmed dead/stale owner: replace;
- unknown process identity/liveness: fail closed without replacement.

The current probe returns no evidence allowing the last three cases to be distinguished safely. No owner claim or backend runtime behavior was changed.

## TARGETED_TESTS

NOT_RUN because implementation stopped at the required scope gate.

After the missing process-identity distinction is resolved, the user-specified focused validation targets remain:
- new owner cases in tests/test_mcp_backend_state.py and tests/test_mcp_backend_control.py;
- directly related named backend-control regressions;
- no full repository pytest suite.

## IMPLEMENTATION_RESULT

STOPPED_BEFORE_EDIT.

Additional production file required: contextor/mcp_process_registry.py, to expose enough information from the existing PID/create-time/executable probe to distinguish confirmed dead/stale from unknown without inferring from PID alone. The change is needed to implement both safe unknown-liveness rejection and confirmed-dead takeover. The existing helper has six direct production consumers and 129 canonical downstream modules, so broadening its established boolean contract in place would have unnecessary blast radius; the minimal additive route must be established before implementation continues.

No production, test, documentation, or configuration file was changed. The walkthrough report is the only task artifact written.

FILES_CHANGED=NONE
FULL_DIFFS=NONE
DIFFS=NONE
