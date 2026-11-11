# P5-M08-I9-I1 + R1 — completion report

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `e9169286f04bc473120402f59bf9f48567cd6830`; worktree clean at R1 start. Active interpreter `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. Contextor LIVE revision 1356, `package_model.py` workspace_sync verified, structural DFS cycles 16, cycle_semantics stale. HEAD includes I9-I1 staging in `execution/state.py`, `package_model.py`, and `tests/test_cycle_semantics_class_decorator_staging.py`. Historical P10/P11 tests were present and unchanged.

## FILES_CHANGED

R1 uncommitted source/test:
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_class_decorator_staging.py`

`walkthrough.md` is this report. Earlier I9-I1 changes are committed in HEAD `e9169286f04bc473120402f59bf9f48567cd6830`; paths: `contextor/core/cycle_semantics/execution/state.py`, `contextor/core/cycle_semantics/package_model.py`, `tests/test_cycle_semantics_class_decorator_staging.py`.

## COMPILER_ADMISSION_CORRECTION

CODE_PATH_PROVED: `_compile` now requires every ordinary named class decorator to have a preceding `DEFINE_FUNCTION` with the same binding in the same compiled module; it uses the computed names in `SNAPSHOT_CLASS_DECORATORS`. It does not accept BIND, IMPORT, FROM, ALIAS, opaque function, or forward definitions as compile proof. Runtime snapshot and restricted callable eligibility remain separate checks. This gate is intentionally conservative and is not a proof of the actual bound object after subsequent rebinding.

## EAGER_WHOLE_MODULE_CONTRACT

DIRECT_EVIDENCE: original P10 eager test passed. Unresolved decorator in unvisited `pkg.bad` causes compile-time UNKNOWN, target `pkg.bad`, events `()`. The new exact copied fixture passed as well.

## STRICT_WHOLE_MODULE_CONTRACT

DIRECT_EVIDENCE: original P11 strict test passed. `value=1` followed by `@unknown_decorator` yields UNKNOWN for `pkg.a` before events; new exact copied fixture passed.

## LAZY_REACHABLE_PREFIX_CONTRACT

DIRECT_EVIDENCE: original P10 lazy path returns MODEL_PASS without visiting `pkg.bad`. Original P11 opt-in path returns UNKNOWN after preceding BIND(value) event. These assertions passed. No `_compile_reachable_prefix` edit.

## DECORATOR_SNAPSHOT_STAGING

CODE_PATH_PROVED: prior I9-I1 source snapshots named decorator object references before PREPARE_PASSIVE_CLASS, retains definition ID and source order, and returns UNKNOWN at DEFINE_DECORATED_PASSIVE_CLASS. R1 changes only the compiler proof gate. New tests cover preceding, unresolved, stacked-unbound, forward and same-name cases; seven I9-T1 UNKNOWN cases remain passing.

## CONDITIONAL_DATACLASS_PRESERVATION

DIRECT_EVIDENCE: exact qualified frozen dataclass staging fixture and related targeted regressions passed. No conditional dataclass code edited by R1. Its assumption-bearing MODEL_PASS is separate from ordinary decorated-class admission.

## CLASS_METACLASS_AND_MRO_PRESERVATION

No R1 edits to _ClassFact, PREPARE_PASSIVE_CLASS, DEFINE_PASSIVE_CLASS, metaclass selection, C3 merge or class-body compilation. Focused passive-class regressions passed.

## NEGATIVE_BOUNDARIES

DIRECT_EVIDENCE: unresolved names, one unresolved decorator in a stack and forward references fail whole-module compile; attribute/call decorators and ordinary decorated class execution remain UNKNOWN. Same-name preceding local function stages, but model remains UNKNOWN. Existing package child-name guards unchanged.

## TARGETED_TEST_RESULTS

First P10/P11 gate: `2 passed, 205 deselected in 1.23s`.

Full specified I9-I1 targeted subset: `365 passed, 2 warnings in 44.30s`. Warnings are external authlib/fastmcp deprecations. No full suite or SCC02. `git diff --check`: exit 0, with LF/CRLF notice for the test file.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor canonical revision 1358. Changed `package_model.py` and staging test: workspace_sync verified, syntax errors 0, module/graph/topology/cycles fresh; cycle_semantics stale. Structural DFS cycle count 16. Production owner has 12 outbound dependencies, unchanged from preflight; staging test has three hard outbound dependencies to execution.calls, execution.class_facts and package_model. `execution.state` has two outbound dependencies. No new production import edge, FULL, update_file or restart. Fresh source does not attest loaded backend code.

## FULL_DIFFS

All current uncommitted source/test diffs:

