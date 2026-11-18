# SP-T4-I2B5-I4B-T67 — fail-closed przed no-op

## PREFLIGHT

- **DIRECT_EVIDENCE:** Contextor MCP source range pokazał koniec `tests/test_p1d3_d2b2_type_only.py` na T66 (`source_total_lines=4846`); T67 nie istniał. Engine freshness envelope w preflight wskazywał revision `1451`, `provenance=live`, `workspace_sync=verified`.
- **DIRECT_EVIDENCE:** `FileDelta.is_empty` zwraca `True`, gdy nie ma zmian membership, importów, artefaktów ani metadanych.
- **CODE_PATH_PROVED:** przy invalid baseline helper działa fail-closed. Gdy zmienia importy zachowanego modułu, planner rozszerza plan o `modules`/`dependency_graph`; wtedy semantic no-op warunek widzi rozszerzony plan i przepuszcza operację do executora mimo `delta.is_empty=True`.
- **DIRECT_EVIDENCE:** HEAD przed zmianą: `7ae3c229d91303cc1736fbd296be221aefefae16`; working tree czysty, plik testowy bez wcześniejszego diffu. Interpreter: CPython 3.15.2.

## CHANGE

- Dopisano na końcu dokładnie jeden test `test_sp_t4_i2b5_i4b_t67_invalid_baseline_noop` zgodnie z podanym ciałem.
- Nie zmieniono kodu produkcyjnego, istniejących asercji, helperów ani monkeypatchy.
- **DIRECT_EVIDENCE:** finalny Git diff zawiera wyłącznie dopisany test T67.
- **NOTATKA WYKONAWCZA:** pierwszy anchor patcha był niejednoznaczny i tymczasowo umieścił test przed końcem pliku. Błąd wykryto przed uruchomieniem testów, tę kopię usunięto i dopisano T67 za unikalnym ogonem T66. Przywrócono też jedną pustą linię T63 do stanu bazowego. Finalny diff potwierdza brak zmian istniejących testów. Feed MCP odnotował pośrednie zdarzenia pliku; końcowy stan potwierdzono osobno na revision `1455`.

## TESTS

Uruchomiono wyłącznie wskazane testy, na CPython 3.15.2, w dwóch parach i kolejności z promptu.

Pierwsza para: T67, następnie T66.

```text
2 passed in 5.90s
```

Druga para: T62, następnie T65.

```text
2 passed in 2.97s
```

| Test | Wynik |
|---|---|
| T67 `invalid_baseline_noop` | PASS |
| T66 `noop_evidence_refresh` | PASS |
| T62 `engine_global_reclassification` | PASS |
| T65 `invalid_baseline_fails_closed` | PASS |

Brak tracebacków. Nie uruchamiano innych testów, pełnego pytest ani FULL.

## T67 EVIDENCE

- **DIRECT_EVIDENCE:** T67 przechodzi z `result.delta.is_empty is True` i `result.status == "UPDATED"`.
- **DIRECT_EVIDENCE:** po update evidence pozostaje `{}`, guarded import jest `type_only=False`, a `pkg.b` przechodzi z soft edge do hard edge.
- **DIRECT_EVIDENCE:** nowe `modules` i `dependency_graph` mają inną tożsamość. Zachowane referencje `before_modules`/`before_graph` nadal mają `type_only=True` i soft edge.
- **INFERENCE:** w tym świadku status `UPDATED` wynika z planu poszerzonego przez fail-closed reclassyfikację, mimo pustego surowego `FileDelta`; asercje T67 oraz ścieżka helper→planner→executor są z tym zgodne.
- **LIMITATION:** jest to jeden syntetyczny świadek `_I1_SAFE`; nie dowodzi zachowania dla wszystkich postaci repozytoriów ani wszystkich zmian źródeł, które dają pusty `FileDelta`.

## MCP POST-CHANGE AUDIT

- **DIRECT_EVIDENCE:** końcowy event `desktop_watcher`, `operation=update_file`, `status=UPDATED` dla pliku testowego, revision `1455`; continuity=`continuous`, `resync_required=false`, `resync_reason=null`; `blast_radius_state=deferred`, affected modules=0.
- **DIRECT_EVIDENCE:** MCP odczytał pełny T67 z `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`, revision `1455`.
- **DIRECT_EVIDENCE:** syntax diagnostics=0/fresh; graph/module/topology/artifact-consumption/cycles/collisions/lineage families fresh. Cycles=16/fresh; cycle warning view fresh, active warnings=16. `cycle_semantics=stale`.
- Źródło zostało zsynchronizowane przez watcher; `update_file` MCP nie wywoływano. Restartu nie wykonywano.

## FINAL VERDICT

**T67_PASS** — dodany test i pozostałe wskazane testy przeszły; końcowy source jest verified w LIVE. Zakres pozostaje ograniczony do T67 i wskazanego subsetu.

## FILES_CHANGED

- `tests/test_p1d3_d2b2_type_only.py` — jedyny zmieniony plik testowy.
- `walkthrough.md` — wymagany raport; bez własnego diffu.

## FULL_DIFFS

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 09eabef..74448b5 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4844,3 +4844,55 @@ def test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh(
         engine.state
     ).type_only is True
 
+
+def test_sp_t4_i2b5_i4b_t67_invalid_baseline_noop(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    before_modules = engine.state.modules
+    before_graph = engine.state.dependency_graph
+
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+
+    engine.state.typing_guard_evidence = {}
+
+    target = root / "pkg/c.py"
+    with target.open("a", encoding="utf-8") as stream:
+        stream.write("\n# evidence fallback\n")
+
+    result = engine.update_file(str(target.resolve()))
+
+    assert result.delta.is_empty is True
+    assert result.status == "UPDATED"
+
+    assert engine.state.typing_guard_evidence == {}
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is False
+
+    assert "pkg.b" in (
+        engine.state.dependency_graph
+        .hard_edges["pkg.a"]
+    )
+    assert "pkg.b" not in (
+        engine.state.dependency_graph
+        .soft_edges["pkg.a"]
+    )
+
+    assert engine.state.modules is not before_modules
+    assert engine.state.dependency_graph is not before_graph
+
+    before_guarded = next(
+        ref for ref in before_modules["pkg.a"].imports
+        if ref.module == "pkg.b"
+    )
+    assert before_guarded.type_only is True
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+
```
