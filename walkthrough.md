# P5-M08-I9-I2 + R1 — first-gate STOP

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `666f3384970c77dc85f77cd3d9157f5d743ed334`; only `walkthrough.md` modified before implementation. Contextor LIVE revision 1358, package_model workspace_sync verified, structural DFS cycles 16. CPython 3.15.2 active. Required I9-I1 staging, R1 compile gate, class-fact creation, snapshot map, continuation, and collision guards were present at expected anchors.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_class_decorator_baseline.py`
- `tests/test_cycle_semantics_class_decorator_staging.py`
- `tests/test_cycle_semantics_class_decorator_execution.py`

`walkthrough.md` is this report.

## CLASS_FACT_CREATION_REUSE

CODE_PATH_PROVED: decorated and undecorated class operations enter the same prepared-fact validation and `_ClassFact` construction at `package_model.py:2512-2576` before branching. No _ClassFact, MRO or metaclass algorithm edited. The decorated branch stores identity before invoking a restricted decorator frame.

## SNAPSHOT_IDENTITY

CODE_PATH_PROVED: `SNAPSHOT_CLASS_DECORATORS` stores name/object pairs before PREPARE; decorated branch pops by definition ID, reverses captured pairs and calls the object reference. No later decorator-name lookup.

## CLASS_BODY_BEFORE_DECORATORS

CODE_PATH_PROVED: compiler orders class-body import steps between PREPARE and decorated definition. Baseline C/D passed in first gate. No class-body compilation edit.

## BOTTOM_UP_APPLICATION

CODE_PATH_PROVED: reversed decorator pairs feed separate frames. Baseline D passed. New E test failed before decorator execution due package child-name collision in its fixture.

## INTERMEDIATE_VALUE_TRANSPORT

CODE_PATH_PROVED: existing function-frame continuation transports returned object to next decorator; no continuation edit. Baseline stacked case passed in first gate.

## FINAL_BINDING

CODE_PATH_PROVED: decorated branch skips namespace write and starts frame; existing completion writes final result. Same-name model run returned MODEL_PASS with CALL_FUNCTION(C). No final namespace binding was directly inspected.

## EARLY_BINDING_HAZARD

Baseline G passed in first gate with expected EARLY_BINDING_HAZARD. No runtime safety conclusion beyond tested fixture.

## METACLASS_AND_MRO_SAFETY

Prepared class validation and C3 MRO code were preserved. Full regression subset was not run because the first gate failed.

## CONDITIONAL_DATACLASS_PRESERVATION

No conditional dataclass code edited in I9-I2. Full regression subset was not run.

## NEGATIVE_CONTRACTS

New B/C/G/H/I/J cases passed first gate. First gate also exposed two blockers:
1. New `E-two-pass-through` fixture defines functions `top` and `bottom` while indexing direct children `pkg.top` and `pkg.bottom`. The existing child-name guard at `package_model.py:1634-1650` / `:1740-1756` returns UNKNOWN with complete model events `[]`; expected MODEL_PASS. Isolated CPython runner succeeded and observed `{"error":null,"imports":["pkg.bottom","pkg.top"]}`. This is a fixture collision, not evidence that the guard should be weakened.
2. Existing `tests/test_cycle_semantics_class_decorator_staging.py::test_same_name_local_decorator_proof_gate` at line 209 still asserts UNKNOWN for the same `def C; @C class C` source. The task authorized changing only the other same-name staging test. Actual model MODEL_PASS, expected UNKNOWN. Complete events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"C"},{"module":"pkg","operation":"DEFINE_PASSIVE_CLASS","target":null,"symbol":"C"},{"module":"pkg","operation":"CALL_FUNCTION","target":null,"symbol":"C"},{"module":"pkg","operation":"READY","target":null,"symbol":null}]
```
The seven-case baseline E and new D CPython checks succeeded; same-name source is valid CPython and model positive. The second historical assertion requires auditor correction.

## CPYTHON_PARITY_MATRIX

First gate: all isolated CPython JSON assertions in the new and baseline files passed. For failing E, exact observation above. Baseline A–G CPython expectations passed; model assertions passed. UNKNOWN negatives are not claimed as CPython parity.

## TARGETED_TEST_RESULTS

Original first gate command: `2 failed, 31 passed in 12.62s`.
- `test_named_class_decorator_execution[E-two-pass-through]`: `tests/test_cycle_semantics_class_decorator_execution.py:108`; AssertionError UNKNOWN != MODEL_PASS, full events `[]`.
- `test_same_name_local_decorator_proof_gate`: `tests/test_cycle_semantics_class_decorator_staging.py:209`; AssertionError MODEL_PASS != UNKNOWN, events above.

