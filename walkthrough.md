# C38E2Q Durable Async LIVE Publication

TASK=CONTEXTOR_C38E2Q_DURABLE_ASYNC_LIVE_PUBLICATION
IMPLEMENTATION_RESULT=Queued committed publication is implemented in the existing coordinator; FULL facade submits and waits for an exact terminal receipt for at most 90 seconds. No production FULL was run.
HEAD_BEFORE=2a2ed8cb318bc8029928b45b88aa00c3e54ad3a5
HEAD_AFTER=2a2ed8cb318bc8029928b45b88aa00c3e54ad3a5
IDEMPOTENCY_IDENTITY_BINDING=Authoritative repo_id is read server-side. Same key and generation reuse one job; changed state_id or revision returns publication_idempotency_conflict before execution. update_file duplicate behavior is unchanged.
EXACT_TERMINAL_RECEIPT=Success requires exact job_id, requested_state_id, requested_revision, completed state, successful committed publication response, matching installed revision, and service identity. Unknown or evicted jobs remain pending_verification.
AUTHORITY_CORRELATION=Submission captures service_instance_id and process_start_identity. Immediate terminal confirmation checks authority_status. Later explicit get_analysis_status connects read-only with endpoint reconciliation disabled and rejects replacement authority without resubmission.
LEGACY_COMPATIBILITY=Synchronous publish and update_file IPC behavior remain available. Existing 30-second request timeout was not changed.
TARGETED_TEST_RESULTS=Initial named subset: 214 passed, 2 failed. One failure was the old synchronous-publish test double and was updated; its rerun passed. The other failed in RuntimeDomainError during test setup before the changed path and passed on focused rerun. Final focused receipt/status/facade subset: 27 passed. Queued server integration: 1 passed. JSON docs parsed. No full pytest suite run.
WATCHER_EVENTS=DIRECT_EVIDENCE: desktop_watcher update_file revisions 574-589 observed, continuous, resync_required=false. Includes ipc.py, publication_receipt.py, facade.py, analysis_jobs.py, get_analysis_status.py, and changed tests through revision 589. Final test file test_durable_verified_publish.py produced UPDATED at 588 and UNCHANGED at 589.
WORKSPACE_SYNC=DIRECT_EVIDENCE: LIVE latest revision 589 at last poll, continuous from pre-edit revision 573 and no resync required. Python file update events observed. Some blast-radius states were deferred, so complete lineage freshness for every changed file is not certified.
LIVE_REVISION_BEFORE_AFTER=573 -> 589 (last observed; watcher may advance)
MCP_BACKEND_RESTART_REQUIRED=YES
LIVE_SERVICE_RESTART_REQUIRED=YES
RESTART_PERFORMED=NO
FINAL_VERDICT=C38E2Q_SOURCE_PASS_PENDING_RUNTIME
NEXT_STEP=Await manual runtime reload and auditor instruction: proceduj.

FILES_CHANGED
C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
C:\Temp\Contextor_Repo\contextor\core\live_state\publication_receipt.py
C:\Temp\Contextor_Repo\contextor\core\api\facade.py
C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py
C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json
C:\Temp\Contextor_Repo\contextor\mcp\docs\analyze_project.json
C:\Temp\Contextor_Repo\tests\test_async_publication_receipt.py
C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py

FULL_DIFFS

