TASK: CONTEXTOR_B0G4C1F_EXPLICIT_DOTTED_IMPORT_ALIAS_FIX
FINAL_VERDICT: B0G4C1F_FINAL_PASS

HEAD_BEFORE: cccfd72ddcb5a976771c1400745f72ac3e66c987
HEAD_AFTER: cccfd72ddcb5a976771c1400745f72ac3e66c987
GIT_STATUS_BEFORE: clean
GIT_STATUS_AFTER_SOURCE_EDIT: M contextor/core/cycle_semantics/package_model.py; M tests/test_cycle_semantics_package_model.py
LIVE_REVISION_BEFORE: 422
LIVE_REVISION_AFTER: 424
ACTIVITY_EPOCH_BEFORE_AFTER: 1beab26da2ff4932852caa7db6ff4242 (unchanged)
CANONICAL_FRESHNESS: revision 424; canonical state, graph, cycles, collisions fresh; production and test module workspace_sync=verified; resync_required=false.
WATCHER_EVENTS: revision 423 desktop_watcher UPDATED contextor/core/cycle_semantics/package_model.py; revision 424 desktop_watcher UPDATED tests/test_cycle_semantics_package_model.py. Event continuity continuous. No manual update_file.

SOURCE_PRECHECK: Contextor implementation and module context confirmed original B0G4C1 anchors, direct test consumer and package_layout dependency at verified revision 422. HEAD and clean Git status checked. Literal comparison with original B0G4C1 text confirmed both files matched the prior implementation; explicit_alias and four regression names were absent. Source anchors matched exactly once before editing.
OWNERSHIP_AND_BLAST_RADIUS: Contextor identifies package_model as the changed owner; one direct inbound hard dependency from tests.test_cycle_semantics_package_model and one outbound hard dependency to contextor.core.cycle_semantics.package_layout. Relevant symbol artifact consumer is the test module. No broader architectural claim is made from this compact context.

FILES_CHANGED:
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
ACTUAL_DIFF=FULL_DIFFS: Complete actual Git diff for both files follows below. walkthrough.md is the report artifact and is not counted as a production/test change.

ROOT_CAUSE: CODE_PATH_PROVED. The old import branch used step.binding != target.split(".")[0] as a proxy for an explicit alias. The spelling of `import pkg.sub as pkg` makes that comparison false even though the syntax explicitly binds pkg.sub. This conflated it with `import pkg.sub`, which binds pkg.
EXACT_CORRECTION: CONTRACT_PROVED against auditor patch. The frozen _Step now records explicit_alias from ast.Import alias.asname. Both import-branch decisions use that syntax flag. ast.ImportFrom, parent-child checks, and ordinary import behavior were preserved. Four exact auditor-specified regression tests were appended.

TEST_COMMAND: & .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py
TEST_RESULTS: DIRECT_EVIDENCE: 149 passed in 5.42s; exit code 0. Previous 145-pass baseline is supplied by the task and was not rerun. Four appended tests are included in the passing run. git diff --check passed.
FALSE_MODEL_PASS_REGRESSION: TEST_COVERED: explicit alias equal to root with value only on pkg.__init__ now yields MISSING_ATTRIBUTE for pkg.sub/value; the fresh-process Python fixture fails as expected.
FALSE_HAZARD_REGRESSION: TEST_COVERED: explicit alias equal to root inside pkg.__init__ yields MODEL_PASS; the fresh-process Python fixture succeeds, covering the prior false EARLY_BINDING_HAZARD.
PLAIN_IMPORT_NONREGRESSION: TEST_COVERED: ordinary `import pkg.sub` still resolves the local name to pkg; the fixture yields MISSING_ATTRIBUTE for pkg/value and actual Python fails. A separate positive fixture verifies `import pkg.sub as pkg` resolves value on pkg.sub and actual Python succeeds.
AST_AND_ANALYZED_SOURCE: CODE_PATH_PROVED for production change: only immutable step metadata and binding decisions changed. TEST_COVERED by the targeted no-AST-mutation test and synthetic fresh-process fixtures. The model itself did not execute analyzed source.
COLLISION_COUNT_BEFORE_AFTER: 0 fresh at revision 422 -> 0 fresh at revision 424.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 fresh at revision 422 -> 16 fresh at revision 424; same activity epoch and verified workspace synchronization.
NO_WARNING_SUPPRESSION: DIRECT_EVIDENCE: full diff contains no warning, graph, resolver, or diagnostic policy change. Existing attention_required remains true because the 16 preexisting cycles remain.
RESTRICTIONS: No full suite, FULL analysis, direct update_file, restart, Git mutation, or unrelated source/test edit was performed. No observed missing evidence needed for this focused verdict.

FULL_DIFFS_BEGINdiff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index e066d4b..3afb3d2 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -37,6 +37,7 @@ class _Step:
     target: str | None = None
     symbol: str | None = None
     binding: str | None = None
+    explicit_alias: bool = False
 
 
 def _compile(
@@ -66,6 +67,7 @@ def _compile(
                         "IMPORT",
                         alias.name,
                         binding=alias.asname or alias.name.split(".")[0],
+                        explicit_alias=alias.asname is not None,
                     )
                 )
 
@@ -388,10 +390,7 @@ def evaluate_package_import_order(
 
             if step.op == "IMPORT":
                 if module != bootstrap:
-                    if (
-                        step.binding != target.split(".")[0]
-                        and "." in target
-                    ):
+                    if step.explicit_alias and "." in target:
                         parent, child = target.rsplit(".", 1)
 
                         if namespaces[parent].get(child) != target:
@@ -399,7 +398,7 @@ def evaluate_package_import_order(
 
                     binding_target = (
                         target
-                        if step.binding != target.split(".")[0]
+                        if step.explicit_alias
                         else target.split(".")[0]
                     )
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index a2eb5d2..b43bb77 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -287,3 +287,68 @@ def test_determinism_invalid_no_ast_mutation():
         ).outcome
         == "UNKNOWN"
     )
+
+
+def test_explicit_alias_equal_root_binds_submodule(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub": "value=2",
+        "entry": "import pkg.sub as pkg\nx=pkg.value",
+    }
+
+    result = _model(source, "entry")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "ATTR"
+        and event.target == "pkg.sub"
+        and event.symbol == "value"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_explicit_alias_equal_root_prevents_false_model_pass(tmp_path):
+    source = {
+        "pkg.__init__": "value=2",
+        "pkg.sub": "pass",
+        "entry": "import pkg.sub as pkg\nx=pkg.value",
+    }
+
+    result = _model(source, "entry")
+
+    assert result.outcome == "MISSING_ATTRIBUTE"
+    assert result.target_module == "pkg.sub"
+    assert result.symbol == "value"
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_explicit_alias_equal_root_inside_package_initializer(tmp_path):
+    source = {
+        "pkg.__init__": "import pkg.sub as pkg\nx=pkg.value",
+        "pkg.sub": "value=2",
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "ATTR"
+        and event.target == "pkg.sub"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_plain_dotted_import_still_binds_root_package(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub": "value=2",
+        "entry": "import pkg.sub\nx=pkg.value",
+    }
+
+    result = _model(source, "entry")
+
+    assert result.outcome == "MISSING_ATTRIBUTE"
+    assert result.target_module == "pkg"
+    assert not _actual(tmp_path, source, "entry")

FULL_DIFFS_END
