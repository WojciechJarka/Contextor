TASK: CONTEXTOR_B0G4C5_CALL_ACTIVATED_IMPORTS
FINAL_VERDICT: B0G4C5_PARTIAL

HEAD_BEFORE: 095e46259bddba0e69c9050e44909070d817df45
HEAD_AFTER: 095e46259bddba0e69c9050e44909070d817df45
GIT_STATUS_BEFORE: clean
LIVE_REVISION_BEFORE: 430
LIVE_REVISION_AFTER: 430 (no watcher update observed)
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242 (unchanged)
SOURCE_SYNC_AFTER: Both edited modules are out_of_sync at canonical revision 430. Repeated get_live_events(after_revision=430) returned no events. No direct update_file, analysis, publish or restart was requested.

FILES_CHANGED:
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
walkthrough.md is the report artifact, excluded from production/test changed files.

SOURCE_PRECHECK: Contextor resolved the exact _compile and evaluate_package_import_order implementations at verified revision 430. package_model owns the changed logic, with tests.test_cycle_semantics_package_model as its sole direct static consumer and package_layout as its outbound dependency. Artifact blast radius identified that test consumer and no production downstream module. C1F explicit_alias, C2 from-package child loading, C3 FROM_REENTRANT_CHILD and C4 PREPARE_FROM_MEMBER anchors were present. HEAD was clean. Repository Python is 3.10.9.
BASELINE_TEST: The specified ten-file suite passed 178 tests before editing.

IMPLEMENTATION_CONTRACT: Applied the auditor's literal C5 patch. _Step carries restricted function body and function-local flags; compiler accepts only zero-argument undecorated top-level definitions with import/pass bodies and direct zero-argument top-level calls; execution stores definitions, expands the import-only body at call time, and withholds function-local import bindings from module namespace. Package child/function name shadowing preflight and call-sensitive rebinding guard were added exactly as specified. Prior C1F through C4 execution branches and budget were preserved. Exactly twelve C5 tests were appended.
DEFINITION_VS_INVOCATION_EVIDENCE: TEST_COVERED: an uncalled definition does not START_IMPORT the child; a direct call activates its import in source order. A definition exported through the package is visible to from-import consumers. CODE_PATH_PROVED by DEFINE_FUNCTION and CALL_FUNCTION branches.
FUNCTION_LOCAL_IMPORT_EVIDENCE: TEST_COVERED: a function-local alias is not exported from the module; child from-import sees an early unbound package name. CODE_PATH_PROVED by conditional namespace write and FUNCTION_LOCAL_IMPORT event.
EARLY_BINDING_RUNTIME_REGRESSION: TEST_COVERED: call before value binding returns EARLY_BINDING_HAZARD and fresh-process Python fails; binding value first gives MODEL_PASS and fresh-process Python succeeds. A flat module pair also exposes an early read.
FUNCTION_CACHE_AND_CALL_ORDER: TEST_COVERED: two calls are recorded and the child receives one START_IMPORT; fresh-process Python succeeds. CODE_PATH_PROVED: body steps are inserted immediately after each CALL_FUNCTION, with existing module state controlling repeat imports.
UNKNOWN_FAIL_CLOSED_EVIDENCE: TEST_COVERED: foreign call, missing local definition, overwritten function binding, and unsupported definitions/bodies return UNKNOWN.
C1F_C2_C3_C4_NONREGRESSION: The prior focused regressions remain within the passing ten-file suite; no old tests were removed or replaced. C5 deterministic result, AST byte-for-byte dump equivalence and JSON serialization test passed.
ANALYZED_SOURCE_EXECUTION: Production model compiles and simulates indexed ASTs without executing them; _actual test fixtures run synthesized source in fresh Python 3.10.9 processes.

