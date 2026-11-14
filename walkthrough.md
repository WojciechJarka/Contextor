# P5-M08-I10-I4-R4B — correct historical test path

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was queried first. Post-change canonical LIVE revision is 1401, provenance live, canonical_state fresh. Project-wide workspace_sync is unverified; per-file workspace_sync is verified for all three changed tests and contextor/core/cycle_semantics/package_model.py.
- DIRECT_EVIDENCE: The pre-edit Contextor snapshot was revision 1398 with canonical_state fresh and project-wide workspace_sync unverified. The post-change audit advanced to revision 1401.
- DIRECT_EVIDENCE: HEAD is ff829dc32640bf86139c5f5a30d8d0c9eac320d2. CPython is 3.15.2. Before R4B edits, the only worktree change was walkthrough.md from the R4 SOURCE_DRIFT report.
- DIRECT_EVIDENCE: I4-R1 production code is present in HEAD: package_model.py ClassDef admission at lines 859-866 and restricted class decorator admission/execution at lines 2657-2702. package_model.py has no worktree diff.
- DIRECT_EVIDENCE: The I4-R2 model-only marker normalization is present at tests/test_cycle_semantics_cross_module_class_decorator_baseline.py:624-640. The I4-R3 public event assertion uses DEFINE_FUNCTION at tests/test_cycle_semantics_class_decorator_import_admission.py:199. Those files are clean relative to HEAD.
- DIRECT_EVIDENCE: The three R4 locations still match their exact fixtures. The fourth fixture is at the corrected path in tests/test_cycle_semantics_cross_module_decorator_baseline.py; its function began near line 697 before edits. All four are the imported identity class-decorator contract. No fixture source or CPython reference was changed.

## SOURCE_DRIFT_RESOLUTION

R4 named tests/test_cycle_semantics_class_decorator_baseline.py for correction D, but the exact function and fixture were in tests/test_cycle_semantics_cross_module_decorator_baseline.py. R4B authorizes the actual file. The test name, fixture, and contract were verified at that location before editing. The mistaken path was not edited. This resolves the prior SOURCE_DRIFT without changing production or redirecting beyond the explicit R4B correction.

## FILES_CHANGED

- tests/test_cycle_semantics_cross_module_stack_continuation.py — R4B correction A.
- tests/test_cycle_semantics_cross_module_single_decorator.py — R4B correction B.
- tests/test_cycle_semantics_cross_module_decorator_baseline.py — R4B corrections C and D.
- walkthrough.md — this report; report-only and excluded from the source/test FULL_DIFF list.

No production file, fixture, or new test file changed. No untracked test file was present. I4-R1 production changes and prior I4-R2/R3 test changes are already in HEAD; the three test files above are the current R4B worktree modifications.

## FOUR_EXACT_TEST_CORRECTIONS

A. In cross_module_stack_continuation.py, renamed test_imported_class_decorator_remains_unknown to test_imported_class_decorator_executes_indexed_identity. It now requires MODEL_PASS, target_module=None, symbol=None, restricted regular package evidence scope, and the complete twelve-event sequence.

B. In cross_module_single_decorator.py, renamed test_imported_class_decorator_remains_unknown to test_imported_class_decorator_preserves_class_identity. It now requires the same outcome, metadata, and complete event sequence, plus CALL_FUNCTION(identity) in pkg.app.

C. In cross_module_decorator_baseline.py, only parameter case E-imported-class-decorator now requires MODEL_PASS, target_module=None, symbol=None, restricted regular package evidence scope, and the complete twelve-event sequence. All other parameter cases retain UNKNOWN and empty events.

D. In the corrected cross_module_decorator_baseline.py location, renamed test_imported_class_decorator_does_not_satisfy_local_compile_gate to test_imported_class_decorator_satisfies_indexed_from_gate. It now requires MODEL_PASS, target_module=None, symbol=None, restricted regular package evidence scope, and the complete twelve-event sequence.

For all four, the exact expected events (module, operation, target, symbol) are:

    ("\x00ENTRY", "START_IMPORT", "pkg", None)
    ("pkg", "READY", None, None)
    ("\x00ENTRY", "START_IMPORT", "pkg.app", None)
    ("pkg.app", "START_IMPORT", "pkg.decorators", None)
    ("pkg.decorators", "DEFINE_FUNCTION", None, "identity")
    ("pkg.decorators", "READY", None, None)
    ("pkg", "BIND_CHILD", "pkg.decorators", "decorators")
    ("pkg.app", "FROM", "pkg.decorators", "identity")
    ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C")
    ("pkg.app", "CALL_FUNCTION", None, "identity")
    ("pkg.app", "READY", None, None)
    ("pkg", "BIND_CHILD", "pkg.app", "app")

## COMPILER_ADMISSION_UNCHANGED

