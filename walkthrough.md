# P5-M08-I10-I2 + R1 + R2 — indexed cross-module decorator

## PREFLIGHT

- **DIRECT_EVIDENCE:** Contextor MCP was queried first. Before R2, canonical LIVE revision was `1381`; both `package_model.py` and `tests/test_cycle_semantics_cross_module_single_decorator.py` had `canonical_state=fresh`, `workspace_sync=verified`, provenance `live`, and no advisory warning.
- **DIRECT_EVIDENCE:** HEAD was `2c68252773c245ab132b01c0813125e0ac590188`; working tree was clean before R2.
- **DIRECT_EVIDENCE:** active `.venv\Scripts\python.exe` is CPython `3.15.2`.
- **CONTRACT_PROVED:** R1's `_RestrictedFunction` import is present at `package_model.py:63-64`; the I10-I2 foreign decorator path remains at `package_model.py:2227-2308`. It checks the exact restricted-function object, foreign defining module membership in `logical_sources` and `programs`, and one parameter; it calls the captured object through `_execute_restricted_object_call`.
- **DIRECT_EVIDENCE:** The three R1 failure anchors were present: C's helper argument at test line 223, G's relative import assertion at lines 249-256, and J's FROM assertion at line 542. Their surrounding contracts matched R2.
- No production or fixture-source changes were made in R2.

## FILES_CHANGED

- `tests/test_cycle_semantics_cross_module_single_decorator.py` — three assertion-only corrections.
- `walkthrough.md` — this report; excluded from source/test diff accounting.
- The I10-I2 and R1 production changes are already in HEAD; they were not modified in R2.

## C_ALIAS_EXPECTATION_CORRECTION

- The CPython reference continues to trace exported decorator `identity`; the indexed `FROM` assertion continues to require symbol `identity`.
- Only the model-call expectation is alias-aware: C passes `alias` to `_single_imported_decorator_contract` because the source applies `@alias`.
- **DIRECT_EVIDENCE:** the C model result is `MODEL_PASS`; its event sequence contains `CALL_FUNCTION(alias)` followed by `CALL_FUNCTION(f)`. The corrected test passes.

## G_FUNCTION_LOCAL_FROM_CORRECTION

- The fixture remains `from .effect import ORIGIN`.
- The G assertion now reads `FUNCTION_LOCAL_FROM`, while preserving target `pkg.decorators.effect`, module `pkg.decorators`, the start-import ordering checks, and the negative check for `pkg.effect`.
- **DIRECT_EVIDENCE:** the model emitted `START_IMPORT(target='pkg.decorators.effect', module='pkg.decorators')` and `FUNCTION_LOCAL_FROM(target='pkg.decorators.effect', symbol='ORIGIN', module='pkg.decorators')`. The corrected test passes.

## J_EARLY_COMPILER_REJECTION_CORRECTION

- The test still requires `modeled.outcome == "UNKNOWN"`.
- It now requires `modeled.events == ()`, matching the existing class compiler admission gate. That gate requires ordinary named class decorators to have an earlier local `DEFINE_FUNCTION` (`package_model.py:848-861`); otherwise `_compile` returns `None` before import-order simulation.
- The compiler gate and production behavior were not changed.

## CROSS_MODULE_CALL_EVIDENCE

- The I10-I2 single-decorator path remains limited to one indexed `_RestrictedFunction` from a different module with one parameter. The same-module path and helper provenance checks remain unchanged.
- The original I10-I2 gate first failed with 17 failures due to the missing `_RestrictedFunction` import. R1 added the exact import line; its gate then exposed the three test expectation errors corrected here.
- The final R2 first gate and regression subset both pass. The production implementation was not changed in R2.

## DEFINING_MODULE_EXECUTION

- B's indexed `pkg.effect` import is reported as a function-local import from `pkg.decorators` during application of the decorator.
- G's relative from-import resolves to indexed child `pkg.decorators.effect` from `pkg.decorators`, not the distractor `pkg.effect`.

## APPLYING_MODULE_BINDING

- A, B, C, and G retain a callable final `f`; their tests invoke `f()` after decoration.
- D's bare-return decorator binds `f` to `None`; definition-only modeling passes and a subsequent `f()` remains `UNKNOWN`.
- The existing `binding_module` result-owner mechanism in I10-I1 remains unchanged.

