# C38E2Q R1 Admission Recovery Hardening

TASK=CONTEXTOR_C38E2Q_R1_ADMISSION_RECOVERY_HARDENING
IMPLEMENTATION_RESULT=Canonical publication keys are enforced by the server; lost admission response recovery uses read-only lookup in the existing coordinator.
HEAD_BEFORE=95a59b1b6ab2f6961f425a2ab7d6f79ea2f4d12c
HEAD_AFTER=95a59b1b6ab2f6961f425a2ab7d6f79ea2f4d12c
CANONICAL_KEY_ENFORCEMENT=Server obtains repo_id from authoritative repository identity, recomputes committed_publication_key(repo_id,state_id,revision), and rejects different keys with invalid_publication_idempotency_key before coordinator admission. update_file key behavior is unchanged.
LOST_ADMISSION_RECOVERY=After both admission responses are lost, the client queries lookup_committed_publish by the deterministic key. Status reconciliation performs the same read-only lookup when the durable job_id is absent, persists a recovered ID, and retains pending_verification for running, unknown, or evicted jobs.
EXACT_RECEIPT_CORRELATION=Lookup validates exact repo_id/state_id/revision and operation under the coordinator condition lock, then reuses existing job status serialization. Reconciliation verifies endpoint and authority service/process identities plus the stored key against authority repo_id. Shared classifier requires the exact job receipt and generation; it does not use revision-only success.
LEGACY_COMPATIBILITY=Existing coordinator queue, worker, terminal status, and retention are reused. No second queue/process was added. update_file and synchronous publish paths are unchanged. Older durable jobs without the new key are not looked up or promoted.
TARGETED_TEST_RESULTS=Final named selection command: pytest -q tests/test_live_mutation_coordinator.py tests/test_durable_verified_publish.py tests/test_live_state_ipc.py tests/mcp/tools/test_analysis_status_concurrency.py tests/test_full_analysis_coordination.py tests/test_async_publication_receipt.py. Result: 230 passed, 1 failed in 136.52s. The sole failure was test_normal_service_shutdown_preserves_authority_event_chronology at runtime_domain.py::_validate_root_relationships with RuntimeDomainError: lock_root must be owned by cache_root. Its isolated rerun passed (1 passed in 2.49s). Focused R1 subset passed 14 tests; py_compile passed; MCP JSON documentation parsed. No full repository pytest, production FULL, update_file, restart, or Git mutation was performed.
WATCHER_EVENTS=DIRECT_EVIDENCE: revisions 590-602, origin desktop_watcher, continuous, resync_required=false. Production changes: ipc.py 590 UPDATED; publication_receipt.py 591 UPDATED/594 UNCHANGED; facade.py 592 UPDATED; analysis_jobs.py 593 UPDATED; get_analysis_status.py 595 UPDATED. Tests: durable_verified_publish.py 597 UPDATED; async_publication_receipt.py 598 UPDATED/600 UNCHANGED; test_analysis_status_concurrency.py 599 UPDATED/601-602 UNCHANGED. No update_file MCP calls.
WORKSPACE_SYNC=DIRECT_EVIDENCE: Contextor reports workspace_sync=verified and syntax_diagnostics checked_and_none for all five changed production Python files at canonical revision 602. Test modules had watcher updates; some later blast-radius states are deferred. No resync required.
LIVE_REVISION_BEFORE_AFTER=589 -> 602
MCP_BACKEND_RESTART_REQUIRED=YES
LIVE_SERVICE_RESTART_REQUIRED=YES
RESTARTS_PERFORMED=NO
FINAL_VERDICT=C38E2Q_R1_SOURCE_PASS_PENDING_RUNTIME
NEXT_STEP=Await manual backend/service reload and user instruction: proceduj.

FILES_CHANGED
C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
C:\Temp\Contextor_Repo\contextor\core\live_state\publication_receipt.py
C:\Temp\Contextor_Repo\contextor\core\api\facade.py
C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py
C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json
C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py
C:\Temp\Contextor_Repo\tests\test_async_publication_receipt.py
C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py

FULL_DIFFS

