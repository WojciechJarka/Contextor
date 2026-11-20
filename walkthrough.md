# SP-T4-REMAINING-R6 — CLASS DECORATOR CONTRACT

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP przed edycją:** LIVE revision 1460, provenance=live, canonical_state=fresh, resync_required=false. Globalne workspace_sync=unverified; dla pliku testowego per-file workspace_sync=verified na revision 1460.
- **DIRECT_EVIDENCE — Git przed edycją:** HEAD caf1ed548a21ba52b0290e5be4fbf71018831e02. Status zawierał wyłącznie wcześniejszą modyfikację walkthrough.md z poprzedniego raportu; plik testowy był czysty.
- **DIRECT_EVIDENCE — interpreter:** repo .venv wskazuje CPython 3.15.2, executable C:\Temp\Contextor_Repo\.venv\Scripts\python.exe.
- **DIRECT_EVIDENCE — anchor MCP i lokalny:** w CASES przypadek class-body-before-decorator miał źródło i expected_imports bez zmian oraz expected_model_outcome="UNKNOWN" w linii 68.
- **CONTRACT_PROVED — niezależna kontrola semantyczna:** discovery R5 dla zweryfikowanego LIVE revision 1460 wykazało ograniczoną ścieżkę evaluator dla dokładnie tego fixture: klasa importuje pkg.body przed wywołaniem dekoratora; ograniczona funkcja deco importuje pkg.decorate, a potem zwraca ten sam abstrakcyjny class_fact. Oba moduły są indeksowane, a ich syntetyczne źródła to pass. MODEL_PASS jest uzasadniony dla tego zamkniętego przypadku. To nie certyfikuje dowolnych dekoratorów ani środowiska runtime.
- Nie zmieniano produkcji. Nie uruchomiono FULL ani pełnego pytest.

## EXACT_CHANGE

W tests/test_cycle_semantics_decorator_import_effect_baseline.py zmieniono wyłącznie expected_model_outcome parametru class-body-before-decorator z UNKNOWN na MODEL_PASS. Źródło, expected_imports, pozostałe parametry i mechanizm testu pozostały bez zmian.

## TARGETED_RESULTS

Interpreter dla obu poleceń: CPython 3.15.2 z repo .venv.

1. Dokładny node ID:
   tests/test_cycle_semantics_decorator_import_effect_baseline.py::test_minimal_decorator_import_effects[class-body-before-decorator]

   Wynik: PASS — 1 passed in 2.11s.

2. Wszystkie parametryzacje funkcji:
   tests/test_cycle_semantics_decorator_import_effect_baseline.py::test_minimal_decorator_import_effects

   Wynik: PASS — 5 passed in 1.38s.

Nie wystąpiły FAIL ani tracebacki.

## CPYTHON_PARITY

- **DIRECT_EVIDENCE:** test wywołuje podproces przez sys.executable -I -B i porównuje observed["imports"] z expected_imports. Interpreter bazowy potwierdzono jako CPython 3.15.2, więc podproces używa tego samego executable.
- **DIRECT_EVIDENCE:** dla class-body-before-decorator test sprawdza kolejność ("pkg.body", "pkg.decorate"). Parametr przeszedł z tym oracle oraz z oceną modelu MODEL_PASS.
- **DIRECT_EVIDENCE:** pięć obecnych expected_model_outcome w CASES po zmianie:
  - decorated-function-body-deferred — MODEL_PASS;
  - decorator-import-during-definition — MODEL_PASS;
  - stacked-decorator-import-order — MODEL_PASS;
  - class-body-before-decorator — MODEL_PASS;
  - default-before-decorator-application — UNKNOWN.
- Wszystkie pięć parametrów przeszło; dotychczasowe oczekiwanie UNKNOWN pozostało dla default-before-decorator-application.

## MODEL_BOUNDARY

- **CODE_PATH_PROVED:** test celuje w syntetyczny zamknięty pakiet. Ograniczony evaluator przyjmuje dla badanego przypadku named decorator z obsługiwanym jednoargumentowym body, importy z indeksowanych modułów i bezpośrednie return cls.
- **DIRECT_EVIDENCE:** evaluator deklaruje założenie conventional builtin bindings i brak atestacji rzeczywistych __builtins__, builtins oraz import environment. MODEL_PASS nie oznacza ogólnego dowodu bezpieczeństwa wykonania.
- **INFERENCE:** oczekiwanie MODEL_PASS jest odpowiednie dla tego przypadku, ponieważ wszystkie jego jawne efekty należą do obsługiwanego podzbioru. Nie rozszerza to kontraktu na arbitralne skutki uboczne dekoratorów.

## LIMITATIONS

- Test obejmuje pięć parametrów jednej funkcji; nie uruchamiano pozostałych testów pliku ani pełnego pytest.
- **DIRECT_EVIDENCE — MCP post-change audit:** Desktop watcher opublikował event revision 1461, operation=update_file, origin=desktop_watcher, status=UPDATED dla wskazanego pliku testowego. affected_modules.total=0, blast_radius_state=deferred.
- LIVE po zmianie: revision=1461, provenance=live, canonical_state=fresh, resync_required=false; per-file workspace_sync=verified dla testu na revision 1461. Globalne workspace_sync pozostaje unverified.
- Diagnostyka LIVE: syntax_errors=0/fresh; graph=fresh; cycles=fresh, structural count=16. cycle_semantics family jest stale. Diagnostyka strukturalna nie jest wynikiem badanego testu ani dowodem wykonania dekoratorów.
- Zmieniono wyłącznie test i walkthrough.md. Nie było potrzeby restartu; nie wywołano MCP update_file.

## FILES_CHANGED

- tests/test_cycle_semantics_decorator_import_effect_baseline.py — jedna zmiana oczekiwanego wyniku.
- walkthrough.md — raport bieżącego zadania; raport nie jest wliczony do FULL_DIFFS.

## FULL_DIFFS

~~~diff
diff --git a/tests/test_cycle_semantics_decorator_import_effect_baseline.py b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
index a53eaf9..cfbf650 100644
--- a/tests/test_cycle_semantics_decorator_import_effect_baseline.py
+++ b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
@@ -65,7 +65,7 @@ CASES = [
             "    import pkg.body\n"
         ),
         ("pkg.body", "pkg.decorate"),
-        "UNKNOWN",
+        "MODEL_PASS",
         id="class-body-before-decorator",
     ),
~~~

