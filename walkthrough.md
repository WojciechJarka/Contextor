# CONTEXTOR_B0G4C23_PASSIVE_FUNCTION_DEFINITION_BINDING

TASK: Controlled literal implementation of passive function binding in the restricted import-order model.
HEAD_BEFORE: c5697ee1c81ba1b2b52a1cf7613168176b25d8b1.
HEAD_AFTER: c5697ee1c81ba1b2b52a1cf7613168176b25d8b1.
GIT_STATUS: Current task modifies contextor/core/cycle_semantics/package_model.py and creates tests/test_cycle_semantics_passive_functions.py; walkthrough.md overwritten as mandated report. Pre-existing C22 modifications and untracked weighted_closures.py, test_cycle_semantics_main_guard.py, test_cycle_semantics_weighted_closures.py remain untouched by C23.
FILES_CHANGED: contextor/core/cycle_semantics/package_model.py; tests/test_cycle_semantics_passive_functions.py. FULL_DIFFS below contain C23 changes only, relative to the verified post-C22 source, without repeating C22's prior diff.

MODEL_CONTRACT_PRECHECK: DIRECT_EVIDENCE: Contextor get_file_edit_context at LIVE revision 450 identified package_model as canonical owner, adapter layer, fresh and workspace_sync=verified. Complete _compile implementation obtained (lines 45-345); _Step, DEFINE_FUNCTION, CALL_FUNCTION and child-shadowing guards matched specified anchors. get_symbol_implementation confirmed real run_repo_generator(parent=None) at main.py:522 and gui.run(*, single_instance=None) at gui.py:2283. Blast radius named five existing direct test consumers before edit. The complete evaluate_package_import_order fetch returned confirmation_required due payload size; exact relevant branches were verified from source after Contextor discovery. No material anchor drift.
FUNCTION_SIGNATURE_SAFETY: CONTRACT_PROVED: _safe_passive_function_definition rejects decorators, return/parameter annotations, type comments/type parameters, reserved names and dynamic defaults. It accepts literal positional and keyword-only defaults. It does not interpret function bodies.
PASSIVE_BINDING_SEMANTICS: CONTRACT_PROVED: safe opaque definitions emit DEFINE_OPAQUE_FUNCTION; evaluator binds a distinct opaque marker at definition time and records event. No body step is emitted or run.
OPAQUE_CALL_FAIL_CLOSED: CONTRACT_PROVED: existing CALL_FUNCTION identity check is unchanged; the opaque marker does not match a restricted function identity, so invocation returns UNKNOWN. New test passes.
EXISTING_FUNCTION_LOCAL_SEMANTICS: Restricted parameterless import-only function compilation and function-local import activation remain present. New parity test and existing tests for this behavior passed.
PACKAGE_EXPORT_BINDING_ORDER: Synthetic re-export test confirms safe function binds before initializer from-import resolves. Definition order remains source order.
REENTRANT_EARLY_BINDING_HAZARD: Synthetic delayed export reports EARLY_BINDING_HAZARD for pkg.a.f; CPython isolated process raises ImportError.
SYNTHETIC_TWO_ENTRY_CPYTHON_PARITY: Parametrized repo-first case: model EARLY_BINDING_HAZARD for repo.run_repo_generator and CPython ImportError. ui-first case: model MODEL_PASS and CPython import succeeds. Both passed. These are synthetic packages, not real GUI execution.
UNSUPPORTED_DEFINITION_REJECTIONS: Dynamic default, decorator and annotation cases return UNKNOWN in new tests. Class definitions remain unsupported.
DETERMINISM_AND_INPUT_IMMUTABILITY: Two assessments equal; AST dumps unchanged; dataclasses.asdict result JSON serializable. New test passed.