## C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
```diff
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -15,6 +15,7 @@
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
 from pathlib import Path
+from types import SimpleNamespace
 from typing import Any, Callable, Mapping
 
 from contextor.core.live_state.runtime_lease import ProcessIdentity
@@ -159,9 +160,23 @@
             request_dict = dict(request)
         except (TypeError, ValueError):
             request_dict = {}
-        file_path = request_dict.get("file_path")
-        if not isinstance(file_path, str) or not file_path:
-            return {"status": "error", "error": "invalid_file_path"}
+        operation = request_dict.get("operation", "submit_update_file")
+        if operation == "submit_committed_publish":
+            state_id = request_dict.get("state_id")
+            revision = request_dict.get("revision")
+            repo_id = request_dict.get("repo_id")
+            if (
+                not isinstance(repo_id, str) or not repo_id
+                or not isinstance(state_id, str) or not state_id
+                or type(revision) is not int or revision < 1
+            ):
+                return {"status": "error", "error": "invalid_publication_identity"}
+        elif operation == "submit_update_file":
+            file_path = request_dict.get("file_path")
+            if not isinstance(file_path, str) or not file_path:
+                return {"status": "error", "error": "invalid_file_path"}
+        else:
+            return {"status": "error", "error": "invalid_mutation_operation"}
         idempotency_key = request_dict.get("idempotency_key")
         if not isinstance(idempotency_key, str) or not idempotency_key:
             return {"status": "error", "error": "invalid_idempotency_key"}
@@ -177,6 +192,15 @@
             if existing_job_id is not None:
                 existing_job = self._jobs.get(existing_job_id)
                 if existing_job is not None:
+                    if operation == "submit_committed_publish":
+                        existing_request = existing_job.request
+                        if (
+                            existing_request.get("operation") != operation
+                            or existing_request.get("repo_id") != repo_id
+                            or existing_request.get("state_id") != state_id
+                            or existing_request.get("revision") != revision
+                        ):
+                            return {"status": "error", "error": "publication_idempotency_conflict"}
                     return {
                         "status": "accepted",
                         "accepted": True,
@@ -267,6 +291,9 @@
                 response["error"] = job.error
             if job.response is not None:
                 response["response"] = copy.deepcopy(job.response)
+            if job.request.get("operation") == "submit_committed_publish":
+                response["requested_state_id"] = job.request["state_id"]
+                response["requested_revision"] = job.request["revision"]
             return response
 
     def _prune_terminal_locked(self) -> None:
@@ -817,7 +844,7 @@
         self._service_cleanup_ok = True
         self._service_wakeup_token = secrets.token_hex(32)
         self._mutation_coordinator = CanonicalMutationCoordinator(
-            self._execute_queued_update_file,
+            self._execute_queued_mutation,
             self._read_revision,
         )
         self._stop = threading.Event()
@@ -1881,6 +1908,57 @@
         with self._mutation_guard(request, self._stop):
             return self._execute_update_file(request, allow_recovery_fence=True)
 
+    def _execute_queued_mutation(self, request: dict[str, Any]) -> dict[str, Any]:
+        if request.get("operation", "submit_update_file") == "submit_update_file":
+            return self._execute_queued_update_file(request)
+        if request.get("operation") == "submit_committed_publish":
+            candidate = SimpleNamespace(
+                state_id=request["state_id"],
+                revision=request["revision"],
+            )
+            return self._execute_publish({
+                "state": candidate,
+                "origin": request["origin"],
+                "trace_op": request.get("trace_op"),
+                "acknowledge_installed": True,
+            })
+        return {"status": "error", "error": "invalid_mutation_operation"}
+
+    def _submit_committed_publish(self, request: dict[str, Any]) -> dict[str, Any]:
+        if self._committed_snapshot_reader is None:
+            return {"status": "error", "error": "committed_snapshot_reader_unavailable"}
+        if not {"operation", "state_id", "revision", "origin", "idempotency_key"} <= set(request) or set(request) - {
+            "operation", "state_id", "revision", "origin", "idempotency_key", "trace_op",
+        }:
+            return {"status": "error", "error": "invalid_committed_publish_request"}
+        state_id = request["state_id"]
+        revision = request["revision"]
+        origin = request["origin"]
+        key = request["idempotency_key"]
+        trace_op = request.get("trace_op")
+        if not isinstance(state_id, str) or not state_id or len(state_id) > 256:
+            return {"status": "error", "error": "invalid_state_id"}
+        if type(revision) is not int or revision < 1:
+            return {"status": "error", "error": "invalid_canonical_revision"}
+        if not isinstance(origin, str) or origin not in {"desktop_analysis", "mcp_analysis", "cli_analysis"}:
+            return {"status": "error", "error": "invalid_publish_origin"}
+        if not isinstance(key, str) or not key or len(key) > 256:
+            return {"status": "error", "error": "invalid_idempotency_key"}
+        if trace_op is not None and (
+            not isinstance(trace_op, str) or not trace_op or len(trace_op) > 256
+        ):
+            return {"status": "error", "error": "invalid_publish_trace_op"}
+        if self._repository_identity_reader is None:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        try:
+            identity = self._repository_identity_reader()
+        except Exception:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        repo_id = getattr(identity, "repo_id", None)
+        if not isinstance(repo_id, str) or not repo_id:
+            return {"status": "error", "error": "repository_identity_unavailable"}
+        return self._mutation_coordinator.submit({**request, "repo_id": repo_id})
+
     def _execute_update_file(
         self, request: dict[str, Any], *, allow_recovery_fence: bool = False
     ) -> dict[str, Any]:
@@ -2172,6 +2250,8 @@
             return self._dispatch_release_desktop_claim(request)
         if operation == "submit_update_file":
             return self._mutation_coordinator.submit(request)
+        if operation == "submit_committed_publish":
+            return self._submit_committed_publish(request)
         if operation == "mutation_status":
             return self._mutation_coordinator.status(request.get("job_id"))
         if operation == "verify_recovery":
@@ -2610,6 +2690,24 @@
             idempotency_key=idempotency_key,
         )
 
+    def submit_committed_publish(
+        self,
+        *,
+        state_id: str,
+        revision: int,
+        origin: str,
+        idempotency_key: str,
+        trace_op: str | None = None,
+    ) -> dict[str, Any]:
+        return self.request(
+            "submit_committed_publish",
+            state_id=state_id,
+            revision=revision,
+            origin=origin,
+            idempotency_key=idempotency_key,
+            trace_op=trace_op,
+        )
+
     def mutation_status(self, job_id: str) -> dict[str, Any]:
         return self.request("mutation_status", job_id=job_id)
 
```

