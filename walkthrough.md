# P3-V10 — generic unmodeled statement provenance

## PREFLIGHT

Contextor MCP first: HEAD `32ef7fdff069b770d3925f421db305b357e37992`, canonical revision 1253, `cycle_semantics=fresh`, `package_model.py` workspace_sync verified. Git status przed zmianą nie wykazał modyfikacji source/tests. Dokładne anchory w HEAD: `package_model.py:1505–1527` binary search i `accepted + (_Step("UNMODELED_STATEMENT"),)`; `package_model.py:2684–2685` gałąź zwracająca UNKNOWN. Planowany zakres: `contextor/core/cycle_semantics/package_model.py` tylko `_compile_reachable_prefix` i `evaluate_package_import_order`; `tests/test_cycle_semantics_namespace_path_model.py` testy A–H; `walkthrough.md` raport. Anchory zgodne, bez SOURCE_DRIFT.

Niezależny warunek integralności: istnieje także sentinel typing guard z `_compile` przy `package_model.py:1029`. Ordinary scenarios wywołują evaluator z domyślnym `_compile_on_first_import=False`. Dlatego emisja eventu jest warunkowana `_compile_on_first_import`; bez tego zmieniłaby ordinary events i potencjalnie scenario fingerprints.

## EXACT_FILES_CHANGED

