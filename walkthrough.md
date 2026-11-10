# P5-M07-I2-T2 — Observable model baseline

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first resolved `_execute_restricted_call` at `contextor/core/cycle_semantics/execution/calls.py:8-35`; canonical LIVE revision 1296, source fresh, `workspace_sync=verified`, `cycle_semantics=stale`. This is source evidence, not running-code adoption.
- DIRECT_EVIDENCE: HEAD `97b86d2cfdecaa9672cd8810b73517a4d288693f`; initial `git status --short` was clean. Active backend interpreter: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M07-I1 source anchors remain at `execution/calls.py:8-35`, `execution/state.py:52-70`, and `package_model.py:1473,1882-1889,2163-2171`. The CPython T1 baseline exists and passed again (`7 passed in 2.26s`). The target model test file did not exist before editing.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_function_identity_model.py` exactly as specified. Full new-file diff below.
- Overwrote `walkthrough.md` for this task. No production or existing test file changed; `git diff --name-only` remained empty before the report edit, with only the new untracked test in `git status --short`.

## CPYTHON_BASELINE_REFERENCE

- DIRECT_EVIDENCE: `tests/test_cycle_semantics_function_identity_cpython.py:22-70,72-105,107-169` contains seven isolated CPython cases and keyed assertions. The T1 test passed in this task. It establishes CPython behavior, not model parity.
- DIRECT_EVIDENCE: The new model test imports exactly the T1 `CASES` and assesses synthetic AST modules (`tests/test_cycle_semantics_function_identity_model.py:1-35`).

## MODEL_OUTCOME_MATRIX

DIRECT_EVIDENCE: Model values below come from a read-only invocation of `evaluate_package_import_order` on the exact seven `CASES` inputs. The imported target list includes bootstrap imports. CPython results are from the passing keyed T1 assertions. `CALL_FUNCTION` entries show `(module, symbol)`.

| Case | CPython result | Current model | Current model START_IMPORT targets | Current model CALL_FUNCTION | Parity status |
|---|---|---|---|---|---|
| direct-call | success; old | MODEL_PASS | `pkg`, `pkg.old` | `(pkg, f)` | Observed import effect matches |
| alias-call | success; old | UNKNOWN | `pkg` | none | UNKNOWN; no parity proved |
| alias-survives-rebinding | success; old | UNKNOWN | `pkg` | none | UNKNOWN; no parity proved |
| old-alias-survives-redefinition | success; old | UNKNOWN | `pkg` | none | UNKNOWN; no parity proved |
| new-definition-call | success; new | MODEL_PASS | `pkg`, `pkg.new` | `(pkg, f)` | Observed import effect matches |
| noncallable-rebinding | `TypeError`; neither | UNKNOWN | `pkg` | none | Conservative UNKNOWN; no false PASS |
| foreign-function-cpython-control | success; old | UNKNOWN | `consumer`, `pkg` | none | Conservative foreign-call UNKNOWN |

- CODE_PATH_PROVED: The three same-module alias cases have CPython success but currently stop at UNKNOWN. They are candidates for future MODEL_PASS only if a later independently audited model change establishes the right import effects; this report does not grant PASS.
- CODE_PATH_PROVED: Noncallable rebinding must not become MODEL_PASS under these inputs because the CPython case fails with `TypeError`. The foreign case remains outside the currently authorized model boundary even though CPython succeeds (`execution/calls.py:20-29`; `tests/test_cycle_semantics_package_model.py:2520-2532`).

## OBSERVABLE_EVENT_EVIDENCE

- DIRECT_EVIDENCE: Direct call emits `DEFINE_FUNCTION`, `CALL_FUNCTION(f)`, `START_IMPORT(pkg.old)`; new-definition call emits two `DEFINE_FUNCTION` events, `ALIAS(f,g)`, `CALL_FUNCTION(f)`, `START_IMPORT(pkg.new)`.
- DIRECT_EVIDENCE: Each same-module alias UNKNOWN trace stops after `ALIAS` (and any subsequent `BIND` or second `DEFINE_FUNCTION`), before `CALL_FUNCTION` or child `START_IMPORT`. Noncallable rebinding stops after `BIND(g)`. Foreign call stops after `FROM(pkg,f)` with no `CALL_FUNCTION`.
- CODE_PATH_PROVED: Current helper requires a string marker formed from current module and call target plus a same-name body key (`execution/calls.py:20-35`); alias copying is at `package_model.py:2196-2210`; failed call returns UNKNOWN before event emission (`package_model.py:2163-2181`). No safety is inferred from the absence of a later event.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: T1 preflight: `7 passed in 2.26s`.
- DIRECT_EVIDENCE: Required combined run using the active backend venv: `14 passed in 5.34s` for `tests/test_cycle_semantics_function_identity_cpython.py` and `tests/test_cycle_semantics_function_identity_model.py` with `-q -rs`.
- DIRECT_EVIDENCE: `git diff --check` exited 0. No full pytest, FULL, `update_file`, restart, Git add/commit/push, or index/history modification.

## SEMANTIC_GAPS

- UNKNOWN: A model UNKNOWN is not CPython parity and supplies no permission to report safe import order. The model currently lacks same-module alias call execution; the new test records this current boundary.
- UNKNOWN: Canonical LIVE status for the newly added test was not separately established. The preflight Contextor revision 1296 and source freshness concern the existing owner symbol. No semantic-cycle refresh was requested or performed.

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_function_identity_model.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_function_identity_model.py
@@ -0,0 +1,87 @@
+import ast
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+from test_cycle_semantics_function_identity_cpython import (
+    CASES,
+)
+
+
+@pytest.mark.parametrize(
+    "package_source,consumer_source,expected",
+    CASES,
+)
+def test_current_model_identity_boundary(
+    package_source,
+    consumer_source,
+    expected,
+):
+    sources = {
+        "pkg.__init__": ast.parse(package_source),
+        "pkg.old": ast.parse("pass\n"),
+        "pkg.new": ast.parse("pass\n"),
+    }
+
+    entry = "pkg"
+
+    if consumer_source is not None:
+        sources["consumer"] = ast.parse(consumer_source)
+        entry = "consumer"
+
+    result = evaluate_package_import_order(
+        sources,
+        entry,
+    )
+
+    operations = [
+        event.operation
+        for event in result.events
+    ]
+
+    imported_targets = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+    ]
+
+    assert result.outcome in {
+        "MODEL_PASS",
+        "UNKNOWN",
+    }
+
+    if expected["ok"] is False:
+        assert result.outcome == "UNKNOWN"
+
+    if expected["ok"] is True:
+        assert result.outcome in {
+            "MODEL_PASS",
+            "UNKNOWN",
+        }
+
+    if result.outcome == "MODEL_PASS":
+        assert ("pkg.old" in imported_targets) == (
+            expected["old"]
+        )
+        assert ("pkg.new" in imported_targets) == (
+            expected["new"]
+        )
+
+    assert not (
+        "pkg.old" in imported_targets
+        and "pkg.new" in imported_targets
+        and expected["old"] != expected["new"]
+    )
+
+    assert result.outcome == (
+        "UNKNOWN"
+        if consumer_source is not None
+        else (
+            "UNKNOWN"
+            if "g()" in package_source
+            else "MODEL_PASS"
+        )
+    )
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact seven-case observable model baseline was added and passed alongside the independent CPython baseline. Direct and redefined-current-name calls show matching import effects; three alias cases remain UNKNOWN; the noncallable and foreign cases remain UNKNOWN. This is a baseline report, not a semantic change or model parity certification for UNKNOWN cases. Stop after this stage.
