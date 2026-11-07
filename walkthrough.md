# CONTEXTOR C16-B03-P1D3G17 — EXACT ASYNC DEFINITION AND MODULE NAME ALIAS PATCH

## IMPLEMENTATION

FILES_CHANGED: `contextor/core/cycle_semantics/package_model.py`; `tests/test_cycle_semantics_package_model_async_alias.py` (new). HEAD at preflight: `54f8d505088a14c52c6d350a194b048f73511b2f`. Contextor MCP first confirmed current G14/G15 code and verified source at canonical revision 1078. Applied the exact requested changes: shared passive guard for FunctionDef/AsyncFunctionDef, passive async class method, opaque module async definition, module-only Name ALIAS compilation/execution, and ALIAS in package-child shadowing guard. No other production file was edited. The supplied new test content was added without changing expectations.

## ASYNC_DEFINITION_CONTRACT

`async def` now emits `DEFINE_OPAQUE_FUNCTION`; its body is not compiled into function_body or executed. Existing invocation of an opaque function remains UNKNOWN. Decorators, nonliteral defaults, annotation-mode restrictions and type parameters retain the existing guard. Passive async class methods use the same guard. The new test `test_async_body_is_not_executed` reaches MODEL_PASS, but its assertion forbids every `START_IMPORT`, including the ordinary imports of `pkg` and `pkg.child` performed to load the entry module. Actual operations: `START_IMPORT, READY, START_IMPORT, DEFINE_OPAQUE_FUNCTION, READY, BIND_CHILD`; there is no import of `missing_external_xyz` from the deferred async body. The exact assertion conflicts with the existing IMPORT event contract.

## NAME_ALIAS_CONTRACT

ALIAS is compiled only for a module Assign with an ast.Name value, after pure literal handling and before ATTR. Execution checks membership in the current module namespace, so an existing binding whose represented value is None is accepted; a missing source remains UNKNOWN. ALIAS copies the represented identity without invoking a function or reading real objects. No class-local or AnnAssign alias was added.

## PACKAGE_CHILD_SHADOWING

The existing writes_child guard now includes `ALIAS` alongside `BIND`, retaining the subsequent import-presence condition unchanged. The supplied `test_package_child_alias_shadowing_unknown` passes. No package-child shadowing safety rule was weakened.

## TARGETED_TESTS

CPython 3.15.2, `PYTHONDONTWRITEBYTECODE=1`, `-B -m pytest -q -rs -p no:cacheprovider`, external `--basetemp C:\Temp\Contextor_G17_pytest_tmp`. Exactly the five requested modules were run: async_alias, literals, annotations315, package_model, optional_child_scenarios. Result: **217 passed, 2 failed in 31.46s**. No full suite. The two failures are contract conflicts under the mandated literal implementation and unchanged test expectations:

1. `tests/test_cycle_semantics_package_model_async_alias.py:46`, `test_async_body_is_not_executed`: requires `START_IMPORT` absent from all events, while loading the entry package/module necessarily emits `START_IMPORT` twice. The async body import was not executed.
2. `tests/test_cycle_semantics_package_model.py:1216`, `test_b0g4c5_definition_effects_updated_contract`: its legacy sample `async def f():\n    import pkg.child` expects `UNKNOWN`. The mandated G17 passive async definition correctly yields `MODEL_PASS` without executing the body. The old expectation directly contradicts G17 section 3.

Per the task's conflict rule, neither test expectation nor production behavior was independently redesigned or changed after these failures.

## NEGATIVE_REGRESSIONS

Other supplied negative cases passed: decorators, eager default effects, unknown target annotation mode, unbound/builtin/dunder alias sources, aliased invocation, early-binding hazard, child shadowing, external import and namespace layout. The two failures above prevent a PASS despite these passing cases.

## ALL_PRODUCTION_COVERAGE

