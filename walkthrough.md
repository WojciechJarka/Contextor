# P10-FINAL-R4-D1 — CONDITIONAL CONTRACT ACCEPTANCE

## PREFLIGHT I LIVE

- DIRECT_EVIDENCE: Contextor MCP LIVE revision **1554**, `canonical_state=fresh`, syntax errors **0/fresh**. `workspace_sync=verified` na revision 1554 dla `execution/calls.py`, `execution/definition_checks.py`, `package_model.py`, `namespace_bound_model.py`, `scenarios.py`, `test_cycle_semantics_external_call_effects.py`, `test_cycle_semantics_annotation_effects_i3.py`, `test_cycle_semantics_annotation_union_i1.py`, `test_cycle_semantics_conditional_class_identity_i2.py`. Osobna rodzina `cycle_semantics=stale` nie jest wynikiem tego audytu.
- DIRECT_EVIDENCE: HEAD `03eb604a1a0cf2832d30afc1cd9518b69a65896c`, preflight `git status --short` oraz `git diff --stat` puste. Lokalny LIVE jest źródłem aktualności; Git służył weryfikacji literalnej.
- DIRECT_EVIDENCE: Contextor `get_symbol_lineage(mode=preview)` rozwiązał `evaluate_package_import_order` i `evaluate_conditional_namespace_import_order` na revision 1554; źródłowo powiązany wrapper znajduje się w `namespace_bound_model.py:52`.

## KOMPLETNA LISTA PRODUCENTÓW I KONSUMENTÓW

| Fakt/kontrakt | Producent | Konsument | Ocena |
|---|---|---|---|
| `_CallableEffectFact` builtin `property` | `execution/calls.py:112-121`; fallback tylko przy braku lokalnego wiązania `:130-145` | `package_model.py:2767-2783` | MODEL_PROVED przy założeniu konwencjonalnych builtins |
| `_CallableEffectFact` zewnętrzny | walidacja deklaracji `execution/calls.py:148-183`; modułowy FROM i zgodny wpis `package_model.py:2185-2220` | snapshot factory `:2718-2751`, field `:2753-2765`, property `:2767-2783` | EXPLICITLY_ASSUMED |
| `_CALL_OUTCOME_CONTRACTS` | `execution/calls.py:72-100` | builtin `:113-119`, `package_model.py:1561-1568,2200-2209` | exact effect + exact kontrakt sprawdzane przez `accept_callable_effect` |
| `_FROZEN_DATACLASS_DECORATOR_CONTRACT` | `execution/calls.py:36-69`; factory przypisana do słownika `:97-99` | snapshot `package_model.py:2746-2751`, application/binding `:2793-2815,2860-2908` | EXPLICITLY_ASSUMED dla importu zewnętrznego |
| `conditional_class_decorator_outcomes` | słownik `package_model.py:1921-1927`, zapis `:2746-2751` pod `definition_id` | pojedynczy `pop` `:2793-2805` | MODEL_PROVED dla kolejności modelu |
| zapis użytych deklaracji | `accept_callable_effect` `package_model.py:1584-1603` | `result` `:1620-1645`: `assumed_external_call_effects` i `evidence_scope` | EXPLICITLY_ASSUMED; brak atestacji runtime |

Literalne przeszukanie aktualnego `contextor/` nie wykazało innych konstruktorów `_CallableEffectFact`, wywołań `accept_callable_effect`, odczytów `_CALL_OUTCOME_CONTRACTS`, ani zapisów/odczytów `conditional_class_decorator_outcomes`. Nie zakładano autorstwa z nazwy importu.

## MACIERZ WARUNKÓW PRZYZNANIA PASS

Kolejność modelu: `ast.ClassDef` i restricted `@name(frozen=True)` (`package_model.py:893-919`, `execution/definition_checks.py:6-25`) → `SNAPSHOT_CONDITIONAL_CLASS_DECORATOR_FACTORY` przed krokami ciała (`package_model.py:954-963`) → zewnętrzny FROM tworzy fakt tylko przy deklaracji (`:2185-2220`) → snapshot bierze **aktualne** `namespaces[module][step.target]`, żąda efektu factory i origin (`:2718-2744`) → zapis kontraktu pod `definition_id` (`:2746-2751`) → restricted ciało klasy i adnotacje (`:1000-1109,2828-2855`) → pojedynczy `pop`, kontrola `INPUT_CLASS`, publikacja założonej dekoracji i związanie sentinela klasy (`:2785-2815,2860-2908`) → wewnętrzny `MODEL_PASS` dopiero po wyczerpaniu kroków (`:3404`).

