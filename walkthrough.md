# CONTEXTOR_REGRESSION_26_MCP_ARCHITECTURE_CONTRACT_3_FIX

## TASK
Controlled test-only repair of three stale get_project_architecture contract regressions. No production or documentation changes.

## HEAD_BEFORE
2c8184c12be6837045931c05e133b1010690f583

## HEAD_AFTER
2c8184c12be6837045931c05e133b1010690f583

## FILES_CHANGED
- tests/mcp/tools/test_architecture_context_contracts.py
- tests/test_mcp_split_s2d.py

## PUBLIC_SIGNATURE_PROOF
DIRECT_EVIDENCE: Python 3.10 inspect.signature of the current implementation returned:
`(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False, cycle_semantics_view: str = 'full', cycle_semantics_component: str | None = None) -> str`.
The two exact signature expectations now match this result, including argument order, annotations, defaults, and return type. Contextor identified the canonical implementation in contextor/mcp/tools/get_project_architecture.py and direct static consumers in contextor.mcp_server and tests.test_mcp_split_s2d.

## DOCS_THRESHOLD_PROOF
DIRECT_EVIDENCE: contextor/mcp/docs/get_project_architecture.json declares the 51200-byte threshold under parameters.allow_large_output. The docs test now includes parameters in its combined semantic text and retains the literal `assert "51200" in combined`. It also checks the documented defaults, overview/diagnostic/full views, and component restriction, while keeping historical parameter and report_catalog/live_state assertions. The existing full-file tests continue checking historical cycle_semantics and separate LIVE diagnostics.

## THREE_REGRESSION_RESULTS
`python -m pytest -q` on the three exact requested node IDs: **3 passed, 1 warning in 6.38s**, exit 0. Warning: third-party FastMCP AuthlibDeprecationWarning.

## FOCUSED_NON_REGRESSION_RESULTS
`python -m pytest -q tests/mcp/tools/test_architecture_context_contracts.py tests/test_mcp_split_s2d.py`: **29 passed, 1 warning in 5.57s**, exit 0. Same third-party warning. Full repository suite was not run. `git diff --check`: exit 0, with Git LF-to-CRLF working-copy notices only.

## REGISTRATION_AND_OWNERSHIP_INVARIANTS
CONTRACT_PROVED by passing test_s2d_registration_order_bindings_signatures_and_descriptions and full test_mcp_split_s2d.py: registration order, wrapper identity, implementation binding, descriptions, ownership, and all other signature expectations remain checked. Only the approved get_project_architecture signature entry changed. Contextor blast-radius result confirmed direct static consumers; dynamic Python usage is outside that tool's evidence scope.

## LIVE_REVISION_BEFORE_AFTER
Before: canonical revision 620, workspace_sync=verified. After: revision 622, canonical_state=fresh, workspace_sync=verified, provenance=live (Contextor blast-radius response). No manual update_file was called.

## WATCHER_EVENTS
Contextor get_live_events(after_revision=620): continuity=continuous, resync_required=false, activity epoch 5d758bf9339c4ac5a5816ab056e7f84b. Revision 621: desktop_watcher UPDATED tests/mcp/tools/test_architecture_context_contracts.py. Revision 622: desktop_watcher UNCHANGED tests/test_mcp_split_s2d.py. The latter event confirms watcher observation but does not claim an UPDATED classification. Contextor file-edit context returned fresh syntax diagnostics, zero errors, for both files at revisions 621 and 622 respectively.

## RESTART_REQUIREMENTS
MCP_BACKEND_RESTART_REQUIRED=NO. LIVE_SERVICE_RESTART_REQUIRED=NO. Only test code changed; no restart performed.

## FULL_DIFFS
```diff

diff --git a/tests/mcp/tools/test_architecture_context_contracts.py b/tests/mcp/tools/test_architecture_context_contracts.py
index b5647f0..887e3a0 100644
--- a/tests/mcp/tools/test_architecture_context_contracts.py
+++ b/tests/mcp/tools/test_architecture_context_contracts.py
@@ -14,7 +14,7 @@ def _load_doc(tool_name: str) -> dict:
 def test_architecture_context_contracts__get_project_architecture_signature():
     tools = mcp_server.mcp._tool_manager._tools
     sig = str(inspect.signature(tools["get_project_architecture"].fn))
-    assert sig == "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False) -> str"
+    assert sig == "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False, cycle_semantics_view: str = 'full', cycle_semantics_component: str | None = None) -> str"
 
 
 def test_architecture_context_contracts__get_file_edit_context_signature():
@@ -47,8 +47,14 @@ def test_architecture_context_contracts__get_project_architecture_docs_complete(
     assert "repo_path (string, required)" in params_text
     assert "fields (array of strings or null, default null)" in params_text
     assert "allow_large_output (boolean, default false)" in params_text
+    assert 'cycle_semantics_view (string, default "full")' in params_text
+    assert "one of overview, diagnostic, or full" in params_text
+    assert "cycle_semantics_component (string or null, default null)" in params_text
+    assert "in overview or diagnostic view" in params_text
+    assert "invalid with full view" in params_text
     combined = "\n".join(
-        doc.get("behavior", [])
+        doc.get("parameters", [])
+        + doc.get("behavior", [])
         + doc.get("freshness", [])
         + doc.get("usage_notes", [])
     )
diff --git a/tests/test_mcp_split_s2d.py b/tests/test_mcp_split_s2d.py
index e61a52f..173cecb 100644
--- a/tests/test_mcp_split_s2d.py
+++ b/tests/test_mcp_split_s2d.py
@@ -33,7 +33,7 @@ _IMPLEMENTATIONS = {
 }
 
 _EXPECTED_SIGNATURES = {
-    "get_project_architecture": "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False) -> str",
+    "get_project_architecture": "(repo_path: str, fields: list[str] | None = None, allow_large_output: bool = False, cycle_semantics_view: str = 'full', cycle_semantics_component: str | None = None) -> str",
     "get_module_context": "(repo_path: str, module_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, module: str | None = None) -> str",
     "get_symbol_implementation": "(repo_path: str, symbol: str, file_paths: list[str] | None = None, mode: str = 'auto', include: list[str] | None = None, methods: list[str] | None = None, member_limit: int | None = 50, file_path: str | None = None) -> str",
     "get_file_edit_context": "(repo_path: str, file_path: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, mode: str | None = None, target: str | None = None) -> str",

```

## FINAL_VERDICT
FINAL PASS for this controlled test-only task: requested signature and documentation contract assertions are updated; all exact and focused gates pass; LIVE continuity and workspace sync are verified. No production or docs files changed.

