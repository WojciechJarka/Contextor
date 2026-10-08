# L37_L38_A3C_COMPLETE_RECOVERY_AND_AUTHORITY_GATE

## CURRENT_HEAD

PRE_EDIT_HEAD=6bfdf977f25f9cf124ad73dd7815e9511316c05c
CURRENT_HEAD=6bfdf977f25f9cf124ad73dd7815e9511316c05c
HEAD_ADVANCED=NO
Working-tree source/test changes are reported against PRE_EDIT_HEAD. The report itself is excluded from FILES_CHANGED and the source diff.

## PRE_EDIT_CONTEXTOR_EVIDENCE

- DIRECT_EVIDENCE: Before editing, Contextor MCP was used for the requested watcher, GUI, IPC and runtime symbols, caller/callee neighborhoods and lineage. The pre-edit LIVE projection was canonical revision 40 with workspace_sync=verified.
- CODE_PATH_PROVED: The pre-edit watcher path reconciled inflight jobs, then drained pending filesystem paths before its startup-resync decision; the submit/update path was inside DesktopLiveWatcher.poll_once.
- CODE_PATH_PROVED: GUI recovery incidents were in-memory and prompt handling could clear prompt-pending state on dialog exceptions; startup on_resync launched automatic FULL; ordinary analyze success started a watcher without explicit durable/LIVE certification.
- DIRECT_EVIDENCE: After editing, Contextor get_live_events and symbol/source retrieval reported canonical revision 70, workspace_sync=verified, all listed canonical families fresh, no diagnostics requiring attention, and resync_required=false for the cursor beginning at revision 69. Retrieved complete implementations included CanonicalLiveServer._execute_recovery_verification, _finish_recovery_verification, DesktopLiveWatcher.poll_once, DesktopLiveWatcher._startup_reconciliation_paths, ContextorGUI.analyze, and both chunks of ContextorGUI._start_live_watcher_blocking.
- DIRECT_EVIDENCE: Desktop watcher events after revision 66 recorded watcher.py at rev 67, test_live_watcher_startup_reconciliation.py at revs 68–69, and test_recovery_authority_gate.py at rev 70. The earlier cursor 40 had a retention gap; the current cursor 69 was continuous. No manual update_file or runtime restart was performed.

## FILES_CHANGED

1. C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
2. C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
3. C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py
4. C:\Temp\Contextor_Repo\contextor\ui\gui.py
5. C:\Temp\Contextor_Repo\tests\test_gui_live_startup.py
6. C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py
7. C:\Temp\Contextor_Repo\tests\test_recovery_authority_gate.py
8. C:\Temp\Contextor_Repo\tests\test_watcher_recovery_admission.py

## RECOVERY_INCIDENT_GENERATIONS

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\ui\gui.py, ContextorGUI._request_full_analysis_recovery (lines 1128–1183), _live_recovery_incident (806–813), and _set_live_recovery_verification_state (815–827):
- Incidents are keyed by canonical resolved repository path.
- Each registration increments that repository's generation and stores reason, required flag and verification state. A valid accepted/rejected publication revision and outcome are preserved.
- Prompt deduplication is repository-scoped and uses _live_recovery_lock.
- Incident state is not removed by prompt decline, acceptance, analysis start, analysis failure, repository deselection or ordinary publish response. The incident is removed only after a matching generation's fenced verification completes successfully.

## WATCHER_ATOMIC_ADMISSION

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\ui\gui.py, ContextorGUI._watcher_recovery_admission (829–841):
- The callback holds _live_recovery_lock while checking the incident and while invoking the synchronous submission callable.
- Active recovery returns RECOVERY_DEFERRED without invoking the submission. The callback does not catch transport errors.
- This serializes incident registration with watcher submission; tests/test_watcher_recovery_admission.py::test_gui_admission_serializes_registration_with_submission uses Events and an observed lock to assert the ordering; ...::test_recovery_admission_does_not_swallow_submission_transport_errors checks exception propagation.

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py, DesktopLiveWatcher._admit_recovery_action (160–163), _enqueue_path (441–451), and _requeue_paths (468–470): existing constructor calls remain valid because admission is optional; path queue deduplication and original update arguments remain unchanged.

## WATCHER_PENDING_AND_INFLIGHT_SAFETY

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py, DesktopLiveWatcher.poll_once (667–943), _poll_inflight_updates (592–665), _drain_pending (453–459):
1. Poll inflight mutation status first.
2. Check recovery before _drain_pending; if active, return reconciled events while preserving pending paths, startup paths, pending intents, ambiguity records and inflight IDs.
3. During active recovery, completed inflight responses are reconciled but do not independently certify the filesystem baseline.
4. Recheck recovery before each path. Baseline acknowledgment operations and submit_update_file run inside admission. If recovery begins mid-poll, later paths are requeued, existing accepted jobs remain tracked, and the current pending intent is retained.
5. Once recovery is explicitly completed, complete_recovery_certificate (168–172) schedules a fresh scan/rebaseline. poll_once recalculates startup reconciliation and candidate decisions using a new LIVE snapshot; it does not reuse the old batch snapshot.

DIRECT_EVIDENCE — tests:
- tests/test_watcher_recovery_admission.py::test_recovery_preserves_pending_paths_intents_ambiguity_and_startup_work (104–134)
- ...::test_inflight_status_reconciles_during_recovery_without_trusting_baseline (137–171)
- ...::test_mid_poll_recovery_defers_remaining_paths_and_keeps_intent (174–209)
- ...::test_recovery_release_rescans_and_revalidates_against_current_live (212–243)

## STARTUP_RESYNC_SINGLE_FULL_OWNER

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\ui\gui.py, ContextorGUI._start_live_watcher_blocking (1626–1946): startup resync callback registers "Startup canonical baseline requires full analysis." and returns False; it does not call run_full_analysis_exclusive. DesktopLiveWatcher.poll_once keeps startup resync uncompleted, requeues paths and returns without marking the baseline trusted. Only the explicit recovery dialog invokes the existing ContextorGUI.analyze FULL owner.

Compatibility detail: when startup has no initial LIVE state/snapshot, _startup_reconciliation_paths returns no startup candidates without claiming a trusted baseline. The watcher waits while ping().available is false and preserves/requeues changed paths. Malformed available state (modules not a dict) or a mismatched/untrusted file-state generation sets _startup_requires_resync. This distinction preserves the existing first-run wait-for-analysis contract.

DIRECT_EVIDENCE — tests/test_gui_live_startup.py::test_startup_resync_queues_one_explicit_full_owner_without_running_full (1165–1225); tests/test_live_watcher_startup_reconciliation.py startup cases include test_untrusted_startup_filestate_uses_single_resync_not_per_file_replay (286), test_failed_startup_resync_does_not_fallback_to_mass_incremental_updates (340), and test_startup_resync_with_analysis_errors_remains_untrusted (519).

## AUTHORITY_VERIFICATION_PROTOCOL

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py, _repository_recovery_verification_guard (1301–1321): obtains the existing full-analysis writer lease with zero wait; the service injects this guard with the committed-snapshot reader and repository identity reader into CanonicalLiveServer.

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:
- CanonicalMutationCoordinator.begin_recovery_verification / end_recovery_verification / recovery_verification_active (217–239) fence new mutations; queue submission rejects while fenced (submit, 155–214).
- _execute_recovery_verification (1525–1654) validates positive incident generation, permanent repo ID and canonical root; enters writer guard; serializes with _mutation_execution_lock and _lock; reads committed snapshot through the injected locked reader; validates snapshot state ID/revision, LIVE state ID/revision, and equality of committed and LIVE revisions. It returns structured error categories and does not persist or mutate canonical state.
- Successful verification returns a certificate with random certificate ID, incident generation, repo ID, canonical root, state ID and revision. The writer lease context and mutation fence remain held after the verification response.
- _execute_publish (1453–1469) checks the fence both before and again inside _mutation_execution_lock. _execute_update_file (1701–1723) does likewise for direct updates. Already accepted queued work is excluded at fence admission by the coordinator's pending-job check.

DIRECT_EVIDENCE — focused tests validate identity/revision/missing/corrupt cases, no persistence, inflight rejection, and live IPC verify/ack round trip. R26 is covered by test_concurrent_publish_cannot_cross_recovery_fence (test file lines 144–215): Events hold the mutation execution lock after publish's first unfenced check, start verification and observe fence admission, then release the lock; publish must fail at the in-lock check and LIVE revision remains unchanged.

## RECOVERY_RELEASE_FENCING

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py, _finish_recovery_verification (1656–1689) releases only the matching pending certificate ID and incident generation. A mismatch leaves the fence active. A valid completion/cancel releases the held writer lease context, clears the pending certificate, then ends the mutation fence.

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\ui\gui.py, ContextorGUI.analyze (1250–1489):
- verifies a completed FULL only when an incident exists;
- checks the certificate's generation, repo ID/root, positive revision and nonempty state ID;
- while holding the GUI incident lock, confirms the same generation is still current, requests server completion, and removes only that incident after the response is status=ok, released=True, and matches certificate ID/generation;
- tells the watcher to rebaseline after verified release;
- otherwise cancels a held certificate best-effort, records failed verification and retains the incident.
Newer generations prevent the older result from clearing recovery.

## GUI_RECOVERY_LIFECYCLE

CODE_PATH_PROVED — C:\Temp\Contextor_Repo\contextor\ui\gui.py:
- _request_full_analysis_recovery (1128–1183) creates repository-scoped generations and queues one prompt.
- _drain_live_recovery_queue (1185–1249) displays dialogs only for the selected repository; an unselected repository retains its incident and can be prompted later. A dialog exception clears only prompt-pending status, re-raises, and leaves the incident. Declining leaves the incident.
- analyze (1250–1489) leaves ordinary analysis behavior intact where no incident exists. Analysis errors or failed certification do not clear recovery. No automatic second FULL is launched.
- _start_live_watcher_blocking (1626–1946) prioritizes resync_required over ordinary status=ok, records accepted/rejected outcome and committed revision, returns before creating a watcher for degraded publication, and suppresses healthy watcher status while an incident is active.

DIRECT_EVIDENCE — GUI focused regressions cover ordinary healthy startup, accepted degraded startup, rejected publication, prompt deduplication, no automatic FULL, switch/decline/dialog exception/analysis failure, and stale-generation rejection.

## GATE_F_COMPATIBILITY

CODE_PATH_PROVED: No facade, durable snapshot schema, persistence ordering, canonical revision policy, or watcher mutation submission arguments were changed. Existing live_publish_status="recovery_required" response semantics remain the accepted-commit/nonhealthy contract. GUI checks resync_required=True before ordinary status=ok and preserves accepted revision/outcome. Ordinary healthy status=ok keeps the previous active-watcher behavior; rejected publication still registers recovery with rejected outcome. No API vocabulary was changed.

DIRECT_EVIDENCE: tests/test_gui_live_startup.py covers healthy startup and both accepted-degraded and rejected startup; selected existing H3A and durable-verified publish regressions passed.

## TARGETED_TEST_RESULTS

All commands used the project venv. No full repository pytest run was performed.

- python -m py_compile on all four changed production files and four changed test files: PASS (exit 0).
- git diff --check on tracked source/test files: PASS (exit 0); a whole-worktree check after report creation flags standard space-prefixed blank context lines inside the verbatim embedded diffs, not trailing whitespace introduced by source/test changes.
- pytest -q tests/test_recovery_authority_gate.py tests/test_watcher_recovery_admission.py tests/test_gui_live_startup.py: PASS, 50 passed, 1 third-party Authlib deprecation warning, 8.46 s.
- pytest -q tests/test_live_state_ipc.py: PASS, 88 passed, 1 third-party Authlib deprecation warning, 56.38 s.
- pytest -q tests/test_live_watcher_startup_reconciliation.py: PASS, 37 passed, 14.03 s.
- pytest -q tests/test_durable_verified_publish.py plus four selected H3A cases (test_h3a_case_t_active_daemon_successful_publish, test_h3a_case_u_active_daemon_publish_raises_failure_semantics, test_h3a_case_v_active_daemon_publish_failure_response_dict, test_full_publish_accepted_recovery_preserves_revision_and_warning): PASS, 19 passed, 36.15 s.
- The first test_live_state_ipc.py run exposed that initial absence of a LIVE snapshot had newly been marked as a recovery-required baseline; the existing first-run waiting test failed. The two flags were removed for the unavailable/missing-initial-state branch, preserving fail-closed handling for malformed available state and mismatched trusted generations. The test then passed and the full IPC module passed.
- The first startup-reconciliation run exposed mock states without the required modules mapping and post-startup tests relying on a preexisting trusted baseline. The real-runtime fixture now supplies modules={}; isolated non-startup behavior tests explicitly establish their post-startup precondition. Assertions were retained. The entire module then passed.
- pytest -q tests/test_recovery_authority_gate.py::test_concurrent_publish_cannot_cross_recovery_fence: PASS, 1 passed; subsequently included in the 50-pass command above.

