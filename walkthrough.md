# P6-D05-I2 — General decorator snapshot + opaque defaults

## PRECHECK

**DIRECT_EVIDENCE — przed zmianami:** Contextor LIVE revision 1469, provenance live; canonical_state=fresh; global workspace_sync=unverified; syntax_errors=0 (fresh); resync_required=false; parse_stale_modules={}; cycle_semantics=stale. Per-file workspace_sync verified przy rev. 1469 dla wszystkich czterech targetów. HEAD: 8248b54b2051aaafaa75316fe60486ee623bd53e. git status przed zmianami: M walkthrough.md — wyłącznie raport z poprzedniego zadania.

Odczytano dokładne kotwice przez Contextor MCP: _DefinitionState i _new_definition_state; _safe_class_namespace_value; _safe_passive_function_definition; gałąź ast.FunctionDef w _compile; obie kolizjowe bramki; handler snapshotów klas; DEFINE_DECORATED_PASSIVE_CLASS; DEFINE_OPAQUE_FUNCTION; DEFINE_STACKED_FUNCTION; snapshot/call/frame helpers. Literalne wystąpienia class_decorator_snapshots były dokładnie pięć: dwa w state.py i trzy w package_model.py. Kotwica decorated-unsupported-body w named_function_decorators.py odpowiadała oczekiwanej starej wartości UNKNOWN.

**DIRECT_EVIDENCE — issues.md:** odczytano bez zmian. Zawiera historyczne wpisy o cyklach strukturalnych, TYPE_CHECKING, kompilowalności AST/CPython i wywołaniach metod; brak wpisu P6-D05.

**INDEPENDENT CPYTHON EVIDENCE:** użyty interpreter to CPython 3.15.2. W izolowanych podprocesach potwierdzono: decorated-unsupported-body wywołuje identity, nie importuje pkg.child z deferred body i wiąże f; early-binding fixture kończy się ImportError, zanim f zostanie związane; child-name collision przechodzi w CPython, wiążąc pkg.child jako funkcję bez załadowania pkg.child module; późniejsze f() w identity-decorated fixture kończy się poprawnie. Z wcześniejszego CPython R1 dla dokładnego stacked default fixture: kolejność importów pkg.default, pkg.lower, pkg.upper, bez wyjątku, f związane. Pierwszy dodatkowy probe importów w tym etapie nie wykonał próbek z powodu błędu instrumentacji fromlist=None; odrzucono go i ponowiono z poprawionym wrapperem, bez zmiany fixtures.

## EXACT_CHANGES

Wprowadzono literalnie wskazane zmiany w czterech plikach:

- execution/state.py: rename class_decorator_snapshots → definition_decorator_snapshots w polu i konstruktorze; typ i inicjalizacja dict bez zmian.
- package_model.py: helper _opaque_function_value; aktualizacja docstringu; restricted defaults dla ast.FunctionDef; snapshot named decoratorów przed default-call; opcode DEFINE_DECORATED_OPAQUE_FUNCTION; wspólny snapshot map dla klas i funkcji; zastosowanie snapshotowanych restricted decorators do opaque value; nowe opcode dodane do obu collision guards.
- named_function_decorators.py: parametr decorated-unsupported-body oczekuje MODEL_PASS i CALL_FUNCTION identity.
- default_definition_effects.py: dopisano dwa testy security z polecenia.

Po nieudanym zestawie nie poprawiano implementacji ani oczekiwań testowych.

## TARGETED_RESULTS

Uruchomiono dokładnie wskazaną komendę:

    .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_default_definition_effects.py tests/test_cycle_semantics_named_function_decorators.py tests/test_cycle_semantics_decorator_import_effect_baseline.py tests/test_cycle_semantics_decorator_snapshots.py tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_function_frame_result_owner.py tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_definition_effect_order_cpython.py --tb=long

Wynik na CPython 3.15.2:

    1 failed, 103 passed in 15.77s

Jedyny FAIL: test_p6_decorated_default_effect_order[stacked-decorators-default]. Actual outcome UNKNOWN; expected MODEL_PASS. Pozostałe 103 przypadki PASS.

