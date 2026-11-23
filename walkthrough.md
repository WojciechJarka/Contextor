# P10-FINAL-R3 — CONDITIONAL SEMANTIC CLOSURE

## PREFLIGHT I LIVE

- **DIRECT_EVIDENCE:** pierwsze źródło: Contextor MCP `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])`: LIVE revision **1538**, `canonical_state=fresh`, provenance `live`, `syntax_errors=0/fresh`. `cycle_semantics=stale` jest odrębną rodziną historyczną; nie stanowi wyniku aktualnego modelu.
- **DIRECT_EVIDENCE:** `get_module_context` na revision 1538: `workspace_sync=verified`, `canonical_state=fresh` dla `execution/calls.py`, `execution/definition_checks.py`, `execution/annotation_effects.py`, `execution/steps.py`, `package_model.py`, `namespace_bound_model.py`, `model_environment.py`.
- **DIRECT_EVIDENCE:** `get_symbol_lineage(mode="preview")` rozwiązał dokładne symbole `_CallableEffectFact`, `_CallOutcomeContract`, `evaluate_package_import_order` i `evaluate_conditional_namespace_import_order` na LIVE 1538. Wewnętrzne przejścia potwierdzono aktualnym źródłem. Git HEAD `607a25b476e3c665e6fa625ceff4579e94089fea`; zastane zmiany I2 w `calls.py`, `package_model.py`, `test_cycle_semantics_external_call_effects.py` oraz poprzedni `walkthrough.md`. Nie przywracano ich. GitHub nie był używany.
- **DIRECT_EVIDENCE:** interpreter lokalny `.venv/Scripts/python.exe --version` = **CPython 3.15.2**. Nie uruchamiano pytest ani FULL.

## MACIERZ POZYTYWNYCH PRZEJŚĆ AST → MODEL_PASS