## LIVE_WATCHER_VERIFICATION

DIRECT_EVIDENCE: Contextor LIVE canonical revision 70, workspace_sync=verified, current IPC symbol and new R26 test both resolved at rev 70. The latest event from revision 69 was desktop-watcher update_file for tests/test_recovery_authority_gate.py at revision 70. The prior event sequence recorded watcher.py at 67 and startup reconciliation test changes at 68 and 69. The rev69→70 cursor was continuous with resync_required=false. No manual update_file was called; no Desktop, LIVE or MCP restart was performed.

LIMITATION: This confirms current workspace synchronization into the existing LIVE analysis authority, not that already running Desktop/MCP processes loaded the modified Python code. The task explicitly defers coordinated runtime integration certification until a manual Desktop/LIVE restart.

## UNRESOLVED_RISKS

- Runtime integration remains unverified until the coordinated manual Desktop/LIVE restart authorized by the task's separate certification boundary; no restart was performed here.
- A recovery certificate intentionally retains the writer lease and server mutation fence until matching completion/cancel. If the Desktop does not complete/cancel it, the server remains fail-closed until server shutdown/cleanup; this is safer than silently resuming mutation but may require recovery interaction.
- The GUI incident registry is in-memory state. This implementation does not add a durable incident journal or claim incident survival across process termination.
- Focused tests do not constitute the explicitly deferred runtime integration certification.

## IMPLEMENTATION_VERDICT

IMPLEMENTED_WITH_FOCUSED_TESTS_PASS
R1–R32 requested behavior has focused source/test coverage; no production change was made outside the four allowed files. Runtime integration certification remains pending the coordinated manual restart described above.
ACTUAL_DIFF=COMPLETE_DIFFS_FOLLOW

## FULL_DIFFS

### contextor/core/live_state/ipc.py
```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index a407b17..60c8ec2 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -14,6 +14,7 @@ import time
 import uuid
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
+from pathlib import Path
 from typing import Any, Callable, Mapping
 
 from contextor.core.live_state.runtime_lease import ProcessIdentity
@@ -140,6 +141,7 @@ class CanonicalMutationCoordinator:
         self._accepting = True
         self._stop = False
         self._queue_order = 0
+        self._recovery_verification_fenced = False
 
     def _ensure_started_locked(self) -> None:
         if self._thread is None:
@@ -163,6 +165,12 @@ class CanonicalMutationCoordinator:
             return {"status": "error", "error": "invalid_idempotency_key"}
 
         with self._condition:
+            if self._recovery_verification_fenced:
+                return {
+                    "status": "error",
+                    "error": "recovery_verification_in_progress",
+                    "accepted": False,
+                }
             existing_job_id = self._idempotency_jobs.get(idempotency_key)
             if existing_job_id is not None:
                 existing_job = self._jobs.get(existing_job_id)
@@ -206,6 +214,30 @@ class CanonicalMutationCoordinator:
                 "state": job.state,
             }
 
+    def begin_recovery_verification(self, timeout: float) -> bool:
+        deadline = time.monotonic() + max(0.0, float(timeout))
+        with self._condition:
+            if self._recovery_verification_fenced:
+                return False
+            self._recovery_verification_fenced = True
+            while any(job.state in {"queued", "running"} for job in self._jobs.values()):
+                remaining = deadline - time.monotonic()
+                if remaining <= 0:
+                    self._recovery_verification_fenced = False
+                    self._condition.notify_all()
+                    return False
+                self._condition.wait(remaining)
+            return True
+
+    def end_recovery_verification(self) -> None:
+        with self._condition:
+            self._recovery_verification_fenced = False
+            self._condition.notify_all()
+
+    def recovery_verification_active(self) -> bool:
+        with self._condition:
+            return self._recovery_verification_fenced
+
     def status(self, job_id: Any) -> dict[str, Any]:
         if not isinstance(job_id, str) or not job_id:
             return {"status": "error", "error": "invalid_mutation_job_id"}
@@ -717,6 +749,8 @@ class CanonicalLiveServer:
         desktop_claim_acquirer: Callable[[str, int, str], Mapping[str, Any]] | None = None,
         desktop_claim_releaser: Callable[[str, int, str], None] | None = None,
         mutation_guard: Callable[[Mapping[str, Any], threading.Event], Any] | None = None,
+        recovery_verification_guard: Callable[[], Any] | None = None,
+        repository_identity_reader: Callable[[], Any] | None = None,
     ):
         if revision is not None and (
             isinstance(revision, bool)
@@ -766,6 +800,10 @@ class CanonicalLiveServer:
         self._lock = threading.RLock()
         self._mutation_execution_lock = threading.Lock()
         self._mutation_guard = mutation_guard
+        self._recovery_verification_guard = recovery_verification_guard
+        self._repository_identity_reader = repository_identity_reader
+        self._recovery_verification_context = None
+        self._pending_recovery_certificate: dict[str, Any] | None = None
         self._mutation_coordinator = CanonicalMutationCoordinator(
             self._execute_queued_update_file,
             self._read_revision,
@@ -1413,7 +1451,19 @@ class CanonicalLiveServer:
             }
 
     def _execute_publish(self, request: dict[str, Any]) -> dict[str, Any]:
+        if self._mutation_coordinator.recovery_verification_active():
+            return {
+                "status": "error",
+                "error": "recovery_verification_in_progress",
+                "resync_required": True,
+            }
         with self._mutation_execution_lock:
+            if self._mutation_coordinator.recovery_verification_active():
+                return {
+                    "status": "error",
+                    "error": "recovery_verification_in_progress",
+                    "resync_required": True,
+                }
             if self._committed_snapshot_reader is not None:
                 return self._execute_committed_publish(request)
             with self._lock:
@@ -1472,18 +1522,204 @@ class CanonicalLiveServer:
                 _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
 
+    def _execute_recovery_verification(
+        self, request: dict[str, Any]
+    ) -> dict[str, Any]:
+        generation = request.get("incident_generation")
+        if (
+            isinstance(generation, bool)
+            or not isinstance(generation, int)
+            or generation < 1
+        ):
+            return {"status": "error", "error": "invalid_recovery_generation"}
+        if (
+            self._recovery_verification_guard is None
+            or self._repository_identity_reader is None
+            or self._committed_snapshot_reader is None
+        ):
+            return {"status": "error", "error": "recovery_verification_unavailable"}
+
+        if not self._mutation_coordinator.begin_recovery_verification(0.0):
+            return {"status": "error", "error": "recovery_mutations_pending"}
+
+        guard_context = None
+        guard_entered = False
+        retain_fence = False
+        try:
+            try:
+                identity = self._repository_identity_reader()
+            except Exception:
+                return {"status": "error", "error": "recovery_identity_unreadable"}
+            if identity is None:
+                return {"status": "error", "error": "recovery_identity_missing"}
+
+            expected_repo_id = self._authority_identity.get("repo_id")
+            expected_root = self._authority_identity.get("root_path")
+            try:
+                identity_root = str(Path(identity.root_path).expanduser().resolve())
+                authority_root = str(Path(expected_root).expanduser().resolve())
+            except (AttributeError, OSError, TypeError, ValueError):
+                return {"status": "error", "error": "recovery_identity_mismatch"}
+            if (
+                not isinstance(expected_repo_id, str)
+                or identity.repo_id != expected_repo_id
+                or identity_root != authority_root
+            ):
+                return {"status": "error", "error": "recovery_identity_mismatch"}
+
+            try:
+                guard_context = self._recovery_verification_guard()
+                guard_context.__enter__()
+                guard_entered = True
+                with self._mutation_execution_lock:
+                    with self._lock:
+                        live_state = self._state
+                        live_revision = self._revision
+                        if live_state is None:
+                            return {"status": "error", "error": "recovery_live_missing"}
+                        try:
+                            with self._committed_snapshot_reader() as loaded:
+                                if loaded is None:
+                                    return {"status": "error", "error": "recovery_snapshot_missing"}
+                                committed_state, metadata = loaded
+                                committed_revision = metadata.revision
+                                committed_state_id = metadata.state_id
+                                metadata_root = str(
+                                    Path(metadata.root_path).expanduser().resolve()
+                                )
+                                if (
+                                    metadata.repo_id != expected_repo_id
+                                    or metadata_root != authority_root
+                                ):
+                                    return {"status": "error", "error": "recovery_snapshot_identity_mismatch"}
+                                if (
+                                    isinstance(committed_revision, bool)
+                                    or not isinstance(committed_revision, int)
+                                    or committed_revision < 1
+                                    or not isinstance(committed_state_id, str)
+                                    or not committed_state_id
+                                    or getattr(committed_state, "state_id", None)
+                                    != committed_state_id
+                                    or _extract_state_revision(committed_state)
+                                    != committed_revision
+                                ):
+                                    return {"status": "error", "error": "recovery_snapshot_invalid"}
+                                if (
+                                    isinstance(live_revision, bool)
+                                    or not isinstance(live_revision, int)
+                                    or live_revision < 1
+                                ):
+                                    return {"status": "error", "error": "recovery_live_revision_invalid"}
+                                if _extract_state_revision(live_state) != live_revision:
+                                    return {"status": "error", "error": "recovery_live_revision_mismatch"}
+                                live_state_id = getattr(live_state, "state_id", None)
+                                if (
+                                    not isinstance(live_state_id, str)
+                                    or not live_state_id
+                                    or committed_state_id != live_state_id
+                                ):
+                                    return {"status": "error", "error": "recovery_live_identity_mismatch"}
+                                if committed_revision != live_revision:
+                                    return {"status": "error", "error": "recovery_live_revision_mismatch"}
+                        except Exception:
+                            return {"status": "error", "error": "recovery_snapshot_unreadable"}
+            except Exception:
+                return {"status": "error", "error": "recovery_writer_admission_failed"}
+
+            certificate = {
+                "certificate_id": uuid.uuid4().hex,
+                "incident_generation": generation,
+                "repo_id": expected_repo_id,
+                "root_path": authority_root,
+                "state_id": committed_state_id,
+                "revision": committed_revision,
+            }
+            self._pending_recovery_certificate = certificate
+            self._recovery_verification_context = guard_context
+            guard_entered = False
+            retain_fence = True
+            return {
+                "status": "ok",
+                "certificate": certificate,
+            }
+        finally:
+            if not retain_fence:
+                guard_released = True
+                if guard_entered and guard_context is not None:
+                    try:
+                        guard_context.__exit__(None, None, None)
+                    except Exception:
+                        guard_released = False
+                if guard_released:
+                    self._mutation_coordinator.end_recovery_verification()
+
+    def _finish_recovery_verification(
+        self, request: dict[str, Any], *, cancelled: bool
+    ) -> dict[str, Any]:
+        certificate_id = request.get("certificate_id")
+        generation = request.get("incident_generation")
+        pending = self._pending_recovery_certificate
+        if (
+            not isinstance(pending, dict)
+            or not isinstance(certificate_id, str)
+            or isinstance(generation, bool)
+            or not isinstance(generation, int)
+            or pending.get("certificate_id") != certificate_id
+            or generation != pending.get("incident_generation")
+        ):
+            return {"status": "error", "error": "recovery_certificate_mismatch"}
+
+        guard_context = self._recovery_verification_context
+        if guard_context is None:
+            return {"status": "error", "error": "recovery_fence_missing"}
+        try:
+            guard_context.__exit__(None, None, None)
+        except Exception:
+            return {"status": "error", "error": "recovery_writer_release_failed"}
+
+        self._recovery_verification_context = None
+        self._pending_recovery_certificate = None
+        self._mutation_coordinator.end_recovery_verification()
+        return {
+            "status": "ok",
+            "released": True,
+            "cancelled": cancelled,
+            "certificate_id": certificate_id,
+            "incident_generation": generation,
+        }
+
     def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
         trace_op = _safe_trace_op(request, "u")
         if trace_op is not None:
             request = {**request, "trace_op": trace_op}
 
         if self._mutation_guard is None:
-            return self._execute_update_file(request)
+            return self._execute_update_file(request, allow_recovery_fence=True)
         with self._mutation_guard(request, self._stop):
-            return self._execute_update_file(request)
+            return self._execute_update_file(request, allow_recovery_fence=True)
 
-    def _execute_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
+    def _execute_update_file(
+        self, request: dict[str, Any], *, allow_recovery_fence: bool = False
+    ) -> dict[str, Any]:
+        if (
+            not allow_recovery_fence
+            and self._mutation_coordinator.recovery_verification_active()
+        ):
+            return {
+                "status": "error",
+                "error": "recovery_verification_in_progress",
+                "accepted": False,
+            }
         with self._mutation_execution_lock:
+            if (
+                not allow_recovery_fence
+                and self._mutation_coordinator.recovery_verification_active()
+            ):
+                return {
+                    "status": "error",
+                    "error": "recovery_verification_in_progress",
+                    "accepted": False,
+                }
             with self._lock:
                 if self._state is None or self._updater is None:
                     return {
@@ -1745,6 +1981,12 @@ class CanonicalLiveServer:
             return self._mutation_coordinator.submit(request)
         if operation == "mutation_status":
             return self._mutation_coordinator.status(request.get("job_id"))
+        if operation == "verify_recovery":
+            return self._execute_recovery_verification(request)
+        if operation == "complete_recovery_verification":
+            return self._finish_recovery_verification(request, cancelled=False)
+        if operation == "cancel_recovery_verification":
+            return self._finish_recovery_verification(request, cancelled=True)
         if operation == "update_file":
             return self._execute_update_file(request)
         if operation == "publish":
@@ -1959,6 +2201,15 @@ class CanonicalLiveServer:
     def close(
         self, *, mutation_join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT
     ) -> bool:
+        pending = self._pending_recovery_certificate
+        if isinstance(pending, dict):
+            self._finish_recovery_verification(
+                {
+                    "certificate_id": pending.get("certificate_id"),
+                    "incident_generation": pending.get("incident_generation"),
+                },
+                cancelled=True,
+            )
         self._stop.set()
         try:
             self._listener.close()
@@ -2123,6 +2374,43 @@ class LiveStateClient:
     def mutation_status(self, job_id: str) -> dict[str, Any]:
         return self.request("mutation_status", job_id=job_id)
 
+    def verify_recovery(
+        self, incident_generation: int, *, timeout: float = 30.0
+    ) -> dict[str, Any]:
+        return self.request(
+            "verify_recovery",
+            timeout=timeout,
+            incident_generation=incident_generation,
+        )
+
+    def complete_recovery_verification(
+        self,
+        certificate_id: str,
+        incident_generation: int,
+        *,
+        timeout: float = 30.0,
+    ) -> dict[str, Any]:
+        return self.request(
+            "complete_recovery_verification",
+            timeout=timeout,
+            certificate_id=certificate_id,
+            incident_generation=incident_generation,
+        )
+
+    def cancel_recovery_verification(
+        self,
+        certificate_id: str,
+        incident_generation: int,
+        *,
+        timeout: float = 30.0,
+    ) -> dict[str, Any]:
+        return self.request(
+            "cancel_recovery_verification",
+            timeout=timeout,
+            certificate_id=certificate_id,
+            incident_generation=incident_generation,
+        )
+
     def get_events(
         self,
         *,
```

