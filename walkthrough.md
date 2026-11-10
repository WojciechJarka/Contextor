# P5-M05-I2 — Execution cursor extraction

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `6ba17c205ae6d519ecf38c32cfd9e597cc89baab`; initial `git status --short` showed only ` M walkthrough.md` from the previous report. That report was replaced as required; no pre-existing production/test changes were overwritten.
- DIRECT_EVIDENCE: Contextor MCP canonical LIVE revision 1272 before edit; `package_model.py` and `execution/state.py` both had `canonical_state=fresh`, `workspace_sync=verified`; `cycle_semantics=stale`. Backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072).
- DIRECT_EVIDENCE: Current `package_model.py:1575-1576` contained exact bootstrap/frame initialization; `:1596,1602-1606` contained exact budget and loop blocks. Literal search found no other `step_budget` references or `frames` rebinding within the evaluator. `execution/state.py:1-25` matched the expected existing content.
- CODE_PATH_PROVED: Semantic-integrity review: factory returns a new list containing the same bootstrap tuple and a budget of 10000; loop still decrements once before testing the same threshold; frame operations keep the same list alias. No operation or ordering branch was changed. Existing targeted tests include positive/negative import order and CPython-backed class/decorator regressions, though this structural result does not certify the restricted model generally.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/state.py` — appended exact cursor dataclass and factory.
- `contextor/core/cycle_semantics/package_model.py` — imported factory and replaced local frame/budget initialization and budget accesses.
- `walkthrough.md` — this report, exempt from production/test FULL_DIFF accounting.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: `_ExecutionCursor` and `_new_execution_cursor` were appended after two blank lines to `state.py`, without changing its earlier definitions. `package_model.py` keeps `bootstrap="\\x00ENTRY"`, binds `frames=execution_cursor.frames`, and decrements/checks `execution_cursor.step_budget` in the same loop location. Full task diffs are below.

## CURSOR_ISOLATION_CHECKS

- CONTRACT_PROVED: Using the active backend venv interpreter, the supplied assertions passed: exact cursor class, independent frame lists and budgets for two instances, mutation isolation, and unchanged `__module__` values for `_compile` and `evaluate_package_import_order`. Output `CURSOR_ISOLATION_CHECKS=PASS`; exit 0.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Exact six-file backend venv command `-m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_f1h_runtime_attestation.py -rs` → **410 passed, 2 third-party deprecation warnings in 42.86 s**. SCC02 was excluded as specified; its two previously observed failures remain separate and unresolved.
- DIRECT_EVIDENCE: `git diff --check` exited 0 with no whitespace-error output. Git's LF/CRLF advisory was not a diff-check failure.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Contextor canonical LIVE revision advanced 1272 → 1274. `package_model.py` and `execution/state.py` have `workspace_sync=verified`, fresh canonical module/graph/topology, and zero syntax errors. The existing hard dependency `package_model → execution.state` remains; `execution.state` has zero outbound hard edges. No new hard edge appears in the module's outbound list.
- DIRECT_EVIDENCE: Hard structural cycle diagnostic **16 normalized DFS back-edge paths**; active warning count **16**. `cycle_semantics` family remains stale.
- UNKNOWN: Current cyclic SCC count was not exposed by the selected LIVE queries. Verified source/workspace sync does not establish adoption by every running process; no restart was performed.

## FULL_DIFFS

### `contextor/core/cycle_semantics/execution/state.py`

```diff
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index f26e7cd..fca6811 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -23,3 +23,18 @@ def _new_module_initialization_state(
             for name in programs
         },
     )
+
+
+@dataclass
+class _ExecutionCursor:
+    frames: list[tuple[str, int]]
+    step_budget: int
+
+
+def _new_execution_cursor(
+    bootstrap: str,
+) -> _ExecutionCursor:
+    return _ExecutionCursor(
+        frames=[(bootstrap, 0)],
+        step_budget=10000,
+    )
```

### `contextor/core/cycle_semantics/package_model.py`

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 8a7071c..efcd6cd 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -35,7 +35,10 @@ from .execution.definition_checks import (
     _exact_restricted_dataclass_hash_field_call,
     _restricted_dataclass_field_annotation,
 )
-from .execution.state import _new_module_initialization_state
+from .execution.state import (
+    _new_module_initialization_state,
+    _new_execution_cursor,
+)
 
 
 @dataclass(frozen=True)
@@ -1573,7 +1576,8 @@ def evaluate_package_import_order(
     }
 
     bootstrap = "\x00ENTRY"
-    frames: list[tuple[str, int]] = [(bootstrap, 0)]
+    execution_cursor = _new_execution_cursor(bootstrap)
+    frames = execution_cursor.frames
 
     def chain(name: str) -> tuple[str, ...]:
         parts = name.split(".")
@@ -1593,16 +1597,15 @@ def evaluate_package_import_order(
 
         return None
 
-    step_budget = 10000
     indexed_roots = frozenset(
         name.split(".", 1)[0]
         for name in programs
     )
 
     while frames:
-        step_budget -= 1
+        execution_cursor.step_budget -= 1
 
-        if step_budget < 0:
+        if execution_cursor.step_budget < 0:
             return result("UNKNOWN")
 
         module, index = frames[-1]
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact structural extraction, cursor isolation and specified focused tests passed. Contextor source/graph audit is fresh at revision 1274; `cycle_semantics` remains stale, so no fresh semantic classification or process-adoption claim is made. STOP after implementation and audit.