| Sytuacja przy snapshot | Warunek i wynik | Klasyfikacja |
|---|---|---|
| Brak deklaracji | FROM wiąże sentinel; brak `_CallableEffectFact` w `:2733` → UNKNOWN | CONSERVATIVE_UNKNOWN |
| Właściwy efekt | zgodny `_CallableEffectFact`, origin i kontrakt `:2733-2738` → możliwy dalszy warunkowy MODEL_PASS | EXPLICITLY_ASSUMED |
| Niewłaściwy efekt | `accept_callable_effect` porównuje efekt i kontrakt `:1557-1568` → UNKNOWN | CONSERVATIVE_UNKNOWN |
| Alias przed snapshot | ALIAS kopiuje bieżącą wartość `:3313-3330`; fakt może przejść | MODEL_PROVED dla propagacji faktu |
| Rebinding przed snapshot | BIND nadpisuje namespace wartością `None` `:3301-3304`; snapshot → UNKNOWN | CONSERVATIVE_UNKNOWN |
| Rebinding po snapshot | snapshot przechowuje kontrakt i origin pod `definition_id`; późniejszy odczyt namespace nie występuje przy `pop` `:2793-2808`. Odpowiada wcześniejszej ewaluacji wyrażenia dekoratora w Pythonie | MODEL_PROVED dla reprezentowanej kolejności; rzeczywista tożsamość zewnętrznego callable jest EXPLICITLY_ASSUMED |

COMPILER_BOUNDARY: `_safe_passive_class_definition` (`package_model.py:291+`) ogranicza ciało; składnia nie daje sama dowodu efektu Call. Każdy dopuszczony zewnętrzny Call przechodzi przez oddzielny `accept_callable_effect`. Nie stwierdzono osiągalnego warunkowego MODEL_PASS dla zewnętrznego Call bez wymaganego jawnego kontraktu na tych trzech konsumentach.

## GRANICA SEMANTYKI RESULT/LIFECYCLE

| Rodzina | Invocation / result / lifecycle | Konsumpcja i brak faktu | Rejestracja |
|---|---|---|---|
| Fabryka frozen dataclass | `NO_UNMODELED_FACTORY_EFFECTS_OR_EXCEPTIONS` / `EXACT_STANDARD_FROZEN_DATACLASS_DECORATOR` / `NO_UNKNOWN_EFFECTS_BEFORE_APPLICATION`; aplikacja: `NO_UNMODELED_DECORATION_EFFECTS_OR_EXCEPTIONS` / `EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION` / `NO_UNKNOWN_EFFECTS_BEFORE_CLASS_BINDING`; `INPUT_CLASS` (`calls.py:43-69`) | snapshot `package_model.py:2718-2751`, później `:2785-2908`; brak faktu/kontraktu → UNKNOWN | `accept_callable_effect` przy snapshot; `AssumedFrozenDataclassDecoration` przy aplikacji |
| `field` | `NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS` / `EXACT_STDLIB_FIELD_NO_DEFAULT_OR_FACTORY_PRESERVE_LITERAL_HASH_COMPARE` / `NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING` (`calls.py:84-96`) | `CHECK_DATACLASS_FIELD_FACTORY` `package_model.py:2753-2765`; brak faktu/efektu → UNKNOWN | `accept_callable_effect` dopisuje `AssumedExternalCallEffect` dla zewnętrznego pochodzenia |
| `property` | `NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS` / `EXACT_BUILTINS_PROPERTY_OF_DECORATED_FUNCTION` / `NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING` (`calls.py:72-83`) | `APPLY_KNOWN_CLASS_DECORATOR` `package_model.py:2767-2783`; brak faktu/efektu → UNKNOWN | zewnętrzny fakt dopisany; konwencjonalny builtin nie jest zewnętrznym założeniem |

Granica wiedzy: te właściwości są deklarowanym kontraktem wejściowym dla zewnętrznego obiektu, a nie obserwacją jego runtime. Fałszywa deklaracja nie jest sama w sobie `CONFIRMED_FALSE_PASS` interpretera. Nie znaleziono w badanej ścieżce wymaganej własności rezultatu, której ani nie sprawdzono, ani nie zadeklarowano.