Traceback z FAIL:

    _____ test_p6_decorated_default_effect_order[stacked-decorators-default] _____
    source = 'def upper(fn):\\n    import pkg.upper\\n    return fn\\ndef lower(fn):\\n    import pkg.lower\\n    return fn\\ndef g():\\n    import pkg.default\\n@upper\\n@lower\\ndef f(x=g()):\\n    pass\\n'
    children = {'pkg.upper': 'pass', 'pkg.lower': 'pass', 'pkg.default': 'pass'}
    expected_imports = ('pkg.default', 'pkg.lower', 'pkg.upper')
    expected_calls = ('g', 'lower', 'upper')

        result = _p6_boundary_model(source, children)
    >   assert result.outcome == "MODEL_PASS"
    E   AssertionError: assert 'UNKNOWN' == 'MODEL_PASS'
    E
    E   - MODEL_PASS
    E   + UNKNOWN
    tests/test_cycle_semantics_default_definition_effects.py:308: AssertionError

Odczytowy evaluator diagnostic dla tego samego wejścia zwrócił outcome=UNKNOWN, target_module=pkg, symbol=None, events=[]. Nie wykonano kolejnego pytest.

## SEMANTIC_ORDER

**DIRECT_EVIDENCE — CPython:** stacked fixture działa poprawnie: default g() wykonuje import pkg.default przed zastosowaniem dekoratorów; następnie lower importuje pkg.lower, a upper importuje pkg.upper. f zostaje związane po łańcuchu dekoracji. Single-decorator fixture również ma import default przed dekoratorem. CPython execution nie raportuje błędu.

**DIRECT_EVIDENCE — model dla failing fixture:** model zwraca UNKNOWN/pkg przed eventami. Wartości eventów nie są częściowo emitowane; lista jest pusta.

**INFERENCE poparta source path:** odmowa następuje przed interpreterem, w istniejącym package child-collision precheck. W module pkg są top-level definicje nazw upper i lower, a indeksowane dzieci pakietu to pkg.upper, pkg.lower i pkg.default. Zatem definicje upper/lower kolidują bezpośrednio z nazwami dzieci.

## OPAQUE_BINDING_BOUNDARY

Single decorated default, early binding hazard i późniejsze opaque f() testy przeszły. Nowa ścieżka tworzy sentinel opaque, przekazuje go do restricted decorator frame i wiąże wynik dopiero po zakończeniu frame/łańcucha. W early-binding fixture import dziecka następuje przed krokiem definicji/bindingu f, więc evaluator publikuje EARLY_BINDING_HAZARD.

**NOT_PROVED dla stacked success w modelu:** test nie dochodzi do snapshotu ani decorated-opaque handlera, ponieważ collision guard zwraca UNKNOWN wcześniej. Oczekiwany event order dla stacked fixture nie został uzyskany przez evaluator.

## COLLISION_GUARDS

**CODE_PATH_PROVED:** istniejąca bramka w package_model.py, linie 1698–1718, zawiera komentarz, że definicja funkcji i bezpośrednie dziecko pakietu o tej samej nazwie wymaga bogatszej semantyki shadowing/import binding. Bramkę rozszerzono o DEFINE_DECORATED_OPAQUE_FUNCTION zgodnie z poleceniem; nie zmieniono warunków.

Fragment aktywny dla stacked fixture:

    if any(
        step.op in {
            "DEFINE_FUNCTION",
            "DEFINE_DECORATED_FUNCTION",
            "DEFINE_STACKED_FUNCTION",
            "DEFINE_OPAQUE_FUNCTION",
            "DEFINE_DECORATED_OPAQUE_FUNCTION",
            "DEFINE_PASSIVE_CLASS",
            "DEFINE_DECORATED_PASSIVE_CLASS",
            "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
        }
        and step.binding in children
        for step in programs[package]
    ):
        return result("UNKNOWN", package)

Dla testu B step.binding=upper/lower jest równy bezpośredniej nazwie dziecka upper/lower. W ten sposób prompt jednocześnie wymaga zachowania collision guardu, a test B wymaga MODEL_PASS dla wejścia objętego tym guardem. To sprzeczne oczekiwania. Osłabienie guardu albo zmiana nazw/fixture przekracza literalne polecenie.

**VERDICT: BLOCKED_SEMANTIC_INTEGRITY.** Stan po wymaganych zmianach pozostawiono do audytu; po odkryciu konfliktu nie zmieniano source ani tests.

