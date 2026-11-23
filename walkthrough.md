# P10-FINAL-R3-I2-R1 — TEST CONTRACT CORRECTION

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP LIVE revision 1550, `canonical_state=fresh`, syntax errors 0/fresh. Wszystkie osiem plików I2 miało `workspace_sync=verified`: `execution/calls.py`, `execution/definition_checks.py`, `package_model.py`, `test_cycle_semantics_package_model.py`, `test_cycle_semantics_namespace_bound_model.py`, `test_cycle_semantics_class_decorator_staging.py`, `test_cycle_semantics_class_decorator_import_admission.py`, `test_cycle_semantics_external_call_effects.py`.
- DIRECT_EVIDENCE: lokalny HEAD `21b19b1e5de1ee741e09a89b5331731bd1c5428d` (`Auto-commit: Cleanup and update`), preflight `git status --short` pusty. I2 znajduje się już w HEAD. Anchor asercji w `tests/test_cycle_semantics_package_model.py:143-146` dokładnie pasował. Zachowano zmiany I2.

## KOREKTA R1

W `test_frozen_dataclass_direct_conditional_record` dodano do oczekiwanego `evidence_scope` literalny człon `|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED`. Nie zmieniono innej asercji ani żadnego innego source/test.

## TESTY

CPython z `.venv/Scripts/python.exe`, grupy uruchomione kolejno:

1. `pytest -q tests/test_cycle_semantics_package_model.py -k "test_frozen_dataclass_direct_conditional_record"` — **1 passed, 240 deselected**.
2. `pytest -q tests/test_cycle_semantics_external_call_effects.py` — **16 passed**.
3. `pytest -q tests/test_cycle_semantics_package_model.py` — **241 passed**.
4. `pytest -q tests/test_cycle_semantics_namespace_bound_model.py` — **64 passed**.
5. `pytest -q tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_class_decorator_import_admission.py` — **33 passed**.
6. `pytest -q tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_annotation_union_i1.py tests/test_cycle_semantics_conditional_class_identity_i2.py` — **30 failed, 20 passed**. Zatrzymano dalsze testy i edycje.

Pierwszy traceback grupy 6 z wyjścia pytest:

```text
_________ test_passive_annotations_remain_conditional_pass[list[int]] _________
tests/test_cycle_semantics_annotation_effects_i3.py:97: AssertionError
>       assert result.outcome == "MODEL_PASS", annotation
E       AssertionError: list[int]
E       assert 'UNKNOWN' == 'MODEL_PASS'
E         - MODEL_PASS
E         + UNKNOWN
```

DIRECT_EVIDENCE: pełny stdout grupy 6 został obcięty przy transmisji (947 linii, 13677 tokenów), dlatego nie zachowano wszystkich 30 tracebacków. Nie uruchamiano testu ponownie po porażce. CODE_PATH_PROVED: helpery `_model` w trzech starszych plikach (`annotation_effects_i3.py:21-39`, `annotation_union_i1.py:44-65`, `conditional_class_identity_i2.py:64-81`) ustawiają `_assume_frozen_dataclass_decoration=True` oraz `_assume_passive_external_imports=True`, lecz nie przekazują `_assumed_external_callable_effects`. Aktualny `package_model.py:2727-2744` wymaga `_CallableEffectFact` o efekcie `FROZEN_DATACLASS_DECORATOR_FACTORY`; bez deklaracji snapshot zwraca UNKNOWN. To wyjaśnia pierwszą porażkę; nie ustalono osobno przyczyny każdego z 30 przypadków.

## SEMANTIC_BOUNDARY

1. CODE_PATH_PROVED: `_restricted_frozen_class_factory_call` (`execution/definition_checks.py:6-25`) sprawdza kształt `ast.Call`, identyfikator, brak argumentów pozycyjnych i literalne `frozen=True`, nie nazwę importu.
2. CODE_PATH_PROVED: zewnętrzny FROM (`package_model.py:2166-2220`) pobiera zadeklarowany efekt z `validated_call_effects[(target, step.symbol)]`. `_CallableEffectFact` powstaje tylko przy deklaracji, inaczej sentinel importu.
3. CODE_PATH_PROVED: snapshot (`package_model.py:2718-2751`) odczytuje aktualne `namespaces[module][step.target]`, wymaga `_CallableEffectFact`, origin i efektu przez `accept_callable_effect`; inaczej UNKNOWN.
4. CODE_PATH_PROVED: alias zachowuje fakt przez wiązanie wartości; rebinding zastępuje bieżącą wartość namespace. Snapshot nie korzysta z historycznej nazwy importu. W R1 nie uruchamiano nowej próby alias/rebind.
5. CODE_PATH_PROVED: brak kontraktu factory pozostawia zewnętrzny sentinel, który nie spełnia warunku snapshot (`package_model.py:2733-2744`).
6. CODE_PATH_PROVED: snapshot zapisuje kontrakt i `import_origin` pod `definition_id` (`package_model.py:2746-2751`); `DEFINE_CONDITIONAL_FROZEN_DATACLASS` konsumuje go przez `pop` (`package_model.py:2785-2805`).
7. CODE_PATH_PROVED: przyjęty efekt zostaje zapisany do `AssumedExternalCallEffect` (`package_model.py:1584-1603`) i sufiksu `evidence_scope` (`package_model.py:1620-1638`). Jest to jawne założenie, nie atestacja runtime.
8. CODE_PATH_PROVED: ścieżka namespace mapuje wynik na `CONDITIONAL_MODEL_PASS` (`package_model.py:3910-3918`); docstring (`package_model.py:3634-3637`) wyklucza warning suppression. MCP pokazuje 0 model-pass i 16 aktywnych ostrzeżeń, ale nie dowodzi to wykonania programu.

CONTRACT_PROVED: korekta R1 sprawdza raportowany zakres wykorzystanej deklaracji. Nie poświadcza realnej tożsamości importowanego obiektu ani runtime przy fałszywej deklaracji.

## POST_CHANGE_MCP

- DIRECT_EVIDENCE: `desktop_watcher` opublikował `update_file UPDATED` dla `tests/test_cycle_semantics_package_model.py`, revision **1551**; ciągłość od 1550 `continuous`, `resync_required=false`.
- DIRECT_EVIDENCE: końcowy LIVE revision **1551**, `canonical_state=fresh`, syntax errors **0/fresh**. Wszystkie osiem plików I2 `workspace_sync=verified` na revision 1551; źródło korekty jest zgodne z LIVE.
- `cycle_semantics=stale` jest odrębną rodziną LIVE i nie jest interpretowane jako wynik bieżących testów.

## FILES_CHANGED

- `tests/test_cycle_semantics_package_model.py` — jedna linia.
- `walkthrough.md` — raport, wyłączony z diffów source/tests.

## FULL_DIFFS

Względem **bieżącego HEAD** I2 nie ma diffów: HEAD zmienił się od poprzedniego etapu i zawiera już I2. Pełny diff source/tests względem HEAD:

```diff
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 2a9dcb3..8089fb9 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -143,6 +143,7 @@ def test_frozen_dataclass_direct_conditional_record():
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
     )
     assert len(result.assumed_dataclass_decorations) == 1
     assert result.assumed_dataclass_decorations[0].class_name == "Graph"
```

`git diff --check` — bez błędów.

## WERDYKT

**BLOCKED** — korekta R1 i pierwszych pięć grup przeszły, szósty wymagany subset zakończył się 30 porażkami. Starsze helpery nie deklarują wymaganej teraz semantyki fabryki; zgodnie z zakresem zadania nie zmieniano ich ani produkcji. Nie zgłoszono PASS.
