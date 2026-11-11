# P5-M08-I6 — single named function decorator

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first reported canonical LIVE revision 1323, `package_model.py` fresh with `workspace_sync=verified`, and stale `cycle_semantics`. Initial HEAD `b6507f71e3c4ffe8a9af13a34df75e96da52ae96`; initial `git status --short` clean. Backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` is CPython 3.15.2 (same active venv as M08-I5).
- DIRECT_EVIDENCE: M08-I5 contracts present at `execution/calls.py:8-52`, `execution/state.py:31-72`, and `package_model.py:980-1150,2279-2348`. Class decorator handling was not edited. Existing M08-T3 and M08-T2 cases and assertions were inspected at `tests/test_cycle_semantics_call_frame_baseline.py:14-193` and `tests/test_cycle_semantics_decorator_import_effect_baseline.py:15-186`.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_named_function_decorators.py` (new)
- `tests/test_cycle_semantics_call_frame_baseline.py`
- `tests/test_cycle_semantics_decorator_import_effect_baseline.py`
- `walkthrough.md` (this report)

## DECORATOR_EVALUATION_AND_APPLICATION

- CODE_PATH_PROVED: Only one ordinary `ast.Name` decorator is admitted for restricted `FunctionDef` at `package_model.py:142-180,980-1105`. The name is resolved in the current module namespace. The newly created restricted function is passed to the existing `_execute_restricted_call`, and the decorator body runs in a function frame (`package_model.py:2018-2072`). There is no decorator-name allowlist or passivity assumption. Decorator factories, attributes, multiple decorators, decorated opaque bodies and class decorators remain unsupported.

## FUNCTION_BINDING_ORDER

- CODE_PATH_PROVED: The decorated function is created without first binding its final module name; the decorator is called through the old namespace binding. The caller is advanced and a frame with `result_binding=step.binding` is pushed. `RETURN_FUNCTION` or ordinary frame completion performs final binding (`package_model.py:2018-2072,2300-2311,1691-1699`). The same-name decorator case has direct CPython/model comparison in `tests/test_cycle_semantics_named_function_decorators.py:30-34,85-114`.

## CPYTHON_PARITY_MATRIX

| Case | CPython 3.15.2 | Model | CALL_FUNCTION |
|---|---|---|---|
| pass-through | success; child | MODEL_PASS; child | identity, f |
| deferred body | success; none | MODEL_PASS; none | identity |
| decorator alias | success; child | MODEL_PASS; child | alias, f |
| same-name decorator | success; child | MODEL_PASS; child | f, f |
| returns None | success; none | MODEL_PASS; none | deco |
| call noncallable result | TypeError; none | UNKNOWN; none | deco |
| noncallable decorator | TypeError; none | UNKNOWN; none | none |
| wrong decorator arity | TypeError; none | UNKNOWN; none | none |
| decorated defaults | success; none | UNKNOWN | none |
| multiple decorators | success; none | UNKNOWN | none |
| decorator import effect | success; child | UNKNOWN | none |

- DIRECT_EVIDENCE: `tests/test_cycle_semantics_named_function_decorators.py:12-114` runs all 11 sources in an isolated CPython process and separately through `evaluate_package_import_order`; exact error type, import trace, model result and call order are asserted. UNKNOWN is not claimed as parity.

## NEGATIVE_CONTRACTS

- CODE_PATH_PROVED: Noncallable/wrong-arity decorators are rejected before a decorator `CALL_FUNCTION` event (`package_model.py:2020-2048`; `execution/calls.py:35-42`). A decorator returning `None` binds that value; later attempted `f()` returns UNKNOWN without a false successful `CALL_FUNCTION(f)` (`package_model.py:2300-2345`). Unsupported decorated definitions return UNKNOWN at compilation (`package_model.py:1086-1105`). Importing decorators and general definition-time effects are still outside this bounded path.

## UPDATED_BASELINE_ASSERTIONS

