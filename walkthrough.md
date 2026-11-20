# P6-D04-I3-R1 — EXACT EARLY BINDING CONTRACT

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP:** przed zmianą LIVE revision 1467, provenance=live, canonical_state=fresh, resync_required=false; globalne syntax_errors=0 (fresh). Plik testowy miał per-file workspace_sync=verified i syntax_diagnostics=checked_and_none.
- **DIRECT_EVIDENCE — lokalny stan:** HEAD fa5f784575e1d3d1f1ca1820db98749a8275d0f1; git status --short był pusty. Dokładna kotwica występowała w test_p6_import_before_function_binding, linii 244.
- **DIRECT_EVIDENCE — issues.md:** odczytano bez modyfikacji. Nie zawiera wpisu P6-D04/I3 ani dotyczącego tego kontraktu.
- **CODE_PATH_PROVED — klasyfikacja importu:** contextor/core/cycle_semantics/execution/imports.py::_execute_from_binding, linie 206–258, zwraca EARLY_BINDING_HAZARD, gdy member nie ma w namespace targetu, a target jest INITIALIZING. Kontrola zawiera target=target i symbol=member.
- **CODE_PATH_PROVED — wynik/event:** contextor/core/cycle_semantics/package_model.py, linie 2166–2180, publikuje PackageModelEvent(module, event_operation, target, member), a następnie zwraca outcome, target i symbol z tego samego import control.
- **INFERENCE:** podczas ewaluacji g() moduł pkg.child importuje się, gdy inicjalizacja pkg nadal trwa i f nie zostało jeszcze związane. Dlatego oczekiwane są outcome EARLY_BINDING_HAZARD, target_module pkg, symbol f oraz event z operation EARLY_BINDING_HAZARD, target pkg, symbol f.

## EXACT_CHANGE

- Zastąpiono wyłącznie asercję result.outcome != MODEL_PASS czterema dokładnie wskazanymi asercjami outcome, target_module, symbol i event.
- Nie zmieniono żadnej innej treści testu, kodu produkcyjnego ani innych testów.
- issues.md odczytano i pozostawiono bez zmian. walkthrough.md nadpisano jako wymagany raport.

## TARGETED_RESULTS

Uruchomiono wyłącznie:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long
~~~

Wynik: 10 passed in 0.87s (exit code 0). Rzeczywisty outcome i wszystkie trzy pola/eventy odpowiadały nowemu kontraktowi; tracebacku nie było. Interpreter w tym samym .venv był bezpośrednio potwierdzony jako Python 3.15.2 w poprzednim zadaniu.

## MCP_AUDIT

- **DIRECT_EVIDENCE — LIVE po zmianie:** revision 1468, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}.
- **DIRECT_EVIDENCE — per-file:** tests/test_cycle_semantics_default_definition_effects.py ma workspace_sync=verified przy canonical_revision=1468, provenance=live.
- **DIRECT_EVIDENCE — składnia:** globalne syntax_errors.count=0 (fresh); plik testowy ma checked_and_none, availability=fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — watcher:** event revision 1468, operation=update_file, origin=desktop_watcher, status=UPDATED dla pliku testowego; continuity=continuous, resync_required=false.
- Agregat project workspace_sync pozostaje unverified; per-file stan testu jest verified.

## FILES_CHANGED

- tests/test_cycle_semantics_default_definition_effects.py — zmieniono wyłącznie wskazaną asercję na cztery asercje dokładnego kontraktu.
- walkthrough.md — nadpisany wymagany raport; nie jest liczony jako zmieniony source/test.
- Nie zmieniono produkcji, innych testów, issues.md ani audyt.txt.

## FULL_DIFFS

### tests/test_cycle_semantics_default_definition_effects.py — pełny rzeczywisty diff

~~~diff
diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
index a53f802..a79661a 100644
--- a/tests/test_cycle_semantics_default_definition_effects.py
+++ b/tests/test_cycle_semantics_default_definition_effects.py
@@ -241,4 +241,12 @@ def test_p6_import_before_function_binding():
         \"    pass\\n\",
         {\"pkg.child\": \"from pkg import f\"},
     )
-    assert result.outcome != \"MODEL_PASS\"
+    assert result.outcome == \"EARLY_BINDING_HAZARD\"
+    assert result.target_module == \"pkg\"
+    assert result.symbol == \"f\"
+    assert any(
+        event.operation == \"EARLY_BINDING_HAZARD\"
+        and event.target == \"pkg\"
+        and event.symbol == \"f\"
+        for event in result.events
+    )
~~~
