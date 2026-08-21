# TOKEN EFFICIENCY — STEP A2.3.1: CLOSE MISSING GET_PROJECT_ARCHITECTURE REGRESSION EVIDENCE

## FILES_CHANGED=NONE

---

## COMMAND

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_mcp_regressions.py::test_project_architecture_marks_analytics_families_unavailable
```

---

## RESULT

```text
ERROR: not found: C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_project_architecture_marks_analytics_families_unavailable
(no match in any of [<Module test_mcp_regressions.py>])
```
**Exit Code: 1**

---

## FAILURE_CLASSIFICATION

- **Klasyfikacja:** `TEST_DRIFT / INVALID_NODE_ID`
- **Przyczyna:** Test o nazwie `test_project_architecture_marks_analytics_families_unavailable` nie istnieje w pliku `tests/test_mcp_regressions.py`.
- **Rzeczywisty test kontraktu:** Testem weryfikującym niedostępność rodzin analitycznych (`action_items`, `top_global_hotspots`, `debt_summary`) oraz poprawność pełnego formatu `layer_index.items` przy `compact=False` jest:
  `tests/test_mcp_regressions.py::test_stale_layer_snapshot_is_not_presented_after_incremental_update` (linie 157–215).
  Test ten został już wykonany w kroku A2.3 i zakończył się wynikiem **PASS**.

---

## STEP_VERDICT

`FIX_REQUIRED` *(niepoprawny selektor test node ID)*

---

## NEXT_STEP_PROPOSAL

**STEP A2.3.2 — run actual existing test `tests/test_mcp_regressions.py::test_stale_layer_snapshot_is_not_presented_after_incremental_update` or proceed directly to STEP A2.4 — post-restart get_project_architecture runtime certification.**
