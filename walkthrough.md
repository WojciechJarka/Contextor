TASK: CONTEXTOR_B0G4C3_REENTRANT_FROMLIST_SYS_MODULES
FINAL_VERDICT: B0G4C3_PASS

HEAD_BEFORE: 72ddc99d94b023a0fc83bab3868f64e6e3748bb4
HEAD_AFTER: 72ddc99d94b023a0fc83bab3868f64e6e3748bb4
GIT_STATUS_BEFORE: clean
LIVE_REVISION_BEFORE: 426
LIVE_REVISION_AFTER: 428
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242 (unchanged)
WATCHER_PROPAGATION: desktop_watcher UPDATED package_model.py at revision 427 and test_cycle_semantics_package_model.py at revision 428; continuity continuous, resync_required=false.
CANONICAL_STATE_AFTER: syntax, graph, cycles and collisions fresh; both changed modules workspace_sync=verified at revision 428.

FILES_CHANGED:
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
walkthrough.md is the report artifact, excluded from production/test changed files.

SOURCE_PRECHECK: Contextor resolved the exact evaluate_package_import_order implementation at verified revision 426. package_model owns the changed logic and has one direct static test consumer, tests.test_cycle_semantics_package_model, plus one outbound package_layout dependency. Artifact blast radius reports that test consumer and no production downstream module. The C1F explicit_alias and C2 single-fromlist/from-package child-loading anchors were present. HEAD was clean. Repository Python is 3.10.9.
BASELINE_TEST: The specified ten-file cycle_semantics suite passed 160 tests before editing.

IMPLEMENTATION_CONTRACT: Applied the auditor's literal same-thread fallback only in the C2 FROM child branch. An absent package attribute plus indexed INITIALIZING child is accepted only when that child is on active frames. The local alias binds to the child and emits FROM_REENTRANT_CHILD; the frame advances. The child is neither restarted nor marked READY by this branch. If INITIALIZING but absent from active frames, result stays UNKNOWN. All remaining C2 initialization, BIND_CHILD, READY, ATTR, precedence, multi-member, operation budget and C1F explicit_alias code is untouched. Replaced the superseded C2 test and appended exactly six C3 tests.
REENTRANT_FROMLIST_EVIDENCE: CODE_PATH_PROVED by the active-frame guard, local namespace binding and event. TEST_COVERED by direct, relative, explicit FROM alias and nested package fixtures; each corresponding _actual fixture executes synthesized imports in a fresh Python process.
SYS_MODULES_FALLBACK_EVIDENCE: INFERENCE tied to CPython 3.10 behavior described in the approved contract; the model does not read sys.modules. Direct evidence is agreement of the scoped model outcomes with fresh-process CPython 3.10.9 fixtures. The test event and success establish the supported same-thread case, not arbitrary sys.modules behavior.
EARLY_BINDING_NONREGRESSION: TEST_COVERED: an unbound value read from the INITIALIZING child returns EARLY_BINDING_HAZARD and the actual fixture fails; binding value before the reentrant read yields MODEL_PASS and the actual fixture succeeds. CODE_PATH_PROVED: fallback does not set READY and ATTR still sees INITIALIZING.
NESTED_PACKAGE_EVIDENCE: TEST_COVERED: pkg.sub.child reentrant fromlist emits FROM_REENTRANT_CHILD and agrees with the actual fresh-process fixture.
PARENT_CHILD_BINDING_AND_SINGLE_INIT: CODE_PATH_PROVED: fallback advances its current frame without adding a START_IMPORT or altering child state; existing READY completion performs BIND_CHILD. C2 parent-binding and single-child-initialization tests remain in the passing suite. No separate new C3 assertion of exact event order was added because the supplied patch and tests were applied literally.
C1F_C2_NONREGRESSION: Four C1F explicit alias tests and C2 package-member, precedence, BIND_CHILD, multi-member and budget tests remain in the passing ten-file suite. The C3 multi-member test also returns UNKNOWN.
DETERMINISM_AND_AST: Existing targeted determinism/no-AST-mutation test passes. The model does not execute indexed source; _actual fixtures compare behavior by running synthesized source in fresh processes.

