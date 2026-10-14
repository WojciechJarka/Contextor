TASK: CONTEXTOR_B0G4C4_MULTI_MEMBER_FROMLIST_PHASES
FINAL_VERDICT: B0G4C4_PASS

HEAD_BEFORE: d595b1dccbae1d77cbb85c9e5fe85e22953f4ce1
HEAD_AFTER: d595b1dccbae1d77cbb85c9e5fe85e22953f4ce1
GIT_STATUS_BEFORE: clean
LIVE_REVISION_BEFORE: 428
LIVE_REVISION_AFTER: 430
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242 (unchanged)
WATCHER_PROPAGATION: desktop_watcher UPDATED package_model.py at revision 429 and test_cycle_semantics_package_model.py at revision 430; continuity continuous, resync_required=false.
CANONICAL_STATE_AFTER: syntax, graph, cycles and collisions fresh; both changed modules workspace_sync=verified at revision 430.

FILES_CHANGED:
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
walkthrough.md is the report artifact, excluded from source/test changed files.

SOURCE_PRECHECK: Contextor resolved _compile and evaluate_package_import_order at verified revision 428. package_model owns the changed logic, with one direct static test consumer and package_layout as its outbound dependency. Artifact blast radius reports tests.test_cycle_semantics_package_model as the direct consumer and no production downstream module. C1F explicit_alias, C2 child loading and C3 FROM_REENTRANT_CHILD anchors were present. HEAD and Git status were clean. Repository Python is 3.10.9.
BASELINE_TEST: The specified ten-file suite passed 166 tests before editing.

IMPLEMENTATION_CONTRACT: Applied the auditor's literal compiler phase split for multi-member ast.ImportFrom: validate all names; emit all PREPARE_FROM_MEMBER steps; then emit existing FROM steps. Target loading includes preparation. Preparation respects an existing package attribute, starts a NEW indexed child, accepts only active-stack INITIALIZING child without restarting it, and returns UNKNOWN for an unexpected READY child without parent binding. It records a preparation event and binds no local alias. Single-member FROM, explicit_alias, C3 fallback, existing child READY/BIND_CHILD and step budget paths were retained. Replaced exactly two superseded tests and appended exactly twelve C4 tests.
PREPARATION_BEFORE_BINDING_EVIDENCE: TEST_COVERED by exact event sequence PREPARE_FROM_MEMBER, PREPARE_FROM_MEMBER, FROM, FROM for the importer. CODE_PATH_PROVED by compiler step ordering and absence of local namespace binding in PREPARE_FROM_MEMBER.
EARLY_BINDING_RUNTIME_REGRESSION: TEST_COVERED: loading second child reimports the still-initializing entry and reads entry.a before local binding; model returns EARLY_BINDING_HAZARD for entry/a and the fresh-process fixture fails.
FROM_PACKAGE_PRECEDENCE_EVIDENCE: TEST_COVERED: a preexisting package a attribute prevents START_IMPORT of indexed pkg.a; the positive fixture agrees with fresh-process Python. C2 single-member precedence tests remain passing.
REENTRANT_FROM_EVIDENCE: TEST_COVERED: a child chain reaches C3 FROM_REENTRANT_CHILD and succeeds in fresh-process Python. C3 direct, relative, alias, nested and early-read tests remain passing.
SINGLE_FROM_NONREGRESSION: CODE_PATH_PROVED: preparation steps are emitted only when len(stmt.names) > 1, leaving single-member compilation unchanged. Existing C2/C3 single-member fixtures remain in the passing suite.
C1F_C2_C3_NONREGRESSION: All prior focused regressions remain in the 178-pass suite; only the two specified multi-member expectations were superseded. Existing budget, determinism, AST immutability, C1F explicit alias, C2 package resolution and C3 fallback coverage passed.
RUNTIME_FIXTURE_SCOPE: Positive and negative _actual fixtures run synthesized source in fresh repository Python 3.10.9 processes. The model itself does not execute analyzed source.

