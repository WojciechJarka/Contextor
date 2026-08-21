# MCP SPLIT FINAL AUDIT — STEP 6A.2: APPLY EXACT F-02 TEST FIX

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`

---

## ACTUAL_DIFF

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index df376a6..5540bb3 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -1009,6 +1009,11 @@ def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
     )
     monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
     monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: True)
+    monkeypatch.setattr(
+        update_file_module,
+        "_mcp_runtime_restart_required",
+        lambda _path: False,
+    )
 
     current = json.loads(
         mcp_server.update_file.fn(repo_path=str(repo), file_path=str(server_path))
@@ -1016,7 +1021,11 @@ def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
     assert current["runtime_restart_required"] is False
     assert "runtime_state" not in current
 
-    monkeypatch.setattr(update_file_module, "_MCP_SERVER_SOURCE_FINGERPRINT", "stale")
+    monkeypatch.setattr(
+        update_file_module,
+        "_mcp_runtime_restart_required",
+        lambda _path: True,
+    )
     result = json.loads(
         mcp_server.update_file.fn(repo_path=str(repo), file_path=str(server_path))
     )
```

---

## TARGETED_TEST_RESULT

Komenda:
```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_mcp_regressions.py::test_update_file_marks_running_mcp_server_as_requiring_restart
```

Wynik:
```text
.                                                                        [100%]
1 passed, 1 warning in 15.83s
```
**Status: 1 PASSED (Exit code: 0)**

---

## STEP_VERDICT

`PASS`

---

## NEXT_STEP_PROPOSAL

**STEP 7: Full Suite Regression Run (S2A–S2E + Regressions) & Final Release Certification**
- Uruchomić pełny zestaw testów architektury modularnej MCP (`test_mcp_split_s2a.py` .. `test_mcp_split_s2e.py`).
- Uruchomić testy integracji i hydratacji MCP (`test_mcp_incremental_hydration.py`, `test_mcp_regressions.py`).
- Wygenerować finalny certyfikat wydania po zakończeniu podziału MCP na 21 dedykowanych narzędzi.
