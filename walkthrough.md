# F2-I1 — aktualizacja kontraktu testowego

## PREFLIGHT

### DIRECT_EVIDENCE

- Contextor MCP sprawdził test oraz helper referencyjny przed edycją.
- Test: tests/test_cycle_semantics_external_import_authority.py (module 628/1), canonical_state=fresh, workspace_sync=verified, canonical_revision=1576, provenance=live, syntax diagnostics checked_and_none (0 błędów).
- Helper: tests/test_cycle_semantics_external_call_effects.py (module 677/1), canonical_state=fresh, workspace_sync=verified, canonical_revision=1576, syntax diagnostics checked_and_none (0 błędów).
- Dokładne ciała testu i helpera zostały odczytane przez Contextor. Helper _run (test_cycle_semantics_external_call_effects.py:15-38) podaje mapę {("dataclasses", "dataclass"): FACTORY_EFFECT}, gdzie FACTORY_EFFECT ma wartość "FROZEN_DATACLASS_DECORATOR_FACTORY".
- HEAD: 97768850d0b91b35affd84d5675a9368146d48ea, branch main, origin/main. Przed zmianą testu jedynym istniejącym lokalnym diffem był raport walkthrough.md z F2-D1.
- CPython: 3.15.2, cpython, AMD64, 64bit.
- Contextor oznacza family cycle_semantics jako stale. Nie używam tego artefaktu do wnioskowania o wyniku testu; źródło pliku jest zweryfikowane, a wynik pochodzi z lokalnego wykonania.

### INFERENCE

- Jawny efekt w helperze referencyjnym jest tym samym kontraktem, którego brak powodował UNKNOWN w F2-D1.

### UNKNOWN

- Nie odczytywano issues.md. Zgodnie z późniejszą instrukcją użytkownika „olej issues”, kontrola tego pliku została pominięta.

## IMPLEMENTATION

### DIRECT_EVIDENCE

- Zmieniono wyłącznie wywołanie evaluate_conditional_namespace_import_order w funkcji test_conditional_external_side_effect_is_not_runtime_authority.
- Dodano assumed_external_callable_effects z kluczem tuple ("dataclasses", "dataclass") i wartością "FROZEN_DATACLASS_DECORATOR_FACTORY", zgodnie z reprezentacją helpera _run.
- Nie był potrzebny import: wartość jest stringowym kontraktem, tak samo jak FACTORY_EFFECT w helperze.
- Zachowano obie flagi założeń, oczekiwanie CONDITIONAL_MODEL_PASS, wszystkie dotychczasowe asercje, AST programu, mutator builtins.property, kontrolny wariant runtime i dotychczasowe granice autorytetu.
- Nie zmieniono produkcji, helperów ani innych testów.

### INFERENCE

- Deklaracja pozwala evaluatorowi utworzyć jawny external callable fact dla dataclasses.dataclass. Nie usuwa to warunkowego evidence scope ani jego ograniczenia względem runtime.

### UNKNOWN

- Po teście nie zmieniano istniejących asercji; błąd wykryty w TARGETED_TESTS pozostaje nierozwiązany zgodnie z poleceniem stop.

## TARGETED_TESTS

### DIRECT_EVIDENCE

Interpreter zweryfikowany jako CPython 3.15.2 AMD64, 64bit.

Uruchomiono wskazany test:

.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_import_authority.py::test_conditional_external_side_effect_is_not_runtime_authority -vv

Wynik: FAILED, exit code 1. Test przeszedł asercje outcome, reason, authority i model.outcome, po czym zawiódł na istniejącej asercji evidence_scope w tests/test_cycle_semantics_external_import_authority.py:219.

- Oczekiwano: CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF
- Otrzymano: CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED

Produkcja dopisuje suffix, gdy zaakceptowano zewnętrzny callable effect (contextor/core/cycle_semantics/package_model.py:1630-1647). Ten sam suffix jest jawnie wymagany przez pozytywny test referencyjny (tests/test_cycle_semantics_external_call_effects.py:273-331).

