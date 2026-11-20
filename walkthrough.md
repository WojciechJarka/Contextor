# P6-D04-I2 — RESTRICTED DEFINITION-TIME DEFAULT CALLS

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP przed zmianą:** LIVE revision 1465, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}; globalne syntax_errors=0 (fresh). Agregat workspace_sync=unverified.
- **DIRECT_EVIDENCE — per-file przed zmianą:** contextor/core/cycle_semantics/package_model.py miało workspace_sync=verified przy rev 1465, syntax_diagnostics=checked_and_none, errors=0. Badane pliki testów również miały per-file workspace_sync=verified.
- **DIRECT_EVIDENCE — lokalny precheck:** HEAD 4e26e0718392d8296433dcaff2044c7a8053f955; git status --short był pusty. Wszystkie cztery dokładne kotwice z promptu odpowiadały aktualnemu plikowi.
- **DIRECT_EVIDENCE — issues.md:** odczytano cały plik. Zawiera wpisy o innych obszarach Contextora; nie ma wpisu P6-D04 ani o default calls. Plik nie został zmieniony.
- **DIRECT_EVIDENCE — istniejące kontrakty testowe:** odczytano przez Contextor testy:
  - tests/test_cycle_semantics_passive_functions.py: test_c23_dynamic_default_unknown, test_c23_positional_default_opaque_binding, test_c23_keyword_only_default_opaque_binding, test_c23_zero_arg_opaque_body_not_executed, test_c23_existing_restricted_function_preserved;
  - tests/test_cycle_semantics_decorator_import_effect_baseline.py: test_minimal_decorator_import_effects;
  - tests/test_cycle_semantics_definition_effect_order_cpython.py: test_definition_effect_order_cpython.
- **CODE_PATH_PROVED:** validator domyślnie dopuszcza tylko literalne defaulty; _compile zapisuje wspierane funkcje restricted jako _RestrictedFunction, a istniejący krok CALL_FUNCTION wykonuje lookup w bieżącym namespace, otwiera _FunctionFrame dla body i wznawia frame modułu po zakończeniu. _RestrictedFunction przechowuje module, body i parametry, nie wartość defaultu.
- **INFERENCE — semantyczny zakres:** w ograniczonym przypadku bezargumentowa nazwana funkcja restricted może mieć modelowane importy w body; jej wywołanie przy definicji dodaje te efekty przed związaniem f. Ponieważ f pozostaje opaque i nie jest wywoływane, modeluje się efekt wywołania, a nie przechowuje wartość defaultu. Nie jest to ogólna ewaluacja wyrażeń Python.

## EXACT_CHANGES

- Zmiana 1: dodano allow_restricted_default_calls=False do _safe_passive_function_definition.
- Zmiana 2: safe_default dopuszcza ast.Call wyłącznie przy włączonym opt-in, bezpośredniej ast.Name z nie-dunderowym identyfikatorem oraz bez argumentów i keywords; pozostała walidacja literalnych defaultów pozostała bez zmian.
- Zmiana 3: opt-in przekazywany jest wyłącznie w gałęzi ast.FunctionDef jako not stmt.decorator_list. AsyncFunctionDef i walidacja metod klas nadal korzystają z domyślnego False.
- Zmiana 4: dla kolejnych args.defaults, a następnie args.kw_defaults, compiler dodaje CALL_FUNCTION przed DEFINE_OPAQUE_FUNCTION dla f. f pozostaje opaque.
- Nie zmieniono _Step, _FunctionFrame, _RestrictedFunction, interpretera, testów ani innych plików produkcyjnych.

## TARGETED_RESULTS

Wykonano dokładnie cztery wskazane polecenia:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long
5 passed in 1.24s
~~~

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_passive_functions.py::test_c23_dynamic_default_unknown tests/test_cycle_semantics_passive_functions.py::test_c23_positional_default_opaque_binding tests/test_cycle_semantics_passive_functions.py::test_c23_keyword_only_default_opaque_binding tests/test_cycle_semantics_passive_functions.py::test_c23_zero_arg_opaque_body_not_executed tests/test_cycle_semantics_passive_functions.py::test_c23_existing_restricted_function_preserved --tb=long
5 passed in 1.22s
~~~

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_decorator_import_effect_baseline.py::test_minimal_decorator_import_effects --tb=long
5 passed in 1.23s
~~~

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_definition_effect_order_cpython.py::test_definition_effect_order_cpython --tb=long
8 passed in 1.37s
~~~

Wynik łączny: 23 przypadki PASS. Testy z test_definition_effect_order_cpython uruchamiają izolowane podprocesy CPython dla porządku efektów definicji i dekoratorów. Interpreter .venv/Scripts/python.exe był bezpośrednio zweryfikowany jako Python 3.15.2 w poprzednim zadaniu na tym samym workspace/venv; w tym zadaniu uruchomiono wyłącznie podane polecenia pytest.

## MODEL_BOUNDARY