## MCP_AUDIT

Po zmianie Contextor zgłosił LIVE revision 1474, provenance live; canonical_state=fresh; global workspace_sync=unverified; syntax_errors=0 (fresh); resync_required=false; parse_stale_modules={}; cycle_semantics=stale.

Per-file workspace_sync przy revision 1474 był verified dla wszystkich czterech plików, co według kontraktu get_symbol_implementation oznacza potwierdzone SHA-256 disk == canonical T0:

- contextor/core/cycle_semantics/package_model.py — verified
- contextor/core/cycle_semantics/execution/state.py — verified
- tests/test_cycle_semantics_named_function_decorators.py — verified
- tests/test_cycle_semantics_default_definition_effects.py — verified

Zapytanie get_live_events(after_revision=1469, limit=20) zwróciło confirmation_required przy estimated_output_bytes=15548, powyżej progu 15360. Nie ponawiano szerokiego zapytania; event details z tej odpowiedzi są niedostępne. Per-file synchronizacja jest bezpośrednio potwierdzona przez odczyty symboli.

git status po zmianach: cztery wskazane source/test files zmienione oraz walkthrough.md. HEAD pozostał 8248b54b2051aaafaa75316fe60486ee623bd53e. Nie wykonano staging, commit, push, restartu, update_file, ręcznego resync ani FULL.

## FILES_CHANGED

1. contextor/core/cycle_semantics/package_model.py
2. contextor/core/cycle_semantics/execution/state.py
3. tests/test_cycle_semantics_named_function_decorators.py
4. tests/test_cycle_semantics_default_definition_effects.py
5. walkthrough.md — raport wymagany poleceniem; report-only.

## FULL_DIFFS

