# P6-D05-I1 — Exact decorated default regressions

## PRECHECK

**DIRECT_EVIDENCE — przed zmianą, Contextor MCP:** LIVE revision 1468, provenance live; canonical_state=fresh; workspace_sync=unverified globalnie; syntax_errors=0 (fresh); resync_required=false; parse_stale_modules={}; cycle_semantics=stale. Per-file workspace_sync dla tests/test_cycle_semantics_default_definition_effects.py był verified przy revision 1468. Odczytany anchor końca pliku: test_p6_import_before_function_binding, linie 236–252.

**DIRECT_EVIDENCE — wcześniejsze niezależne CPython discovery P6-D05-R1:** dokładne źródła single i stacked z obecnych dwóch parametrów wykonują default g() przed zastosowaniem dekoratorów. Importy: single pkg.default, pkg.decorate; stacked pkg.default, pkg.lower, pkg.upper. Dla missing decorator CPython zgłasza NameError przed wykonaniem g/defaultu; dla deco=None default import zachodzi przed TypeError. Te obserwacje są zgodne z oczekiwanym kierunkiem przypadków w dodanym fragmencie.

## EXACT_CHANGE

Do tests/test_cycle_semantics_default_definition_effects.py dopisano na końcu pliku dokładny fragment z polecenia: 2 przypadki parametryzowane oraz 4 testy bezpośrednie. Nie zmieniono istniejącej treści, produkcji, innych testów, issues.md ani audyt.txt. issues.md odczytano bez modyfikacji; zawiera istniejące notatki o cyklach strukturalnych, TYPE_CHECKING, kompilowalności AST/CPython i wywołaniach metod. Nie ma tam wpisu dotyczącego P6-D05.

**INDEPENDENT SEMANTIC AUDIT:** dwa przypadki MODEL_PASS oczekują modelowego odtworzenia kolejności importów i restricted calls potwierdzonej w CPython. Test missing decorator przechodzi w obecnym evaluatorze, ale jego UNKNOWN/no-import może wynikać z ogólnej odmowy kompilacji dekorowanego dynamic defaultu; sam test nie dowodzi, że evaluator rozpoznał brak nazwy dekoratora. Podobnie test rebindingu asertywnie sprawdza tylko UNKNOWN i nie dowodzi obsłużenia rebindu. To ograniczenia siły tych asercji, nie zmieniono dostarczonego kodu testowego.

## TARGETED_RESULTS

Uruchomiono wyłącznie:

    .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long

Interpreter testowy: CPython 3.15.2. Wynik: 12 passed, 4 failed in 2.15s; exit code 1. Dziesięć dotychczasowych przypadków przeszło, podobnie missing-decorator i unmodeled-rebinding. Nie uruchamiano ponownie pytest ani innych testów.

## EXPECTED_FAILURES

Podane oczekiwania 12 PASS / 4 FAIL zostały spełnione:

- test_p6_decorated_default_effect_order[single-decorator-default] — FAIL w asercji linii 308: actual UNKNOWN, expected MODEL_PASS.
- test_p6_decorated_default_effect_order[stacked-decorators-default] — FAIL w tej samej asercji: actual UNKNOWN, expected MODEL_PASS.
- test_p6_noncallable_decorator_after_default — FAIL w asercji obecności START_IMPORT dla pkg.default, która zwróciła false. Wcześniejsza asercja outcome == UNKNOWN przeszła.
- test_p6_decorated_opaque_later_call_unknown — FAIL w asercji obecności DEFINE_OPAQUE_FUNCTION dla f, która zwróciła false. Wcześniejsza asercja outcome == UNKNOWN przeszła.

Dwa ostatnie wyniki są zgodne z wcześniejszym źródłowym odkryciem: evaluator zwraca UNKNOWN już podczas kompilacji dekorowanej f z default-call, zanim emituje eventy defaultu, dekoracji albo definicji funkcji. Dokładny rezultat uruchomienia zachowano w konsoli; testów ani produkcji po wyniku nie zmieniano.

## MCP_AUDIT

**DIRECT_EVIDENCE — po zmianie, Contextor MCP:**

- LIVE revision 1468, provenance live; canonical_state=fresh; global workspace_sync=unverified.
- Per-file workspace_sync dla tests/test_cycle_semantics_default_definition_effects.py: out_of_sync. get_symbol_implementation zwrócił stale_source; plik na dysku różni się od kanonicznego T0 revision 1468. Odczyt wskazał dopisany symbol test_p6_decorated_default_effect_order, zakres linii 255–331, ale implementation_is_complete=false dla niezsynchronizowanego źródła.
- syntax_errors=0 (fresh) dotyczy kanonicznego stanu revision 1468, nie potwierdza parsowania zmienionego lokalnego pliku przez MCP. Lokalne zebranie i wykonanie 16 przypadków przez pytest potwierdza, że bieżący plik jest składniowo czytelny przez CPython 3.15.2.
- resync_required=false; parse_stale_modules={}; cycle_semantics=stale.
- Nie wykonano update_file ani analizy FULL. Stan out_of_sync pozostaje nierozstrzygnięty przez MCP po zmianie.