No compiler or production source changed. The imported decorator reaches the existing indexed FROM admission path. The expected public sequence preserves the import and FROM events before passive class creation, then the class-decorator call. I4-R1 admission code remains the HEAD implementation.

## RUNTIME_SEMANTICS_UNCHANGED

No runtime evaluator, class-fact, continuation, binding, or callable behavior changed. These edits update historical assertions to match the accepted existing I4-R1 behavior only. The three local identity-class fixtures remain unchanged.

## CPYTHON_PARITY

DIRECT_EVIDENCE: The parametrized E reference remains unchanged and ran as part of both requested gates. Its isolated subprocess uses the active CPython 3.15.2 with -I -B. The reference asserts successful import, imports exactly pkg.decorators, final C binding present with type builtins.type and callable true, one decorator call, the class object received by the decorator is the final binding, the imported decorator export is the binding, and instantiating C yields pkg.app.C. The parametrized CPython reference and model test passed.

BOUNDARY: The three other historical assertions are model-only tests and have no separate CPython subprocess in those test functions. Their source fixtures were preserved; no additional CPython observations are claimed for them.

## FIRST_GATE_RESULTS

DIRECT_EVIDENCE: Passed, 45 tests.

Command:

    .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_stack_continuation.py tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_class_decorator_baseline.py -rs

## FULL_TARGETED_RESULTS

DIRECT_EVIDENCE: Passed, 348 tests.

Command:

    .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_class_decorator_import_admission.py tests/test_cycle_semantics_cross_module_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_cross_module_stack_continuation.py tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py tests/test_cycle_semantics_decorator_snapshots.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_package_model.py -rs

DIRECT_EVIDENCE: git diff --check passed. Git printed only LF-to-CRLF working-copy notices for the three changed test files and walkthrough.md; no whitespace error was reported. No full pytest, SCC02, FULL, update_file, restart, semantic refresh, or Git index/history operation was performed.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: canonical LIVE revision 1401; canonical_state fresh; provenance live. Project-level workspace_sync remains unverified.
- DIRECT_EVIDENCE: workspace_sync verified at revision 1401 for cross_module_stack_continuation.py, cross_module_single_decorator.py, cross_module_decorator_baseline.py, and package_model.py.
- DIRECT_EVIDENCE: Contextor syntax diagnostics report zero errors for each of those four files; project diagnostics also report zero syntax errors.
- DIRECT_EVIDENCE: Changed test modules import/consume the production cycle semantics package model; package_model.py has production dependencies and consumers, and no dependency direction was changed because no production source was edited. The queried contexts show the test-to-production imports and package_model consumers (46 total, truncated evidence).
- DIRECT_EVIDENCE: structural DFS cycle count is 16, fresh, with Contextor's stated DFS back-edge-path semantics. Cycle-semantics freshness is stale separately; no semantic refresh was requested or performed.
- INFERENCE: Since all R4B edits are confined to tests and no production dependency edge changed, this task does not alter the production dependency graph. The current graph metric was still checked in MCP.

## FULL_DIFFS

The following are the complete actual worktree diffs for all source/test files changed by R4B. I4 changes already in HEAD are not part of these diffs.

### tests/test_cycle_semantics_cross_module_stack_continuation.py

<pre>
diff --git a/tests/test_cycle_semantics_cross_module_stack_continuation.py b/tests/test_cycle_semantics_cross_module_stack_continuation.py
index 6679107..310f59b 100644
--- a/tests/test_cycle_semantics_cross_module_stack_continuation.py
+++ b/tests/test_cycle_semantics_cross_module_stack_continuation.py
@@ -466,7 +466,7 @@ def test_single_imported_decorator_remains_model_pass():
     _assert_unique_module_starts(modeled)
-def test_imported_class_decorator_remains_unknown():
+def test_imported_class_decorator_executes_indexed_identity():
     modeled = _model(
         {
             "pkg.__init__": "pass\n",
@@ -480,8 +480,27 @@ def test_imported_class_decorator_remains_unknown():
         }
     )
