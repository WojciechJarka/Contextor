# P10-FINAL-R3-I2 — DECLARED DECORATOR FACTORY SEMANTICS

## PREFLIGHT

- DIRECT_EVIDENCE — Contextor MCP jako pierwsze źródło: LIVE revision **1541**, `canonical_state=fresh`, syntax errors 0/fresh; wszystkie osiem wskazanych plików source/tests miało `workspace_sync=verified`.
- DIRECT_EVIDENCE — `git rev-parse HEAD=068143ba1dd3b1fe4b67c45df59f47e1d374a341`; przed zadaniem `git status --short` wykazywał tylko `walkthrough.md`. I1 jest w HEAD; żadnych plików nie przywracano. Anchory produkcyjne i wymienione funkcje testowe odpowiadały lokalnemu LIVE.
- SEMANTIC_INTEGRITY_CHECK — rozpoznanie `@name(frozen=True)` pozostaje kontrolą AST; deklaracja `(import_module, imported_symbol) → FROZEN_DATACLASS_DECORATOR_FACTORY` stanowi jawne założenie pełnej semantyki standardowej fabryki, aplikacji i tożsamości wyniku, bez atestacji runtime. To zamknięty kontrakt własności CPython, a nie whitelist nazw Contextora. Nie jest to dowód realnej tożsamości importu.

## FILES_CHANGED

W tym zadaniu zmieniono literalnie wskazane pliki: `contextor/core/cycle_semantics/execution/calls.py`, `contextor/core/cycle_semantics/execution/definition_checks.py`, `contextor/core/cycle_semantics/package_model.py`, `tests/test_cycle_semantics_package_model.py`, `tests/test_cycle_semantics_namespace_bound_model.py`, `tests/test_cycle_semantics_class_decorator_staging.py`, `tests/test_cycle_semantics_class_decorator_import_admission.py`, `tests/test_cycle_semantics_external_call_effects.py`, oraz raport `walkthrough.md`. Żadnych innych plików nie zmieniono.

## TARGETED_TESTS

Wykonano kolejno do pierwszego niepowodzenia:

1. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_call_effects.py` — **16 passed**.
2. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py` — **1 failed, 240 passed**. Dokładna porażka:

```text
FAILED tests/test_cycle_semantics_package_model.py::test_frozen_dataclass_direct_conditional_record
tests/test_cycle_semantics_package_model.py:143: AssertionError
assert result.evidence_scope == (
    "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
    "ASSUMPTIONS_NOT_RUNTIME_PROOF"
)
actual: "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
expected: "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF"
```

- CODE_PATH_PROVED — ta sama funkcja otrzymała zgodnie z pkt 8 instrukcji `_assumed_external_callable_effects=FROZEN_FACTORY_EFFECTS`. Snapshot konsumuje fakt przez `accept_callable_effect`, co zapisuje `AssumedExternalCallEffect`; `result()` dopisuje suffix, gdy lista jest niepusta (`package_model.py:1557-1638,2719-2745`). To oczekiwane warunkowe evidence, lecz instrukcja dopuściła zmianę oczekiwanego scope tylko w czterech innych funkcjach i zakazała zmieniać pozostałe oczekiwania. Właśnie ten kontrakt testu pozostał sprzeczny z wymaganą zmianą fixture.
- STOP/BLOCKED: zgodnie z pkt 13 nie edytowano asercji po porażce. Nie uruchomiono pozostałych trzech komend: pełnego wskazanego pliku namespace-bound, pary class-decorator oraz trzech plików annotation/union/identity. Bez pełnego pytest i FULL.
- Odczytowe `git diff --check` dla ośmiu plików zakończyło się exit 0.

## POST_CHANGE_MCP

