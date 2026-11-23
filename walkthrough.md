# P10-FINAL-R3-I2-R2 — THREE LEGACY TEST HELPERS

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP LIVE revision **1551**, `canonical_state=fresh`, syntax errors **0/fresh**; `workspace_sync=verified` dla trzech wskazanych testów.
- DIRECT_EVIDENCE: lokalny HEAD `71e0d9ca2eab856585bec9b04f4ea64c4946c299`; preflight `git status --short` i `git diff --stat` puste. Zastane zmiany poprzedniego etapu są już w HEAD.
- DIRECT_EVIDENCE: dokładne anchory `_model`: `annotation_effects_i3.py:25-39`, `annotation_union_i1.py:47-65`, `conditional_class_identity_i2.py:67-81`. Każdy zawierał wskazaną opcję i wskazaną asercję.

## SIX_REPLACEMENTS

W każdym z trzech helperów `_model` wykonano dokładnie dwa zastąpienia: dodano jawny kontrakt `("dataclasses", "dataclass"): "FROZEN_DATACLASS_DECORATOR_FACTORY"` po `_assume_frozen_dataclass_decoration=True`; oczekiwanie `evidence_scope` rozszerzono wyłącznie gdy `first.assumed_external_call_effects` jest niepuste. Zachowano drugą ewaluację, kontrolę `first == second` i `ast.dump`. Pełne diffy są poniżej.

## TESTY

Wskazany interpreter `.venv/Scripts/python.exe`; grupy uruchomione kolejno:

1. `pytest -q tests/test_cycle_semantics_annotation_effects_i3.py` — **25 passed in 5.05s**.
2. `pytest -q tests/test_cycle_semantics_annotation_union_i1.py` — **20 passed in 3.83s**.
3. `pytest -q tests/test_cycle_semantics_conditional_class_identity_i2.py` — **5 passed in 1.55s**.
4. `pytest -q tests/test_cycle_semantics_external_call_effects.py` — **16 passed in 0.77s**.

## SEMANTIC_BOUNDARY

1. DIRECT_EVIDENCE: jawna deklaracja fabryki jest obecnie przekazana przez `options` wyłącznie w trzech fixture helperach; nie dopisano rozpoznawania nazw do produkcji.
2. CODE_PATH_PROVED: `execution/calls.py:153` waliduje deklaracje; `package_model.py:2190-2220` tworzy `_CallableEffectFact` dla zewnętrznego FROM tylko przy zgodnym wpisie `validated_call_effects`; inaczej tworzy sentinel importu.
3. CODE_PATH_PROVED: `package_model.py:2718-2751` snapshot odczytuje bieżące wiązanie w `namespaces[module]`, sprawdza `_CallableEffectFact`, `import_origin` i efekt `FROZEN_DATACLASS_DECORATOR_FACTORY`. Bez tego zwraca UNKNOWN.
4. CODE_PATH_PROVED: alias propaguje wartość namespace; rebinding zastępuje bieżące wiązanie. Snapshot nie używa pierwotnej nazwy jako stałego dowodu. Poprzedni focused subset import/decorator sprawdzał te granice; R2 nie zmieniał produkcji.
5. CODE_PATH_PROVED: deklaracja factory nie ingeruje w `_eval`/`_consume` adnotacji (`package_model.py:2840-2855`); nieznana operacja w adnotacji nadal prowadzi do UNKNOWN. Przejście 25 testów `annotation_effects_i3` jest wsparciem regresyjnym, a nie ogólnym dowodem.
6. CODE_PATH_PROVED: `accept_callable_effect` (`package_model.py:1557-1603`) wymaga dokładnie efektu oczekiwanego przez konkretnego konsumenta. Deklaracja factory sama nie autoryzuje innych `Call`, np. `CHECK_DATACLASS_FIELD_FACTORY` wymaga `PASSIVE_DEFAULTLESS_DATACLASS_FIELD` (`package_model.py:2753-2765`).
7. CODE_PATH_PROVED: wykorzystany zewnętrzny efekt jest zapisywany w `AssumedExternalCallEffect` i sufiksie `evidence_scope` (`package_model.py:1584-1638`). `MODEL_PASS` zależny od niego jest warunkowy i nie stanowi runtime proof.
8. CODE_PATH_PROVED: `evaluate_conditional_namespace_import_order` wyklucza MODEL_PASS warning suppression (`package_model.py:3634-3637`) i mapuje wynik na `CONDITIONAL_MODEL_PASS` (`package_model.py:3910-3918`). Nie obserwowano promocji wyniku warunkowego do bezwarunkowego.