## GRANICA PUBLIKACJI OSTRZEŻEŃ

- `evaluate_package_import_order` przyjmuje opcje prywatne, domyślnie `False/None` (`package_model.py:1512-1524`). Jego wewnętrzne `MODEL_PASS` przy wykorzystanym efekcie ma `assumed_external_call_effects` i sufiks `EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED` (`:1620-1645`).
- Publiczny wrapper namespace przekazuje jawne opcje (`package_model.py:3894-3908`), a `MODEL_PASS` mapuje na **`CONDITIONAL_MODEL_PASS`** (`:3910-3920`); docstring `:3626-3637` wyklucza warning suppression.
- Source-bound wrapper przekazuje te same opcje (`namespace_bound_model.py:220-234`) i zachowuje wynik warunkowy bez promocji (`:236-246`).
- Produkcyjny klasyfikator SCC w `scenarios.py:330-358` wywołuje `evaluate_package_import_order(sources, entry, _session=session)` **bez** opcji zewnętrznych Call ani frozen dataclass. Klasyfikacja `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` wymaga wszystkich `MODEL_PASS`; `evidence.py:327-334` ponownie sprawdza wyniki. Warning eligibility czyta tę klasyfikację (`warning_eligibility.py:70-75`, `partial_warning_eligibility.py:89-95`). Nie ma w tym przepływie wejścia dla `assumed_external_callable_effects`.

CODE_PATH_PROVED: nie znaleziono przeniesienia wyniku zależnego od tych założeń do bezwarunkowej klasyfikacji SCC lub suppression. MCP LIVE raportuje obecnie 0 model-pass i 16 aktywnych ścieżek ostrzeżeń; to statyczny stan zainstalowanej generacji, nie dowód runtime.

## POKRYCIE I POZOSTAŁE LUKI

- DIRECT_EVIDENCE z raportów I2/R1/R2, bez ponownego uruchamiania: `package_model` 241 passed, `namespace_bound_model` 64 passed, `class decorator` 33 passed, `annotation_effects_i3` 25 passed, `annotation_union_i1` 20 passed, `conditional_class_identity_i2` 5 passed, `external_call_effects` 16 passed. Są to wyniki poprzednich przebiegów, nie wykonane w D1.
- DIRECT_EVIDENCE: obecny HEAD obejmuje poprzednie poprawki; preflight czysty i LIVE wszystkie wskazane pliki verified. Między tymi przebiegami a D1 nie stwierdzono dalszej lokalnej zmiany source/tests. `git log` pokazuje auto-commity `21b19b1`, `03eb604` po I2; porównania historycznych commitów z dokładnymi czasami testów nie wykonywano, więc twierdzenie o braku jakiejkolwiek przejściowej zmiany byłoby zbyt silne.
- Pokryte: brak kontraktu, błędny efekt, alias, rebinding, źródło importu niezależne od nazwy, factory, field, property oraz trzy starsze macierze. Nie pozostał niezweryfikowany produkcyjny konsument **nowego kontraktu** w literalnie przeszukanych ścieżkach. Testy nie stanowią pełnego dowodu semantyki dowolnego programu Python.
- UNKNOWN: rzeczywista tożsamość importowanego callable, prawdziwość deklaracji caller, niestandardowe import finders/builtins i zachowanie poza restrykcyjnym modelem nie są atestowane. To jawna granica warunkowego wyniku, nie wykazany `UNPROVEN_REACHABLE_PATH` przy prawdziwych założeniach.

## WERDYKT DOWODOWY

**EVIDENCE_COMPLETE** dla zadanego audytu przepływu autoryzacji i publikacji przy jawnych założeniach. Nie jest to FINAL PASS projektu ani certyfikat bezpieczeństwa runtime. W badanych ścieżkach nie potwierdzono `CONFIRMED_FALSE_PASS` ani konkretnego `UNPROVEN_REACHABLE_PATH`.

## FILES_CHANGED

- `walkthrough.md` — jedyny nadpisany plik.

## FULL_DIFFS

`FULL_DIFFS=NONE` dla source/tests. Nie wykonywano pytest, FULL, restartu, staging, commit ani push.