- DIRECT_EVIDENCE: Only `pass-through-decorator-defers-body` and `pass-through-decorator-then-call` now expect `MODEL_PASS` in M08-T3; its other five cases expect UNKNOWN. Only `decorated-function-body-deferred` now expects MODEL_PASS in M08-T2; its other four cases expect UNKNOWN. CPython inputs and assertions were preserved (`tests/test_cycle_semantics_call_frame_baseline.py:14-193`; `tests/test_cycle_semantics_decorator_import_effect_baseline.py:15-186`).

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: The requested 12-file focused pytest command completed: **316 passed, 2 third-party Authlib deprecation warnings**, exit 0, 32.31 s. `git diff --check` exit 0; Git emitted line-ending notices only. No full suite or SCC02 was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Canonical LIVE revision **1327**; `package_model.py` and all three changed test files source fresh, `workspace_sync=verified`. Syntax errors 0, structural DFS back-edge cycle count 16, active warnings 16; graph and cycles fresh, `cycle_semantics=stale`. No new production hard dependency edge was observed. Source freshness does not prove loaded-code adoption or fresh semantic classification.

## FULL_DIFFS

Complete changed-source diffs follow. Blank context lines omit Git's trailing context space for Markdown whitespace hygiene.

### package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 0500033..c8c81a6 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -145,6 +145,7 @@ def _safe_passive_function_definition(
     allow_dunder: bool = False,
     annotation_semantics: str | None = None,
     allow_builtin_property: bool = False,