TEST_COMMAND: & .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py
TEST_RESULTS: DIRECT_EVIDENCE: 190 passed in 12.42s; exit code 0. Baseline: 178 passed in 10.73s. git diff --check for the two approved source/test files passed.
COLLISION_COUNT_BEFORE_AFTER: Before: 0 fresh at synchronized revision 430. After: UNKNOWN for edited source because Contextor still reports both files out_of_sync at revision 430. The LIVE projection still displays 0, but it does not incorporate these edits.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: Before: 16 fresh at synchronized revision 430. After: UNKNOWN for edited source because no watcher update occurred. The LIVE projection still displays 16 for the old canonical state.
NO_SAFETY_CERTIFICATION: MODEL_PASS is restricted-model evidence only; neither the tests nor stale LIVE diagnostics certify arbitrary Python import safety.
NO_WARNING_SUPPRESSION: Actual source diff contains no graph, ArchitectureCycle, warning or diagnostic-policy modification. Canonical post-edit warning evidence is unavailable until synchronization.
UNRESOLVED_LIMITATIONS: Canonical LIVE synchronization is missing for both edited files; post-edit collision/cycle parity and Contextor architectural freshness are unverified. Concurrency, external hooks, manual sys.modules changes, reloading, arbitrary calls and syntax outside the restricted AST contract remain unmodeled by design. No cause is assigned to the missing watcher event without evidence.
EVIDENCE_DISCIPLINE: DIRECT_EVIDENCE = Git, tests, Contextor revision and out_of_sync status; CONTRACT_PROVED = auditor patch and source anchors; CODE_PATH_PROVED = C5 compile/execute branches; UNKNOWN = post-edit canonical diagnostics and general import safety.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 55deed6..50cc0b0 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -8,7 +8,7 @@ from __future__ import annotations
 
 import ast
 from collections.abc import Mapping
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 
 from contextor.core.cycle_semantics.package_layout import build_package_layout
 
@@ -38,6 +38,8 @@ class _Step:
     symbol: str | None = None
     binding: str | None = None
     explicit_alias: bool = False
