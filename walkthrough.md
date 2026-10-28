# CONTEXTOR P1D3-D1 — constant branches and import-time class bodies

## 1. EXECUTIVE RESULT
**GO for the restricted P1D3-D1 contract.** DIRECT_EVIDENCE: required focused suite passed; controlled synthetic CPython observations matched supported positive/hazard cases. Active LIVE loaded-code adoption remains UNKNOWN.

## 2. INITIAL AND FINAL HEAD/WORKTREE
- Initial HEAD: `7dfa71e4adf18dd7eb392afaf07deb51550e7bc6`.
- Final HEAD: `7dfa71e4adf18dd7eb392afaf07deb51550e7bc6`.
- Initial worktree: clean (`git status --short` empty).
- Final worktree: modified `contextor/core/cycle_semantics/package_model.py`, `tests/test_cycle_semantics_package_model.py`, `tests/test_p1d3_package_cycle_integration.py`, and this report `walkthrough.md`.
- No Git history/branch mutation by this task.

## 3. EXACT PRODUCTION CHANGES
CODE_PATH_PROVED: only `package_model.py` changed. `_Step.class_local` was appended, literal bool selection was added to the existing `ast.If` compiler branch, direct class-body imports are compiled before `DEFINE_PASSIVE_CLASS`, and three import-binding paths suppress module namespace writes for class-local imports while emitting class-specific operation names. No evidence/manifest/receipt/schema/version source changed.

## 4. BOOLEAN BRANCH IMPLEMENTATION
CODE_PATH_PROVED: `ast.Constant` with `type(value) is bool` selects body or orelse. Existing exact `__name__` comparison validation remains the fallback. Recursive `_compile` and depth limit 32 remain. Unselected branch emits no execution steps. Existing whole-module `compile()` still runs before modeling and rejects compile-invalid AST even under `if False`.

## 5. CLASS-BODY EXECUTION IMPLEMENTATION
CODE_PATH_PROVED: class validation retains base/metaclass/decorator/type-parameter exclusions and passive method rules, admitting only direct `ast.Import`/`ast.ImportFrom` in addition to prior passive statements. Each direct import compiles via the existing fragment compiler, only IMPORT/FROM/PREPARE_FROM_MEMBER steps are accepted, and class name binding follows all such steps. Method bodies remain deferred.

## 6. CLASS-LOCAL VS MODULE BINDING
CODE_PATH_PROVED: `class_local=True` import steps activate imports but do not write `namespaces[module]`. Function-local behavior remains separately marked and unchanged. Added event names: `CLASS_LOCAL_IMPORT`, `CLASS_LOCAL_FROM`, `CLASS_LOCAL_FROM_REENTRANT_CHILD`. No assessment event dataclass fields changed.

## 7. HAZARD ATTRIBUTION
DIRECT_EVIDENCE: T04 initializer hazard used logical event target `pkg`, while the integrated SCC members were indexed `pkg.__init__` and `pkg.a`; T05/T07 hazards arose while the target was partially initialized. The class name was not emitted as bound before a class-body import failure. Scenario classification is based on the existing indexed SCC mapping.

## 8. T01–T15 RESULTS
- T01 DIRECT_EVIDENCE: false-branch import retained canonical lexical hard edge, but no `START_IMPORT pkg.b` for fresh `pkg.a`; model and CPython passed.
- T02 DIRECT_EVIDENCE: true-branch import produced internal early-binding hazard; synthetic CPython import failed.
- T03 DIRECT_EVIDENCE: same graph with false branch passed; evidence token differed from T02.
- T04 DIRECT_EVIDENCE: initializer active hazard and reordered safe variant had same indexed SCC; CPython differed accordingly.
- T05 DIRECT_EVIDENCE: class-body import preceded class binding and produced hazard; CPython failed.
- T06 DIRECT_EVIDENCE: value bound before class-body import passed; same graph as T05; CPython passed.
- T07 DIRECT_EVIDENCE: class-local alias did not become a module export; model hazard and CPython failure. P0 marked this particular negative scenario INCOMPLETE_EVIDENCE, and P1B UNAVAILABLE; no positive claim was inferred from it.
- T08 DIRECT_EVIDENCE: uncalled method import remained inactive for fresh `pkg.a`; lexical edge remained; CPython passed.
- T09 DIRECT_EVIDENCE: unknown name and integer `1` conditions yielded UNKNOWN and no prepared manifest.
- T10 DIRECT_EVIDENCE: bases, metaclass, decorator, call, expression assignment, nested class, conditional class import and star import yielded UNKNOWN.
- T11 DIRECT_EVIDENCE: compile-invalid AST `return` under unselected branch yielded UNKNOWN.
- T12 DIRECT_EVIDENCE: repeated representative model calls yielded equal result/events and unchanged AST dumps; active/inactive and reordered class sources yielded different evidence tokens.
- T13 DIRECT_EVIDENCE: isolated original-worker preparation and official synthetic FULL publication passed with v2 manifest/receipt; active repository untouched.
- T14 DIRECT_EVIDENCE: forged class-import event with recomputed component token passed P0 consistency then failed P1B independent replay with MODEL_REPLAY_MISMATCH; no positive manifest was minted from forged declaration.
- T15 DIRECT_EVIDENCE: required focused suite includes existing name guards, function calls/local bindings, package/reentrant imports, source reorder, unsupported constructs and resource limits; all passed.

