# P6-D04-I3 — EXACT BOUNDARY REGRESSION TESTS

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP:** przed zmianą LIVE revision 1466, provenance=live, canonical_state=fresh, resync_required=false; globalne syntax_errors=0 (fresh). Plik tests/test_cycle_semantics_default_definition_effects.py miał per-file workspace_sync=verified, canonical_revision=1466, syntax_diagnostics=checked_and_none.
- **DIRECT_EVIDENCE — lokalny stan:** HEAD 54ed000d6e2b163b0e3c655914f98762a5d376b8; git status --short był pusty. Odczytano dokładny koniec pliku: ostatnia asercja porządku eventów kończyła dotychczasowy test_default_definition_effects.
- **DIRECT_EVIDENCE — issues.md:** odczytano bez modyfikacji; zawiera wpisy o innych obszarach, bez P6-D04/I3.
- **INFERENCE — niezależna ocena przypadków:** keyword-only defaults mają być ewaluowane kolejno; powtórne g() powinno dać dwa wywołania, ale pojedynczy START_IMPORT dla już załadowanego modułu; g=h przed definicją powinno użyć aktualnego aliasu; call f() po definicji f nadal jest poza obsługą opaque funkcji; import pkg.child z from pkg import f podczas ewaluacji defaultu zachodzi przed związaniem f, więc nie może uzyskać MODEL_PASS.

## EXACT_CHANGE

- Na końcu tests/test_cycle_semantics_default_definition_effects.py dopisano dokładnie dostarczony helper _p6_boundary_model oraz pięć testów granicznych.
- Istniejąca treść pliku pozostała bez zmian. Nie zmieniono produkcji ani innych testów.
- issues.md pozostał bez zmian. walkthrough.md nadpisano zgodnie z poleceniem raportowym.

## TARGETED_RESULTS

Uruchomiono dokładnie:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long
~~~

Wynik: 10 passed in 0.78s (exit code 0). Wykonano wszystkie pięć dotychczasowych i pięć dopisanych przypadków; tracebacków nie było. Interpreter .venv/Scripts/python.exe był bezpośrednio zweryfikowany jako Python 3.15.2 w poprzednim zadaniu na tym samym workspace/venv.

## SEMANTIC_BOUNDARIES

- **DIRECT_EVIDENCE — keyword-only order:** test wymaga importów pkg.a, pkg.b w kolejności odpowiadającej x=g(), y=h().
- **DIRECT_EVIDENCE — repeated call:** test wymaga dwóch eventów CALL_FUNCTION symbol=g oraz jednego START_IMPORT dla pkg.child.
- **DIRECT_EVIDENCE — aktualny namespace:** po g = h test wymaga wyłącznie importu pkg.b, co sprawdza lookup aliasu w chwili default call.
- **DIRECT_EVIDENCE — opaque boundary:** późniejsze f() daje UNKNOWN, mimo że wcześniejszy default g() pozwolił związać f jako DEFINE_OPAQUE_FUNCTION.
- **DIRECT_EVIDENCE — kolejność wiązania:** gdy default g() importuje pkg.child, a child wykonuje from pkg import f, wynik nie może być MODEL_PASS. Asercja celowo wymaga tylko outcome != MODEL_PASS.
- **CODE_PATH_PROVED — interpreter:** istniejący CALL_FUNCTION robi lookup nazwy w bieżącym module namespace, odrzuca wartość, która nie jest zgodną _RestrictedFunction, i uruchamia jej body w _FunctionFrame. Importy body są eventami modelu; po zakończeniu frame wraca do kolejnego kroku. _FunctionFrame.result_binding jest opcjonalny; wywołania defaultów nie wiążą wartości pod dodatkową nazwą.
- **INFERENCE:** pięć nowych przypadków zawęża granicę wyłącznie dla efektów wywołania i kolejności definicji; nie testują ani nie wprowadzają reprezentacji wartości zwracanej jako defaultu.

## MCP_AUDIT