## C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
```diff
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -276,25 +276,58 @@
                     "error": "unknown_mutation_job",
                     "job_id": job_id,
                 }
-            response: dict[str, Any] = {
-                "status": "ok",
-                "job_id": job.job_id,
-                "queue_order": job.queue_order,
-                "accepted_revision": job.accepted_revision,
-                "state": job.state,
-            }
-            if job.started_revision is not None:
-                response["started_revision"] = job.started_revision
-            if job.final_revision is not None:
-                response["final_revision"] = job.final_revision
-            if job.error is not None:
-                response["error"] = job.error
-            if job.response is not None:
-                response["response"] = copy.deepcopy(job.response)
-            if job.request.get("operation") == "submit_committed_publish":
-                response["requested_state_id"] = job.request["state_id"]
-                response["requested_revision"] = job.request["revision"]
-            return response
+            return self._serialize_status_locked(job)
+
+    @staticmethod
+    def _serialize_status_locked(job: _MutationJob) -> dict[str, Any]:
+        response: dict[str, Any] = {
+            "status": "ok",
+            "job_id": job.job_id,
+            "queue_order": job.queue_order,
+            "accepted_revision": job.accepted_revision,
+            "state": job.state,
+        }
+        if job.started_revision is not None:
+            response["started_revision"] = job.started_revision
+        if job.final_revision is not None:
+            response["final_revision"] = job.final_revision
+        if job.error is not None:
+            response["error"] = job.error
+        if job.response is not None:
+            response["response"] = copy.deepcopy(job.response)
+        if job.request.get("operation") == "submit_committed_publish":
+            response["requested_state_id"] = job.request["state_id"]
+            response["requested_revision"] = job.request["revision"]
+        return response
+
+    def lookup_committed_publish(
+        self,
+        *,
+        idempotency_key: str,
+        repo_id: str,
+        state_id: str,
+        revision: int,
+    ) -> dict[str, Any]:
+        if (
+            not isinstance(idempotency_key, str) or not idempotency_key
+            or not isinstance(repo_id, str) or not repo_id
+            or not isinstance(state_id, str) or not state_id
+            or type(revision) is not int or revision < 1
+        ):
+            return {"status": "error", "error": "unknown_publication_job"}
+        with self._condition:
+            job_id = self._idempotency_jobs.get(idempotency_key)
+            job = self._jobs.get(job_id) if job_id is not None else None
+            if (
+                job is None
+                or job.request.get("operation") != "submit_committed_publish"
+                or job.request.get("repo_id") != repo_id
+                or job.request.get("state_id") != state_id
+                or type(job.request.get("revision")) is not int
+                or job.request.get("revision") != revision
+            ):
+                return {"status": "error", "error": "unknown_publication_job"}
+            return self._serialize_status_locked(job)
 
     def _prune_terminal_locked(self) -> None:
         terminal = {"completed", "failed", "cancelled"}
@@ -1957,7 +1990,39 @@
         repo_id = getattr(identity, "repo_id", None)
         if not isinstance(repo_id, str) or not repo_id:
             return {"status": "error", "error": "repository_identity_unavailable"}
+        from contextor.core.live_state.publication_receipt import committed_publication_key
+        if key != committed_publication_key(repo_id, state_id, revision):
+            return {"status": "error", "error": "invalid_publication_idempotency_key"}
         return self._mutation_coordinator.submit({**request, "repo_id": repo_id})
+
+    def _lookup_committed_publish(self, request: dict[str, Any]) -> dict[str, Any]:
+        if set(request) != {"operation", "idempotency_key", "state_id", "revision"}:
+            return {"status": "error", "error": "invalid_committed_publish_lookup"}
+        key = request["idempotency_key"]
+        state_id = request["state_id"]
+        revision = request["revision"]
+        if not isinstance(key, str) or not key or len(key) > 256:
+            return {"status": "error", "error": "invalid_idempotency_key"}
+        if not isinstance(state_id, str) or not state_id or len(state_id) > 256:
+            return {"status": "error", "error": "invalid_state_id"}
+        if type(revision) is not int or revision < 1:
+            return {"status": "error", "error": "invalid_canonical_revision"}
+        if self._repository_identity_reader is None:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        try:
+            identity = self._repository_identity_reader()
+        except Exception:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        repo_id = getattr(identity, "repo_id", None)
+        if not isinstance(repo_id, str) or not repo_id:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        from contextor.core.live_state.publication_receipt import committed_publication_key
+        if key != committed_publication_key(repo_id, state_id, revision):
+            return {"status": "error", "error": "invalid_publication_idempotency_key"}
+        return self._mutation_coordinator.lookup_committed_publish(
+            idempotency_key=key, repo_id=repo_id, state_id=state_id,
+            revision=revision,
+        )
 
     def _execute_update_file(
         self, request: dict[str, Any], *, allow_recovery_fence: bool = False
@@ -2252,6 +2317,8 @@
             return self._mutation_coordinator.submit(request)
         if operation == "submit_committed_publish":
             return self._submit_committed_publish(request)
+        if operation == "lookup_committed_publish":
+            return self._lookup_committed_publish(request)
         if operation == "mutation_status":
             return self._mutation_coordinator.status(request.get("job_id"))
         if operation == "verify_recovery":
@@ -2708,6 +2775,20 @@
             trace_op=trace_op,
         )
 
+    def lookup_committed_publish(
+        self,
+        *,
+        idempotency_key: str,
+        state_id: str,
+        revision: int,
+    ) -> dict[str, Any]:
+        return self.request(
+            "lookup_committed_publish",
+            idempotency_key=idempotency_key,
+            state_id=state_id,
+            revision=revision,
+        )
+
     def mutation_status(self, job_id: str) -> dict[str, Any]:
         return self.request("mutation_status", job_id=job_id)
 
```

