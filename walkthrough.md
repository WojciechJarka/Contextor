# L37/L38 A3C owner-thread certificate finalization

## CURRENT_HEAD

PRE_EDIT_HEAD=`6f0e774d40d395446d3962328ef2eb090aab9f30`. CURRENT_HEAD=`6f0e774d40d395446d3962328ef2eb090aab9f30`. The source worktree was clean before editing, apart from the previous task's `walkthrough.md`. No external commit advanced HEAD during this task. No Desktop, LIVE, or MCP restart; no manual `update_file`.

## PRE_EDIT_CONTEXTOR_EVIDENCE

Contextor MCP was used first. Deferred `get_symbol_implementation`, `get_symbol_lineage`, and `get_symbol_call_context` were discovered and their current MCP documentation read. Symbol previews for `CanonicalLiveServer.__init__`, `serve_forever`, `close`, `_execute_recovery_verification`, `_finish_recovery_verification`, `DesktopLiveWatcher.poll_once`, and `_startup_reconciliation_paths` resolved at canonical revision 70 with `workspace_sync=verified`. The complete implementations and source ranges from the immediately preceding read-only audit were available; Git/worktree source confirmed exact pre-edit anchors before editing. Call context for `CanonicalLiveServer.close` is intra-module only and located `__exit__`; Git source confirmed runtime watchdog/finally callers. Lineage preview was considered, but its narrow server path reports `workspace_sync=unverified`, so it was not used for literal source verification.