## C:\Temp\Contextor_Repo\contextor\core\live_state\publication_receipt.py
```diff
--- a/contextor/core/live_state/publication_receipt.py
+++ b/contextor/core/live_state/publication_receipt.py
@@ -0,0 +1,162 @@
+"""Bounded confirmation of one exact committed LIVE publication job."""
+
+from __future__ import annotations
+
+import hashlib
+import json
+import time
+from typing import Any
+
+
+CONFIRMATION_SECONDS = 90.0
+POLL_SECONDS = 0.1
+
+
+def committed_publication_key(repo_id: str, state_id: str, revision: int) -> str:
+    if (
+        not isinstance(repo_id, str) or not repo_id
+        or not isinstance(state_id, str) or not state_id
+        or type(revision) is not int or revision < 1
+    ):
+        raise ValueError("Invalid committed publication identity.")
+    encoded = json.dumps(
+        [repo_id, state_id, revision],
+        ensure_ascii=False,
+        separators=(",", ":"),
+    ).encode("utf-8")
+    return "cp-" + hashlib.sha256(encoded).hexdigest()
+
+
+def _result(
+    status: str, *, job_id: str | None, service_instance_id: str | None,
+    process_start_identity: str | None, state_id: str, revision: int,
+    published_revision: int | None = None, warning: str | None = None,
+) -> dict[str, object]:
+    return {
+        "live_publish_status": status,
+        "live_publish_revision": published_revision,
+        "live_publish_warning": warning,
+        "live_publish_job_id": job_id,
+        "live_publish_service_instance_id": service_instance_id,
+        "live_publish_process_start_identity": process_start_identity,
+        "live_publish_expected_state_id": state_id,
+        "live_publish_expected_revision": revision,
+    }
+
+
+def classify_publication_receipt(
+    receipt: object, *,
+    job_id: str,
+    service_instance_id: str,
+    process_start_identity: str,
+    state_id: str,
+    revision: int,
+) -> dict[str, object]:
+    common = dict(
+        job_id=job_id, service_instance_id=service_instance_id,
+        process_start_identity=process_start_identity,
+        state_id=state_id, revision=revision,
+    )
+    if not isinstance(receipt, dict) or receipt.get("job_id") != job_id:
+        return _result("pending_verification", **common, warning="Exact mutation job status unavailable.")
+    if (
+        receipt.get("requested_state_id") != state_id
+        or type(receipt.get("requested_revision")) is not int
+        or receipt["requested_revision"] != revision
+    ):
+        return _result("pending_verification", **common, warning="Mutation generation identity mismatch.")
+    if receipt.get("status") != "ok":
+        return _result("pending_verification", **common, warning="Mutation status unavailable.")
+    state = receipt.get("state")
+    if state == "queued" or state == "running":
+        return _result("pending_verification", **common)
+    if state != "completed" and state != "failed" and state != "cancelled":
+        return _result("pending_verification", **common, warning="Mutation completion state unavailable.")
+    response = receipt.get("response")
+    if state != "completed":
+        return _result("failed", **common, warning="Committed publication job failed.")
+    if not isinstance(response, dict):
+        return _result("pending_verification", **common, warning="Terminal publication response unavailable.")
+    if response.get("status") != "ok":
+        return _result("failed", **common, warning="Committed publication was rejected.")
+    if type(response.get("revision")) is not int or response["revision"] != revision:
+        return _result("pending_verification", **common, warning="Installed revision did not match request.")
+    if response.get("resync_required") is True:
+        return _result("recovery_required", **common, published_revision=revision,
+                       warning="LIVE recovery verification required.")
+    warning = (
+        "LIVE generation was already installed; event origin is not verified."
+        if response.get("already_installed") is True else None
+    )
+    return _result("success", **common, published_revision=revision, warning=warning)
+
+
+def publish_committed_and_wait(
+    client,
+    *,
+    repo_id,
+    state_id,
+    revision,
+    origin,
+) -> dict[str, object]:
+    key = committed_publication_key(repo_id, state_id, revision)
+    endpoint = client.endpoint
+    service_id = getattr(endpoint, "service_instance_id", None)
+    process_identity = getattr(endpoint, "process_start_identity", None)
+    common = dict(
+        job_id=None, service_instance_id=service_id,
+        process_start_identity=process_identity,
+        state_id=state_id, revision=revision,
+    )
+    if not isinstance(service_id, str) or not service_id or not isinstance(process_identity, str) or not process_identity:
+        return _result("unverified_authority_changed", **common,
+                       warning="Verified LIVE service identity unavailable.")
+    deadline = time.monotonic() + CONFIRMATION_SECONDS
+    accepted: dict[str, Any] | None = None
+    for _ in range(2):
+        try:
+            submitted = client.submit_committed_publish(
+                state_id=state_id, revision=revision, origin=origin,
+                idempotency_key=key,
+            )
+        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+            continue
+        if isinstance(submitted, dict):
+            accepted = submitted
+        break
+    if accepted is None:
+        return _result("pending_verification", **common,
+                       warning="Publication admission result unavailable.")
+    if accepted.get("status") != "accepted" or accepted.get("accepted") is not True:
+        return _result("failed", **common, warning="Publication admission rejected.")
+    job_id = accepted.get("job_id")
+    if not isinstance(job_id, str) or not job_id:
+        return _result("pending_verification", **common, warning="Publication job identity unavailable.")
+    common["job_id"] = job_id
+    while True:
+        try:
+            status = client.mutation_status(job_id)
+        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+            return _result("pending_verification", **common,
+                           warning="Publication status unavailable.")
+        classified = classify_publication_receipt(
+            status, job_id=job_id, service_instance_id=service_id,
+            process_start_identity=process_identity,
+            state_id=state_id, revision=revision,
+        )
+        if classified["live_publish_status"] != "pending_verification":
+            try:
+                authority = client.authority_status()
+            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                authority = None
+            if not isinstance(authority, dict) or authority.get("status") != "ok":
+                return _result("pending_verification", **common,
+                               warning="LIVE authority identity unavailable for receipt verification.")
+            if (authority.get("service_instance_id") != service_id
+                    or authority.get("process_start_identity") != process_identity):
+                return _result("unverified_authority_changed", **common,
+                               warning="LIVE authority identity changed before receipt verification.")
+            return classified
+        if time.monotonic() >= deadline:
+            return classified
+        time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))
```