## C:\Temp\Contextor_Repo\contextor\core\live_state\publication_receipt.py
```diff
--- a/contextor/core/live_state/publication_receipt.py
+++ b/contextor/core/live_state/publication_receipt.py
@@ -30,6 +30,7 @@
 def _result(
     status: str, *, job_id: str | None, service_instance_id: str | None,
     process_start_identity: str | None, state_id: str, revision: int,
+    idempotency_key: str | None = None,
     published_revision: int | None = None, warning: str | None = None,
 ) -> dict[str, object]:
     return {
@@ -41,6 +42,7 @@
         "live_publish_process_start_identity": process_start_identity,
         "live_publish_expected_state_id": state_id,
         "live_publish_expected_revision": revision,
+        "live_publish_idempotency_key": idempotency_key,
     }
 
 
@@ -51,11 +53,13 @@
     process_start_identity: str,
     state_id: str,
     revision: int,
+    idempotency_key: str | None = None,
 ) -> dict[str, object]:
     common = dict(
         job_id=job_id, service_instance_id=service_instance_id,
         process_start_identity=process_start_identity,
         state_id=state_id, revision=revision,
+        idempotency_key=idempotency_key,
     )
     if not isinstance(receipt, dict) or receipt.get("job_id") != job_id:
         return _result("pending_verification", **common, warning="Exact mutation job status unavailable.")
@@ -106,7 +110,7 @@
     common = dict(
         job_id=None, service_instance_id=service_id,
         process_start_identity=process_identity,
-        state_id=state_id, revision=revision,
+        state_id=state_id, revision=revision, idempotency_key=key,
     )
     if not isinstance(service_id, str) or not service_id or not isinstance(process_identity, str) or not process_identity:
         return _result("unverified_authority_changed", **common,
@@ -125,13 +129,37 @@
             accepted = submitted
         break
     if accepted is None:
+        try:
+            accepted = client.lookup_committed_publish(
+                idempotency_key=key, state_id=state_id, revision=revision,
+            )
+        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+            accepted = None
+        if not isinstance(accepted, dict) or accepted.get("status") != "ok":
+            return _result("pending_verification", **common,
+                           warning="Publication admission and read-only job lookup unavailable.")
+    if accepted.get("status") == "ok" and isinstance(accepted.get("job_id"), str):
+        job_id = accepted["job_id"]
+    elif accepted.get("status") == "accepted" and accepted.get("accepted") is True:
+        job_id = accepted.get("job_id")
+    else:
+        return _result("failed", **common, warning="Publication admission rejected.")
+    if not isinstance(job_id, str) or not job_id:
+        try:
+            recovered = client.lookup_committed_publish(
+                idempotency_key=key, state_id=state_id, revision=revision,
+            )
+        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+            recovered = None
+        if isinstance(recovered, dict) and recovered.get("status") == "ok":
+            accepted = recovered
+            job_id = recovered.get("job_id")
+        else:
+            return _result("pending_verification", **common,
+                           warning="Publication job identity unavailable; read-only recovery found no job.")
+    if not isinstance(job_id, str) or not job_id:
         return _result("pending_verification", **common,
-                       warning="Publication admission result unavailable.")
-    if accepted.get("status") != "accepted" or accepted.get("accepted") is not True:
-        return _result("failed", **common, warning="Publication admission rejected.")
-    job_id = accepted.get("job_id")
-    if not isinstance(job_id, str) or not job_id:
-        return _result("pending_verification", **common, warning="Publication job identity unavailable.")
+                       warning="Publication job identity unavailable.")
     common["job_id"] = job_id
     while True:
         try:
@@ -142,7 +170,7 @@
         classified = classify_publication_receipt(
             status, job_id=job_id, service_instance_id=service_id,
             process_start_identity=process_identity,
-            state_id=state_id, revision=revision,
+            state_id=state_id, revision=revision, idempotency_key=key,
         )
         if classified["live_publish_status"] != "pending_verification":
             try:
```

