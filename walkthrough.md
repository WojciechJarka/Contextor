# P9-I1 — zatrzymane po błędzie edycji

## PREFLIGHT

- DIRECT_EVIDENCE: pierwszym źródłem był Contextor MCP `get_project_architecture(fields=[])`: LIVE revision 1488, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `resync_required=false`, `syntax_errors=0` (fresh).
- DIRECT_EVIDENCE: per-file MCP `workspace_sync=verified` dla `execution/calls.py`, `package_model.py` i obu wskazanych plików testowych. HEAD `53993b328f13e44d922a4428fef5c276db449e22`. Zastane zmiany: `M audyt.txt`, `M walkthrough.md`.
- CODE_PATH_PROVED: aktualne kotwice P9-R2 były obecne: `_RestrictedFunction` w `execution/calls.py:8–12`, `allow_builtin_property`, `uses_property`, `CHECK_BUILTIN_PROPERTY`, handler `ALIAS` i gałąź `external_decision == 'ASSUME'` w `package_model.py`. Nie było SOURCE_DRIFT.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: rozpoczęto zmianę w `execution/calls.py` i `package_model.py`. Patch dla `_compile` użył zbyt ogólnego kontekstu i wstawił duży fragment w miejsce początku obsługi `ast.AnnAssign`, pozostawiając niepoprawną strukturę `elif isinstance(stmt, ast.FunctionDef)`.
- Zgodnie z warunkiem zadania „przy błędzie zatrzymaj się” przerwano implementację przed edycją testów i przed pytest. Oba pliki produkcyjne były czyste w preflight; przywrócono je do HEAD poleceniem `git restore --` wyłącznie dla tych dwóch ścieżek. Końcowy `git diff --` obu plików jest pusty. Nie pozostawiono częściowej implementacji.

## BINDING_IDENTITY

- CODE_PATH_PROVED z preflight: istniejące `FROM` może tworzyć znacznik zewnętrznego importu; `ALIAS` kopiuje wartość z module namespace, lecz nie ma builtin fallback. `CHECK_BUILTIN_PROPERTY` sprawdza brak nazwy `property` w module namespace, a nie tożsamość aliasu. W tym zadaniu nie zmieniono tych mechanizmów.

## CLASS_DECORATOR_ADMISSION

- NOT_PROVED po zmianie: brak wdrożonej zmiany, brak nowych kontraktów i brak oceny modelu po implementacji. Obowiązuje stan sprzed P9-I1.

## CPYTHON_315_PARITY

DIRECT_EVIDENCE: przed edycją każdy A–M wykonano w osobnym podprocesie CPython 3.15.2 i osobnym pakiecie tymczasowym; `pkg.child` zawierał `pass`. Klasa miała dwa wymagane pola oraz dekorowaną metodę `value` zwracającą 1.

| Przypadek | Wynik | C związana | child | Typ `C.value` |
|---|---|---|---|---|
| A `@property` | OK | tak | tak | property |
| B `from builtins import property as prop; @prop` | OK | tak | tak | property |
| C `alias=prop; @alias` | OK | tak | tak | property |
| D `alias=property; @alias` | OK | tak | tak | property |
| E `alias=property; property=None; @alias` | OK | tak | tak | property |
| F `@property; property=None` później | OK | tak | tak | property |
| G `property=None; @property` | `TypeError: 'NoneType' object is not callable` | nie | nie | — |
| H `prop=None; @prop` | ten sam `TypeError` | nie | nie | — |
| I obca funkcja `property` | OK | tak | tak | function |
| J obca funkcja `ta_nazwa` | OK | tak | tak | function |
| K class-local `property: object=None` | ten sam `TypeError` | nie | nie | — |
| L class-local `def property(fn)` | OK | tak | tak | function |
| M class-local `from builtins import property as property` | OK | tak | tak | property |

## TARGETED_RESULTS

- NOT_PROVED: nie uruchomiono pytest ani ewaluacji po zmianie, ponieważ literalna edycja była błędna i została wycofana. Brak traceback pytest; błąd wykryto przez `git diff` przed wykonaniem testów.

## PRODUCTION_AUTHORITY

- CODE_PATH_PROVED z bieżącego kodu sprzed edycji: warunkowy `MODEL_PASS` pozostaje wewnętrzny; publiczna ścieżka mapuje go na `CONDITIONAL_MODEL_PASS`; zwykła ścieżka produkcyjna nie używa flag założeń. P9-I1 nie zmienił tej granicy.

## MCP_POST_AUDIT

- NOT_PROVED: nie było post-change audytu nowej implementacji, gdyż została wycofana przed testami. Preflight LIVE rev 1488 i per-file verified pozostaje jedynym odczytem MCP dla kodu; końcowy lokalny `git diff` produkcji jest pusty. Nie deklaruję FINAL PASS.

## FILES_CHANGED

- Source/tests: brak końcowych zmian. `execution/calls.py` i `package_model.py` przywrócono do HEAD po błędzie edycji. Zastany `audyt.txt` zachowano. Nadpisano tylko `walkthrough.md` jako raport.

## FULL_DIFFS=NONE

ACTUAL_DIFF=DIFFS=NONE dla końcowego stanu source/tests; `walkthrough.md` jest raportem.
