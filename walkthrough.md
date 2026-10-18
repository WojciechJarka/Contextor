TASK=CONTEXTOR_C38E2Q_R2_STATUS_RECOVERY_INVARIANTS
MODE=FOCUSED CORRECTION

HEAD_BEFORE=cca8b8aa035fafbd373ddbf3f86133eeed1aaa58
HEAD_AFTER=cca8b8aa035fafbd373ddbf3f86133eeed1aaa58

FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
- C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py

AUTHORITY_TRI_STATE_CLASSIFICATION
- connect(...) returning None: retains pending_verification and skips authority and mutation lookup.
- Endpoint identity explicitly different from the durable service/process identity: returns unverified_authority_changed and skips receipt lookup.
- authority_status transport exceptions, non-object, unavailable/error status, or missing identity fields: retains pending_verification and skips mutation lookup. Missing evidence is not classified as replacement.
- Explicit authority service/process mismatch: returns unverified_authority_changed and skips mutation lookup.
- Matching endpoint and authority service/process identities with status=ok: continues existing receipt reconciliation.
- The caller uses connect(root, reconcile_missing_endpoint_binding=False); the LIVE connection implementation and normal caller defaults are unchanged.

LOOKUP_IDENTITY_VALIDATION
Before accepting a recovered job ID, the handler requires a dict, status=ok, a nonempty string job_id, exact requested_state_id, and requested_revision whose exact type is int and whose value equals the expected revision. Persistence occurs only after these checks.

INVALID_LOOKUP_NON_PERSISTENCE
Targeted regressions prove wrong state ID, wrong revision, and boolean revision leave live_publish_job_id unset, preserve the canonical idempotency key, remain pending_verification, and do not call mutation_status. The handler performs no submit, publication, update_file, or FULL request.

RECOVERY_RETRY_PROOF
A first invalid lookup leaves the pending durable record unchanged. A later read-only lookup for the same canonical key returns the exact generation; the handler persists that job ID and accepts the matching successful terminal receipt. The test asserts reconciliation connects with reconciliation disabled on both calls.

TARGETED_TEST_RESULTS
- Isolated file: & .\.venv\Scripts\python.exe -m pytest tests/mcp/tools/test_analysis_status_concurrency.py -q — 36 passed, 1 existing AuthlibDeprecationWarning, 6.42s.
- Required named C38E2Q focused selection: tests/test_live_mutation_coordinator.py tests/test_durable_verified_publish.py tests/test_live_state_ipc.py tests/mcp/tools/test_analysis_status_concurrency.py tests/test_full_analysis_coordination.py tests/test_async_publication_receipt.py — 243 passed, 1 existing AuthlibDeprecationWarning, 130.13s.
- Full repository pytest suite was not run.

PREVIOUS_FAILURE_REPRODUCTION_STATUS
The previously recorded failure `tests/test_live_state_ipc.py::test_normal_service_shutdown_preserves_authority_event_chronology` with `RuntimeDomainError: lock_root must be owned by cache_root for this runtime layout` did not reproduce in the required six-file selection; that run completed with 243 passed and 0 failed. No failing test order or traceback exists in this run.

WATCHER_EVENTS
- Revision 603: desktop_watcher / update_file / UPDATED / C:\Temp\Contextor_Repo\contextor\mcp\tools\get_analysis_status.py
- Revision 604: desktop_watcher / update_file / UPDATED / C:\Temp\Contextor_Repo\tests\mcp\tools\test_analysis_status_concurrency.py
- Event query after revision 603 returned continuity=continuous, resync_required=false; latest_revision=604.

WORKSPACE_SYNC
- contextor/mcp/tools/get_analysis_status.py: verified at canonical LIVE revision 604; syntax diagnostics checked_and_none, 0 errors.
- tests/mcp/tools/test_analysis_status_concurrency.py: verified at canonical LIVE revision 604; syntax diagnostics checked_and_none, 0 errors.

LIVE_REVISION_BEFORE_AFTER=602 -> 604
MCP_BACKEND_RESTART_REQUIRED=YES
LIVE_SERVICE_RESTART_REQUIRED=YES
RESTARTS_PERFORMED=NO

FINAL_VERDICT=C38E2Q_R2_SOURCE_PASS_PENDING_RUNTIME

