# P6-D05-I2-R2 — Final semantic boundaries

## PRECHECK

**DIRECT_EVIDENCE — Contextor MCP:** przed zmianą LIVE revision 1475, provenance=live, canonical_state=fresh, global workspace_sync=unverified, syntax_errors=0 (fresh), resync_required=false, parse_stale_modules={}; cycle_semantics=stale. Per-file workspace_sync dla tests/test_cycle_semantics_default_definition_effects.py wynosił verified przy revision 1475.

**DIRECT_EVIDENCE — kotwica i repozytorium:** Contextor odczytał test_p6_stacked_decorator_child_name_collision_unknown (linie 448–472), stanowiący dokładną kotwicę EOF. HEAD: 5f2f4375912a4921ee5df9265d8b19b47ef15498. Przed zmianą status zawierał już modyfikacje pliku testowego i walkthrough.md z poprzedniego zadania. issues.md odczytano zgodnie z poleceniem i pozostawiono bez zmian.

## EXACT_CHANGE

Do końca tests/test_cycle_semantics_default_definition_effects.py dopisano dokładnie cztery testy podane w zleceniu:

- test_p6_decorator_import_before_final_binding
- test_p6_decorator_same_name_as_defined_function
- test_p6_keyword_only_defaults_before_decorator
- test_p6_cross_module_decorator_with_default

Nie zmieniono istniejącego kodu testowego ani żadnego pliku produkcyjnego. Nie zmieniono oczekiwań.

## TARGETED_RESULTS

Interpreter: CPython 3.15.2. Uruchomiono wyłącznie:

    .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py --tb=long

Wynik rzeczywisty: **23 passed in 1.02s**, exit code 0. Prompt przewidywał 22 PASS; liczba rzeczywistych zaliczeń różni się o jeden. Nie wystąpił FAIL, więc nie ma tracebacku FAIL. Nie uruchamiano dodatkowego pytest.

## SEMANTIC_BOUNDARIES

**DIRECT_EVIDENCE z target run:** wszystkie cztery dopisane przypadki przeszły wraz z asercjami:

- import z dekoratora przed końcowym związaniem f daje EARLY_BINDING_HAZARD, target pkg, symbol f; zdarzenia CALL_FUNCTION to g, deco;
- dekorator nazwany tak samo jak wiązana funkcja f daje MODEL_PASS, wywołania g, f i dokładnie jedno DEFINE_OPAQUE_FUNCTION dla f;
- kw-only defaults wykonują importy pkg.a, pkg.b przed importem pkg.decorate, z wywołaniami g, h, deco;
- dekorator z pkg.decorators zastosowany do f w pkg.app daje MODEL_PASS; importy pkg.default, pkg.decorate; wywołania g, deco; f jest wiązane w pkg.app.

**INFERENCE:** target run potwierdza evaluatorowe asercje dla tych czterech źródeł. Nie wykonano osobnych runtime probes CPythona dla tych czterech fixture’ów.

## MCP_AUDIT

Po zmianie LIVE revision 1476, provenance=live, canonical_state=fresh. Per-file workspace_sync dla tests/test_cycle_semantics_default_definition_effects.py wynosi verified przy revision 1476. Odpowiedź symbolu test_p6_cross_module_decorator_with_default wykazała syntax_errors=0 (fresh); resync_required=false, parse_stale_modules={}. Global workspace_sync pozostaje unverified; cycle_semantics=stale.

get_live_events po revision 1475 potwierdził ciągłość i zdarzenie revision 1476: update_file, origin=desktop_watcher, status=UPDATED, ścieżka wskazuje zmieniony plik testowy. resync_required=false.

issues.md nie został zmieniony. Nie wykonano FULL, dodatkowych testów, restartu, staging, commit ani push.

## FILES_CHANGED

- tests/test_cycle_semantics_default_definition_effects.py — dopisano cztery testy w tym zadaniu; plik zawiera także wcześniejsze, istniejące zmiany R1.
- walkthrough.md — wymagany raport.

## FULL_DIFFS