| Przejście i wszystkie osiągalne dodatnie gałęzie P10 | Fakt modelu / jawne założenie | Konsument i warunek UNKNOWN | Mechanizm CPython 3.15.2 |
|---|---|---|---|
| AST klasy → dopuszczenie | `_exact_frozen_dataclass_decorator` wymaga dokładnego kształtu `@dataclass(frozen=True)`; conditional tylko `DEFERRED`, bez baz/metaclass, z ograniczonym ciałem, różnymi nazwami pól i metod. `package_model.py:283-552,885-911`; `definition_checks.py:6-59`. To dowód składni, nie identity dekoratora. | `_compile`; odrzucenie daje brak programu/UNKNOWN po osiągnięciu, `package_model.py:1917-1933`. | Wykonanie wyrażenia dekoratora, ciała klasy, `type.__new__`, potem wywołanie dekoratora. |
| Ciało klasy → kolejność kroków | `_compile` zachowuje kolejność AST: `CHECK_DATACLASS_FIELD_FACTORY` → `BIND(class_local)` dla `field(...)`, `APPLY_KNOWN_CLASS_DECORATOR` dla metody, potem `DEFINE_CONDITIONAL_FROZEN_DATACLASS`, `package_model.py:984-1111`. Literalne defaulty oraz ograniczone metody w `283-552`. | Nieobsłużone instrukcje/wyrażenia kończą UNKNOWN. `_Step` przenosi target, binding, adnotacje i definition_id, `steps.py:7-31`. | Call defaultu wykonuje się w ciele klasy; dekorator metody wywoływany jest przy definicji metody; nazwa klasy nadal nie jest związana. |
| Import zewnętrzny → wiązanie | `ASSUME_PASSIVE_EXTERNAL_SUCCESS` zapewnia warunkowe przejście importu. Przy zewnętrznym FROM deklaracja `(module,symbol) → efekt` tworzy `_CallableEffectFact`; bez niej sentinel. `package_model.py:2120-2188`. | `accept_callable_effect` wymaga faktu; sam import nie wystarcza. Import class-local nie promuje zewnętrznego callable do globalnego faktu. | `IMPORT_NAME`/`IMPORT_FROM` mogą dać dowolny obiekt z faktycznego środowiska; model nie atestuje `sys.modules` ani import hooks. |
| Builtin/alias/rebinding → callable fact | Konwencjonalny `property`: `calls.py:73-105`, `model_environment.py:3-5`, z jawnym precondition standardowych builtinów. `ALIAS` kopiuje wartość, `package_model.py:3196-3215`; nowe BIND/FROM zastępują stary fakt. | `_resolve_known_builtin_callable` najpierw sprawdza namespace; nieznany/shadowed/rebound wynik daje UNKNOWN w `APPLY...`. | Python wiąże obiekt, nie nazwę; alias zachowuje obiekt, rebinding zmienia późniejszy lookup. |
| Dwa dopuszczone Call → rezultat | `_CALL_OUTCOME_CONTRACTS`, `calls.py:17-63`: `PASSIVE_PROPERTY` i `PASSIVE_DEFAULTLESS_DATACLASS_FIELD` obejmują invocation, dokładny standardowy result i lifecycle do związania klasy. Zewnętrzny kontrakt jest założeniem caller, standardowy builtin zależy od conventional builtins. | Jedyne konsumenty `_CallableEffectFact` w ścieżce P10: `CHECK_DATACLASS_FIELD_FACTORY` i `APPLY_KNOWN_CLASS_DECORATOR`, `package_model.py:2685-2715`. `accept_callable_effect` sprawdza typ, tag, pełny obiekt kontraktu i provenance, `1532-1578`. Brak/niewłaściwy fakt → UNKNOWN przed publikacją dekoracji. | `dataclasses.field` tworzy Field; `builtins.property` tworzy descriptor. Wynik i jego `__set_name__` mają znaczenie jeszcze przed `@dataclass`. |
| Class-local rezultat → class creation | `CLASS_LOCAL_BIND` nie przechowuje samego rezultatu; nie-literalne wartości w `annotation_class_bindings` są `None`, `package_model.py:1087-1109,3184-3194,2724-2739`. Dokładne zachowanie Field/property w tym przedziale jest **założone w pełnym kontrakcie Call**, nie odtworzone przez model. | Gdy brak faktu Call, UNKNOWN wcześniej. Natomiast po przyjęciu faktu nie ma dodatkowej kontroli realnego wyniku. | CPython wstawia rzeczywisty rezultat do namespace; `type.__new__` uruchamia `__set_name__`; dokładny standardowy `Field` nie ma własnego dynamicznego haka, a builtin property ma standardową semantykę. |
| Adnotacje → ewaluacja i konsumpcja | `annotation_fields` zachowuje AST; `_eval` w `annotation_effects.py:235-416` dopuszcza: Constant, Name (class-local → module → konwencjonalny builtin), List/Tuple, atrybut indeksowanego modułu, Subscript sekwencji/standardowego GenericAlias, BitOr z udowodnionym slotem, ograniczoną arytmetykę int, UnaryOp int i IfExp z bool. `_consume` dla str/ścieżki w `446-490`. Tożsamość/symboliczne wartości z `77-232`. | Każde `None` z `_eval` lub false z `_consume` → UNKNOWN w `package_model.py:2741-2761`; ponowne `_consume` nie jest pełną symulacją retry. | CPython odracza ewaluację; `annotationlib.get_annotations(FORWARDREF)` i `call_annotate_function` mogą próbować ponownie przy Exception, `C:\\Python315\\Lib\\annotationlib.py:733-844,943-1019`. `dataclasses._process_class` odczytuje wynik w `C:\\Python315\\Lib\\dataclasses.py:1050-1083`. Znane, pasywne wyrażenia modelu nie wymagają nieudowodnionego dispatchu; inne zatrzymuje UNKNOWN. |
| Frozen dataclass → nazwa klasy | Model sprawdza sentinel `dataclass`, konsumuje adnotacje, a następnie przy założeniu `ASSUME_PASSIVE_FROZEN_DATACLASS` publikuje `ASSUMED_FROZEN_DATACLASS_DECORATION`, wiąże `\\x00PASSIVE_CLASS:` + definition_id i emituje `DEFINE_PASSIVE_CLASS`, `package_model.py:2717-2792`. | Brak sentinela, zła adnotacja albo brak definition_id → UNKNOWN. **Brak osobnej przesłanki o tożsamości i wartości zwróconej przez sam dekorator `dataclass`** przed wiązaniem jako klasy. | Standardowy `dataclasses._process_class` przetwarza realne Field, generuje metody, wywołuje `abc.update_abstractmethods` i zwraca `cls` dla `slots=False`, `C:\\Python315\\Lib\\dataclasses.py:1050-1250`. `dataclass(frozen=True)` wywołuje ten proces przez `wrap`, `1434-1462`. |
| Koniec ramek → MODEL_PASS | `package_model.py:3282-3287`; tylko brak UNKNOWN/hazard pozwala na MODEL_PASS. `assumed_external_call_effects` zapisuje pełne invocation/result/lifecycle, `1532-1619`; scope ma suffix `NOT_RUNTIME_ATTESTED` gdy fakt został użyty. | `UNMODELED_STATEMENT` i nieznany krok → UNKNOWN, `3267-3283`. | Jest to rozstrzygnięcie modelu dla dostarczonego AST, nie wykonanie analizowanego pakietu. |