FULL_DIFFS
The following are complete unified diffs for every changed source/test file. This report is excluded from FILES_CHANGED.
diff --git a/contextor/mcp/tools/get_analysis_status.py b/contextor/mcp/tools/get_analysis_status.py
index eecd05f..2d6d115 100644
--- a/contextor/mcp/tools/get_analysis_status.py
+++ b/contextor/mcp/tools/get_analysis_status.py
@@ -124,28 +124,55 @@ def get_analysis_status(
             client = None
         expected_service = job.get("live_publish_service_instance_id")
         expected_process = job.get("live_publish_process_start_identity")
-        if client is None:
-            pass  # Retain the durable pending status.
-        else:
-            try:
-                authority = client.authority_status()
-            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+        if client is not None:
+            endpoint_service = client.endpoint.service_instance_id
+            endpoint_process = client.endpoint.process_start_identity
+            endpoint_identity_available = (
+                isinstance(endpoint_service, str) and bool(endpoint_service)
+                and isinstance(endpoint_process, str) and bool(endpoint_process)
+            )
+            if endpoint_identity_available and (
+                endpoint_service != expected_service
+                or endpoint_process != expected_process
+            ):
+                job = {
+                    **job,
+                    "live_publish_status": "unverified_authority_changed",
+                    "live_publish_revision": None,
+                    "live_publish_warning": "LIVE authority identity changed before receipt verification.",
+                }
+                endpoint_identity_available = False
+            if endpoint_identity_available:
+                try:
+                    authority = client.authority_status()
+                except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
+                    authority = None
+            else:
                 authority = None
-        if client is not None and (
-            client.endpoint.service_instance_id != expected_service
-            or client.endpoint.process_start_identity != expected_process
-            or not isinstance(authority, dict)
-            or authority.get("status") != "ok"
-            or authority.get("service_instance_id") != expected_service
-            or authority.get("process_start_identity") != expected_process
-        ):
-            job = {
-                **job,
-                "live_publish_status": "unverified_authority_changed",
-                "live_publish_revision": None,
-                "live_publish_warning": "LIVE authority identity changed before receipt verification.",
-            }
-        elif client is not None:
+        if client is not None and authority is not None:
+            if not isinstance(authority, dict) or authority.get("status") != "ok":
+                authority = None
+            else:
+                authority_service = authority.get("service_instance_id")
+                authority_process = authority.get("process_start_identity")
+                authority_identity_available = (
+                    isinstance(authority_service, str) and bool(authority_service)
+                    and isinstance(authority_process, str) and bool(authority_process)
+                )
+                if authority_identity_available and (
+                    authority_service != expected_service
+                    or authority_process != expected_process
+                ):
+                    job = {
+                        **job,
+                        "live_publish_status": "unverified_authority_changed",
+                        "live_publish_revision": None,
+                        "live_publish_warning": "LIVE authority identity changed before receipt verification.",
+                    }
+                    authority = None
+                elif not authority_identity_available:
+                    authority = None
+        if client is not None and isinstance(authority, dict) and authority.get("status") == "ok":
             mutation_job_id = job.get("live_publish_job_id")
             if not isinstance(mutation_job_id, str):
                 state_id = job["live_publish_expected_state_id"]
@@ -158,9 +185,7 @@ def get_analysis_status(
                         expected_key = committed_publication_key(repo_id, state_id, revision)
                     except ValueError:
                         expected_key = None
-                if not isinstance(stored_key, str) or stored_key != expected_key:
-                    authority = None
-                else:
+                if isinstance(stored_key, str) and stored_key == expected_key:
                     try:
                         lookup = client.lookup_committed_publish(
                             idempotency_key=stored_key, state_id=state_id,
@@ -168,16 +193,21 @@ def get_analysis_status(
                         )
                     except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                         lookup = None
-                    if isinstance(lookup, dict) and lookup.get("status") == "ok":
-                        mutation_job_id = lookup.get("job_id")
-                        if isinstance(mutation_job_id, str) and mutation_job_id:
-                            job = {**job, "live_publish_job_id": mutation_job_id}
-                            try:
-                                analysis_jobs._write_analysis_job(root, job)
-                            except OSError:
-                                pass
-                    else:
-                        mutation_job_id = None
+                    if (
+                        isinstance(lookup, dict)
+                        and lookup.get("status") == "ok"
+                        and isinstance(lookup.get("job_id"), str)
+                        and bool(lookup.get("job_id"))
+                        and lookup.get("requested_state_id") == state_id
+                        and type(lookup.get("requested_revision")) is int
+                        and lookup.get("requested_revision") == revision
+                    ):
+                        mutation_job_id = lookup["job_id"]
+                        job = {**job, "live_publish_job_id": mutation_job_id}
+                        try:
+                            analysis_jobs._write_analysis_job(root, job)
+                        except OSError:
+                            pass
             if isinstance(mutation_job_id, str) and mutation_job_id:
                 try:
                     receipt = client.mutation_status(mutation_job_id)
diff --git a/tests/mcp/tools/test_analysis_status_concurrency.py b/tests/mcp/tools/test_analysis_status_concurrency.py
index 9d7e7ef..4ab3c0e 100644
--- a/tests/mcp/tools/test_analysis_status_concurrency.py
+++ b/tests/mcp/tools/test_analysis_status_concurrency.py
@@ -56,6 +56,336 @@ def _create_job(
     return payload
 
 
+def _pending_publication_job(root: Path, suffix: int = 980) -> dict:
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+
+    job = _create_job(
+        root,
+        suffix,
+        live_publish_status="pending_verification",
+        live_publish_revision=None,
+    )
+    job.update({
+        "live_publish_job_id": None,
+        "live_publish_idempotency_key": committed_publication_key(
+            "repo-id", "sid", 7
+        ),
+        "live_publish_service_instance_id": "service",
+        "live_publish_process_start_identity": "process",
+        "live_publish_expected_state_id": "sid",
+        "live_publish_expected_revision": 7,
+    })
+    analysis_jobs._write_analysis_job(root, job)
+    return job
+
+
+def _patch_reconciliation_diagnostics(monkeypatch) -> None:
+    import contextor.mcp.tools.get_analysis_status as status_module
+
+    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
+    monkeypatch.setattr(
+        status_module,
+        "diagnostics_summary_for_completed_job",
+        lambda _summary, _job: {"attention_required": False},
+    )
+
+
+def _status_response(root: Path, job: dict) -> dict:
+    return json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
+
+
+@pytest.mark.parametrize(
+    "authority_result",
+    [
+        TimeoutError("authority timeout"),
+        ConnectionError("authority transport failed"),
+        None,
+        {"status": "unavailable"},
+        {"status": "error", "error": "authority_unavailable"},
+    ],
+    ids=["timeout", "transport-error", "non-object", "unavailable", "error-status"],
+)
+def test_authority_status_uncertainty_retains_pending_without_lookup(
+    tmp_path, monkeypatch, authority_result
+):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            if isinstance(authority_result, BaseException):
+                raise authority_result
+            return authority_result
+
+        def lookup_committed_publish(self, **kwargs):
+            calls.append(("lookup", kwargs))
+            raise AssertionError("uncertain authority must not trigger lookup")
+
+        def mutation_status(self, job_id):
+            calls.append(("status", job_id))
+            raise AssertionError("uncertain authority must not trigger status")
+
+    monkeypatch.setattr(
+        live_state_module,
+        "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
+    )
+
+    result = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert result["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_job_id"] is None
+    assert calls == []
+
+
+def test_missing_client_retains_pending_without_mutation_lookup(tmp_path, monkeypatch):
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    connect_calls = []
+
+    def connect(_root, *, reconcile_missing_endpoint_binding=True):
+        connect_calls.append(reconcile_missing_endpoint_binding)
+        return None
+
+    monkeypatch.setattr(live_state_module, "connect", connect)
+    result = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert connect_calls == [False]
+    assert result["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_job_id"] is None
+
+
+def test_missing_authority_identity_is_uncertain_not_replacement(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    lookup_calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            return {"status": "ok", "repo_id": "repo-id"}
+
+        def lookup_committed_publish(self, **kwargs):
+            lookup_calls.append(kwargs)
+
+    monkeypatch.setattr(
+        live_state_module,
+        "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
+    )
+    result = _status_response(tmp_path, job)
+    assert result["live_publish_status"] == "pending_verification"
+    assert lookup_calls == []
+
+
+def test_explicit_authority_service_mismatch_is_unverified(tmp_path, monkeypatch):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    lookup_calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            return {
+                "status": "ok",
+                "service_instance_id": "replacement",
+                "process_start_identity": "process",
+                "repo_id": "repo-id",
+            }
+
+        def lookup_committed_publish(self, **kwargs):
+            lookup_calls.append(kwargs)
+
+    monkeypatch.setattr(
+        live_state_module,
+        "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
+    )
+    result = _status_response(tmp_path, job)
+    assert result["live_publish_status"] == "unverified_authority_changed"
+    assert lookup_calls == []
+
+
+@pytest.mark.parametrize(
+    "lookup_result",
+    [
+        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "other",
+         "requested_revision": 7},
+        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "sid",
+         "requested_revision": 8},
+        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "sid",
+         "requested_revision": True},
+    ],
+    ids=["wrong-state-id", "wrong-revision", "boolean-revision"],
+)
+def test_invalid_lookup_identity_is_not_persisted(
+    tmp_path, monkeypatch, lookup_result
+):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            return {
+                "status": "ok",
+                "service_instance_id": "service",
+                "process_start_identity": "process",
+                "repo_id": "repo-id",
+            }
+
+        def lookup_committed_publish(self, **kwargs):
+            calls.append(("lookup", kwargs))
+            return lookup_result
+
+        def mutation_status(self, mutation_job_id):
+            calls.append(("status", mutation_job_id))
+            raise AssertionError("invalid lookup must not reach mutation status")
+
+        def submit_committed_publish(self, **kwargs):
+            calls.append(("submit", kwargs))
+            raise AssertionError("status recovery must never submit")
+
+        def publish(self, **kwargs):
+            calls.append(("publish", kwargs))
+            raise AssertionError("status recovery must never publish")
+
+        def update_file(self, **kwargs):
+            calls.append(("update_file", kwargs))
+            raise AssertionError("status recovery must never update_file")
+
+        def analyze_project(self, **kwargs):
+            calls.append(("full", kwargs))
+            raise AssertionError("status recovery must never run FULL")
+
+    monkeypatch.setattr(
+        live_state_module,
+        "connect",
+        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
+    )
+    result = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert result["live_publish_status"] == "pending_verification"
+    assert result["live_publish_job_id"] is None
+    assert stored["live_publish_status"] == "pending_verification"
+    assert stored["live_publish_job_id"] is None
+    assert stored["live_publish_idempotency_key"] == job[
+        "live_publish_idempotency_key"
+    ]
+    assert [name for name, _ in calls] == ["lookup"]
+
+
+def test_invalid_lookup_then_valid_lookup_recovers_original_publication(
+    tmp_path, monkeypatch
+):
+    from types import SimpleNamespace
+    import contextor.core.live_state as live_state_module
+
+    _patch_reconciliation_diagnostics(monkeypatch)
+    job = _pending_publication_job(tmp_path)
+    calls = []
+
+    class Client:
+        endpoint = SimpleNamespace(
+            service_instance_id="service", process_start_identity="process"
+        )
+
+        def authority_status(self):
+            return {
+                "status": "ok",
+                "service_instance_id": "service",
+                "process_start_identity": "process",
+                "repo_id": "repo-id",
+            }
+
+        def lookup_committed_publish(self, **kwargs):
+            calls.append(("lookup", kwargs))
+            if sum(name == "lookup" for name, _ in calls) == 1:
+                return {
+                    "status": "ok", "job_id": "mu-wrong",
+                    "requested_state_id": "other", "requested_revision": 7,
+                }
+            return {
+                "status": "ok", "job_id": "mu-exact",
+                "requested_state_id": "sid", "requested_revision": 7,
+            }
+
+        def mutation_status(self, mutation_job_id):
+            calls.append(("status", mutation_job_id))
+            return {
+                "status": "ok", "job_id": mutation_job_id, "state": "completed",
+                "requested_state_id": "sid", "requested_revision": 7,
+                "response": {"status": "ok", "revision": 7},
+            }
+
+        def submit_committed_publish(self, **kwargs):
+            raise AssertionError("recovery retry must never submit")
+
+        def publish(self, **kwargs):
+            raise AssertionError("recovery retry must never publish")
+
+        def update_file(self, **kwargs):
+            raise AssertionError("recovery retry must never update_file")
+
+        def analyze_project(self, **kwargs):
+            raise AssertionError("recovery retry must never run FULL")
+
+    connect_flags = []
+
+    def connect(_root, *, reconcile_missing_endpoint_binding=True):
+        connect_flags.append(reconcile_missing_endpoint_binding)
+        return Client()
+
+    monkeypatch.setattr(live_state_module, "connect", connect)
+    first = _status_response(tmp_path, job)
+    after_invalid = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert first["live_publish_status"] == "pending_verification"
+    assert after_invalid["live_publish_job_id"] is None
+    assert after_invalid["live_publish_idempotency_key"] == job[
+        "live_publish_idempotency_key"
+    ]
+
+    second = _status_response(tmp_path, job)
+    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
+    assert second["live_publish_status"] == "success"
+    assert second["live_publish_job_id"] == "mu-exact"
+    assert stored["live_publish_status"] == "success"
+    assert stored["live_publish_job_id"] == "mu-exact"
+    assert [name for name, _ in calls] == ["lookup", "lookup", "status"]
+    assert connect_flags == [False, False]
+
+
 def test_pending_publication_reconciles_only_exact_job_on_same_authority(tmp_path, monkeypatch):
     from types import SimpleNamespace
     import contextor.core.live_state as live_state_module