## C:\Temp\Contextor_Repo\contextor\core\api\facade.py
```diff
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -578,6 +578,11 @@
             list: List of architectural validation errors, if any.
         """
         facade_started = time.monotonic()
+        live_publish_job_id = None
+        live_publish_service_instance_id = None
+        live_publish_process_start_identity = None
+        live_publish_expected_state_id = None
+        live_publish_expected_revision = None
 
         def emit_stage_end(stage: str, started: float) -> None:
             elapsed_ms = (time.monotonic() - started) * 1000.0
@@ -1160,6 +1165,11 @@
             live_publish_status = "not_attempted"
             live_publish_revision = None
             live_publish_warning = None
+            live_publish_job_id = None
+            live_publish_service_instance_id = None
+            live_publish_process_start_identity = None
+            live_publish_expected_state_id = None
+            live_publish_expected_revision = None
 
             writer = "mcp" if "mcp" in str(owner) else "desktop"
             origin = str(owner) if str(owner) in {"desktop_analysis", "mcp_analysis", "cli_analysis"} else "desktop_analysis"
@@ -1246,40 +1256,25 @@
                     if client is not None:
                         component_started = time.monotonic()
                         try:
-                            published = client.publish(
-                                state,
+                            from contextor.core.live_state.publication_receipt import publish_committed_and_wait
+                            published = publish_committed_and_wait(
+                                client,
+                                repo_id=registry.repo_id,
+                                state_id=meta.state_id,
+                                revision=meta.revision,
                                 origin=origin,
-                                acknowledge_installed=True,
                             )
                         finally:
                             publish_ms = (time.monotonic() - component_started) * 1000.0
                         component_started = time.monotonic()
-                        if (
-                            isinstance(published, dict)
-                            and published.get("status") == "ok"
-                            and published.get("revision") is not None
-                        ):
-                            live_publish_revision = int(published["revision"])
-                            if published.get("resync_required") is True:
-                                live_publish_status = "recovery_required"
-                                live_publish_warning = (
-                                    published.get("warning")
-                                    or "LIVE recovery verification required."
-                                )
-                            else:
-                                live_publish_status = "success"
-                                live_publish_warning = (
-                                    "LIVE generation was already installed; "
-                                    "event origin is not verified."
-                                    if published.get("already_installed") is True
-                                    else None
-                                )
-                        else:
-                            live_publish_status = "failed"
-                            live_publish_revision = None
-                            err = published.get("error") if isinstance(published, dict) else None
-                            status_val = published.get("status") if isinstance(published, dict) else None
-                            live_publish_warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
+                        live_publish_status = published["live_publish_status"]
+                        live_publish_revision = published["live_publish_revision"]
+                        live_publish_warning = published["live_publish_warning"]
+                        live_publish_job_id = published["live_publish_job_id"]
+                        live_publish_service_instance_id = published["live_publish_service_instance_id"]
+                        live_publish_process_start_identity = published["live_publish_process_start_identity"]
+                        live_publish_expected_state_id = published["live_publish_expected_state_id"]
+                        live_publish_expected_revision = published["live_publish_expected_revision"]
                         status_handling_ms = (time.monotonic() - component_started) * 1000.0
                         if live_publish_status == "failed" and log:
                             log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
@@ -1289,7 +1284,7 @@
                         status_handling_ms = (time.monotonic() - component_started) * 1000.0
                 except Exception as e:
                     component_started = time.monotonic()
-                    live_publish_status = "timed_out" if isinstance(e, TimeoutError) else "failed"
+                    live_publish_status = "pending_verification" if isinstance(e, TimeoutError) else "failed"
                     live_publish_revision = None
                     live_publish_warning = f"{type(e).__name__}: {e}"
                     status_handling_ms = (time.monotonic() - component_started) * 1000.0
@@ -1389,10 +1384,20 @@
             analysis_result.live_publish_status = live_publish_status
             analysis_result.live_publish_revision = live_publish_revision
             analysis_result.live_publish_warning = live_publish_warning
+            analysis_result.live_publish_job_id = live_publish_job_id
+            analysis_result.live_publish_service_instance_id = live_publish_service_instance_id
+            analysis_result.live_publish_process_start_identity = live_publish_process_start_identity
+            analysis_result.live_publish_expected_state_id = live_publish_expected_state_id
+            analysis_result.live_publish_expected_revision = live_publish_expected_revision
             if hasattr(analysis_result, "summary_data") and isinstance(analysis_result.summary_data, dict):
                 analysis_result.summary_data["live_publish_status"] = live_publish_status
                 analysis_result.summary_data["live_publish_revision"] = live_publish_revision
                 analysis_result.summary_data["live_publish_warning"] = live_publish_warning
+                analysis_result.summary_data["live_publish_job_id"] = live_publish_job_id
+                analysis_result.summary_data["live_publish_service_instance_id"] = live_publish_service_instance_id
+                analysis_result.summary_data["live_publish_process_start_identity"] = live_publish_process_start_identity
+                analysis_result.summary_data["live_publish_expected_state_id"] = live_publish_expected_state_id
+                analysis_result.summary_data["live_publish_expected_revision"] = live_publish_expected_revision
 
         progress.begin("Finalizing analysis")
         progress.finish()
```