Pre-edit control flow: `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1180-1242` served IPC serially on one thread; recovery guard entered at 1570–1574 and was retained at 1637–1639; completion exited the guard at 1676 and cleared fence at 1682. `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py:1572-1582` starts that service thread, while watchdog at 1699–1719 and runtime finally at 1739–1746 call `server.close()` from other threads. `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:80-88,228-276,584-603` uses a process lock plus OS fd lock. This proves the existing foreign-thread `close` release path was unsafe to certify. `C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py:667-685` acknowledged a filesystem scan before canonical snapshot trust was established.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py`
- `C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py`
- `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py`
- `C:\Temp\Contextor_Repo\tests\test_recovery_authority_gate.py`
- `C:\Temp\Contextor_Repo\tests\test_watcher_recovery_admission.py`

`walkthrough.md` is the required report and is excluded from this source/test list. `runtime.py` and `gui.py` were inspected and left unchanged because their existing call/result boundaries are compatible with the owner-thread finalization and historical certificate-generation semantics.

## SERVICE_THREAD_OWNERSHIP

CODE_PATH_PROVED: `ipc.py:1192-1224` records the service thread identity before dispatch; `_execute_recovery_verification` at 1687 and `_finalize_recovery_certificate` at 1614 reject foreign-thread creation/finalization once service ownership exists. Normal complete/cancel still use synchronous IPC dispatch. The retained generator context exits only on its recorded owner thread. Direct non-service test objects retain same-thread lifecycle behavior before `serve_forever` starts.

## CERTIFICATE_DEADLINE_AND_WAKEUP

CODE_PATH_PROVED: `ipc.py:96-97,806-817,1578-1613,1780-1845` stores a unique ID, generation, repo/root/state ID/revision, owner identity, and a 30-second monotonic deadline (the public certificate shape remains compatible). One daemon `threading.Timer` is created for the outstanding certificate; it only sends an authenticated local lifecycle-wake IPC request and never exits the guard. The service thread checks expiry before dispatch and during a silent connected client's `poll` loop. The authenticated wake branch at `ipc.py:2135` waits any small remaining monotonic interval, then expires on the owner thread. This closes a reproduced early-wakeup race in which a timer request could arrive just before the deadline and leave the service blocked in `accept`. Release cancels the timer. Expired completion returns an error and cannot certify GUI recovery. The deadline does not mutate canonical revision or state.

## OWNER_THREAD_FINALIZATION

CODE_PATH_PROVED: `ipc.py:1614-1686,1847-1854` uses one finalizer for complete, cancel, expiry, and shutdown. It checks certificate ID/generation, owner thread, pending/finalizing/degraded state, and monotonic deadline. It transitions to `finalizing`, exits the guard, and only then clears certificate ownership and the mutation fence. A duplicate ack cannot release twice. The certificate's revision and state ID remain historical verification evidence; the code makes no latest-generation assertion after fence release.

## SHUTDOWN_HANDSHAKE

CODE_PATH_PROVED: `ipc.py:1192-1224,2376-2426` makes nonowner `close` set stop, send an authenticated local wake, wait boundedly for service-thread termination, and return false if cleanup was not confirmed. The service thread's `finally` finalizes the certificate, closes listener and coordinator, and sets a completion event. A service-thread close does not self-join. A later runtime `close(mutation_join_timeout=30.0)` can retry the mutation-worker join without crossing the certificate writer-lease boundary. `runtime.py` watchdog and finally callers were left intact. Hard OS/process termination was not claimed to perform graceful finalization.

## LOCK_RELEASE_FAILURE_SEMANTICS

CODE_PATH_PROVED: `ipc.py:1642-1686` marks release failure `release_unverified`, retains the pending certificate and mutation fence, and returns error with `resync_required=True`; it never returns `released=True`. Shutdown returns false when ownership remains pending or degraded. Initial verification cleanup failure also retains degraded state. The existing GUI at `C:\Temp\Contextor_Repo\contextor\ui\gui.py:1403-1427` clears only after status ok, released true, and exact certificate ID/generation match; an expired/unverified response therefore cannot clear its incident or bypass watcher rebaseline. Gate F public statuses, durable snapshot schema, revision policy, and persistence-first ordering were not changed.

## WATCHER_VERIFIED_REBASELINE

CODE_PATH_PROVED: `watcher.py:667-733` now fetches a LIVE snapshot before scanning; requires ok status, available state, positive integer matching response/state revision, nonempty state ID, modules dict, and trusted matching file-state materialization. It scans and computes pending paths against that verified generation, merging startup paths, pending intents, ambiguity, and tracked deletions before assigning `_snapshot`. Only after these steps does it clear `_recovery_rebaseline_pending`. Any failure returns with flag, old snapshot, pending paths/intents, ambiguity, and inflight tracking preserved, without submitting a mutation. Inflight reconciliation runs after successful rebaseline. Changes found by trusted file-state are queued even when the previous local scan already matches the filesystem.

## CONCURRENCY_TEST_RESULTS

New focused tests in `tests/test_recovery_authority_gate.py:419-694` verify service-thread completion/cancellation/expiry, foreign watchdog-style close, silent connected client shutdown, expired ack rejection, 30-second timer cancellation, duplicate ack, release-error degradation, service-thread shutdown, no process launch, and N+1 after release. Completion-vs-expiry and cancellation-vs-expiry use a `threading.Barrier` to send concurrent ack/wake requests; the service thread releases exactly once. The disconnected-client expiry test was repeated 20 consecutive times after repairing the early-wakeup race: 20/20 passed. Tests in `tests/test_watcher_recovery_admission.py:256-322` cover read failure, malformed state, stale revision, missing identity, missing trusted materialization, retry, preserved pending/ambiguous/inflight work, and newly detected changes. Existing IPC transport stubs gained `poll` to match the real connection contract.

## TARGETED_TEST_RESULTS

Final focused command: `& .\.venv\Scripts\python.exe -m pytest -q tests\test_recovery_authority_gate.py tests\test_watcher_recovery_admission.py tests\test_live_state_ipc.py tests\test_live_mutation_coordinator.py tests\test_durable_verified_publish.py tests\test_gui_live_startup.py tests\test_live_watcher_startup_reconciliation.py` — **233 passed, 1 external AuthlibDeprecationWarning, 0 failed** (82.81 s). This includes existing durable publish, memory-only IPC, persistence-first mutation, and GUI recovery-generation regressions. Earlier focused attempts exposed an early-wakeup expiry race and outdated IPC test doubles; both were corrected, then the final command passed. `git diff --check` passed. No full repository pytest suite was run.

## LIVE_WATCHER_VERIFICATION

Contextor `get_live_events(after_revision=70)` showed continuous `desktop_watcher` updates through revision 102 for the changed source/test files, with `resync_required=false`. Subsequent Contextor symbol previews for the finalizer and new expiry regression reported `workspace_sync=verified` at canonical revision 102. No manual `update_file` was called. The running Desktop/LIVE/MCP processes were not restarted, so this is source freshness and watcher progression, not execution certification of the newly edited server code in the pre-existing runtime process.

## UNRESOLVED_RISKS

- The one-shot authenticated wake depends on a responsive local IPC service. Hard termination or an indefinitely blocked unrelated service handler cannot be certified to release a process-held writer lease at exactly 30 seconds; the deadline still rejects later completion. These are outside the responsive-service tests and are not classified as healthy cleanup.
- No production Desktop/LIVE reload was authorized. The focused tests exercise new code in fresh test servers; existing running service behavior was not recertified.
- The current successful N+1 test proves ordinary post-certificate advancement with a test persister; durable matching and persistence-first behavior are covered by the existing focused durable-publish and mutation regressions, not by a new end-to-end process-death test.

## IMPLEMENTATION_VERDICT

FOCUSED_IMPLEMENTATION_PASS for the auditor-defined responsive-service lifecycle and watcher rebaseline. The unresolved runtime and hard-termination limits above remain explicit; no global certification is claimed.

## FULL_DIFFS

The following fenced block is the complete actual `git diff --no-ext-diff` for every changed source/test file, relative to PRE_EDIT_HEAD. It is written directly from Git without excerpting.

```diff
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 60c8ec2..5f08eaf 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -94,6 +94,8 @@ ACTIVITY_EVENT_RETENTION = 10_000
 _DIAGNOSTIC_JOURNAL_LIMIT = 3
 _MUTATION_JOB_RETENTION = 256
 _MUTATION_WORKER_JOIN_TIMEOUT = 2.0
+_RECOVERY_CERTIFICATE_VALIDITY_SECONDS = 30.0
+_RECOVERY_SHUTDOWN_WAIT_SECONDS = 5.0
 
 
 _MISSING_REVISION = object()
@@ -804,6 +806,16 @@ class CanonicalLiveServer:
         self._repository_identity_reader = repository_identity_reader
         self._recovery_verification_context = None
         self._pending_recovery_certificate: dict[str, Any] | None = None