CONTRACT_PROVED: fixture deklaruje semantykę importowanego callable jako założenie wejściowe. Testy nie atestują tożsamości rzeczywistego obiektu runtime. Zamknięty kontrakt factory jest własnością żądaną przez model, a nie wyjątkiem zależnym od Contextora.

## POST_CHANGE_MCP

- DIRECT_EVIDENCE: watcher opublikował kolejno `update_file UPDATED`: revision **1552** dla `annotation_effects_i3.py`, **1553** dla `annotation_union_i1.py`, **1554** dla `conditional_class_identity_i2.py`; od 1551 `continuity=continuous`, `resync_required=false`.
- DIRECT_EVIDENCE: LIVE revision **1554**, `canonical_state=fresh`, syntax errors **0/fresh**; wszystkie trzy pliki mają `workspace_sync=verified` na revision 1554. `cycle_semantics=stale` jest odrębną rodziną i nie ocenia tych testów.
- CODE_PATH_PROVED: producer to walidowany kontrakt z `options` oraz zewnętrzny FROM (`package_model.py:2190-2220`); consumer to snapshot (`package_model.py:2718-2751`) i `accept_callable_effect` (`package_model.py:1557-1603`). Aktualny `evidence_scope` w helperach zależy od zapisanych użytych założeń.
- DIRECT_EVIDENCE: `git diff --name-only` pokazuje tylko trzy testy; brak zmian kodu produkcyjnego. `git diff --check` bez błędów (Git zgłasza tylko informację o przyszłej konwersji LF/CRLF).

## FILES_CHANGED

- `tests/test_cycle_semantics_annotation_effects_i3.py`
- `tests/test_cycle_semantics_annotation_union_i1.py`
- `tests/test_cycle_semantics_conditional_class_identity_i2.py`
- `walkthrough.md` — raport; jego własny diff pominięty.

## FULL_DIFFS

Pełne diffy trzech testów względem HEAD `71e0d9ca2eab856585bec9b04f4ea64c4946c299`:

```diff
diff --git a/tests/test_cycle_semantics_annotation_effects_i3.py b/tests/test_cycle_semantics_annotation_effects_i3.py
index 648b5b8..4e88567 100644
--- a/tests/test_cycle_semantics_annotation_effects_i3.py
+++ b/tests/test_cycle_semantics_annotation_effects_i3.py
@@ -27,6 +27,10 @@ def _model(source, **other_sources):
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                "FROZEN_DATACLASS_DECORATOR_FACTORY",
+        },
     )
     first = evaluate_package_import_order(trees, "pkg", **options)
     second = evaluate_package_import_order(trees, "pkg", **options)
@@ -35,6 +39,11 @@ def _model(source, **other_sources):
     assert first.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        + (
+            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+            if first.assumed_external_call_effects
+            else ""
+        )
     )
     return first

diff --git a/tests/test_cycle_semantics_annotation_union_i1.py b/tests/test_cycle_semantics_annotation_union_i1.py
index c6d5a98..76277e5 100644
--- a/tests/test_cycle_semantics_annotation_union_i1.py
+++ b/tests/test_cycle_semantics_annotation_union_i1.py
@@ -49,6 +49,10 @@ def _model(source):
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                "FROZEN_DATACLASS_DECORATOR_FACTORY",
+        },
     )
     first = evaluate_package_import_order(
         {"pkg.__init__": tree}, "pkg", **options,
@@ -61,6 +65,11 @@ def _model(source):
     assert first.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        + (
+            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+            if first.assumed_external_call_effects
+            else ""
+        )
     )
     return first

diff --git a/tests/test_cycle_semantics_conditional_class_identity_i2.py b/tests/test_cycle_semantics_conditional_class_identity_i2.py
index 54ab964..1916625 100644
--- a/tests/test_cycle_semantics_conditional_class_identity_i2.py
+++ b/tests/test_cycle_semantics_conditional_class_identity_i2.py
@@ -69,6 +69,10 @@ def _model(sources):
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "dataclass"):
+                "FROZEN_DATACLASS_DECORATOR_FACTORY",
+        },
     )
     first = evaluate_package_import_order(trees, "pkg", **options)
     second = evaluate_package_import_order(trees, "pkg", **options)
@@ -77,6 +81,11 @@ def _model(sources):
     assert first.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        + (
+            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+            if first.assumed_external_call_effects
+            else ""
+        )
     )
     return first
```

## WERDYKT

**PASS** w literalnym zakresie R2: sześć zastąpień w trzech helperach, cztery wymagane grupy testów przechodzą, LIVE jest świeży i zsynchronizowany. PASS nie stanowi atestacji środowiska uruchomieniowego analizowanego pakietu.