## C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py
```diff
--- a/contextor/mcp/analysis_jobs.py
+++ b/contextor/mcp/analysis_jobs.py
@@ -197,6 +197,9 @@
             "created_at", "started_at", "completed_at", "updated_at",
             "message", "error", "live_publish_status",
             "live_publish_revision", "live_publish_warning",
+            "live_publish_job_id", "live_publish_service_instance_id",
+            "live_publish_process_start_identity",
+            "live_publish_expected_state_id", "live_publish_expected_revision",
         )
     }
     if "skipped_python_files" in job:
@@ -273,6 +276,11 @@
                             "live_publish_warning",
                             None,
                         ),
+                        "live_publish_job_id": getattr(result, "live_publish_job_id", None),
+                        "live_publish_service_instance_id": getattr(result, "live_publish_service_instance_id", None),
+                        "live_publish_process_start_identity": getattr(result, "live_publish_process_start_identity", None),
+                        "live_publish_expected_state_id": getattr(result, "live_publish_expected_state_id", None),
+                        "live_publish_expected_revision": getattr(result, "live_publish_expected_revision", None),
                     }
                 if operation == "layer":
                     ContextorFacade.analyze_layer(
@@ -380,6 +388,16 @@
                 "live_publish_status": pub_status or "failed",
                 "live_publish_revision": pub_rev,
                 "live_publish_warning": pub_warn,
+                **{
+                    key: (analysis_outcome or {}).get(key)
+                    for key in (
+                        "live_publish_job_id",
+                        "live_publish_service_instance_id",
+                        "live_publish_process_start_identity",
+                        "live_publish_expected_state_id",
+                        "live_publish_expected_revision",
+                    )
+                },
             }
 
             cold_migration = False
@@ -461,6 +479,11 @@
                 "pending" if operation == "project" else "not_applicable"
             ),
             "live_publish_revision": None, "live_publish_warning": None,
+            "live_publish_job_id": None,
+            "live_publish_service_instance_id": None,
+            "live_publish_process_start_identity": None,
+            "live_publish_expected_state_id": None,
+            "live_publish_expected_revision": None,
             "owner_pid": os.getpid(),
         }
         _write_analysis_job(root, job)
```

## C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
```diff
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -101,6 +101,51 @@
                         f"{type(exc).__name__}: {exc}"
                     ),
                 }
+    if (
+        job_id is not None
+        and job.get("status") == "completed"
+        and job.get("live_publish_status") == "pending_verification"
+        and isinstance(job.get("live_publish_job_id"), str)
+        and isinstance(job.get("live_publish_expected_state_id"), str)
+        and type(job.get("live_publish_expected_revision")) is int
+    ):
+        from contextor.core.live_state import connect
+        from contextor.core.live_state.publication_receipt import classify_publication_receipt
+
+        try:
+            client = connect(root, reconcile_missing_endpoint_binding=False)
+        except (OSError, ValueError, RuntimeError):
+            client = None
+        expected_service = job.get("live_publish_service_instance_id")
+        expected_process = job.get("live_publish_process_start_identity")
+        if client is None:
+            pass  # Retain the durable pending status.
+        elif (
+            client.endpoint.service_instance_id != expected_service
+            or client.endpoint.process_start_identity != expected_process
+        ):
+            job = {
+                **job,
+                "live_publish_status": "unverified_authority_changed",
+                "live_publish_revision": None,
+                "live_publish_warning": "LIVE authority identity changed before receipt verification.",
+            }
+        else:
+            try:
+                receipt = client.mutation_status(job["live_publish_job_id"])
+            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                receipt = None
+            classified = classify_publication_receipt(
+                receipt,
+                job_id=job["live_publish_job_id"],
+                service_instance_id=expected_service,
+                process_start_identity=expected_process,
+                state_id=job["live_publish_expected_state_id"],
+                revision=job["live_publish_expected_revision"],
+            )
+            if classified["live_publish_status"] in {"success", "failed", "recovery_required"}:
+                job = {**job, **classified}
+                analysis_jobs._write_analysis_job(root, job)
     public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
     if public_job.get("status") == "completed":
         diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
```

