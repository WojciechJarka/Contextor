# FINAL CORRECTION - LAYER INDEX EXACT COVERAGE

## SUMMARY

Canonical `module_layers` jest available wyłącznie przy exact domain coverage.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\mcp_server.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\walkthrough.md`

## IMPLEMENTATION

- `get_project_architecture`: `set(module_layers) == set(state.modules)`.
- Missing, extra/deleted i non-empty layers dla pustego repo są unavailable.
- Empty modules + empty layers pozostaje available fresh-empty.

## OUT_OF_SCOPE_FINDINGS

- Brak.

## TARGETED_TESTS

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q tests/test_mcp_regressions.py::test_project_architecture_requires_present_complete_module_layers tests/test_mcp_regressions.py::test_project_architecture_rejects_extra_deleted_module_layer
```

Result: `2 passed, 1 warning in 4.80s`. Warning: third-party `AuthlibDeprecationWarning` z `fastmcp`.

## LIVE_VERIFICATION

- Pre-edit revision: `743`.
- `desktop_watcher`: production revision `744` UPDATED; test revision `745` UPDATED.
- Final Contextor revision: `746`.

RESTART MCP

## CONTEXTOR_POST_CHANGE_AUDIT

- implementation: Contextor potwierdzil exact equality w `get_project_architecture` lines 1474-1562.
- consumers/blast_radius: bez zmian; scope ograniczony do layer-index projection i jednego regression.
- dead_or_duplicate_paths: brak.
- canonical_contract: domain keys musza byc identyczne z canonical `state.modules`.
- scope_leakage: brak.
- final_contextor_verdict: PASS.

## FULL_DIFFS

```diff
diff --git a/contextor/mcp_server.py b/contextor/mcp_server.py
--- a/contextor/mcp_server.py
+++ b/contextor/mcp_server.py
@@ -1524,7 +1524,7 @@ def get_project_architecture(
         ):
             candidate_layers = cached_analytics["module_layers"]
-            if not canonical_modules or canonical_modules.issubset(candidate_layers):
+            if set(candidate_layers) == canonical_modules:
                 module_layers = candidate_layers
         if isinstance(module_layers, dict):
             layer_counts: dict[str, int] = {}
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -278,6 +278,27 @@ def test_project_architecture_requires_present_complete_module_layers(
         "truncated": False,
     }
 
 
+def test_project_architecture_rejects_extra_deleted_module_layer(
+    tmp_path, monkeypatch
+):
+    state = RepositoryAnalysisState(
+        modules={"a": object(), "b": object()},
+        cached_analytics_state="fresh",
+        cached_analytics={
+            "module_layers": {"a": "core", "b": "api", "deleted": "legacy"}
+        },
+    )
+    monkeypatch.setattr(
+        mcp_server, "_get_or_init_engine", lambda _root: SimpleNamespace(state=state)
+    )
+
+    result = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))
+
+    assert result["layer_index"]["available"] is False
+
+
 def test_lookup_returns_symbol_facts_when_consumers_are_stale(tmp_path, monkeypatch):
```

## FINAL_VERDICT

PASS