+    allow_restricted_decorator: bool = False,
 ) -> bool:
     """A definition whose creation has no unknown evaluations.

@@ -168,6 +169,12 @@ def _safe_passive_function_definition(
                 and statement.decorator_list[0].id
                 == "property"
             )
+            and not (
+                allow_restricted_decorator
+                and len(statement.decorator_list) == 1
+                and type(statement.decorator_list[0]) is ast.Name
+                and not statement.decorator_list[0].id.startswith("__")
+            )
         )
         or (statement.returns is not None and annotation_semantics not in {
             "DEFERRED", "STRINGIFIED",
@@ -973,7 +980,9 @@ def _compile(

         elif isinstance(stmt, ast.FunctionDef):
             if not _safe_passive_function_definition(
-                stmt, annotation_semantics=annotation_semantics,
+                stmt,
+                annotation_semantics=annotation_semantics,
+                allow_restricted_decorator=True,
             ):
                 return None

@@ -1074,10 +1083,22 @@ def _compile(
             ):
                 restricted_callable = False

+            if stmt.decorator_list and not restricted_callable:
+                return None
+
             if restricted_callable:
                 steps.append(
                     _Step(
-                        "DEFINE_FUNCTION",
+                        (
+                            "DEFINE_DECORATED_FUNCTION"
+                            if stmt.decorator_list
+                            else "DEFINE_FUNCTION"
+                        ),
+                        target=(
+                            stmt.decorator_list[0].id
+                            if stmt.decorator_list
+                            else None
+                        ),
                         binding=stmt.name,
                         function_body=tuple(function_steps),
                         parameters=tuple(
@@ -1545,6 +1566,7 @@ def evaluate_package_import_order(
         if any(
             step.op in {
                 "DEFINE_FUNCTION",
+                "DEFINE_DECORATED_FUNCTION",
                 "DEFINE_OPAQUE_FUNCTION",
                 "DEFINE_PASSIVE_CLASS",
                 "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
@@ -1645,6 +1667,7 @@ def evaluate_package_import_order(
                 if any(
                     step.op in {
                         "DEFINE_FUNCTION",
+                        "DEFINE_DECORATED_FUNCTION",
                         "DEFINE_OPAQUE_FUNCTION",
                         "DEFINE_PASSIVE_CLASS",
                         "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
@@ -1995,6 +2018,61 @@ def evaluate_package_import_order(
                     )
                 )

+        elif step.op == "DEFINE_DECORATED_FUNCTION":
+            if (
+                not step.target
+                or not step.binding
+                or step.target not in namespaces[module]
+            ):
+                return result("UNKNOWN", module, step.target)
+
+            decorated_function = _new_restricted_function(
+                module,
+                step.function_body,
+                step.parameters,
+            )
+            decorator_call = _Step(
+                "CALL_FUNCTION",
+                target=step.target,
+                call_argument_values=(decorated_function,),
+            )
+            local_bindings: dict[str, object | None] = {}
+            body = _execute_restricted_call(
+                decorator_call,
+                module=module,
+                namespaces=namespaces,
+                local_bindings=local_bindings,
+            )
+
+            if body is None:
+                return result("UNKNOWN", module, step.target)
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_FUNCTION",
+                    symbol=step.binding,
+                )
+            )
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "CALL_FUNCTION",
+                    symbol=step.target,
+                )
+            )
+            frames[-1] = _advance_frame(frames[-1])
+            frames.append(
+                _FunctionFrame(
+                    module,
+                    0,
+                    body,
+                    local_bindings,
+                    step.binding,
+                )
+            )
+            continue
+
         elif step.op == "DEFINE_FUNCTION":
             namespaces[module][step.binding] = (
                 _new_restricted_function(
```

### tests/test_cycle_semantics_call_frame_baseline.py

```diff
diff --git a/tests/test_cycle_semantics_call_frame_baseline.py b/tests/test_cycle_semantics_call_frame_baseline.py
index 47c62ec..ae973e0 100644
--- a/tests/test_cycle_semantics_call_frame_baseline.py
+++ b/tests/test_cycle_semantics_call_frame_baseline.py
@@ -20,6 +20,7 @@ CASES = [
         ),
         None,
         (),
+        "UNKNOWN",
         id="positional-identity-return",
@@ -32,6 +33,7 @@ CASES = [
         ),
         None,
         (),
+        "UNKNOWN",
         id="parameter-and-local-binding",
@@ -43,6 +45,7 @@ CASES = [
         ),
         None,
         (),
+        "UNKNOWN",
         id="return-skips-later-import",
@@ -55,6 +58,7 @@ CASES = [
         ),
         None,
         (),
+        "MODEL_PASS",
         id="pass-through-decorator-defers-body",
@@ -68,6 +72,7 @@ CASES = [
         ),
         None,
         ("pkg.child",),
+        "MODEL_PASS",
         id="pass-through-decorator-then-call",
@@ -81,6 +86,7 @@ CASES = [
         ),
         None,
         ("pkg.child",),
+        "UNKNOWN",
         id="return-callable-and-invoke",
@@ -91,6 +97,7 @@ CASES = [
         ),
         "TypeError",
         (),
+        "UNKNOWN",
         id="missing-required-argument",
@@ -129,7 +136,7 @@ print(json.dumps({


 @pytest.mark.parametrize(
-    "source,expected_error,expected_imports",
+    "source,expected_error,expected_imports,expected_model_outcome",
     CASES,
 )
 def test_call_frame_cpython_and_current_model(
@@ -137,6 +144,7 @@ def test_call_frame_cpython_and_current_model(
     source: str,
     expected_error: str | None,
     expected_imports: tuple[str, ...],
+    expected_model_outcome: str,
 ):
     package = tmp_path / "pkg"
     package.mkdir()
@@ -182,9 +190,7 @@ def test_call_frame_cpython_and_current_model(
         "pkg",
     )

-    # Baseline of the current model, not the target
-    # outcome after call-frame implementation.
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == expected_model_outcome

     # A conservative UNKNOWN must not be presented
     # as execution parity or as evidence of passivity.
```

### tests/test_cycle_semantics_decorator_import_effect_baseline.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_import_effect_baseline.py b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
index 5ec980b..32d3067 100644
--- a/tests/test_cycle_semantics_decorator_import_effect_baseline.py
+++ b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
@@ -22,6 +22,7 @@ CASES = [
             "    import pkg.child\n"
         ),
         (),
+        "MODEL_PASS",
         id="decorated-function-body-deferred",
@@ -34,6 +35,7 @@ CASES = [
             "    pass\n"
         ),
         ("pkg.child",),
+        "UNKNOWN",
         id="decorator-import-during-definition",
@@ -50,6 +52,7 @@ CASES = [
             "    pass\n"
         ),
         ("pkg.lower", "pkg.upper"),
+        "UNKNOWN",
         id="stacked-decorator-import-order",
@@ -62,6 +65,7 @@ CASES = [
             "    import pkg.body\n"
         ),
         ("pkg.body", "pkg.decorate"),
+        "UNKNOWN",
         id="class-body-before-decorator",
@@ -77,6 +81,7 @@ CASES = [
             "    pass\n"
         ),
         ("pkg.default", "pkg.decorate"),
+        "UNKNOWN",
         id="default-before-decorator-application",
@@ -114,11 +119,12 @@ print(json.dumps({
 """


-@pytest.mark.parametrize("source,expected_imports", CASES)
+@pytest.mark.parametrize("source,expected_imports,expected_model_outcome", CASES)
 def test_minimal_decorator_import_effects(
     tmp_path: Path,
     source: str,
     expected_imports: tuple[str, ...],
+    expected_model_outcome: str,
 ):
     package = tmp_path / "pkg"
     package.mkdir()