## 9. CPYTHON DIFFERENTIAL RESULTS
DIRECT_EVIDENCE: controlled `-I -B` imports of authored temporary fixtures succeeded for T01/T03/T04-safe/T06/T08 and failed for T02/T04-hazard/T05/T07. `tests/cycle_semantics_lab` supplied the fixture writer and subprocess runner. No analyzed active-repository code was executed.

## 10. ORIGINAL-WORKER FULL TEST
DIRECT_EVIDENCE: `test_p1d3_d1_original_worker_prepares_v2` used original-worker capture on isolated `D1_CLASS_SAFE`; preparation status was `PREPARED_UNPUBLISHED_NON_ATOMIC`, closure was `pkg.__init__`, `pkg.a`, `pkg.b`, and component classification was all fresh entries pass. `test_p1d3_d1_official_isolated_full_receipt` exercised isolated `ContextorFacade.analyze_project` with opt-in publication.

## 11. P0/P1B REPLAY TEST
DIRECT_EVIDENCE: integrated supported cases had P0 `DECLARED_INPUTS_CONSISTENT` and P1B `BYTE_AST_CONSISTENT_NON_ATOMIC`. The class-local negative case remained incomplete/unavailable under validation. Forged D1 event with recomputed token reached P1B and returned `MODEL_REPLAY_MISMATCH`.

## 12. MANIFEST/RECEIPT RESULTS
DIRECT_EVIDENCE: positive D1 original-worker manifest retained `cycle-source-manifest/2`; isolated official FULL receipt retained `cycle-prepared-co-publication/2` and passed `verify_co_published_cycle_manifest`. These are isolated synthetic publication facts, not active LIVE adoption.

## 13. EXISTING REGRESSION RESULTS
DIRECT_EVIDENCE: existing tests in the seven specified focused files passed unchanged. The R1 test additions committed before this task were not edited.

