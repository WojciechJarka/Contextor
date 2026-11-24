# P16-I1 — wzmocnienie kontraktów CPython dla G2 i G6

## PREFLIGHT

**DIRECT_EVIDENCE**

- Contextor MCP sprawdził przed patchem `tests/test_cycle_semantics_package_model.py`: `canonical_state=fresh`, `workspace_sync=verified`, canonical revision `1568`, provenance `live`. Rodzina `cycle_semantics` jest `stale`; to test-only zmiana i nie była traktowana jako źródło semantycznego wyniku.
- `get_source_range` potwierdził dokładne anchory: `test_b0g4c2_existing_attribute_precedes_child` (2018), `test_b0g4c3_early_read_from_reentrant_child` (2128), `test_b0g4c4_preparation_before_local_binding_hazard` (2220). Każda kotwica i wskazana asercja zgadzały się z promptem.
- HEAD przed zmianą: `5dbff8c91ca50a8e5e1a9953775428143e684511`. Plik testowy nie miał wcześniejszego diffu. Istniały wcześniejsze modyfikacje `CHANGELOG.md`, `audyt.txt` i `walkthrough.md`; nie zmieniono dwóch pierwszych.
- Nie zmieniono importów, `_model`, `_actual` ani evaluatorów.

**INFERENCE**

- Brak driftu kotwic; wykonano dokładnie wskazane trzy lokalne zmiany.

## G2_EXACT_CONTRACT

Dodano `test_from_package_import_child_binds_exact_runtime_object` bezpośrednio po `test_b0g4c2_existing_attribute_precedes_child`. Zachowany bez zmian `_model` daje `MODEL_PASS` dla obu fixture; eventy `START_IMPORT` sprawdzają, czy model startuje `pkg.child` wyłącznie w przypadku `MODULE`.

Każdy przypadek przechodzi przez istniejący `_actual(..., return_process=True)` i dodatkowy CPython subprocess. Drugi proces zapisuje JSON o rodzaju rzeczywistego bindingu, wartości, obecności `pkg.child` w `sys.modules` i tożsamości obiektu względem wpisu w `sys.modules`.

Po przejściu testu zaobserwowane i asertywne runtime wartości to:

- `ATTRIBUTE`: `value=3`, `child_loaded=false`, `module_identity=false`.
- `MODULE`: `value=7`, `child_loaded=true`, `module_identity=true`.

Źródło: zmieniona funkcja w `tests/test_cycle_semantics_package_model.py:2034-2098`, potwierdzona przez MCP po zmianie.

## G6_EXACT_CONTRACT

W `test_b0g4c3_early_read_from_reentrant_child` zastąpiono tylko booleanową asercję `_actual` pobraniem `CompletedProcess` i kontrolą końcowej linii tracebacku. Test nadal sprawdza evaluator `EARLY_BINDING_HAZARD`, `target_module="pkg.child"`, `symbol="value"`; CPython potwierdza `AttributeError` dotyczący częściowo zainicjalizowanego `pkg.child` bez `value`.

W `test_b0g4c4_preparation_before_local_binding_hazard` zastąpiono tylko booleanową asercję `_actual` pobraniem `CompletedProcess` i kontrolą końcowej linii tracebacku. Test nadal sprawdza evaluator `EARLY_BINDING_HAZARD`, `target_module="entry"`, `symbol="a"`; CPython potwierdza `AttributeError` dotyczący częściowo zainicjalizowanego `entry` bez `a`.

Pozostałe asercje obu funkcji są niezmienione. Źródła po zmianie: `tests/test_cycle_semantics_package_model.py:2194-2214` i `:2293-2311`.

## CPYTHON_PARITY

**DIRECT_EVIDENCE**

- G2 używa `sys.executable -I -B -c` i rozpoznaje `types.ModuleType`, wynikową wartość oraz stan `sys.modules`; nie opiera się jedynie na return code.
- G6 wykorzystuje istniejący `_actual(..., return_process=True)`, który wykonuje fixture w subprocessie CPython `sys.executable -I -B -c`; asercje odnoszą się do końcowej linii rzeczywistego stderr.
- Wszystkie trzy wskazane testy przeszły. Nie pojawił się traceback porażki.

## TARGETED_TESTS

**Celowany zestaw — exit code 0:**

```text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k "from_package_import_child_binds_exact_runtime_object or b0g4c3_early_read_from_reentrant_child or b0g4c4_preparation_before_local_binding_hazard"
...                                                                      [100%]
3 passed, 246 deselected in 2.59s
```

**Cały wskazany plik — exit code 0:**

```text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py
........................................................................ [ 28%]
........................................................................ [ 57%]
........................................................................ [ 86%]
.................................                                        [100%]
249 passed in 16.58s
```

Nie uruchomiono pełnego pytest ani FULL.

## MCP_POST_CHANGE

**DIRECT_EVIDENCE**

