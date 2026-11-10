# P5-M07-I2B — Function identity counterexample regressions

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `_execute_restricted_call` resolves to `contextor/core/cycle_semantics/execution/calls.py:25-45`; canonical LIVE revision 1302, production source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `fd65eeb25ed66b556ba24623ae8e7df3820c6cfd`; initial `git status --short` clean. Active backend executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M07-I2A is present: identity-equality `_RestrictedFunction` at `execution/calls.py:9-22`; namespace-object call resolution at `:25-45`; fresh factory call in DEFINE_FUNCTION at `package_model.py:1884-1891`; `function_definitions` no longer appears in the inspected production modules. T1/T2 test files exist. The new counterexample file did not exist before this task.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_function_identity_counterexamples.py` exactly as specified. Complete new-file diff below.
- Overwrote `walkthrough.md` for this task. No production or previously existing test file changed.

## CPYTHON_COUNTEREXAMPLE_MATRIX

DIRECT_EVIDENCE: Each row is the observed JSON from the isolated CPython runner using the active venv. The new test independently asserts success/error and import membership (`tests/test_cycle_semantics_function_identity_counterexamples.py:100-117`).

| Case | `ok` | `error` | `pkg.old` | `pkg.new` | `g is f` |
|---|---:|---|---:|---:|---:|
| alias-chain-survives-rebinding | true | null | true | false | false |
| alias-rebound-to-new-definition | true | null | false | true | true |
| old-and-new-bodies-both-executed | true | null | true | true | false |
| old-object-restored-under-original-name | true | null | true | false | true |
| alias-overwritten-with-noncallable | false | `TypeError` | false | false | null |

## MODEL_COUNTEREXAMPLE_MATRIX

DIRECT_EVIDENCE: `START_IMPORT` child targets and ordered `CALL_FUNCTION` symbols were read from `PackageImportAssessment.events` on the same five AST inputs and are asserted in `tests/test_cycle_semantics_function_identity_counterexamples.py:119-151`.

| Case | Model outcome | Child `START_IMPORT` order | `CALL_FUNCTION` order | Contract |
|---|---|---|---|---|
| alias-chain-survives-rebinding | MODEL_PASS | `pkg.old` | `h` | CPython import effect matches |
| alias-rebound-to-new-definition | MODEL_PASS | `pkg.new` | `g` | CPython import effect matches |
| old-and-new-bodies-both-executed | MODEL_PASS | `pkg.old`, `pkg.new` | `g`, `f` | CPython import effects match |
| old-object-restored-under-original-name | MODEL_PASS | `pkg.old` | `f` | CPython import effect matches |
| alias-overwritten-with-noncallable | UNKNOWN | none | none | Conservative stop; no false PASS |

## EVENT_ORDER_VERIFICATION

- DIRECT_EVIDENCE: Alias chain: `START_IMPORT(pkg) → DEFINE_FUNCTION(f) → ALIAS(f,g) → ALIAS(g,h) → BIND(f) → CALL_FUNCTION(h) → START_IMPORT(pkg.old) → READY(pkg.old) → BIND_CHILD(pkg.old) → FUNCTION_LOCAL_IMPORT(pkg.old) → READY(pkg)`.
- DIRECT_EVIDENCE: Rebound alias: `START_IMPORT(pkg) → DEFINE_FUNCTION(f) → ALIAS(f,g) → DEFINE_FUNCTION(f) → ALIAS(f,g) → CALL_FUNCTION(g) → START_IMPORT(pkg.new) → READY(pkg.new) → BIND_CHILD(pkg.new) → FUNCTION_LOCAL_IMPORT(pkg.new) → READY(pkg)`.
- DIRECT_EVIDENCE: Both bodies: `START_IMPORT(pkg) → DEFINE_FUNCTION(f) → ALIAS(f,g) → DEFINE_FUNCTION(f) → CALL_FUNCTION(g) → START_IMPORT(pkg.old) → READY(pkg.old) → BIND_CHILD(pkg.old) → FUNCTION_LOCAL_IMPORT(pkg.old) → CALL_FUNCTION(f) → START_IMPORT(pkg.new) → READY(pkg.new) → BIND_CHILD(pkg.new) → FUNCTION_LOCAL_IMPORT(pkg.new) → READY(pkg)`.
- DIRECT_EVIDENCE: Restored original: `START_IMPORT(pkg) → DEFINE_FUNCTION(f) → ALIAS(f,g) → DEFINE_FUNCTION(f) → ALIAS(g,f) → CALL_FUNCTION(f) → START_IMPORT(pkg.old) → READY(pkg.old) → BIND_CHILD(pkg.old) → FUNCTION_LOCAL_IMPORT(pkg.old) → READY(pkg)`.
- DIRECT_EVIDENCE: Noncallable: `START_IMPORT(pkg) → DEFINE_FUNCTION(f) → ALIAS(f,g) → BIND(g)` and UNKNOWN. No call or child-import event was emitted. This absence reflects the explicit return before event emission in `package_model.py:2164-2181` and the object check in `execution/calls.py:33-39`; it is not independent proof of safety.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused command using the active backend venv across the five specified test files returned `64 passed in 11.71s`.
- DIRECT_EVIDENCE: `git diff --check` exited 0. No full pytest, SCC02, FULL, `update_file`, restart, Git add/commit/push, or index/history modification.

## MCP_POST_TASK_AUDIT

- DIRECT_EVIDENCE: Post-task Contextor lookup still reported canonical LIVE revision 1302, production symbol fresh, `workspace_sync=verified`, structural DFS back-edge cycle count 16, syntax errors 0, cycle_semantics stale. A new test file has no attested canonical freshness in that production-symbol response. No semantic-cycle refresh or backend adoption is claimed.

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_function_identity_counterexamples.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_function_identity_counterexamples.py
@@ -0,0 +1,151 @@
+import ast
+import json
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+from test_cycle_semantics_function_identity_cpython import (
+    RUNNER,
+    OLD,
+    NEW,
+)
+
+
+CASES = [
+    pytest.param(
+        OLD + "\ng = f\nh = g\nf = None\nh()\n",
+        "MODEL_PASS",
+        True,
+        False,
+        ["h"],
+        None,
+        id="alias-chain-survives-rebinding",
+    ),
+    pytest.param(
+        OLD + "\ng = f\n" + NEW + "\ng = f\ng()\n",
+        "MODEL_PASS",
+        False,
+        True,
+        ["g"],
+        None,
+        id="alias-rebound-to-new-definition",
+    ),
+    pytest.param(
+        OLD + "\ng = f\n" + NEW + "\ng()\nf()\n",
+        "MODEL_PASS",
+        True,
+        True,
+        ["g", "f"],
+        None,
+        id="old-and-new-bodies-both-executed",
+    ),
+    pytest.param(
+        OLD + "\ng = f\n" + NEW + "\nf = g\nf()\n",
+        "MODEL_PASS",
+        True,
+        False,
+        ["f"],
+        None,
+        id="old-object-restored-under-original-name",
+    ),
+    pytest.param(
+        OLD + "\ng = f\ng = None\ng()\n",
+        "UNKNOWN",
+        False,
+        False,
+        [],
+        "TypeError",
+        id="alias-overwritten-with-noncallable",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,outcome,old,new,call_names,error",
+    CASES,
+)
+def test_function_identity_counterexample_parity(
+    tmp_path: Path,
+    source: str,
+    outcome: str,
+    old: bool,
+    new: bool,
+    call_names: list[str],
+    error: str | None,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source,
+        encoding="utf-8",
+    )
+    (package / "old.py").write_text(
+        "pass\n",
+        encoding="utf-8",
+    )
+    (package / "new.py").write_text(
+        "pass\n",
+        encoding="utf-8",
+    )
+
+    process = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            RUNNER,
+            str(tmp_path),
+            "pkg",
+        ],
+        text=True,
+        capture_output=True,
+        timeout=20,
+        check=False,
+    )
+
+    assert process.returncode == 0, process.stderr
+
+    actual = json.loads(process.stdout)
+
+    assert actual["ok"] == (error is None)
+    assert actual["error"] == error
+    assert actual["old"] is old
+    assert actual["new"] is new
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.old": ast.parse("pass\n"),
+            "pkg.new": ast.parse("pass\n"),
+        },
+        "pkg",
+    )
+
+    assert result.outcome == outcome
+
+    imported = {
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target in {"pkg.old", "pkg.new"}
+    }
+
+    assert ("pkg.old" in imported) is old
+    assert ("pkg.new" in imported) is new
+
+    model_calls = [
+        event.symbol
+        for event in result.events
+        if event.operation == "CALL_FUNCTION"
+        and event.module == "pkg"
+    ]
+
+    assert model_calls == call_names
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact five counterexample regressions pass on isolated CPython and the Contextor evaluator; model event order and child import effects match the supported cases, while the noncallable case remains UNKNOWN. This is focused evidence for the bounded M07-I2A behavior, not general call or decorator semantics. Stop after this test stage.