-    assert modeled.outcome == "UNKNOWN"
-    assert modeled.events == ()
+    assert modeled.outcome == "MODEL_PASS"
+    assert modeled.target_module is None
+    assert modeled.symbol is None
+    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert tuple(
+        (event.module, event.operation, event.target, event.symbol)
+        for event in modeled.events
+    ) == (
+        ("\x00ENTRY", "START_IMPORT", "pkg", None),
+        ("pkg", "READY", None, None),
+        ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+        ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+        ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+        ("pkg.decorators", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+        ("pkg.app", "FROM", "pkg.decorators", "identity"),
+        ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+        ("pkg.app", "CALL_FUNCTION", None, "identity"),
+        ("pkg.app", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.app", "app"),
+    )
 def test_external_functools_lru_cache_remains_unknown():
</pre>

### tests/test_cycle_semantics_cross_module_single_decorator.py

<pre>
diff --git a/tests/test_cycle_semantics_cross_module_single_decorator.py b/tests/test_cycle_semantics_cross_module_single_decorator.py
index cae7c9f..3e27b40 100644
--- a/tests/test_cycle_semantics_cross_module_single_decorator.py
+++ b/tests/test_cycle_semantics_cross_module_single_decorator.py
@@ -524,7 +524,7 @@ def test_same_module_single_decorator_keeps_call_order():
     assert not any(event.operation == "FROM" for event in modeled.events)
-def test_imported_class_decorator_remains_unknown():
+def test_imported_class_decorator_preserves_class_identity():
     modeled = _model(
         {
             "pkg.__init__": "pass\n",
@@ -538,9 +538,32 @@ def test_imported_class_decorator_remains_unknown():
         }
     )
-    assert modeled.outcome == "UNKNOWN"
-    assert modeled.events == ()
-    assert not _events(modeled, "CALL_FUNCTION")
+    assert modeled.outcome == "MODEL_PASS"
+    assert modeled.target_module is None
+    assert modeled.symbol is None
+    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert tuple(
+        (event.module, event.operation, event.target, event.symbol)
+        for event in modeled.events
+    ) == (
+        ("\x00ENTRY", "START_IMPORT", "pkg", None),
+        ("pkg", "READY", None, None),
+        ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+        ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+        ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+        ("pkg.decorators", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+        ("pkg.app", "FROM", "pkg.decorators", "identity"),
+        ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+        ("pkg.app", "CALL_FUNCTION", None, "identity"),
+        ("pkg.app", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.app", "app"),
+    )
+    assert tuple(
+        (event.module, event.symbol)
+        for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+    ) == (("pkg.app", "identity"),)
 def test_imported_stacked_decorators_execute_bottom_to_top():
</pre>

### tests/test_cycle_semantics_cross_module_decorator_baseline.py

<pre>
diff --git a/tests/test_cycle_semantics_cross_module_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
index f42ee97..c93ebf3 100644
--- a/tests/test_cycle_semantics_cross_module_decorator_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
@@ -400,9 +400,31 @@ def test_indexed_cross_module_decorator_reference_and_model_boundary(
         {name: ast.parse(source) for name, source in sources.items()},
         "pkg.app",
     )
-    assert modeled.outcome == "UNKNOWN"
     assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
-    assert modeled.events == ()
+    if case == "E":
+        assert modeled.outcome == "MODEL_PASS"
+        assert modeled.target_module is None
+        assert modeled.symbol is None
+        assert tuple(
+            (event.module, event.operation, event.target, event.symbol)
+            for event in modeled.events
+        ) == (
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "identity"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "identity"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )
+    else:
+        assert modeled.outcome == "UNKNOWN"
+        assert modeled.events == ()
 @pytest.mark.parametrize(
@@ -694,7 +716,7 @@ def test_external_functools_decorator_remains_unmodeled_without_assumptions():
     )
-def test_imported_class_decorator_does_not_satisfy_local_compile_gate():
+def test_imported_class_decorator_satisfies_indexed_from_gate():
     sources = {
         "pkg.__init__": ast.parse("pass\n"),
         "pkg.decorators": ast.parse(
@@ -709,9 +731,27 @@ def test_imported_class_decorator_does_not_satisfy_local_compile_gate():
     }
     modeled = evaluate_package_import_order(sources, "pkg.app")
-    assert modeled.outcome == "UNKNOWN"
+    assert modeled.outcome == "MODEL_PASS"
+    assert modeled.target_module is None
+    assert modeled.symbol is None
     assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
-    assert modeled.events == ()
+    assert tuple(
+        (event.module, event.operation, event.target, event.symbol)
+        for event in modeled.events
+    ) == (
+        ("\x00ENTRY", "START_IMPORT", "pkg", None),
+        ("pkg", "READY", None, None),
+        ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+        ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+        ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+        ("pkg.decorators", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+        ("pkg.app", "FROM", "pkg.decorators", "identity"),
+        ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+        ("pkg.app", "CALL_FUNCTION", None, "identity"),
+        ("pkg.app", "READY", None, None),
+        ("pkg", "BIND_CHILD", "pkg.app", "app"),
+    )
</pre>

## FINAL_VERDICT

FINAL PASS for the bounded R4B test-contract correction: the corrected historical expectations match the exact accepted twelve-event contract, the first gate passed 45 tests, the targeted regression passed 348 tests, git diff --check passed, and the requested Contextor post-change audit completed. This does not certify cycle_semantics freshness: that family remains stale. Production behavior and the I4-R1/R2/R3 changes were not modified in R4B.
