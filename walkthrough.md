# P14-I2 — rzeczywisty hazard po IMPORT_NAME

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `816592a8d9b3c1ed92be8f3c24c2ba1de89393f1`; worktree przed zmianą czysty. Contextor MCP `get_module_context` dla `tests/test_cycle_semantics_initialization_model.py` i `contextor/core/cycle_semantics/initialization_model.py`: LIVE revision 1567, `canonical_state=fresh`, `workspace_sync=verified`, `cycle_semantics=stale`. `get_source_range` potwierdził starą funkcję testową w `tests/test_cycle_semantics_initialization_model.py:259-272`. Pierwsza próba zakresu 255–280 była poza końcem pliku (272 linie); poprawny odczyt wykonałem po sprawdzeniu granicy. Produkcyjny `initialization_model.py:183-198` już zawiera transfer `aliases[target].get(step.symbol)`.
- Nie czytano `issues.md`. Bez FULL, restartu i operacji zapisu Git.

## EXACT_TEST_CORRECTION

- Zastąpiono wyłącznie `test_from_import_module_identity_detects_later_hazard` w `tests/test_cycle_semantics_initialization_model.py:259-302`. Pozostałe testy i kod produkcyjny niezmienione. Nowa próbka sprawdza udane `IMPORT_NAME c.root` przed hazardem `a.value`, a nie brak `a_ref` podczas wcześniejszego from-import.

## SEMANTIC_EVIDENCE

- CODE_PATH_PROVED: `a` inicjuje `b` przed związaniem `value`; `b` inicjuje `c`; `c` wykonuje `import a as root` przy stanie INITIALIZING. `initialization_model.py:179-194` nie rozpoczyna drugiej ramki `a` i zapisuje `aliases[c]['root']='a'`. `b` po `from c import root as x` przenosi tę tożsamość przez `:183-198`. `READ_ATTRIBUTE x.value` rozwiązuje `target='a'` (`:203-206`), a brak `value` przy INITIALIZING daje `EARLY_BINDING_HAZARD` (`:207-220`). Wcześniejszy test kończył się na brakującym `a_ref`, więc nie wykonywał transferu tożsamości.
- DIRECT_EVIDENCE: asercja modelu potwierdziła `(outcome,target_module,symbol)=(EARLY_BINDING_HAZARD,a,value)` oraz istotną kolejność eventów `IMPORT_NAME(c,root) → EARLY_BINDING_HAZARD(a,value)`; bez udanego `READ_ATTRIBUTE`. To jest brak pierwszego atrybutu, więc interpreter nie emituje eventu udanego odczytu.

## CPYTHON_PARITY

- DIRECT_EVIDENCE: `_actual(tmp_path,sources,'a',return_process=True)` uruchamia osobny proces `sys.executable -I -B -c` (`tests/test_cycle_semantics_initialization_model.py:20-33`). Test potwierdził niezerowy returncode i końcowy `AttributeError` zawierający `partially initialized module 'a'` oraz `has no attribute 'value'`. Przedmiotem zgodności jest moduł a i symbol value, nie sam fakt błędu. Test nie porównuje pełnej kolejności wewnętrznych wywołań importlib; modelową kolejność sprawdza jawna asercja eventów.

## TARGETED_TESTS

- Zmieniony test: `1 passed in 0.93s`.
- `tests/test_cycle_semantics_initialization_model.py`, `tests/test_cycle_semantics_scenarios.py`, `tests/test_cycle_semantics_evidence.py`: `129 passed in 4.27s`. Bez pełnego pytest.

## MCP_POST_CHANGE

- DIRECT_EVIDENCE: `get_live_events(after_revision=1567)` zwrócił `desktop_watcher UPDATED` dla pliku testowego na revision 1568, ciągłość `continuous`, `resync_required=false`. Nie użyto `update_file`.
- DIRECT_EVIDENCE: `get_module_context` pliku testowego i niezmienionego produkcyjnego po zmianie: LIVE 1568, `canonical_state=fresh`, `workspace_sync=verified`, provenance live. Rodzina `cycle_semantics=stale`, więc nie jest to dowód przeliczenia semantyki ani runtime safety. Końcowy `git status --short` pokazuje wyłącznie `M tests/test_cycle_semantics_initialization_model.py` przed zapisem tego raportu.

## FULL_DIFFS

### tests/test_cycle_semantics_initialization_model.py — pełny ACTUAL_DIFF

```diff
diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
index ffd0ce9..00d104f 100644
--- a/tests/test_cycle_semantics_initialization_model.py
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -259,14 +259,44 @@ def test_from_import_ordinary_binding_does_not_gain_module_identity():
 def test_from_import_module_identity_detects_later_hazard(tmp_path):
     sources = {
         "a": "import b\nvalue = 3\n",
-        "b": "from a import a_ref as x\ny = x.value\n",
+        "b": "from c import root as x\ny = x.value\n",
+        "c": "import a as root\n",
     }
-    # Brak a_ref zatrzymuje import nazwy przed READ_ATTRIBUTE.
+
     result = _assess(sources, "a")
-    assert (result.outcome, result.target_module, result.symbol) == (
-        "EARLY_BINDING_HAZARD", "a", "a_ref"
+
+    assert (
+        result.outcome,
+        result.target_module,
+        result.symbol,
+    ) == (
+        "EARLY_BINDING_HAZARD",
+        "a",
+        "value",
     )
-    assert not any(
-        event.operation == "READ_ATTRIBUTE"
+
+    assert [
+        (event.operation, event.target, event.symbol)
         for event in result.events
+        if event.operation in {
+            "IMPORT_NAME",
+            "READ_ATTRIBUTE",
+            "EARLY_BINDING_HAZARD",
+        }
+    ] == [
+        ("IMPORT_NAME", "c", "root"),
+        ("EARLY_BINDING_HAZARD", "a", "value"),
+    ]
+
+    process = _actual(
+        tmp_path,
+        sources,
+        "a",
+        return_process=True,
+    )
+
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'a'" in exception_line
+    assert "has no attribute 'value'" in exception_line
```

## FINAL_STATUS

- Test skorygowany zgodnie z rzeczywistym kontraktem i zgodnością CPython; 129 wskazanych testów przechodzi, oba źródła `workspace_sync=verified` na LIVE 1568. Nie zgłaszam globalnego FINAL PASS cycle semantics, gdyż rodzina pozostaje stale. Bez zmian produkcji, commit/push/staging/restart.
- FILES_CHANGED: `tests/test_cycle_semantics_initialization_model.py` (oraz `walkthrough.md` jako raport); pełny diff pliku testowego powyżej.