TEST_COMMAND: & .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py
TEST_RESULTS: DIRECT_EVIDENCE: 178 passed in 10.84s; exit code 0. Baseline: 166 passed in 7.50s. git diff --check for both approved source/test files passed.
COLLISION_COUNT_BEFORE_AFTER: 0 fresh at revision 428 -> 0 fresh at revision 430.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 fresh at revision 428 -> 16 fresh at revision 430; same activity epoch and verified workspace sync.
NO_SAFETY_CERTIFICATION: MODEL_PASS is restricted-model evidence, never a general Python import safety certification.
NO_WARNING_SUPPRESSION: The exact diff has no graph, ArchitectureCycle, warning or diagnostic policy changes. attention_required remains true because 16 preexisting structural cycles remain.
UNRESOLVED_LIMITATIONS: Arbitrary import hooks, external/manual sys.modules changes, concurrency, reloads, non-indexed namespace packages and syntax outside the restricted AST contract remain unmodeled or UNKNOWN. This stage does not claim general import safety.
EVIDENCE_DISCIPLINE: DIRECT_EVIDENCE = Git, LIVE, tests and exact diff; CONTRACT_PROVED = auditor patch and Contextor source anchors; CODE_PATH_PROVED = compiler/prepare ordering and unchanged single FROM path; UNKNOWN = general runtime import safety.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 4f291fc..55deed6 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -72,9 +72,9 @@ def _compile(
                 )
 
         elif isinstance(stmt, ast.ImportFrom):