## C:\Temp\Contextor_Repo\contextor\mcp\docs\get_analysis_status.json
```diff
--- a/contextor/mcp/docs/get_analysis_status.json
+++ b/contextor/mcp/docs/get_analysis_status.json
@@ -14,7 +14,9 @@
     "Returns durable status for a specified or latest analysis job without any cardinality hard limit.\nResolution & ambiguity:\n1. Explicit job_id: returns the exact requested durable job without enumerating active jobs; missing jobs return status='not_found'.\n2. Omitted job_id: enumerates persisted queued/running jobs. When multiple active jobs exist, returns read-only status='ambiguous_job' with job_id=null, repo_path, active_job_count, bounded active_jobs list (max 5 candidates ordered newest mtime first, tie-broken by ascending job_id, each containing job_id, operation, target, status, created_at, updated_at), truncated boolean flag, and guidance message to repeat with one listed job_id.\n3. Single or zero active jobs: preserves legacy latest-durable-job selection (a sole active job is NOT automatically preferred over a newer terminal job).\nOutput <= 15 KiB (15360 UTF-8 bytes) returns the status payload normally.\nWhen output > 15 KiB with ``allow_large_output=false``, oversized status responses automatically single-shot reduce ``skipped_files`` evidence to the largest prefix fitting within 15360 UTF-8 bytes (adding top-level ``_output.auto_bounded=true``, ``bounded_collection='skipped_files'``, and ``returned_count``); scalar job metadata and progress state are never truncated. If minimal status with zero skipped files still exceeds 15360 bytes, ``status: 'confirmation_required'`` is returned.\nPassing ``allow_large_output=true`` returns the complete lossless status response without auto-bounding.\nFor running jobs, note that status and progress may advance between preflight and retry."
   ],
   "freshness": [
-    "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``recovery_required``,\n``timed_out`` or ``failed``; an analysis failure before publication reports\n``not_attempted``. ``success`` means accepted and healthy;\n``recovery_required`` means the durable generation was committed and LIVE\npublication accepted, but LIVE health is not certified. Both accepted states\npreserve ``live_publish_revision`` (the revision returned by the daemon).\n``recovery_required`` preserves ``live_publish_warning`` and requires recovery\nverification before normal operation resumes. Rejected publication retains\n``failed`` and its warning even when the report job completes.\nLayer and single-file jobs report ``not_applicable`` because their shared\nfacade updates canonical state incrementally rather than publishing a new\nglobal baseline here.",
+    "For an explicit completed job with live_publish_status=pending_verification and saved publication correlation, this read-only tool reconnects to the existing verified LIVE authority with endpoint reconciliation disabled, verifies service instance and process start identity, then checks the exact mutation job receipt. A terminal verified receipt is durably persisted. It never submits a publication, update, or FULL analysis.",
+    "Publication acceptance is not success. A completed analysis may retain pending_verification until the exact mutation job is verified. Replaced authority yields unverified_authority_changed; missing/evicted job remains pending. Matching LIVE revision alone cannot certify the publication. Historical timed_out jobs without exact correlation are not promoted.",
+    "Every job also exposes durable LIVE publication state. Project jobs move\nfrom ``live_publish_status='pending'`` to ``success``, ``recovery_required``,\n``pending_verification`` or ``failed``; an analysis failure before publication reports\n``not_attempted``. ``success`` requires an exact completed mutation receipt\nfor the requested generation on the verified service. ``recovery_required``\nmeans the generation was installed but LIVE health needs recovery verification.\nOnly these verified installed outcomes expose ``live_publish_revision``.\nA missing receipt remains ``pending_verification``; replaced authority yields\n``unverified_authority_changed``. Layer and single-file jobs report\n``not_applicable`` because their shared facade updates canonical state\nincrementally rather than publishing a new global baseline here.",
     "Where diagnostics_summary.cycles is exposed, its count is the number of unique normalized DFS back-edge paths after rotational deduplication, not the SCC count, cyclic-module count, cyclic-edge count, runtime failure count, or exhaustive number of simple cycles. diagnostics_attention_required retains its structural diagnostic meaning."
   ],
   "errors": [
```

## C:\Temp\Contextor_Repo\contextor\mcp\docs\analyze_project.json
```diff
--- a/contextor/mcp/docs/analyze_project.json
+++ b/contextor/mcp/docs/analyze_project.json
@@ -9,6 +9,7 @@
     "exclude_paths (array of strings or null, optional, default null): repository-relative or accepted existing exclusion paths forwarded to project analysis; null means no additional exclusions supplied by this request."
   ],
   "behavior": [
+    "After the durable committed snapshot is saved, FULL publication submits the exact state_id and revision to the existing LIVE mutation queue with a deterministic generation idempotency key. The service acknowledges admission before loading the snapshot; its existing mutation worker performs committed-snapshot validation and installation. The analysis job may complete while publication remains pending_verification. The original synchronous publish API remains available to other consumers.",
     "1. Starts global architectural analysis asynchronously/non-blocking and immediately returns job identity and initial status.\n2. An active queued or running equivalent request may be reused according to existing job-owner semantics.\n3. Progress, completion, and coverage metrics are read through get_analysis_status.\n4. Tool does not require the LLM to poll source files directly.\n5. Initial queued acceptance is durably persisted before the worker starts. After acceptance, running, progress, and terminal job-metadata persistence are best-effort observability updates; failure to persist those updates does not abort an otherwise valid repository analysis."
   ],
   "freshness": [],
```