ISOLATED_TEST_RESULTS: 13 passed in 2.62s.
FOCUSED_TEST_RESULTS: 328 passed, 2 failed in 21.56s across exactly the 20 specified focused files. Failures:
- tests/test_cycle_semantics_function_local_from.py::test_unsupported_function_semantics_stay_unknown (line 471): legacy assertion expects UNKNOWN for every sample, including literal-default or opaque-body definition now intentionally modeled as passive MODEL_PASS.
- tests/test_cycle_semantics_package_model.py::test_b0g4c5_unsupported_definition_effects_unknown (line 914): legacy assertion expects UNKNOWN for literal-default/opaque-body definitions now intentionally modeled as passive MODEL_PASS.
DIRECT_EVIDENCE: both failures compare actual MODEL_PASS with expected UNKNOWN. This is an existing test-contract conflict with the auditor's C23 semantics. The task explicitly permits creating only the new test file; changing these legacy test files was not authorized. No additional tests or source adjustments were made after this finding. The exact failing sample within each loop was not isolated, because doing so would repeat tests without changing the conclusion.
LIVE_REVISION_BEFORE_AFTER: 450 -> 452.
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242 before and after.
LIVE_EVENT_CONTINUITY: get_live_events(after_revision=450) returned continuous, resync_required=false; desktop_watcher UPDATED for production file at revision 451 and new test file at revision 452.
WORKSPACE_SYNC: Contextor get_file_edit_context at revision 452 returned verified for both task files.
CANONICAL_FRESHNESS: Both task files canonical_state=fresh at 452; module/graph/topology/artifact-consumption/cycles/collisions/lineage fresh; syntax errors 0. Post-edit blast radius adds new test as sixth direct static consumer.
COLLISION_COUNT_BEFORE_AFTER: 0 -> 0, fresh.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 -> 16 reported paths, fresh. No warning policy or canonical graph change.
NO_RUNTIME_SAFETY_CERTIFICATION: Synthetic CPython comparisons do not certify the real SCC modules or general Python import safety.
NO_WARNING_SUPPRESSION: None.
UNRESOLVED_LIMITATIONS: The two legacy test expectations require an auditor decision in a separately authorized stage. The specified PASS gate 330/330 is unmet. General opaque-body invocation and real GUI/repo-generator import behavior remain UNKNOWN.
FINAL_VERDICT: B0G4C23_PARTIAL. Exact production patch and 13 new tests passed; LIVE synchronized without diagnostic regression; focused gate failed 328 passed / 2 failed due the identified legacy assertions. STOP and await proceduj.

FULL_DIFFS

ACTUAL_DIFF: contextor/core/cycle_semantics/package_model.py (C23-only)
~~~diff
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -40,6 +40,77 @@
     explicit_alias: bool = False
     function_body: tuple[_Step, ...] = ()
     function_local: bool = False