### Granica publikacji ostrzeżeń

**CODE_PATH_PROVED:** `evaluate_conditional_namespace_import_order` mapuje wewnętrzny `MODEL_PASS` na `CONDITIONAL_MODEL_PASS`, `package_model.py:3777-3819`; docstring `3510-3520` wyklucza warning suppression. Source-bound wrapper zachowuje warunkowy outcome i assessment, `namespace_bound_model.py:220-247`. Zwykła ścieżka publikacyjna w `scenarios.py:329-358` wywołuje `evaluate_package_import_order` **bez** flag `_assume_passive_external_imports`, `_assume_frozen_dataclass_decoration` i `_assumed_external_callable_effects`; więc te warunkowe pozytywne ścieżki nie są źródłem `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` ani suppression.

## BRAKUJĄCA WŁASNOŚĆ I NOWA PRÓBA RÓŻNICOWA

**UNPROVEN_REACHABLE_PATH:** pełny kontrakt Call zamyka rezultat `field`/metodowego `property`, lecz nie określa rezultatu wywołania samego dekoratora klasy `dataclass(frozen=True)`. Publiczna polityka nazywa się `ASSUME_PASSIVE_FROZEN_DATACLASS`, `package_model.py:3533-3536`. Source sprawdza sentinel i zakłada pasywną dekorację, ale nie ma jawnego kontraktu „dekorator zwraca tę samą klasę” (ani równoważnego dowodu) w `package_model.py:2717-2792`. Tożsamość klasy jest użyta później przez `_value`/`_Class` i importy, `annotation_effects.py:77-115`. Założenie o pasywności działania nie jest samo dowodem wartości zwracanej.

Minimalna, odtwarzalna próba (analizowany kod przekazany modelowi wyłącznie jako AST; CPython w osobnych podprocesach 3.15.2, tymczasowy `PYTHONPATH`, bez zapisu do repo):

```python
# pkg/__init__.py
from dataclasses import dataclass
@dataclass(frozen=True)
class C:
    x: int
@dataclass(frozen=True)
class D:
    y: C | None
import pkg.child

# pkg/child.py
from pkg import D
```

Model: `evaluate_package_import_order({"pkg.__init__": ast.parse(source), "pkg.child": ast.parse(child)}, "pkg", annotation_semantics="DEFERRED", _compile_on_first_import=True, _assume_passive_external_imports=True, _assume_frozen_dataclass_decoration=True)` → **MODEL_PASS**, scope `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`; eventy `START_IMPORT → ASSUMED_EXTERNAL_IMPORT(dataclass) → ASSUMED_FROZEN_DATACLASS_DECORATION(C) → DEFINE_PASSIVE_CLASS(C) → ASSUMED_FROZEN_DATACLASS_DECORATION(D) → DEFINE_PASSIVE_CLASS(D) → START_IMPORT(child) → FROM(D) → READY(child) → BIND_CHILD(child) → IMPORT(pkg) → READY(pkg)`.