### contextor/core/live_state/runtime.py
```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 591a8f2..992d25d 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1298,6 +1298,29 @@ def _repository_mutation_guard(root: Path):
     return guard
 
 
+def _repository_recovery_verification_guard(root: Path):
+    @contextlib.contextmanager
+    def guard():
+        from contextor.core.analysis.full_analysis_coordinator import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        lease = acquire_full_analysis(
+            root,
+            owner="desktop_recovery_verification",
+            writer_kind="full_analysis",
+            timeout=0.0,
+            poll_interval=0.01,
+        )
+        try:
+            yield
+        finally:
+            release_full_analysis(lease)
+
+    return guard
+
+
 def run_service(
     repo_path: str | Path,
     owner_pid: int | None = None,
@@ -1521,6 +1544,8 @@ def run_service(
                 _repository_canonical_query_handler
             ),
             mutation_guard=_repository_mutation_guard(root),
+            recovery_verification_guard=_repository_recovery_verification_guard(root),
+            repository_identity_reader=lambda: read_repository_identity(root),
             authority_identity=authority_identity,
             desktop_claim=desktop_claim,
             desktop_claim_reader=lambda: manager.read_desktop_claim(lease),
```

### contextor/core/live_state/watcher.py
```diff
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index a5047d9..052c723 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -9,6 +9,7 @@ from collections import OrderedDict, deque
 from collections.abc import Callable
 from dataclasses import dataclass
 from pathlib import Path
+from typing import Any
 
 from watchdog.events import FileSystemEventHandler
 from watchdog.observers import Observer
@@ -17,6 +18,9 @@ from watchdog.observers.polling import PollingObserver
 from .ipc import LiveStateClient
 
 
+RECOVERY_DEFERRED = object()
+
+
 @dataclass(frozen=True)
 class _PendingMutationIntent:
     idempotency_key: str
@@ -116,6 +120,7 @@ class DesktopLiveWatcher:
         on_status: Callable[[str], None] | None = None,
         on_reconnect: Callable[[LiveStateClient], None] | None = None,
         on_resync: Callable[[], object] | None = None,
+        recovery_admission: Callable[[Callable[[], Any]], Any] | None = None,
     ):
         """Watch one repository and route filesystem changes through LIVE.
 
@@ -140,8 +145,10 @@ class DesktopLiveWatcher:
         self.on_status = on_status
         self.on_reconnect = on_reconnect
         self.on_resync = on_resync
+        self.recovery_admission = recovery_admission
         self._startup_requires_resync = False
         self._startup_resync_attempted = False
+        self._recovery_rebaseline_pending = False
         self._ambiguous_updates: set[str] = set()
         self._pending_intents: dict[str, _PendingMutationIntent] = {}
         self._inflight_updates: OrderedDict[str, _WatcherMutationJob] = OrderedDict()
@@ -150,6 +157,20 @@ class DesktopLiveWatcher:
         self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
         self._event_handler = _LiveFilesystemEventHandler(self._enqueue_path)
 
+    def _admit_recovery_action(self, action: Callable[[], Any]) -> Any:
+        if self.recovery_admission is None:
+            return action()
+        return self.recovery_admission(action)
+
+    def _recovery_is_active(self) -> bool:
+        return self._admit_recovery_action(lambda: True) is RECOVERY_DEFERRED
+
+    def complete_recovery_certificate(self) -> None:
+        self._startup_requires_resync = False
+        self._startup_resync_attempted = False
+        self._recovery_rebaseline_pending = True
+        self._wake.set()
+
     def _observer_timeout(self) -> float:
         return max(2.0, self.interval * 2)
 
@@ -487,6 +508,7 @@ class DesktopLiveWatcher:
         state = response["state"]
         modules = getattr(state, "modules", None)
         if not isinstance(modules, dict):
+            self._startup_requires_resync = True
             return []
 
         from contextor.core.analysis.state_manager import FileStateManager
@@ -589,10 +611,15 @@ class DesktopLiveWatcher:
                 result = response.get("result") if isinstance(response, dict) else None
                 result_status = getattr(result, "status", None)
                 if isinstance(response, dict) and response.get("status") == "ok" and result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}:
-                    if job.observed_state is None:
-                        self._snapshot.pop(job.path, None)
-                    else:
-                        self._snapshot[job.path] = job.observed_state
+                    def trust_completed_path() -> bool:
+                        if job.observed_state is None:
+                            self._snapshot.pop(job.path, None)
+                        else:
+                            self._snapshot[job.path] = job.observed_state
+                        return True
+
+                    if self._admit_recovery_action(trust_completed_path) is RECOVERY_DEFERRED:
+                        self._enqueue_path(job.path, wake=False)
                     completed.append(job.path)
                     from contextor.core.runtime_trace import trace_event
                     try:
@@ -639,10 +666,27 @@ class DesktopLiveWatcher:
 
     def poll_once(self) -> list[str]:
         reconciled = self._poll_inflight_updates()
+        if self._recovery_is_active():
+            return reconciled
+        if self._recovery_rebaseline_pending:
+            current_scan = self._scan()
+            self._snapshot = current_scan
+            previous_startup_pending = set(self._startup_pending)
+            reconciled_startup_pending = self._startup_reconciliation_paths(
+                current_scan
+            )
+            if self._startup_requires_resync:
+                previous_startup_pending.update(reconciled_startup_pending)
+                self._startup_pending = sorted(previous_startup_pending)
+            else:
+                self._startup_pending = reconciled_startup_pending
+            for pending_path in self._startup_pending:
+                self._enqueue_path(pending_path, wake=False)
+            self._recovery_rebaseline_pending = False
         changed = self._drain_pending()
-        if not changed and self._startup_pending:
+        using_startup_pending = not changed and bool(self._startup_pending)
+        if using_startup_pending:
             changed = list(self._startup_pending)
-            self._startup_pending = []
         if not changed and not self._startup_requires_resync:
             return reconciled
         current: dict[str, tuple[int, int]] = {}
@@ -668,26 +712,32 @@ class DesktopLiveWatcher:
             return reconciled
         if self._startup_requires_resync:
             if self._startup_resync_attempted:
+                self._requeue_paths(changed)
                 return reconciled
             self._startup_resync_attempted = True
             if self.on_resync is None:
+                self._requeue_paths(changed)
                 self._emit("LIVE: canonical baseline requires resync")
                 return reconciled
             try:
                 outcome = self.on_resync()
                 if not self._resync_completed(outcome):
+                    self._requeue_paths(changed)
                     self._emit("LIVE: startup resync failed; baseline remains untrusted")
                     return []
             except Exception as exc:
+                self._requeue_paths(changed)
                 self._emit(f"LIVE: startup resync failed: {exc}")
                 return reconciled
             current = self._scan()
             try:
                 snapshot = self.client.snapshot()
             except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
+                self._requeue_paths(changed)
                 self._emit("LIVE: startup resync baseline could not be verified")
                 return reconciled
             if self._trusted_file_state(snapshot) is None:
+                self._requeue_paths(changed)
                 self._emit("LIVE: startup resync baseline remains untrusted")
                 return []
             self._snapshot = current
@@ -720,7 +770,10 @@ class DesktopLiveWatcher:
             self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
             return reconciled
 
-        for path in changed:
+        for path_index, path in enumerate(changed):
+            if self._recovery_is_active():
+                deferred.extend(changed[path_index:])
+                break
             from contextor.core.runtime_trace import new_trace_operation, trace_event
 
             op = new_trace_operation("u")
@@ -751,14 +804,22 @@ class DesktopLiveWatcher:
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if not candidate_requires_update:
-                    self._pending_intents.pop(path, None)
+                    def accept_unchanged_path() -> bool:
+                        self._pending_intents.pop(path, None)
+                        if was_ambiguous:
+                            self._ambiguous_updates.discard(path)
+                        if path in current:
+                            self._snapshot[path] = current[path]
+                        else:
+                            self._snapshot.pop(path, None)
+                        return True
+
+                    admitted = self._admit_recovery_action(accept_unchanged_path)
+                    if admitted is RECOVERY_DEFERRED:
+                        deferred.extend(changed[path_index:])
+                        break
                     if was_ambiguous:
-                        self._ambiguous_updates.discard(path)
                         trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
-                    if path in current:
-                        self._snapshot[path] = current[path]
-                    else:
-                        self._snapshot.pop(path, None)
                     reconciled.append(path)
                     continue
                 current_state = current.get(path)
@@ -808,8 +869,15 @@ class DesktopLiveWatcher:
                 )
                 if current_inflight is not None:
                     if pending_intent is not None:
-                        self._pending_intents.pop(path, None)
-                        self._ambiguous_updates.discard(path)
+                        def clear_duplicate_intent() -> bool:
+                            self._pending_intents.pop(path, None)
+                            self._ambiguous_updates.discard(path)
+                            return True
+
+                        admitted = self._admit_recovery_action(clear_duplicate_intent)
+                        if admitted is RECOVERY_DEFERRED:
+                            deferred.extend(changed[path_index:])
+                            break
                     continue
                 if pending_intent is None:
                     pending_intent = _PendingMutationIntent(
@@ -821,15 +889,20 @@ class DesktopLiveWatcher:
                         observed_sha256=current_sha256,
                     )
                     self._pending_intents[path] = pending_intent
+                response = self._admit_recovery_action(
+                    lambda: self.client.submit_update_file(
+                        path,
+                        origin="desktop_watcher",
+                        trace_op=pending_intent.trace_op,
+                        idempotency_key=pending_intent.idempotency_key,
+                    )
+                )
+                if response is RECOVERY_DEFERRED:
+                    deferred.extend(changed[path_index:])
+                    break
                 if was_ambiguous:
                     self._ambiguous_updates.discard(path)
                     trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
-                response = self.client.submit_update_file(
-                    path,
-                    origin="desktop_watcher",
-                    trace_op=pending_intent.trace_op,
-                    idempotency_key=pending_intent.idempotency_key,
-                )
             except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                 self._ambiguous_updates.add(path)
                 trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
@@ -863,7 +936,8 @@ class DesktopLiveWatcher:
                 deferred.append(path)
         if deferred:
             self._requeue_paths(deferred)
-        self._startup_pending = []
+        elif self._startup_pending and set(self._startup_pending).issubset(set(changed)):
+            self._startup_pending = []
         return reconciled + self._poll_inflight_updates()
 
     def _handle_poll_error(self, exc: OSError | RuntimeError | EOFError) -> None:
```