+
+
+def _safe_passive_function_definition(
+    statement: ast.FunctionDef,
+) -> bool:
+    """A definition whose creation has no unknown evaluations.
+
+    Its body may be opaque because function bodies are deferred.
+    Only literal default expressions are supported.
+    """
+    if (
+        not statement.name.isidentifier()
+        or statement.name.startswith("__")
+        or statement.decorator_list
+        or statement.returns is not None
+        or statement.type_comment is not None
+        or getattr(statement, "type_params", ())
+    ):
+        return False
+
+    arguments = statement.args
+
+    parameters = (
+        tuple(arguments.posonlyargs)
+        + tuple(arguments.args)
+        + tuple(arguments.kwonlyargs)
+        + (
+            (arguments.vararg,)
+            if arguments.vararg is not None
+            else ()
+        )
+        + (
+            (arguments.kwarg,)
+            if arguments.kwarg is not None
+            else ()
+        )
+    )
+
+    if any(
+        parameter.annotation is not None
+        for parameter in parameters
+    ):
+        return False
+
+    def safe_default(value: ast.AST) -> bool:
+        return (
+            isinstance(value, ast.Constant)
+            and type(value.value) in (
+                type(None),
+                bool,
+                int,
+                float,
+                complex,
+                str,
+                bytes,
+            )
+        )
+
+    if any(
+        not safe_default(value)
+        for value in arguments.defaults
+    ):
+        return False
+
+    if any(
+        value is not None and not safe_default(value)
+        for value in arguments.kw_defaults
+    ):
+        return False
+
+    return True
 
 
 def _compile(
@@ -250,72 +321,83 @@
                 return None
 
         elif isinstance(stmt, ast.FunctionDef):
+            if not _safe_passive_function_definition(stmt):
+                return None
+
             args = stmt.args
 
-            if (
-                not stmt.name.isidentifier()
-                or stmt.name.startswith("__")
-                or stmt.decorator_list
-                or stmt.returns is not None
-                or stmt.type_comment is not None
-                or args.posonlyargs
+            restricted_callable = not (
+                args.posonlyargs
                 or args.args
                 or args.vararg is not None
                 or args.kwonlyargs
                 or args.kwarg is not None
                 or args.defaults
                 or args.kw_defaults
-            ):
-                return None
+            )
 
             function_steps: list[_Step] = []
 
-            for body_statement in stmt.body:
-                if isinstance(body_statement, ast.Pass):
-                    continue
-
-                if not isinstance(
-                    body_statement,
-                    (ast.Import, ast.ImportFrom),
-                ):
-                    return None
-
-                fragment = ast.Module(
-                    body=[body_statement],
-                    type_ignores=[],
-                )
-
-                compiled = _compile(
-                    fragment,
-                    logical,
-                    package,
-                )
-
-                if (
-                    compiled is None
-                    or any(
-                        item.op not in {
-                            "IMPORT",
-                            "FROM",
-                            "PREPARE_FROM_MEMBER",
-                        }
+            if restricted_callable:
+                for body_statement in stmt.body:
+                    if isinstance(body_statement, ast.Pass):
+                        continue
+
+                    if not isinstance(
+                        body_statement,
+                        (ast.Import, ast.ImportFrom),
+                    ):
+                        restricted_callable = False
+                        break
+
+                    fragment = ast.Module(
+                        body=[body_statement],
+                        type_ignores=[],
+                    )
+
+                    compiled = _compile(
+                        fragment,
+                        logical,
+                        package,
+                    )
+
+                    if (
+                        compiled is None
+                        or any(
+                            item.op not in {
+                                "IMPORT",
+                                "FROM",
+                                "PREPARE_FROM_MEMBER",
+                            }
+                            for item in compiled
+                        )
+                    ):
+                        restricted_callable = False
+                        break
+
+                    function_steps.extend(
+                        replace(
+                            item,
+                            function_local=True,
+                        )
                         for item in compiled
                     )
-                ):
-                    return None
-
-                function_steps.extend(
-                    replace(item, function_local=True)
-                    for item in compiled
-                )
-
-            steps.append(
-                _Step(
-                    "DEFINE_FUNCTION",
-                    binding=stmt.name,
-                    function_body=tuple(function_steps),
-                )
-            )
+
+            if restricted_callable:
+                steps.append(
+                    _Step(
+                        "DEFINE_FUNCTION",
+                        binding=stmt.name,
+                        function_body=tuple(function_steps),
+                    )
+                )
+            else:
+                steps.append(
+                    _Step(
+                        "DEFINE_OPAQUE_FUNCTION",
+                        binding=stmt.name,
+                    )
+                )
 
         elif isinstance(stmt, ast.Expr):
             expression = stmt.value
@@ -451,7 +533,10 @@
         # same package attribute name need richer shadowing
         # and import-binding semantics.
         if any(
-            step.op == "DEFINE_FUNCTION"
+            step.op in {
+                "DEFINE_FUNCTION",
+                "DEFINE_OPAQUE_FUNCTION",
+            }
             and step.binding in children
             for step in programs[package]
         ):
@@ -768,6 +853,22 @@
                 )
             )
 