No production exception. Full targeted regression subset NOT RUN per failure contract. `git diff --check`: exit 0; LF/CRLF notices only.

## MCP_POST_CHANGE_AUDIT

NOT RUN because the original specification allows it only after all tests pass. No FULL, update_file, restart or semantic refresh. Post-edit LIVE freshness is not claimed.

## FULL_DIFFS

```diff
warning: in the working copy of 'tests/test_cycle_semantics_class_decorator_baseline.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_cycle_semantics_class_decorator_staging.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 82116cb..7c80b5b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -2509,14 +2509,10 @@ def evaluate_package_import_order(
                 return result("UNKNOWN", module, step.binding)
             prepared_class_bases[step.definition_id] = (base_facts, selected)
 
-        elif step.op == "DEFINE_DECORATED_PASSIVE_CLASS":
-            return result(
-                "UNKNOWN",
-                module,
-                step.binding,
-            )
-
-        elif step.op == "DEFINE_PASSIVE_CLASS":
+        elif step.op in {
+            "DEFINE_PASSIVE_CLASS",
+            "DEFINE_DECORATED_PASSIVE_CLASS",
+        }:
             prepared = prepared_class_bases.pop(
                 step.definition_id or "",
                 None,
@@ -2574,6 +2570,61 @@ def evaluate_package_import_order(
                 ),
             )
             class_facts_by_identity[identity] = class_fact
+            if step.op == "DEFINE_DECORATED_PASSIVE_CLASS":
+                decorator_pairs = class_decorator_snapshots.pop(
+                    identity,
+                    None,
+                )
+
+                if not decorator_pairs:
+                    return result("UNKNOWN", module, step.binding)
+
+                application_order = tuple(
+                    reversed(decorator_pairs)
+                )
+
+                first_name, first_object = application_order[0]
+                local_bindings: dict[str, object | None] = {}
+
+                body = _execute_restricted_object_call(
+                    first_object,
+                    class_fact,
+                    module=module,
+                    local_bindings=local_bindings,
+                )
+
+                if body is None:
+                    return result("UNKNOWN", module, first_name)
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        "DEFINE_PASSIVE_CLASS",
+                        symbol=step.binding,
+                    )
+                )
+
+                events.append(
+                    PackageModelEvent(
+                        module,
+                        "CALL_FUNCTION",
+                        symbol=first_name,
+                    )
+                )
+
+                frames[-1] = _advance_frame(frames[-1])
+                frames.append(
+                    _FunctionFrame(
+                        module=module,
+                        index=0,
+                        steps=body,
+                        local_bindings=local_bindings,
+                        decorator_final_binding=step.binding,
+                        remaining_decorators=application_order[1:],
+                    )
+                )
+                continue
+
             namespaces[module][step.binding] = (
                 class_fact
             )
diff --git a/tests/test_cycle_semantics_class_decorator_baseline.py b/tests/test_cycle_semantics_class_decorator_baseline.py
index 1253d08..84026b7 100644
--- a/tests/test_cycle_semantics_class_decorator_baseline.py
+++ b/tests/test_cycle_semantics_class_decorator_baseline.py
@@ -16,46 +16,59 @@ from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
 CASES = [
     pytest.param(
         "def identity(cls):\n    return cls\n@identity\nclass C:\n    pass\n",
-        None, (), id="A-pass-through",
+        None, (), "MODEL_PASS", ("identity",), (), id="A-pass-through",
     ),
     pytest.param(
-        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
-        "@decorate\nclass C:\n    pass\n",
-        None, ("pkg.decorate",), id="B-decorator-import",
+        "def apply_decorator(cls):\n    import pkg.decorate\n    return cls\n"
+        "@apply_decorator\nclass C:\n    pass\n",
+        None, ("pkg.decorate",), "MODEL_PASS",
+        ("apply_decorator",), ("pkg.decorate",), id="B-decorator-import",
     ),
     pytest.param(
-        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
-        "@decorate\nclass C:\n    import pkg.body\n",
-        None, ("pkg.body", "pkg.decorate"), id="C-body-before-decorator",
+        "def apply_decorator(cls):\n    import pkg.decorate\n    return cls\n"
+        "@apply_decorator\nclass C:\n    import pkg.body\n",
+        None, ("pkg.body", "pkg.decorate"), "MODEL_PASS",
+        ("apply_decorator",), ("pkg.body", "pkg.decorate"),
+        id="C-body-before-decorator",
     ),
     pytest.param(
         "def top_decorator(cls):\n    import pkg.top\n    return cls\n"
         "def bottom_decorator(cls):\n    import pkg.bottom\n    return cls\n"
         "@top_decorator\n@bottom_decorator\nclass C:\n"
         "    import pkg.body\n",
-        None, ("pkg.body", "pkg.bottom", "pkg.top"),
+        None, ("pkg.body", "pkg.bottom", "pkg.top"), "MODEL_PASS",
+        ("bottom_decorator", "top_decorator"),
+        ("pkg.body", "pkg.bottom", "pkg.top"),
         id="D-stacked-class-decorators",
     ),
     pytest.param(
         "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
-        None, (), id="E-same-name-decorator",
+        None, (), "MODEL_PASS", ("C",), (), id="E-same-name-decorator",
     ),
     pytest.param(
-        "def decorate(cls):\n    return\n@decorate\nclass C:\n"
+        "def apply_decorator(cls):\n    return\n@apply_decorator\nclass C:\n"
         "    import pkg.body\n",
-        None, ("pkg.body",), id="F-decorator-returns-none",
+        None, ("pkg.body",), "MODEL_PASS",
+        ("apply_decorator",), ("pkg.body",),
+        id="F-decorator-returns-none",
     ),
     pytest.param(
-        "def decorate(cls):\n    import pkg.child\n    return cls\n"
-        "@decorate\nclass C:\n    pass\n",
-        "ImportError", ("pkg.child",), id="G-early-class-binding-hazard",
+        "def apply_decorator(cls):\n    import pkg.child\n    return cls\n"
+        "@apply_decorator\nclass C:\n    pass\n",
+        "ImportError", ("pkg.child",), "EARLY_BINDING_HAZARD",
+        ("apply_decorator",), ("pkg.child",),
+        id="G-early-class-binding-hazard",
     ),
 ]
 
 
-@pytest.mark.parametrize("source,expected_error,expected_imports", CASES)
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports,expected_model_outcome,expected_calls,expected_starts",
+    CASES,
+)
 def test_class_decorator_definition_time_baseline(
     tmp_path, source, expected_error, expected_imports,
+    expected_model_outcome, expected_calls, expected_starts,
 ):
     package = tmp_path / "pkg"
     package.mkdir()
@@ -86,7 +99,31 @@ def test_class_decorator_definition_time_baseline(
     }
 
     result = evaluate_package_import_order(sources, "pkg")
-    assert result.outcome == "UNKNOWN", (
+    assert result.outcome == expected_model_outcome, (
         result.outcome,
         [event.__dict__ for event in result.events],
     )
+    actual_calls = tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    )
+    assert actual_calls == expected_calls
+    actual_starts = tuple(
+        event.target for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target is not None
+        and event.target.startswith("pkg.")
+    )
+    assert actual_starts == expected_starts
+    if expected_model_outcome == "EARLY_BINDING_HAZARD":
+        assert any(
+            event.operation == "EARLY_BINDING_HAZARD"
+            and event.symbol == "C"
+            for event in result.events
+        )
+        assert not any(
+            event.operation == "BIND"
+            and event.module == "pkg"
+            and event.symbol == "C"
+            for event in result.events
+        )
diff --git a/tests/test_cycle_semantics_class_decorator_staging.py b/tests/test_cycle_semantics_class_decorator_staging.py
index f393741..be9578e 100644
--- a/tests/test_cycle_semantics_class_decorator_staging.py
+++ b/tests/test_cycle_semantics_class_decorator_staging.py
@@ -72,7 +72,7 @@ def test_multiple_named_class_decorators_keep_source_order():
     assert snapshot.decorator_names == ("top", "bottom")
 
 
-def test_same_name_decorator_stages_but_remains_unknown():
+def test_same_name_decorator_stages_and_executes():
     source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
     steps = _steps(source)
     assert steps is not None
@@ -81,7 +81,12 @@ def test_same_name_decorator_stages_but_remains_unknown():
     result = evaluate_package_import_order(
         {"pkg.__init__": ast.parse(source)}, "pkg",
     )
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol == "C"
+        for event in result.events
+    )
 
 
 def test_attribute_class_decorator_stays_unknown():
diff --git a/tests/test_cycle_semantics_class_decorator_execution.py b/tests/test_cycle_semantics_class_decorator_execution.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_class_decorator_execution.py
@@ -0,0 +1,126 @@
+"""Restricted named class decorator execution and fail-closed boundaries."""
+
+import ast
+import json
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        "class C:\n    pass\n", None, (), "MODEL_PASS", (), (),
+        id="A-undecorated-class",
+    ),
+    pytest.param(
+        "def deco(cls):\n    return cls\n"
+        "deco = None\n@deco\nclass C:\n    pass\n",
+        "TypeError", (), "UNKNOWN", (), (),
+        id="B-overwritten-decorator",
+    ),
+    pytest.param(
+        "def deco(cls):\n    import pkg.effect\n    return\n"
+        "@deco\nclass C:\n    pass\nC()\n",
+        "TypeError", ("pkg.effect",), "UNKNOWN", ("deco",),
+        ("pkg.effect",), id="C-final-none-called",
+    ),
+    pytest.param(
+        "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
+        None, (), "MODEL_PASS", ("C",), (),
+        id="D-same-name",
+    ),
+    pytest.param(
+        "def top(cls):\n    import pkg.top\n    return cls\n"
+        "def bottom(cls):\n    import pkg.bottom\n    return cls\n"
+        "@top\n@bottom\nclass C:\n    pass\n",
+        None, ("pkg.bottom", "pkg.top"), "MODEL_PASS",
+        ("bottom", "top"), ("pkg.bottom", "pkg.top"),
+        id="E-two-pass-through",
+    ),
+    pytest.param(
+        "def deco(cls):\n    import pkg.effect\n    return cls\n"
+        "@deco\nclass C:\n    import pkg.body\n",
+        None, ("pkg.body", "pkg.effect"), "MODEL_PASS",
+        ("deco",), ("pkg.body", "pkg.effect"),
+        id="F-body-before-decorator",
+    ),
+    pytest.param(
+        "@factory.decorate\nclass C:\n    pass\n",
+        "NameError", (), "UNKNOWN", (), (),
+        id="G-attribute-decorator",
+    ),
+    pytest.param(
+        "def deco(cls):\n    return cls\n"
+        "class Meta(type):\n    def __new__(mcls, name, bases, ns):\n"
+        "        return super().__new__(mcls, name, bases, ns)\n"
+        "@deco\nclass C(metaclass=Meta):\n    pass\n",
+        None, (), "UNKNOWN", (), (),
+        id="H-unsupported-metaclass",
+    ),
+    pytest.param(
+        "def deco(cls):\n    return cls\n"
+        "class X: pass\nclass Y: pass\n"
+        "class A(X, Y): pass\nclass B(Y, X): pass\n"
+        "@deco\nclass C(A, B): pass\n",
+        "TypeError", (), "UNKNOWN", (), (),
+        id="I-conflicting-mro",
+    ),
+    pytest.param(
+        "def deco(cls):\n    return cls\n"
+        "@deco\nclass child:\n    pass\n",
+        None, (), "UNKNOWN", (), (),
+        id="J-indexed-child-name-collision",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,error,imports,outcome,calls,starts", CASES,
+)
+def test_named_class_decorator_execution(
+    tmp_path, source, error, imports, outcome, calls, starts,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    child_names = ("effect", "body", "top", "bottom", "child")
+    sources = {"pkg.__init__": ast.parse(source)}
+    for name in child_names:
+        (package / f"{name}.py").write_text("pass\n", encoding="utf-8")
+        sources[f"pkg.{name}"] = ast.parse("pass\n")
+
+    process = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
+        capture_output=True, text=True, timeout=20, check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    assert json.loads(process.stdout) == {
+        "error": error, "imports": list(imports),
+    }
+
+    result = evaluate_package_import_order(sources, "pkg")
+    assert result.outcome == outcome, [
+        event.__dict__ for event in result.events
+    ]
+    assert tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ) == calls
+    assert tuple(
+        event.target for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target is not None
+        and event.target.startswith("pkg.")
+    ) == starts
+    if outcome == "MODEL_PASS":
+        assert any(
+            event.operation == "DEFINE_PASSIVE_CLASS"
+            and event.symbol == "C"
+            for event in result.events
+        )
```

## FINAL_VERDICT

REGRESSION_FAILURE / BLOCKED_SEMANTIC_INTEGRITY. FINAL PASS denied. Changes remain uncommitted; no independent test repair was made after the first gate failed.
