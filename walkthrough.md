# P11-I1 — złożone odczyty `ast.Attribute`

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `70153e681c68aca8d464b8afa02c446bb11a3e4d`; przed edycją roboczy `walkthrough.md` był jedyną zmianą. Po edycji `audyt.txt` pojawił się jako zmieniony przez proces zewnętrzny; nie edytowałem go ani nie zaliczam do P11-I1.
- DIRECT_EVIDENCE: Contextor MCP revision 1555 przed zmianą, `canonical_state=fresh`, `workspace_sync=verified` dla trzech modułów produkcyjnych. Aktualne kotwice `_Step`, obu `_compile` i obu interpreterów odpowiadały promptowi. AST audyt wywołań `_Step` w `contextor/` i `tests/` nie znalazł wywołania z więcej niż czterema argumentami pozycyjnymi.
- DIRECT_EVIDENCE: dostępny repozytoryjny `.venv` używa CPython 3.15.2. Systemowy `C:\Python315\python.exe` również ma 3.15.2, lecz nie ma `pytest`; testy uruchomiono przez `.venv`.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/steps.py`
- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/initialization_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_initialization_model.py`

`walkthrough.md` jest wyłącznie raportem. `audyt.txt` ma równoległą zmianę niezwiązaną z tym zadaniem i pozostaje nietknięty.

## IMPLEMENTATION

- CODE_PATH_PROVED: `_Step` i `ModelStep` dostały `attribute_tail` po czwartym dotychczasowym polu. Kompilatory zbierają segmenty `ast.Attribute` od zewnętrznego węzła do `Name`, odwracają je i tworzą jeden krok bez syntetycznych bindingów.
- CODE_PATH_PROVED: interpreter pakietowy odczytuje segmenty po kolei. Każdy zakończony odczyt emituje `ATTR`; brak symbolu w znanym module daje istniejącą klasyfikację hazardu lub `MISSING_ATTRIBUTE`, a nierozpoznany odbiorca daje `UNKNOWN`. Binding celu następuje dopiero po całym łańcuchu.
- CODE_PATH_PROVED: płaski interpreter po potwierdzeniu pierwszego odczytu emituje jego event i dla dalszego segmentu zwraca `UNKNOWN`, bez zapisywania celu. Pierwszy segment nadal może zgłosić hazard.

## SEMANTIC_EVIDENCE

- DIRECT_EVIDENCE: `execution/state.py:10-27` przechowuje pakietowe namespace jako mapy nazw na wartości; `package_model.py:3313-3339` zachowuje wartość przez `ALIAS`; `:3341-3381` rozpoznaje moduł przez klucz namespace. Płaski `initialization_model.py:137-139,181-195` przechowuje tylko zbiory bindingów i aliasy importowanych modułów, nie wynik odczytanego atrybutu.
- DIRECT_EVIDENCE: istniejące helpery testowe uruchamiają import w izolowanym procesie CPythona (`tests/test_cycle_semantics_package_model.py:1375-1415`, `tests/test_cycle_semantics_initialization_model.py:17-30`). Nowe przypadki hazardów porównują model z tym uruchomieniem.
- INFERENCE: `p.a.value` musi odczytać `p.a` przed `.value`; pośredni zwykły obiekt może uruchamiać kod użytkownika przy kolejnym odczycie. Model pakietowy konserwatywnie zwraca `UNKNOWN`, jeśli wartość pośrednia nie identyfikuje znanego modułu. Płaski model nie wnioskuje tożsamości z samej obecności bindingu.
- UNKNOWN: te testy i statyczny model nie stanowią ogólnego dowodu bezpieczeństwa importów ani atestacji środowiska builtins.

## TARGETED_TESTS

- DIRECT_EVIDENCE: nowe testy: 9 passed, 267 deselected na CPython 3.15.2. Pełny zakres dwóch plików modelowych: 276 passed w 17.99 s. Następnie dodatkowy test trzech segmentów: 1 passed w 1.44 s. Nie uruchomiono pełnego pytest suite. `git diff --check` nie zgłosił błędów whitespace.
- DIRECT_EVIDENCE: przypadki obejmują dwa i trzy rozpoznane moduły, pierwszy i późniejszy hazard z CPython parity, pośrednią zwykłą wartość, alias i nadpisanie oraz regresję pojedynczego odczytu. Płaski model obejmuje hazard pierwszego segmentu, `UNKNOWN` po pierwszym odczycie i regresję pojedynczego odczytu.

## MCP_POST_CHANGE

