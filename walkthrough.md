# CONTEXTOR_REGRESSION_26_H3A_4_COMMITTED_PUBLICATION_FIX

## TASK
Controlled test-only migration of four H3A fault injections to the active committed LIVE publication protocol. Production unchanged.

## HEAD_BEFORE
761f99f9864367a268779a0cfcc2b18ecb7544ab

## HEAD_AFTER
761f99f9864367a268779a0cfcc2b18ecb7544ab (no commit)

## FILES_CHANGED
- tests/test_h3a_workspace_canonical_freshness.py

tests/test_incremental_phase_trace.py was already modified before this task and was not touched. walkthrough.md is this report.

## FOUR_CASE_CONTRACTS

U: Two LiveStateClient.submit_committed_publish calls each raise ConnectionResetError before sending; one lookup_committed_publish returns unknown_publication_job. Test asserts two identical generation/idempotency requests, one lookup, pending_verification, no job ID or published revision, canonical admission warning, full correlation in result and summary. Disk/FileState advance to P1; this controlled fixture's daemon remains P0. Pending status alone does not guarantee P0.

V: LiveStateClient.submit_committed_publish returns explicit error before enqueue, without actual submit. Test asserts one attempt, failed, no job ID or published revision, canonical warning "Publication admission rejected.", disk/FileState P1, daemon P0, and result/summary agreement.

Recovery: Real submit and committed snapshot installation execute. Wrapper delegates to original mutation_status and changes only a matching completed, status-ok receipt response copy to resync_required=True. Test observes original and patched terminal receipts, preserving job and generation identity; verifies daemon/disk/FileState P1, final authority service/process match, canonical key, recovery_required, published P1, canonical warning, and result/summary agreement.

Y: Synthetic accepted job ID is returned without a real submit. mutation_status for that ID returns the exact requested {status:rejected,revision:999}; CONFIRMATION_SECONDS=0 only in this test. Test verifies one status call, daemon P0, disk/FileState P1, pending_verification, no published revision, exact key/generation/authority correlation and result/summary agreement. No fake success receipt is used.

None of U/V/recovery/Y patches LiveStateClient.publish.

## FAULT_INJECTION_PROOF
U counts two submits and one lookup and compares full argument dictionaries. V counts its one rejected pre-enqueue submit. Recovery retains original mutation_status, records a real completed receipt with correct installed revision, records the modified copy with resync_required=True, and verifies unchanged job/generation. Y counts one synthetic admission and exactly one rejected status response for h3a-y-synthetic, with no actual submit. These are active protocol methods per Contextor publish_committed_and_wait source.

## STATUS_REVISION_WARNING_MATRIX

| Case | Status | Published revision | Warning |
|---|---|---|---|
| U | pending_verification | None | Publication admission and read-only job lookup unavailable. |
| V | failed | None | Publication admission rejected. |
| recovery | recovery_required | P1 | LIVE recovery verification required. |
| Y | pending_verification | None | Exact mutation job status unavailable. |

CONTRACT DISCREPANCY: The supplied design expected Y warning "Mutation status unavailable." with receipt exactly {status:rejected,revision:999}. Current classify_publication_receipt first checks that receipt.job_id equals the expected synthetic job ID; the stipulated response has no job_id, so it returns "Exact mutation job status unavailable." before reaching the top-level status check. The exact response and fail-closed status were retained. Achieving the stipulated warning would require changing the response shape (adding matching job/generation fields) or production ordering, both outside this approved literal contract. There is no pytest traceback for this discrepancy because the test asserts and passes against actual current behavior.

## DAEMON_DISK_FILESTATE_EVIDENCE
U/V/Y assert disk metadata and FileState at P1 while the controlled daemon snapshot remains P0. Recovery asserts all three at P1. This distinguishes durable commit from LIVE installation.

## FAIL_CLOSED_PROOF
U/Y retain pending_verification and None revision despite ambiguous/unknown evidence. V is an explicit pre-enqueue failure with None revision. Recovery exposes P1 only after a real exact completed mutation receipt and matching final authority. Correlation fields and summary_data equality are asserted. No test creates a synthetic successful installation.

## TARGETED_TEST_RESULTS
Four exact named H3A tests: 4 passed in 29.63 s. After one added recovery correlation assertion, focused rerun of recovery with W/X: 3 passed in 18.07 s. No full repository suite.