+        self._recovery_certificate_deadline: float | None = None
+        self._recovery_certificate_owner: int | None = None
+        self._recovery_certificate_wakeup: threading.Timer | None = None
+        self._recovery_certificate_state = "none"
+        self._last_expired_recovery_certificate: tuple[str, int] | None = None
+        self._recovery_release_degraded = False
+        self._service_thread_identity: int | None = None
+        self._service_finished = threading.Event()
+        self._service_cleanup_ok = True
+        self._service_wakeup_token = secrets.token_hex(32)
         self._mutation_coordinator = CanonicalMutationCoordinator(
             self._execute_queued_update_file,
             self._read_revision,
@@ -1178,6 +1190,40 @@ class CanonicalLiveServer:
         }
 
     def serve_forever(self) -> None:
+        self._service_thread_identity = threading.get_ident()
+        self._service_finished.clear()
+        try:
+            self._serve_requests()
+        finally:
+            try:
+                if self._pending_recovery_certificate is not None:
+                    self._finalize_recovery_certificate(
+                        reason="shutdown",
+                        certificate_id=self._pending_recovery_certificate["certificate_id"],
+                        generation=self._pending_recovery_certificate["incident_generation"],
+                    )
+                    if self._pending_recovery_certificate is not None:
+                        self._service_cleanup_ok = False
+            except Exception:
+                self._service_cleanup_ok = False
+            finally:
+                self._stop.set()
+                try:
+                    self._listener.close()
+                except OSError:
+                    pass
+                try:
+                    worker_closed = self._mutation_coordinator.close()
+                except Exception:
+                    worker_closed = False
+                self._service_cleanup_ok = (
+                    worker_closed
+                    and self._service_cleanup_ok
+                    and not self._recovery_release_degraded
+                )
+                self._service_finished.set()
+
+    def _serve_requests(self) -> None:
         while not self._stop.is_set():
             accept_started = time.monotonic()
             try:
@@ -1198,6 +1244,12 @@ class CanonicalLiveServer:
             request_started = time.monotonic()
             try:
                 try:
+                    while not connection.poll(0.25):
+                        self._expire_recovery_certificate()
+                        if self._stop.is_set():
+                            break
+                    if self._stop.is_set():
+                        continue
                     request = connection.recv()
                 except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
                     _safe_trace_event(
@@ -1216,6 +1268,7 @@ class CanonicalLiveServer:
                 if isinstance(request, dict) and isinstance(request.get("operation"), str):
                     request_type = request["operation"]
                 try:
+                    self._expire_recovery_certificate()
                     response = self._dispatch(request)
                 except Exception as exc:
                     try:
@@ -1522,9 +1575,123 @@ class CanonicalLiveServer:
                 _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
 
+    def _wake_service(self) -> None:
+        try:
+            connection = Client(
+                self.endpoint.address, family="AF_INET", authkey=self._authkey
+            )
+            try:
+                connection.send({
+                    "operation": "_recovery_lifecycle_wake",
+                    "token": self._service_wakeup_token,
+                })
+            finally:
+                connection.close()
+        except (OSError, EOFError, ConnectionError):
+            pass
+
+    def _cancel_recovery_wakeup(self) -> None:
+        wakeup = self._recovery_certificate_wakeup
+        self._recovery_certificate_wakeup = None
+        if wakeup is not None:
+            wakeup.cancel()
+
+    def _expire_recovery_certificate(self) -> None:
+        pending = self._pending_recovery_certificate
+        deadline = self._recovery_certificate_deadline
+        if (
+            pending is not None
+            and self._recovery_certificate_state == "pending"
+            and deadline is not None
+            and time.monotonic() >= deadline
+        ):
+            self._finalize_recovery_certificate(
+                reason="expired",
+                certificate_id=pending["certificate_id"],
+                generation=pending["incident_generation"],
+            )
+
+    def _finalize_recovery_certificate(
+        self, *, reason: str, certificate_id: Any, generation: Any
+    ) -> dict[str, Any]:
+        pending = self._pending_recovery_certificate
+        if (
+            not isinstance(pending, dict)
+            or not isinstance(certificate_id, str)
+            or isinstance(generation, bool)
+            or not isinstance(generation, int)
+            or pending.get("certificate_id") != certificate_id
+            or pending.get("incident_generation") != generation
+        ):
+            if (
+                reason == "complete"
+                and (certificate_id, generation)
+                == self._last_expired_recovery_certificate
+            ):
+                return {"status": "error", "error": "recovery_certificate_expired"}
+            return {"status": "error", "error": "recovery_certificate_mismatch"}
+        if (
+            self._recovery_certificate_owner != threading.get_ident()
+            or (
+                self._service_thread_identity is not None
+                and self._service_thread_identity != threading.get_ident()
+            )
+        ):
+            return {"status": "error", "error": "recovery_owner_thread_mismatch"}
+        if self._recovery_release_degraded:
+            return {"status": "error", "error": "recovery_writer_release_unverified"}
+        if self._recovery_certificate_state != "pending":
+            return {"status": "error", "error": "recovery_finalization_unavailable"}
+        deadline = self._recovery_certificate_deadline
+        expired = deadline is not None and time.monotonic() >= deadline
+        if reason == "expired" and not expired:
+            return {"status": "error", "error": "recovery_certificate_not_expired"}
+        if expired:
+            reason = "expired"
+        guard_context = self._recovery_verification_context
+        if guard_context is None:
+            self._recovery_release_degraded = True
+            self._recovery_certificate_state = "release_unverified"
+            return {"status": "error", "error": "recovery_fence_missing"}
+        self._cancel_recovery_wakeup()
+        self._recovery_certificate_state = "finalizing"
+        try:
+            guard_context.__exit__(None, None, None)
+        except Exception:
+            self._recovery_release_degraded = True
+            self._recovery_certificate_state = "release_unverified"
+            return {
+                "status": "error",
+                "error": "recovery_writer_release_failed",
+                "resync_required": True,
+            }
+        self._recovery_verification_context = None
+        self._pending_recovery_certificate = None
+        self._recovery_certificate_deadline = None
+        self._recovery_certificate_owner = None
+        self._mutation_coordinator.end_recovery_verification()
+        self._recovery_certificate_state = reason
+        if reason == "expired":
+            self._last_expired_recovery_certificate = (
+                certificate_id, generation
+            )
+            return {"status": "error", "error": "recovery_certificate_expired"}
+        return {
+            "status": "ok",
+            "released": True,
+            "cancelled": reason != "complete",
+            "certificate_id": certificate_id,
+            "incident_generation": generation,
+        }
+
     def _execute_recovery_verification(
         self, request: dict[str, Any]
     ) -> dict[str, Any]:
+        if (
+            self._service_thread_identity is not None
+            and threading.get_ident() != self._service_thread_identity
+        ):
+            return {"status": "error", "error": "recovery_owner_thread_mismatch"}
         generation = request.get("incident_generation")
         if (
             isinstance(generation, bool)
@@ -1636,6 +1803,27 @@ class CanonicalLiveServer:
             }
             self._pending_recovery_certificate = certificate
             self._recovery_verification_context = guard_context
+            self._recovery_certificate_owner = threading.get_ident()
+            self._recovery_certificate_state = "pending"
+            self._recovery_certificate_deadline = (
+                time.monotonic() + _RECOVERY_CERTIFICATE_VALIDITY_SECONDS
+            )
+            wakeup = threading.Timer(
+                _RECOVERY_CERTIFICATE_VALIDITY_SECONDS, self._wake_service
+            )
+            wakeup.daemon = True
+            self._recovery_certificate_wakeup = wakeup
+            try:
+                wakeup.start()
+            except Exception:
+                self._cancel_recovery_wakeup()
+                self._pending_recovery_certificate = None
+                self._recovery_verification_context = None
+                self._recovery_certificate_deadline = None
+                self._recovery_certificate_owner = None
+                self._recovery_certificate_state = "none"
+                guard_entered = True
+                raise
             guard_entered = False
             retain_fence = True
             return {
@@ -1652,41 +1840,18 @@ class CanonicalLiveServer:
                         guard_released = False
                 if guard_released:
                     self._mutation_coordinator.end_recovery_verification()
+                else:
+                    self._recovery_release_degraded = True
+                    self._recovery_certificate_state = "release_unverified"
 
     def _finish_recovery_verification(
         self, request: dict[str, Any], *, cancelled: bool
     ) -> dict[str, Any]:
-        certificate_id = request.get("certificate_id")
-        generation = request.get("incident_generation")
-        pending = self._pending_recovery_certificate
-        if (
-            not isinstance(pending, dict)
-            or not isinstance(certificate_id, str)
-            or isinstance(generation, bool)
-            or not isinstance(generation, int)
-            or pending.get("certificate_id") != certificate_id
-            or generation != pending.get("incident_generation")
-        ):
-            return {"status": "error", "error": "recovery_certificate_mismatch"}
-
-        guard_context = self._recovery_verification_context
-        if guard_context is None:
-            return {"status": "error", "error": "recovery_fence_missing"}
-        try:
-            guard_context.__exit__(None, None, None)
-        except Exception:
-            return {"status": "error", "error": "recovery_writer_release_failed"}
-
-        self._recovery_verification_context = None
-        self._pending_recovery_certificate = None
-        self._mutation_coordinator.end_recovery_verification()
-        return {
-            "status": "ok",
-            "released": True,
-            "cancelled": cancelled,
-            "certificate_id": certificate_id,
-            "incident_generation": generation,
-        }
+        return self._finalize_recovery_certificate(
+            reason="cancel" if cancelled else "complete",
+            certificate_id=request.get("certificate_id"),
+            generation=request.get("incident_generation"),
+        )
 
     def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
         trace_op = _safe_trace_op(request, "u")
@@ -1967,6 +2132,16 @@ class CanonicalLiveServer:
         if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
             return {"status": "error", "error": "invalid_request"}
         operation = request["operation"]
+        if operation == "_recovery_lifecycle_wake":
+            if request.get("token") != self._service_wakeup_token:
+                return {"status": "error", "error": "invalid_lifecycle_wake"}
+            deadline = self._recovery_certificate_deadline
+            if deadline is not None and not self._stop.is_set():
+                remaining = deadline - time.monotonic()
+                if remaining > 0:
+                    self._stop.wait(remaining)
+            self._expire_recovery_certificate()
+            return {"status": "ok"}
 
         # Desktop authority callbacks cross the RuntimeLease/observability
         # boundary and may synchronously emit back into record_authority_event.
@@ -2201,21 +2376,55 @@ class CanonicalLiveServer:
     def close(
         self, *, mutation_join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT
     ) -> bool:
-        pending = self._pending_recovery_certificate
-        if isinstance(pending, dict):
-            self._finish_recovery_verification(
-                {
-                    "certificate_id": pending.get("certificate_id"),
-                    "incident_generation": pending.get("incident_generation"),
-                },
-                cancelled=True,
-            )
         self._stop.set()
-        try:
-            self._listener.close()
-        except OSError:
-            pass
-        return self._mutation_coordinator.close(join_timeout=mutation_join_timeout)
+        if self._service_thread_identity is None:
+            if self._pending_recovery_certificate is not None:
+                if self._recovery_certificate_owner != threading.get_ident():
+                    return False
+                pending = self._pending_recovery_certificate
+                self._finalize_recovery_certificate(
+                    reason="shutdown",
+                    certificate_id=pending["certificate_id"],
+                    generation=pending["incident_generation"],
+                )
+                if self._pending_recovery_certificate is not None:
+                    return False
+            try:
+                self._listener.close()
+            except OSError:
+                pass
+            return self._mutation_coordinator.close(
+                join_timeout=mutation_join_timeout
+            )
+        if threading.get_ident() == self._service_thread_identity:
+            # Never join the service thread from itself. The loop's finally
+            # block closes the listener and mutation coordinator.
+            if self._pending_recovery_certificate is not None:
+                pending = self._pending_recovery_certificate
+                self._finalize_recovery_certificate(
+                    reason="shutdown",
+                    certificate_id=pending["certificate_id"],
+                    generation=pending["incident_generation"],
+                )
+                return self._pending_recovery_certificate is None
+            return not self._recovery_release_degraded
+        threading.Thread(
+            target=self._wake_service,
+            name="contextor-live-shutdown-wake",
+            daemon=True,
+        ).start()
+        if not self._service_finished.wait(_RECOVERY_SHUTDOWN_WAIT_SECONDS):
+            return False
+        # The owner thread already closed admission. A later runtime finally
+        # may allow a longer join for a mutation worker still draining.
+        worker_closed = self._mutation_coordinator.close(
+            join_timeout=mutation_join_timeout
+        )
+        return (
+            worker_closed
+            and self._pending_recovery_certificate is None
+            and not self._recovery_release_degraded
+        )
 
     def __enter__(self) -> "CanonicalLiveServer":
         return self
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 052c723..5d24349 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -665,24 +665,55 @@ class DesktopLiveWatcher:
         return completed
 
     def poll_once(self) -> list[str]:
-        reconciled = self._poll_inflight_updates()
-        if self._recovery_is_active():
-            return reconciled
         if self._recovery_rebaseline_pending:
-            current_scan = self._scan()
+            if self._recovery_is_active():
+                return []
+            try:
+                live_snapshot = self.client.snapshot()
+                if not isinstance(live_snapshot, dict) or live_snapshot.get("status") != "ok":
+                    return []
+                state = live_snapshot.get("state")
+                revision = live_snapshot.get("revision")
+                state_id = getattr(state, "state_id", None)
+                modules = getattr(state, "modules", None)
+                if (
+                    isinstance(revision, bool)
+                    or not isinstance(revision, int)
+                    or revision < 1
+                    or getattr(state, "revision", None) != revision
+                    or not isinstance(state_id, str)
+                    or not state_id
+                    or not isinstance(modules, dict)
+                ):
+                    return []
+                manager = self._trusted_file_state(live_snapshot)
+                if manager is None:
+                    return []
+                current_scan = self._scan()
+                pending = set(self._startup_pending)
+                pending.update(self._pending_intents)
+                pending.update(self._ambiguous_updates)
+                pending.update(
+                    path for path in current_scan
+                    if manager.has_changed(path)
+                    or self._module_name(Path(path)) not in modules
+                )
+                for tracked_path in manager.tracked_paths():
+                    normalized = self._normalize_watch_path(tracked_path)
+                    if normalized is not None and normalized not in current_scan:
+                        pending.add(normalized)
+            except Exception:
+                return []
+            # Every path above was compared with the verified LIVE generation.
+            # Commit the local scan only after preserving all outstanding work.
             self._snapshot = current_scan
-            previous_startup_pending = set(self._startup_pending)
-            reconciled_startup_pending = self._startup_reconciliation_paths(
-                current_scan
-            )
-            if self._startup_requires_resync:
-                previous_startup_pending.update(reconciled_startup_pending)
-                self._startup_pending = sorted(previous_startup_pending)
-            else:
-                self._startup_pending = reconciled_startup_pending
+            self._startup_pending = sorted(pending)
             for pending_path in self._startup_pending:
                 self._enqueue_path(pending_path, wake=False)
             self._recovery_rebaseline_pending = False
+        reconciled = self._poll_inflight_updates()
+        if self._recovery_is_active():
+            return reconciled
         changed = self._drain_pending()
         using_startup_pending = not changed and bool(self._startup_pending)
         if using_startup_pending:
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index efb1b05..6a47ec6 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -388,6 +388,7 @@ def test_server_dispatch_transport_shaped_error_is_not_ipc_failure(monkeypatch,
     events, sent = [], []
     server = CanonicalLiveServer(SimpleNamespace(files=[]))
     class Connection:
+        def poll(self, _timeout): return True
         def recv(self): return {"operation": "ping"}
         def send(self, value): sent.append(value)
         def close(self): server._stop.set()
@@ -408,6 +409,7 @@ def test_server_transport_boundary_emits_once(monkeypatch, stage):
     server = CanonicalLiveServer(SimpleNamespace(files=[]))
     class Connection:
         closed = False
+        def poll(self, _timeout): return True
         def recv(self):
             if stage == "recv": raise ConnectionResetError("recv")
             return {"operation": "ping"}
@@ -451,6 +453,7 @@ def test_server_recv_and_send_trace_emitter_failure_are_fail_open(monkeypatch, s
 
     class Connection:
         closed = False
+        def poll(self, _timeout): return True
 
         def recv(self):
             if stage == "recv":
diff --git a/tests/test_recovery_authority_gate.py b/tests/test_recovery_authority_gate.py
index 4dd7131..18c7c66 100644
--- a/tests/test_recovery_authority_gate.py
+++ b/tests/test_recovery_authority_gate.py
@@ -1,10 +1,13 @@
 from contextlib import contextmanager
+import multiprocessing
+from multiprocessing.connection import Client
 import threading
 from types import SimpleNamespace
 
 import pytest
 
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
+import contextor.core.live_state.ipc as live_ipc
 
 
 def _recovery_server(
@@ -147,6 +150,9 @@ def test_concurrent_publish_cannot_cross_recovery_fence(tmp_path):
     recovery_fence_started = threading.Event()
     publish_result = {}
     verify_result = {}
+    finish_result = {}
+    verified = threading.Event()
+    allow_finish = threading.Event()
     original_active = server._mutation_coordinator.recovery_verification_active
     original_begin = server._mutation_coordinator.begin_recovery_verification
 
@@ -179,6 +185,9 @@ def test_concurrent_publish_cannot_cross_recovery_fence(tmp_path):
 
     def verify():
         verify_result.update(_verify(server))
+        verified.set()
+        if allow_finish.wait(2) and verify_result.get("status") == "ok":
+            finish_result.update(_finish(server, verify_result["certificate"]))
 
     publish_thread = threading.Thread(target=publish, name="racing-publish")
     verify_thread = threading.Thread(target=verify, name="recovery-verification")
@@ -196,16 +205,19 @@ def test_concurrent_publish_cannot_cross_recovery_fence(tmp_path):
             execution_lock_held = False
 
         publish_thread.join(2)
-        verify_thread.join(2)
+        assert verified.wait(2)
         assert not publish_thread.is_alive()
-        assert not verify_thread.is_alive()
         assert verify_result["status"] == "ok"
         assert publish_result["status"] == "error"
         assert publish_result["error"] == "recovery_verification_in_progress"
         assert server._revision == 1
         assert server._mutation_coordinator.recovery_verification_active()
-        assert _finish(server, verify_result["certificate"])["released"] is True
+        allow_finish.set()
+        verify_thread.join(2)
+        assert not verify_thread.is_alive()
+        assert finish_result["released"] is True
     finally:
+        allow_finish.set()
         if execution_lock_held:
             execution_lock.release()
         if publish_thread.ident is not None:
@@ -401,3 +413,278 @@ def test_recovery_verification_and_ack_round_trip_through_live_ipc(tmp_path):
     finally:
         server.close()
         thread.join(2)
+
+
+@pytest.mark.parametrize("operation", ["complete", "cancel"])
+def test_certificate_finalization_stays_on_service_thread(tmp_path, operation):
+    server = _recovery_server(tmp_path)
+    owner_threads = []
+    release_threads = []
+
+    @contextmanager
+    def guarded():
+        owner_threads.append(threading.get_ident())
+        try:
+            yield
+        finally:
+            release_threads.append(threading.get_ident())
+
+    server._recovery_verification_guard = guarded
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(7)["certificate"]
+        if operation == "complete":
+            result = client.complete_recovery_verification(certificate["certificate_id"], 7)
+        else:
+            result = client.cancel_recovery_verification(certificate["certificate_id"], 7)
+        assert result["released"] is True
+        assert owner_threads == release_threads == [thread.ident]
+        duplicate = client.complete_recovery_verification(certificate["certificate_id"], 7)
+        assert duplicate["status"] == "error"
+        assert release_threads == [thread.ident]
+    finally:
+        assert server.close()
+        thread.join(2)
+        assert not thread.is_alive()
+
+
+def test_disconnected_certificate_expires_on_owner_thread(tmp_path, monkeypatch):
+    monkeypatch.setattr(live_ipc, "_RECOVERY_CERTIFICATE_VALIDITY_SECONDS", 0.05)
+    server = _recovery_server(tmp_path)
+    entered = threading.Event()
+    exited = threading.Event()
+    threads = []
+
+    @contextmanager
+    def guarded():
+        threads.append(threading.get_ident())
+        entered.set()
+        try:
+            yield
+        finally:
+            threads.append(threading.get_ident())
+            exited.set()
+
+    server._recovery_verification_guard = guarded
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(8)["certificate"]
+        assert entered.wait(2)
+        # request() has already closed the original connection.
+        assert exited.wait(2)
+        assert threads == [thread.ident, thread.ident]
+        rejected = client.complete_recovery_verification(certificate["certificate_id"], 8)
+        assert rejected == {"status": "error", "error": "recovery_certificate_expired"}
+        assert not server._mutation_coordinator.recovery_verification_active()
+    finally:
+        assert server.close()
+        thread.join(2)
+
+
+def test_foreign_thread_close_wakes_service_and_releases_on_owner(tmp_path):
+    server = _recovery_server(tmp_path)
+    exited = threading.Event()
+    exit_threads = []
+
+    @contextmanager
+    def guarded():
+        try:
+            yield
+        finally:
+            exit_threads.append(threading.get_ident())
+            exited.set()
+
+    server._recovery_verification_guard = guarded
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.verify_recovery(9)
+    close_result = []
+    watchdog = threading.Thread(
+        target=lambda: close_result.append(server.close()),
+        name="contextor-live-watchdog-test",
+    )
+    watchdog.start()
+    watchdog.join(2)
+    assert not watchdog.is_alive()
+    assert close_result == [True]
+    assert exited.wait(2)
+    thread.join(2)
+    assert not thread.is_alive()
+    assert exit_threads == [thread.ident]
+
+
+def test_foreign_close_interrupts_client_that_never_sends_request(tmp_path):
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.verify_recovery(15)
+    silent_connection = Client(
+        server.endpoint.address, family="AF_INET", authkey=server.endpoint.authkey
+    )
+    try:
+        assert server.close()
+        thread.join(2)
+        assert not thread.is_alive()
+        assert server._test_guard_exited == [True]
+    finally:
+        silent_connection.close()
+
+
+def test_release_failure_never_reopens_mutation_fence(tmp_path):
+    server = _recovery_server(tmp_path)
+
+    @contextmanager
+    def failing_guard():
+        yield
+        raise OSError("injected unlock failure")
+
+    server._recovery_verification_guard = failing_guard
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    certificate = client.verify_recovery(10)["certificate"]
+    result = client.complete_recovery_verification(certificate["certificate_id"], 10)
+    assert result["status"] == "error"
+    assert result["error"] == "recovery_writer_release_failed"
+    assert result.get("released") is not True
+    assert server._mutation_coordinator.recovery_verification_active()
+    assert server._recovery_certificate_state == "release_unverified"
+    assert not server.close()
+    thread.join(2)
+    assert not thread.is_alive()
+
+
+def test_service_thread_shutdown_finalizes_without_self_join(tmp_path):
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.verify_recovery(11)
+    response = client.request("shutdown")
+    assert response["status"] == "ok"
+    thread.join(2)
+    assert not thread.is_alive()
+    assert server._test_guard_exited == [True]
+    assert server._service_cleanup_ok
+    assert not server._mutation_coordinator.recovery_verification_active()
+
+
+@pytest.mark.parametrize("operation", ["complete", "cancel"])
+def test_expiry_competing_with_ack_releases_once(tmp_path, monkeypatch, operation):
+    monkeypatch.setattr(live_ipc, "_RECOVERY_CERTIFICATE_VALIDITY_SECONDS", 30.0)
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(12)["certificate"]
+        # Concurrent authenticated wake and ack requests meet at the service
+        # thread after the deadline; only that thread may release the guard.
+        server._recovery_certificate_deadline = live_ipc.time.monotonic() - 1
+        barrier = threading.Barrier(3)
+        response_holder = {}
+
+        def acknowledge():
+            barrier.wait(2)
+            if operation == "complete":
+                response_holder.update(
+                    client.complete_recovery_verification(certificate["certificate_id"], 12)
+                )
+            else:
+                response_holder.update(
+                    client.cancel_recovery_verification(certificate["certificate_id"], 12)
+                )
+
+        def wake():
+            barrier.wait(2)
+            server._wake_service()
+
+        ack_thread = threading.Thread(target=acknowledge)
+        wake_thread = threading.Thread(target=wake)
+        ack_thread.start()
+        wake_thread.start()
+        barrier.wait(2)
+        ack_thread.join(2)
+        wake_thread.join(2)
+        assert not ack_thread.is_alive()
+        assert not wake_thread.is_alive()
+        response = response_holder
+        assert response["status"] == "error"
+        assert server._test_guard_exited == [True]
+        assert not server._mutation_coordinator.recovery_verification_active()
+        assert server._recovery_certificate_wakeup is None
+        assert client.complete_recovery_verification(
+            certificate["certificate_id"], 12
+        )["status"] == "error"
+        assert server._test_guard_exited == [True]
+    finally:
+        assert server.close()
+        thread.join(2)
+
+
+def test_next_committed_update_after_certificate_release_is_normal(tmp_path):
+    server = _recovery_server(
+        tmp_path, updater=lambda _candidate, _path: SimpleNamespace(status="UPDATED")
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(13)["certificate"]
+        acknowledged = client.complete_recovery_verification(
+            certificate["certificate_id"], 13
+        )
+        assert acknowledged["released"] is True
+        updated = client.update_file(str(tmp_path / "change.py"))
+        assert updated["status"] == "ok"
+        assert updated["revision"] == certificate["revision"] + 1
+        assert server._test_persists == [True]
+        assert client.snapshot()["revision"] == updated["revision"]
+    finally:
+        assert server.close()
+        thread.join(2)
+
+
+def test_one_certificate_wakeup_is_cancelled_after_ack(tmp_path):
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(14)["certificate"]
+        wakeup = server._recovery_certificate_wakeup
+        assert isinstance(wakeup, threading.Timer)
+        assert wakeup.is_alive()
+        assert client.complete_recovery_verification(
+            certificate["certificate_id"], 14
+        )["released"] is True
+        assert server._recovery_certificate_wakeup is None
+        assert wakeup.finished.is_set()
+    finally:
+        assert server.close()
+        thread.join(2)
+
+
+def test_certificate_lifecycle_starts_no_process(tmp_path, monkeypatch):
+    def forbidden_start(_process):
+        pytest.fail("certificate lifecycle must not start a process")
+
+    monkeypatch.setattr(multiprocessing.process.BaseProcess, "start", forbidden_start)
+    server = _recovery_server(tmp_path)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        certificate = client.verify_recovery(16)["certificate"]
+        assert client.cancel_recovery_verification(
+            certificate["certificate_id"], 16
+        )["released"] is True
+    finally:
+        assert server.close()
+        thread.join(2)
diff --git a/tests/test_watcher_recovery_admission.py b/tests/test_watcher_recovery_admission.py
index d9f7a46..57a9686 100644
--- a/tests/test_watcher_recovery_admission.py
+++ b/tests/test_watcher_recovery_admission.py
@@ -15,6 +15,12 @@ from contextor.ui.gui import ContextorGUI
 
 
 class _Manager:
+    def has_changed(self, path):
+        return True
+
+    def tracked_paths(self):
+        return []
+
     def get_current_file_state(self, path, *, compute_hash):
         stat = Path(path).stat()
         return SimpleNamespace(
@@ -243,6 +249,77 @@ def test_recovery_release_rescans_and_revalidates_against_current_live(
     assert not watcher._recovery_rebaseline_pending
 
 
+@pytest.mark.parametrize(
+    "failure",
+    ["read_error", "malformed", "stale_revision", "identity_missing", "untrusted"],
+)
+def test_rebaseline_failure_preserves_work_and_retries(tmp_path, failure):
+    client = _Client()
+    watcher, source = _watcher(tmp_path, client)
+    path = str(source.resolve())
+    old_snapshot = dict(watcher._snapshot)
+    intent = _PendingMutationIntent(
+        "intent-1", path, "trace-1", (1, 1), 1.0, "sha"
+    )
+    job = _WatcherMutationJob(
+        "job-1", path, "trace-1", "intent-1", (1, 1), 1.0, "sha"
+    )
+    watcher._pending_intents[path] = intent
+    watcher._ambiguous_updates.add(path)
+    watcher._startup_pending = [path]
+    watcher._inflight_updates[job.job_id] = job
+    watcher._enqueue_path(path)
+    watcher.complete_recovery_certificate()
+    healthy_snapshot = client.snapshot
+
+    def failed_snapshot():
+        if failure == "read_error":
+            raise ConnectionError("snapshot unavailable")
+        response = healthy_snapshot()
+        if failure == "malformed":
+            return {"status": "ok", "revision": client.revision, "state": None}
+        if failure == "stale_revision":
+            response["state"].revision -= 1
+        if failure == "identity_missing":
+            response["state"].state_id = ""
+        return response
+
+    client.snapshot = failed_snapshot
+    if failure == "untrusted":
+        watcher._trusted_file_state = lambda _snapshot=None: None
+    assert watcher.poll_once() == []
+    assert watcher._recovery_rebaseline_pending
+    assert watcher._snapshot == old_snapshot
+    assert watcher._startup_pending == [path]
+    assert watcher._pending_intents[path] is intent
+    assert path in watcher._ambiguous_updates
+    assert watcher._inflight_updates[job.job_id] is job
+    assert list(watcher._pending_paths) == [path]
+    assert client.submissions == []
+    assert client.mutation_status_calls == []
+
+    client.snapshot = healthy_snapshot
+    watcher._trusted_file_state = lambda _snapshot=None: _Manager()
+    watcher.poll_once()
+    assert not watcher._recovery_rebaseline_pending
+    assert client.mutation_status_calls
+    assert set(client.mutation_status_calls) == {job.job_id}
+
+
+def test_rebaseline_queues_change_even_when_old_scan_looks_current(tmp_path):
+    client = _Client()
+    watcher, source = _watcher(tmp_path, client)
+    path = str(source.resolve())
+    watcher._snapshot = watcher._scan()
+    watcher.complete_recovery_certificate()
+
+    watcher.poll_once()
+
+    assert not watcher._recovery_rebaseline_pending
+    assert client.submissions
+    assert client.submissions[0][0] == path
+
+
 def test_gui_admission_serializes_registration_with_submission():
     submission_entered = threading.Event()
     registration_waiting = threading.Event()
```

ACTUAL_DIFF=FULL_DIFFS above; production and test edits are exactly the five files listed in FILES_CHANGED.
