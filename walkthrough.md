# P10-FINAL-R3-I1 — CLASS DECORATOR OUTCOME CONTRACT

## PREFLIGHT

- DIRECT_EVIDENCE — Contextor MCP przed zmianą: LIVE revision **1538**, `canonical_state=fresh`, provenance=live, syntax errors 0/fresh. `execution/calls.py`, `package_model.py` i `tests/test_cycle_semantics_external_call_effects.py`: `workspace_sync=verified`.
- DIRECT_EVIDENCE — `git rev-parse HEAD=6df29a3f09ae505d12e2d55067120a4f3cbdf7f2`; `git status --short` przed zmianą pusty. Stan I2 obecny w HEAD, bez przywracania plików. Aktualne anchory pasują: `calls.py` po `_CallOutcomeContract`; `package_model.py` import, rekord, `_compile` przed `if not conditional_dataclass`, stan po `definition_decorator_snapshots`, gałęzie `CHECK_DATACLASS_FIELD_FACTORY` i `DEFINE_CONDITIONAL_FROZEN_DATACLASS`; testy na końcu pliku.
- CODE_PATH_PROVED — kontrakt opisuje oddzielnie wywołanie factory `dataclass(frozen=True)`, zastosowanie do gotowej klasy i tożsamość wyniku. CPython 3.15.2 `C:\\Python315\\Lib\\dataclasses.py:1434-1462` tworzy `wrap`, `1002-1250` przetwarza klasę i przy `slots=False` zwraca `cls`. Podmieniony dekorator zwracający `None` z R3 narusza `EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION` oraz `INPUT_CLASS`; nie jest świadkiem przy prawdziwym pełnym kontrakcie.

## FILES_CHANGED

1. `contextor/core/cycle_semantics/execution/calls.py`: dokładny `_ClassDecoratorOutcomeContract` i stały kontrakt standardowej frozen dataclass.
2. `contextor/core/cycle_semantics/package_model.py`: import kontraktu, sześć pól w rekordzie, snapshot factory przed ciałem klasy, stan indeksowany definition_id, pojedyncza konsumpcja przy dekoracji i zapis jawnego założenia rezultatu.
3. `tests/test_cycle_semantics_external_call_effects.py`: dokładnie dwa dopisane testy, bez zmiany istniejących asercji.
4. `walkthrough.md`: raport; jego własny diff pominięty poniżej.

## TARGETED_TESTS

Wymagane komendy, kolejno, CPython 3.15.2:

1. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_call_effects.py` — **12 passed**.
2. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k "p8 or p9 or r11 or frozen_dataclass"` — **63 passed, 178 deselected**.
3. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_namespace_bound_model.py -k "dataclass or p8 or p9"` — **39 passed, 25 deselected**.
4. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_annotation_union_i1.py tests/test_cycle_semantics_conditional_class_identity_i2.py` — **50 passed**.
5. `git diff --check` na trzech plikach — exit 0. Bez pełnego pytest i FULL.

## POST_CHANGE_MCP