## C:\Temp\Contextor_Repo\contextor\core\api\facade.py
```diff
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -578,6 +578,7 @@
             list: List of architectural validation errors, if any.
         """
         facade_started = time.monotonic()
+        live_publish_idempotency_key = None
         live_publish_job_id = None
         live_publish_service_instance_id = None
         live_publish_process_start_identity = None
@@ -1165,6 +1166,7 @@
             live_publish_status = "not_attempted"
             live_publish_revision = None
             live_publish_warning = None
+            live_publish_idempotency_key = None
             live_publish_job_id = None
             live_publish_service_instance_id = None
             live_publish_process_start_identity = None
@@ -1270,6 +1272,7 @@
                         live_publish_status = published["live_publish_status"]
                         live_publish_revision = published["live_publish_revision"]
                         live_publish_warning = published["live_publish_warning"]
+                        live_publish_idempotency_key = published["live_publish_idempotency_key"]
                         live_publish_job_id = published["live_publish_job_id"]
                         live_publish_service_instance_id = published["live_publish_service_instance_id"]
                         live_publish_process_start_identity = published["live_publish_process_start_identity"]
@@ -1384,6 +1387,7 @@
             analysis_result.live_publish_status = live_publish_status
             analysis_result.live_publish_revision = live_publish_revision
             analysis_result.live_publish_warning = live_publish_warning
+            analysis_result.live_publish_idempotency_key = live_publish_idempotency_key
             analysis_result.live_publish_job_id = live_publish_job_id
             analysis_result.live_publish_service_instance_id = live_publish_service_instance_id
             analysis_result.live_publish_process_start_identity = live_publish_process_start_identity
@@ -1393,6 +1397,7 @@
                 analysis_result.summary_data["live_publish_status"] = live_publish_status
                 analysis_result.summary_data["live_publish_revision"] = live_publish_revision
                 analysis_result.summary_data["live_publish_warning"] = live_publish_warning
+                analysis_result.summary_data["live_publish_idempotency_key"] = live_publish_idempotency_key
                 analysis_result.summary_data["live_publish_job_id"] = live_publish_job_id
                 analysis_result.summary_data["live_publish_service_instance_id"] = live_publish_service_instance_id
                 analysis_result.summary_data["live_publish_process_start_identity"] = live_publish_process_start_identity
```

## C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py
```diff
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -197,6 +197,7 @@
             "created_at", "started_at", "completed_at", "updated_at",
             "message", "error", "live_publish_status",
             "live_publish_revision", "live_publish_warning",
+            "live_publish_idempotency_key",
             "live_publish_job_id", "live_publish_service_instance_id",
             "live_publish_process_start_identity",
             "live_publish_expected_state_id", "live_publish_expected_revision",
@@ -276,6 +277,7 @@
                             "live_publish_warning",
                             None,
                         ),
+                        "live_publish_idempotency_key": getattr(result, "live_publish_idempotency_key", None),
                         "live_publish_job_id": getattr(result, "live_publish_job_id", None),
                         "live_publish_service_instance_id": getattr(result, "live_publish_service_instance_id", None),
                         "live_publish_process_start_identity": getattr(result, "live_publish_process_start_identity", None),
@@ -391,6 +393,7 @@
                 **{
                     key: (analysis_outcome or {}).get(key)
                     for key in (
+                        "live_publish_idempotency_key",
                         "live_publish_job_id",
                         "live_publish_service_instance_id",
                         "live_publish_process_start_identity",
@@ -479,6 +482,7 @@
                 "pending" if operation == "project" else "not_applicable"
             ),
             "live_publish_revision": None, "live_publish_warning": None,
+            "live_publish_idempotency_key": None,
             "live_publish_job_id": None,
             "live_publish_service_instance_id": None,
             "live_publish_process_start_identity": None,
```

