# P11-I2 — przyczyna hazardów CPython

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `3e3560702beba90dc880009412a333f0ff9cddd8`; przed edycją tylko `audyt.txt` był zmieniony w drzewie roboczym. Nie edytowano go. Zmiany P11-I1 są już w HEAD.
- DIRECT_EVIDENCE: Contextor MCP przed zmianą: LIVE revision 1563, `canonical_state=fresh`, `workspace_sync=verified` dla `tests/test_cycle_semantics_package_model.py` i `tests/test_cycle_semantics_initialization_model.py`; `cycle_semantics=stale`. `get_source_range` potwierdził dokładne kotwice obu helperów oraz trzech asercji.
- DIRECT_EVIDENCE: repozytoryjny `.venv` działa na CPython 3.15.2. `issues.md` odczytano tylko do wyszukiwania; brak trafień dla `P11`, `p.a.value`, złożonych/nested odczytów atrybutów. Nie oznacza to braku innych, niejednoznacznie nazwanych kwestii.

## FILES_CHANGED

- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_initialization_model.py`

`walkthrough.md` jest wyłącznie raportem. Równoległa zmiana `audyt.txt` nie należy do P11-I2 i nie była edytowana.

## EXACT_CHANGES

- DIRECT_EVIDENCE: oba `_actual` dostały opcjonalny argument keyword-only `return_process=False`. Zachowano zapis plików, `subprocess.run` i domyślną wartość bool. Przy `True` helper zwraca `CompletedProcess`.
- DIRECT_EVIDENCE: trzy wskazane testy sprawdzają niezerowy `returncode` oraz ostatnią linię `stderr`: `AttributeError`, częściowo zainicjalizowany właściwy moduł i właściwy brakujący atrybut. Pozostałych asercji i testów nie zmieniano.

## CPYTHON_EXCEPTION_EVIDENCE

- DIRECT_EVIDENCE: trzy zmienione testy przeszły na CPython 3.15.2. Osobne kontrolowane wywołanie tych samych helperów z tymi samymi źródłami dało poniższe pełne tracebacki. Tymczasowe katalogi różnią się od katalogów pytest; semantyczne końcowe linie są zgodne z asercjami.

### Pakiet, pierwszy segment `a`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import importlib,sys;sys.path.insert(0,sys.argv[1]);importlib.import_module(sys.argv[2])
                                                        ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Python315\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1389, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1353, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1249, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 857, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 751, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "C:\Users\DafoO\AppData\Local\Temp\tmpp5yg8x28\route\__init__.py", line 1, in <module>
    import route.consumer
  File "C:\Users\DafoO\AppData\Local\Temp\tmpp5yg8x28\route\consumer.py", line 2, in <module>
    x=route.a.value
      ^^^^^^^
AttributeError: partially initialized module 'route' from 'C:\Users\DafoO\AppData\Local\Temp\tmpp5yg8x28\route\__init__.py' has no attribute 'a' (most likely due to a circular import)
```

### Pakiet, późniejszy segment `value`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import importlib,sys;sys.path.insert(0,sys.argv[1]);importlib.import_module(sys.argv[2])
                                                        ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Python315\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1389, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1353, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1249, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 857, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 751, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "C:\Users\DafoO\AppData\Local\Temp\tmptg8dn3cm\route\__init__.py", line 3, in <module>
    import route.consumer
  File "C:\Users\DafoO\AppData\Local\Temp\tmptg8dn3cm\route\consumer.py", line 2, in <module>
    x=route.a.value
      ^^^^^^^^^^^^^
AttributeError: partially initialized module 'route' from 'C:\Users\DafoO\AppData\Local\Temp\tmptg8dn3cm\route\__init__.py' has no attribute 'value' (most likely due to a circular import)
```

### Moduły płaskie, pierwszy segment `value`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import importlib,sys; sys.path.insert(0,sys.argv[1]); importlib.import_module(sys.argv[2])
                                                          ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Python315\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1389, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1353, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1249, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 857, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 751, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "C:\Users\DafoO\AppData\Local\Temp\tmpy7x0wpyx\alpha.py", line 1, in <module>
    import beta
  File "C:\Users\DafoO\AppData\Local\Temp\tmpy7x0wpyx\beta.py", line 2, in <module>
    x=alpha.value.next
      ^^^^^^^^^^^
AttributeError: partially initialized module 'alpha' from 'C:\Users\DafoO\AppData\Local\Temp\tmpy7x0wpyx\alpha.py' has no attribute 'value' (most likely due to a circular import)
```

## TARGETED_TESTS