### contextor/ui/gui.py
```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index a32a7cb..91fb6ac 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -14,6 +14,7 @@ from datetime import datetime
 from queue import Empty, Queue
 from pathlib import Path
 from tkinter import filedialog, messagebox, ttk
+from typing import Any
 
 from contextor.core.analysis.full_analysis_coordinator import (
     FullAnalysisBusyError,
@@ -30,8 +31,10 @@ from contextor.core.live_state import (
     DesktopLiveWatcher,
     SecondDesktopActive,
     connect_or_start,
+    connect,
     migrate_legacy_snapshot,
 )
+from contextor.core.live_state.watcher import RECOVERY_DEFERRED
 from contextor.core.repository_identity import (
     RepositoryIdentityError,
     read_repository_identity,
@@ -145,6 +148,8 @@ class ContextorGUI:
         self._live_recovery_queue: Queue[tuple[str, str]] = Queue()
         self._live_recovery_prompt_pending: set[str] = set()
         self._live_recovery_lock = threading.Lock()
+        self._live_recovery_incidents: dict[str, dict[str, Any]] = {}
+        self._live_recovery_generations: dict[str, int] = {}
         self.last_live_state: dict[str, Any] | None = None
 
         self._closing = False
@@ -786,6 +791,54 @@ class ContextorGUI:
             self._selected_live_repo_path = ""
             return
         self._selected_live_repo_path = repo_path_var.get()
+        selected = self._selected_live_repo_path
+        if selected:
+            try:
+                repository_key = str(Path(selected).expanduser().resolve())
+            except (OSError, ValueError):
+                repository_key = str(selected)
+            with self._live_recovery_lock:
+                incident = self._live_recovery_incidents.get(repository_key)
+                if incident is not None and repository_key not in self._live_recovery_prompt_pending:
+                    self._live_recovery_prompt_pending.add(repository_key)
+                    self._live_recovery_queue.put((repository_key, incident["reason"]))
+
+    def _live_recovery_incident(self, repository_path: str) -> dict[str, Any] | None:
+        try:
+            repository_key = str(Path(repository_path).expanduser().resolve())
+        except (OSError, ValueError):
+            repository_key = str(repository_path)
+        with self._live_recovery_lock:
+            incident = self._live_recovery_incidents.get(repository_key)
+            return dict(incident) if incident is not None else None
+
+    def _set_live_recovery_verification_state(
+        self, repository_path: str, generation: int, state: str
+    ) -> bool:
+        try:
+            repository_key = str(Path(repository_path).expanduser().resolve())
+        except (OSError, ValueError):
+            repository_key = str(repository_path)
+        with self._live_recovery_lock:
+            incident = self._live_recovery_incidents.get(repository_key)
+            if incident is None or incident.get("generation") != generation:
+                return False
+            incident["verification_state"] = state
+            return True
+
+    def _watcher_recovery_admission(self, repository_path: str):
+        try:
+            repository_key = str(Path(repository_path).expanduser().resolve())
+        except (OSError, ValueError):
+            repository_key = str(repository_path)
+
+        def admit(submission_callable):
+            with self._live_recovery_lock:
+                if repository_key in self._live_recovery_incidents:
+                    return RECOVERY_DEFERRED
+                return submission_callable()
+
+        return admit
 
     def _is_selected_live_repository(self, path):
         if not hasattr(self, "_selected_live_repo_path"):
@@ -1076,10 +1129,14 @@ class ContextorGUI:
         self,
         repository_path: str,
         reason: str,
-    ) -> None:
+        *,
+        publication_revision: int | None = None,
+        publication_outcome: str | None = None,
+        queue_prompt: bool = True,
+    ) -> int | None:
         """Queue a confirmed recovery incident without calling Tk."""
         if getattr(self, "_closing", False):
-            return
+            return None
 
         try:
             repository_key = str(
@@ -1089,18 +1146,41 @@ class ContextorGUI:
             repository_key = str(repository_path)
 
         if not repository_key:
-            return
+            return None
 
         lock = getattr(self, "_live_recovery_lock", None)
         if lock is None:
-            return
+            return None
 
         with lock:
+            incidents = getattr(self, "_live_recovery_incidents", None)
+            if incidents is None:
+                incidents = self._live_recovery_incidents = {}
+            generations = getattr(self, "_live_recovery_generations", None)
+            if generations is None:
+                generations = self._live_recovery_generations = {}
+            generation = generations.get(repository_key, 0) + 1
+            generations[repository_key] = generation
+            incident = {
+                "generation": generation,
+                "reason": str(reason),
+                "required": True,
+                "verification_state": "required",
+            }
+            if (
+                isinstance(publication_revision, int)
+                and not isinstance(publication_revision, bool)
+                and publication_revision > 0
+            ):
+                incident["publication_revision"] = publication_revision
+            if publication_outcome in {"accepted", "rejected"}:
+                incident["publication_outcome"] = publication_outcome
+            incidents[repository_key] = incident
             pending = self._live_recovery_prompt_pending
-            if repository_key in pending:
-                return
-            pending.add(repository_key)
-            self._live_recovery_queue.put((repository_key, reason))
+            if queue_prompt and repository_key not in pending:
+                pending.add(repository_key)
+                self._live_recovery_queue.put((repository_key, str(reason)))
+            return generation
 
     def _drain_live_recovery_queue(self) -> None:
         """Process recovery dialogs exclusively on the Tk event loop."""
@@ -1114,6 +1194,10 @@ class ContextorGUI:
         except Empty:
             pass
         else:
+            with self._live_recovery_lock:
+                incident = self._live_recovery_incidents.get(repository_key)
+                if incident is not None:
+                    reason = incident["reason"]
             if not ContextorGUI._is_selected_live_repository(
                 self, repository_key
             ):
@@ -1122,6 +1206,9 @@ class ContextorGUI:
                         repository_key
                     )
             else:
+                self._set_live_status(
+                    "LIVE: recovery required; incremental updates are deferred."
+                )
                 try:
                     run_analysis = messagebox.askyesno(
                         "Contextor â€” Recovery Required",
@@ -1145,8 +1232,14 @@ class ContextorGUI:
                         )
                     raise
 
+                with self._live_recovery_lock:
+                    incident = self._live_recovery_incidents.get(repository_key)
+                    generation = incident["generation"] if incident else None
                 if run_analysis:
-                    self.analyze()
+                    self.analyze(
+                        recovery_repository=repository_key,
+                        recovery_generation=generation,
+                    )
 
         finally:
             if not getattr(self, "_closing", False):
@@ -1154,17 +1247,41 @@ class ContextorGUI:
                     100, self._drain_live_recovery_queue
                 )
 
-    def analyze(self):
-        path = self.repo_path_var.get()
+    def analyze(
+        self,
+        *,
+        recovery_repository: str | None = None,
+        recovery_generation: int | None = None,
+    ):
+        path = recovery_repository or self.repo_path_var.get()
         if not path:
             messagebox.showwarning(
                 "Missing repository", "Please select ROOT directory of scanned project"
             )
             return
 
+        try:
+            path = str(Path(path).expanduser().resolve())
+        except (OSError, ValueError):
+            pass
+        starting_incident = self._live_recovery_incident(path)
+        starting_generation = (
+            starting_incident.get("generation")
+            if starting_incident is not None
+            else None
+        )
+        if (
+            recovery_generation is not None
+            and starting_generation != recovery_generation
+        ):
+            return
+        if recovery_generation is not None:
+            self._set_live_recovery_verification_state(
+                path, recovery_generation, "full_analysis"
+            )
+
         pre_seq = 0
         try:
-            from pathlib import Path
             from contextor.core.live_state import connect
             live_client = connect(Path(path))
             if live_client is not None:
@@ -1174,24 +1291,185 @@ class ContextorGUI:
             pre_seq = 0
 
         def task(log=None, progress_callback=None):
-            errors, _ = run_full_analysis_exclusive(
+            errors, analysis_result = run_full_analysis_exclusive(
                 path,
                 owner="desktop_analysis",
                 log=log,
                 progress_callback=progress_callback,
                 is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
             )
-            return errors
+            return errors, analysis_result
+
+        def on_success(outcome):
+            errors, analysis_result = outcome
+            incident_before_publish_result = self._live_recovery_incident(path)
+            analysis_recovery_generation = None
+            if getattr(analysis_result, "live_publish_status", None) == "recovery_required":
+                analysis_recovery_generation = self._request_full_analysis_recovery(
+                    path,
+                    getattr(analysis_result, "live_publish_warning", None)
+                    or "Canonical LIVE publish requires recovery verification.",
+                    publication_revision=getattr(
+                        analysis_result, "live_publish_revision", None
+                    ),
+                    publication_outcome="accepted",
+                    queue_prompt=False,
+                )
+            current_incident = self._live_recovery_incident(path)
+            if current_incident is None:
+                self._start_live_watcher(path, initial_seq=pre_seq)
+                if not errors:
+                    messagebox.showinfo("OK", "No issues found. Repository is healthy!")
+                    return
+                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
+                messagebox.showwarning("Issues Detected", msg)
+                return
 
-        def on_success(errors):
             self._start_live_watcher(path, initial_seq=pre_seq)
-            if not errors:
-                messagebox.showinfo("OK", "No issues found. Repository is healthy!")
+            generation = None
+            if (
+                analysis_recovery_generation is not None
+                and current_incident["generation"] == analysis_recovery_generation
+                and (
+                    (
+                        incident_before_publish_result is None
+                        and starting_generation is None
+                    )
+                    or (
+                        incident_before_publish_result is not None
+                        and incident_before_publish_result.get("generation")
+                        == starting_generation
+                    )
+                )
+            ):
+                generation = analysis_recovery_generation
+            elif (
+                analysis_recovery_generation is None
+                and starting_generation is not None
+                and current_incident["generation"] == starting_generation
+            ):
+                generation = starting_generation
+            if generation is None:
+                self._set_live_status(
+                    "LIVE recovery verification failed; full repository analysis may be required."
+                )
+                if errors:
+                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
+                    messagebox.showwarning("Issues Detected", msg)
+                else:
+                    messagebox.showinfo(
+                        "Analysis complete",
+                        "No static issues found. LIVE recovery verification failed; "
+                        "full repository analysis may be required.",
+                    )
+                return
+
+            self._set_live_recovery_verification_state(
+                path, generation, "verifying"
+            )
+
+            verification_client = None
+            try:
+                verification_client = connect(Path(path))
+                if verification_client is None:
+                    verification = {"status": "error", "error": "recovery_live_missing"}
+                else:
+                    verification = verification_client.verify_recovery(generation)
+            except Exception as exc:
+                verification = {
+                    "status": "error",
+                    "error": f"{type(exc).__name__}: {exc}",
+                }
+
+            certificate = verification.get("certificate") if isinstance(verification, dict) else None
+            try:
+                identity = read_repository_identity(path)
+            except Exception:
+                identity = None
+            cert_valid = (
+                isinstance(verification, dict)
+                and verification.get("status") == "ok"
+                and isinstance(certificate, dict)
+                and certificate.get("incident_generation") == generation
+                and identity is not None
+                and certificate.get("repo_id") == identity.repo_id
+                and certificate.get("root_path") == str(Path(identity.root_path).resolve())
+                and isinstance(certificate.get("revision"), int)
+                and not isinstance(certificate.get("revision"), bool)
+                and certificate.get("revision", 0) > 0
+                and isinstance(certificate.get("state_id"), str)
+                and bool(certificate.get("state_id"))
+            )
+            cleared = False
+            if cert_valid:
+                with self._live_recovery_lock:
+                    latest = self._live_recovery_incidents.get(path)
+                    if latest is not None and latest.get("generation") == generation:
+                        try:
+                            completed = verification_client.complete_recovery_verification(
+                                certificate["certificate_id"], generation
+                            )
+                        except Exception as exc:
+                            completed = {"status": "error", "error": str(exc)}
+                        if (
+                            isinstance(completed, dict)
+                            and completed.get("status") == "ok"
+                            and completed.get("released") is True
+                            and completed.get("certificate_id")
+                            == certificate["certificate_id"]
+                            and completed.get("incident_generation") == generation
+                        ):
+                            watcher = self.live_watchers.get(identity.repo_id)
+                            if watcher is not None:
+                                watcher.complete_recovery_certificate()
+                            del self._live_recovery_incidents[path]
+                            self._live_recovery_prompt_pending.discard(path)
+                            cleared = True
+
+            if cleared:
+                self._set_live_status(
+                    "LIVE recovery verified; incremental updates resumed."
+                )
+                if not errors:
+                    messagebox.showinfo("OK", "LIVE recovery verified; incremental updates resumed.")
+                else:
+                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
+                    messagebox.showwarning("Issues Detected", msg)
                 return
-            msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
-            messagebox.showwarning("Issues Detected", msg)
+
+            if (
+                isinstance(certificate, dict)
+                and isinstance(certificate.get("certificate_id"), str)
+                and verification_client is not None
+            ):
+                try:
+                    verification_client.cancel_recovery_verification(
+                        certificate["certificate_id"], generation
+                    )
+                except Exception:
+                    pass
+            self._set_live_recovery_verification_state(
+                path, generation, "failed"
+            )
+
+            self._set_live_status(
+                "LIVE recovery verification failed; full repository analysis may be required."
+            )
+            if not errors:
+                messagebox.showinfo(
+                    "Analysis complete",
+                    "No static issues found. LIVE recovery verification failed; "
+                    "full repository analysis may be required.",
+                )
+            else:
+                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
+                messagebox.showwarning("Issues Detected", msg)
 
         def on_error(exc):
+            if recovery_generation is not None:
+                self._set_live_recovery_verification_state(
+                    path, recovery_generation, "analysis_failed"
+                )
             self._set_live_status(f"Repository analysis failed: {exc}", category="LIVE_STATE")
             messagebox.showerror("error", str(exc))
 
@@ -1377,9 +1655,14 @@ class ContextorGUI:
                 self.live_event_feed = feeds.get(identity.repo_id)
                 if existing_client is not None:
                     self.live_client = existing_client
-                self._set_live_status(
-                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
-                )
+                if self._live_recovery_incident(path) is None:
+                    self._set_live_status(
+                        f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
+                    )
+                else:
+                    self._set_live_status(
+                        "LIVE: recovery required; incremental updates are deferred."
+                    )
             if getattr(self, "_live_start_retry_after_id", None) is not None:
                 if hasattr(self, "root") and hasattr(self.root, "after_cancel"):
                     try:
@@ -1463,7 +1746,12 @@ class ContextorGUI:
             if state_revision is not None and live_revision == int(state_revision):
                 if state_id and getattr(live_state, "state_id", None) == state_id:
                     if ContextorGUI._is_selected_live_repository(self, path):
-                        self._set_live_status("LIVE: shared state attached; watcher active")
+                        if self._live_recovery_incident(path) is None:
+                            self._set_live_status("LIVE: shared state attached; watcher active")
+                        else:
+                            self._set_live_status(
+                                "LIVE: recovery required; incremental updates are deferred."
+                            )
                 else:
                     if ContextorGUI._is_selected_live_repository(self, path):
                         self._set_live_status(
@@ -1473,7 +1761,6 @@ class ContextorGUI:
                             path,
                             "Canonical state identity mismatch.",
                         )
-                    return
             else:
                 startup_lease = None
                 try:
@@ -1501,18 +1788,21 @@ class ContextorGUI:
                         isinstance(published, dict)
                         and published.get("resync_required") is True
                     ):
+                        outcome = (
+                            "accepted" if published.get("status") == "ok"
+                            else "rejected"
+                        )
+                        revision = published.get("revision")
                         self._request_full_analysis_recovery(
                             path,
                             "Canonical LIVE publish requires recovery verification.",
+                            publication_revision=revision,
+                            publication_outcome=outcome,
                         )
                         if ContextorGUI._is_selected_live_repository(self, path):
-                            outcome = (
-                                "accepted" if published.get("status") == "ok"
-                                else "rejected"
-                            )
                             self._set_live_status(
                                 f"LIVE: recovery required after {outcome} publish "
-                                f"(revision {published.get('revision')})"
+                                f"(revision {revision})"
                             )
                         return
                     if (
@@ -1559,14 +1849,30 @@ class ContextorGUI:
                 self.live_event_feed = feeds.get(identity.repo_id)
                 if existing_client is not None:
                     self.live_client = existing_client
-                self._set_live_status(
-                    f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
-                )
+                incident = self._live_recovery_incident(path)
+                if incident is None:
+                    self._set_live_status(
+                        f"[{identity.repo_name}] LIVE: shared state attached; watcher active"
+                    )
+                else:
+                    self._set_live_status(
+                        "LIVE: recovery required; incremental updates are deferred."
+                    )
             return
 
         def status_callback(message, event=None, name=identity.repo_name):
             if not ContextorGUI._is_selected_live_repository(self, path):
                 return
+            incident = self._live_recovery_incident(path)
+            if incident is not None and any(
+                marker in message.lower()
+                for marker in (
+                    "watcher active",
+                    "shared state attached",
+                    "shared state published",
+                )
+            ):
+                return
             if event is None and (message.startswith("LIVE update successful:") or message.startswith("Updating LIVE:")):
                 return
             cat = event.get("category", "LIVE_STATE") if isinstance(event, dict) else "LIVE_STATE"
@@ -1589,12 +1895,11 @@ class ContextorGUI:
                 feed.client = new_client
 
         def on_resync():
-            from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
-            return run_full_analysis_exclusive(
+            self._request_full_analysis_recovery(
                 path,
-                owner="desktop_analysis",
-                timeout=30.0,
+                "Startup canonical baseline requires full analysis.",
             )
+            return False
 
         if getattr(self, "_closing", False):
             return
@@ -1607,6 +1912,7 @@ class ContextorGUI:
             on_status=status_callback,
             on_reconnect=on_reconnect,
             on_resync=on_resync,
+            recovery_admission=self._watcher_recovery_admission(path),
         )
         if initial_seq is not None:
             feed = DesktopLiveEventFeed(
@@ -1633,6 +1939,11 @@ class ContextorGUI:
             return
         watcher.start()
         feed.start()
+        incident = self._live_recovery_incident(path)
+        if incident is not None and ContextorGUI._is_selected_live_repository(self, path):
+            self._set_live_status(
+                "LIVE: recovery required; incremental updates are deferred."
+            )
 
     def _refresh_repo_identity(self, path):
         """Refresh the permanent repository identity shown beside LIVE status."""
```