+    function_body: tuple[_Step, ...] = ()
+    function_local: bool = False
 
 
 def _compile(
@@ -197,6 +199,83 @@ def _compile(
             else:
                 return None
 
+        elif isinstance(stmt, ast.FunctionDef):
+            args = stmt.args
+
+            if (
+                not stmt.name.isidentifier()
+                or stmt.name.startswith("__")
+                or stmt.decorator_list
+                or stmt.returns is not None
+                or stmt.type_comment is not None
+                or args.posonlyargs
+                or args.args
+                or args.vararg is not None
+                or args.kwonlyargs
+                or args.kwarg is not None
+                or args.defaults
+                or args.kw_defaults
+            ):
+                return None
+
+            function_steps: list[_Step] = []
+
+            for body_statement in stmt.body:
+                if isinstance(body_statement, ast.Pass):
+                    continue
+
+                if not isinstance(body_statement, ast.Import):
+                    return None
+
+                fragment = ast.Module(
+                    body=[body_statement],
+                    type_ignores=[],
+                )
+
+                compiled = _compile(
+                    fragment,
+                    logical,
+                    package,
+                )
+
+                if (
+                    compiled is None
+                    or any(item.op != "IMPORT" for item in compiled)
+                ):
+                    return None
+
+                function_steps.extend(
+                    replace(item, function_local=True)
+                    for item in compiled
+                )
+
+            steps.append(
+                _Step(
+                    "DEFINE_FUNCTION",
+                    binding=stmt.name,
+                    function_body=tuple(function_steps),
+                )
+            )
+
+        elif isinstance(stmt, ast.Expr):
+            expression = stmt.value
+
+            if (
+                not isinstance(expression, ast.Call)
+                or not isinstance(expression.func, ast.Name)
+                or expression.func.id.startswith("__")
+                or expression.args
+                or expression.keywords
+            ):
+                return None
+
+            steps.append(
+                _Step(
+                    "CALL_FUNCTION",
+                    target=expression.func.id,
+                )
+            )
+
         elif isinstance(stmt, ast.Pass):
             continue
 
@@ -286,7 +365,7 @@ def evaluate_package_import_order(
     if not valid_chain(entry_module):
         return result("UNKNOWN", entry_module)
 
-    programs: dict[str, tuple[_Step, ...]] = {}
+    programs: dict[str, list[_Step]] = {}
 
     for name, tree in logical_sources.items():
         if not valid_chain(name):
@@ -297,7 +376,7 @@ def evaluate_package_import_order(
         if program is None:
             return result("UNKNOWN", name)
 
-        programs[name] = program
+        programs[name] = list(program)
 
     # A package may prebind a same-named attribute before a later
     # from-import; the attribute takes priority. Keep more complex
@@ -308,6 +387,16 @@ def evaluate_package_import_order(
             for name in programs
             if "." in name and name.rsplit(".", 1)[0] == package
         }
+        # A function and a direct indexed child with the
+        # same package attribute name need richer shadowing
+        # and import-binding semantics.
+        if any(
+            step.op == "DEFINE_FUNCTION"
+            and step.binding in children
+            for step in programs[package]
+        ):
+            return result("UNKNOWN", package)
+
         writes_child = any(
             step.binding in children
             and (
@@ -317,7 +406,7 @@ def evaluate_package_import_order(
             for step in programs[package]
         )
         if writes_child and any(
-            step.op in {"IMPORT", "FROM"}
+            step.op in {"IMPORT", "FROM", "CALL_FUNCTION"}
             for step in programs[package]
         ):
             return result("UNKNOWN", package)
@@ -332,6 +421,14 @@ def evaluate_package_import_order(
         for name in programs
     }
 
+    function_definitions: dict[
+        str,
+        dict[str, tuple[_Step, ...]],
+    ] = {
+        name: {}
+        for name in programs
+    }
+
     bootstrap = "\x00ENTRY"
     frames: list[tuple[str, int]] = [(bootstrap, 0)]
 
@@ -484,12 +581,17 @@ def evaluate_package_import_order(
                         else target.split(".")[0]
                     )
 
-                    namespaces[module][step.binding] = binding_target
+                    if not step.function_local:
+                        namespaces[module][step.binding] = binding_target
 
                     events.append(
                         PackageModelEvent(
                             module,
-                            "IMPORT",
+                            (
+                                "FUNCTION_LOCAL_IMPORT"
+                                if step.function_local
+                                else "IMPORT"
+                            ),
                             target,
                             step.binding,
                         )
@@ -579,6 +681,58 @@ def evaluate_package_import_order(
                     )
                 )
 
+        elif step.op == "DEFINE_FUNCTION":
+            function_definitions[module][step.binding] = (
+                step.function_body
+            )
+
+            namespaces[module][step.binding] = (
+                "\x00FUNCTION:" + module + ":" + step.binding
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_FUNCTION",
+                    symbol=step.binding,
+                )
+            )
+
+        elif step.op == "CALL_FUNCTION":
+            expected_binding = (
+                "\x00FUNCTION:" + module + ":" + step.target
+            )
+
+            if (
+                namespaces[module].get(step.target)
+                != expected_binding
+                or step.target
+                not in function_definitions[module]
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
+            # Expand the function's restricted import-only body
+            # at its actual call site. This changes only the
+            # in-memory compiled execution sequence, never
+            # caller AST or source bytes.
+            body_steps = function_definitions[module][step.target]
+
+            programs[module][
+                index + 1:index + 1
+            ] = list(body_steps)
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "CALL_FUNCTION",
+                    symbol=step.target,
+                )
+            )
+
         elif step.op == "BIND":
             namespaces[module][step.binding] = None
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index e526e8f..4becc17 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -744,3 +744,204 @@ def test_b0g4c4_namespace_layout_remains_unknown():
         "entry": "from pkg import a,b",
     }
     assert _model(source, "entry").outcome == "UNKNOWN"
+
+
+def test_b0g4c5_deferred_function_import_not_executed(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    import pkg.child\n"
+            "value=7"
+        ),
+        "pkg.child": "import pkg\nx=pkg.missing",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert not any(
+        e.operation == "START_IMPORT"
+        and e.target == "pkg.child"
+        for e in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_call_activates_early_binding_hazard(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    import pkg.child\n"
+            "load()\n"
+            "value=7"
+        ),
+        "pkg.child": "import pkg\nx=pkg.value",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "value"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_binding_before_call_passes(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    import pkg.child\n"
+            "value=7\n"
+            "load()"
+        ),
+        "pkg.child": "import pkg\nx=pkg.value",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_function_local_import_not_exported(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def activate():\n"
+            "    import pkg.child as local_only\n"
+            "activate()"
+        ),
+        "pkg.child": "from pkg import local_only",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "local_only"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_repeated_calls_import_child_once(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def activate():\n"
+            "    import pkg.child\n"
+            "activate()\n"
+            "activate()"
+        ),
+        "pkg.child": "value=7",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert sum(
+        e.operation == "START_IMPORT"
+        and e.target == "pkg.child"
+        for e in result.events
+    ) == 1
+    assert sum(
+        e.operation == "CALL_FUNCTION"
+        for e in result.events
+    ) == 2
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_plain_flat_module_function_call(tmp_path):
+    source = {
+        "a": (
+            "def load():\n"
+            "    import b\n"
+            "load()\n"
+            "value=7"
+        ),
+        "b": "import a\nx=a.value",
+    }
+    result = _model(source, "a")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert not _actual(tmp_path, source, "a")
+
+
+def test_b0g4c5_exported_definition_is_available(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    pass"
+        ),
+        "pkg.user": "from pkg import load",
+    }
+    result = _model(source, "pkg.user")
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg.user")
+
+
+def test_b0g4c5_foreign_function_call_unknown():
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    import pkg.child"
+        ),
+        "pkg.child": "pass",
+        "pkg.user": (
+            "from pkg import load\n"
+            "load()"
+        ),
+    }
+    assert _model(source, "pkg.user").outcome == "UNKNOWN"
+
+
+def test_b0g4c5_call_without_local_definition_unknown():
+    source = {
+        "pkg.__init__": "missing()",
+    }
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+
+
+def test_b0g4c5_shadowed_function_call_unknown(tmp_path):
+    source = {
+        "pkg.__init__": (
+            "def load():\n"
+            "    pass\n"
+            "load=3\n"
+            "load()"
+        ),
+    }
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_b0g4c5_unsupported_definition_effects_unknown():
+    samples = [
+        "def f(x=1):\n    import pkg.child",
+        "def f(x):\n    import pkg.child",
+        "@decorator\ndef f():\n    import pkg.child",
+        "def f() -> int:\n    import pkg.child",
+        "def f():\n    from pkg import child",
+        "def f():\n    helper()",
+        "async def f():\n    import pkg.child",
+        "def f():\n    return 1",
+    ]
+    for code in samples:
+        assert _model(
+            {"pkg.__init__": code, "pkg.child": "pass"},
+            "pkg",
+        ).outcome == "UNKNOWN"
+
+
+def test_b0g4c5_deterministic_ast_unchanged():
+    source = {
+        "pkg.__init__": ast.parse(
+            "def activate():\n"
+            "    import pkg.child\n"
+            "activate()"
+        ),
+        "pkg.child": ast.parse("pass"),
+    }
+
+    before = {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in source.items()
+    }
+
+    first = evaluate_package_import_order(source, "pkg")
+    second = evaluate_package_import_order(source, "pkg")
+
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+
+    assert {
+        key: ast.dump(tree, include_attributes=True)
+        for key, tree in source.items()
+    } == before
+
+    json.dumps(asdict(first))
FULL_DIFFS_END
