# P6-D04-I1-R1 — EXACT REGRESSION TEST IMPLEMENTATION

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP przed zmianą:** LIVE revision `1463`, `provenance=live`, `canonical_state=fresh`, `resync_required=false`, `parse_stale_modules={}`; globalne `syntax_errors=0` (`fresh`). Agregat `workspace_sync=unverified` nie potwierdza synchronizacji wszystkich plików.
- **DIRECT_EVIDENCE — repozytorium przed zmianą:** HEAD `8bb5d7f60ced527d99e6531702573b0f32039234`; docelowy test nie istniał. `git status --short` pokazywał już `M audyt.txt` i `M walkthrough.md`; `audyt.txt` jest zmianą zastaną, poza zakresem tego zadania.
- **CODE_PATH_PROVED — niezależny kontrakt semantyczny:** w odczytanym przy rev `1463` symbolu `contextor/core/cycle_semantics/package_model.py::_safe_passive_function_definition` (zakres linii 145–242, plik `workspace_sync=verified`) dozwolone są literalne defaulty; wywołanie w wyrażeniu defaultu nie przechodzi `safe_default`, więc kompilacja zachowuje się konserwatywnie i wynik modelu to `UNKNOWN`. CPython wykonuje wyrażenia defaultów podczas wykonywania instrukcji `def`, przed związaniem nazwy funkcji; wywołanie `g()` może więc w tej chwili wykonać importy z ciała `g`. Oczekiwanie `MODEL_PASS` w pierwszych trzech parametrach opisuje zamierzoną obsługę efektu, której obecna ścieżka modelu nie dopuszcza. Nie zmieniono produkcyjnego zachowania.
- **INFERENCE:** trzy oczekiwane FAIL są regresyjnym zapisem brakującej obsługi efektu definicji. Dwa oczekiwane PASS utrzymują oczekiwany `UNKNOWN` dla fixture z rebindingiem przed definicją i fixture z jawnym `return`; ponieważ evaluator odrzuca dynamiczne wyrażenie defaultu wcześniej, sam PASS nie dowodzi, że rozróżnił te dwie przyczyny.

## EXACT_CHANGE

- Dodano dokładnie jeden plik testowy: `tests/test_cycle_semantics_default_definition_effects.py`.
- Treść przypadków, parametrów i asercji jest zgodna z treścią dostarczoną w zadaniu. Nie zmieniono kodu produkcyjnego, innych testów, `issues.md` ani `audyt.txt`.
- Nadpisano `walkthrough.md` zgodnie z poleceniem raportowym.

## TARGETED_RESULTS

Uruchomiono wyłącznie wymagane polecenie:

```text
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long
```

Wynik: `FFF.. [100%]`; `3 failed, 2 passed in 2.05s` (exit code `1`). Nie uruchomiono innych testów.

## EXPECTED_FAILURES

- **DIRECT_EVIDENCE — oczekiwane FAIL:**
  - `test_default_definition_effects[single-default-import]`
  - `test_default_definition_effects[sequential-default-imports]`
  - `test_default_definition_effects[rebind-after-default]`
- Każdy zatrzymał się na `tests/test_cycle_semantics_default_definition_effects.py:102`, przy `assert result.outcome == expected_outcome`: wynik evaluatora to `UNKNOWN`, a oczekiwany wynik parametru to `MODEL_PASS`. W tych trzech przypadkach asercje kolejności eventów nie zostały osiągnięte, bo wcześniej nie powstał wynik `MODEL_PASS`.
- **DIRECT_EVIDENCE — oczekiwane PASS:** `test_default_definition_effects[rebind-before-default]` i `test_default_definition_effects[unsupported-return]`; oba oczekują `UNKNOWN` i kończą się przed asercjami eventów. **CODE_PATH_PROVED:** wynik wynika z odmowy obsługi call expression jako defaultu; test nie dowodzi osobnej klasyfikacji późniejszego rebindingu ani wartości zwracanej.
- **Werdykt względem kontraktu uruchomienia:** zaobserwowano dokładnie podział FAIL/PASS wskazany w promptcie. Nie poprawiano testu ani tracebacków.

## MCP_AUDIT