### tests/test_gui_live_startup.py
```diff
diff --git a/tests/test_gui_live_startup.py b/tests/test_gui_live_startup.py
index ba0c96b..aec5314 100644
--- a/tests/test_gui_live_startup.py
+++ b/tests/test_gui_live_startup.py
@@ -89,16 +89,37 @@ def _make_controller(repo_path, root=None):
         _live_start_lock=threading.Lock(),
         _live_start_inflight=set(),
         _live_start_threads={},
+        _live_recovery_queue=Queue(),
+        _live_recovery_prompt_pending=set(),
+        _live_recovery_lock=threading.Lock(),
+        _live_recovery_incidents={},
+        _live_recovery_generations={},
         repo_id_var=_GuiFakeVar("Repo ID: unregistered"),
         repo_path_var=_GuiFakeVar(str(repo_path)),
         _selected_live_repo_path=str(repo_path),
         layer_path_var=_GuiFakeVar(""),
         file_path_var=_GuiFakeVar(""),
         theme_mode="light",
-        _set_live_status=lambda msg: statuses.append(msg),
+        _set_live_status=lambda msg, **_kwargs: statuses.append(msg),
         _events=events,
         _statuses=statuses,
     )
+    controller._live_recovery_incident = (
+        lambda path: ContextorGUI._live_recovery_incident(controller, path)
+    )
+    controller._set_live_recovery_verification_state = (
+        lambda path, generation, state: ContextorGUI._set_live_recovery_verification_state(
+            controller, path, generation, state
+        )
+    )
+    controller._watcher_recovery_admission = (
+        lambda path: ContextorGUI._watcher_recovery_admission(controller, path)
+    )
+    controller._request_full_analysis_recovery = (
+        lambda path, reason, **kwargs: ContextorGUI._request_full_analysis_recovery(
+            controller, path, reason, **kwargs
+        )
+    )
     return controller
 
 
@@ -605,9 +626,11 @@ def _bind_recovery_prompt(controller):
     controller._live_recovery_queue = Queue()
     controller._live_recovery_prompt_pending = set()
     controller._live_recovery_lock = threading.Lock()
+    controller._live_recovery_incidents = {}
+    controller._live_recovery_generations = {}
     controller._request_full_analysis_recovery = (
-        lambda path, reason: ContextorGUI._request_full_analysis_recovery(
-            controller, path, reason
+        lambda path, reason, **kwargs: ContextorGUI._request_full_analysis_recovery(
+            controller, path, reason, **kwargs
         )
     )
     controller._drain_live_recovery_queue = (
@@ -616,6 +639,183 @@ def _bind_recovery_prompt(controller):
     return controller
 
 
+def _make_analysis_controller(repo):
+    controller = ContextorGUI.__new__(ContextorGUI)
+    controller.root = MockTkRoot()
+    controller.repo_path_var = _GuiFakeVar(str(repo))
+    controller.progress_bar = SimpleNamespace(is_cancelled=False)
+    controller.log_box = object()
+    controller.cpu_indicator = object()
+    controller.stop_btn = object()
+    controller._closing = False
+    controller._live_recovery_queue = Queue()
+    controller._live_recovery_prompt_pending = set()
+    controller._live_recovery_lock = threading.Lock()
+    controller._live_recovery_incidents = {}
+    controller._live_recovery_generations = {}
+    controller.live_watchers = {}
+    controller._statuses = []
+    controller._set_live_status = lambda message, **_kwargs: controller._statuses.append(message)
+    controller._start_live_watcher = MagicMock()
+    controller._busy_buttons = lambda: []
+    return controller
+
+
+def test_full_analysis_certifies_accepted_degraded_publish_and_preserves_revision(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = PersistentIdentityRegistry(str(repo))
+    controller = _make_analysis_controller(repo)
+    watcher = SimpleNamespace(complete_recovery_certificate=MagicMock())
+    controller.live_watchers[identity.repo_id] = watcher
+    observations = []
+
+    certificate = {
+        "certificate_id": "certificate-1",
+        "incident_generation": 1,
+        "repo_id": identity.repo_id,
+        "root_path": str(repo.resolve()),
+        "state_id": "state-id",
+        "revision": 4,
+    }
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return {"latest_seq": 9}
+
+        def verify_recovery(self, generation):
+            incident = ContextorGUI._live_recovery_incident(controller, str(repo))
+            observations.append((generation, incident))
+            return {"status": "ok", "certificate": certificate}
+
+        def complete_recovery_verification(self, certificate_id, generation):
+            return {
+                "status": "ok",
+                "released": True,
+                "certificate_id": certificate_id,
+                "incident_generation": generation,
+            }
+
+        def cancel_recovery_verification(self, *_args, **_kwargs):
+            pytest.fail("a valid certificate must not be cancelled")
+
+    client = Client()
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda *_args: client)
+    full_calls = []
+    monkeypatch.setattr(
+        gui,
+        "run_full_analysis_exclusive",
+        lambda *_args, **_kwargs: (
+            full_calls.append(True)
+            or (
+                [],
+                SimpleNamespace(
+                    live_publish_status="recovery_required",
+                    live_publish_revision=4,
+                    live_publish_warning="snapshot_lock_release_unverified",
+                ),
+            )
+        ),
+    )
+    monkeypatch.setattr(
+        gui,
+        "run_with_progress",
+        lambda _root, _progress, task, *, on_success, **_kwargs: on_success(task()),
+    )
+    monkeypatch.setattr(gui.messagebox, "showinfo", MagicMock())
+    monkeypatch.setattr(gui.messagebox, "showwarning", MagicMock())
+
+    ContextorGUI.analyze(controller)
+
+    assert full_calls == [True]
+    assert observations == [
+        (
+            1,
+            {
+                "generation": 1,
+                "reason": "snapshot_lock_release_unverified",
+                "required": True,
+                "verification_state": "verifying",
+                "publication_revision": 4,
+                "publication_outcome": "accepted",
+            },
+        )
+    ]
+    assert ContextorGUI._live_recovery_incident(controller, str(repo)) is None
+    watcher.complete_recovery_certificate.assert_called_once_with()
+    assert controller._statuses[-1] == (
+        "LIVE recovery verified; incremental updates resumed."
+    )
+
+
+def test_older_recovery_certificate_cannot_clear_newer_incident(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = PersistentIdentityRegistry(str(repo))
+    controller = _make_analysis_controller(repo)
+    controller._request_full_analysis_recovery(
+        str(repo), "first incident"
+    )
+    certificate = {
+        "certificate_id": "old-certificate",
+        "incident_generation": 1,
+        "repo_id": identity.repo_id,
+        "root_path": str(repo.resolve()),
+        "state_id": "state-id",
+        "revision": 4,
+    }
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return {"latest_seq": 9}
+
+        def verify_recovery(self, generation):
+            assert generation == 1
+            ContextorGUI._request_full_analysis_recovery(
+                controller, str(repo), "newer incident"
+            )
+            return {"status": "ok", "certificate": certificate}
+
+        def complete_recovery_verification(self, *_args, **_kwargs):
+            pytest.fail("stale generation must not be completed")
+
+        def cancel_recovery_verification(self, certificate_id, generation):
+            assert certificate_id == "old-certificate"
+            assert generation == 1
+            return {"status": "ok", "released": True}
+
+    client = Client()
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda *_args: client)
+    monkeypatch.setattr(
+        gui,
+        "run_full_analysis_exclusive",
+        lambda *_args, **_kwargs: ([], SimpleNamespace(live_publish_status="success")),
+    )
+    monkeypatch.setattr(
+        gui,
+        "run_with_progress",
+        lambda _root, _progress, task, *, on_success, **_kwargs: on_success(task()),
+    )
+    monkeypatch.setattr(gui.messagebox, "showinfo", MagicMock())
+    monkeypatch.setattr(gui.messagebox, "showwarning", MagicMock())
+
+    ContextorGUI.analyze(
+        controller,
+        recovery_repository=str(repo),
+        recovery_generation=1,
+    )
+
+    incident = ContextorGUI._live_recovery_incident(controller, str(repo))
+    assert incident["generation"] == 2
+    assert incident["reason"] == "newer incident"
+    assert incident["verification_state"] == "required"
+    assert "LIVE recovery verification failed" in controller._statuses[-1]
+
+
 def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -630,6 +830,9 @@ def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch
         def snapshot(self):
             return {"state": remote, "revision": 7}
 
+        def get_events(self, **_kwargs):
+            return {"latest_seq": 0}
+
         def publish(self, *_args, **_kwargs):
             raise AssertionError("generation conflict must not publish")
 
@@ -646,6 +849,9 @@ def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch
 
     assert controller._statuses.count(
         "LIVE: generation conflict; analysis required"
+    ) == 1
+    assert controller._statuses.count(
+        "LIVE: recovery required; incremental updates are deferred."
     ) == 2
     assert controller._live_recovery_queue.qsize() == 1
     assert root.scheduled == {}
@@ -673,6 +879,7 @@ def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
     assert "Canonical state identity mismatch." in ask.call_args.args[1]
     controller.analyze.assert_not_called()
     assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._live_recovery_incidents[str(repo.resolve())]["required"] is True
 
     ContextorGUI._request_full_analysis_recovery(
         controller, str(repo), "Canonical state identity mismatch."
@@ -697,8 +904,12 @@ def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch
     ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_called_once()
-    controller.analyze.assert_called_once_with()
+    controller.analyze.assert_called_once_with(
+        recovery_repository=str(repo.resolve()),
+        recovery_generation=1,
+    )
     assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
+    assert controller._live_recovery_incidents[str(repo.resolve())]["verification_state"] == "required"
     assert controller._live_recovery_queue.qsize() == 0
     assert next(iter(root.scheduled.values()))[0] == 100
 
@@ -706,7 +917,10 @@ def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch
         controller, str(repo), "Canonical state identity mismatch."
     )
     assert controller._live_recovery_queue.qsize() == 0
-    controller.analyze.assert_called_once_with()
+    controller.analyze.assert_called_once_with(
+        recovery_repository=str(repo.resolve()),
+        recovery_generation=1,
+    )
 
 
 def test_recovery_prompt_failed_analysis_preserves_incident(tmp_path, monkeypatch):
@@ -725,9 +939,13 @@ def test_recovery_prompt_failed_analysis_preserves_incident(tmp_path, monkeypatc
         ContextorGUI._drain_live_recovery_queue(controller)
 
     ask.assert_called_once()
-    controller.analyze.assert_called_once_with()
+    controller.analyze.assert_called_once_with(
+        recovery_repository=str(repo.resolve()),
+        recovery_generation=1,
+    )
     assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
     assert controller._live_recovery_queue.qsize() == 0
+    assert controller._live_recovery_incidents[str(repo.resolve())]["required"] is True
 
 
 def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
@@ -772,10 +990,44 @@ def test_recovery_prompt_suppressed_after_repository_switch(tmp_path, monkeypatc
     ask.assert_not_called()
     controller.analyze.assert_not_called()
     assert controller._live_recovery_prompt_pending == set()
+    assert str(repo.resolve()) in controller._live_recovery_incidents
     assert controller._live_recovery_queue.qsize() == 0
     assert next(iter(root.scheduled.values()))[0] == 100
 
 
+def test_dialog_exception_preserves_incident_and_allows_a_later_prompt(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    controller = _bind_recovery_prompt(
+        _make_controller(repo, MockTkRoot())
+    )
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "canonical state needs recovery"
+    )
+    monkeypatch.setattr(
+        gui.messagebox,
+        "askyesno",
+        MagicMock(side_effect=RuntimeError("dialog failed")),
+    )
+
+    with pytest.raises(RuntimeError, match="dialog failed"):
+        ContextorGUI._drain_live_recovery_queue(controller)
+
+    incident = controller._live_recovery_incidents[str(repo.resolve())]
+    assert incident["generation"] == 1
+    assert incident["required"] is True
+    assert controller._live_recovery_prompt_pending == set()
+    assert controller._live_recovery_queue.qsize() == 0
+
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(repo), "canonical state needs recovery"
+    )
+    assert controller._live_recovery_queue.qsize() == 1
+    assert controller._live_recovery_incidents[str(repo.resolve())]["generation"] == 2
+
+
 def test_live_connection_retry_does_not_prompt_for_recovery(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -897,11 +1149,80 @@ def test_accepted_startup_publication_requires_recovery_without_watcher(tmp_path
     assert controller._live_recovery_queue.qsize() == 1
     assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
     assert controller._statuses[-1] == "LIVE: recovery required after accepted publish (revision 7)"
+    assert controller._live_recovery_incidents[str(repo.resolve())] == {
+        "generation": 2,
+        "reason": "Canonical LIVE publish requires recovery verification.",
+        "required": True,
+        "verification_state": "required",
+        "publication_revision": 7,
+        "publication_outcome": "accepted",
+    }
     assert "LIVE: shared state published; watcher active" not in controller._statuses
     controller.analyze.assert_not_called()
 
 
 
+def test_startup_resync_queues_one_explicit_full_owner_without_running_full(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    controller = _bind_recovery_prompt(_make_controller(repo, MockTkRoot()))
+    loaded = SimpleNamespace(revision=7, state_id="same-generation")
+    captured = {}
+
+    class Client:
+        def snapshot(self):
+            return {"status": "ok", "state": loaded, "revision": 7}
+
+        def get_events(self, **_kwargs):
+            return {"latest_seq": 0}
+
+    class Watcher:
+        def __init__(self, *_args, **kwargs):
+            captured.update(kwargs)
+
+        def start(self):
+            pass
+
+    class Feed:
+        def __init__(self, *_args, **_kwargs):
+            pass
+
+        def replay_authority_events(self):
+            pass
+
+        def start(self):
+            pass
+
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
+    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_a, **_k: loaded,
+    )
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
+    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
+    monkeypatch.setattr(
+        gui,
+        "run_full_analysis_exclusive",
+        lambda *_a, **_kwargs: pytest.fail("startup resync must not launch FULL"),
+    )
+    monkeypatch.setattr(gui.messagebox, "askyesno", MagicMock(return_value=False))
+
+    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
+    assert captured["on_resync"]() is False
+    assert controller._live_recovery_queue.qsize() == 1
+    assert len(controller._live_recovery_incidents) == 1
+    assert next(iter(controller._live_recovery_incidents.values()))["reason"] == (
+        "Startup canonical baseline requires full analysis."
+    )
+    ContextorGUI._drain_live_recovery_queue(controller)
+    assert "LIVE: recovery required; incremental updates are deferred." in controller._statuses
+    assert next(iter(controller._live_recovery_incidents.values()))["required"] is True
+
+
 def test_recovery_request_from_worker_uses_queue_without_tk(tmp_path, monkeypatch):
     repo = tmp_path / "repo"
     repo.mkdir()
@@ -961,7 +1282,7 @@ def test_recovery_request_from_worker_uses_queue_without_tk(tmp_path, monkeypatc
                 "error": "canonical_persistence_revision_conflict",
                 "resync_required": True,
             },
-            "Canonical LIVE consistency error: canonical_persistence_revision_conflict.",
+                "Canonical LIVE publish requires recovery verification.",
         ),
     ],
 )
@@ -1014,7 +1335,12 @@ def test_startup_publication_error_recovery_classification(
     ContextorGUI._start_live_watcher_blocking(controller, str(repo))
 
     assert len(released) == 1
-    assert "LIVE: shared state attach failed; analysis required" in controller._statuses
+    if response.get("resync_required") is True:
+        assert controller._statuses[-1] == (
+            "LIVE: recovery required after rejected publish (revision None)"
+        )
+    else:
+        assert "LIVE: shared state attach failed; analysis required" in controller._statuses
     if expected_reason is None:
         assert controller._live_recovery_queue.qsize() == 0
         assert controller._live_recovery_prompt_pending == set()
```

