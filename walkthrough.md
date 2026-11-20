# P6-D04-I1-R2 — EXACT PACKAGE FIXTURE CORRECTION

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP przed zmianą:** LIVE revision 1464, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}; globalne syntax_errors=0 (fresh). Agregat workspace_sync=unverified nie potwierdza synchronizacji wszystkich plików.
- **DIRECT_EVIDENCE — lokalny precheck:** HEAD f622f1e645987cbc179efacf16a4c7e98928cc9b; git status --short był pusty. Dokładny anchor był w tests/test_cycle_semantics_default_definition_effects.py:89–95. Interpreter .venv/Scripts/python.exe --version zgłosił Python 3.15.2.
- **DIRECT_EVIDENCE — źródła Contextor:** contextor/core/cycle_semantics/package_layout.py::build_package_layout, linie 54–124, oraz contextor/core/cycle_semantics/package_model.py::evaluate_package_import_order i _safe_passive_function_definition miały workspace_sync=verified przy rev 1464.

## EXACT_CHANGE

- Zmieniono wyłącznie wskazany klucz mapy wejściowej w teście: "pkg" → "pkg.__init__".
- CASES, parametry, asercje i kod produkcyjny pozostały bez zmian. Pełny rzeczywisty diff znajduje się w FULL_DIFFS.
- walkthrough.md nadpisano zgodnie z wymaganym raportem.

## TARGETED_RESULTS

Uruchomiono na CPython 3.15.2 wyłącznie wymagane polecenie:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long
~~~

Wynik: FFF.. [100%]; 3 failed, 2 passed in 0.94s (exit code 1). Wszystkie trzy FAIL kończą się w tests/test_cycle_semantics_default_definition_effects.py:102 na assert result.outcome == expected_outcome; evaluator zwrócił UNKNOWN, parametr oczekiwał MODEL_PASS.

- FAIL: single-default-import, sequential-default-imports, rebind-after-default.
- PASS: rebind-before-default, unsupported-return.
- Nie uruchomiono innych testów.

## PACKAGE_LAYOUT_EVIDENCE

- **DIRECT_EVIDENCE — package_layout.py::build_package_layout, linie 85–124:** funkcja normalizuje identyfikator kończący się .__init__ do logicznej nazwy pakietu. Dla węzła wylicza is_init, is_file i has_children. Gdy istnieje plik pkg oraz indeksowane dzieci, ale brak pkg.__init__, warunek (is_file and has_children and not is_init) nadaje AMBIGUOUS_LAYOUT. Zatem dosłowny stary układ pkg + pkg.child nie jest w tym kodzie klasyfikowany jako samodzielny MODULE_FILE; jest niejednoznaczny.
- **CODE_PATH_PROVED — po korekcie:** klucze pkg.__init__ i pkg.child dają dla logicznego pkg is_init=True, is_file=False, has_children=True, czyli REGULAR_PACKAGE; pkg.child jest MODULE_FILE. evaluate_package_import_order (linie 1460–1510) odrzuca w bramce layoutu tylko węzły spoza REGULAR_PACKAGE i MODULE_FILE. Walidacja łańcucha rodziców (linie 1560–1625) wymaga, aby każdy prefiks dziecka był pakietem. Skorygowany układ spełnia tę bramkę.
- **DIRECT_EVIDENCE — przyczyna pozostałych UNKNOWN:** _safe_passive_function_definition (package_model.py, linie 145–242) dopuszcza default wyłącznie gdy safe_default widzi ast.Constant o obsługiwanym typie. Wyrażenie g() jest ast.Call i zostaje odrzucone. W _compile (linie 1030–1095) odrzucenie definicji FunctionDef zwraca None; evaluate_package_import_order (linie 1560–1625) mapuje program is None na UNKNOWN.
- **WERYFIKACJA WYNIKU:** po zmianie fixture testy bezpośrednio pokazały UNKNOWN zamiast MODEL_PASS we wszystkich trzech wymaganych przypadkach. Ponieważ skorygowany layout spełnia warunki bramki, te FAIL nie wynikają już z nieprawidłowego layoutu, tylko z konserwatywnej odmowy dynamicznego defaultu. Nie doszło do asercji eventów w tych trzech testach, bo test kończy się wcześniej na asercji outcome.
- **INFERENCE — ograniczenie dwóch PASS:** rebind-before-default i unsupported-return także przechodzą przez ogólną odmowę dynamicznego defaultu. Sam PASS nie dowodzi, że evaluator osobno rozróżnia rebinding przed definicją od wartości zwracanej; ta zmiana testu tego nie sprawdza.

## MCP_AUDIT

- **DIRECT_EVIDENCE — po zmianie:** Contextor LIVE revision 1465, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}. Agregat workspace_sync=unverified; rodzina cycle_semantics=stale.
- **DIRECT_EVIDENCE — badany plik:** per-file workspace_sync=verified dla tests/test_cycle_semantics_default_definition_effects.py, canonical_revision=1465, provenance=live.
- **DIRECT_EVIDENCE — składnia:** globalne syntax_errors.count=0 (fresh); file diagnostics: checked_and_none, fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — watcher:** get_live_events(after_revision=1464) zwrócił event revision 1465, operation=update_file, origin=desktop_watcher, status=UPDATED, ścieżka testu; continuity=continuous, resync_required=false.
- **UNKNOWN:** przyczyna agregatowego workspace_sync=unverified nie była badana; plik docelowy ma osobne, zweryfikowane workspace_sync=verified.

## FILES_CHANGED

- tests/test_cycle_semantics_default_definition_effects.py — zmieniono wyłącznie klucz "pkg" na "pkg.__init__".
- walkthrough.md — nadpisany raport wymagany zadaniem; jako raport nie jest liczony jako zmieniony source/test.
- Nie zmieniono kodu produkcyjnego, innych testów, issues.md ani audyt.txt.

## FULL_DIFFS

### tests/test_cycle_semantics_default_definition_effects.py — pełny rzeczywisty diff

~~~diff
diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
index 1966af0..00e309a 100644
--- a/tests/test_cycle_semantics_default_definition_effects.py
+++ b/tests/test_cycle_semantics_default_definition_effects.py
@@ -87,7 +87,7 @@ def test_default_definition_effects(
     expected_imports,
 ):
     sources = {
-        "pkg": ast.parse(source),
+        "pkg.__init__": ast.parse(source),
         **{
             name: ast.parse(child_source)
             for name, child_source in children.items()
~~~