Kompletny rzeczywisty diff czterech source/test files względem HEAD:

    diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
    index d54a968..31a2bdf 100644
    --- a/contextor/core/cycle_semantics/execution/state.py
    +++ b/contextor/core/cycle_semantics/execution/state.py
    @@ -100,7 +100,7 @@ class _DefinitionState:
             str, tuple[tuple[_ClassFact, ...], _ClassFact]
         ]
         class_facts_by_identity: dict[str, _ClassFact]
    -    class_decorator_snapshots: dict[
    +    definition_decorator_snapshots: dict[
             str,
             tuple[tuple[str, object], ...],
         ]
    @@ -113,5 +113,5 @@ def _new_definition_state() -> _DefinitionState:
                 fact.identity: fact
                 for fact in _BUILTIN_CLASS_FACTS.values()
             },
    -        class_decorator_snapshots={},
    +        definition_decorator_snapshots={},
         )
    diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
    index 8f8b5cc..88f8bc9 100644
    --- a/contextor/core/cycle_semantics/package_model.py
    +++ b/contextor/core/cycle_semantics/package_model.py
    @@ -107,6 +107,10 @@ def _safe_class_namespace_value(value: object) -> bool:
         return False
     
     
    +def _opaque_function_value(module: str, name: str) -> str:
    +    return "\x00OPAQUE_FUNCTION:" + module + ":" + name
    +
    +
     @dataclass(frozen=True)
     class PackageImportAssessment:
         entry_module: str
    @@ -154,7 +158,7 @@ def _safe_passive_function_definition(
         """A definition whose creation has no unknown evaluations.
     
         Its body may be opaque because function bodies are deferred.
    -    Only literal default expressions are supported.
    +    Only literal defaults and opt-in restricted calls are supported.
         """
         if (
             not statement.name.isidentifier()
    @@ -1050,7 +1054,7 @@ def _compile(
                     stmt,
                     annotation_semantics=annotation_semantics,
                     allow_restricted_decorator=True,
    -                allow_restricted_default_calls=not stmt.decorator_list,
    +                allow_restricted_default_calls=True,
                 ):
                     return None
     
    @@ -1159,7 +1163,38 @@ def _compile(
                         restricted_callable = False
     
                 if stmt.decorator_list and not restricted_callable:
    -                return None
    +                if not (
    +                    args.defaults
    +                    or any(
    +                        value is not None
    +                        for value in args.kw_defaults
    +                    )
    +                ):
    +                    return None
    +
    +                if (
    +                    type(stmt.lineno) is not int
    +                    or stmt.lineno < 1
    +                    or type(stmt.col_offset) is not int
    +                    or stmt.col_offset < 0
    +                ):
    +                    return None
    +
    +                decorator_definition_id = (
    +                    f"{logical}:{stmt.lineno}:{stmt.col_offset}"
    +                )
    +
    +                steps.append(
    +                    _Step(
    +                        "SNAPSHOT_FUNCTION_DECORATORS",
    +                        binding=stmt.name,
    +                        definition_id=decorator_definition_id,
    +                        decorator_names=tuple(
    +                            item.id
    +                            for item in stmt.decorator_list
    +                        ),
    +                    )
    +                )
     
                 for default in (*args.defaults, *args.kw_defaults):
                     if type(default) is ast.Call:
    @@ -1199,6 +1234,14 @@ def _compile(
                             ) if len(stmt.decorator_list) > 1 else (),
                         )
                     )
    +            elif stmt.decorator_list:
    +                steps.append(
    +                    _Step(
    +                        "DEFINE_DECORATED_OPAQUE_FUNCTION",
    +                        binding=stmt.name,
    +                        definition_id=decorator_definition_id,
    +                    )
    +                )
                 else:
                     steps.append(
                         _Step(
    @@ -1661,6 +1704,7 @@ def evaluate_package_import_order(
                     "DEFINE_DECORATED_FUNCTION",
                     "DEFINE_STACKED_FUNCTION",
                     "DEFINE_OPAQUE_FUNCTION",
    +                "DEFINE_DECORATED_OPAQUE_FUNCTION",
                     "DEFINE_PASSIVE_CLASS",
                     "DEFINE_DECORATED_PASSIVE_CLASS",
                     "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
    @@ -1692,8 +1736,8 @@ def evaluate_package_import_order(
         definition_state = _new_definition_state()
         prepared_class_bases = definition_state.prepared_class_bases
         class_facts_by_identity = definition_state.class_facts_by_identity
    -    class_decorator_snapshots = (
    -        definition_state.class_decorator_snapshots
    +    definition_decorator_snapshots = (
    +        definition_state.definition_decorator_snapshots
         )
     
         bootstrap = "\x00ENTRY"
    @@ -1767,6 +1811,7 @@ def evaluate_package_import_order(
                             "DEFINE_DECORATED_FUNCTION",
                             "DEFINE_STACKED_FUNCTION",
                             "DEFINE_OPAQUE_FUNCTION",
    +                        "DEFINE_DECORATED_OPAQUE_FUNCTION",
                             "DEFINE_PASSIVE_CLASS",
                             "DEFINE_DECORATED_PASSIVE_CLASS",
                             "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
    @@ -2188,6 +2233,78 @@ def evaluate_package_import_order(
                         )
                     )
     
    +        elif step.op == "DEFINE_DECORATED_OPAQUE_FUNCTION":
    +            if not step.binding or not step.definition_id:
    +                return result("UNKNOWN", module, step.binding)
    +
    +            decorator_pairs = (
    +                definition_decorator_snapshots.pop(
    +                    step.definition_id,
    +                    None,
    +                )
    +            )
    +
    +            if not decorator_pairs:
    +                return result("UNKNOWN", module, step.binding)
    +
    +            application_order = tuple(
    +                reversed(decorator_pairs)
    +            )
    +            first_name, first_object = application_order[0]
    +
    +            if (
    +                not isinstance(first_object, _RestrictedFunction)
    +                or len(first_object.parameters) != 1
    +                or first_object.defining_module not in logical_sources
    +                or first_object.defining_module not in programs
    +            ):
    +                return result("UNKNOWN", module, first_name)
    +
    +            opaque_function = _opaque_function_value(
    +                module,
    +                step.binding,
    +            )
    +            local_bindings: dict[str, object | None] = {}
    +
    +            body = _execute_restricted_object_call(
    +                first_object,
    +                opaque_function,
    +                module=first_object.defining_module,
    +                local_bindings=local_bindings,
    +            )
    +
    +            if body is None:
    +                return result("UNKNOWN", module, first_name)
    +
    +            events.append(
    +                PackageModelEvent(
    +                    module,
    +                    "DEFINE_OPAQUE_FUNCTION",
    +                    symbol=step.binding,
    +                )
    +            )
    +            events.append(
    +                PackageModelEvent(
    +                    module,
    +                    "CALL_FUNCTION",
    +                    symbol=first_name,
    +                )
    +            )
    +
    +            frames[-1] = _advance_frame(frames[-1])
    +            frames.append(
    +                _FunctionFrame(
    +                    module=first_object.defining_module,
    +                    index=0,
    +                    steps=body,
    +                    local_bindings=local_bindings,
    +                    decorator_final_binding=step.binding,
    +                    remaining_decorators=application_order[1:],
    +                    binding_module=module,
    +                )
    +            )
    +            continue
    +
             elif step.op == "DEFINE_STACKED_FUNCTION":
                 if (
                     not step.binding
    @@ -2379,10 +2496,7 @@ def evaluate_package_import_order(
     
             elif step.op == "DEFINE_OPAQUE_FUNCTION":
                 namespaces[module][step.binding] = (
    -                "\x00OPAQUE_FUNCTION:"
    -                + module
    -                + ":"
    -                + step.binding
    +                _opaque_function_value(module, step.binding)
                 )
     
                 events.append(
    @@ -2488,7 +2602,10 @@ def evaluate_package_import_order(
                     )
                 )
     
    -        elif step.op == "SNAPSHOT_CLASS_DECORATORS":
    +        elif step.op in {
    +            "SNAPSHOT_CLASS_DECORATORS",
    +            "SNAPSHOT_FUNCTION_DECORATORS",
    +        }:
                 if (
                     not step.definition_id
                     or not step.binding
    @@ -2508,7 +2625,7 @@ def evaluate_package_import_order(
                         step.binding,
                     )
     
    -            class_decorator_snapshots[
    +            definition_decorator_snapshots[
                     step.definition_id
                 ] = tuple(
                     zip(
    @@ -2662,7 +2779,7 @@ def evaluate_package_import_order(
                 )
                 class_facts_by_identity[identity] = class_fact
                 if step.op == "DEFINE_DECORATED_PASSIVE_CLASS":
    -                decorator_pairs = class_decorator_snapshots.pop(
    +                decorator_pairs = definition_decorator_snapshots.pop(
                         identity,
                         None,
                     )
    diff --git a/tests/test_cycle_semantics_default_definition_effects.py b/tests/test_cycle_semantics_default_definition_effects.py
    index 85776b1..aa604ad 100644
    --- a/tests/test_cycle_semantics_default_definition_effects.py
    +++ b/tests/test_cycle_semantics_default_definition_effects.py
    @@ -411,3 +411,35 @@ def test_p6_decorated_opaque_later_call_unknown():
             and event.symbol == "f"
             for event in result.events
         )
    +
    +
    +def test_p6_decorated_default_early_binding_hazard():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    import pkg.child\n"
    +        "@deco\n"
    +        "def f(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.child": "from pkg import f"},
    +    )
    +
    +    assert result.outcome == "EARLY_BINDING_HAZARD"
    +    assert result.target_module == "pkg"
    +    assert result.symbol == "f"
    +
    +
    +def test_p6_decorated_opaque_child_collision_unknown():
    +    result = _p6_boundary_model(
    +        "def deco(fn):\n"
    +        "    return fn\n"
    +        "def g():\n"
    +        "    return\n"
    +        "@deco\n"
    +        "def child(x=g()):\n"
    +        "    pass\n",
    +        {"pkg.child": "pass"},
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    diff --git a/tests/test_cycle_semantics_named_function_decorators.py b/tests/test_cycle_semantics_named_function_decorators.py
    index 9e88d6a..45853c5 100644
    --- a/tests/test_cycle_semantics_named_function_decorators.py
    +++ b/tests/test_cycle_semantics_named_function_decorators.py
    @@ -52,7 +52,7 @@ CASES = [
         pytest.param(
              "def identity(fn):\n    return fn\n@identity\ndef f(x=1):\n    import pkg.child\n",
    -        None, (), "UNKNOWN", (),
    +        None, (), "MODEL_PASS", ("identity",),
             id="decorated-unsupported-body",
         ),