### tests/test_live_watcher_startup_reconciliation.py
```diff
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 35d44fd..251f801 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -87,7 +87,7 @@ def _real_watcher_runtime(tmp_path, updater):
     manager = FileStateManager(str(repo_cache_dir(repo)))
     manager.save(identity.repo_id, revision=0)
     server = CanonicalLiveServer(
-        SimpleNamespace(revision=0, state_id=identity.repo_id),
+        SimpleNamespace(revision=0, state_id=identity.repo_id, modules={}),
         revision=0,
         updater=updater,
     )
@@ -741,6 +741,9 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
                 return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
         client = _QueuedClientAdapter(Client())
         watcher = DesktopLiveWatcher(repo, client)
+        # This case seeds and validates the generation below; startup recovery
+        # is covered by the dedicated startup tests.
+        watcher._startup_requires_resync = False
         watcher._snapshot = {str(source): (0, 1)}
         source.write_text("VALUE = 2\n", encoding="utf-8")
         manager = FileStateManager(str(repo_cache_dir(repo)))
@@ -769,6 +772,8 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
             status = "ERROR" if len(calls) == 1 else "UPDATED"
             return {"status": "ok", "result": SimpleNamespace(status=status)}
     watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
+    # This case exercises update-result retry behavior after startup.
+    watcher._startup_requires_resync = False
     watcher._snapshot = {str(source): (0, 1)}
     watcher._candidate_requires_update = lambda *_args: True
     source.write_text("VALUE = 2\n", encoding="utf-8")
@@ -794,6 +799,8 @@ def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path)
         def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
         def update_file(self, path, **_kwargs): calls.append(path); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
     watcher = DesktopLiveWatcher(repo, _QueuedClientAdapter(Client()))
+    # This case exercises deferred sibling reconciliation after startup.
+    watcher._startup_requires_resync = False
     watcher._snapshot = {str(first): (0, 1), str(second): (0, 1)}
     first.write_text("A = 2\n", encoding="utf-8"); second.write_text("B = 2\n", encoding="utf-8")
     manager = FileStateManager(str(repo_cache_dir(repo)))
```