- DIRECT_EVIDENCE — Contextor MCP po watcherze: `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo",fields=[])`: LIVE revision **1541**, `canonical_state=fresh`, syntax errors **0/fresh**, advisory warning null. Rodzina `cycle_semantics=stale` nie jest oceną aktualnego testu ani modelu.
- DIRECT_EVIDENCE — `get_module_context` dla wszystkich trzech zmienionych plików na finalnym revision 1541: `workspace_sync=verified`, `canonical_state=fresh`. W przejściowym odczycie na revision 1540 test miał `out_of_sync`; sekwencyjny odczyt po zdarzeniu watchera na 1541 potwierdził `verified`.
- DIRECT_EVIDENCE — `get_symbol_lineage` rozwiązał na LIVE `contextor.core.cycle_semantics.execution.calls::_ClassDecoratorOutcomeContract` (artifact `A9576/1`); definicja i użycie konstruktora są w `calls.py`. Lineage statyczny nie dowodzi kolejności runtime; tę potwierdzono kompilacją AST i ścieżką kodu.
- CODE_PATH_PROVED + obserwacja modelu — dla źródła `from dataclasses import dataclass, field; @dataclass(frozen=True) class C: x: int = field()`, bez uruchamiania analizowanego pakietu: `_compile(..., annotation_semantics="DEFERRED", assume_frozen_dataclass=True)` zwrócił kolejno `PREPARE_FROM_MEMBER, PREPARE_FROM_MEMBER, FROM(dataclass), FROM(field), SNAPSHOT_CONDITIONAL_CLASS_DECORATOR_FACTORY(definition_id="pkg:3:0"), CHECK_DATACLASS_FIELD_FACTORY(field), BIND(x,class_local), DEFINE_CONDITIONAL_FROZEN_DATACLASS(definition_id="pkg:3:0")`. Snapshot nie emituje eventu nieznanego kodu. To **dowód kolejności kroków modelu**, nie obserwacja importu CPython.
- CODE_PATH_PROVED — snapshot sprawdza aktualne wiązanie factory przed ciałem klasy i zapisuje kontrakt pod definition_id. `DEFINE_CONDITIONAL_FROZEN_DATACLASS` usuwa go przez `pop(definition_id,None)`, sprawdza `return_identity="INPUT_CLASS"`, następnie konsumuje adnotacje i zapisuje sześć jawnych pól rekordu. Drugi odczyt tego samego ID nie otrzyma już kontraktu. Istniejące eventy `ASSUMED_FROZEN_DATACLASS_DECORATION` i `DEFINE_PASSIVE_CLASS` oraz ich kolejność pozostały.
- CONTRACT_PROVED — `factory` i `application` są **jawnymi założeniami** dla importowanego dekoratora; model nie atestuje realnego `sys.modules`, obiektu callable ani efektów runtime. Symboliczna tożsamość klasy po dekoracji jest warunkowa względem `INPUT_CLASS`. Zwykły pipeline ostrzeżeń wywołuje model bez tych prywatnych założeń (`scenarios.py:329-358`); namespace wrapper mapuje wewnętrzny `MODEL_PASS` na `CONDITIONAL_MODEL_PASS` (`package_model.py:3793-3819`), source-bound wrapper go nie promuje (`namespace_bound_model.py:220-247`). Brak bezwarunkowego warning suppression.
- GRANICA: pozytywne targeted tests dowodzą zgodności z określonymi przypadkami i regresjami, nie autorytetu runtime. Faktyczne wykonanie CPython 3.15.2 ze standardowym `dataclass` i podmienionym dekoratorem z R3 jest odrębną obserwacją; ten drugi nie spełnia nowego kontraktu.

## FULL_DIFFS

Pełne rzeczywiste diffy source/tests względem HEAD; `walkthrough.md` jako raport pominięty:

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 1b74406..7a68be3 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -33,6 +33,42 @@ class _CallOutcomeContract:
     lifecycle: str
 
 