- DIRECT_EVIDENCE: trzy zmienione testy: `3 passed in 3.44s`.
- DIRECT_EVIDENCE: dwa wskazane pliki testowe: `277 passed in 16.03s`. Nie uruchomiono pełnego pytest suite. `git diff --check` dla dwóch plików testowych nie wykazał błędów.

## MCP_POST_CHANGE

- DIRECT_EVIDENCE: `get_live_events(after_revision=1563)` zwrócił `desktop_watcher` UPDATED dla testu pakietowego w revision 1564 i płaskiego w revision 1565, `continuity=continuous`.
- DIRECT_EVIDENCE: `get_module_context` dla obu plików testowych w LIVE revision 1565 zwrócił `canonical_state=fresh`, `workspace_sync=verified`, provenance `live`; `cycle_semantics=stale`. To potwierdza stan kanoniczny plików, a nie wykonanie testów przez MCP czy adopcję kodu runtime.

## FULL_DIFFS

Poniżej rzeczywisty pełny diff obu plików FILES_CHANGED względem bieżącego HEAD, wygenerowany przez Git. `walkthrough.md` jako raport nie jest do niego włączony.

```diff
diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
index a0c5cad..866beab 100644
--- a/tests/test_cycle_semantics_initialization_model.py
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -17,7 +17,7 @@ def _assess(sources, entry):
     )
 
 
-def _actual(tmp_path, sources, entry):
+def _actual(tmp_path, sources, entry, *, return_process=False):
     for name, code in sources.items():
         (tmp_path / (name + ".py")).write_text(code, encoding="utf-8")
     result = subprocess.run(
@@ -28,6 +28,8 @@ def _actual(tmp_path, sources, entry):
         ), str(tmp_path), entry],
         capture_output=True, text=True, timeout=10, check=False,
     )
+    if return_process:
+        return result
     return result.returncode == 0
 
 
@@ -155,7 +157,14 @@ def test_nested_attribute_first_segment_hazard(tmp_path):
     assert not any(
         event.operation == "READ_ATTRIBUTE" for event in result.events
     )
-    assert not _actual(tmp_path, sources, "alpha")
+    process = _actual(
+        tmp_path, sources, "alpha", return_process=True
+    )
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'alpha'" in exception_line
+    assert "has no attribute 'value'" in exception_line
 
 
 def test_nested_attribute_known_first_segment_stops_unknown():
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 007c9a8..c6863ef 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1372,7 +1372,7 @@ def test_indexed_import_has_no_reached_blocker():
     assert result.reached_unmodeled_import is None
 
 
-def _actual(tmp_path, source, entry):
+def _actual(tmp_path, source, entry, *, return_process=False):
     for module_id, code in source.items():
         parts = module_id.split(".")
 
@@ -1416,6 +1416,8 @@ def _actual(tmp_path, source, entry):
         check=False,
     )
 
+    if return_process:
+        return process
     return process.returncode == 0
 
 
@@ -3400,7 +3402,14 @@ def test_nested_attribute_first_segment_initializing_hazard(tmp_path):
         "EARLY_BINDING_HAZARD", "route", "a",
     )
     assert not any(e.operation == "ATTR" for e in result.events)
-    assert not _actual(tmp_path, source, "route")
+    process = _actual(
+        tmp_path, source, "route", return_process=True
+    )
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'route'" in exception_line
+    assert "has no attribute 'a'" in exception_line
 
 
 def test_nested_attribute_later_segment_initializing_hazard(tmp_path):
@@ -3416,7 +3425,14 @@ def test_nested_attribute_later_segment_initializing_hazard(tmp_path):
         ("ATTR", "route", "a"),
         ("EARLY_BINDING_HAZARD", "route", "value"),
     ]
-    assert not _actual(tmp_path, source, "route")
+    process = _actual(
+        tmp_path, source, "route", return_process=True
+    )
+    assert process.returncode != 0
+    exception_line = process.stderr.strip().splitlines()[-1]
+    assert exception_line.startswith("AttributeError:")
+    assert "partially initialized module 'route'" in exception_line
+    assert "has no attribute 'value'" in exception_line
 
 
 def test_nested_attribute_unknown_after_ordinary_value(tmp_path):
```

## FINAL_STATUS

- DIRECT_EVIDENCE: CPython 3.15.2 potwierdził dokładny AttributeError i brakujący segment we wszystkich trzech hazardach. Zmiana jest ograniczona do dwóch plików testowych; focused regression 277/277 passed.
- DIRECT_EVIDENCE: LIVE revision 1565 ma verified sync obu testów; cycle_semantics pozostaje stale. Nie wykonano staging, commit, push ani restartu.
- UNKNOWN: bieżąca adopcja kodu produkcyjnego przez proces MCP i globalna semantyka LIVE nie są certyfikowane przez ten etap.