### tests/test_recovery_authority_gate.py
```diff
diff --git a/tests/test_recovery_authority_gate.py b/tests/test_recovery_authority_gate.py
new file mode 100644
--- /dev/null
+++ b/tests/test_recovery_authority_gate.py
@@ -0,0 +1,403 @@
+from contextlib import contextmanager
+import threading
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
+
+
+def _recovery_server(
+    root,
+    *,
+    live_state="state",
+    committed_state="state",
+    committed_metadata=None,
+    identity=None,
+    snapshot_error=None,
+    updater=None,
+):
+    root_path = str(root.resolve())
+    repo_id = "repo-id"
+    if live_state == "state":
+        live_state = SimpleNamespace(state_id="state-id", revision=1)
+    if committed_state == "state":
+        committed_state = SimpleNamespace(state_id="state-id", revision=1)
+    if committed_metadata is None:
+        committed_metadata = SimpleNamespace(
+            repo_id=repo_id,
+            root_path=root_path,
+            state_id="state-id",
+            revision=1,
+        )
+    if identity is None:
+        identity = SimpleNamespace(repo_id=repo_id, root_path=root_path)
+
+    lock = __import__("threading").Lock()
+    entered = []
+    exited = []
+    persists = []
+
+    @contextmanager
+    def verification_guard():
+        lock.acquire()
+        entered.append(True)
+        try:
+            yield
+        finally:
+            exited.append(True)
+            lock.release()
+
+    @contextmanager
+    def committed_reader():
+        if snapshot_error is not None:
+            raise snapshot_error
+        if committed_state is None:
+            yield None
+        else:
+            yield committed_state, committed_metadata
+
+    server = CanonicalLiveServer(
+        live_state,
+        revision=(getattr(live_state, "revision", 1) if live_state is not None else 1),
+        updater=updater,
+        persister=lambda *_args: persists.append(True),
+        committed_snapshot_reader=committed_reader,
+        recovery_verification_guard=verification_guard,
+        repository_identity_reader=lambda: identity,
+        authority_identity={"repo_id": repo_id, "root_path": root_path},
+    )
+    server._test_guard_entered = entered
+    server._test_guard_exited = exited
+    server._test_persists = persists
+    return server
+
+
+def _verify(server, generation=1):
+    return server._dispatch(
+        {"operation": "verify_recovery", "incident_generation": generation}
+    )
+
+
+def _finish(server, certificate, operation="complete_recovery_verification"):
+    return server._dispatch(
+        {
+            "operation": operation,
+            "certificate_id": certificate["certificate_id"],
+            "incident_generation": certificate["incident_generation"],
+        }
+    )
+
+
+def test_recovery_certificate_holds_writer_and_mutation_fences_until_ack(tmp_path):
+    server = _recovery_server(tmp_path)
+    try:
+        result = _verify(server)
+        assert result["status"] == "ok"
+        certificate = result["certificate"]
+        assert certificate == {
+            "certificate_id": certificate["certificate_id"],
+            "incident_generation": 1,
+            "repo_id": "repo-id",
+            "root_path": str(tmp_path.resolve()),
+            "state_id": "state-id",
+            "revision": 1,
+        }
+        assert server._test_guard_entered == [True]
+        assert server._test_guard_exited == []
+        assert server._test_persists == []
+        assert server._mutation_coordinator.recovery_verification_active()
+
+        update = server._dispatch(
+            {"operation": "update_file", "file_path": str(tmp_path / "a.py")}
+        )
+        submitted = server._dispatch(
+            {
+                "operation": "submit_update_file",
+                "file_path": str(tmp_path / "a.py"),
+                "idempotency_key": "blocked-update",
+            }
+        )
+        published = server._dispatch(
+            {
+                "operation": "publish",
+                "state": SimpleNamespace(state_id="state-id", revision=2),
+                "origin": "test",
+            }
+        )
+        assert update["error"] == "recovery_verification_in_progress"
+        assert submitted["accepted"] is False
+        assert submitted["error"] == "recovery_verification_in_progress"
+        assert published["error"] == "recovery_verification_in_progress"
+        assert server._revision == 1
+
+        completed = _finish(server, certificate)
+        assert completed["status"] == "ok"
+        assert completed["released"] is True
+        assert completed["incident_generation"] == 1
+        assert server._test_guard_exited == [True]
+        assert not server._mutation_coordinator.recovery_verification_active()
+    finally:
+        server.close()
+
+
+def test_concurrent_publish_cannot_cross_recovery_fence(tmp_path):
+    server = _recovery_server(tmp_path)
+    publish_initial_check = threading.Event()
+    recovery_fence_started = threading.Event()
+    publish_result = {}
+    verify_result = {}
+    original_active = server._mutation_coordinator.recovery_verification_active
+    original_begin = server._mutation_coordinator.begin_recovery_verification
+
+    def observe_active():
+        active = original_active()
+        if threading.current_thread().name == "racing-publish" and not active:
+            publish_initial_check.set()
+        return active
+
+    def observe_begin(timeout):
+        admitted = original_begin(timeout)
+        if admitted:
+            recovery_fence_started.set()
+        return admitted
+
+    server._mutation_coordinator.recovery_verification_active = observe_active
+    server._mutation_coordinator.begin_recovery_verification = observe_begin
+    execution_lock = server._mutation_execution_lock
+
+    def publish():
+        publish_result.update(
+            server._dispatch(
+                {
+                    "operation": "publish",
+                    "state": SimpleNamespace(state_id="state-id", revision=2),
+                    "origin": "racing-test",
+                }
+            )
+        )
+
+    def verify():
+        verify_result.update(_verify(server))
+
+    publish_thread = threading.Thread(target=publish, name="racing-publish")
+    verify_thread = threading.Thread(target=verify, name="recovery-verification")
+    execution_lock_held = False
+    try:
+        execution_lock.acquire()
+        execution_lock_held = True
+        try:
+            publish_thread.start()
+            assert publish_initial_check.wait(2)
+            verify_thread.start()
+            assert recovery_fence_started.wait(2)
+        finally:
+            execution_lock.release()
+            execution_lock_held = False
+
+        publish_thread.join(2)
+        verify_thread.join(2)
+        assert not publish_thread.is_alive()
+        assert not verify_thread.is_alive()
+        assert verify_result["status"] == "ok"
+        assert publish_result["status"] == "error"
+        assert publish_result["error"] == "recovery_verification_in_progress"
+        assert server._revision == 1
+        assert server._mutation_coordinator.recovery_verification_active()
+        assert _finish(server, verify_result["certificate"])["released"] is True
+    finally:
+        if execution_lock_held:
+            execution_lock.release()
+        if publish_thread.ident is not None:
+            publish_thread.join(2)
+        if verify_thread.ident is not None:
+            verify_thread.join(2)
+        server.close()
+
+
+@pytest.mark.parametrize(
+    ("kwargs", "error"),
+    [
+        (
+            {
+                "committed_state": SimpleNamespace(state_id="other", revision=1),
+                "committed_metadata": SimpleNamespace(
+                    repo_id="repo-id",
+                    root_path="ROOT",
+                    state_id="other",
+                    revision=1,
+                ),
+            },
+            "recovery_live_identity_mismatch",
+        ),
+        (
+            {
+                "live_state": SimpleNamespace(state_id="state-id", revision=2),
+            },
+            "recovery_live_revision_mismatch",
+        ),
+        (
+            {
+                "committed_metadata": SimpleNamespace(
+                    repo_id="other",
+                    root_path="ROOT",
+                    state_id="state-id",
+                    revision=1,
+                ),
+            },
+            "recovery_snapshot_identity_mismatch",
+        ),
+        (
+            {
+                "committed_metadata": SimpleNamespace(
+                    repo_id="repo-id",
+                    root_path="ROOT",
+                    state_id="state-id",
+                    revision=0,
+                ),
+            },
+            "recovery_snapshot_invalid",
+        ),
+        (
+            {"committed_state": None},
+            "recovery_snapshot_missing",
+        ),
+        (
+            {"snapshot_error": OSError("unreadable")},
+            "recovery_snapshot_unreadable",
+        ),
+        (
+            {"identity": SimpleNamespace(repo_id="other", root_path="ROOT")},
+            "recovery_identity_mismatch",
+        ),
+        (
+            {"identity": SimpleNamespace(repo_id="repo-id", root_path="wrong-root")},
+            "recovery_identity_mismatch",
+        ),
+        (
+            {"live_state": None},
+            "recovery_live_missing",
+        ),
+    ],
+)
+def test_recovery_verification_rejects_invalid_authority_pairs(
+    tmp_path, kwargs, error
+):
+    root_path = str(tmp_path.resolve())
+    if "committed_metadata" in kwargs:
+        kwargs = {
+            **kwargs,
+            "committed_metadata": SimpleNamespace(
+                **{
+                    **vars(kwargs["committed_metadata"]),
+                    "root_path": root_path,
+                }
+            ),
+        }
+    if "identity" in kwargs and kwargs["identity"].root_path == "ROOT":
+        kwargs = {
+            **kwargs,
+            "identity": SimpleNamespace(
+                repo_id=kwargs["identity"].repo_id, root_path=root_path
+            ),
+        }
+    server = _recovery_server(tmp_path, **kwargs)
+    try:
+        result = _verify(server)
+        assert result == {"status": "error", "error": error}
+        assert not server._mutation_coordinator.recovery_verification_active()
+        assert server._test_guard_exited == server._test_guard_entered
+    finally:
+        server.close()
+
+
+def test_recovery_generation_and_certificate_are_required_to_release_fence(tmp_path):
+    server = _recovery_server(tmp_path)
+    try:
+        result = _verify(server, generation=8)
+        certificate = result["certificate"]
+        wrong = server._dispatch(
+            {
+                "operation": "complete_recovery_verification",
+                "certificate_id": "wrong",
+                "incident_generation": 8,
+            }
+        )
+        assert wrong == {
+            "status": "error",
+            "error": "recovery_certificate_mismatch",
+        }
+        assert server._mutation_coordinator.recovery_verification_active()
+
+        cancelled = _finish(
+            server, certificate, operation="cancel_recovery_verification"
+        )
+        assert cancelled["status"] == "ok"
+        assert cancelled["cancelled"] is True
+        assert cancelled["incident_generation"] == 8
+        assert not server._mutation_coordinator.recovery_verification_active()
+    finally:
+        server.close()
+
+
+def test_inflight_update_prevents_recovery_certificate(tmp_path):
+    updater_entered = threading.Event()
+    release_updater = threading.Event()
+
+    def updater(_candidate, _path):
+        updater_entered.set()
+        assert release_updater.wait(5)
+        return SimpleNamespace(status="UNCHANGED")
+
+    server = _recovery_server(tmp_path, updater=updater)
+    try:
+        accepted = server._dispatch(
+            {
+                "operation": "submit_update_file",
+                "file_path": str(tmp_path / "a.py"),
+                "idempotency_key": "inflight-update",
+            }
+        )
+        assert accepted["accepted"] is True
+        assert updater_entered.wait(2)
+
+        result = _verify(server)
+        assert result == {
+            "status": "error",
+            "error": "recovery_mutations_pending",
+        }
+        assert server._test_guard_entered == []
+        assert not server._mutation_coordinator.recovery_verification_active()
+    finally:
+        release_updater.set()
+        server.close()
+
+
+def test_recovery_verification_and_ack_round_trip_through_live_ipc(tmp_path):
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        verified = client.verify_recovery(3)
+        assert verified["status"] == "ok"
+        certificate = verified["certificate"]
+        assert certificate["incident_generation"] == 3
+        assert server._mutation_coordinator.recovery_verification_active()
+
+        blocked = client.submit_update_file(
+            str(tmp_path / "change.py"),
+            idempotency_key="while-recovery-is-fenced",
+        )
+        assert blocked["accepted"] is False
+        assert blocked["error"] == "recovery_verification_in_progress"
+
+        released = client.complete_recovery_verification(
+            certificate["certificate_id"], 3
+        )
+        assert released["status"] == "ok"
+        assert released["released"] is True
+        assert not server._mutation_coordinator.recovery_verification_active()
+    finally:
+        server.close()
+        thread.join(2)
```