- **DIRECT_EVIDENCE:** named no-arg default call przechodzi compile tylko w niedekorowanym FunctionDef. CALL_FUNCTION nie ma bindingu, więc wartość zwrócona przez restricted callee nie jest wiązana jako nazwa ani zapisywana do reprezentacji f.
- **CODE_PATH_PROVED:** istniejący interpreter robi namespace lookup targetu; _execute_restricted_call akceptuje tylko _RestrictedFunction z tego samego modułu i zgodną liczbą argumentów. Następnie CALL_FUNCTION dopisuje event, przesuwa frame modułu i uruchamia body w _FunctionFrame. Po końcu body moduł wznawia się od następnego kroku. To pozwala zaobserwować importy g/h przed krokiem definicji opaque f.
- **DIRECT_EVIDENCE — granice zachowane przez testy:** nieznane compute_default nadal daje UNKNOWN; defaulty stałe, keyword-only i opaque body zachowują dotychczasowe zachowanie; zwykłe body f nie jest wykonywane przy definicji; istniejące restricted function call pozostaje obsłużone. Baseline dekoratorów nadal przechodzi, w tym dynamic default w dekorowanej funkcji z oczekiwanym UNKNOWN.
- **INFERENCE — rebinding i unsupported return:** rebinding g przed defaultem widzi w runtime bieżące g, a nie wcześniejszą definicję; jeśli nie jest _RestrictedFunction, wynik jest UNKNOWN. G z unsupported return jest reprezentowane opaque, więc jej wywołanie pozostaje UNKNOWN. Testy regresyjne potwierdziły te oczekiwane statusy.
- **INFERENCE — kolejność:** konkatenacja args.defaults i args.kw_defaults daje positional defaults w kolejności AST, potem keyword-only defaults w kolejności AST; pominięte kw-only defaults mają wartość None i nie generują CALL_FUNCTION.
- Rozszerzenie nie dotyczy dekorowanych funkcji, AsyncFunctionDef, metod klas, wywołań z argumentami, atrybutowych callees ani wartości defaultów dostępnych przy późniejszej introspekcji.

## MCP_AUDIT

- **DIRECT_EVIDENCE — LIVE po zmianie:** revision 1466, provenance=live, canonical_state=fresh, resync_required=false, parse_stale_modules={}.
- **DIRECT_EVIDENCE — per-file:** contextor/core/cycle_semantics/package_model.py ma workspace_sync=verified przy canonical_revision=1466, provenance=live.
- **DIRECT_EVIDENCE — składnia:** globalne syntax_errors.count=0 (fresh); produkcyjny plik ma checked_and_none, availability=fresh, errors=[], total=0.
- **DIRECT_EVIDENCE — freshness:** graph=fresh, cycles=fresh, cycle_semantics=stale. Pozostałe rodziny module, topology, artifact_consumption, collisions i lineage są fresh. Agregat workspace_sync pozostaje unverified mimo verified dla badanego pliku.
- **DIRECT_EVIDENCE — watcher:** event revision 1466, operation=update_file, origin=desktop_watcher, status=UPDATED dla package_model.py; continuity=continuous, resync_required=false.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_model.py — jedyny zmieniony plik produkcyjny.
- walkthrough.md — nadpisany wymagany raport; nie jest liczony jako zmieniony source/test.
- Nie zmieniono żadnego testu, issues.md ani audyt.txt.

## FULL_DIFFS

### contextor/core/cycle_semantics/package_model.py — pełny rzeczywisty diff

~~~diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 5275c9b..8f8b5cc 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -149,6 +149,7 @@ def _safe_passive_function_definition(
     annotation_semantics: str | None = None,
     allow_builtin_property: bool = False,
     allow_restricted_decorator: bool = False,
+    allow_restricted_default_calls: bool = False,
 ) -> bool:
     """A definition whose creation has no unknown evaluations.
 
@@ -214,6 +215,17 @@ def _safe_passive_function_definition(
         return False
 
     def safe_default(value: ast.AST) -> bool:
+        if (
+            allow_restricted_default_calls
+            and type(value) is ast.Call
+            and type(value.func) is ast.Name
+            and value.func.id.isidentifier()
+            and not value.func.id.startswith("__")
+            and not value.args
+            and not value.keywords
+        ):
+            return True
+
         return (
             isinstance(value, ast.Constant)
             and type(value.value) in (
@@ -1038,6 +1050,7 @@ def _compile(
                 stmt,
                 annotation_semantics=annotation_semantics,
                 allow_restricted_decorator=True,
+                allow_restricted_default_calls=not stmt.decorator_list,
             ):
                 return None
@@ -1148,6 +1161,15 @@ def _compile(
             if stmt.decorator_list and not restricted_callable:
                 return None
 
+            for default in (*args.defaults, *args.kw_defaults):
+                if type(default) is ast.Call:
+                    steps.append(
+                        _Step(
+                            "CALL_FUNCTION",
+                            target=default.func.id,
+                        )
+                    )
+
             if restricted_callable:
                 steps.append(
                     _Step(
~~~