## C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
```diff
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -105,12 +105,18 @@
         job_id is not None
         and job.get("status") == "completed"
         and job.get("live_publish_status") == "pending_verification"
-        and isinstance(job.get("live_publish_job_id"), str)
         and isinstance(job.get("live_publish_expected_state_id"), str)
         and type(job.get("live_publish_expected_revision")) is int
+        and isinstance(job.get("live_publish_service_instance_id"), str)
+        and isinstance(job.get("live_publish_process_start_identity"), str)
+        and (
+            isinstance(job.get("live_publish_job_id"), str)
+            or isinstance(job.get("live_publish_idempotency_key"), str)
+        )
     ):
         from contextor.core.live_state import connect
         from contextor.core.live_state.publication_receipt import classify_publication_receipt
+        from contextor.core.live_state.publication_receipt import committed_publication_key
 
         try:
             client = connect(root, reconcile_missing_endpoint_binding=False)
@@ -120,9 +126,18 @@
         expected_process = job.get("live_publish_process_start_identity")
         if client is None:
             pass  # Retain the durable pending status.
-        elif (
+        else:
+            try:
+                authority = client.authority_status()
+            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                authority = None
+        if client is not None and (
             client.endpoint.service_instance_id != expected_service
             or client.endpoint.process_start_identity != expected_process
+            or not isinstance(authority, dict)
+            or authority.get("status") != "ok"
+            or authority.get("service_instance_id") != expected_service
+            or authority.get("process_start_identity") != expected_process
         ):
             job = {
                 **job,
@@ -130,22 +145,56 @@
                 "live_publish_revision": None,
                 "live_publish_warning": "LIVE authority identity changed before receipt verification.",
             }
-        else:
-            try:
-                receipt = client.mutation_status(job["live_publish_job_id"])
-            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
-                receipt = None
-            classified = classify_publication_receipt(
-                receipt,
-                job_id=job["live_publish_job_id"],
-                service_instance_id=expected_service,
-                process_start_identity=expected_process,
-                state_id=job["live_publish_expected_state_id"],
-                revision=job["live_publish_expected_revision"],
-            )
-            if classified["live_publish_status"] in {"success", "failed", "recovery_required"}:
-                job = {**job, **classified}
-                analysis_jobs._write_analysis_job(root, job)
+        elif client is not None:
+            mutation_job_id = job.get("live_publish_job_id")
+            if not isinstance(mutation_job_id, str):
+                state_id = job["live_publish_expected_state_id"]
+                revision = job["live_publish_expected_revision"]
+                stored_key = job.get("live_publish_idempotency_key")
+                repo_id = authority.get("repo_id")
+                expected_key = None
+                if isinstance(repo_id, str) and repo_id:
+                    try:
+                        expected_key = committed_publication_key(repo_id, state_id, revision)
+                    except ValueError:
+                        expected_key = None
+                if not isinstance(stored_key, str) or stored_key != expected_key:
+                    authority = None
+                else:
+                    try:
+                        lookup = client.lookup_committed_publish(
+                            idempotency_key=stored_key, state_id=state_id,
+                            revision=revision,
+                        )
+                    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                        lookup = None
+                    if isinstance(lookup, dict) and lookup.get("status") == "ok":
+                        mutation_job_id = lookup.get("job_id")
+                        if isinstance(mutation_job_id, str) and mutation_job_id:
+                            job = {**job, "live_publish_job_id": mutation_job_id}
+                            try:
+                                analysis_jobs._write_analysis_job(root, job)
+                            except OSError:
+                                pass
+                    else:
+                        mutation_job_id = None
+            if isinstance(mutation_job_id, str) and mutation_job_id:
+                try:
+                    receipt = client.mutation_status(mutation_job_id)
+                except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                    receipt = None
+                classified = classify_publication_receipt(
+                    receipt,
+                    job_id=mutation_job_id,
+                    service_instance_id=expected_service,
+                    process_start_identity=expected_process,
+                    state_id=job["live_publish_expected_state_id"],
+                    revision=job["live_publish_expected_revision"],
+                    idempotency_key=job.get("live_publish_idempotency_key"),
+                )
+                if classified["live_publish_status"] in {"success", "failed", "recovery_required"}:
+                    job = {**job, **classified}
+                    analysis_jobs._write_analysis_job(root, job)
     public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
     if public_job.get("status") == "completed":
         diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
```