- **DIRECT_EVIDENCE — LIVE po zmianie:** revision 1467, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}.
- **DIRECT_EVIDENCE — per-file:** tests/test_cycle_semantics_default_definition_effects.py ma workspace_sync=verified przy canonical_revision=1467, provenance=live.
- **DIRECT_EVIDENCE — składnia:** globalne syntax_errors.count=0 (fresh); plik docelowy ma checked_and_none, availability=fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — freshness:** graph=fresh i cycles=fresh; cycle_semantics=stale. Rodziny module, topology, artifact_consumption, collisions i lineage są fresh. Agregat workspace_sync=unverified, mimo verified dla pliku docelowego.
- **DIRECT_EVIDENCE — watcher:** event revision 1467, operation=update_file, origin=desktop_watcher, status=UPDATED dla testu; continuity=continuous, resync_required=false.

## FILES_CHANGED

- tests/test_cycle_semantics_default_definition_effects.py — dopisano wyłącznie dostarczony fragment.
- walkthrough.md — nadpisany wymagany raport; nie jest liczony jako zmieniony source/test.
- Nie zmieniono produkcji, innych testów, issues.md ani audyt.txt.

## FULL_DIFFS

### tests/test_cycle_semantics_default_definition_effects.py — pełny rzeczywisty diff

~~~diff
diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
index 00e309a..a53f802 100644
--- a/tests/test_cycle_semantics_default_definition_effects.py
+++ b/tests/test_cycle_semantics_default_definition_effects.py
@@ -138,3 +138,107 @@ def test_default_definition_effects(
         position < definition_position
         for position in observed_positions
     )
+
+
+def _p6_boundary_model(source, children):
+    sources = {
+        "pkg.__init__": ast.parse(source),
+        **{
+            name: ast.parse(code)
+            for name, code in children.items()
+        },
+    }
+    return evaluate_package_import_order(sources, "pkg")
+
+
+def test_p6_keyword_only_default_order():
+    result = _p6_boundary_model(
+        "def g():\n"
+        "    import pkg.a\n"
+        "def h():\n"
+        "    import pkg.b\n"
+        "def f(*, x=g(), y=h()):\n"
+        "    pass\n",
+        {"pkg.a": "pass", "pkg.b": "pass"},
+    )
+    assert result.outcome == "MODEL_PASS"
+    imports = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target in {"pkg.a", "pkg.b"}
+    ]
+    assert imports == ["pkg.a", "pkg.b"]
+
+
+def test_p6_repeated_default_call():
+    result = _p6_boundary_model(
+        "def g():\n"
+        "    import pkg.child\n"
+        "def f(x=g(), y=g()):\n"
+        "    pass\n",
+        {"pkg.child": "pass"},
+    )
+    assert result.outcome == "MODEL_PASS"
+    calls = [
+        event.symbol
+        for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ]
+    assert calls == ["g", "g"]
+    imports = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    ]
+    assert imports == ["pkg.child"]
+
+
+def test_p6_alias_rebinding_before_default():
+    result = _p6_boundary_model(
+        "def g():\n"
+        "    import pkg.a\n"
+        "def h():\n"
+        "    import pkg.b\n"
+        "g = h\n"
+        "def f(x=g()):\n"
+        "    pass\n",
+        {"pkg.a": "pass", "pkg.b": "pass"},
+    )
+    assert result.outcome == "MODEL_PASS"
+    imports = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target in {"pkg.a", "pkg.b"}
+    ]
+    assert imports == ["pkg.b"]
+
+
+def test_p6_later_opaque_call_remains_unknown():
+    result = _p6_boundary_model(
+        "def g():\n"
+        "    import pkg.child\n"
+        "def f(x=g()):\n"
+        "    pass\n"
+        "f()\n",
+        {"pkg.child": "pass"},
+    )
+    assert result.outcome == "UNKNOWN"
+    assert any(
+        event.operation == "DEFINE_OPAQUE_FUNCTION"
+        and event.symbol == "f"
+        for event in result.events
+    )
+
+
+def test_p6_import_before_function_binding():
+    result = _p6_boundary_model(
+        "def g():\n"
+        "    import pkg.child\n"
+        "def f(x=g()):\n"
+        "    pass\n",
+        {"pkg.child": "from pkg import f"},
+    )
+    assert result.outcome != "MODEL_PASS"
~~~