@@ -177,6 +183,4 @@ def test_minimal_decorator_import_effects(
         "pkg",
     )

-    # Current conservative model boundary.
-    # Not the target behavior after implementation.
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == expected_model_outcome
```

### tests/test_cycle_semantics_named_function_decorators.py

```diff
diff --git a/tests/test_cycle_semantics_named_function_decorators.py b/tests/test_cycle_semantics_named_function_decorators.py
new file mode 100644
index 0000000..806084b
--- /dev/null
+++ b/tests/test_cycle_semantics_named_function_decorators.py
@@ -0,0 +1,114 @@
+import ast
+import json
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        "def identity(fn):\n    return fn\n@identity\ndef f():\n    import pkg.child\nf()\n",
+        None, ("pkg.child",), "MODEL_PASS", ("identity", "f"),
+        id="pass-through-decorator",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\n@identity\ndef f():\n    import pkg.child\n",
+        None, (), "MODEL_PASS", ("identity",),
+        id="deferred-decorated-function",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\nalias = identity\n@alias\ndef f():\n    import pkg.child\nf()\n",
+        None, ("pkg.child",), "MODEL_PASS", ("alias", "f"),
+        id="decorator-alias",
+    ),
+    pytest.param(
+        "def f(fn):\n    return fn\n@f\ndef f():\n    import pkg.child\nf()\n",
+        None, ("pkg.child",), "MODEL_PASS", ("f", "f"),
+        id="same-name-decorator",
+    ),
+    pytest.param(
+        "def deco(fn):\n    return\n@deco\ndef f():\n    import pkg.child\n",
+        None, (), "MODEL_PASS", ("deco",),
+        id="decorator-returns-none",
+    ),
+    pytest.param(
+        "def deco(fn):\n    return\n@deco\ndef f():\n    import pkg.child\nf()\n",
+        "TypeError", (), "UNKNOWN", ("deco",),
+        id="noncallable-decorated-result",
+    ),
+    pytest.param(
+        "deco = None\n@deco\ndef f():\n    import pkg.child\n",
+        "TypeError", (), "UNKNOWN", (),
+        id="noncallable-decorator",
+    ),
+    pytest.param(
+        "def deco():\n    return\n@deco\ndef f():\n    import pkg.child\n",
+        "TypeError", (), "UNKNOWN", (),
+        id="decorator-wrong-arity",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\n@identity\ndef f(x=1):\n    import pkg.child\n",
+        None, (), "UNKNOWN", (),
+        id="decorated-unsupported-body",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\n@identity\n@identity\ndef f():\n    import pkg.child\n",
+        None, (), "UNKNOWN", (),
+        id="multiple-decorators",
+    ),
+    pytest.param(
+        "def deco(fn):\n    import pkg.child\n    return fn\n@deco\ndef f():\n    pass\n",
+        None, ("pkg.child",), "UNKNOWN", (),
+        id="decorator-import-effect-unsupported",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports,expected_outcome,expected_calls",
+    CASES,
+)
+def test_named_function_decorator_cpython_and_model(
+    tmp_path, source, expected_error, expected_imports,
+    expected_outcome, expected_calls,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    (package / "child.py").write_text("pass\n", encoding="utf-8")
+    process = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
+        capture_output=True, text=True, timeout=20, check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    assert json.loads(process.stdout) == {
+        "error": expected_error,
+        "imports": list(expected_imports),
+    }
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse("pass\n"),
+        },
+        "pkg",
+    )
+    assert result.outcome == expected_outcome
+    assert tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ) == expected_calls
+    if expected_outcome == "MODEL_PASS":
+        assert tuple(
+            event.target for event in result.events
+            if event.operation == "START_IMPORT" and event.target == "pkg.child"
+        ) == expected_imports
+    else:
+        assert not any(
+            event.operation == "START_IMPORT" and event.target == "pkg.child"
+            for event in result.events
+        )
```

## FINAL_VERDICT

CONTRACT_PROVED for the bounded single-name decorator cases with direct CPython comparison and focused tests. Canonical source/graph is fresh; `cycle_semantics` remains stale, so no fresh warning-suppression or runtime-safety verdict is claimed. STOP after this stage.
