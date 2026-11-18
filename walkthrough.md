# SP-T4-I2B5-I4B-I1B — korekta T06

## PREFLIGHT

- **DIRECT_EVIDENCE:** HEAD przed zmianą: `b88ee3cad7f61ee1ed4a0e49254da535a134ae18`; working tree był czysty. Plik testowy nie miał wcześniejszego diffu.
- **DIRECT_EVIDENCE:** interpreter `.venv\Scripts\python.exe`: CPython 3.15.2.
- **DIRECT_EVIDENCE:** Contextor MCP przed zmianą wskazał canonical revision `1448`, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified` dla `tests/test_p1d3_d2b2_type_only.py`. Syntax diagnostics: 0/fresh; graph i cycles: fresh; cycles=16; `cycle_semantics=stale`; `resync_required=false`.
- **DIRECT_EVIDENCE:** MCP odczytał funkcję `test_sp_t4_i1_t06_updated_invalidates_evidence`, linie 2722–2736. W jej bloku występowała dokładnie wskazana asercja `assert engine.state.typing_guard_evidence == {}`. W pliku są dwie dalsze takie asercje poza T06; nie zmieniono ich.

## EXACT CHANGE

- Zmieniono tylko wskazaną asercję T06 na asercje `schema_version == 2` oraz `global_policy_satisfied is True`.
- Nie zmieniono nazwy T06, pozostałych asercji, helperów ani kodu produkcyjnego.
- **CONTRACT_PROVED (zakres testowy):** nowy oczekiwany stan evidence jest zgodny z kontraktem integracji I4B-I1 polegającym na zachowaniu zaktualizowanego schema-v2 evidence. Pięć wskazanych testów publicznego przepływu potwierdziło ten zestaw oczekiwań w tym ograniczonym zakresie.
- **WĄTPLIWOŚĆ / INFERENCE:** nazwa `updated_invalidates_evidence` sugeruje zerowanie/inwalidację, podczas gdy nowe asercje wymagają zachowanego evidence. Nazwa jest semantycznie nieaktualna; zachowano ją zgodnie z literalnym zakazem zmiany nazwy. Nie zmieniano żadnego testu poza T06.

## TARGETED TESTS

Uruchomiono wyłącznie T06, T62, T63, T64 i T65:

```text
& .\.venv\Scripts\python.exe -m pytest -q --tb=long tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i1_t06_updated_invalidates_evidence tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t62_engine_global_reclassification tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t63_consecutive_updates tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t64_deletion_restores_soft tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed
```

```text
.....                                                                    [100%]
5 passed in 10.36s
```

- T06, T62, T63, T64, T65: PASS.
- Brak tracebacków.
- Nie uruchamiano pełnego pytest ani FULL.
- **LIMITATION:** wynik dotyczy wyłącznie pięciu wskazanych testów; nie stanowi samodzielnego dowodu ogólnej semantyki dla dowolnych repozytoriów Python.

## MCP POST-CHANGE AUDIT

- **DIRECT_EVIDENCE:** po krótkim oczekiwaniu pojawił się event `desktop_watcher`, `operation=update_file`, `status=UPDATED` dla zmienionego pliku, revision `1449`. `continuity=continuous`, `resync_required=false`, `resync_reason=null`; `blast_radius_state=deferred`, `affected_modules.total=0`.
- **DIRECT_EVIDENCE:** MCP odczytał zmieniony T06 przy revision `1449`, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified`.
- **DIRECT_EVIDENCE:** syntax diagnostics `0/fresh`; graph/module/topology/artifact-consumption/cycles/collisions/lineage families fresh. Cycles=16/fresh; aktywne ostrzeżenia cykli=16, warning view fresh. `cycle_semantics=stale`.
- **LIMITATION:** event i `workspace_sync` potwierdzają synchronizację źródła w LIVE. Nie dowodzą adopcji kodu przez proces; zmieniono test, restartu nie wykonywano ani nie wymagano.

## FINAL VERDICT

**I4B_I1B_PASS** dla dokładnej korekty testu: wskazany fragment zmieniono, pięć wymaganych testów przeszło, a MCP potwierdził synchronizację pliku. Zakres nie obejmuje pełnego suite ani nowej walidacji produkcji.

## FILES_CHANGED

- `tests/test_p1d3_d2b2_type_only.py` — jedyny zmieniony plik testowy.
- `walkthrough.md` — wymagany raport; nie jest liczony jako plik produkcyjny/testowy i nie zawiera własnego diffu.

## FULL_DIFFS

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 39435a5..c53f911 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -2730,7 +2730,12 @@ def test_sp_t4_i1_t06_updated_invalidates_evidence(tmp_path, isolated_dirs):
     target.write_text("pass\nVALUE = 2\n", encoding="utf-8")
     result = engine.update_file(str(target.resolve()))
     assert result.status == "UPDATED"
-    assert engine.state.typing_guard_evidence == {}
+    assert engine.state.typing_guard_evidence[
+        "schema_version"
+    ] == 2
+    assert engine.state.typing_guard_evidence[
+        "global_policy_satisfied"
+    ] is True
     assert _i1_guarded_import(engine.state).type_only == before_import.type_only
     assert engine.state.dependency_graph.hard_edges == before_hard
     assert engine.state.dependency_graph.soft_edges == before_soft
```