- DIRECT_EVIDENCE — po watcherze `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo",fields=[])`: LIVE revision **1550**, `canonical_state=fresh`, syntax errors **0/fresh**. `cycle_semantics=stale` jest osobną rodziną; nie należy z niej wyciągać wniosku o wynikach testów. Przejściowe odczyty revision 1548–1549 miały `unverified` podczas aktualizacji watchera; ponowny odczyt na 1550 potwierdził `workspace_sync=verified` dla wszystkich ośmiu plików.
- DIRECT_EVIDENCE — `get_symbol_lineage(mode="preview")` na LIVE 1550 rozwiązał `_CallableEffectFact`, nową `_restricted_frozen_class_factory_call` i `evaluate_package_import_order`. Lokalny source potwierdza producer/consumer.
- CODE_PATH_PROVED — `definition_checks.py:6-24` sprawdza kształt `ast.Call` z identyfikatorem, `frozen=True` i bez dodatkowych argumentów, bez nazwy `dataclass`. `package_model.py:311,908` używa nowego helpera; `954-965` emituje snapshot przed ciałem. `package_model.py:2175-2210` tworzy `_CallableEffectFact` tylko po jawnej mapie efektów dla zewnętrznego FROM, z `import_origin` oraz `canonical_identity=None`. `package_model.py:2719-2745` bierze aktualny fakt z namespace, wymaga `import_origin` i `accept_callable_effect(...,"FROZEN_DATACLASS_DECORATOR_FACTORY")`, po czym zapisuje kontrakt i pochodzenie pod definition_id. Stare porównanie do `\\x00ASSUMED_EXTERNAL:dataclasses:dataclass` nie występuje w mechanizmie autoryzacji factory (odczytowe `rg` nie znalazło go w `package_model.py`).
- CODE_PATH_PROVED — `package_model.py:2794-2865` pobiera zapisany stan przez `pop(definition_id,None)`, wymaga `return_identity="INPUT_CLASS"` i zapisuje dekorator z `import_origin`; dalej zachowuje symboliczną klasę i kolejność eventów. `ALIAS` kopiuje fakt, a `BIND`/rebind go zastępuje (`package_model.py:3265-3295`); pierwsza grupa testów objęła również nowy alias i rebinding.
- CODE_PATH_PROVED — fakt zewnętrzny zapisuje użyty kontrakt w `assumed_external_call_effects` i warunkowy suffix `evidence_scope`; nie jest runtime proof. `evaluate_conditional_namespace_import_order` mapuje wewnętrzny `MODEL_PASS` na `CONDITIONAL_MODEL_PASS` (`package_model.py:3910-3930`), a standardowa ścieżka scenariuszy wywołuje model bez prywatnych flag (`scenarios.py:329-358`); brak promocji do bezwarunkowego warning suppression.

## SEMANTIC_BOUNDARY

- Zmiana produkcyjna usuwa autoryzację factory na podstawie literalnej nazwy importu; nadal wymaga opt-in ograniczonego modelu klasy oraz **osobnej, jawnej** deklaracji pełnej semantyki factory. Zewnętrzny import sam nie stanowi dowodu Call. Wnioski są warunkowe względem prawdziwości deklaracji caller.
- Wynik testu wskazuje sprzeczność instrukcji fixture/assertion, a nie potwierdzony błąd semantyki CPython czy runtime. Dla tego samego testu źródło testu poleca deklarować efekt factory, ale zakazuje dopisania suffixu w jego asercji. Brak autoryzacji do zmiany tej asercji w tym etapie jest dokładną przyczyną blokady.
- Pozostałe trzy wymagane grupy testów są **NOT_RUN**. Nie można ogłosić PASS ani pełnej regresji. Nie zmieniano kontraktów/oczekiwań po pierwszej porażce.

## FULL_DIFFS

Pełne rzeczywiste diffy wszystkich ośmiu plików source/tests względem HEAD; `walkthrough.md` jako raport nie ma własnego diffu:

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 7a68be3..51b1c40 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -94,6 +94,9 @@ _CALL_OUTCOME_CONTRACTS = {
                 "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
             ),
         ),
+    "FROZEN_DATACLASS_DECORATOR_FACTORY": (
+        _FROZEN_DATACLASS_DECORATOR_CONTRACT.factory
+    ),
 }
 
 
diff --git a/contextor/core/cycle_semantics/execution/definition_checks.py b/contextor/core/cycle_semantics/execution/definition_checks.py
index 31c555d..78835e1 100644
--- a/contextor/core/cycle_semantics/execution/definition_checks.py
+++ b/contextor/core/cycle_semantics/execution/definition_checks.py
@@ -3,13 +3,14 @@ from __future__ import annotations
 import ast
 
 