### tests/test_watcher_recovery_admission.py
```diff
diff --git a/tests/test_watcher_recovery_admission.py b/tests/test_watcher_recovery_admission.py
new file mode 100644
--- /dev/null
+++ b/tests/test_watcher_recovery_admission.py
@@ -0,0 +1,324 @@
+import threading
+from collections import OrderedDict, deque
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.live_state.watcher import (
+    RECOVERY_DEFERRED,
+    DesktopLiveWatcher,
+    _PendingMutationIntent,
+    _WatcherMutationJob,
+)
+from contextor.ui.gui import ContextorGUI
+
+
+class _Manager:
+    def get_current_file_state(self, path, *, compute_hash):
+        stat = Path(path).stat()
+        return SimpleNamespace(
+            mtime_ns=stat.st_mtime_ns,
+            size=stat.st_size,
+            sha256="current-sha256" if compute_hash else None,
+        )
+
+
+class _Client:
+    def __init__(self):
+        self.revision = 1
+        self.submissions = []
+        self.mutation_status_calls = []
+        self.status_by_job = {}
+
+    def ping(self):
+        return {"available": True, "revision": self.revision}
+
+    def snapshot(self):
+        return {
+            "status": "ok",
+            "revision": self.revision,
+            "state": SimpleNamespace(
+                revision=self.revision,
+                state_id="state-id",
+                modules={},
+            ),
+        }
+
+    def mutation_status(self, job_id):
+        self.mutation_status_calls.append(job_id)
+        return self.status_by_job.get(
+            job_id, {"status": "ok", "state": "queued", "job_id": job_id}
+        )
+
+    def submit_update_file(self, path, **kwargs):
+        self.submissions.append((path, kwargs))
+        job_id = f"job-{len(self.submissions)}"
+        return {"status": "accepted", "accepted": True, "job_id": job_id}
+
+
+def _watcher(tmp_path, client=None, *, recovery_admission=None):
+    source = tmp_path / "sample.py"
+    source.write_text("value = 2\n", encoding="utf-8")
+    client = client or _Client()
+    watcher = DesktopLiveWatcher.__new__(DesktopLiveWatcher)
+    watcher.root = tmp_path.resolve()
+    watcher.client = client
+    watcher.recovery_admission = recovery_admission
+    watcher._pending_lock = threading.Lock()
+    watcher._pending_paths = deque()
+    watcher._pending_set = set()
+    watcher._wake = threading.Event()
+    watcher._snapshot = {str(source.resolve()): (0, 0)}
+    watcher._startup_pending = []
+    watcher._startup_requires_resync = False
+    watcher._startup_resync_attempted = False
+    watcher._recovery_rebaseline_pending = False
+    watcher._pending_intents = {}
+    watcher._ambiguous_updates = set()
+    watcher._inflight_updates = OrderedDict()
+    watcher._excluded_paths = ()
+    watcher._ignored_dirs = frozenset()
+    watcher._using_polling_fallback = False
+    watcher.interval = 0.01
+    watcher.on_status = lambda *_args, **_kwargs: None
+    watcher.on_reconnect = None
+    watcher.on_resync = None
+    watcher.owner_pid = None
+    watcher.owner_token = None
+    watcher.desktop_instance_id = None
+    watcher._trusted_file_state = lambda _snapshot=None: _Manager()
+    watcher._candidate_requires_update = (
+        lambda _path, _current, _snapshot, _manager: True
+    )
+    watcher._scan = lambda: {
+        str(source.resolve()): (
+            source.stat().st_mtime_ns,
+            source.stat().st_size,
+        )
+    }
+    watcher._startup_reconciliation_paths = lambda _current: []
+    return watcher, source
+
+
+def test_recovery_preserves_pending_paths_intents_ambiguity_and_startup_work(
+    tmp_path,
+):
+    active = True
+    client = _Client()
+
+    def admission(action):
+        return RECOVERY_DEFERRED if active else action()
+
+    watcher, source = _watcher(
+        tmp_path, client, recovery_admission=admission
+    )
+    path = str(source.resolve())
+    watcher._enqueue_path(path)
+    watcher._startup_pending = [path]
+    intent = _PendingMutationIntent(
+        "intent-1", path, "trace-1", (1, 1), 1.0, "sha"
+    )
+    watcher._pending_intents[path] = intent
+    watcher._ambiguous_updates.add(path)
+    original_scan = watcher._scan
+    watcher._scan = lambda: pytest.fail("blocked poll must not rescan")
+
+    assert watcher.poll_once() == []
+    assert list(watcher._pending_paths) == [path]
+    assert watcher._startup_pending == [path]
+    assert watcher._pending_intents[path] is intent
+    assert path in watcher._ambiguous_updates
+    assert client.submissions == []
+
+    watcher._scan = original_scan
+
+
+def test_inflight_status_reconciles_during_recovery_without_trusting_baseline(
+    tmp_path,
+):
+    client = _Client()
+    active = True
+    watcher, source = _watcher(
+        tmp_path,
+        client,
+        recovery_admission=lambda action: (
+            RECOVERY_DEFERRED if active else action()
+        ),
+    )
+    path = str(source.resolve())
+    old_baseline = watcher._snapshot[path]
+    watcher._inflight_updates["job-existing"] = _WatcherMutationJob(
+        "job-existing", path, "trace", "idem", old_baseline, 1.0, "sha"
+    )
+    client.status_by_job["job-existing"] = {
+        "status": "ok",
+        "state": "completed",
+        "response": {
+            "status": "ok",
+            "revision": 2,
+            "seq": 3,
+            "result": SimpleNamespace(status="UPDATED"),
+        },
+    }
+
+    watcher.poll_once()
+
+    assert client.mutation_status_calls == ["job-existing"]
+    assert "job-existing" not in watcher._inflight_updates
+    assert watcher._snapshot[path] == old_baseline
+    assert list(watcher._pending_paths) == [path]
+    assert client.submissions == []
+
+
+def test_mid_poll_recovery_defers_remaining_paths_and_keeps_intent(
+    tmp_path,
+):
+    client = _Client()
+    watcher, first = _watcher(tmp_path, client)
+    second = tmp_path / "later.py"
+    second.write_text("value = 3\n", encoding="utf-8")
+    second_path = str(second.resolve())
+    watcher._snapshot[second_path] = (0, 0)
+    active = False
+    first_path = str(first.resolve())
+
+    def admission(action):
+        nonlocal active
+        if active:
+            return RECOVERY_DEFERRED
+        result = action()
+        if client.submissions:
+            active = True
+        return result
+
+    watcher.recovery_admission = admission
+    watcher._enqueue_path(first_path)
+    watcher._enqueue_path(second_path)
+    pending_intent = _PendingMutationIntent(
+        "intent-2", second_path, "trace-2", (1, 1), 2.0, "sha-2"
+    )
+    watcher._pending_intents[second_path] = pending_intent
+
+    watcher.poll_once()
+
+    assert len(client.submissions) == 1
+    assert client.submissions[0][0] == first_path
+    assert watcher._pending_intents[second_path] is pending_intent
+    assert second_path in watcher._pending_paths
+    assert "job-1" in watcher._inflight_updates
+
+
+def test_recovery_release_rescans_and_revalidates_against_current_live(
+    tmp_path,
+):
+    client = _Client()
+    active = True
+    seen_revisions = []
+
+    def admission(action):
+        return RECOVERY_DEFERRED if active else action()
+
+    watcher, source = _watcher(
+        tmp_path, client, recovery_admission=admission
+    )
+    path = str(source.resolve())
+    watcher._enqueue_path(path)
+    watcher._startup_pending = [path]
+    watcher._candidate_requires_update = (
+        lambda _path, _current, snapshot, _manager: (
+            seen_revisions.append(snapshot["revision"]) or True
+        )
+    )
+    watcher.poll_once()
+    assert client.submissions == []
+
+    active = False
+    client.revision = 2
+    watcher.complete_recovery_certificate()
+    watcher.poll_once()
+
+    assert seen_revisions == [2]
+    assert client.submissions[0][0] == path
+    assert not watcher._recovery_rebaseline_pending
+
+
+def test_gui_admission_serializes_registration_with_submission():
+    submission_entered = threading.Event()
+    registration_waiting = threading.Event()
+    release_submission = threading.Event()
+    registration_done = threading.Event()
+
+    class ObservedLock:
+        def __init__(self):
+            self.inner = threading.Lock()
+
+        def __enter__(self):
+            if threading.current_thread().name == "recovery-registration":
+                registration_waiting.set()
+            self.inner.acquire()
+            return self
+
+        def __exit__(self, *_args):
+            self.inner.release()
+
+    controller = SimpleNamespace(
+        _live_recovery_lock=ObservedLock(),
+        _live_recovery_incidents={},
+        _live_recovery_generations={},
+        _live_recovery_prompt_pending=set(),
+        _live_recovery_queue=__import__("queue").Queue(),
+        _closing=False,
+    )
+    admission = ContextorGUI._watcher_recovery_admission(
+        controller, str(Path.cwd())
+    )
+
+    def submit():
+        submission_entered.set()
+        assert release_submission.wait(5)
+        return "submitted"
+
+    submit_result = []
+    submit_thread = threading.Thread(
+        target=lambda: submit_result.append(admission(submit)),
+        name="watcher-submission",
+    )
+    submit_thread.start()
+    assert submission_entered.wait(2)
+
+    def register():
+        ContextorGUI._request_full_analysis_recovery(
+            controller, str(Path.cwd()), "test incident"
+        )
+        registration_done.set()
+
+    registration_thread = threading.Thread(
+        target=register, name="recovery-registration"
+    )
+    registration_thread.start()
+    assert registration_waiting.wait(2)
+    assert not registration_done.is_set()
+
+    release_submission.set()
+    submit_thread.join(2)
+    registration_thread.join(2)
+    assert not submit_thread.is_alive()
+    assert not registration_thread.is_alive()
+    assert submit_result == ["submitted"]
+    assert registration_done.is_set()
+    assert len(controller._live_recovery_incidents) == 1
+
+
+def test_recovery_admission_does_not_swallow_submission_transport_errors(
+    tmp_path,
+):
+    controller = SimpleNamespace(
+        _live_recovery_lock=threading.Lock(),
+        _live_recovery_incidents={},
+    )
+    admission = ContextorGUI._watcher_recovery_admission(
+        controller, str(tmp_path)
+    )
+    with pytest.raises(ConnectionError, match="wire failed"):
+        admission(lambda: (_ for _ in ()).throw(ConnectionError("wire failed")))
```
