TASK: CONTEXTOR_B0G4C2_FROM_PACKAGE_MEMBER_RESOLUTION
FINAL_VERDICT: B0G4C2_PASS

HEAD_BEFORE: 14a145d7b4f1e7b4ee0b92cebcd738974d2af549
HEAD_AFTER: 14a145d7b4f1e7b4ee0b92cebcd738974d2af549
GIT_STATUS_BEFORE: clean
LIVE_REVISION_BEFORE: 424
LIVE_REVISION_AFTER: 426
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242 (unchanged)
WATCHER_PROPAGATION: desktop_watcher UPDATED package_model.py at revision 425 and test_cycle_semantics_package_model.py at revision 426; continuity continuous, resync_required=false.
CANONICAL_STATE_AFTER: graph, cycles, collisions, syntax and both changed modules fresh; workspace_sync=verified at revision 426.

FILES_CHANGED:
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
The report artifact walkthrough.md is excluded from source/test changed files.

SOURCE_PRECHECK: Contextor resolved the exact _compile and evaluate_package_import_order implementations at verified revision 424. The package_model owner has one direct static consumer, tests.test_cycle_semantics_package_model, and one outbound dependency, package_layout. Artifact blast radius reports that test module as the direct consumer and no production downstream module. Literal anchors and C1F explicit_alias code matched the requested baseline. HEAD was clean. Python version: 3.10.9.
BASELINE_TEST: The specified ten-file suite passed 149 tests before editing.

IMPLEMENTATION_CONTRACT: Applied the four auditor-defined production changes only: refuse multi-member fromlists in _compile; narrow the package child-shadowing guard; on FROM, prioritize an existing package attribute, initialize a NEW indexed child, and return UNKNOWN for an already non-NEW child with absent parent attribute; retain existing FROM completion, BIND_CHILD, BIND, ATTR, READY and C1F explicit_alias behavior. Replaced the one superseded C1 test and appended the 11 exact C2 tests. No graph, resolver, schema, LIVE/MCP/Desktop, or package-export code changed.
FROM_PACKAGE_RESOLUTION: TEST_COVERED by indexed child, relative initializer, relative submodule and regular reexport cases. A missing member without indexed child remains MISSING_EXPORT.
ATTRIBUTE_PRECEDENCE: TEST_COVERED: an existing package attribute prevents START_IMPORT of the same-named child. A constant attribute followed by attribute access returns UNKNOWN rather than a false MODEL_PASS.
PARENT_CHILD_BINDING: TEST_COVERED: relative initializer test sees BIND_CHILD after the child becomes READY.
REENTRANT_UNKNOWN: TEST_COVERED: child already INITIALIZING with absent parent binding produces UNKNOWN, while the actual fresh-process fixture succeeds through semantics outside this restricted model.
MULTI_FROMLIST_UNKNOWN: TEST_COVERED: two-member fromlist produces UNKNOWN at compilation.
BUDGET_REGRESSION: TEST_COVERED: oversized operation sequence returns UNKNOWN.
C1F_NONREGRESSION: The four C1F explicit alias regressions remain in the passing ten-file suite; explicit_alias code was unchanged.
SHADOWING: TEST_COVERED: package-owned child binding followed by an import remains UNKNOWN.
DETERMINISM_AND_AST: Existing focused determinism/no-AST-mutation coverage remains in the passing suite. The model does not execute the indexed source; _actual fixtures run synthesized source in fresh processes to compare behavior.

TEST_COMMAND: & .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py
TEST_RESULTS: DIRECT_EVIDENCE: 160 passed in 8.16s; exit code 0. Baseline 149 passed in 6.25s. git diff --check for both approved source/test files passed.
COLLISION_COUNT_BEFORE_AFTER: 0 fresh at revision 424 -> 0 fresh at revision 426.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 fresh at revision 424 -> 16 fresh at revision 426, same activity epoch and verified workspace sync.
NO_SAFETY_CERTIFICATION: MODEL_PASS is restricted model evidence only. These tests and fresh canonical metrics do not certify arbitrary Python imports as safe.
NO_WARNING_SUPPRESSION: The actual diff has no warning, graph, resolver, or diagnostic policy changes. Existing attention_required remains true with 16 structural cycles.
UNRESOLVED_LIMITATIONS: Multiple from-import members, reentrant fromlist fallback, complex package-owned rebinding, nonmodule attribute dereference, and behavior outside indexed closed regular packages remain UNKNOWN by contract.
EVIDENCE_DISCIPLINE: DIRECT_EVIDENCE = Git, LIVE, test results and diff; CONTRACT_PROVED = exact patch anchors and Contextor implementations; CODE_PATH_PROVED = changed model branches; UNKNOWN = general Python import safety beyond the restricted model. No inference is used to claim global safety.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 3afb3d2..8e48249 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -72,6 +72,10 @@ def _compile(
                 )
 
         elif isinstance(stmt, ast.ImportFrom):