## C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json
```diff
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -14,7 +14,7 @@
     "Returns durable status for a specified or latest analysis job without any cardinality hard limit.\nResolution & ambiguity:\n1. Explicit job_id: returns the exact requested durable job without enumerating active jobs; missing jobs return status='not_found'.\n2. Omitted job_id: enumerates persisted queued/running jobs. When multiple active jobs exist, returns read-only status='ambiguous_job' with job_id=null, repo_path, active_job_count, bounded active_jobs list (max 5 candidates ordered newest mtime first, tie-broken by ascending job_id, each containing job_id, operation, target, status, created_at, updated_at), truncated boolean flag, and guidance message to repeat with one listed job_id.\n3. Single or zero active jobs: preserves legacy latest-durable-job selection (a sole active job is NOT automatically preferred over a newer terminal job).\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nWhen output > 15 KiB with ``allow_large_output=false``, oversized status responses automatically single-shot reduce ``skipped_files`` evidence to the largest prefix fitting within 15360 UTF-8 bytes (adding top-level ``_output.auto_bounded=true``, ``bounded_collection='skipped_files'``, and ``returned_count``); scalar job metadata and progress state are never truncated. If minimal status with zero skipped files still exceeds 15360 bytes, ``status: 'confirmation_required'`` is returned.\nPassing ``allow_large_output=true`` returns the complete lossless status response without auto-bounding.\nFor running jobs, note that status and progress may advance between preflight and retry."
   ],
   "freshness": [
-    "For an explicit completed job with live_publish_status=pending_verification and saved publication correlation, this read-only tool reconnects to the existing verified LIVE authority with endpoint reconciliation disabled, verifies service instance and process start identity, then checks the exact mutation job receipt. A terminal verified receipt is durably persisted. It never submits a publication, update, or FULL analysis.",
+    "For an explicit completed job with live_publish_status=pending_verification and saved publication correlation, this read-only tool reconnects to the existing verified LIVE authority with endpoint reconciliation disabled and verifies service instance and process start identity. If the mutation job ID was lost, it verifies the canonical generation key against the authority repository identity and performs a read-only lookup in the existing mutation coordinator. A recovered job ID is durably saved; only its exact receipt can resolve publication status. It never submits a publication, update, or FULL analysis.",
     "Publication acceptance is not success. A completed analysis may retain pending_verification until the exact mutation job is verified. Replaced authority yields unverified_authority_changed; missing/evicted job remains pending. Matching LIVE revision alone cannot certify the publication. Historical timed_out jobs without exact correlation are not promoted.",
     "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``recovery_required``,\n``pending_verification`` or ``failed``; an analysis failure before publication reports\n``not_attempted``. ``success`` requires an exact completed mutation receipt\nfor the requested generation on the verified service. ``recovery_required``\nmeans the generation was installed but LIVE health needs recovery verification.\nOnly these verified installed outcomes expose ``live_publish_revision``.\nA missing receipt remains ``pending_verification``; replaced authority yields\n``unverified_authority_changed``. Layer and single-file jobs report\n``not_applicable`` because their shared facade updates canonical state\nincrementally rather than publishing a new global baseline here.",
     "Where diagnostics_summary.cycles is exposed, its count is the number of unique normalized DFS back-edge paths after rotational deduplication, not the SCC count, cyclic-module count, cyclic-edge count, runtime failure count, or exhaustive number of simple cycles. diagnostics_attention_required retains its structural diagnostic meaning."
```

