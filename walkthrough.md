# P5-M08-I9-T2 — class decorator identity counterexamples

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `1fd481a32b8507793fc6c1f3e47e91aaa9ae9de7`; worktree clean before task edits. Active interpreter `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. Contextor LIVE revision 1365, package_model workspace_sync verified, structural DFS cycle count 16, cycle_semantics stale. I9-I2/R3 production contracts verified: decorator snapshot before PREPARE, identity-based object pairs, shared _ClassFact creation, final binding after decorator frames, both child-name guards active. New target test did not exist.

## FILES_CHANGED

- `tests/test_cycle_semantics_class_decorator_identity_counterexamples.py`

`walkthrough.md` is this report. No production or existing test file changed.

## CPYTHON_COUNTEREXAMPLE_MATRIX

| Case | CPython JSON | Model | Calls | FUNCTION_LOCAL_IMPORT | START_IMPORT |
|---|---|---|---|---:|---|
| A pre-snapshot rebinding | `{"error":"TypeError","imports":[]}` | UNKNOWN | none | 0 | none |
| B same-name decorator | `{"error":null,"imports":["pkg.effect"]}` | MODEL_PASS | C | 1 | pkg.effect |
| C duplicate references | `{"error":null,"imports":["pkg.effect","pkg.effect"]}` | MODEL_PASS | deco, deco | 2 | pkg.effect once |
| D class-local shadowing | `{"error":null,"imports":["pkg.body","pkg.effect"]}` | MODEL_PASS | deco | 1 | pkg.body, pkg.effect |
| E post-decoration rebinding | `{"error":null,"imports":["pkg.effect"]}` | MODEL_PASS | deco | 1 | pkg.effect |
| F noncallable upper member | `{"error":"TypeError","imports":["pkg.bottom_effect"]}` | UNKNOWN | bottom | 1 | pkg.bottom_effect |

DIRECT_EVIDENCE: each isolated subprocess JSON assertion and model event assertion passed. CPython import tracing records both execution of repeated import statements in C; model START_IMPORT records initial module execution once, while FUNCTION_LOCAL_IMPORT records both statements.

## PRE_SNAPSHOT_REBINDING

DIRECT_EVIDENCE: A rebinds deco to None before class decoration. CPython raises TypeError without importing pkg.effect. Model returns UNKNOWN after DEFINE_FUNCTION(deco), BIND(deco); there is no CALL_FUNCTION or effect import.

## SAME_NAME_OBJECT_IDENTITY

DIRECT_EVIDENCE: B captures the preceding function object C, creates the class fact, calls C, and records the effect import. It returns MODEL_PASS. No name-specific code path is asserted or added.

## DUPLICATE_DECORATOR_IDENTITY

DIRECT_EVIDENCE: C calls deco twice in bottom-up order and records two FUNCTION_LOCAL_IMPORT(pkg.effect) statements. START_IMPORT(pkg.effect) occurs once because module initialization is cached; CPython's trace records two import statements.

## CLASS_LOCAL_SHADOWING

DIRECT_EVIDENCE: prior direct model observation gave MODEL_PASS without unsupported module rebinding: source-order events are START_IMPORT(pkg.body), BIND(deco) inside pkg.body, CLASS_LOCAL_FROM(pkg.body, deco), DEFINE_PASSIVE_CLASS(C), then CALL_FUNCTION(deco) and START_IMPORT(pkg.effect). The decorator invocation uses the object snapshotted before class-body execution. CPython import order is pkg.body then pkg.effect.

Complete D model events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg","operation":"START_IMPORT","target":"pkg.body","symbol":null},{"module":"pkg.body","operation":"BIND","target":null,"symbol":"deco"},{"module":"pkg.body","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.body","symbol":"body"},{"module":"pkg","operation":"CLASS_LOCAL_FROM","target":"pkg.body","symbol":"deco"},{"module":"pkg","operation":"DEFINE_PASSIVE_CLASS","target":null,"symbol":"C"},{"module":"pkg","operation":"CALL_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg","operation":"START_IMPORT","target":"pkg.effect","symbol":null},{"module":"pkg.effect","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.effect","symbol":"effect"},{"module":"pkg","operation":"FUNCTION_LOCAL_IMPORT","target":"pkg.effect","symbol":"pkg"},{"module":"pkg","operation":"READY","target":null,"symbol":null}]
```

## POST_DECORATION_REBINDING

DIRECT_EVIDENCE: E applies deco and imports pkg.effect, then executes BIND(deco=None). The decoration uses its earlier snapshotted reference; model returns MODEL_PASS.

## NONCALLABLE_STACK_MEMBER

DIRECT_EVIDENCE: F applies bottom first, imports pkg.bottom_effect, then returns UNKNOWN when the captured top object is None. There is no CALL_FUNCTION(top) or START_IMPORT(pkg.top_effect). CPython raises TypeError after the bottom effect.