CPython kontrolny, standardowe `dataclasses.dataclass`: `RESULT <class 'pkg.C'> <class 'pkg.D'>`. CPython z uprzednio załadowanym rzeczywistym `dataclasses`, ale `sys.modules["dataclasses"]` podmienionym na `types.ModuleType` o skopiowanym słowniku i pasywnym `dataclass(*, frozen): return lambda cls: None`: `RESULT None None`. Dekorator i import nie wywołują dodatkowego kodu poza wskazanym wywołaniem, ale rezultat różni się od symbolicznej klasy modelu. W osobnym wariancie tylko pierwszy dekorator zwracał `None`, drugi był rzeczywistym standardowym dataclass: CPython zwrócił `C=None` i `D.__dataclass_fields__["y"].type = ForwardRef('C | None', ...)`, podczas gdy model zachowuje symbol klasy C. **To nie dowodzi CONFIRMED_FALSE_PASS przy silnym założeniu „dokładny standardowy dataclass”**; taki silny rezultat nie jest jednak jawnie zapisany w istniejącym kontrakcie `ASSUME_PASSIVE_FROZEN_DATACLASS`. Próba jest świadkiem luki między pasywnością a wynikiem wiązania.

## PONOWNA KLASYFIKACJA D1 / F1 / F2 / P1

| Próba z D1/D3 | Prawdziwość pełnych założeń I2 | Naruszony warunek | Ocena |
|---|---|---|---|
| D1: podmienione `field()` importuje indeksowany child przed `C` | Fałszywe | `invocation=NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS` | Bez kontraktu model UNKNOWN; z fałszywym kontraktem conditional MODEL_PASS nie jest defektem interpretera przy prawdziwym kontrakcie. |
| F1: pasywny `field(hash=False, compare=False)` zwraca Field o `hash=True, compare=True` | Fałszywe | `result=...PRESERVE_LITERAL_HASH_COMPARE` | Różnica w metodach i polach CPython wynika z fałszywego kontraktu rezultatu. |
| F2: pasywny Call zwraca subklasę Field, której `__set_name__` importuje child | Fałszywe | `result=EXACT_STDLIB_FIELD...` i `lifecycle=NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING` | ImportError CPython jest skutkiem fałszywego kontraktu, nie potwierdzonym defektem przy prawdziwym. |
| P1: pasywny zamiennik `property` zwraca int 42 | Fałszywe | `result=EXACT_BUILTINS_PROPERTY_OF_DECORATED_FUNCTION` | Zmieniony atrybut klasy nie spełnia pełnego kontraktu. |

**CONTRACT_PROVED w granicy obecnych tagów:** `calls.py:17-63` rozdziela invocation/result/lifecycle, `package_model.py:1532-1578,2167-2186,2685-2715` wymaga tego kontraktu dla obu osiągalnych konsumentów `_CallableEffectFact`; `model_environment.py:3-5` jasno oznacza standardowe builtiny jako założone, nie runtime-attested. F1/F2/P1/D1 nie są kontrprzykładami przy prawdziwym pełnym kontrakcie Call.

## KOŃCOWY WERDYKT

**UNPROVEN_REACHABLE_PATH**

Konkretne przejście: `DEFINE_CONDITIONAL_FROZEN_DATACLASS` → `namespaces[module][step.binding] = "\\x00PASSIVE_CLASS:" + definition_id`, `package_model.py:2717-2792`. Model potrzebuje własności rezultatu dekoratora klasy, której nie dowodzi z AST/importu ani nie wypowiada jawnie polityka `ASSUME_PASSIVE_FROZEN_DATACLASS`. Świadek CPython pokazuje, że sama pasywność dekoratora nie determinuje tożsamości/wartości związanej nazwy. Nie rozstrzygano tu architektury ani nie projektowano naprawy.

## FILES_CHANGED

Tylko `walkthrough.md`. Zastane zmiany source/tests z I2 pozostawiono nietknięte. Nie czytano ani nie zmieniano `issues.md`; bez pytest, FULL, restartu, staging, commit i push.

## FULL_DIFFS

`FULL_DIFFS=NONE` dla source/tests w tym zadaniu; raport nie zawiera własnego diffu.
