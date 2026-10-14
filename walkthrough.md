TASK: CONTEXTOR_B0G4C15F_LEGACY_TEST_CONTRACT_MIGRATION
HEAD_BEFORE: 2b06e82028f4fc8e68d96a9167da4f0f52ead55f
HEAD_AFTER: 2b06e82028f4fc8e68d96a9167da4f0f52ead55f
GIT_STATUS:
 M tests/test_cycle_semantics_package_model.py

LIVE_REVISION_BEFORE: 441
LIVE_REVISION_AFTER: 442
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242
FILES_CHANGED: tests/test_cycle_semantics_package_model.py only (walkthrough.md is report artifact)
LEGACY_EXPECTATION_CONFLICT: DIRECT_EVIDENCE C5 test expected UNKNOWN for an uncalled function-local ImportFrom; C15 now supports that form and yielded MODEL_PASS. The conflicting element was exactly the specified sample.
EXACT_TEST_MIGRATION: Removed only the specified sample from the C5 UNKNOWN loop. Added the exact auditor-supplied positive test immediately after it. No other source/test edits. git diff --check passed.
SUPPORTED_FROM_DEFINITION_REGRESSION: TEST_COVERED. New test confirms MODEL_PASS, DEFINE_FUNCTION event, no FUNCTION_LOCAL_FROM or reentrant event, and no child START_IMPORT.
REMAINING_UNSUPPORTED_C5_CASES: Seven original samples retained with UNKNOWN assertion; focused tests pass.
CPYTHON_SYNTHETIC_PARITY: TEST_COVERED. New test asserts _actual(tmp_path, source, pkg) for generated synthetic package. C15's 14 differential tests also pass in focused run.
TARGETED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_function_local_from.py => 72 passed in 11.49s.
FULL_FOCUSED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_function_local_from.py tests/test_cycle_semantics_closure_witness.py tests/test_cycle_semantics_activation_view.py tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py => 257 passed in 17.17s.
PACKAGE_MODEL_DIFF_UNCHANGED: DIRECT_EVIDENCE git diff for contextor/core/cycle_semantics/package_model.py is empty in this task; production file was not edited.
LIVE_EVENT_CONTINUITY: DIRECT_EVIDENCE get_live_events after revision 440 showed delayed desktop_watcher UPDATED for new C15 test at 441. After current test edit, get_live_events after 441 showed desktop_watcher UPDATED tests/test_cycle_semantics_package_model.py at 442, continuity=continuous, resync_required=false, same epoch.
LIVE_SYNC_ALL_THREE_PATHS: DIRECT_EVIDENCE full get_file_edit_context at revision 442: package_model.py verified/fresh; test_cycle_semantics_function_local_from.py verified/fresh; test_cycle_semantics_package_model.py verified/fresh.
CANONICAL_FRESHNESS: Revision 442; module/graph/topology/artifact_consumption/cycles/collisions/lineage all fresh for all three paths; syntax errors 0/fresh.
COLLISION_COUNT_BEFORE_AFTER: 0/fresh -> 0/fresh.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16/fresh -> 16/fresh. Count stable; path-by-path identity not independently checked.
NO_WARNING_SUPPRESSION: No warning policy or production source modified.
NO_RUNTIME_SAFETY_CERTIFICATION: Focused tests and LIVE sync are not a Desktop/MCP runtime safety certification.
FINAL_VERDICT: B0G4C15F_FINAL_PASS

FULL_DIFFS:
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 4becc17..ee6b1dc 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -906,7 +906,6 @@ def test_b0g4c5_unsupported_definition_effects_unknown():
         "def f(x):\n    import pkg.child",
         "@decorator\ndef f():\n    import pkg.child",
         "def f() -> int:\n    import pkg.child",
-        "def f():\n    from pkg import child",
         "def f():\n    helper()",
         "async def f():\n    import pkg.child",
         "def f():\n    return 1",
@@ -918,6 +917,42 @@ def test_b0g4c5_unsupported_definition_effects_unknown():
         ).outcome == "UNKNOWN"
 
 
+def test_b0g4c15_uncalled_function_local_from_supported(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def f():\n"
+            "    from pkg import child"
+        ),
+        "pkg.child": "pass",
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert any(
+        event.operation == "DEFINE_FUNCTION"
+        and event.symbol == "f"
+        for event in result.events
+    )
+
+    assert not any(
+        event.operation in {
+            "FUNCTION_LOCAL_FROM",
+            "FUNCTION_LOCAL_FROM_REENTRANT_CHILD",
+        }
+        for event in result.events
+    )
+
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+        for event in result.events
+    )
+
+    assert _actual(tmp_path, source, "pkg")
+
+
 def test_b0g4c5_deterministic_ast_unchanged():
     source = {
         "pkg.__init__": ast.parse(