-def _exact_frozen_dataclass_decorator(
+def _restricted_frozen_class_factory_call(
     decorator: ast.AST,
 ) -> bool:
     return (
         isinstance(decorator, ast.Call)
         and isinstance(decorator.func, ast.Name)
-        and decorator.func.id == "dataclass"
+        and decorator.func.id.isidentifier()
+        and not decorator.func.id.startswith("__")
         and not decorator.args
         and len(decorator.keywords) == 1
         and decorator.keywords[0].arg == "frozen"
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index ab365a7..b1464a9 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -31,7 +31,7 @@ from .execution.expressions import (
     _safe_annassign,
 )
 from .execution.definition_checks import (
-    _exact_frozen_dataclass_decorator,
+    _restricted_frozen_class_factory_call,
     _restricted_defaultless_dataclass_field_call,
 )
 from .execution.annotation_effects import (
@@ -308,7 +308,7 @@ def _safe_passive_class_definition(
         allow_conditional_frozen_dataclass
         and annotation_semantics == "DEFERRED"
         and len(statement.decorator_list) == 1
-        and _exact_frozen_dataclass_decorator(
+        and _restricted_frozen_class_factory_call(
             statement.decorator_list[0]
         )
     )
@@ -905,7 +905,7 @@ def _compile(
                 assume_frozen_dataclass
                 and annotation_semantics == "DEFERRED"
                 and len(stmt.decorator_list) == 1
-                and _exact_frozen_dataclass_decorator(
+                and _restricted_frozen_class_factory_call(
                     stmt.decorator_list[0]
                 )
             )
@@ -1531,6 +1531,12 @@ def evaluate_package_import_order(
     bindings. The evaluator does not attest the actual contents of
     __builtins__, builtins, or the import environment, and cannot certify
     general Python import safety.
+    The frozen-dataclass option enables a restricted
+    class model; it does not establish imported
+    decorator identity or call outcome. An external
+    decorator factory requires an explicit
+    assumed_external_callable_effects declaration.
+    The declared behavior is not runtime-attested.
     """
     events: list[PackageModelEvent] = []
     assumed_external_imports: list[ReachedUnmodeledImport] = []
@@ -1913,7 +1919,11 @@ def evaluate_package_import_order(
     )
 
     conditional_class_decorator_outcomes: dict[
-        str, _ClassDecoratorOutcomeContract
+        str,
+        tuple[
+            _ClassDecoratorOutcomeContract,
+            tuple[str, str],
+        ],
     ] = {}
 
     bootstrap = "\x00ENTRY"
@@ -2708,14 +2718,24 @@ def evaluate_package_import_order(
         elif step.op == (
             "SNAPSHOT_CONDITIONAL_CLASS_DECORATOR_FACTORY"
         ):
+            callable_value = (
+                namespaces[module].get(step.target)
+                if step.target
+                else None
+            )
+
             if (
                 not _assume_frozen_dataclass_decoration
                 or not step.definition_id
                 or not step.target
                 or step.definition_id
                 in conditional_class_decorator_outcomes
-                or namespaces[module].get(step.target)
-                != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
+                or type(callable_value) is not _CallableEffectFact
+                or callable_value.import_origin is None
+                or not accept_callable_effect(
+                    callable_value,
+                    "FROZEN_DATACLASS_DECORATOR_FACTORY",
+                )
             ):
                 return result(
                     "UNKNOWN",
@@ -2725,7 +2745,10 @@ def evaluate_package_import_order(
 
             conditional_class_decorator_outcomes[
                 step.definition_id
-            ] = _FROZEN_DATACLASS_DECORATOR_CONTRACT
+            ] = (
+                _FROZEN_DATACLASS_DECORATOR_CONTRACT,
+                callable_value.import_origin,
+            )
 
         elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
             if (
@@ -2767,17 +2790,25 @@ def evaluate_package_import_order(
                     step.binding,
                 )
 
-            decorator_contract = (
+            decorator_state = (
                 conditional_class_decorator_outcomes.pop(
                     step.definition_id,
                     None,
                 )
             )
 
-            if (
-                decorator_contract is None
-                or decorator_contract.return_identity != "INPUT_CLASS"
-            ):
+            if decorator_state is None:
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.binding,
+                )
+
+            decorator_contract, import_origin = (
+                decorator_state
+            )
+
+            if decorator_contract.return_identity != "INPUT_CLASS":
                 return result(
                     "UNKNOWN",
                     module,
@@ -2830,7 +2861,12 @@ def evaluate_package_import_order(
                 AssumedFrozenDataclassDecoration(
                     module=module,
                     class_name=step.binding,
-                    decorator="dataclasses.dataclass(frozen=True)",
+                    decorator=(
+                        import_origin[0]
+                        + "."
+                        + import_origin[1]
+                        + "(frozen=True)"
+                    ),
                     line=step.source_line,
                     column=step.source_column,
                     factory_invocation_semantics=(
diff --git a/tests/test_cycle_semantics_class_decorator_import_admission.py b/tests/test_cycle_semantics_class_decorator_import_admission.py
index 0f20555..f8046fc 100644
--- a/tests/test_cycle_semantics_class_decorator_import_admission.py
+++ b/tests/test_cycle_semantics_class_decorator_import_admission.py
@@ -235,12 +235,17 @@ def test_n_conditional_frozen_dataclass_path_is_unchanged():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                "FROZEN_DATACLASS_DECORATOR_FACTORY",
+        },
     )
 
     assert result.outcome == "MODEL_PASS"
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     assert len(result.assumed_dataclass_decorations) == 1
     assert result.assumed_dataclass_decorations[0].class_name == "Record"
diff --git a/tests/test_cycle_semantics_class_decorator_staging.py b/tests/test_cycle_semantics_class_decorator_staging.py
index 9bede4b..8f902e8 100644
--- a/tests/test_cycle_semantics_class_decorator_staging.py
+++ b/tests/test_cycle_semantics_class_decorator_staging.py
@@ -131,11 +131,16 @@ def test_qualified_conditional_frozen_dataclass_unchanged():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                "FROZEN_DATACLASS_DECORATOR_FACTORY",
+        },
     )
     assert result.outcome == "MODEL_PASS"
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     assert len(result.assumed_dataclass_decorations) == 1
     assert result.assumed_dataclass_decorations[0].class_name == "Graph"
diff --git a/tests/test_cycle_semantics_external_call_effects.py b/tests/test_cycle_semantics_external_call_effects.py
index e56e1d1..80b9fcb 100644
--- a/tests/test_cycle_semantics_external_call_effects.py
+++ b/tests/test_cycle_semantics_external_call_effects.py
@@ -7,9 +7,19 @@ from contextor.core.cycle_semantics.package_model import (
 
 FIELD_EFFECT = "PASSIVE_DEFAULTLESS_DATACLASS_FIELD"
 PROPERTY_EFFECT = "PASSIVE_PROPERTY"
+FACTORY_EFFECT = (
+    "FROZEN_DATACLASS_DECORATOR_FACTORY"
+)
 
 
 def _run(source, effects=None):
+    declared_effects = {
+        ("dataclasses", "dataclass"): FACTORY_EFFECT,
+    }
+
+    if effects is not None:
+        declared_effects.update(effects)
+
     return evaluate_package_import_order(
         {
             "pkg.__init__": ast.parse(source),
@@ -22,7 +32,9 @@ def _run(source, effects=None):
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
-        _assumed_external_callable_effects=effects,
+        _assumed_external_callable_effects=(
+            declared_effects
+        ),
     )
 
 
@@ -45,7 +57,10 @@ def test_import_success_is_not_call_effect_proof():
     )
 
     assert result.outcome == "UNKNOWN"
-    assert result.assumed_external_call_effects == ()
+    assert tuple(
+        row.effect
+        for row in result.assumed_external_call_effects
+    ) == (FACTORY_EFFECT,)
     assert not any(
         event.operation
         == "ASSUMED_FROZEN_DATACLASS_DECORATION"
@@ -63,8 +78,13 @@ def test_declared_effect_preserves_field():
     )
 
     assert result.outcome == "MODEL_PASS"
-    assert len(result.assumed_external_call_effects) == 1
-    row = result.assumed_external_call_effects[0]
+    field_rows = tuple(
+        row
+        for row in result.assumed_external_call_effects
+        if row.effect == FIELD_EFFECT
+    )
+    assert len(field_rows) == 1
+    row = field_rows[0]
     assert (
         row.import_module,
         row.imported_symbol,
@@ -93,9 +113,10 @@ def test_declared_effect_is_independent_of_import_name():
     )
 
     assert result.outcome == "MODEL_PASS"
-    assert (
-        result.assumed_external_call_effects[0].import_module
-        == "some_external_module"
+    assert any(
+        row.import_module == "some_external_module"
+        and row.effect == FIELD_EFFECT
+        for row in result.assumed_external_call_effects
     )
 
 
@@ -109,7 +130,10 @@ def test_rebinding_invalidates_callable_fact():
     )
 
     assert result.outcome == "UNKNOWN"
-    assert result.assumed_external_call_effects == ()
+    assert tuple(
+        row.effect
+        for row in result.assumed_external_call_effects
+    ) == (FACTORY_EFFECT,)
 
 
 def test_wrong_effect_does_not_authorize_call():
@@ -155,9 +179,9 @@ def test_imported_property_needs_own_effect_proof():
 
     assert without.outcome == "UNKNOWN"
     assert with_contract.outcome == "MODEL_PASS"
-    assert (
-        with_contract.assumed_external_call_effects[0].effect
-        == PROPERTY_EFFECT
+    assert any(
+        row.effect == PROPERTY_EFFECT
+        for row in with_contract.assumed_external_call_effects
     )
 
 
@@ -173,7 +197,10 @@ def test_conventional_builtin_property_remains():
     )
 
     assert result.outcome == "MODEL_PASS"
-    assert result.assumed_external_call_effects == ()
+    assert tuple(
+        row.effect
+        for row in result.assumed_external_call_effects
+    ) == (FACTORY_EFFECT,)
 
 
 def test_field_contract_includes_result_and_lifecycle():
@@ -186,9 +213,13 @@ def test_field_contract_includes_result_and_lifecycle():
     )
 
     assert result.outcome == "MODEL_PASS"
-    assert len(result.assumed_external_call_effects) == 1
-
-    row = result.assumed_external_call_effects[0]
+    field_rows = tuple(
+        row
+        for row in result.assumed_external_call_effects
+        if row.effect == FIELD_EFFECT
+    )
+    assert len(field_rows) == 1
+    row = field_rows[0]
 
     assert row.invocation_semantics == (
         "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
@@ -220,9 +251,13 @@ def test_property_contract_includes_result_and_lifecycle():
     )
 
     assert result.outcome == "MODEL_PASS"
-    assert len(result.assumed_external_call_effects) == 1
-
-    row = result.assumed_external_call_effects[0]
+    property_rows = tuple(
+        row
+        for row in result.assumed_external_call_effects
+        if row.effect == PROPERTY_EFFECT
+    )
+    assert len(property_rows) == 1
+    row = property_rows[0]
 
     assert row.invocation_semantics == (
         "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
@@ -259,6 +294,9 @@ def test_frozen_class_decorator_outcome_is_explicit():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"): FACTORY_EFFECT,
+        },
     )
 
     assert result.outcome == "MODEL_PASS"
@@ -288,6 +326,7 @@ def test_frozen_class_decorator_outcome_is_explicit():
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
 
 
@@ -307,3 +346,114 @@ def test_rebound_class_decorator_has_no_outcome_fact():
         and event.symbol == "C"
         for event in result.events
     )
+
+
+def test_factory_name_is_not_authority():
+    source = (
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert result.assumed_external_call_effects == ()
+
+
+def test_factory_semantics_independent_of_import_name():
+    source = (
+        "from external_provider import make as decorate\n"
+        "@decorate(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("external_provider", "make"):
+                FACTORY_EFFECT,
+        },
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+    assert (
+        result.assumed_dataclass_decorations[0].decorator
+        == "external_provider.make(frozen=True)"
+    )
+    assert (
+        result.assumed_external_call_effects[0].effect
+        == FACTORY_EFFECT
+    )
+
+
+def test_factory_alias_preserves_declared_semantics():
+    source = (
+        "from external_provider import make\n"
+        "alias = make\n"
+        "@alias(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("external_provider", "make"):
+                FACTORY_EFFECT,
+        },
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert (
+        result.assumed_dataclass_decorations[0].decorator
+        == "external_provider.make(frozen=True)"
+    )
+
+
+def test_factory_rebinding_removes_declared_semantics():
+    source = (
+        "from external_provider import make\n"
+        "make = None\n"
+        "@make(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+
+    result = evaluate_package_import_order(
+        {"pkg.__init__": ast.parse(source)},
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("external_provider", "make"):
+                FACTORY_EFFECT,
+        },
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert result.assumed_external_call_effects == ()
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 90f2291..e78a5cd 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -20,6 +20,11 @@ from contextor.core.cycle_semantics.namespace_source_binding import (
 )
 
 
+FROZEN_FACTORY_EFFECT = (
+    "FROZEN_DATACLASS_DECORATOR_FACTORY"
+)
+
+
 def _snapshot(text):
     raw = text.encode("utf-8")
     return SourceSnapshot(
@@ -130,6 +135,18 @@ def _dataclass_result(
     source, *, decorate=False, external=True, child=None,
     assumed_effects=None,
 ):
+    declared_effects = (
+        {
+            ("dataclasses", "dataclass"):
+                FROZEN_FACTORY_EFFECT,
+        }
+        if decorate
+        else {}
+    )
+
+    if assumed_effects is not None:
+        declared_effects.update(assumed_effects)
+
     return evaluate_source_bound_conditional_namespace_import_order(
         *_external_case(source, child=child),
         "pkg.ns.a",
@@ -137,7 +154,7 @@ def _dataclass_result(
         target_python_version=(3, 15),
         assume_passive_external_imports=external,
         assume_frozen_dataclass_decoration=decorate,
-        assumed_external_callable_effects=assumed_effects,
+        assumed_external_callable_effects=declared_effects,
     )
 
 
@@ -165,6 +182,7 @@ def test_frozen_dataclass_t02_exact_conditional_pass():
     assert model.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     assert len(model.assumed_external_imports) == 1
     assert model.assumed_external_imports[0].target == "dataclasses"
@@ -351,12 +369,20 @@ def test_frozen_dataclass_t15_deterministic():
         target_python_version=(3, 15),
         assume_passive_external_imports=True,
         assume_frozen_dataclass_decoration=True,
+        assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                FROZEN_FACTORY_EFFECT,
+        },
     )
     second = evaluate_source_bound_conditional_namespace_import_order(
         *args, "pkg.ns.a", standard_finder_assumed=True,
         target_python_version=(3, 15),
         assume_passive_external_imports=True,
         assume_frozen_dataclass_decoration=True,
+        assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                FROZEN_FACTORY_EFFECT,
+        },
     )
     assert first == second
     assert first.conditional_assessment.model_assessment.events == (
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 4f0a9d2..2a9dcb3 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -14,6 +14,12 @@ from contextor.core.cycle_semantics.model_environment import (
 )
 
 
+FROZEN_FACTORY_EFFECTS = {
+    ("dataclasses", "dataclass"):
+        "FROZEN_DATACLASS_DECORATOR_FACTORY",
+}
+
+
 def _model(source, entry):
     return evaluate_package_import_order(
         {
@@ -74,11 +80,15 @@ def test_builtin_environment_precondition_is_metadata_not_dataclass_field():
         conditional_sources, "pkg", **options,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
     assert conditional.outcome == "MODEL_PASS"
     assert conditional.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     assert (
         conditional.builtin_environment_precondition
@@ -125,6 +135,9 @@ def test_frozen_dataclass_direct_conditional_record():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
     assert result.outcome == "MODEL_PASS"
     assert result.evidence_scope == (
@@ -147,6 +160,9 @@ def test_frozen_dataclass_rebound_name_does_not_bind_class():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
     assert result.outcome == "UNKNOWN"
     assert result.assumed_dataclass_decorations == ()
@@ -176,6 +192,9 @@ def _r8_frozen_dataclass_result(
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=assume,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
 
 
@@ -212,6 +231,7 @@ def test_r8_importref_shape_crosses_class_definition():
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
 
     assert len(result.assumed_dataclass_decorations) == 1
@@ -569,6 +589,9 @@ def _r10_qualified_ast_result(
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=assume,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
 
 
@@ -600,6 +623,7 @@ def test_r10_external_ast_attribute_has_no_authoritative_binding():
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     _r10_assert_rejected(result)
 
@@ -785,6 +809,7 @@ def _r11_module_result(
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=assume,
         _assumed_external_callable_effects={
+            **FROZEN_FACTORY_EFFECTS,
             ("dataclasses", "field"):
                 "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
         },
@@ -906,6 +931,9 @@ def test_r11_named_passive_class_annotation_not_hardcoded():
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects=(
+            FROZEN_FACTORY_EFFECTS
+        ),
     )
 
     assert result.outcome == "MODEL_PASS"
@@ -2980,6 +3008,7 @@ def _p8_field_result(class_body, *, import_line=None, prelude=""):
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
         _assumed_external_callable_effects={
+            **FROZEN_FACTORY_EFFECTS,
             ("dataclasses", "field"):
                 "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
         },
@@ -3250,6 +3279,7 @@ def test_p9_i1_known_builtin_decorator_identity(
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
         _assumed_external_callable_effects={
+            **FROZEN_FACTORY_EFFECTS,
             ("builtins", "property"): "PASSIVE_PROPERTY",
         },
     )
```

## WERDYKT

**BLOCKED** — wymagany zakres implementacji pozostawiono do przeglądu, ale test `test_frozen_dataclass_direct_conditional_record` ma niezgodną z nową deklaracją asercję `evidence_scope`. Zgodnie z instrukcją zatrzymano pracę bez jej zmiany i bez pozostałych testów.