## CPYTHON_PARITY_MATRIX

| Case | CPython 3.15.2 reference | Model result |
|---|---|---|
| A imported identity | Import succeeds; one decorator call; `f` remains the same callable object. | `MODEL_PASS`; targeted test passes. |
| B indexed effect | Imports `pkg.decorators`, then `pkg.effect`; decorator receives and returns `f`. | `MODEL_PASS`; effect event runs under `pkg.decorators`; targeted test passes. |
| C imported alias | Alias applies the imported identity decorator; `f` remains the same callable object. | `MODEL_PASS`; `CALL_FUNCTION(alias)` then `CALL_FUNCTION(f)`; corrected test passes. |
| D bare return | Decorator binds `f` to `None`; later invocation raises `TypeError`. | Definition `MODEL_PASS`; later invocation `UNKNOWN`; targeted test passes. |
| G relative import | Relative effect module is `pkg.decorators.effect`; decorated `f` remains callable. | `MODEL_PASS`; corrected `FUNCTION_LOCAL_FROM` assertion passes. |

## FIRST_GATE_RESULTS

- Command: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py -rs`
- **DIRECT_EVIDENCE:** `35 passed in 7.62s`.

## FULL_TARGETED_RESULTS

- Command: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_stacked_decorator_identity.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_decorator_snapshots.py tests/test_cycle_semantics_package_model.py -rs`
- **DIRECT_EVIDENCE:** `317 passed in 26.65s`.
- `git diff --check` exited `0`. Git printed only its working-copy LF-to-CRLF notice for the changed test file.
- The first check of the assembled report caught three whitespace-only lines in its embedded diff; they were removed, and the final `git diff --check` then exited `0`.

## MCP_POST_CHANGE_AUDIT

- **DIRECT_EVIDENCE:** canonical LIVE revision `1382`, provenance `live`; both the changed test source and `package_model.py` report `canonical_state=fresh`, `workspace_sync=verified`, and no advisory warning.
- **DIRECT_EVIDENCE:** syntax error count `0`.
- **DIRECT_EVIDENCE:** package_model dependency directions are complete: 12 outbound hard dependencies (including the existing `execution.calls` dependency) and 42 inbound dependencies. R2 changes only test assertions, so no production dependency direction changed.
- **DIRECT_EVIDENCE:** structural DFS cycle count `16`, with Contextor semantics `DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES`; this is not a count of every simple cycle.
- `cycle_semantics` family remains marked stale. No semantic refresh was requested or performed.
- No FULL, SCC02, full pytest, `update_file`, backend restart, Git staging, commit, push, index mutation, or history mutation was performed.

## FULL_DIFFS

All current uncommitted source/test changes relative to HEAD are shown below. R2 changed only the three test expectations; the I10-I2/R1 implementation is already present in HEAD. The walkthrough itself is the report artifact and is excluded from this diff.

```diff
diff --git a/tests/test_cycle_semantics_cross_module_single_decorator.py b/tests/test_cycle_semantics_cross_module_single_decorator.py
index e130e2b..69647b4 100644
--- a/tests/test_cycle_semantics_cross_module_single_decorator.py
+++ b/tests/test_cycle_semantics_cross_module_single_decorator.py
@@ -223 +223 @@ def test_indexed_single_decorator_matches_cpython_and_binds_result(
-        decorator_name,
+        "alias" if case == "C" else decorator_name,
@@ -252 +252 @@ def test_indexed_single_decorator_matches_cpython_and_binds_result(
-            for event in local_imports
+            for event in _events(modeled, "FUNCTION_LOCAL_FROM")
@@ -542 +542 @@ def test_imported_class_decorator_remains_unknown():
-    assert any(event.operation == "FROM" for event in modeled.events)
+    assert modeled.events == ()
```

## FINAL_VERDICT

**FINAL PASS for the requested I10-I2/R1/R2 targeted scope.** All three exact test corrections pass the first gate, the full specified targeted subset, `git diff --check`, and the required Contextor post-change audit. No production behavior changed in R2.