- DIRECT_EVIDENCE: Desktop watcher opublikował zmiany do LIVE revision 1560; `get_module_context` dla trzech plików produkcyjnych oraz obu plików testowych wskazał `canonical_state=fresh`, `workspace_sync=verified` w revision 1560. Rodzina `cycle_semantics=stale` po zmianach, więc nie jest to świeży dowód globalnej semantyki cykli.
- DIRECT_EVIDENCE: po dodatkowej edycji testu trzech segmentów `get_live_events(after_revision=1560)` początkowo zwracał brak eventu, a `get_module_context` dla `tests/test_cycle_semantics_package_model.py` wskazywał `workspace_sync=out_of_sync`. Test uruchomiony bezpośrednio użył aktualnego pliku. Końcową świeżość LIVE należy rozpatrywać według późniejszego sprawdzenia poniżej; bez niego nie deklaruję FINAL PASS.
- UNKNOWN: zmiana kodu repo nie dowodzi, że już działający proces MCP załadował nowy Python. Nie zmieniano kodu serwera MCP i nie wykonywano restartu.

## FULL_DIFFS

Poniżej rzeczywisty pełny `git diff` pięciu plików z FILES_CHANGED, względem HEAD. Raport nie jest w nim uwzględniony.

```diff
diff --git a/contextor/core/cycle_semantics/execution/steps.py b/contextor/core/cycle_semantics/execution/steps.py
index e46a053..f031069 100644
--- a/contextor/core/cycle_semantics/execution/steps.py
+++ b/contextor/core/cycle_semantics/execution/steps.py
@@ -10,6 +10,7 @@ class _Step:
     target: str | None = None
     symbol: str | None = None
     binding: str | None = None
+    attribute_tail: tuple[str, ...] = ()
     explicit_alias: bool = False
     function_body: tuple[_Step, ...] = ()
     function_local: bool = False
diff --git a/contextor/core/cycle_semantics/initialization_model.py b/contextor/core/cycle_semantics/initialization_model.py
index 033873a..3bc2117 100644
--- a/contextor/core/cycle_semantics/initialization_model.py
+++ b/contextor/core/cycle_semantics/initialization_model.py
@@ -17,6 +17,7 @@ class ModelStep:
     target: str | None = None
     symbol: str | None = None
     binding: str | None = None
+    attribute_tail: tuple[str, ...] = ()
 
 
 @dataclass(frozen=True)
@@ -81,15 +82,32 @@ def _compile(tree: ast.Module) -> tuple[ModelStep, ...] | None:
                 type(None), bool, int, float, complex, str, bytes,
             }:
                 steps.append(ModelStep("BIND_CONSTANT", binding=name))
-            elif (
-                isinstance(value, ast.Attribute)
-                and isinstance(value.value, ast.Name)
-                and _valid_name(value.value.id)
-                and _valid_name(value.attr)
-            ):
-                steps.append(ModelStep(
-                    "READ_ATTRIBUTE", value.value.id, value.attr, name,
-                ))
+            elif isinstance(value, ast.Attribute):
+                attributes: list[str] = []
+                receiver: ast.expr = value
+
+                while isinstance(receiver, ast.Attribute):
+                    if not _valid_name(receiver.attr):
+                        return None
+                    attributes.append(receiver.attr)
+                    receiver = receiver.value
+
+                if (
+                    not isinstance(receiver, ast.Name)
+                    or not _valid_name(receiver.id)
+                ):
+                    return None
+
+                attributes.reverse()
+                steps.append(
+                    ModelStep(
+                        "READ_ATTRIBUTE",
+                        receiver.id,
+                        attributes[0],
+                        name,
+                        tuple(attributes[1:]),
+                    )
+                )
             else:
                 return None
         elif isinstance(statement, ast.Pass):
@@ -190,6 +208,16 @@ def evaluate_flat_import_order(
                 )
                 events.append(ModelEvent(module, outcome, target, step.symbol))
                 return result(outcome, target, step.symbol)
+            if step.attribute_tail:
+                events.append(
+                    ModelEvent(
+                        module,
+                        "READ_ATTRIBUTE",
+                        target,
+                        step.symbol,
+                    )
+                )
+                return result("UNKNOWN", target, step.attribute_tail[0])
             bindings[module].add(step.binding)
             aliases[module].pop(step.binding, None)
             events.append(ModelEvent(module, "READ_ATTRIBUTE", target, step.symbol))
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b1464a9..4f163a4 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -832,17 +832,27 @@ def _compile(
                     )
                 )
 
-            elif (
-                isinstance(value, ast.Attribute)
-                and isinstance(value.value, ast.Name)
-                and not value.attr.startswith("__")
-            ):
+            elif isinstance(value, ast.Attribute):
+                attributes: list[str] = []
+                receiver: ast.expr = value
+
+                while isinstance(receiver, ast.Attribute):
+                    if receiver.attr.startswith("__"):
+                        return None
+                    attributes.append(receiver.attr)
+                    receiver = receiver.value
+
+                if not isinstance(receiver, ast.Name):
+                    return None
+
+                attributes.reverse()
                 steps.append(
                     _Step(
                         "ATTR",
-                        value.value.id,
-                        value.attr,
+                        receiver.id,
+                        attributes[0],
                         name,
+                        attribute_tail=tuple(attributes[1:]),
                     )
                 )
             elif (
@@ -3341,45 +3351,53 @@ def evaluate_package_import_order(
         elif step.op == "ATTR":
             reference = namespaces[module].get(step.target)
 
-            if reference not in namespaces:
-                return result(
-                    "UNKNOWN",
-                    step.target,
-                    step.symbol,
-                )
+            for attribute in (step.symbol, *step.attribute_tail):
+                if (
+                    type(reference) is not str
+                    or reference not in namespaces
+                ):
+                    return result(
+                        "UNKNOWN",
+                        step.target,
+                        attribute,
+                    )
 
-            if step.symbol not in namespaces[reference]:
-                outcome = (
-                    "EARLY_BINDING_HAZARD"
-                    if states[reference] == "INITIALIZING"
-                    else "MISSING_ATTRIBUTE"
-                )
+                if attribute not in namespaces[reference]:
+                    outcome = (
+                        "EARLY_BINDING_HAZARD"
+                        if states[reference] == "INITIALIZING"
+                        else "MISSING_ATTRIBUTE"
+                    )
+
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            outcome,
+                            reference,
+                            attribute,
+                        )
+                    )
+
+                    return result(
+                        outcome,
+                        reference,
+                        attribute,
+                    )
+
+                value = namespaces[reference][attribute]
 
                 events.append(
                     PackageModelEvent(
                         module,
-                        outcome,
+                        "ATTR",
                         reference,
-                        step.symbol,
+                        attribute,
                     )
                 )
 
-                return result(
-                    outcome,
-                    reference,
-                    step.symbol,
-                )
-
-            namespaces[module][step.binding] = namespaces[reference][step.symbol]
+                reference = value
 
-            events.append(
-                PackageModelEvent(
-                    module,
-                    "ATTR",
-                    reference,
-                    step.symbol,
-                )
-            )
+            namespaces[module][step.binding] = reference
 
         elif step.op == "UNMODELED_STATEMENT":
             if _compile_on_first_import:
diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
index 2af1589..a0c5cad 100644
--- a/tests/test_cycle_semantics_initialization_model.py
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -141,3 +141,50 @@ def test_iterative_1200_module_chain():
     }
     modules["m1200"] = ast.parse("x=1\n")
     assert evaluate_flat_import_order(modules, "m0").outcome == "MODEL_PASS"
+
+
+def test_nested_attribute_first_segment_hazard(tmp_path):
+    sources = {
+        "alpha": "import beta\nvalue=7",
+        "beta": "import alpha\nx=alpha.value.next",
+    }
+    result = _assess(sources, "alpha")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "EARLY_BINDING_HAZARD", "alpha", "value",
+    )
+    assert not any(
+        event.operation == "READ_ATTRIBUTE" for event in result.events
+    )
+    assert not _actual(tmp_path, sources, "alpha")
+
+
+def test_nested_attribute_known_first_segment_stops_unknown():
+    sources = {
+        "alpha": "import beta\nx=beta.value.next",
+        "beta": "value=7",
+    }
+    result = _assess(sources, "alpha")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "UNKNOWN", "beta", "next",
+    )
+    assert [
+        (event.target, event.symbol)
+        for event in result.events
+        if event.operation == "READ_ATTRIBUTE"
+    ] == [
+        ("beta", "value"),
+    ]
+
+
+def test_single_attribute_flat_model_contract_after_nested_support(tmp_path):
+    sources = {"alpha": "import beta\nx=beta.value", "beta": "value=7"}
+    result = _assess(sources, "alpha")
+    assert result.outcome == "MODEL_PASS"
+    assert [
+        (event.target, event.symbol)
+        for event in result.events
+        if event.operation == "READ_ATTRIBUTE"
+    ] == [
+        ("beta", "value"),
+    ]
+    assert _actual(tmp_path, sources, "alpha")
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 8089fb9..007c9a8 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -3357,3 +3357,108 @@ def test_p9_i1_known_builtin_decorator_identity(
             _actual(tmp_path, sources, "pkg")
             is python_success
         )
+
+
+def test_nested_attribute_reads_two_known_modules(tmp_path):
+    source = {
+        "route.__init__": "pass",
+        "route.leaf": "value=7",
+        "entry": "import route.leaf\nx=route.leaf.value",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert [(e.target, e.symbol) for e in result.events if e.operation == "ATTR"] == [
+        ("route", "leaf"), ("route.leaf", "value"),
+    ]
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_nested_attribute_reads_three_known_modules(tmp_path):
+    source = {
+        "tree.__init__": "pass",
+        "tree.branch.__init__": "pass",
+        "tree.branch.leaf": "value=9",
+        "entry": "import tree.branch.leaf\nx=tree.branch.leaf.value",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert [(e.target, e.symbol) for e in result.events if e.operation == "ATTR"] == [
+        ("tree", "branch"),
+        ("tree.branch", "leaf"),
+        ("tree.branch.leaf", "value"),
+    ]
+    assert _actual(tmp_path, source, "entry")
+
+
+def test_nested_attribute_first_segment_initializing_hazard(tmp_path):
+    source = {
+        "route.__init__": "import route.consumer\na=1",
+        "route.consumer": "import route\nx=route.a.value",
+    }
+    result = _model(source, "route")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "EARLY_BINDING_HAZARD", "route", "a",
+    )
+    assert not any(e.operation == "ATTR" for e in result.events)
+    assert not _actual(tmp_path, source, "route")
+
+
+def test_nested_attribute_later_segment_initializing_hazard(tmp_path):
+    source = {
+        "route.__init__": "import route\na=route\nimport route.consumer\nvalue=7",
+        "route.consumer": "import route\nx=route.a.value",
+    }
+    result = _model(source, "route")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "EARLY_BINDING_HAZARD", "route", "value",
+    )
+    assert [(e.operation, e.target, e.symbol) for e in result.events if e.operation in {"ATTR", "EARLY_BINDING_HAZARD"}] == [
+        ("ATTR", "route", "a"),
+        ("EARLY_BINDING_HAZARD", "route", "value"),
+    ]
+    assert not _actual(tmp_path, source, "route")
+
+
+def test_nested_attribute_unknown_after_ordinary_value(tmp_path):
+    source = {
+        "route.__init__": "a=3",
+        "entry": "import route\nx=route.a.value",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "UNKNOWN"
+    assert result.symbol == "value"
+    assert [(e.target, e.symbol) for e in result.events if e.operation == "ATTR"] == [
+        ("route", "a"),
+    ]
+    assert not _actual(tmp_path, source, "entry")
+
+
+def test_nested_attribute_alias_and_overwrite(tmp_path):
+    source = {
+        "route.__init__": "pass",
+        "route.leaf": "value=7",
+        "entry": "import route.leaf\nalias=route\nx=alias.leaf.value",
+    }
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert [(e.target, e.symbol) for e in result.events if e.operation == "ATTR"] == [
+        ("route", "leaf"), ("route.leaf", "value"),
+    ]
+    assert _actual(tmp_path, source, "entry")
+
+    overwritten = dict(source)
+    overwritten["entry"] = "import route.leaf\ntmp=route.leaf\ntmp=3\nx=tmp.value"
+    result = _model(overwritten, "entry")
+    assert result.outcome == "UNKNOWN"
+    assert not any(e.operation == "ATTR" and e.symbol == "value" for e in result.events)
+    assert not _actual(tmp_path, overwritten, "entry")
+
+
+def test_single_attribute_event_contract_after_nested_support(tmp_path):
+    source = {"route.__init__": "value=7", "entry": "import route\nx=route.value"}
+    result = _model(source, "entry")
+    assert result.outcome == "MODEL_PASS"
+    assert [(e.target, e.symbol) for e in result.events if e.operation == "ATTR"] == [
+        ("route", "value"),
+    ]
+    assert _actual(tmp_path, source, "entry")
```

## FINAL_STATUS

- DIRECT_EVIDENCE: końcowy Contextor MCP: LIVE revision 1563, canonical_state=fresh i workspace_sync=verified dla obu testów i package_model.py; desktop_watcher revision 1561 potwierdza ostatnią zmianę testu pakietowego. Wcześniejsze odczyty potwierdziły verified pozostałych dwóch modułów produkcyjnych. cycle_semantics=stale ogranicza globalną certyfikację.
- DIRECT_EVIDENCE: testy dwóch modeli przeszły na aktualnym kodzie dyskowym; nie wykonano commit, push, zmiany indeksu Git ani restartu.
- UNKNOWN: adopcja kodu przez już działający proces MCP nie jest potwierdzona. Status implementacji i testów celowanych: PASS; globalna semantyka LIVE: STALE.