## C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py
```diff
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -77,6 +77,11 @@
         endpoint = SimpleNamespace(service_instance_id="replacement",
                                    process_start_identity="process")
 
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": self.endpoint.service_instance_id,
+                    "process_start_identity": self.endpoint.process_start_identity,
+                    "repo_id": "repo-id"}
+
         def mutation_status(self, job_id):
             calls.append(job_id)
             return {"status": "ok", "job_id": job_id, "state": "completed",
@@ -101,6 +106,208 @@
     assert result["live_publish_revision"] == 7
     assert calls == ["mu-exact"]
     assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "success"
+
+
+def test_pending_publication_without_job_id_recovers_by_canonical_key_read_only(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+
+    root = tmp_path
+    import contextor.mcp.tools.get_analysis_status as status_module
+    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
+    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
+                        lambda _summary, _job: {"attention_required": False})
+    job = _create_job(root, 991, live_publish_status="pending_verification",
+                      live_publish_revision=None)
+    key = committed_publication_key("repo-id", "sid", 7)
+    job.update({
+        "live_publish_job_id": None,
+        "live_publish_idempotency_key": key,
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+    calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service",
+                                   process_start_identity="process")
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process", "repo_id": "repo-id"}
+
+        def lookup_committed_publish(self, *, idempotency_key, state_id, revision):
+            calls.append(("lookup", idempotency_key, state_id, revision))
+            return {"status": "ok", "job_id": "mu-recovered", "state": "completed",
+                    "requested_state_id": "sid", "requested_revision": 7,
+                    "response": {"status": "ok", "revision": 7}}
+
+        def mutation_status(self, recovered_job_id):
+            calls.append(("status", recovered_job_id))
+            return {"status": "ok", "job_id": recovered_job_id, "state": "completed",
+                    "requested_state_id": "sid", "requested_revision": 7,
+                    "response": {"status": "ok", "revision": 7}}
+
+    def connect(_root, *, reconcile_missing_endpoint_binding=True):
+        assert reconcile_missing_endpoint_binding is False
+        return Client()
+
+    monkeypatch.setattr(live_state_module, "connect", connect)
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert calls == [("lookup", key, "sid", 7), ("status", "mu-recovered")]
+    assert result["live_publish_status"] == "success"
+    assert result["live_publish_job_id"] == "mu-recovered"
+    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
+    assert stored["live_publish_job_id"] == "mu-recovered"
+    assert stored["live_publish_idempotency_key"] == key
+
+
+def test_pending_publication_missing_or_replaced_authority_stays_unverified(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+
+    root = tmp_path
+    import contextor.mcp.tools.get_analysis_status as status_module
+    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
+    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
+                        lambda _summary, _job: {"attention_required": False})
+    job = _create_job(root, 992, live_publish_status="pending_verification",
+                      live_publish_revision=None)
+    job.update({
+        "live_publish_job_id": None,
+        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+    lookup_calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="replacement",
+                                   process_start_identity="process")
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "replacement",
+                    "process_start_identity": "process", "repo_id": "repo-id"}
+
+        def lookup_committed_publish(self, **kwargs):
+            lookup_calls.append(kwargs)
+            return {"status": "error", "error": "unknown_publication_job"}
+
+    monkeypatch.setattr(
+        live_state_module, "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
+    )
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert result["live_publish_revision"] is None
+    assert lookup_calls == []
+    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "pending_verification"
+
+
+def test_pending_publication_unknown_key_lookup_remains_pending(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+
+    root = tmp_path
+    import contextor.mcp.tools.get_analysis_status as status_module
+    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
+    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
+                        lambda _summary, _job: {"attention_required": False})
+    job = _create_job(root, 993, live_publish_status="pending_verification",
+                      live_publish_revision=None)
+    job.update({
+        "live_publish_job_id": None,
+        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service",
+                                   process_start_identity="process")
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process", "repo_id": "repo-id"}
+
+        def lookup_committed_publish(self, **kwargs):
+            return {"status": "error", "error": "unknown_publication_job"}
+
+    monkeypatch.setattr(
+        live_state_module, "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
+    )
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert result["live_publish_status"] == "pending_verification"
+    assert result["live_publish_job_id"] is None
+    assert result["live_publish_revision"] is None
+    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_job_id"] is None
+
+
+def test_running_publication_recovery_persists_job_id_and_stays_pending(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+    import contextor.mcp.tools.get_analysis_status as status_module
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+
+    root = tmp_path
+    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
+    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
+                        lambda _summary, _job: {"attention_required": False})
+    job = _create_job(root, 994, live_publish_status="pending_verification",
+                      live_publish_revision=None)
+    job.update({
+        "live_publish_job_id": None,
+        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service",
+                                   process_start_identity="process")
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process", "repo_id": "repo-id"}
+
+        def lookup_committed_publish(self, **kwargs):
+            return {"status": "ok", "job_id": "mu-running", "state": "running",
+                    "requested_state_id": "sid", "requested_revision": 7}
+
+        def mutation_status(self, mutation_job_id):
+            assert mutation_job_id == "mu-running"
+            return {"status": "ok", "job_id": mutation_job_id, "state": "running",
+                    "requested_state_id": "sid", "requested_revision": 7}
+
+    monkeypatch.setattr(
+        live_state_module, "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
+    )
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert result["live_publish_status"] == "pending_verification"
+    assert result["live_publish_job_id"] == "mu-running"
+    assert result["live_publish_revision"] is None
+    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_job_id"] == "mu-running"
 
 
 def test_analysis_status_concurrency__multiple_active_without_job_id_returns_ambiguity(tmp_path):
```