TEST_COMMAND: & .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py
TEST_RESULTS: DIRECT_EVIDENCE: 166 passed in 8.66s; exit code 0. Baseline: 160 passed in 7.34s. git diff --check for both approved source/test files passed.
COLLISION_COUNT_BEFORE_AFTER: 0 fresh at revision 426 -> 0 fresh at revision 428.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 fresh at revision 426 -> 16 fresh at revision 428; same activity epoch and verified workspace sync.
NO_SAFETY_CERTIFICATION: MODEL_PASS is restricted-model evidence and does not certify arbitrary Python imports as safe.
NO_WARNING_SUPPRESSION: Full diff contains no warning, ArchitectureCycle, graph or diagnostic-policy changes. attention_required remains true because 16 preexisting cycles remain.
UNRESOLVED_LIMITATIONS: Concurrency, external import hooks, manual sys.modules modifications, arbitrary reloads, non-active INITIALIZING children, multiple fromlist members and imports outside the restricted indexed regular-package source set remain unmodeled or UNKNOWN by contract.
EVIDENCE_DISCIPLINE: DIRECT_EVIDENCE = Git, LIVE, tests and exact diff; CONTRACT_PROVED = supplied patch and Contextor source anchors; CODE_PATH_PROVED = active-frame branch and unchanged READY/ATTR paths; INFERENCE = correspondence to CPython's sys.modules fallback; UNKNOWN = general import safety.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 8e48249..4f291fc 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -430,8 +430,30 @@ def evaluate_package_import_order(
                     child = target + "." + member
 
                     if child in programs:
-                        # Reentrant fromlist fallback through sys.modules is
-                        # intentionally unsupported by this restricted model.
+                        # CPython 3.10 IMPORT_FROM can fall back to sys.modules
+                        # for a child that has not yet been attached to its
+                        # parent package. Model only the active same-thread case.
+                        if states[child] == "INITIALIZING":
+                            if not any(
+                                active == child
+                                for active, _ in frames
+                            ):
+                                return result("UNKNOWN", child, member)
+
+                            namespaces[module][step.binding] = child
+
+                            events.append(
+                                PackageModelEvent(
+                                    module,
+                                    "FROM_REENTRANT_CHILD",
+                                    child,
+                                    member,
+                                )
+                            )
+
+                            frames[-1] = (module, index + 1)
+                            continue
+
                         if states[child] != "NEW":
                             return result("UNKNOWN", child, member)
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index b4afeb4..f266770 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -443,13 +443,19 @@ def test_b0g4c2_regular_attribute_reexport(tmp_path):
     assert _actual(tmp_path, source, "pkg.user")
 
 
-def test_b0g4c2_reentrant_child_fails_closed(tmp_path):
+def test_b0g4c3_reentrant_child_uses_same_thread_fallback(tmp_path):
     source = {
         "pkg.__init__": "from . import child",
         "pkg.child": "from pkg import child",
     }
     result = _model(source, "pkg")
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "FROM_REENTRANT_CHILD"
+        and event.target == "pkg.child"
+        and event.module == "pkg.child"
+        for event in result.events
+    )
     assert _actual(tmp_path, source, "pkg")
 
 
@@ -487,3 +493,91 @@ def test_b0g4c2_operation_budget_unknown():
         "entry": "import pkg\n" * 10020,
     }
     assert _model(source, "entry").outcome == "UNKNOWN"
+
+
+def test_b0g4c3_early_read_from_reentrant_child(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": (
+            "from pkg import child\n"
+            "x=child.value\n"
+            "value=7"
+        ),
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg.child"
+    assert result.symbol == "value"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c3_bound_attribute_before_reentrant_read(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": (
+            "value=7\n"
+            "from pkg import child\n"
+            "x=child.value"
+        ),
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c3_relative_reentrant_child(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": "from . import child",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "FROM_REENTRANT_CHILD"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c3_explicit_from_alias(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": (
+            "value=7\n"
+            "from pkg import child as c\n"
+            "x=c.value"
+        ),
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "FROM_REENTRANT_CHILD"
+        and event.symbol == "child"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c3_nested_regular_package_fallback(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub.__init__": "from . import child",
+        "pkg.sub.child": "from pkg.sub import child",
+    }
+    result = _model(source, "pkg.sub")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "FROM_REENTRANT_CHILD"
+        and event.target == "pkg.sub.child"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "pkg.sub")
+
+
+def test_b0g4c3_multi_member_fromlist_still_unknown():
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.child": "pass",
+        "entry": "from pkg import child, missing",
+    }
+    assert _model(source, "entry").outcome == "UNKNOWN"
FULL_DIFFS_END