## 14. COMMANDS, EXIT CODES, DURATION
- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/package_model.py` → exit 0, 0.88 s.
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py` → 226 passed in 46.20 s, exit 0.
- After adding the extra direct reentrant-child class-scope regression: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_package_model.py::test_p1d3_d1_class_local_reentrant_child_from` → 1 passed in 1.22 s, exit 0. The previously passing tests were not rerun unnecessarily.
- `git diff --check` → exit 0, with only an LF/CRLF normalization warning.
- During test construction, an initial class-import assertion expected a success event after a child had already raised a hazard. The assertion was corrected to check `START_IMPORT`; production was unchanged for that correction. Another initial integration assertion used the nonexistent P1B field `evidence_state`; corrected to documented `bytes_state`. No final test failures remain.

## 15. FILES_CHANGED
- `contextor/core/cycle_semantics/package_model.py` (production)
- `tests/test_cycle_semantics_package_model.py` (tests)
- `tests/test_p1d3_package_cycle_integration.py` (tests)
- `walkthrough.md` (this report; excluded from source/test diff)

## 17. UNSUPPORTED SEMANTICS
CONTRACT_PROVED: nonliteral conditions, integer truthiness, unsupported class effects, class-body dynamic evaluation, nested class semantics, and arbitrary analyzed code execution remain outside D1. INFERENCE: these exclusions preserve the intended restricted model boundary. UNKNOWN: arbitrary Python runtime safety and active service loaded-code adoption.

## 18. BLOCKERS / CONTRACT CONFLICTS
None for the restricted D1 implementation. The class-local alias hazard is model evidence, while P0/P1B do not issue a positive verified claim for that negative scenario; recorded as a validation limitation rather than promoted to a pass.

## 19. FINAL GO / PARTIAL / NO_GO
GO for the specified source/test implementation and isolated verification. Stop after P1D3-D1; await another explicit `proceduj`.

## 16. ACTUAL_DIFF / FULL_DIFF
Complete raw diff of every task-changed production/test file against initial HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index c12f47b..aede764 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -40,6 +40,7 @@ class _Step:
     explicit_alias: bool = False
     function_body: tuple[_Step, ...] = ()
     function_local: bool = False
+    class_local: bool = False
 
 
 def _safe_passive_function_definition(
@@ -124,11 +125,11 @@ def _safe_passive_class_definition(
     """Validate a class whose body has no unknown effects.
 
     Class body evaluation is not generally passive.
-    Only a literal docstring, Pass and safe method
-    definitions are modeled here.
+    Only a literal docstring, Pass, safe method
+    definitions and restricted imports are modeled.
 
-    The model records class-name binding only.
-    It does not execute class or method code.
+    Direct class-body imports execute before class-name
+    binding. Method bodies remain deferred.
     """
     if (
         not statement.name.isidentifier()
@@ -146,6 +147,9 @@ def _safe_passive_class_definition(
         if isinstance(body_statement, ast.Pass):
             continue
 
+        if isinstance(body_statement, (ast.Import, ast.ImportFrom)):
+            continue
+
         if (
             index == 0
             and isinstance(body_statement, ast.Expr)
@@ -293,32 +297,42 @@ def _compile(
             condition = stmt.test
 
             if (
-                not isinstance(condition, ast.Compare)
-                or not isinstance(condition.left, ast.Name)
-                or condition.left.id != "__name__"
-                or len(condition.ops) != 1
-                or not isinstance(
-                    condition.ops[0],
-                    (ast.Eq, ast.NotEq),
-                )
-                or len(condition.comparators) != 1
-                or not isinstance(
-                    condition.comparators[0],
-                    ast.Constant,
-                )
-                or type(
-                    condition.comparators[0].value
-                ) is not str
-                or condition.comparators[0].value
-                != "__main__"
+                isinstance(condition, ast.Constant)
+                and type(condition.value) is bool
             ):
-                return None
+                selected = (
+                    stmt.body
+                    if condition.value
+                    else stmt.orelse
+                )
+            else:
+                if (
+                    not isinstance(condition, ast.Compare)
+                    or not isinstance(condition.left, ast.Name)
+                    or condition.left.id != "__name__"
+                    or len(condition.ops) != 1
+                    or not isinstance(
+                        condition.ops[0],
+                        (ast.Eq, ast.NotEq),
+                    )
+                    or len(condition.comparators) != 1
+                    or not isinstance(
+                        condition.comparators[0],
+                        ast.Constant,
+                    )
+                    or type(
+                        condition.comparators[0].value
+                    ) is not str
+                    or condition.comparators[0].value
+                    != "__main__"
+                ):
+                    return None
 
-            selected = (
-                stmt.orelse
-                if isinstance(condition.ops[0], ast.Eq)
-                else stmt.body
-            )
+                selected = (
+                    stmt.orelse
+                    if isinstance(condition.ops[0], ast.Eq)
+                    else stmt.body
+                )
 
             selected_steps = _compile(
                 ast.Module(
@@ -382,6 +396,41 @@ def _compile(
             if not _safe_passive_class_definition(stmt):
                 return None
 
+            for body_statement in stmt.body:
+                if not isinstance(
+                    body_statement,
+                    (ast.Import, ast.ImportFrom),
+                ):
+                    continue
+
+                fragment = ast.Module(
+                    body=[body_statement],
+                    type_ignores=[],
+                )
+                compiled = _compile(
+                    fragment,
+                    logical,
+                    package,
+                    _depth=_depth + 1,
+                )
+                if (
+                    compiled is None
+                    or any(
+                        item.op not in {
+                            "IMPORT",
+                            "FROM",
+                            "PREPARE_FROM_MEMBER",
+                        }
+                        for item in compiled
+                    )
+                ):
+                    return None
+
+                steps.extend(
+                    replace(item, class_local=True)
+                    for item in compiled
+                )
+
             steps.append(
                 _Step(
                     "DEFINE_PASSIVE_CLASS",
@@ -820,7 +869,7 @@ def evaluate_package_import_order(
                         else target.split(".")[0]
                     )
 
-                    if not step.function_local:
+                    if not step.function_local and not step.class_local:
                         namespaces[module][step.binding] = binding_target
 
                     events.append(
@@ -829,6 +878,8 @@ def evaluate_package_import_order(
                             (
                                 "FUNCTION_LOCAL_IMPORT"
                                 if step.function_local
+                                else "CLASS_LOCAL_IMPORT"
+                                if step.class_local
                                 else "IMPORT"
                             ),
                             target,
@@ -856,7 +907,7 @@ def evaluate_package_import_order(
                             ):
                                 return result("UNKNOWN", child, member)
 
-                            if not step.function_local:
+                            if not step.function_local and not step.class_local:
                                 namespaces[module][step.binding] = child
 
                             events.append(
@@ -865,6 +916,8 @@ def evaluate_package_import_order(
                                     (
                                         "FUNCTION_LOCAL_FROM_REENTRANT_CHILD"
                                         if step.function_local
+                                        else "CLASS_LOCAL_FROM_REENTRANT_CHILD"
+                                        if step.class_local
                                         else "FROM_REENTRANT_CHILD"
                                     ),
                                     child,
@@ -914,7 +967,7 @@ def evaluate_package_import_order(
 
                     return result(outcome, target, member)
 
-                if not step.function_local:
+                if not step.function_local and not step.class_local:
                     namespaces[module][step.binding] = namespaces[target][member]
 
                 events.append(
@@ -923,6 +976,8 @@ def evaluate_package_import_order(
                         (
                             "FUNCTION_LOCAL_FROM"
                             if step.function_local
+                            else "CLASS_LOCAL_FROM"
+                            if step.class_local
                             else "FROM"
                         ),
                         target,
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index f5494e8..c5d2fa6 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -4,6 +4,8 @@ import subprocess
 import sys
 from dataclasses import asdict
 
+import pytest
+
 from contextor.core.cycle_semantics.package_model import (
     evaluate_package_import_order,
 )
@@ -1004,3 +1006,154 @@ def test_b0g4c5_deterministic_ast_unchanged():
     } == before
 
     json.dumps(asdict(first))
+
+
+@pytest.mark.parametrize(
+    "condition,expected,active",
+    [
+        ("False", "MODEL_PASS", False),
+        ("True", "EARLY_BINDING_HAZARD", True),
+    ],
+)
+def test_p1d3_d1_literal_branch_activation(tmp_path, condition, expected, active):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": f"if {condition}:\n    import pkg.b\nvalue = 1",
+        "pkg.b": "from pkg.a import value",
+    }
+    result = _model(source, "pkg.a")
+    assert result.outcome == expected
+    assert any(
+        event.operation == "START_IMPORT" and event.target == "pkg.b"
+        for event in result.events
+    ) is active
+    assert _actual(tmp_path, source, "pkg.a") is (not active)
+
+
+def test_p1d3_d1_false_else_and_name_guard(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "if False:\n    pass\nelse:\n    import pkg.b\n"
+            "if __name__ == '__main__':\n    import pkg.missing\n"
+            "value = 1"
+        ),
+        "pkg.b": "pass",
+    }
+    result = _model(source, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
+    assert _actual(tmp_path, source, "pkg.a")
+
+
+@pytest.mark.parametrize(
+    "body,expected,operation",
+    [
+        ("class Loader:\n    import pkg.b\nvalue = 1", "EARLY_BINDING_HAZARD", "CLASS_LOCAL_IMPORT"),
+        ("value = 1\nclass Loader:\n    import pkg.b", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
+        ("class Loader:\n    from pkg.b import value", "MODEL_PASS", "CLASS_LOCAL_FROM"),
+        ("class Loader:\n    import pkg.b as local_child", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
+    ],
+)
+def test_p1d3_d1_class_import_timing(tmp_path, body, expected, operation):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": body,
+        "pkg.b": "from pkg.a import value" if "value = 1" in body else "value = 2",
+    }
+    result = _model(source, "pkg.a")
+    assert result.outcome == expected
+    if expected == "MODEL_PASS":
+        assert any(e.operation == operation for e in result.events)
+    else:
+        assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
+    assert _actual(tmp_path, source, "pkg.a") is (expected == "MODEL_PASS")
+
+
+def test_p1d3_d1_class_local_binding_does_not_escape(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class Loader:\n    import pkg.b as local_child",
+        "pkg.b": "from pkg.a import local_child",
+    }
+    result = _model(source, "pkg.a")
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg.a"
+    assert result.symbol == "local_child"
+    assert not any(e.operation == "DEFINE_PASSIVE_CLASS" for e in result.events)
+    assert not _actual(tmp_path, source, "pkg.a")
+
+
+def test_p1d3_d1_class_local_reentrant_child_from(tmp_path):
+    source = {
+        "pkg.__init__": "from . import child",
+        "pkg.child": "class Loader:\n    from pkg import child",
+    }
+    result = _model(source, "pkg")
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "CLASS_LOCAL_FROM_REENTRANT_CHILD"
+        and event.target == "pkg.child"
+        for event in result.events
+    )
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_p1d3_d1_uncalled_method_import_is_deferred(tmp_path):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class Loader:\n    def load(self):\n        import pkg.b\nvalue = 1",
+        "pkg.b": "from pkg.a import value",
+    }
+    result = _model(source, "pkg.a")
+    assert result.outcome == "MODEL_PASS"
+    assert not any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
+    assert _actual(tmp_path, source, "pkg.a")
+
+
+@pytest.mark.parametrize("condition", ["unknown_condition", "1"])
+def test_p1d3_d1_unsupported_condition(condition):
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": f"if {condition}:\n    import pkg.b",
+        "pkg.b": "pass",
+    }
+    assert _model(source, "pkg.a").outcome == "UNKNOWN"
+
+
+@pytest.mark.parametrize("body", [
+    "class Loader(Base):\n    import pkg.b",
+    "class Loader(metaclass=Meta):\n    import pkg.b",
+    "@decorator\nclass Loader:\n    import pkg.b",
+    "class Loader:\n    helper()",
+    "class Loader:\n    x = helper()",
+    "class Loader:\n    class Nested:\n        pass",
+    "class Loader:\n    if True:\n        import pkg.b",
+    "class Loader:\n    from pkg.b import *",
+])
+def test_p1d3_d1_unsupported_class_effects(body):
+    source = {"pkg.__init__": "pass", "pkg.a": body, "pkg.b": "pass"}
+    assert _model(source, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_p1d3_d1_invalid_unselected_branch_fails_compile():
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "if False:\n    return 1\nelse:\n    pass",
+    }
+    assert _model(source, "pkg.a").outcome == "UNKNOWN"
+
+
+def test_p1d3_d1_deterministic_events_and_ast_unchanged():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse("if True:\n    class Loader:\n        import pkg.b"),
+        "pkg.b": ast.parse("from pkg.a import Loader"),
+    }
+    before = {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()}
+    first = evaluate_package_import_order(sources, "pkg.a")
+    second = evaluate_package_import_order(sources, "pkg.a")
+    assert first == second
+    assert first.events == second.events
+    assert first.outcome == "EARLY_BINDING_HAZARD"
+    assert {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()} == before
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 2330638..151845b 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -59,6 +59,42 @@ F4 = {
     "pkg/a.py": "value = 1\nimport pkg.b\n",
 }
 
+D1_FALSE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "if False:\n    import pkg.b\nvalue = 1\n",
+    "pkg/b.py": "import pkg.a\n",
+}
+D1_TRUE_HAZARD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "if True:\n    import pkg.b\nvalue = 1\n",
+    "pkg/b.py": "from pkg.a import value\n",
+}
+D1_FALSE_SAFE = {**D1_TRUE_HAZARD, "pkg/a.py": "if False:\n    import pkg.b\nvalue = 1\n"}
+D1_CLASS_HAZARD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "class Loader:\n    import pkg.b\nvalue = 1\n",
+    "pkg/b.py": "from pkg.a import value\n",
+}
+D1_CLASS_SAFE = {**D1_CLASS_HAZARD, "pkg/a.py": "value = 1\nclass Loader:\n    import pkg.b\n"}
+D1_CLASS_LOCAL = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "class Loader:\n    import pkg.b as local_child\n",
+    "pkg/b.py": "from pkg.a import local_child\n",
+}
+D1_METHOD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "class Loader:\n    def load(self):\n        import pkg.b\nvalue = 1\n",
+    "pkg/b.py": "from pkg.a import value\n",
+}
+D1_INITIALIZER_HAZARD = {
+    "pkg/__init__.py": "if True:\n    import pkg.a\nvalue = 1\n",
+    "pkg/a.py": "import pkg\nx = pkg.value\n",
+}
+D1_INITIALIZER_SAFE = {
+    **D1_INITIALIZER_HAZARD,
+    "pkg/__init__.py": "value = 1\nif True:\n    import pkg.a\n",
+}
+
 
 @pytest.fixture(autouse=True)
 def _inline(monkeypatch):
@@ -518,3 +554,223 @@ def test_official_isolated_package_publication(tmp_path, isolated_dirs, monkeypa
             state_id=metadata.state_id, repo_id=metadata.repo_id,
             root_path=metadata.root_path,
         )
+
+
+@pytest.mark.parametrize("fixture,classification,entry,success", [
+    (D1_FALSE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
+    (D1_TRUE_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
+    (D1_FALSE_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
+    (D1_CLASS_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
+    (D1_CLASS_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
+    (D1_CLASS_LOCAL, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg.a", False),
+    (D1_METHOD, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg.a", True),
+    (D1_INITIALIZER_HAZARD, "MODEL_INTERNAL_EARLY_BINDING_HAZARD", "pkg", False),
+    (D1_INITIALIZER_SAFE, "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "pkg", True),
+])
+def test_p1d3_d1_integrated_model_and_cpython(
+    tmp_path, isolated_dirs, fixture, classification, entry, success,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    parsed = {
+        name: parse_source_snapshot(snapshot, name)
+        for name, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    scenario = evidence.scenarios.components[0]
+    assert scenario.model_kind == "REGULAR_PACKAGE"
+    assert scenario.classification == classification
+    assert scenario.evidence_scope == "CLOSED_REGULAR_PACKAGE_FRESH_ENTRY_MODEL"
+    assert all(
+        item.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+        for item in scenario.entry_assessments
+    )
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        _snapshot(root, index, graph), evidence,
+    )
+    if fixture is D1_CLASS_LOCAL:
+        assert p0[0].evidence_state == "INCOMPLETE_EVIDENCE"
+    else:
+        assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        _snapshot(root, index, graph), evidence,
+        captured.original_worker_source_snapshots,
+    )
+    if fixture is D1_CLASS_LOCAL:
+        assert p1b[0].bytes_state == "UNAVAILABLE"
+    else:
+        assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    assert (run_synthetic_import(root, entry).returncode == 0) is success
+    if fixture is D1_FALSE:
+        assert "pkg.b" in graph.hard_edges["pkg.a"]
+        assert not any(
+            event.operation == "START_IMPORT" and event.target == "pkg.b"
+            for assessment in scenario.entry_assessments
+            if assessment.entry_module == "pkg.a"
+            for event in assessment.events
+        )
+    if fixture is D1_METHOD:
+        assert "pkg.b" in graph.hard_edges["pkg.a"]
+        assert not any(
+            event.operation == "START_IMPORT" and event.target == "pkg.b"
+            for assessment in scenario.entry_assessments
+            if assessment.entry_module == "pkg.a"
+            for event in assessment.events
+        )
+    if fixture is D1_CLASS_LOCAL:
+        assert any(
+            event.operation == "EARLY_BINDING_HAZARD"
+            and event.target == "pkg.a"
+            and event.symbol == "local_child"
+            for assessment in scenario.entry_assessments
+            for event in assessment.events
+        )
+    if fixture is D1_INITIALIZER_HAZARD:
+        assert set(scenario.members) == {"pkg.__init__", "pkg.a"}
+        assert any(
+            event.operation == "EARLY_BINDING_HAZARD"
+            and event.target == "pkg"
+            and event.symbol == "value"
+            for assessment in scenario.entry_assessments
+            for event in assessment.events
+        )
+
+
+def test_p1d3_d1_same_graph_changes_model_evidence(tmp_path, isolated_dirs):
+    values = []
+    for name, fixture in (("active", D1_TRUE_HAZARD), ("inactive", D1_FALSE_SAFE),
+                          ("class_early", D1_CLASS_HAZARD), ("class_late", D1_CLASS_SAFE)):
+        root = write_synthetic_repository(tmp_path / name, fixture)
+        index, graph = _indexed(root)
+        _, captured = _captured(root, index, graph)
+        parsed = {
+            module: parse_source_snapshot(snapshot, module)
+            for module, snapshot in captured.original_worker_source_snapshots.items()
+        }
+        evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+        values.append((graph.hard_edges, evidence.components[0].evidence_token))
+    assert values[0][0] == values[1][0]
+    assert values[2][0] == values[3][0]
+    assert values[0][1] != values[1][1]
+    assert values[2][1] != values[3][1]
+
+
+def test_p1d3_d1_original_worker_prepares_v2(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, _snapshot(root, index, graph),
+    )
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert prepared.source_modules == ("pkg.__init__", "pkg.a", "pkg.b")
+    assert prepared.manifest.version == MANIFEST_VERSION
+    assert prepared.manifest.components[0].model_kind == "REGULAR_PACKAGE"
+    assert prepared.manifest.components[0].model_classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+
+
+@pytest.mark.parametrize("condition", ["unknown_condition", "1"])
+def test_p1d3_d1_unsupported_condition_no_manifest(
+    tmp_path, isolated_dirs, condition,
+):
+    fixture = {**D1_TRUE_HAZARD,
+               "pkg/a.py": f"if {condition}:\n    import pkg.b\nvalue = 1\n"}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, _snapshot(root, index, graph),
+    )
+    assert prepared.status == "UNAVAILABLE"
+    assert prepared.manifest is None
+
+
+def test_p1d3_d1_forged_class_event_fails_replay(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    sources = captured.original_worker_source_snapshots
+    parsed = {name: parse_source_snapshot(snapshot, name) for name, snapshot in sources.items()}
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    scenario = evidence.scenarios.components[0]
+    assessment = next(
+        item for item in scenario.entry_assessments
+        if any(event.operation == "CLASS_LOCAL_IMPORT" for event in item.events)
+    )
+    event = next(event for event in assessment.events if event.operation == "CLASS_LOCAL_IMPORT")
+    forged_assessment = replace(
+        assessment,
+        events=tuple(
+            replace(item, operation="FORGED_CLASS_IMPORT") if item is event else item
+            for item in assessment.events
+        ),
+    )
+    forged_scenario = replace(
+        scenario,
+        entry_assessments=tuple(
+            forged_assessment if item is assessment else item
+            for item in scenario.entry_assessments
+        ),
+    )
+    component = evidence.components[0]
+    subgraph = tuple(
+        (name, tuple(sorted(graph.hard_edges[name])))
+        for name in component.reachable_modules
+    )
+    forged_component = replace(
+        component,
+        evidence_token=_component_token(
+            component.members, subgraph,
+            component.source_signatures, forged_scenario,
+        ),
+    )
+    forged = replace(
+        evidence,
+        components=(forged_component,),
+        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
+    )
+    snapshot = _snapshot(root, index, graph)
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged, sources,
+    )
+    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"
+
+
+@pytest.mark.live
+def test_p1d3_d1_official_isolated_full_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D1_CLASS_SAFE)
+    with _official_live(root, monkeypatch) as (client, server, identity, calls):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        assert result.cycle_source_preparation_preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        state, metadata = _persisted(root)
+        receipt = state.cycle_source_publication
+        assert receipt.version == PUBLICATION_BINDING_VERSION
+        assert receipt.prepared_manifest.version == MANIFEST_VERSION
+        assert receipt.prepared_manifest.components[0].model_classification == (
+            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        )
+        assert verify_co_published_cycle_manifest(
+            state, revision=metadata.revision,
+            state_id=metadata.state_id, repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+        assert result.live_publish_status == "success"
+        assert calls == [root.resolve()]
```