Ponieważ wskazany test nie przeszedł, oba pliki z pełnym testami nie zostały uruchomione.

### INFERENCE

- Niepowodzenie jest skutkiem zachowania istniejącej asercji evidence_scope przy dodaniu jawnego efektu. Nowy wynik dokładnie odzwierciedla dodatkowe założenie callable-effect i odpowiada kontraktowi referencyjnemu.
- Dalsza zmiana asercji byłaby kolejną poprawką; nie została wykonana, zgodnie z instrukcją zatrzymania przy błędzie.

### UNKNOWN

- Asercje po linii 219, w tym runtime subprocess z mutatorem i wariant kontrolny, nie zostały wykonane w tym pytest.
- Nie ustalano wyniku całego pliku ani pliku external_call_effects, ponieważ po failu obowiązuje instrukcja stop.

## POST_CHANGE_MCP_AUDIT

### DIRECT_EVIDENCE

- Desktop watcher opublikował event revision 1577: operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=tests/test_cycle_semantics_external_import_authority.py.
- Continuity: continuous; resync_required=false.
- Contextor po zmianie: canonical_state=fresh, workspace_sync=verified, canonical_revision=1577, provenance=live.
- Syntax diagnostics: checked_and_none, 0 błędów. Brak ostrzeżeń Contextor dla pliku.
- cycle_semantics family nadal stale; cycle warning view jest oznaczony fresh dla revision 1577. To nie jest runtime safety evidence.
- Nie wykonano restartu ani operacji modyfikujących Git.

### INFERENCE

- Zmiana testu została zaobserwowana i zsynchronizowana przez desktop watcher. Nie używano update_file.

### UNKNOWN

- Blast radius dla zmiany jest deferred; nie interpretowano go jako pełnej analizy wpływu.

## ISSUES_CHECK

### DIRECT_EVIDENCE

- issues.md nie został odczytany.

### INFERENCE

- Kontrolę pominięto na polecenie użytkownika „olej issues”.

### UNKNOWN

- Zawartość issues.md pozostaje nieznana.

## FILES_CHANGED

- tests/test_cycle_semantics_external_import_authority.py — jedyna zmiana w kodzie/testach.
- walkthrough.md — raport F2-I1.
- Bez zmian w produkcji, helperach, innych testach lub pozostałych plikach.

## FULL_DIFFS

Pełny diff testu:

    diff --git a/tests/test_cycle_semantics_external_import_authority.py b/tests/test_cycle_semantics_external_import_authority.py
    index 90723e3..b699c64 100644
    --- a/tests/test_cycle_semantics_external_import_authority.py
    +++ b/tests/test_cycle_semantics_external_import_authority.py
    @@ -202,6 +202,10 @@ def test_conditional_external_side_effect_is_not_runtime_authority(tmp_path):
             target_python_version=sys.version_info[:2],
             assume_passive_external_imports=True,
             assume_frozen_dataclass_decoration=True,
    +        assumed_external_callable_effects={
    +            ("dataclasses", "dataclass"):
    +                "FROZEN_DATACLASS_DECORATOR_FACTORY",
    +        },
         )
 
         assert conditional.outcome == "CONDITIONAL_MODEL_PASS"

## REMAINING_UNKNOWNS

### DIRECT_EVIDENCE

- Test zatrzymał się na asercji evidence_scope; żaden kolejny test poza zakresem nie został uruchomiony.
- MCP zgłasza stale dla family cycle_semantics, mimo że stan pliku i syntax diagnostics są świeże.

### UNKNOWN

- Nieznany jest wynik obu pełnych plików testowych, bo wskazany test nie przeszedł, a użytkownik nakazał w tej sytuacji przerwać.
- Nieznane są wyniki runtime assertions z końca wskazanej funkcji w tym przebiegu pytest.
- Nie proponowano ani nie wykonywano kolejnej poprawki.