Complete F model events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"top"},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"bottom"},{"module":"pkg","operation":"BIND","target":null,"symbol":"top"},{"module":"pkg","operation":"DEFINE_PASSIVE_CLASS","target":null,"symbol":"C"},{"module":"pkg","operation":"CALL_FUNCTION","target":null,"symbol":"bottom"},{"module":"pkg","operation":"START_IMPORT","target":"pkg.bottom_effect","symbol":null},{"module":"pkg.bottom_effect","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.bottom_effect","symbol":"bottom_effect"},{"module":"pkg","operation":"FUNCTION_LOCAL_IMPORT","target":"pkg.bottom_effect","symbol":"pkg"}]
```

## TARGETED_TEST_RESULTS

Specified regression set: `69 passed in 15.02s`. `git diff --check`: exit 0. No full pytest or SCC02.

## MCP_POST_TASK_AUDIT

DIRECT_EVIDENCE: Contextor canonical revision 1366. New test source and package_model both workspace_sync verified; syntax errors 0, structural DFS cycle count 16. New test has one hard outbound dependency to package_model. Production owner retains 12 outbound dependencies. cycle_semantics remains stale; source freshness does not certify loaded backend adoption. No FULL, update_file, restart or semantic refresh.

## FULL_DIFFS

Complete new-file diff:

```diff
diff --git a/tests/test_cycle_semantics_class_decorator_identity_counterexamples.py b/tests/test_cycle_semantics_class_decorator_identity_counterexamples.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_class_decorator_identity_counterexamples.py
@@ -0,0,115 @@
+"""CPython identity and rebinding counterexamples for class decorators."""
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
+        "def deco(cls):\n    import pkg.effect\n    return cls\n"
+        "deco = None\n@deco\nclass C:\n    pass\n",
+        "TypeError", (), "UNKNOWN", (), 0, (),
+        id="A-rebind-before-snapshot",
+    ),
+    pytest.param(
+        "def C(cls):\n    import pkg.effect\n    return cls\n"
+        "@C\nclass C:\n    pass\n",
+        None, ("pkg.effect",), "MODEL_PASS", ("C",), 1,
+        ("pkg.effect",), id="B-same-name",
+    ),
+    pytest.param(
+        "def deco(cls):\n    import pkg.effect\n    return cls\n"
+        "@deco\n@deco\nclass C:\n    pass\n",
+        None, ("pkg.effect", "pkg.effect"), "MODEL_PASS",
+        ("deco", "deco"), 2, ("pkg.effect",),
+        id="C-duplicate-references",
+    ),
+    pytest.param(
+        "def deco(cls):\n    import pkg.effect\n    return cls\n"
+        "@deco\nclass C:\n    from pkg.body import deco\n",
+        None, ("pkg.body", "pkg.effect"), "MODEL_PASS",
+        ("deco",), 1, ("pkg.body", "pkg.effect"),
+        id="D-class-local-shadowing",
+    ),
+    pytest.param(
+        "def deco(cls):\n    import pkg.effect\n    return cls\n"
+        "@deco\nclass C:\n    pass\n"
+        "deco = None\n",
+        None, ("pkg.effect",), "MODEL_PASS", ("deco",), 1,
+        ("pkg.effect",), id="E-rebind-after-decoration",
+    ),
+    pytest.param(
+        "def top(cls):\n    import pkg.top_effect\n    return cls\n"
+        "def bottom(cls):\n    import pkg.bottom_effect\n    return cls\n"
+        "top = None\n@top\n@bottom\nclass C:\n    pass\n",
+        "TypeError", ("pkg.bottom_effect",), "UNKNOWN",
+        ("bottom",), 1, ("pkg.bottom_effect",),
+        id="F-noncallable-stack-member",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,error,imports,outcome,calls,local_import_count,starts",
+    CASES,
+)
+def test_class_decorator_identity_counterexamples(
+    tmp_path, source, error, imports, outcome, calls,
+    local_import_count, starts,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+
+    child_names = ("effect", "top_effect", "bottom_effect", "body")
+    sources = {"pkg.__init__": ast.parse(source)}
+    for child in child_names:
+        child_source = (
+            "deco = None\n" if child == "body" else "pass\n"
+        )
+        (package / f"{child}.py").write_text(
+            child_source, encoding="utf-8",
+        )
+        sources[f"pkg.{child}"] = ast.parse(child_source)
+
+    process = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
+        capture_output=True,
+        text=True,
+        timeout=20,
+        check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    observed = json.loads(process.stdout)
+    assert observed == {"error": error, "imports": list(imports)}
+
+    result = evaluate_package_import_order(sources, "pkg")
+    assert result.outcome == outcome
+    actual_calls = tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    )
+    assert actual_calls == calls
+    assert sum(
+        event.operation == "FUNCTION_LOCAL_IMPORT"
+        and event.target in {
+            "pkg.effect", "pkg.top_effect", "pkg.bottom_effect",
+        }
+        for event in result.events
+    ) == local_import_count
+    actual_starts = tuple(
+        event.target for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target is not None
+        and event.target.startswith("pkg.")
+    )
+    assert actual_starts == starts
```

## FINAL_VERDICT

PASS for I9-T2 counterexample verification and specified targeted regressions. No production behavior was modified or newly admitted.