Read-only G17 `_compile` census at canonical revision 1080, state_id `20261106_195021`, with explicit `annotation_semantics="DEFERRED"`. Actual production inventory: 307 files (`contextor/**/*.py` plus `main.py`). All 307 current source byte SHA-256 values matched the referenced FileState; 0 unbound or unavailable. G16-R1 baseline **147/307** supported; G17 **154 supported / 153 unsupported**, net +7. First rejected statement types: ClassDef 86, Assign 56, AnnAssign 3, If 1, FunctionDef 3, AsyncFunctionDef 1, Expr 3. Seven production modules contain top-level AsyncFunctionDef; seven contain top-level Assign(Name). Three newly supported modules with async definitions are `contextor.mcp.tools.analyze_layer`, `contextor.mcp.tools.analyze_project`, `contextor.mcp.tools.analyze_single_file`. Four newly supported Name-alias-containing modules are `contextor.core.analysis.export_analysis`, `contextor.core.api.public_api`, `contextor.core.graph.cycles`, `contextor.core.reference.__init__`. These named contributors were observed as supported under G17; the +7 total aligns with 3+4. This is compiler coverage only, not a project MODEL_PASS.

## SCC1_COVERAGE

Closure 201 modules, all FileState-bound. G16-R1 baseline 90/201; G17 **94 supported / 107 unsupported**, net +4. First rejection ClassDef 69, Assign 33, AnnAssign 2, If 1, FunctionDef 2. No supported SCC1 module had a top-level async definition in this diagnostic; four supported modules had Name aliases.

## SCC2_COVERAGE

Closure 221 modules, all FileState-bound. G16-R1 baseline 103/221; G17 **107 supported / 114 unsupported**, net +4. First rejection ClassDef 72, Assign 37, AnnAssign 2, If 1, FunctionDef 2. This closure equals the SCC union by module identity; four supported modules had Name aliases.

## OUTSIDE_SCC_COVERAGE

Outside both closures: 86 modules, all FileState-bound. G16-R1 baseline 44/86; G17 **47 supported / 39 unsupported**, net +3. First rejection Assign 19, ClassDef 14, AnnAssign 1, AsyncFunctionDef 1, FunctionDef 1, Expr 3. The three supported async-definition modules noted above are outside the closures.

## REMAINING_BLOCKERS

Both real SCCs still encounter namespace/external execution uncertainty and other AST limits; this read-only census did not call production FULL, bypass layout/graph gates, or create a receipt. Snapshot at revision 1080 had no optional /3 receipt. The two targeted regression conflicts above are the exact blocker. No test was modified to force PASS.

## MCP_POST_CHANGE_AUDIT

Read-only Contextor MCP for production and new test modules at canonical revision 1080: `canonical_state=fresh`, `workspace_sync=verified`, advisory_warning null, syntax errors 0, structural DFS cycles 16 (fresh), active_warning_count 16, model_pass_count 0, `cycle_semantics=stale`. No production FULL, restart, update_file, warning suppression edit or manual commit.

## FULL_DIFFS