+            # Python resolves the entire fromlist before its STORE_NAME steps.
+            # This model processes single members only, to avoid false proofs.
+            if len(stmt.names) != 1:
+                return None
             if stmt.level:
                 context = (
                     logical.split(".")
@@ -270,23 +274,26 @@ def evaluate_package_import_order(
 
         programs[name] = program
 
-    # A package initializer that overwrites a direct child
-    # binding requires richer import-statement semantics.
-    # This restricted model refuses that case.
+    # A package may prebind a same-named attribute before a later
+    # from-import; the attribute takes priority. Keep more complex
+    # package-owned import/rebinding sequences indeterminate.
     for package in packages:
         children = {
             name.rsplit(".", 1)[1]
             for name in programs
-            if (
-                "." in name
-                and name.rsplit(".", 1)[0] == package
-            )
+            if "." in name and name.rsplit(".", 1)[0] == package
         }
-
-        if any(
+        writes_child = any(
             step.binding in children
+            and (
+                step.op == "BIND"
+                or (step.op == "FROM" and step.target != package)
+            )
+            for step in programs[package]
+        )
+        if writes_child and any(
+            step.op in {"IMPORT", "FROM"}
             for step in programs[package]
-            if step.op in {"BIND", "FROM"}
         ):
             return result("UNKNOWN", package)
 
@@ -416,13 +423,35 @@ def evaluate_package_import_order(
             else:
                 member = step.symbol
 
-                # from-package child resolution is ambiguous.
-                # C1 does not attempt to resolve that ambiguity.
-                if (
-                    target in packages
-                    and target + "." + member in programs
-                ):
-                    return result("UNKNOWN", target, member)
+                # CPython checks a package attribute before attempting
+                # to load a same-named child module. An existing binding
+                # takes precedence over the indexed child candidate.
+                if target in packages and member not in namespaces[target]:
+                    child = target + "." + member
+
+                    if child in programs:
+                        # Reentrant fromlist fallback through sys.modules is
+                        # intentionally unsupported by this restricted model.
+                        if states[child] != "NEW":
+                            return result("UNKNOWN", child, member)
+
+                        next_child = missing_piece(child)
+
+                        if next_child != child:
+                            return result("UNKNOWN", child, member)
+
+                        states[child] = "INITIALIZING"
+
+                        events.append(
+                            PackageModelEvent(
+                                module,
+                                "START_IMPORT",
+                                child,
+                            )
+                        )
+
+                        frames.append((child, 0))
+                        continue
 
                 if member not in namespaces[target]:
                     outcome = (
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index b43bb77..b4afeb4 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -182,14 +182,22 @@ def test_dotted_alias_to_child(tmp_path):
     assert _actual(tmp_path, source, "entry")
 
 
-def test_from_package_child_remains_unknown():
+def test_from_package_child_loads_indexed_child(tmp_path):
     source = {
         "pkg.__init__": "pass",
         "pkg.child": "value=7",
-        "entry": "from pkg import child",
+        "entry": "from pkg import child\nx=child.value",
     }
 
-    assert _model(source, "entry").outcome == "UNKNOWN"
+    result = _model(source, "entry")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "entry")
 
 
 def test_namespace_ambiguous_external_unknown():
@@ -352,3 +360,130 @@ def test_plain_dotted_import_still_binds_root_package(tmp_path):
     assert result.outcome == "MISSING_ATTRIBUTE"
     assert result.target_module == "pkg"
     assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c2_relative_initializer_imports_child(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": "value=7",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        e.operation == "BIND_CHILD"
+        and e.target == "pkg.child"
+        for e in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c2_relative_import_from_submodule(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.child": "value=7",
+        "pkg.user": "from . import child\nx=child.value",
+    }
+    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg.user")
+
+
+def test_b0g4c2_existing_attribute_precedes_child(tmp_path):
+    source = {
+        "pkg.__init__": "child=3",
+        "pkg.child": "value=7",
+        "entry": "from pkg import child",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert not any(
+        e.operation == "START_IMPORT"
+        and e.target == "pkg.child"
+        for e in result.events
+    )
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c2_constant_attribute_is_not_module(tmp_path):
+    source = {
+        "pkg.__init__": "child=3",
+        "pkg.child": "value=7",
+        "entry": "from pkg import child\nx=child.value",
+    }
+    assert _model(source, "entry").outcome == "UNKNOWN"
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c2_child_already_initialized(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.child": "value=7",
+        "entry": (
+            "import pkg.child\n"
+            "from pkg import child\n"
+            "x=child.value"
+        ),
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert sum(
+        e.operation == "START_IMPORT"
+        and e.target == "pkg.child"
+        for e in result.events
+    ) == 1
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c2_regular_attribute_reexport(tmp_path):
+    source = {
+        "pkg.__init__": "from .util import exposed",
+        "pkg.util": "exposed=7",
+        "pkg.user": "from pkg import exposed",
+    }
+    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg.user")
+
+
+def test_b0g4c2_reentrant_child_fails_closed(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": "from pkg import child",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "UNKNOWN"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c2_missing_member_no_child(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "entry": "from pkg import missing",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MISSING_EXPORT"
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c2_multiple_fromlist_members_unknown():
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "pass",
+        "pkg.b": "pass",
+        "entry": "from pkg import a, b",
+    }
+    assert _model(source, "entry").outcome == "UNKNOWN"
+
+
+def test_b0g4c2_shadowing_sequence_stays_unknown():
+    source = {
+        "pkg.__init__": "child=1\nimport pkg.child",
+        "pkg.child": "pass",
+    }
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+
+
+def test_b0g4c2_operation_budget_unknown():
+    source = {
+        "pkg.__init__": "pass",
+        "entry": "import pkg\n" * 10020,
+    }
+    assert _model(source, "entry").outcome == "UNKNOWN"
FULL_DIFFS_END