+        elif step.op == "DEFINE_OPAQUE_FUNCTION":
+            namespaces[module][step.binding] = (
+                "\x00OPAQUE_FUNCTION:"
+                + module
+                + ":"
+                + step.binding
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_OPAQUE_FUNCTION",
+                    symbol=step.binding,
+                )
+            )
+
         elif step.op == "CALL_FUNCTION":
             expected_binding = (
                 "\x00FUNCTION:" + module + ":" + step.target
~~~

ACTUAL_DIFF: tests/test_cycle_semantics_passive_functions.py
~~~diff
--- /dev/null
+++ b/tests/test_cycle_semantics_passive_functions.py
@@ -0,0 +1,231 @@
+"""CPython parity for passive function definitions in package imports."""
+
+import ast
+import json
+import subprocess
+import sys
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _model(sources, entry):
+    return evaluate_package_import_order(
+        {name: ast.parse(source) for name, source in sources.items()},
+        entry,
+    )
+
+
+def _actual(tmp_path, sources, entry):
+    for module, source in sources.items():
+        parts = module.split(".")
+        path = tmp_path.joinpath(
+            *parts[:-1],
+            "__init__.py"
+            if parts[-1] == "__init__"
+            else parts[-1] + ".py",
+        )
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(source + "\n", encoding="utf-8")
+
+    return subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            (
+                "import importlib,sys;"
+                "sys.path.insert(0,sys.argv[1]);"
+                "importlib.import_module(sys.argv[2])"
+            ),
+            str(tmp_path),
+            entry,
+        ],
+        capture_output=True,
+        text=True,
+        timeout=10,
+        check=False,
+    )
+
+
+def test_c23_positional_default_opaque_binding(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": 'def f(value=None):\n    raise RuntimeError("not called")',
+    }
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "f"
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_c23_keyword_only_default_opaque_binding(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "def run(*, single_instance=None):\n"
+            '    raise RuntimeError("not called")'
+        ),
+    }
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "run"
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_c23_zero_arg_opaque_body_not_executed(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f():\n    dangerous()",
+    }
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert any(event.operation == "DEFINE_OPAQUE_FUNCTION" for event in result.events)
+    assert not any(event.operation == "CALL_FUNCTION" for event in result.events)
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_c23_existing_restricted_function_preserved(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f():\n    from pkg import child\nf()",
+        "pkg.child": "pass",
+    }
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert any(event.operation == "CALL_FUNCTION" for event in result.events)
+    assert any(
+        event.operation.startswith("FUNCTION_LOCAL_FROM") for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_c23_passive_reexport_is_available(tmp_path):
+    sources = {
+        "pkg.__init__": "from pkg.a import f",
+        "pkg.a": "def f(x=None):\n    dangerous()",
+    }
+    result = _model(sources, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_OPAQUE_FUNCTION" and event.symbol == "f"
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg").returncode == 0
+
+
+def test_c23_reentrant_early_export_still_hazard(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "from pkg.b import ready\ndef f(x=None):\n    dangerous()",
+        "pkg.b": "from pkg.a import f\nready = 1",
+    }
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert (result.target_module, result.symbol) == ("pkg.a", "f")
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert process.returncode != 0
+    assert "ImportError" in process.stderr
+
+
+@pytest.mark.parametrize(
+    ("entry", "expected_outcome", "expected_module", "expected_symbol"),
+    [
+        ("repo", "EARLY_BINDING_HAZARD", "repo", "run_repo_generator"),
+        ("ui", "MODEL_PASS", None, None),
+    ],
+)
+def test_c23_two_package_entry_order(
+    tmp_path, entry, expected_outcome, expected_module, expected_symbol
+):
+    sources = {
+        "repo.__init__": "from repo.main import run_repo_generator",
+        "repo.main": (
+            "from repo.filters import ready\n"
+            "def run_repo_generator(parent=None):\n"
+            "    dangerous()"
+        ),
+        "repo.filters": "from ui import theme\nready = 1",
+        "ui.__init__": "from ui.gui import run",
+        "ui.gui": (
+            "from repo import run_repo_generator\n"
+            "def run(*, single_instance=None):\n"
+            "    dangerous()"
+        ),
+        "ui.theme": "ready = 1",
+    }
+    result = _model(sources, entry)
+    assert result.outcome == expected_outcome
+    assert (result.target_module, result.symbol) == (
+        expected_module,
+        expected_symbol,
+    )
+    process = _actual(tmp_path, sources, entry)
+    if expected_outcome == "MODEL_PASS":
+        assert process.returncode == 0
+    else:
+        assert process.returncode != 0
+        assert "ImportError" in process.stderr
+
+
+def test_c23_opaque_call_is_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f(value=None):\n    pass\nf()",
+    }
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_c23_dynamic_default_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f(x=compute_default()):\n    pass",
+    }
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_c23_decorator_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "@decorator\ndef f():\n    pass",
+    }
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_c23_annotation_unknown():
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f(x: unknown_annotation):\n    pass",
+    }
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_c23_determinism_ast_immutability_json():
+    trees = {
+        "pkg.__init__": ast.parse("from pkg.a import f"),
+        "pkg.a": ast.parse("def f(x=None):\n    dangerous()"),
+    }
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in trees.items()
+    }
+    first = evaluate_package_import_order(trees, "pkg")
+    second = evaluate_package_import_order(trees, "pkg")
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+    assert before == {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in trees.items()
+    }
+    json.dumps(asdict(first))
~~~