## C:\Temp\Contextor_Repo\tests\test_async_publication_receipt.py
```diff
--- a/tests/test_async_publication_receipt.py
+++ b/tests/test_async_publication_receipt.py
@@ -1,6 +1,7 @@
 """Focused safety contracts for queued committed publication receipts."""
 
 from types import SimpleNamespace
+import time
 
 from contextor.core.live_state.ipc import CanonicalMutationCoordinator
 from contextor.core.live_state.publication_receipt import (
@@ -37,6 +38,10 @@
         status = coordinator.status(first["job_id"])
         assert status["requested_state_id"] == "sid"
         assert status["requested_revision"] == 1
+        deadline = time.monotonic() + 2
+        while status["state"] not in {"completed", "failed", "cancelled"} and time.monotonic() < deadline:
+            time.sleep(0.01)
+            status = coordinator.status(first["job_id"])
         coordinator.close()
         assert len(executed) == 1
         assert executed[0]["state_id"] == "sid"
@@ -136,3 +141,90 @@
     )
     assert result["live_publish_status"] == "unverified_authority_changed"
     assert result["live_publish_revision"] is None
+
+
+def test_lost_first_admission_response_reuses_same_generation_job():
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def __init__(self):
+            self.submissions = []
+
+        def submit_committed_publish(self, **kwargs):
+            self.submissions.append(kwargs)
+            if len(self.submissions) == 1:
+                raise TimeoutError("response lost")
+            return {"status": "accepted", "accepted": True, "job_id": "mu-original"}
+
+        def mutation_status(self, job_id):
+            assert job_id == "mu-original"
+            return {**_terminal(), "job_id": job_id}
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process"}
+
+    client = Client()
+    result = publish_committed_and_wait(
+        client, repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
+    )
+    assert result["live_publish_status"] == "success"
+    assert result["live_publish_job_id"] == "mu-original"
+    assert len(client.submissions) == 2
+    assert client.submissions[0]["idempotency_key"] == client.submissions[1]["idempotency_key"]
+
+
+def test_lost_both_admission_responses_recovers_original_receipt_read_only():
+    key = committed_publication_key("repo", "sid", 1)
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def __init__(self):
+            self.submissions = 0
+            self.lookups = 0
+
+        def submit_committed_publish(self, **kwargs):
+            self.submissions += 1
+            raise TimeoutError("response lost")
+
+        def lookup_committed_publish(self, *, idempotency_key, state_id, revision):
+            self.lookups += 1
+            assert (idempotency_key, state_id, revision) == (key, "sid", 1)
+            return {**_terminal(), "job_id": "mu-original"}
+
+        def mutation_status(self, job_id):
+            assert job_id == "mu-original"
+            return {**_terminal(), "job_id": job_id}
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process"}
+
+    client = Client()
+    result = publish_committed_and_wait(
+        client, repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
+    )
+    assert client.submissions == 2
+    assert client.lookups == 1
+    assert result["live_publish_status"] == "success"
+    assert result["live_publish_job_id"] == "mu-original"
+    assert result["live_publish_idempotency_key"] == key
+
+
+def test_lost_admission_and_missing_lookup_remain_pending_with_key():
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def submit_committed_publish(self, **kwargs):
+            raise TimeoutError("response lost")
+
+        def lookup_committed_publish(self, **kwargs):
+            return {"status": "error", "error": "unknown_publication_job"}
+
+    result = publish_committed_and_wait(
+        Client(), repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
+    )
+    assert result["live_publish_status"] == "pending_verification"
+    assert result["live_publish_job_id"] is None
+    assert result["live_publish_idempotency_key"] == committed_publication_key("repo", "sid", 1)
```

## C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
```diff
--- a/tests/test_durable_verified_publish.py
+++ b/tests/test_durable_verified_publish.py
@@ -12,6 +12,7 @@
 
 from contextor.core.live_state import ipc as ipc_module
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
+from contextor.core.live_state.publication_receipt import committed_publication_key
 from contextor.core.live_state.store import (
     load_snapshot,
     locked_committed_snapshot,
@@ -209,13 +210,27 @@
     server._repository_identity_reader = lambda: durable_harness.identity
     request = {
         "operation": "submit_committed_publish", "state_id": "sid",
-        "revision": 1, "origin": "mcp_analysis", "idempotency_key": "cp-test",
+        "revision": 1, "origin": "mcp_analysis",
+        "idempotency_key": committed_publication_key(durable_harness.identity.repo_id, "sid", 1),
         "trace_op": None,
     }
     accepted = server._dispatch(request)
     assert accepted["status"] == "accepted"
     assert server._dispatch(request)["job_id"] == accepted["job_id"]
-    assert server._dispatch({**request, "state_id": "other"})["error"] == "publication_idempotency_conflict"
+    assert server._dispatch({**request, "idempotency_key": "arbitrary"})["error"] == "invalid_publication_idempotency_key"
+    lookup = server._dispatch({
+        "operation": "lookup_committed_publish",
+        "idempotency_key": request["idempotency_key"],
+        "state_id": "sid", "revision": 1,
+    })
+    assert lookup["job_id"] == accepted["job_id"]
+    assert len(server._mutation_coordinator._jobs) == 1
+    assert server._dispatch({
+        "operation": "lookup_committed_publish",
+        "idempotency_key": request["idempotency_key"],
+        "state_id": "other", "revision": 1,
+    })["error"] == "invalid_publication_idempotency_key"
+    assert server._dispatch({**request, "idempotency_key": "different-key"})["error"] == "invalid_publication_idempotency_key"
     deadline = time.monotonic() + 3
     while time.monotonic() < deadline:
         receipt = server._dispatch({"operation": "mutation_status", "job_id": accepted["job_id"]})
```