FILES_CHANGED:
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`

`walkthrough.md` jest tylko raportem. Innych source/tests/docs nie edytowano.

## GENERIC_PROVENANCE_IMPLEMENTATION

`_compile_reachable_prefix` zachowuje binary search i warunki `accepted`/ `compile_prefix(high)`. Po nich wybiera `tree.body[low]` jako pierwszy odrzucony statement. Dla FunctionDef, AsyncFunctionDef i ClassDef z decorator list bierze pierwszy decorator; dla pozostałych sam statement. Odczytuje rzeczywiste `lineno`/`col_offset`, przy niepoprawnych lub niedostępnych wartościach zachowuje `None`. Sentinel ma `target=type(statement).__name__` i współrzędne.

W `evaluate_package_import_order` po faktycznym osiągnięciu `UNMODELED_STATEMENT` w trybie `_compile_on_first_import=True` dodaje jeden `PackageModelEvent(module, "UNMODELED_STATEMENT", step.target, "<line>:<column>")`, albo `symbol=None` przy niekompletnej lokalizacji. Dotychczasowy wynik pozostaje UNKNOWN i model nie kontynuuje po odmowie. Dataclasses assessment/event pozostają nietknięte. Nie dodano obsługi `lru_cache`, importów ani warningów.

## TARGETED_TEST_RESULTS

`& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_namespace_bound_model.py` → **117 passed in 78.50s**, exit code 0. `git diff --check` → exit code 0. Uruchomiono tylko dwie wymagane grupy.

Nowe testy: A dekorator FunctionDef `2:1`; B ClassDef `1:1`; C zwykły Raise `2:0`; D zachowane wcześniejsze BIND i import; E zewnętrzny import zatrzymuje przed provenance event; F wcześniejszy EARLY_BINDING_HAZARD zachowuje priorytet; G CONDITIONAL_MODEL_PASS bez eventu; H deterministyczny wynik i AST bez mutacji.

## NEGATIVE_REGRESSIONS

E/F/G potwierdzają brak fałszywego eventu przy wcześniejszym external stop, hazard oraz PASS. Warunek emisji działa tylko po osiągnięciu sentinela w warunkowej ścieżce. Zmiana nie emituje przy layout/validation rejection, bo te gałęzie wracają przed `evaluate_package_import_order` albo przed obsługą sentinela. Wcześniejszy unresolved internal import zwraca zanim sentinel zostanie osiągnięty. Nieosiągnięty dekorator także nie daje eventu.

## ORDINARY_EVIDENCE_INTEGRITY

CODE_PATH_PROVED: `scenarios.py:332` używa `evaluate_package_import_order` bez `_compile_on_first_import`, czyli domyślne `False`; `_compile_reachable_prefix` jest wywoływana wyłącznie w gałęzi `if _compile_on_first_import` (`package_model.py:1918`). Nowy `events.append` jest jawnie osłonięty tym samym warunkiem. Drugi producent sentinela typing guard pozostaje bez zmian, a ordinary path nie emituje nowego eventu. Ordinary scenario event tuples, fingerprints i serialized evidence są zatem niezmienione w tym code path. `EVIDENCE_SEMANTIC_VERSION=cycle-semantics-evidence/4`, `OPTIONAL_EVIDENCE_SEMANTIC_VERSION=cycle-semantics-evidence/5` pozostały bez zmian; receipt schemas także. Nie ma podstaw do zmiany P3-V1 epoch.

## MCP_POST_CHANGE_AUDIT

Watcher: revision 1254 `package_model.py UPDATED`; 1255 test file `UNCHANGED`; 1256 test file `UPDATED`. Oba zmienione source/test symbole mają po zmianie `workspace_sync=verified` przy revision 1256. Końcowy LIVE: canonical revision 1256, state_id `20261109_210842`, syntax errors 0, graph/cycles fresh, 16 structural DFS paths, soft-dependent potential SCC 1; cycle_semantics **stale**. Zachowany graph SHA-256 `2b45d940afccdaefb3c0f4a686b83bcbc2687e0d8b167cadc986106b01eedf6f`; source diff nie dodaje import statements/edges. Hard/optional receipts `None`; poprzedni partial receipt po invalidation również `None`. Warning view revision 1256: structural 16, MODEL_PASS 0, active 16. Fresh structural cycles nie oznaczają świeżej semantyki. Nie uruchomiono FULL ani publikacji.

## FULL_DIFFS

Pełny rzeczywisty git diff obu plików zmienionych w tym zadaniu:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 78a68ab..3a7a46d 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1521,8 +1521,26 @@ def _compile_reachable_prefix(
     ):
         return None
 
+    statement = tree.body[low]
+    location = (
+        statement.decorator_list[0]
+        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
+                                  ast.ClassDef))
+        and statement.decorator_list
+        else statement
+    )
+    line = getattr(location, "lineno", None)
+    column = getattr(location, "col_offset", None)
+
     return accepted + (
-        _Step("UNMODELED_STATEMENT"),
+        _Step(
+            "UNMODELED_STATEMENT",
+            target=type(statement).__name__,
+            source_line=line if type(line) is int and line >= 1 else None,
+            source_column=(
+                column if type(column) is int and column >= 0 else None
+            ),
+        ),
     )
 
 
@@ -2682,6 +2700,18 @@ def evaluate_package_import_order(
             )
 
         elif step.op == "UNMODELED_STATEMENT":
+            if _compile_on_first_import:
+                events.append(PackageModelEvent(
+                    module,
+                    "UNMODELED_STATEMENT",
+                    step.target,
+                    (
+                        f"{step.source_line}:{step.source_column}"
+                        if step.source_line is not None
+                        and step.source_column is not None
+                        else None
+                    ),
+                ))
             return result("UNKNOWN", module)
 
         else:
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index 442e1fa..a3d875d 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -1461,3 +1461,138 @@ def test_g18_p2_p8_no_full_inventory_shortcut():
     assert result.reason == (
         "INVENTORY_SOURCE_DOMAIN_MISMATCH"
     )
+
+
+def _p3_v10_assess(sources, *, assume_external=False):
+    files = frozenset(
+        module.replace(".", "/") + ".py"
+        for module in sources
+    )
+    return evaluate_conditional_namespace_import_order(
+        sources,
+        "ns.a",
+        (SearchPortion("root", files),),
+        target_python_version=(3, 15),
+        assume_passive_external_imports=assume_external,
+    )
+
+
+def test_p3_v10_function_decorator_location():
+    sources = {"ns.a": ast.parse(
+        "from functools import lru_cache\n"
+        "@lru_cache(maxsize=1024)\n"
+        "def parse(value):\n"
+        "    return value\n"
+    )}
+    result = _p3_v10_assess(sources, assume_external=True)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.events[-1].operation == "UNMODELED_STATEMENT"
+    assert result.model_assessment.events[-1].target == "FunctionDef"
+    assert result.model_assessment.events[-1].symbol == "2:1"
+
+
+def test_p3_v10_class_decorator_location():
+    result = _p3_v10_assess({"ns.a": ast.parse(
+        "@decorator\n"
+        "class Thing:\n"
+        "    pass\n"
+    )})
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.events[-1].operation == "UNMODELED_STATEMENT"
+    assert result.model_assessment.events[-1].target == "ClassDef"
+    assert result.model_assessment.events[-1].symbol == "1:1"
+
+
+def test_p3_v10_ordinary_statement_location():
+    result = _p3_v10_assess({"ns.a": ast.parse(
+        "value = 1\n"
+        "raise RuntimeError('stop')\n"
+    )})
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.events[-1].operation == "UNMODELED_STATEMENT"
+    assert result.model_assessment.events[-1].target == "Raise"
+    assert result.model_assessment.events[-1].symbol == "2:0"
+
+
+def test_p3_v10_prior_bind_and_import_retained():
+    result = _p3_v10_assess({
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "import ns.b\n"
+            "raise RuntimeError('stop')\n"
+        ),
+        "ns.b": ast.parse("pass\n"),
+    })
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    events = result.model_assessment.events
+    assert events[-1].operation == "UNMODELED_STATEMENT"
+    assert events[-1].symbol == "3:0"
+    assert any(event.operation == "BIND" and event.symbol == "value"
+               for event in events[:-1])
+    assert any(event.operation == "START_IMPORT" and event.target == "ns.b"
+               for event in events[:-1])
+
+
+def test_p3_v10_external_stop_has_no_provenance_event():
+    result = _p3_v10_assess({"ns.a": ast.parse(
+        "import external_unknown\n"
+        "raise RuntimeError('unreached')\n"
+    )})
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "external_unknown"
+    assert not any(event.operation == "UNMODELED_STATEMENT"
+                   for event in result.model_assessment.events)
+
+
+def test_p3_v10_early_hazard_precedes_unmodeled_statement():
+    result = _p3_v10_assess({
+        "ns.a": ast.parse(
+            "from ns.b import ready\n"
+            "ready = 1\n"
+            "raise RuntimeError('unreached')\n"
+        ),
+        "ns.b": ast.parse("from ns.a import ready\n"),
+    })
+
+    assert result.outcome == "CONDITIONAL_EARLY_BINDING_HAZARD"
+    assert result.model_assessment is not None
+    assert result.model_assessment.events[-1].operation == "EARLY_BINDING_HAZARD"
+    assert not any(event.operation == "UNMODELED_STATEMENT"
+                   for event in result.model_assessment.events)
+
+
+def test_p3_v10_model_pass_has_no_provenance_event():
+    result = _p3_v10_assess({"ns.a": ast.parse("value = 1\n")})
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.model_assessment is not None
+    assert not any(event.operation == "UNMODELED_STATEMENT"
+                   for event in result.model_assessment.events)
+
+
+def test_p3_v10_repeatable_without_ast_mutation():
+    sources = {"ns.a": ast.parse(
+        "value = 1\n"
+        "@decorator\n"
+        "class Thing:\n"
+        "    pass\n"
+    )}
+    before = ast.dump(sources["ns.a"], include_attributes=True)
+
+    first = _p3_v10_assess(sources)
+    second = _p3_v10_assess(sources)
+
+    assert first == second
+    assert first.model_assessment is not None
+    assert first.model_assessment.events[-1].symbol == "2:1"
+    assert ast.dump(sources["ns.a"], include_attributes=True) == before
```

## FINAL_VERDICT

Wymagana provenance jest emitowana tylko na faktycznie osiągniętym sentinelu warunkowej ścieżki, z zachowaniem UNKNOWN i ordinary evidence. Focused tests PASS (117). MCP źródło verified, syntax 0; `cycle_semantics=stale` po watcher update i brak warning suppression authority. STOP.