-            # Python resolves the entire fromlist before its STORE_NAME steps.
-            # This model processes single members only, to avoid false proofs.
-            if len(stmt.names) != 1:
+            # CPython resolves the fromlist during IMPORT_NAME,
+            # before individual IMPORT_FROM / STORE_NAME operations.
+            if not stmt.names:
                 return None
             if stmt.level:
                 context = (
@@ -106,6 +106,31 @@ def _compile(
             ):
                 return None
 
+            if len(stmt.names) > 1:
+                # Validate every member before emitting phase steps.
+                if any(
+                    not alias.name.isidentifier()
+                    or alias.name.startswith("__")
+                    or (
+                        alias.asname is not None
+                        and (
+                            not alias.asname.isidentifier()
+                            or alias.asname.startswith("__")
+                        )
+                    )
+                    for alias in stmt.names
+                ):
+                    return None
+
+                for alias in stmt.names:
+                    steps.append(
+                        _Step(
+                            "PREPARE_FROM_MEMBER",
+                            target,
+                            alias.name,
+                        )
+                    )
+
             for alias in stmt.names:
                 if (
                     not alias.name.isidentifier()
@@ -370,7 +395,11 @@ def evaluate_package_import_order(
 
         step = steps[index]
 
-        if step.op in {"IMPORT", "FROM"}:
+        if step.op in {
+            "IMPORT",
+            "FROM",
+            "PREPARE_FROM_MEMBER",
+        }:
             target = step.target
 
             if not target or target not in programs:
@@ -395,7 +424,53 @@ def evaluate_package_import_order(
                 frames.append((next_piece, 0))
                 continue
 
-            if step.op == "IMPORT":
+            if step.op == "PREPARE_FROM_MEMBER":
+                member = step.symbol
+
+                if (
+                    target in packages
+                    and member not in namespaces[target]
+                ):
+                    child = target + "." + member
+
+                    if child in programs:
+                        if states[child] == "NEW":
+                            if missing_piece(child) != child:
+                                return result("UNKNOWN", child, member)
+
+                            states[child] = "INITIALIZING"
+
+                            events.append(
+                                PackageModelEvent(
+                                    module,
+                                    "START_IMPORT",
+                                    child,
+                                )
+                            )
+
+                            frames.append((child, 0))
+                            continue
+
+                        if states[child] == "INITIALIZING":
+                            if not any(
+                                active == child
+                                for active, _ in frames
+                            ):
+                                return result("UNKNOWN", child, member)
+
+                        elif states[child] == "READY":
+                            return result("UNKNOWN", child, member)
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        "PREPARE_FROM_MEMBER",
+                        target,
+                        member,
+                    )
+                )
+
+            elif step.op == "IMPORT":
                 if module != bootstrap:
                     if step.explicit_alias and "." in target:
                         parent, child = target.rsplit(".", 1)
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index f266770..e526e8f 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -469,14 +469,16 @@ def test_b0g4c2_missing_member_no_child(tmp_path):
     assert not _actual(tmp_path, source, "entry")
 
 
-def test_b0g4c2_multiple_fromlist_members_unknown():
+def test_b0g4c4_multiple_fromlist_members_supported(tmp_path):
     source = {
         "pkg.__init__": "pass",
         "pkg.a": "pass",
         "pkg.b": "pass",
         "entry": "from pkg import a, b",
     }
-    assert _model(source, "entry").outcome == "UNKNOWN"
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "entry")
 
 
 def test_b0g4c2_shadowing_sequence_stays_unknown():
@@ -574,10 +576,171 @@ def test_b0g4c3_nested_regular_package_fallback(tmp_path):
     assert _actual(tmp_path, source, "pkg.sub")
 
 
-def test_b0g4c3_multi_member_fromlist_still_unknown():
+def test_b0g4c4_multi_member_missing_export(tmp_path):
     source = {
         "pkg.__init__": "pass",
         "pkg.child": "pass",
         "entry": "from pkg import child, missing",
     }
+    result = _model(source, "entry")
+    assert result.outcome == "MISSING_EXPORT"
+    assert result.target_module == "pkg"
+    assert result.symbol == "missing"
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_preparation_before_local_binding_hazard(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "value=1",
+        "pkg.b": "import entry\nx=entry.a",
+        "entry": "from pkg import a,b",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "entry"
+    assert result.symbol == "a"
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_all_prepares_before_from_bindings(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "pass",
+        "pkg.b": "pass",
+        "entry": "from pkg import a,b",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    operations = [
+        e.operation
+        for e in result.events
+        if e.module == "entry"
+        and e.operation in {"PREPARE_FROM_MEMBER", "FROM"}
+    ]
+    assert operations == [
+        "PREPARE_FROM_MEMBER",
+        "PREPARE_FROM_MEMBER",
+        "FROM",
+        "FROM",
+    ]
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_aliases_after_preparation(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "value=1",
+        "pkg.b": "value=2",
+        "entry": "from pkg import a as aa,b as bb\nx=aa.value",
+    }
+    assert _model(source, "entry").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_multi_from_plain_module(tmp_path):
+    source = {
+        "provider": "x=1\ny=2",
+        "entry": "from provider import x,y",
+    }
+    assert _model(source, "entry").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_relative_multi_in_initializer(tmp_path):
+    source = {
+        "pkg.__init__": "from . import a,b",
+        "pkg.a": "value=1",
+        "pkg.b": "from pkg import a\nx=a.value",
+    }
+    assert _model(source, "pkg").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c4_relative_multi_in_module(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "value=1",
+        "pkg.b": "value=2",
+        "pkg.user": "from . import a,b",
+    }
+    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg.user")
+
+
+def test_b0g4c4_nested_relative_multi(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.sub.__init__": "from . import a,b",
+        "pkg.sub.a": "pass",
+        "pkg.sub.b": "pass",
+    }
+    assert _model(source, "pkg.sub").outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg.sub")
+
+
+def test_b0g4c4_attribute_precedence_during_preparation(tmp_path):
+    source = {
+        "pkg.__init__": "a=7",
+        "pkg.a": "pass",
+        "pkg.b": "pass",
+        "entry": "from pkg import a,b",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert not any(
+        e.operation == "START_IMPORT" and e.target == "pkg.a"
+        for e in result.events
+    )
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_reentrant_child_chain(tmp_path):
+    source = {
+        "pkg.__init__": "from . import a,b",
+        "pkg.a": "from pkg import b",
+        "pkg.b": "from pkg import a",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        e.operation == "FROM_REENTRANT_CHILD"
+        for e in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c4_later_child_loads_before_missing_export(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.b": "pass",
+        "entry": "from pkg import missing,b",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MISSING_EXPORT"
+    assert ("pkg.b", "READY") in [
+        (e.module, e.operation)
+        for e in result.events
+    ]
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_sibling_uses_prepared_child(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "value=1",
+        "pkg.b": "from pkg import a\nx=a.value",
+        "entry": "from pkg import a,b",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_b0g4c4_namespace_layout_remains_unknown():
+    source = {
+        "pkg.a": "pass",
+        "pkg.b": "pass",
+        "entry": "from pkg import a,b",
+    }
     assert _model(source, "entry").outcome == "UNKNOWN"
FULL_DIFFS_END