- **DIRECT_EVIDENCE — stan po zmianie:** Contextor LIVE revision `1464`, `provenance=live`, `canonical_state=fresh`; `resync_required=false`; `parse_stale_modules={}`.
- **DIRECT_EVIDENCE — synchronizacja badanego pliku:** `get_symbol_implementation` rozpoznał `test_default_definition_effects` w `tests/test_cycle_semantics_default_definition_effects.py` (linie 79–140), `workspace_sync=verified`, `canonical_revision=1464`. Per-file sync oznacza zgodność fingerprintu pliku na dysku z canonical T0. Agregat projektowy nadal ma `workspace_sync=unverified`.
- **DIRECT_EVIDENCE — składnia:** dla badanego pliku `syntax_diagnostics.status=checked_and_none`, `availability=fresh`, `errors=[]`; globalne `syntax_errors.count=0`, `availability=fresh`.
- **DIRECT_EVIDENCE — resync/event stream:** `get_live_events(after_revision=1464, limit=1)` zwrócił `events=[]`, `continuity=continuous`, `resync_required=false`. Odczyt od rev `1463` zwrócił `confirmation_required` z powodu projekcji o szacowanym rozmiarze `19.23 KiB`; nie uzyskano w ten sposób bezpośredniego payloadu eventu przejścia `1463→1464`. Rewizja `1464` i zweryfikowany per-file sync potwierdzają jednak, że nowy plik znajduje się w aktualnym canonical state.
- **DIRECT_EVIDENCE — pozostałe freshness:** rodzina `cycle_semantics` była oznaczona jako `stale`; pozostałe wymienione rodziny (`module`, `graph`, `topology`, `artifact_consumption`, `cycles`, `collisions`, `lineage`) były `fresh`. To metadane stanu LIVE, nie wynik testu.
- **UNKNOWN:** nie ustalano, czy agregat `workspace_sync=unverified` wynika z dowolnego konkretnego pliku; audyt potwierdza wyłącznie wymagany per-file stan dla nowego testu.

## FILES_CHANGED

- `tests/test_cycle_semantics_default_definition_effects.py` — nowy plik, cała treść pokazana w `FULL_DIFFS`.
- `walkthrough.md` — nadpisany raport wymagany zadaniem; jako sam raport nie jest liczony jako zmieniony plik source/test.
- `audyt.txt` — zmiana była obecna już przed zadaniem i nie została przez to zadanie zmodyfikowana.
- Nie zmieniono żadnego pliku produkcyjnego, innego testu ani `issues.md`.

## FULL_DIFFS

### `tests/test_cycle_semantics_default_definition_effects.py` — pełna dodana treść

```python
import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


CASES = [
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "MODEL_PASS",
        ("pkg.child",),
        id="single-default-import",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.a\n"
            "def h():\n"
            "    import pkg.b\n"
            "def f(x=g(), y=h()):\n"
            "    pass\n"
        ),
        {"pkg.a": "pass", "pkg.b": "pass"},
        "MODEL_PASS",
        ("pkg.a", "pkg.b"),
        id="sequential-default-imports",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "def f(x=g()):\n"
            "    pass\n"
            "g = None\n"
        ),
        {"pkg.child": "pass"},
        "MODEL_PASS",
        ("pkg.child",),
        id="rebind-after-default",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "g = None\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "UNKNOWN",
        (),
        id="rebind-before-default",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "    return 10\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "UNKNOWN",
        (),
        id="unsupported-return",
    ),
]


@pytest.mark.parametrize(
    "source,children,expected_outcome,expected_imports",
    CASES,
)
def test_default_definition_effects(
    source,
    children,
    expected_outcome,
    expected_imports,
):
    sources = {
        "pkg": ast.parse(source),
        **{
            name: ast.parse(child_source)
            for name, child_source in children.items()
        },
    }

    result = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert result.outcome == expected_outcome

    if expected_outcome == "UNKNOWN":
        return

    events = list(result.events)

    definition_positions = [
        index
        for index, event in enumerate(events)
        if (
            event.operation == "DEFINE_OPAQUE_FUNCTION"
            and event.symbol == "f"
        )
    ]

    assert len(definition_positions) == 1
    definition_position = definition_positions[0]

    observed_positions = []

    for target in expected_imports:
        positions = [
            index
            for index, event in enumerate(events)
            if (
                event.operation == "START_IMPORT"
                and event.target == target
            )
        ]

        assert len(positions) == 1
        observed_positions.append(positions[0])

    assert observed_positions == sorted(observed_positions)
    assert all(
        position < definition_position
        for position in observed_positions
    )
```