```diff
warning: in the working copy of 'tests/test_cycle_semantics_class_decorator_staging.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 68261cb..82116cb 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -849,6 +849,22 @@ def _compile(
                 and not conditional_dataclass
             )
 
+            if ordinary_named_decorators:
+                decorator_names = tuple(
+                    decorator.id
+                    for decorator in stmt.decorator_list
+                )
+
+                if any(
+                    not any(
+                        earlier.op == "DEFINE_FUNCTION"
+                        and earlier.binding == decorator_name
+                        for earlier in steps
+                    )
+                    for decorator_name in decorator_names
+                ):
+                    return None
+
             if not conditional_dataclass:
                 if (
                     type(stmt.lineno) is not int
@@ -867,10 +883,7 @@ def _compile(
                             "SNAPSHOT_CLASS_DECORATORS",
                             binding=stmt.name,
                             definition_id=definition_id,
-                            decorator_names=tuple(
-                                decorator.id
-                                for decorator in stmt.decorator_list
-                            ),
+                            decorator_names=decorator_names,
                         )
                     )
                 steps.append(
diff --git a/tests/test_cycle_semantics_class_decorator_staging.py b/tests/test_cycle_semantics_class_decorator_staging.py
index 7031c3f..f393741 100644
--- a/tests/test_cycle_semantics_class_decorator_staging.py
+++ b/tests/test_cycle_semantics_class_decorator_staging.py
@@ -54,10 +54,22 @@ def test_decorated_class_body_import_staging():
 
 
 def test_multiple_named_class_decorators_keep_source_order():
-    steps = _steps("@top\n@bottom\nclass C:\n    pass\n")
+    steps = _steps(
+        "def top(cls):\n"
+        "    return cls\n"
+        "def bottom(cls):\n"
+        "    return cls\n"
+        "@top\n"
+        "@bottom\n"
+        "class C:\n"
+        "    pass\n"
+    )
     assert steps is not None
-    assert steps[0].op == "SNAPSHOT_CLASS_DECORATORS"
-    assert steps[0].decorator_names == ("top", "bottom")
+    snapshot = next(
+        step for step in steps
+        if step.op == "SNAPSHOT_CLASS_DECORATORS"
+    )
+    assert snapshot.decorator_names == ("top", "bottom")
 
 
 def test_same_name_decorator_stages_but_remains_unknown():
@@ -143,3 +155,114 @@ def test_snapshot_preserves_class_fact_reference_without_execution():
     assert snapshot is not None
     assert snapshot.values[0] is class_fact
     assert namespace == before
+
+
+def test_unresolved_decorator_rejects_whole_module_compile():
+    assert _steps(
+        "value = 1\n@unknown_decorator\nclass Bad:\n    pass\n"
+    ) is None
+
+
+def test_preceding_local_restricted_decorator_stages_in_order():
+    steps = _steps(
+        "def identity(cls):\n    return cls\n"
+        "@identity\nclass C:\n    pass\n"
+    )
+    assert steps is not None
+    assert tuple(step.op for step in steps) == (
+        "DEFINE_FUNCTION",
+        "SNAPSHOT_CLASS_DECORATORS",
+        "PREPARE_PASSIVE_CLASS",
+        "DEFINE_DECORATED_PASSIVE_CLASS",
+    )
+    assert steps[0].binding == "identity"
+
+
+def test_unbound_decorator_in_stack_rejects_compile():
+    assert _steps(
+        "def known(cls):\n    return cls\n"
+        "@unknown\n@known\nclass C:\n    pass\n"
+    ) is None
+
+
+def test_forward_decorator_reference_rejects_compile():
+    assert _steps(
+        "@later\nclass C:\n    pass\n"
+        "def later(cls):\n    return cls\n"
+    ) is None
+
+
+def test_same_name_local_decorator_proof_gate():
+    source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
+    steps = _steps(source)
+    assert steps is not None
+    snapshot = next(
+        step for step in steps
+        if step.op == "SNAPSHOT_CLASS_DECORATORS"
+    )
+    assert snapshot.decorator_names == ("C",)
+    assert evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)}, "pkg",
+    ).outcome == "UNKNOWN"
+
+
+def test_exact_p10_eager_and_lazy_fixture():
+    source = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse(
+            "def later():\n"
+            "    import pkg.bad\n"
+            "value = 1\n"
+        ),
+        "pkg.bad": ast.parse(
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+    eager = evaluate_package_import_order(
+        source, "pkg.a", annotation_semantics="DEFERRED",
+    )
+    lazy = evaluate_package_import_order(
+        source, "pkg.a", annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+    assert eager.outcome == "UNKNOWN"
+    assert eager.target_module == "pkg.bad"
+    assert eager.events == ()
+    assert lazy.outcome == "MODEL_PASS"
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.bad"
+        for event in lazy.events
+    )
+
+
+def test_exact_p11_strict_and_opt_in_fixture():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse(
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+    strict = evaluate_package_import_order(
+        sources, "pkg.a", annotation_semantics="DEFERRED",
+    )
+    opt_in = evaluate_package_import_order(
+        sources, "pkg.a", annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+    assert strict.outcome == "UNKNOWN"
+    assert strict.target_module == "pkg.a"
+    assert strict.events == ()
+    assert opt_in.outcome == "UNKNOWN"
+    assert opt_in.target_module == "pkg.a"
+    assert any(
+        event.operation == "BIND"
+        and event.module == "pkg.a"
+        and event.symbol == "value"
+        for event in opt_in.events
+    )
```

Earlier I9-I1 source/test changes are in HEAD `e9169286f04bc473120402f59bf9f48567cd6830`; no uncommitted diff exists for those earlier changes.

## FINAL_VERDICT

FINAL PASS for I9-I1 + R1 scoped compiler staging and focused regressions. Decorated-class execution remains UNKNOWN; no loaded-backend adoption or general Python parity is claimed.