## C:\Temp\Contextor_Repo\tests\test_async_publication_receipt.py
```diff
--- a/tests/test_async_publication_receipt.py
+++ b/tests/test_async_publication_receipt.py
@@ -0,0 +1,138 @@
+"""Focused safety contracts for queued committed publication receipts."""
+
+from types import SimpleNamespace
+
+from contextor.core.live_state.ipc import CanonicalMutationCoordinator
+from contextor.core.live_state.publication_receipt import (
+    classify_publication_receipt,
+    committed_publication_key,
+    publish_committed_and_wait,
+)
+
+
+def _request(state_id="sid", revision=1, operation="submit_committed_publish"):
+    return {
+        "operation": operation,
+        "repo_id": "repo",
+        "state_id": state_id,
+        "revision": revision,
+        "idempotency_key": "fixed",
+    }
+
+
+def test_publication_idempotency_binds_exact_generation_without_conflict_execution():
+    executed = []
+    coordinator = CanonicalMutationCoordinator(
+        lambda request: executed.append(request) or {"status": "ok", "revision": 1},
+        lambda: 0,
+    )
+    try:
+        first = coordinator.submit(_request())
+        assert first["accepted"] is True
+        assert coordinator.submit(_request())["job_id"] == first["job_id"]
+        for conflicting in (_request(state_id="other"), _request(revision=2)):
+            assert coordinator.submit(conflicting) == {
+                "status": "error", "error": "publication_idempotency_conflict",
+            }
+        status = coordinator.status(first["job_id"])
+        assert status["requested_state_id"] == "sid"
+        assert status["requested_revision"] == 1
+        coordinator.close()
+        assert len(executed) == 1
+        assert executed[0]["state_id"] == "sid"
+    finally:
+        coordinator.close()
+
+
+def test_update_file_duplicate_preserves_existing_key_behavior():
+    coordinator = CanonicalMutationCoordinator(lambda _: {"status": "ok"}, lambda: 0)
+    try:
+        first = coordinator.submit({"file_path": "one.py", "idempotency_key": "fixed"})
+        second = coordinator.submit({"file_path": "two.py", "idempotency_key": "fixed"})
+        assert first["job_id"] == second["job_id"]
+    finally:
+        coordinator.close()
+
+
+def _terminal(state_id="sid", revision=1):
+    return {
+        "status": "ok", "job_id": "mu-1", "state": "completed",
+        "requested_state_id": state_id, "requested_revision": revision,
+        "response": {"status": "ok", "revision": 1},
+    }
+
+
+def _classify(receipt):
+    return classify_publication_receipt(
+        receipt, job_id="mu-1", service_instance_id="service",
+        process_start_identity="process", state_id="sid", revision=1,
+    )
+
+
+def test_receipt_requires_exact_job_generation_and_installed_revision():
+    assert _classify(_terminal())["live_publish_status"] == "success"
+    for receipt in (
+        {**_terminal(), "job_id": "mu-other"},
+        _terminal(state_id="other"),
+        _terminal(revision=2),
+        {**_terminal(), "response": {"status": "ok", "revision": 2}},
+        {"status": "error", "error": "unknown_mutation_job", "revision": 1},
+    ):
+        result = _classify(receipt)
+        assert result["live_publish_status"] != "success"
+        assert result["live_publish_revision"] is None
+
+
+def test_generation_key_is_deterministic_and_identity_sensitive():
+    key = committed_publication_key("repo", "sid", 1)
+    assert key.startswith("cp-") and len(key) == 67
+    assert key == committed_publication_key("repo", "sid", 1)
+    assert key != committed_publication_key("repo", "sid", 2)
+    assert key != committed_publication_key("repo", "other", 1)
+
+
+def test_receipt_uses_verified_service_identity_from_client():
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def submit_committed_publish(self, **kwargs):
+            self.submitted = kwargs
+            return {"status": "accepted", "accepted": True, "job_id": "mu-1"}
+
+        def mutation_status(self, job_id):
+            assert job_id == "mu-1"
+            return _terminal()
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
+    assert result["live_publish_service_instance_id"] == "service"
+    assert result["live_publish_process_start_identity"] == "process"
+    assert client.submitted["idempotency_key"] == committed_publication_key("repo", "sid", 1)
+
+
+def test_changed_service_instance_rejects_completion():
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def submit_committed_publish(self, **kwargs):
+            return {"status": "accepted", "accepted": True, "job_id": "mu-1"}
+
+        def mutation_status(self, job_id):
+            return _terminal()
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "replacement",
+                    "process_start_identity": "process"}
+
+    result = publish_committed_and_wait(
+        Client(), repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
+    )
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert result["live_publish_revision"] is None
```