Pełny rzeczywisty diff aktualnego pliku testowego względem HEAD. Fragment dotyczący stacked-decorators-default i testu kolizji istniał w worktree przed R2; cztery końcowe testy są zmianą R2.

    diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
    index aa604ad..e79dff6 100644
    --- a/tests/test_cycle_semantics_default_definition_effects.py
    +++ b/tests/test_cycle_semantics_default_definition_effects.py
    @@ -273,16 +273,16 @@ def test_p6_import_before_function_binding():
             ),
             pytest.param(
                 (
    -                "def upper(fn):\n"
    +                "def upper_decorator(fn):\n"
                     "    import pkg.upper\n"
                     "    return fn\n"
    -                "def lower(fn):\n"
    +                "def lower_decorator(fn):\n"
                     "    import pkg.lower\n"
                     "    return fn\n"
                     "def g():\n"
                     "    import pkg.default\n"
    -                "@upper\n"
    -                "@lower\n"
    +                "@upper_decorator\n"
    +                "@lower_decorator\n"
                     "def f(x=g()):\n"
                     "    pass\n"
                 ),
    @@ -292,7 +292,7 @@ def test_p6_import_before_function_binding():
                     "pkg.default": "pass",
                 },
                 ("pkg.default", "pkg.lower", "pkg.upper"),
    -            ("g", "lower", "upper"),
    +            ("g", "lower_decorator", "upper_decorator"),
                 id="stacked-decorators-default",
             ),
         ],
    @@ -443,3 +443,159 @@ def test_p6_decorated_opaque_child_collision_unknown():
         )
     
         assert result.outcome == "UNKNOWN"
    +
    +
    +def test_p6_stacked_decorator_child_name_collision_unknown():
    +    result = _p6_boundary_model(
    +        "def upper(fn):\n"
    +        "    import pkg.upper\n"
    +        "    return fn\n"
    +        "def lower(fn):\n"
    +        "    import pkg.lower\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.default\n"
    +        "@upper\n"
    +        "@lower\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {
    +            "pkg.upper": "pass",
    +            "pkg.lower": "pass",
    +            "pkg.default": "pass",
    +        },
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +    assert result.target_module == "pkg"
    +    assert result.symbol is None
    +    assert result.events == ()
    +
    +
    +def test_p6_decorator_import_before_final_binding():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    import pkg.child\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    return\n"
    +        "@deco\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.child": "from pkg import f"},
    +    )
    +
    +    assert result.outcome == "EARLY_BINDING_HAZARD"
    +    assert result.target_module == "pkg"
    +    assert result.symbol == "f"
    +    assert tuple(
    +        event.symbol
    +        for event in result.events
    +        if event.operation == "CALL_FUNCTION"
    +    ) == ("g", "deco")
    +
    +
    +def test_p6_decorator_same_name_as_defined_function():
    +    result = _p6_boundary_model(
    +        "def f(fn):\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.default\n"
    +        "@f\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.default": "pass"},
    +    )
    +
    +    assert result.outcome == "MODEL_PASS"
    +    assert tuple(
    +        event.symbol
    +        for event in result.events
    +        if event.operation == "CALL_FUNCTION"
    +    ) == ("g", "f")
    +    assert sum(
    +        event.operation == "DEFINE_OPAQUE_FUNCTION"
    +        and event.symbol == "f"
    +        for event in result.events
    +    ) == 1
    +
    +
    +def test_p6_keyword_only_defaults_before_decorator():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    import pkg.decorate\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.a\n"
    +        "def h():\n"
    +        "    import pkg.b\n"
    +        "@deco\n"
    +        "def f(x=1, *, y=g(), z=h()):\n"
    +        "    pass\n",
    +        {
    +            "pkg.a": "pass",
    +            "pkg.b": "pass",
    +            "pkg.decorate": "pass",
    +        },
    +    )
    +
    +    assert result.outcome == "MODEL_PASS"
    +    assert tuple(
    +        event.target
    +        for event in result.events
    +        if event.operation == "START_IMPORT"
    +        and event.target in {
    +            "pkg.a", "pkg.b", "pkg.decorate"
    +        }
    +    ) == ("pkg.a", "pkg.b", "pkg.decorate")
    +    assert tuple(
    +        event.symbol
    +        for event in result.events
    +        if event.operation == "CALL_FUNCTION"
    +    ) == ("g", "h", "deco")
    +
    +
    +def test_p6_cross_module_decorator_with_default():
    +    sources = {
    +        "pkg.__init__": ast.parse("pass"),
    +        "pkg.decorators": ast.parse(
    +            "def deco(fn):\n"
    +            "    import pkg.decorate\n"
    +            "    return fn\n"
    +        ),
    +        "pkg.app": ast.parse(
    +            "from pkg.decorators import deco\n"
    +            "def g():\n"
    +            "    import pkg.default\n"
    +            "@deco\n"
    +            "def f(x=g()):\n"
    +            "    pass\n"
    +        ),
    +        "pkg.default": ast.parse("pass"),
    +        "pkg.decorate": ast.parse("pass"),
    +    }
    +
    +    result = evaluate_package_import_order(
    +        sources, "pkg.app"
    +    )
    +
    +    assert result.outcome == "MODEL_PASS"
    +    assert tuple(
    +        event.target
    +        for event in result.events
    +        if event.operation == "START_IMPORT"
    +        and event.target in {
    +            "pkg.default", "pkg.decorate"
    +        }
    +    ) == ("pkg.default", "pkg.decorate")
    +    assert tuple(
    +        event.symbol
    +        for event in result.events
    +        if event.operation == "CALL_FUNCTION"
    +    ) == ("g", "deco")
    +    assert sum(
    +        event.operation == "DEFINE_OPAQUE_FUNCTION"
    +        and event.symbol == "f"
    +        and event.module == "pkg.app"
    +        for event in result.events
    +    ) == 1
