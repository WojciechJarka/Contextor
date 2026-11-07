# CONTEXTOR C16-B03-P1D3G17-R1 — TWO-TEST CONTRACT CORRECTION

## IMPLEMENTATION

FILES_CHANGED: `tests/test_cycle_semantics_package_model_async_alias.py`; `tests/test_cycle_semantics_package_model.py`. Contextor MCP was used first and both target modules reported canonical revision 1080, fresh state, verified workspace sync. Pre-edit HEAD `94755750d68024c7f57f241b39814a0c007f47a3`; worktree was clean. Both specified anchors matched once. No production code or other test was changed.

## TWO_CONTRACT_CORRECTIONS

In `test_async_body_is_not_executed`, replaced the blanket ban on `START_IMPORT` with an assertion that the opaque async definition was recorded and no event targets `missing_external_xyz`. This distinguishes entry package/module loading from the deferred async body. In `test_b0g4c5_definition_effects_updated_contract`, changed only the `async def f():\n    import pkg.child` sample's expected outcome from `UNKNOWN` to `MODEL_PASS`. All other samples and assertions remain unchanged.

## TARGETED_TESTS

CPython 3.15.2, `PYTHONDONTWRITEBYTECODE=1`, `-B -m pytest -q -rs -p no:cacheprovider`, external `--basetemp C:\Temp\Contextor_G17_R1_pytest_tmp`. Ran exactly the five specified modules: async_alias, literals, annotations315, package_model, optional_child_scenarios. Result: **219 passed in 24.38s**, 0 failed, exit 0. No full suite.

## MCP_POST_CHANGE_AUDIT

Read-only Contextor MCP for both edited tests: canonical revision 1082, `canonical_state=fresh`, `workspace_sync=verified`, advisory_warning null, syntax errors 0, structural DFS cycles 16 (fresh), active_warning_count 16, model_pass_count 0, `cycle_semantics=stale`. Read-only canonical snapshot at revision 1082 has no optional /3 receipt. No production FULL, restart, update_file, warning suppression edit, or manual commit.

## FULL_DIFFS

Complete actual diffs for both changed test files follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 6f17c1e..da99426 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1199,7 +1199,7 @@ def test_b0g4c5_definition_effects_updated_contract():
         ),
         (
             "async def f():\n    import pkg.child",
-            "UNKNOWN",
+            "MODEL_PASS",
         ),
         (
             "def f():\n    return 1",
diff --git a/tests/test_cycle_semantics_package_model_async_alias.py b/tests/test_cycle_semantics_package_model_async_alias.py
index 5d0dbcf..5897cb8 100644
--- a/tests/test_cycle_semantics_package_model_async_alias.py
+++ b/tests/test_cycle_semantics_package_model_async_alias.py
@@ -43,7 +43,11 @@ def test_async_body_is_not_executed():
         "    import missing_external_xyz\n"
     )
     assert result.outcome == "MODEL_PASS"
-    assert "START_IMPORT" not in _operations(result)
+    assert "DEFINE_OPAQUE_FUNCTION" in _operations(result)
+    assert not any(
+        event.target == "missing_external_xyz"
+        for event in result.events
+    )
 
 
 def test_annotated_async_definition_deferred():
```

## FINAL_VERDICT

PASS — both corrections are literal, all 219 targeted tests pass, source code is unchanged, structural cycles remain 16, and no optional /3 receipt exists.