## C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
```diff
--- a/tests/test_durable_verified_publish.py
+++ b/tests/test_durable_verified_publish.py
@@ -2,6 +2,7 @@
 
 import copy
 import threading
+import time
 from contextlib import contextmanager
 from multiprocessing import get_context
 from pathlib import Path
@@ -200,6 +201,33 @@
         "state": SimpleNamespace(state_id=state_id, revision=revision),
         **request_fields,
     })
+
+
+def test_queued_committed_publish_reuses_existing_worker_and_loads_committed_state(durable_harness):
+    committed, _ = durable_harness.commit(1)
+    server = durable_harness.server(state=None, revision=0)
+    server._repository_identity_reader = lambda: durable_harness.identity
+    request = {
+        "operation": "submit_committed_publish", "state_id": "sid",
+        "revision": 1, "origin": "mcp_analysis", "idempotency_key": "cp-test",
+        "trace_op": None,
+    }
+    accepted = server._dispatch(request)
+    assert accepted["status"] == "accepted"
+    assert server._dispatch(request)["job_id"] == accepted["job_id"]
+    assert server._dispatch({**request, "state_id": "other"})["error"] == "publication_idempotency_conflict"
+    deadline = time.monotonic() + 3
+    while time.monotonic() < deadline:
+        receipt = server._dispatch({"operation": "mutation_status", "job_id": accepted["job_id"]})
+        if receipt.get("state") in {"completed", "failed"}:
+            break
+        time.sleep(0.01)
+    assert receipt["state"] == "completed"
+    assert receipt["requested_state_id"] == "sid"
+    assert receipt["requested_revision"] == 1
+    assert receipt["response"]["revision"] == 1
+    assert server._state.state_id == committed.state_id
+    assert server._state.value == committed.value
 
 
 def _unchanged(server):
```

## C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
```diff
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -660,13 +660,9 @@
     observed = []
 
     class AlreadyInstalledClient:
-        def publish(
-            self,
-            state,
-            *,
-            origin="unknown",
-            acknowledge_installed=False,
-        ):
+        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")
+
+        def submit_committed_publish(self, *, state_id, revision, origin, idempotency_key, trace_op=None):
             try:
                 probe_lease = acquire_full_analysis(
                     repo,
@@ -678,23 +674,33 @@
             else:
                 release_full_analysis(probe_lease)
                 lease_held = False
-            revision = int(state.revision)
             observed.append(
                 {
                     "origin": origin,
-                    "acknowledge_installed": acknowledge_installed,
+                    "state_id": state_id,
                     "lease_held": lease_held,
                     "revision": revision,
                 }
             )
+            return {"status": "accepted", "accepted": True, "job_id": "mu-test"}
+
+        def mutation_status(self, job_id):
+            assert job_id == "mu-test"
             return {
                 "status": "ok",
-                "revision": revision,
-                "seq": 9,
-                "source": "committed_snapshot",
-                "already_installed": True,
-                "origin_verified": False,
+                "job_id": job_id,
+                "state": "completed",
+                "requested_state_id": observed[0]["state_id"],
+                "requested_revision": observed[0]["revision"],
+                "response": {
+                    "status": "ok", "revision": observed[0]["revision"],
+                    "already_installed": True,
+                },
             }
+
+        def authority_status(self):
+            return {"status": "ok", "service_instance_id": "service",
+                    "process_start_identity": "process"}
 
     client = AlreadyInstalledClient()
     monkeypatch.setattr(
@@ -712,7 +718,7 @@
     assert isinstance(analysis_result, AnalysisResult)
     assert len(observed) == 1
     assert observed[0]["origin"] == "mcp_analysis"
-    assert observed[0]["acknowledge_installed"] is True
+    assert observed[0]["state_id"] == analysis_result.live_publish_expected_state_id
     assert observed[0]["lease_held"] is True
     assert analysis_result.live_publish_status == "success"
     assert analysis_result.live_publish_revision == observed[0]["revision"]
```

## C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py
```diff
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -56,6 +56,53 @@
     return payload
 
 
+def test_pending_publication_reconciles_only_exact_job_on_same_authority(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    root = tmp_path
+    job = _create_job(root, 990, live_publish_status="pending_verification",
+                      live_publish_revision=None)
+    job.update({
+        "live_publish_job_id": "mu-exact",
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+    calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(service_instance_id="replacement",
+                                   process_start_identity="process")
+
+        def mutation_status(self, job_id):
+            calls.append(job_id)
+            return {"status": "ok", "job_id": job_id, "state": "completed",
+                    "requested_state_id": "sid", "requested_revision": 7,
+                    "response": {"status": "ok", "revision": 7}}
+
+    def connect(_root, *, reconcile_missing_endpoint_binding=True):
+        if reconcile_missing_endpoint_binding:
+            return None
+        return Client()
+
+    monkeypatch.setattr(live_state_module, "connect", connect)
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert result["live_publish_revision"] is None
+    assert calls == []
+    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "pending_verification"
+
+    Client.endpoint.service_instance_id = "service"
+    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+    assert result["live_publish_status"] == "success"
+    assert result["live_publish_revision"] == 7
+    assert calls == ["mu-exact"]
+    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "success"
+
+
 def test_analysis_status_concurrency__multiple_active_without_job_id_returns_ambiguity(tmp_path):
     root = tmp_path
     foreign_owner = os.getpid() + 100000
```