## FOCUSED_NON_REGRESSION
tests/test_async_publication_receipt.py: 9 passed in 1.00 s.
Existing H3A test_h3a_case_w_no_active_daemon_not_attempted and test_h3a_case_x_journal_ahead_canonical_cache_separation: both passed in the 3-test focused run above.
git diff --check passed.

## LIVE_REVISION_BEFORE_AFTER
Before 617; after 619, same activity epoch 5d758bf9339c4ac5a5816ab056e7f84b. Continuity=continuous; resync_required=false. Contextor test symbol source is canonical_state=fresh, workspace_sync=verified at revision 619. File edit context reports syntax diagnostics checked_and_none, zero errors. Contextor blast radius still identifies facade as direct production consumer of publish_committed_and_wait.

## WATCHER_EVENTS
Revision 618: desktop_watcher update_file UPDATED tests/test_h3a_workspace_canonical_freshness.py.
Revision 619: desktop_watcher update_file UPDATED the same test file after final assertion refinement.
No manual update_file.

## RESTART_REQUIREMENTS
MCP_BACKEND_RESTART_REQUIRED=NO. LIVE_SERVICE_RESTART_REQUIRED=NO. Only a test file changed; no process was restarted.

## FULL_DIFFS
Complete actual unified diff of the sole task-changed file follows.
```diff
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 8a14781..c09d9ef 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -1018,19 +1018,13 @@ def test_h3a_case_t_active_daemon_successful_publish(tmp_path):
 
 
 def test_h3a_case_u_active_daemon_publish_raises_failure_semantics(tmp_path, monkeypatch):
-    """Case U (H3A-H6 - Active Daemon + Publish Raises Exception):
-    - Active daemon running holding P0
-    - Publish fails with exception during full analysis
-    - EXPECT:
-      - disk snapshot = P1 (preserved)
-      - FileState = P1 (preserved)
-      - daemon remains P0
-      - analysis completes without error
-      - live_publish_status = 'failed'
-      - live_publish_revision = None
-      - live_publish_warning contains exception info
+    """Ambiguous committed admission stays pending with durable correlation.
+
+    These simulated transport errors occur before sending, so this fixture's
+    daemon remains at P0; pending verification alone does not imply that.
     """
     from contextor.core.live_state import LiveStateClient
+    from contextor.core.live_state.publication_receipt import committed_publication_key
     from contextor.core.live_state.store import load_snapshot, read_metadata
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
@@ -1051,11 +1045,19 @@ def test_h3a_case_u_active_daemon_publish_raises_failure_semantics(tmp_path, mon
         time.sleep(0.05)
         mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 888\n", encoding="utf-8")
 
-        # Mock publish to raise RuntimeError
-        orig_publish = LiveStateClient.publish
-        def mock_publish(self, state, *args, **kwargs):
+        submissions = []
+        lookups = []
+
+        def mock_submit(self, **kwargs):
+            submissions.append(kwargs)
             raise ConnectionResetError("Simulated daemon socket drop")
-        monkeypatch.setattr(LiveStateClient, "publish", mock_publish)
+
+        def mock_lookup(self, **kwargs):
+            lookups.append(kwargs)
+            return {"status": "error", "error": "unknown_publication_job"}
+
+        monkeypatch.setattr(LiveStateClient, "submit_committed_publish", mock_submit)
+        monkeypatch.setattr(LiveStateClient, "lookup_committed_publish", mock_lookup)
 
         errors, res = ContextorFacade.analyze_project(str(repo))
         assert not errors
@@ -1069,34 +1071,45 @@ def test_h3a_case_u_active_daemon_publish_raises_failure_semantics(tmp_path, mon
         sm = FileStateManager(str(cache))
         assert sm.revision == p1
 
-        # Restore publish and check daemon state is still P0
-        monkeypatch.setattr(LiveStateClient, "publish", orig_publish)
         daemon_snap = server_client.snapshot()
         daemon_state = daemon_snap.get("state")
         assert getattr(daemon_state, "revision", None) == p0
 
-        # Check facade result metadata reports failure
-        assert res.live_publish_status == "failed"
+        assert len(submissions) == 2
+        assert len(lookups) == 1
+        key = committed_publication_key(identity.repo_id, res.live_publish_expected_state_id, p1)
+        assert submissions[0] == submissions[1] == {
+            "state_id": res.live_publish_expected_state_id,
+            "revision": p1,
+            "origin": "desktop_analysis",
+            "idempotency_key": key,
+        }
+        assert lookups[0] == {
+            "idempotency_key": key,
+            "state_id": res.live_publish_expected_state_id,
+            "revision": p1,
+        }
+        assert res.live_publish_status == "pending_verification"
         assert res.live_publish_revision is None
-        assert res.live_publish_warning is not None
-        assert "ConnectionResetError" in res.live_publish_warning
-        assert "Simulated daemon socket drop" in res.live_publish_warning
-        assert res.summary_data.get("live_publish_status") == "failed"
+        assert res.live_publish_job_id is None
+        assert res.live_publish_warning == "Publication admission and read-only job lookup unavailable."
+        assert res.live_publish_idempotency_key == key
+        assert res.live_publish_expected_revision == p1
+        assert res.live_publish_service_instance_id == server_client.endpoint.service_instance_id
+        assert res.live_publish_process_start_identity == server_client.endpoint.process_start_identity
+        for field in (
+            "live_publish_status", "live_publish_revision", "live_publish_warning",
+            "live_publish_job_id", "live_publish_idempotency_key",
+            "live_publish_service_instance_id", "live_publish_process_start_identity",
+            "live_publish_expected_state_id", "live_publish_expected_revision",
+        ):
+            assert res.summary_data[field] == getattr(res, field)
     finally:
         _stop_authoritative_live(repo, server_client)
 
 
 def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkeypatch):
-    """Case V (H3A-H6 - Active Daemon + Explicit Failure Response Dict):
-    - Active daemon returns {'status': 'error', 'error': 'daemon_busy'}
-    - EXPECT:
-      - disk snapshot = P1 (preserved)
-      - FileState = P1 (preserved)
-      - daemon remains P0
-      - live_publish_status = 'failed'
-      - live_publish_revision = None
-      - live_publish_warning = 'daemon_busy'
-    """
+    """Explicit committed admission rejection leaves the daemon at P0."""
     from contextor.core.live_state import LiveStateClient
     from contextor.core.live_state.store import load_snapshot, read_metadata
     from contextor.core.paths import repo_cache_dir
@@ -1118,11 +1131,13 @@ def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkey
         time.sleep(0.05)
         mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 999\n", encoding="utf-8")
 
-        # Mock publish to return error dict
-        orig_publish = LiveStateClient.publish
-        def mock_publish(self, state, *args, **kwargs):
+        submissions = []
+
+        def mock_submit(self, **kwargs):
+            submissions.append(kwargs)
             return {"status": "error", "error": "daemon_busy_rejecting_publish"}
-        monkeypatch.setattr(LiveStateClient, "publish", mock_publish)
+
+        monkeypatch.setattr(LiveStateClient, "submit_committed_publish", mock_submit)
 
         errors, res = ContextorFacade.analyze_project(str(repo))
         assert not errors
@@ -1136,8 +1151,6 @@ def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkey
         sm = FileStateManager(str(cache))
         assert sm.revision == p1
 
-        # Restore publish and check daemon state is still P0
-        monkeypatch.setattr(LiveStateClient, "publish", orig_publish)
         daemon_snap = server_client.snapshot()
         daemon_state = daemon_snap.get("state")
         assert getattr(daemon_state, "revision", None) == p0
@@ -1145,34 +1158,96 @@ def test_h3a_case_v_active_daemon_publish_failure_response_dict(tmp_path, monkey
         # Check facade result metadata reports failure
         assert res.live_publish_status == "failed"
         assert res.live_publish_revision is None
-        assert res.live_publish_warning == "daemon_busy_rejecting_publish"
-        assert res.summary_data.get("live_publish_status") == "failed"
+        assert res.live_publish_job_id is None
+        assert res.live_publish_warning == "Publication admission rejected."
+        assert len(submissions) == 1
+        assert submissions[0]["revision"] == p1
+        for field in (
+            "live_publish_status", "live_publish_revision", "live_publish_warning",
+            "live_publish_job_id", "live_publish_idempotency_key",
+            "live_publish_expected_state_id", "live_publish_expected_revision",
+        ):
+            assert res.summary_data[field] == getattr(res, field)
     finally:
         _stop_authoritative_live(repo, server_client)
 
 
 def test_full_publish_accepted_recovery_preserves_revision_and_warning(tmp_path, monkeypatch):
     from contextor.core.live_state import LiveStateClient
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+    from contextor.core.live_state.store import read_metadata
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.repository_identity import require_repository_identity
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
+    identity = require_repository_identity(repo)
+    cache = repo_cache_dir(repo)
+    p0 = read_metadata(cache).revision
     server_client = _start_authoritative_live(repo)
     try:
         mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 333\n", encoding="utf-8")
-        monkeypatch.setattr(
-            LiveStateClient, "publish",
-            lambda self, state, **kwargs: {
-                "status": "ok", "revision": state.revision,
-                "resync_required": True, "warning": "release unverified",
-            },
-        )
+        original_status = LiveStateClient.mutation_status
+        terminal_receipts = []
+        patched_receipts = []
+
+        def recovery_status(self, job_id):
+            receipt = original_status(self, job_id)
+            if (
+                receipt.get("status") == "ok"
+                and receipt.get("job_id") == job_id
+                and receipt.get("state") == "completed"
+                and isinstance(receipt.get("response"), dict)
+                and receipt["response"].get("status") == "ok"
+                and receipt["response"].get("revision") == receipt.get("requested_revision")
+            ):
+                terminal_receipts.append(receipt)
+                patched = {
+                    **receipt,
+                    "response": {**receipt["response"], "resync_required": True},
+                }
+                patched_receipts.append(patched)
+                return patched
+            return receipt
+
+        monkeypatch.setattr(LiveStateClient, "mutation_status", recovery_status)
         errors, result = ContextorFacade.analyze_project(str(repo))
         assert not errors
+        assert result is not None
+        p1 = read_metadata(cache).revision
+        assert p1 > p0
+        assert FileStateManager(str(cache)).revision == p1
+        assert server_client.snapshot()["state"].revision == p1
+        assert terminal_receipts
+        assert terminal_receipts[-1]["job_id"] == result.live_publish_job_id
+        assert terminal_receipts[-1]["requested_state_id"] == result.live_publish_expected_state_id
+        assert terminal_receipts[-1]["requested_revision"] == p1
+        assert terminal_receipts[-1]["response"]["revision"] == p1
+        assert terminal_receipts[-1]["response"].get("resync_required") is not True
+        assert patched_receipts[-1]["response"]["resync_required"] is True
+        assert patched_receipts[-1]["job_id"] == terminal_receipts[-1]["job_id"]
+        assert patched_receipts[-1]["requested_state_id"] == terminal_receipts[-1]["requested_state_id"]
+        assert patched_receipts[-1]["requested_revision"] == p1
         assert result.live_publish_status == "recovery_required"
-        assert result.live_publish_revision is not None
-        assert result.live_publish_warning == "release unverified"
-        assert result.summary_data["live_publish_status"] == "recovery_required"
-        assert result.summary_data["live_publish_revision"] == result.live_publish_revision
+        assert result.live_publish_revision == p1
+        assert result.live_publish_warning == "LIVE recovery verification required."
+        assert result.live_publish_expected_revision == p1
+        assert result.live_publish_service_instance_id == server_client.endpoint.service_instance_id
+        assert result.live_publish_process_start_identity == server_client.endpoint.process_start_identity
+        assert result.live_publish_idempotency_key == committed_publication_key(
+            identity.repo_id, result.live_publish_expected_state_id, p1
+        )
+        authority = server_client.authority_status()
+        assert authority["service_instance_id"] == result.live_publish_service_instance_id
+        assert authority["process_start_identity"] == result.live_publish_process_start_identity
+        for field in (
+            "live_publish_status", "live_publish_revision", "live_publish_warning",
+            "live_publish_job_id", "live_publish_idempotency_key",
+            "live_publish_service_instance_id", "live_publish_process_start_identity",
+            "live_publish_expected_state_id", "live_publish_expected_revision",
+        ):
+            assert result.summary_data[field] == getattr(result, field)
     finally:
         _stop_authoritative_live(repo, server_client)
 
@@ -1285,17 +1360,20 @@ def test_h3a_case_x_journal_ahead_canonical_cache_separation(tmp_path):
 
 
 def test_h3a_case_y_unknown_status_facade_fail_closed(tmp_path, monkeypatch):
-    """Case Y (H3A-H7 - Unknown Status in Facade Fails Closed):
-    - Client returns {'status': 'rejected', 'revision': 999}
-    - EXPECT:
-      - live_publish_status == 'failed'
-      - live_publish_revision is None
-      - live_publish_warning is not None and mentions rejected
-    """
+    """Unknown committed mutation receipt remains pending, never success."""
     from contextor.core.live_state import LiveStateClient
+    from contextor.core.live_state import publication_receipt
+    from contextor.core.live_state.publication_receipt import committed_publication_key
+    from contextor.core.live_state.store import read_metadata
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.repository_identity import require_repository_identity
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
+    identity = require_repository_identity(repo)
+    cache = repo_cache_dir(repo)
+    p0 = read_metadata(cache).revision
 
     client = _start_authoritative_live(repo)
 
@@ -1303,22 +1381,51 @@ def test_h3a_case_y_unknown_status_facade_fail_closed(tmp_path, monkeypatch):
         time.sleep(0.05)
         mod_a.write_text("def compute_data(x: int) -> int:\n    return x * 12345\n", encoding="utf-8")
 
-        monkeypatch.setattr(
-            LiveStateClient,
-            "publish",
-            lambda self, state, *args, **kwargs: {"status": "rejected", "revision": 999},
-        )
+        submissions = []
+        status_calls = []
+
+        def synthetic_submit(self, **kwargs):
+            submissions.append(kwargs)
+            return {"status": "accepted", "accepted": True, "job_id": "h3a-y-synthetic"}
+
+        def unknown_status(self, job_id):
+            status_calls.append(job_id)
+            return {"status": "rejected", "revision": 999}
+
+        monkeypatch.setattr(LiveStateClient, "submit_committed_publish", synthetic_submit)
+        monkeypatch.setattr(LiveStateClient, "mutation_status", unknown_status)
+        monkeypatch.setattr(publication_receipt, "CONFIRMATION_SECONDS", 0.0)
 
         errors, res = ContextorFacade.analyze_project(str(repo))
         assert not errors
         assert res is not None
 
-        assert res.live_publish_status == "failed"
+        p1 = read_metadata(cache).revision
+        assert p1 > p0
+        assert FileStateManager(str(cache)).revision == p1
+        assert client.snapshot()["state"].revision == p0
+        assert len(submissions) == 1
+        assert status_calls == ["h3a-y-synthetic"]
+        assert res.live_publish_status == "pending_verification"
         assert res.live_publish_revision is None
-        assert res.live_publish_warning is not None
-        assert "rejected" in res.live_publish_warning
-        assert res.summary_data.get("live_publish_status") == "failed"
-        assert res.summary_data.get("live_publish_revision") is None
+        assert res.live_publish_job_id == "h3a-y-synthetic"
+        assert res.live_publish_warning == "Exact mutation job status unavailable."
+        assert res.live_publish_idempotency_key == committed_publication_key(
+            identity.repo_id, res.live_publish_expected_state_id, p1
+        )
+        assert submissions[0]["idempotency_key"] == res.live_publish_idempotency_key
+        assert submissions[0]["state_id"] == res.live_publish_expected_state_id
+        assert submissions[0]["revision"] == p1
+        assert res.live_publish_expected_revision == p1
+        assert res.live_publish_service_instance_id == client.endpoint.service_instance_id
+        assert res.live_publish_process_start_identity == client.endpoint.process_start_identity
+        for field in (
+            "live_publish_status", "live_publish_revision", "live_publish_warning",
+            "live_publish_job_id", "live_publish_idempotency_key",
+            "live_publish_service_instance_id", "live_publish_process_start_identity",
+            "live_publish_expected_state_id", "live_publish_expected_revision",
+        ):
+            assert res.summary_data[field] == getattr(res, field)
     finally:
         _stop_authoritative_live(repo, client)
 
```
## FINAL_VERDICT
PARTIAL against the literal approved design solely because Y's required warning text conflicts with the exact stipulated receipt shape and current classifier order. The four migrated tests and all named focused gates pass; no production change or out-of-scope mock change was made.

STOP. Await `proceduj`.