Complete actual source and new-test diffs follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 33b9cab..eb7b592 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -61,7 +61,7 @@ class _PackageSourceSession:
 
 
 def _safe_passive_function_definition(
-    statement: ast.FunctionDef,
+    statement: ast.FunctionDef | ast.AsyncFunctionDef,
     *,
     allow_dunder: bool = False,
     annotation_semantics: str | None = None,
@@ -204,7 +204,10 @@ def _safe_passive_class_definition(
             continue
 
         if (
-            isinstance(body_statement, ast.FunctionDef)
+            isinstance(
+                body_statement,
+                (ast.FunctionDef, ast.AsyncFunctionDef),
+            )
             and _safe_passive_function_definition(
                 body_statement,
                 allow_dunder=True,
@@ -580,6 +583,21 @@ def _compile(
             if _pure_literal_expression(value):
                 steps.append(_Step("BIND", binding=name))
 
+            elif isinstance(value, ast.Name):
+                if (
+                    not value.id.isidentifier()
+                    or value.id.startswith("__")
+                ):
+                    return None
+
+                steps.append(
+                    _Step(
+                        "ALIAS",
+                        target=value.id,
+                        binding=name,
+                    )
+                )
+
             elif (
                 isinstance(value, ast.Attribute)
                 and isinstance(value.value, ast.Name)
@@ -746,6 +764,20 @@ def _compile(
                     )
                 )
 
+        elif isinstance(stmt, ast.AsyncFunctionDef):
+            if not _safe_passive_function_definition(
+                stmt,
+                annotation_semantics=annotation_semantics,
+            ):
+                return None
+
+            steps.append(
+                _Step(
+                    "DEFINE_OPAQUE_FUNCTION",
+                    binding=stmt.name,
+                )
+            )
+
         elif isinstance(stmt, ast.Expr):
             expression = stmt.value
 
@@ -1018,7 +1050,7 @@ def evaluate_package_import_order(
         writes_child = any(
             step.binding in children
             and (
-                step.op == "BIND"
+                step.op in {"BIND", "ALIAS"}
                 or (step.op == "FROM" and step.target != package)
             )
             for step in programs[package]
@@ -1428,6 +1460,31 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "ALIAS":
+            if (
+                not step.target
+                or not step.binding
+                or step.target not in namespaces[module]
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
+            namespaces[module][step.binding] = (
+                namespaces[module][step.target]
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "ALIAS",
+                    target=step.target,
+                    symbol=step.binding,
+                )
+            )
+
         elif step.op == "ATTR":
             reference = namespaces[module].get(step.target)
 
diff --git a/tests/test_cycle_semantics_package_model_async_alias.py b/tests/test_cycle_semantics_package_model_async_alias.py
new file mode 100644
index 0000000..5d0dbcf
--- /dev/null
+++ b/tests/test_cycle_semantics_package_model_async_alias.py
@@ -0,0 +1,299 @@
+import ast
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _model(
+    child: str,
+    *,
+    initializer: str = "pass",
+    entry: str = "pkg.child",
+    annotation_semantics=None,
+):
+    return evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(initializer),
+            "pkg.child": ast.parse(child),
+        },
+        entry,
+        annotation_semantics=annotation_semantics,
+    )
+
+
+def _operations(result):
+    return [event.operation for event in result.events]
+
+
+def test_plain_async_definition_passes():
+    result = _model(
+        "async def worker():\n"
+        "    pass\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert "DEFINE_OPAQUE_FUNCTION" in _operations(result)
+
+
+def test_async_body_is_not_executed():
+    result = _model(
+        "async def worker():\n"
+        "    import missing_external_xyz\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert "START_IMPORT" not in _operations(result)
+
+
+def test_annotated_async_definition_deferred():
+    result = _model(
+        "async def worker(x: Missing) -> Missing:\n"
+        "    pass\n",
+        annotation_semantics="DEFERRED",
+    )
+    assert result.outcome == "MODEL_PASS"
+
+
+def test_annotated_async_unknown_version():
+    result = _model(
+        "async def worker(x: Missing):\n"
+        "    pass\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_annotated_async_eager():
+    result = _model(
+        "async def worker(x: side_effect()):\n"
+        "    pass\n",
+        annotation_semantics="STOCK_EAGER",
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+@pytest.mark.parametrize(
+    "source",
+    [
+        "@decorator\nasync def worker():\n    pass",
+        "async def worker(x=side_effect()):\n    pass",
+        "@side_effect()\nasync def worker():\n    pass",
+    ],
+)
+def test_async_eager_definition_effects_unknown(source):
+    assert _model(source).outcome == "UNKNOWN"
+
+
+def test_async_invocation_unknown():
+    result = _model(
+        "async def worker():\n"
+        "    pass\n"
+        "worker()\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_passive_async_class_method():
+    result = _model(
+        "class C:\n"
+        "    async def method(self):\n"
+        "        import missing_external_xyz\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert "DEFINE_PASSIVE_CLASS" in _operations(result)
+
+
+def test_decorated_async_class_method_unknown():
+    result = _model(
+        "class C:\n"
+        "    @staticmethod\n"
+        "    async def method():\n"
+        "        pass\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_simple_module_alias():
+    result = _model(
+        "original = [1, 2]\n"
+        "copied = original\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "ALIAS"
+        and event.target == "original"
+        and event.symbol == "copied"
+        for event in result.events
+    )
+
+
+def test_chained_alias():
+    result = _model(
+        "a = 1\n"
+        "b = a\n"
+        "c = b\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert _operations(result).count("ALIAS") == 2
+
+
+def test_bound_self_alias():
+    result = _model(
+        "a = 1\n"
+        "a = a\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+
+
+def test_unbound_self_alias_unknown():
+    assert _model("a = a").outcome == "UNKNOWN"
+
+
+def test_unbound_source_unknown():
+    assert _model("copied = missing").outcome == "UNKNOWN"
+
+
+def test_builtin_not_assumed_bound():
+    assert _model("copied = len").outcome == "UNKNOWN"
+
+
+def test_special_source_not_assumed():
+    assert _model("copied = __name__").outcome == "UNKNOWN"
+
+
+def test_alias_from_imported_name():
+    result = _model(
+        "from pkg import value\n"
+        "copied = value\n",
+        initializer="value = 7",
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert "FROM" in _operations(result)
+    assert "ALIAS" in _operations(result)
+
+
+def test_alias_export_from_child():
+    result = _model(
+        "original = 7\n"
+        "copied = original\n",
+        initializer="from pkg.child import copied",
+        entry="pkg",
+    )
+    assert result.outcome == "MODEL_PASS"
+
+
+def test_alias_before_binding_unknown():
+    result = _model(
+        "copied = original\n"
+        "original = 1\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_alias_preserves_early_binding_hazard():
+    result = _model(
+        "from pkg import late\n"
+        "copied = late\n",
+        initializer=(
+            "import pkg.child\n"
+            "late = 1\n"
+        ),
+        entry="pkg",
+    )
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "late"
+
+
+def test_package_child_alias_shadowing_unknown():
+    result = _model(
+        "pass",
+        initializer=(
+            "value = 1\n"
+            "child = value\n"
+            "import pkg.child\n"
+        ),
+        entry="pkg",
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_alias_of_function_is_bound():
+    result = _model(
+        "def f():\n"
+        "    pass\n"
+        "other = f\n"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert "ALIAS" in _operations(result)
+
+
+def test_aliased_function_call_not_invented():
+    result = _model(
+        "def f():\n"
+        "    pass\n"
+        "other = f\n"
+        "other()\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_class_body_name_alias_still_unknown():
+    result = _model(
+        "x = 1\n"
+        "class C:\n"
+        "    copied = x\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_external_import_still_unknown():
+    result = _model(
+        "import missing_external_xyz\n"
+        "copy = missing_external_xyz\n"
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_namespace_layout_still_unknown():
+    result = evaluate_package_import_order(
+        {
+            "pkg.child": ast.parse(
+                "value = 1\n"
+                "copy = value\n"
+            )
+        },
+        "pkg.child",
+    )
+    assert result.outcome == "UNKNOWN"
+
+
+def test_determinism_and_ast_immutability():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.child": ast.parse(
+            "async def worker():\n"
+            "    pass\n"
+            "value = [1, 2]\n"
+            "copied = value\n"
+        ),
+    }
+
+    before = {
+        name: ast.dump(tree)
+        for name, tree in sources.items()
+    }
+
+    first = evaluate_package_import_order(
+        sources, "pkg.child"
+    )
+    second = evaluate_package_import_order(
+        sources, "pkg.child"
+    )
+
+    assert first == second
+    assert first.outcome == "MODEL_PASS"
+    assert before == {
+        name: ast.dump(tree)
+        for name, tree in sources.items()
+    }
```

## FINAL_VERDICT

BLOCKED — 217 targeted tests pass and 2 conflict with the mandated G17 contract. The exact assertion and legacy expectation are documented above; no redesign or test edits were made.