+@dataclass(frozen=True)
+class _ClassDecoratorOutcomeContract:
+    factory: _CallOutcomeContract
+    application: _CallOutcomeContract
+    return_identity: str
+
+
+_FROZEN_DATACLASS_DECORATOR_CONTRACT = (
+    _ClassDecoratorOutcomeContract(
+        factory=_CallOutcomeContract(
+            invocation=(
+                "NO_UNMODELED_FACTORY_EFFECTS_OR_EXCEPTIONS"
+            ),
+            result=(
+                "EXACT_STANDARD_FROZEN_DATACLASS_DECORATOR"
+            ),
+            lifecycle=(
+                "NO_UNKNOWN_EFFECTS_BEFORE_APPLICATION"
+            ),
+        ),
+        application=_CallOutcomeContract(
+            invocation=(
+                "NO_UNMODELED_DECORATION_EFFECTS_OR_EXCEPTIONS"
+            ),
+            result=(
+                "EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION"
+            ),
+            lifecycle=(
+                "NO_UNKNOWN_EFFECTS_BEFORE_CLASS_BINDING"
+            ),
+        ),
+        return_identity="INPUT_CLASS",
+    )
+)
+
+
 _CALL_OUTCOME_CONTRACTS = {
     "PASSIVE_PROPERTY": _CallOutcomeContract(
         invocation=(
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 22c7c74..ab365a7 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -69,6 +69,8 @@ from .execution.lifecycle import (
 from .execution.calls import (
     _CALL_OUTCOME_CONTRACTS,
     _CallableEffectFact,
+    _ClassDecoratorOutcomeContract,
+    _FROZEN_DATACLASS_DECORATOR_CONTRACT,
     _RestrictedFunction,
     _execute_restricted_call,
     _execute_restricted_object_call,
@@ -105,6 +107,12 @@ class AssumedFrozenDataclassDecoration:
     decorator: str
     line: int
     column: int
+    factory_invocation_semantics: str
+    factory_result_semantics: str
+    application_invocation_semantics: str
+    application_result_semantics: str
+    application_lifecycle_semantics: str
+    returned_class_identity: str
 
 
 @dataclass(frozen=True)
@@ -943,6 +951,17 @@ def _compile(
                 ):
                     return None
 
+            if conditional_dataclass:
+                steps.append(
+                    _Step(
+                        "SNAPSHOT_CONDITIONAL_CLASS_DECORATOR_FACTORY",
+                        target=stmt.decorator_list[0].func.id,
+                        definition_id=definition_id,
+                        source_line=stmt.decorator_list[0].lineno,
+                        source_column=stmt.decorator_list[0].col_offset,
+                    )
+                )
+
             if not conditional_dataclass:
                 if ordinary_named_decorators:
                     steps.append(
@@ -1893,6 +1912,10 @@ def evaluate_package_import_order(
         definition_state.definition_decorator_snapshots
     )
 
+    conditional_class_decorator_outcomes: dict[
+        str, _ClassDecoratorOutcomeContract
+    ] = {}
+
     bootstrap = "\x00ENTRY"
     execution_cursor = _new_execution_cursor(bootstrap)
     frames = execution_cursor.frames
@@ -2682,6 +2705,28 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == (
+            "SNAPSHOT_CONDITIONAL_CLASS_DECORATOR_FACTORY"
+        ):
+            if (
+                not _assume_frozen_dataclass_decoration
+                or not step.definition_id
+                or not step.target
+                or step.definition_id
+                in conditional_class_decorator_outcomes
+                or namespaces[module].get(step.target)
+                != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
+            conditional_class_decorator_outcomes[
+                step.definition_id
+            ] = _FROZEN_DATACLASS_DECORATOR_CONTRACT
+
         elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
             if (
                 not step.target
@@ -2715,11 +2760,29 @@ def evaluate_package_import_order(
                 )
 
         elif step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS":
+            if not step.definition_id or not step.binding:
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.binding,
+                )
+
+            decorator_contract = (
+                conditional_class_decorator_outcomes.pop(
+                    step.definition_id,
+                    None,
+                )
+            )
+
             if (
-                namespaces[module].get("dataclass")
-                != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
+                decorator_contract is None
+                or decorator_contract.return_identity != "INPUT_CLASS"
             ):
-                return result("UNKNOWN", module, step.binding)
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.binding,
+                )
 
             class_bindings = {
                 "__module__": _Scalar(module),
@@ -2770,6 +2833,24 @@ def evaluate_package_import_order(
                     decorator="dataclasses.dataclass(frozen=True)",
                     line=step.source_line,
                     column=step.source_column,
+                    factory_invocation_semantics=(
+                        decorator_contract.factory.invocation
+                    ),
+                    factory_result_semantics=(
+                        decorator_contract.factory.result
+                    ),
+                    application_invocation_semantics=(
+                        decorator_contract.application.invocation
+                    ),
+                    application_result_semantics=(
+                        decorator_contract.application.result
+                    ),
+                    application_lifecycle_semantics=(
+                        decorator_contract.application.lifecycle
+                    ),
+                    returned_class_identity=(
+                        decorator_contract.return_identity
+                    ),
                 )
             )
             namespaces[module][step.binding] = (
diff --git a/tests/test_cycle_semantics_external_call_effects.py b/tests/test_cycle_semantics_external_call_effects.py
index 5f950fa..e56e1d1 100644
--- a/tests/test_cycle_semantics_external_call_effects.py
+++ b/tests/test_cycle_semantics_external_call_effects.py
@@ -233,3 +233,77 @@ def test_property_contract_includes_result_and_lifecycle():
     assert row.result_lifecycle_semantics == (
         "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
     )
+
+
+def test_frozen_class_decorator_outcome_is_explicit():
+    source = (
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+        "@dataclass(frozen=True)\n"
+        "class D:\n"
+        "    y: C | None\n"
+        "import pkg.child\n"
+    )
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse(
+                "from pkg import D\n"
+            ),
+        },
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert tuple(
+        row.class_name
+        for row in result.assumed_dataclass_decorations
+    ) == ("C", "D")
+
+    for row in result.assumed_dataclass_decorations:
+        assert row.factory_invocation_semantics == (
+            "NO_UNMODELED_FACTORY_EFFECTS_OR_EXCEPTIONS"
+        )
+        assert row.factory_result_semantics == (
+            "EXACT_STANDARD_FROZEN_DATACLASS_DECORATOR"
+        )
+        assert row.application_invocation_semantics == (
+            "NO_UNMODELED_DECORATION_EFFECTS_OR_EXCEPTIONS"
+        )
+        assert row.application_result_semantics == (
+            "EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION"
+        )
+        assert row.application_lifecycle_semantics == (
+            "NO_UNKNOWN_EFFECTS_BEFORE_CLASS_BINDING"
+        )
+        assert row.returned_class_identity == "INPUT_CLASS"
+
+    assert result.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+
+
+def test_rebound_class_decorator_has_no_outcome_fact():
+    result = _run(
+        "from dataclasses import dataclass\n"
+        "dataclass = None\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "C"
+        for event in result.events
+    )
```

## WERDYKT

**PASS** dla dosłownego zakresu I1. Zmienione pliki mają świeży LIVE i pełny diff; wynik warunkowy nadal zależy od jawnych, nieatestowanych założeń.
