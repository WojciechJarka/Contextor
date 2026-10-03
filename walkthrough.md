STATUS=STOP_TARGETED_COMMAND_ERROR
FILES_CHANGED=contextor/mcp/runtime.py; contextor/mcp/diagnostics.py; tests/mcp/test_live_diagnostics_narrow.py; tests/test_mcp_diagnostics.py

FULL_DIFFS=
```diff
diff --git a/contextor/mcp/diagnostics.py b/contextor/mcp/diagnostics.py
index 7ee0e0c..4760280 100644
--- a/contextor/mcp/diagnostics.py
+++ b/contextor/mcp/diagnostics.py
@@ -187,7 +187,10 @@ def inject_diagnostics_summary(
     root = Path(root_path).expanduser().resolve() if root_path else None
     if root is None:
         return result
-    summary = diagnostics_summary(root)
+    try:
+        summary = diagnostics_summary(root)
+    except Exception:
+        summary = diagnostics_summary_for_state(None)
     payload.setdefault("diagnostics_summary", summary)
     payload.setdefault("diagnostics_attention_required", summary["attention_required"])
     serialized = json.dumps(payload, indent=2, ensure_ascii=False)
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index 92cc969..dee186a 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -5,6 +5,7 @@ from pathlib import Path
 import threading
 from typing import Any, Iterator
 
+from contextor.core.live_state.runtime_domain import RuntimeDomainError
 from contextor.core.lineage_query.live_query import (
     LiveSymbolLineageQueryResult,
 )
@@ -101,6 +102,7 @@ def query_live_diagnostics_summary_narrow(
         ConnectionError,
         TimeoutError,
         RuntimeError,
+        RuntimeDomainError,
     ) as exc:
         return LiveDiagnosticsSummaryTransportResult(
             status="error",
             error="canonical_live_transport_error",
diff --git a/tests/mcp/test_live_diagnostics_narrow.py b/tests/mcp/test_live_diagnostics_narrow.py
index 31719ea..87d6b9a 100644
--- a/tests/mcp/test_live_diagnostics_narrow.py
+++ b/tests/mcp/test_live_diagnostics_narrow.py
@@ -6,6 +6,7 @@ from types import SimpleNamespace
 import pytest
 
 import contextor.core.live_state as live_state
+from contextor.core.live_state.runtime_domain import RuntimeDomainError
 from contextor.core.diagnostics_projection import (
     diagnostics_summary_for_state,
 )
@@ -391,6 +392,40 @@ def test_diagnostics_summary_transport_error_fails_closed_without_cache(
     )
 
 
+def test_narrow_live_diagnostics_query_treats_runtime_domain_error_as_transport_error(
+    monkeypatch,
+):
+    def fail_connect(_root):
+        raise RuntimeDomainError(
+            "invalid runtime domain"
+        )
+
+    monkeypatch.setattr(
+        live_state,
+        "connect",
+        fail_connect,
+    )
+
+    result = (
+        mcp_runtime
+        .query_live_diagnostics_summary_narrow(
+            Path(
+                r"C:\Temp\Contextor_Repo"
+            )
+        )
+    )
+
+    assert result.status == "error"
+    assert (
+        result.error
+        == "canonical_live_transport_error"
+    )
+    assert (
+        "invalid runtime domain"
+        in (result.detail or "")
+    )
+
+
 def test_mcp_diagnostics_keeps_projection_binding():
     assert (
         mcp_diagnostics
         .diagnostics_summary_for_state
         is diagnostics_summary_for_state
     )
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index 290108f..05c14de 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -322,3 +322,47 @@ def test_cheap_filters_run_before_severity_and_severity_filter_survives(tmp_path
 def test_registered_name_collision_tool_and_shared_summary_wrapper():
     assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
     assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 29
+
+
+def test_wrapper_diagnostics_exception_cannot_replace_successful_tool_result(
+    tmp_path,
+    monkeypatch,
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+
+    def fail_diagnostics(_root):
+        raise StopIteration(
+            "synthetic exhausted diagnostics transport"
+        )
+
+    monkeypatch.setattr(
+        "contextor.mcp.diagnostics.diagnostics_summary",
+        fail_diagnostics,
+    )
+
+    wrapped = mcp_server._instrument_mcp_tool(
+        lambda repo_path: json.dumps(
+            {
+                "status": "ok",
+                "repo_path": repo_path,
+                "value": 42,
+            }
+        ),
+        "synthetic_query",
+    )
+
+    result = json.loads(
+        wrapped(
+            str(repo)
+        )
+    )
+
+    assert result["status"] == "ok"
+    assert result["value"] == 42
+    assert result["diagnostics_summary"]["availability"] == {
+        "syntax_errors": "unavailable",
+        "name_collisions": "unavailable",
+        "cycles": "unavailable",
+    }
+    assert result["diagnostics_attention_required"] is False
+```

PY_COMPILE=PASS
TARGETED_TESTS=COMMAND_ERROR_NO_TESTS_RUN
TARGETED_TEST_COUNT=0
TARGETED_FAILURES=ERROR: file or directory not found: tests/live_e2e_corrections.py::test_affected_mcp_queries_fail_closed_on_parse_stale_state; pytest reported "no tests ran in 0.02s" and exited with code 4.
TARGETED_COMMAND_EXECUTED=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/mcp/test_live_diagnostics_narrow.py::test_narrow_live_diagnostics_query_treats_runtime_domain_error_as_transport_error tests/mcp/test_live_diagnostics_narrow.py::test_diagnostics_summary_transport_error_fails_closed_without_cache tests/test_mcp_diagnostics.py::test_wrapper_diagnostics_exception_cannot_replace_successful_tool_result tests/live_e2e_corrections.py::test_affected_mcp_queries_fail_closed_on_parse_stale_state tests/live_e2e_corrections.py::test_minimal_valid_syntax_error_query_repair_query_flow tests/live_e2e_corrections.py::test_live_events_retries_same_owner_and_preserves_journal tests/live_e2e_corrections.py::test_matching_owner_retry_success_preserves_revision_and_journal tests/test_mcp_regressions.py::test_stale_topology_is_not_presented_in_file_edit_context_after_incremental_update tests/test_mcp_regressions.py::test_minimal_file_context_fails_closed_without_usable_live_graph tests/test_mcp_regressions.py::test_full_file_context_public_api_uses_canonical_symbol_domain tests/test_mcp_regressions.py::test_file_edit_context_prefers_fresh_live_graph_over_stale_saved_matrix tests/test_mcp_regressions.py::test_file_edit_context_minimal_mode_and_target_resolution tests/test_mcp_regressions.py::test_module_context_forgiving_input_and_artifact_redirect tests/test_mcp_regressions.py::test_artifact_blast_radius_module_aware_diagnostic
RUNTIME_DOMAIN_ERROR_FAILS_CLOSED=NO
DIAGNOSTICS_ENRICHMENT_EXCEPTION_FAILS_CLOSED=NO
SUCCESSFUL_MCP_RESULT_PRESERVED=NO
CACHE_FALLBACK_CONTRACT_CHANGED=NO
PER_TOOL_DIAGNOSTICS_OPT_OUT_ADDED=NO
FAMILY_A_11_FAILURES_TARGETED_VALIDATED=NO

CONTEXTOR_REVISION=1443 (pre-edit)
WORKSPACE_SYNC=verified (pre-edit; post-edit verification not run because pytest command failed)
CANONICAL_STATE=fresh (pre-edit; post-edit verification not run because pytest command failed)

FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
PROCESS_TERMINATION_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO
STOP=YES; no pytest rerun and no further source/test edits after the command error.