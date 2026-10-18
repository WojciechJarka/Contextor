# CONTEXTOR_REGRESSION_26_MCP_WORKER_RESULT_FIX

## TASK
Controlled test-only correction of the _run_analysis_worker result contract. No production or documentation edits.

## HEAD_BEFORE
05a991f2c633935af2f989454bc23c6d9565da93

## HEAD_AFTER
05a991f2c633935af2f989454bc23c6d9565da93

## FILES_CHANGED
- tests/test_mcp_regressions.py

## ROOT_CAUSE
CONTRACT_PROVED: Contextor fetched the complete current _run_analysis_worker implementation at contextor/mcp/analysis_jobs.py:229-311. Its project branch returns ten keys, including six LIVE publication correlation fields. The original test expected only four keys, so its exact dictionary comparison had an outdated expected shape. Contextor direct static consumers: tests.test_full_analysis_coordination, tests.test_mcp_child_process_cleanup, tests.test_mcp_regressions.

## EXACT_IMPLEMENTATION
Added the six expected keys with None values to the existing exact dictionary assertion. Added one separate focused test with six distinct non-empty correlation values supplied by a mocked analysis result. No result status or revision was fabricated as success/recovery; the test keeps not_attempted and null published revision.

## FULL_RESULT_CONTRACT
The exact expected result is skipped_python_files, live_publish_status, live_publish_revision, live_publish_warning, live_publish_idempotency_key, live_publish_job_id, live_publish_service_instance_id, live_publish_process_start_identity, live_publish_expected_state_id, live_publish_expected_revision. The original skipped-file list and not_attempted status remain checked.

## NON_NULL_CORRELATION_PROOF
The focused test supplies canonical-key-123, exact-mutation-job-456, service-instance-789, process-start-012, state-345, and canonical revision 67 to the mocked result. Its exact entire-dictionary assertion confirms unchanged propagation of all six metadata values and absence of a fabricated publication verdict.

## ORIGINAL_REGRESSION_RESULT
Exact original and new focused tests: 2 passed, 1 third-party AuthlibDeprecationWarning, exit 0 (8.60s).

## TARGETED_NON_REGRESSION
Eleven related _run_analysis_worker and durable-status tests in tests/test_mcp_regressions.py were selected. First run: 10 passed, 1 failed, exit 1. The failure was test_analysis_job_persists_failure_for_later_polling with KeyError when indexing _analysis_tasks[accepted["job_id"]] at line 1008; it is outside the edited result-dictionary assertion. Exact isolated rerun of that test: 1 passed, exit 0. Exact same eleven-test selection rerun: 11 passed, exit 0 (4.42s). UNKNOWN: the cause of the first-run KeyError was not captured; no race or environment diagnosis is claimed. No change was made outside the approved test. Full repository suite was not run. git diff --check exited 0 (Git emitted an LF-to-CRLF working-copy notice).

## LIVE_REVISION_BEFORE_AFTER
Before edit: canonical revision 622, workspace_sync=verified. Immediately after edit, Contextor reported stale_source/out_of_sync at revision 622, accurately identifying disk divergence. After desktop watcher processing, revision 623, canonical_state=fresh, workspace_sync=verified, provenance=live. Contextor preview resolved the new test function from this fresh revision.

## WATCHER_EVENTS
get_live_events(after_revision=622) returned continuity=continuous, resync_required=false, revision 623, with one desktop_watcher UPDATED event for tests/test_mcp_regressions.py. No manual update_file call.

## RESTART_REQUIREMENTS
MCP_BACKEND_RESTART_REQUIRED=NO. LIVE_SERVICE_RESTART_REQUIRED=NO. Only test code changed; no process was restarted.

## FULL_DIFFS
```diff

diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index c9e5d62..5938d8b 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -1117,6 +1117,46 @@ def test_project_worker_carries_indexer_skips_into_durable_job_status(
         "live_publish_status": "not_attempted",
         "live_publish_revision": None,
         "live_publish_warning": None,
+        "live_publish_idempotency_key": None,
+        "live_publish_job_id": None,
+        "live_publish_service_instance_id": None,
+        "live_publish_process_start_identity": None,
+        "live_publish_expected_state_id": None,
+        "live_publish_expected_revision": None,
+    }
+
+
+def test_project_worker_preserves_live_publication_correlation_metadata(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    correlation = {
+        "live_publish_idempotency_key": "canonical-key-123",
+        "live_publish_job_id": "exact-mutation-job-456",
+        "live_publish_service_instance_id": "service-instance-789",
+        "live_publish_process_start_identity": "process-start-012",
+        "live_publish_expected_state_id": "state-345",
+        "live_publish_expected_revision": 67,
+    }
+
+    def fake_analyze_project(*_args, **_kwargs):
+        return [], SimpleNamespace(summary_data={"skipped_files": []}, **correlation)
+
+    monkeypatch.setattr(
+        analysis_jobs.ContextorFacade,
+        "analyze_project",
+        staticmethod(fake_analyze_project),
+    )
+
+    outcome = asyncio.run(analysis_jobs._run_analysis_worker("project", repo))
+
+    assert outcome == {
+        "skipped_python_files": [],
+        "live_publish_status": "not_attempted",
+        "live_publish_revision": None,
+        "live_publish_warning": None,
+        **correlation,
     }
 
 

```

## FINAL_VERDICT
PASS for the approved worker-result test contract: exact original and non-null correlation tests pass; the repeated related gate passes 11/11; LIVE workspace sync is verified. The initial related-test KeyError remains an unexplained observation and is recorded above without a root-cause claim.