issues.md odczytano tylko do odczytu; nie zmieniono.

## FILES_CHANGED

- tests/test_cycle_semantics_default_definition_effects.py — dopisany fragment z polecenia.
- walkthrough.md — nadpisany wymaganym raportem; jest plikiem raportowym.

## FULL_DIFFS

Pełny rzeczywisty diff zmiany testowej względem HEAD:

    diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
    index a79661a..85776b1 100644
    --- a/tests/test_cycle_semantics_default_definition_effects.py
    +++ b/tests/test_cycle_semantics_default_definition_effects.py
    @@ -250,3 +250,164 @@ def test_p6_import_before_function_binding():
             and event.symbol == "f"
             for event in result.events
         )
    +
    +
    +@pytest.mark.parametrize(
    +    "source,children,expected_imports,expected_calls",
    +    [
    +        pytest.param(
    +            (
    +                "def deco(fn):\n"
    +                "    import pkg.decorate\n"
    +                "    return fn\n"
    +                "def g():\n"
    +                "    import pkg.default\n"
    +                "@deco\n"
    +                "def f(x=g()):\n"
    +                "    pass\n"
    +            ),
    +            {"pkg.decorate": "pass", "pkg.default": "pass"},
    +            ("pkg.default", "pkg.decorate"),
    +            ("g", "deco"),
    +            id="single-decorator-default",
    +        ),
    +        pytest.param(
    +            (
    +                "def upper(fn):\n"
    +                "    import pkg.upper\n"
    +                "    return fn\n"
    +                "def lower(fn):\n"
    +                "    import pkg.lower\n"
    +                "    return fn\n"
    +                "def g():\n"
    +                "    import pkg.default\n"
    +                "@upper\n"
    +                "@lower\n"
    +                "def f(x=g()):\n"
    +                "    pass\n"
    +            ),
    +            {
    +                "pkg.upper": "pass",
    +                "pkg.lower": "pass",
    +                "pkg.default": "pass",
    +            },
    +            ("pkg.default", "pkg.lower", "pkg.upper"),
    +            ("g", "lower", "upper"),
    +            id="stacked-decorators-default",
    +        ),
    +    ],
    +)
    +def test_p6_decorated_default_effect_order(
    +    source,
    +    children,
    +    expected_imports,
    +    expected_calls,
    +):
    +    result = _p6_boundary_model(source, children)
    +
    +    assert result.outcome == "MODEL_PASS"
    +
    +    imports = tuple(
    +        event.target
    +        for event in result.events
    +        if event.operation == "START_IMPORT"
    +        and event.target in children
    +    )
    +    assert imports == expected_imports
    +
    +    calls = tuple(
    +        event.symbol
    +        for event in result.events
    +        if event.operation == "CALL_FUNCTION"
    +    )
    +    assert calls == expected_calls
    +
    +    definitions = [
    +        event
    +        for event in result.events
    +        if event.operation == "DEFINE_OPAQUE_FUNCTION"
    +        and event.symbol == "f"
    +    ]
    +    assert len(definitions) == 1
    +
    +
    +def test_p6_missing_decorator_precedes_default():
    +    result = _p6_boundary_model(
    +        "def g():\n"
    +        "    import pkg.default\n"
    +        "@missing\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.default": "pass"},
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +    assert not any(
    +        event.operation == "START_IMPORT"
    +        and event.target == "pkg.default"
    +        for event in result.events
    +    )
    +
    +
    +def test_p6_noncallable_decorator_after_default():
    +    result = _p6_boundary_model(
    +        "deco = None\n"
    +        "def g():\n"
    +        "    import pkg.default\n"
    +        "@deco\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.default": "pass"},
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +    assert any(
    +        event.operation == "START_IMPORT"
    +        and event.target == "pkg.default"
    +        for event in result.events
    +    )
    +    assert not any(
    +        event.operation == "CALL_FUNCTION"
    +        and event.symbol == "deco"
    +        for event in result.events
    +    )
    +
    +
    +def test_p6_unmodeled_decorator_rebinding_unknown():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    import pkg.original\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.child\n"
    +        "@deco\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {
    +            "pkg.child": "import pkg\npkg.deco = None\n",
    +            "pkg.original": "pass",
    +        },
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +
    +
    +def test_p6_decorated_opaque_later_call_unknown():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.default\n"
    +        "@deco\n"
    +        "def f(x=g()):\n"
    +        "    pass\n"
    +        "f()\n",
    +        {"pkg.default": "pass"},
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +    assert any(
    +        event.operation == "DEFINE_OPAQUE_FUNCTION"
    +        and event.symbol == "f"
    +        for event in result.events
    +    )