- `get_live_events(after_revision=1568)` zwrócił revision `1569`, continuous/no-resync, z eventem `desktop_watcher`, operation `update_file`, status `UPDATED`, plik `tests/test_cycle_semantics_package_model.py`.
- `get_file_edit_context` po zmianie: `canonical_state=fresh`, `workspace_sync=verified`, `canonical_revision=1569`, provenance `live`.
- AST/syntax z tego samego MCP kontekstu: `status=checked_and_none`, `availability=fresh`, `materialized=true`, `errors=[]`, `total=0`.
- `get_source_range` na revision 1569 odczytał nowe ciało G2 (`2034-2098`) oraz obie zmienione funkcje G6 (`2194-2214`, `2293-2311`). Treść potwierdza testowe źródło rzeczywistego wyniku i zachowane asercje modelu.
- `git diff --check -- tests/test_cycle_semantics_package_model.py` nie zgłosił błędów whitespace.

**INFERENCE**

- Lokalny test i odczyt MCP wskazują na tę samą treść pliku po watcher revision 1569; nie opieram się na nieświeżej rodzinie `cycle_semantics`.

## FULL_DIFFS

`FILES_CHANGED: tests/test_cycle_semantics_package_model.py` (walkthrough jest raportem i nie jest liczony jako source/test).

Pełny diff pliku testowego:

```diff
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index c6863ef..ee42539 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -2031,6 +2031,72 @@ def test_b0g4c2_existing_attribute_precedes_child(tmp_path):
     assert _actual(tmp_path, source, "entry")
+
+
+def test_from_package_import_child_binds_exact_runtime_object(tmp_path):
+    for initializer, expected_kind in (
+        ("child=3", "ATTRIBUTE"),
+        ("pass", "MODULE"),
+    ):
+        source = {
+            "pkg.__init__": initializer,
+            "pkg.child": "value=7",
+            "entry": "from pkg import child",
+        }
+
+        case_dir = tmp_path / expected_kind.lower()
+        result = _model(source, "entry")
+        assert result.outcome == "MODEL_PASS"
+
+        child_starts = [
+            event
+            for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target == "pkg.child"
+        ]
+        assert bool(child_starts) == (expected_kind == "MODULE")
+
+        process = _actual(
+            case_dir, source, "entry", return_process=True
+        )
+        assert process.returncode == 0, process.stderr
+
+        script = (
+            "import importlib,json,sys,types;"
+            "sys.path.insert(0,sys.argv[1]);"
+            "entry=importlib.import_module('entry');"
+            "child=entry.child;"
+            "print(json.dumps({"
+            "'kind':'MODULE' if isinstance(child,types.ModuleType) "
+            "else 'ATTRIBUTE',"
+            "'value':child.value if isinstance(child,types.ModuleType) "
+            "else child,"
+            "'child_loaded':'pkg.child' in sys.modules,"
+            "'module_identity':child is sys.modules.get('pkg.child')"
+            "}))"
+        )
+        runtime = subprocess.run(
+            [
+                sys.executable, "-I", "-B", "-c",
+                script, str(case_dir),
+            ],
+            capture_output=True,
+            text=True,
+            timeout=8,
+            check=False,
+        )
+        assert runtime.returncode == 0, runtime.stderr
+        observed = json.loads(runtime.stdout)
+
+        assert observed["kind"] == expected_kind
+        if expected_kind == "ATTRIBUTE":
+            assert observed["value"] == 3
+            assert observed["child_loaded"] is False
+            assert observed["module_identity"] is False
+        else:
+            assert observed["value"] == 7
+            assert observed["child_loaded"] is True
+            assert observed["module_identity"] is True
 def test_b0g4c2_constant_attribute_is_not_module(tmp_path):
     source = {
         "pkg.__init__": "child=3",
@@ -2138,7 +2204,14 @@ def test_b0g4c3_early_read_from_reentrant_child(tmp_path):
     assert result.outcome == "EARLY_BINDING_HAZARD"
     assert result.target_module == "pkg.child"
     assert result.symbol == "value"
-    assert not _actual(tmp_path, source, "pkg")
+    process = _actual(
+        tmp_path, source, "pkg", return_process=True
+    )
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'pkg.child'" in exception_line
+    assert "has no attribute 'value'" in exception_line
+
+
 def test_b0g4c3_bound_attribute_before_reentrant_read(tmp_path):
@@ -2228,7 +2301,14 @@ def test_b0g4c4_preparation_before_local_binding_hazard(tmp_path):
     assert result.outcome == "EARLY_BINDING_HAZARD"
     assert result.target_module == "entry"
     assert result.symbol == "a"
-    assert not _actual(tmp_path, source, "entry")
+    process = _actual(
+        tmp_path, source, "entry", return_process=True
+    )
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'entry'" in exception_line
+    assert "has no attribute 'a'" in exception_line
+
+
 def test_b0g4c4_all_prepares_before_from_bindings(tmp_path):
```

## FINAL_STATUS

**PASS** — wskazane zmiany testowe zostały zastosowane, celowane testy i cały `test_cycle_semantics_package_model.py` przeszły, a MCP potwierdził revision 1569, watcher update, świeży kanoniczny plik, `workspace_sync=verified` i AST bez błędów.

Nie wykonano commit, push, staging, FULL ani restartu. Wcześniejsze zmiany `CHANGELOG.md` i `audyt.txt` pozostały nietknięte.
