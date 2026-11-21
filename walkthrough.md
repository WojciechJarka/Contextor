# P7-I1 — Dataclass class-namespace binding guard

## PRECHECK

DIRECT_EVIDENCE: Contextor MCP przed zmianą: LIVE revision 1476, canonical_state=fresh, global workspace_sync=unverified, syntax_errors=0 (fresh), resync_required=false. Per-file workspace_sync=verified dla package_model.py, test_cycle_semantics_package_model.py i test_cycle_semantics_namespace_bound_model.py. _safe_passive_class_definition miał kotwicę if conditional_dataclass bezpośrednio przed seen_default_field = False (package_model.py:335–336). Odczytano helpery _r8_frozen_dataclass_result i _r8_assert_rejected oraz końce obu plików testowych.

HEAD przed zmianą: bc5e3856f0b59c9ac9340e94eeaf9e2dfb683e8b. Git status przed zmianą: M CHANGELOG.md, M walkthrough.md. To zastane zmiany; CHANGELOG.md nie został dotknięty.

## EXACT_CHANGES

W package_model.py dodano dokładnie wskazany warunek: przecięcie prostych nazw AnnAssign z nazwami FunctionDef/AsyncFunctionDef w warunkowej klasie dataclass zwraca False przed dalszą analizą pól. Nie zmieniono innych warunków ani handlerów runtime.

Na końcu test_cycle_semantics_package_model.py dopisano dwa negatywne warianty kolizji oraz pozytywny wariant niepowiązanej property. Na końcu test_cycle_semantics_namespace_bound_model.py dopisano publiczny kontrakt UNKNOWN. Podczas kontroli diffu wykryto, że ostatni test był początkowo umieszczony przy wcześniejszej identycznej kotwicy; przeniesiono ten sam blok na rzeczywisty EOF bez zmiany treści.

## TARGETED_RESULTS

Interpreter: CPython 3.15.2. Pierwsze dokładnie wskazane polecenie: 109 passed, 152 deselected. Po przeniesieniu testu na EOF wykonano je ponownie, aby sprawdzić końcową kolejność: 109 passed, 152 deselected w 3.07 s.

    .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_namespace_bound_model.py -k "r8 or r10 or r11 or frozen_dataclass or p7" --tb=long

Drugie dokładnie wskazane polecenie: 3 passed, 105 deselected w 1.59 s.

    .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_import_authority.py tests/test_cycle_semantics_passive_classes.py -k "dataclass or conditional_external" --tb=long

Brak FAIL; nie ma tracebacku. Nie uruchamiano pełnego pytest ani FULL.

## FIELD_NAMESPACE_INVARIANT

CODE_PATH_PROVED: warunek dotyczy wyłącznie conditional_dataclass i porównuje wszystkie proste nazwy pól z nazwami wiązanymi przez definicje funkcji w tym samym class body. Kolizja x/property x oraz token/metoda token kończy walidację przed ASSUMED_FROZEN_DATACLASS_DECORATION i DEFINE_PASSIVE_CLASS. Niezwiązana property label pozostaje poza przecięciem i test potwierdza wewnętrzny MODEL_PASS z jednym rekordem założonej dekoracji C.

DIRECT_EVIDENCE z P7-R1: CPython 3.15.2 dla obu kolizji z późniejszym wymaganym polem zgłasza TypeError: non-default argument 'y' follows default argument 'x' (w wariancie metody analogicznie), przed związaniem C i importem dziecka. Guard konserwatywnie zwraca UNKNOWN także dla innych kolizji tych nazw; nie twierdzi, że każda taka klasa jest błędna w CPython.

## CONDITIONAL_AUTHORITY_BOUNDARY

MODEL_PASS w pozytywnym teście jest wewnętrznym wynikiem z jawnymi założeniami o imporcie dataclasses i dekoracji frozen; nie jest produkcyjnym dowodem runtime. Nowy test publiczny potwierdza UNKNOWN oraz pustą listę assumed_dataclass_decorations dla kolizji. Nie zmieniono mapowania CONDITIONAL_MODEL_PASS, polityk warunkowych, receipt ani warning suppression.

## MCP_AUDIT

Desktop watcher opublikował kolejno: revision 1477 dla package_model.py, 1478 dla test_cycle_semantics_package_model.py, 1479 dla test_cycle_semantics_namespace_bound_model.py oraz 1480 po przeniesieniu testu na EOF. Wszystkie eventy: origin=desktop_watcher, operation=update_file, status=UPDATED; ciągłość zachowana, resync_required=false.

Końcowy Contextor LIVE revision 1480, canonical_state=fresh, syntax_errors=0 (fresh), resync_required=false. Per-file workspace_sync=verified przy revision 1480 dla wszystkich trzech zmienionych plików. Global workspace_sync=unverified, cycle_semantics=stale.

Bez restartu, staging, commit i push.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
- tests/test_cycle_semantics_namespace_bound_model.py
- walkthrough.md — wyłącznie raport

Zastany CHANGELOG.md pozostawiono bez zmian.

## FULL_DIFFS

Pełny rzeczywisty diff trzech zmienionych plików względem HEAD:

    diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
    index 88f8bc9..ea520f5 100644
    --- a/contextor/core/cycle_semantics/package_model.py
    +++ b/contextor/core/cycle_semantics/package_model.py
    @@ -334,6 +334,28 @@ def _safe_passive_class_definition(
             return False
     
         if conditional_dataclass:
    +        annotated_names = frozenset(
    +            item.target.id
    +            for item in statement.body
    +            if (
    +                isinstance(item, ast.AnnAssign)
    +                and isinstance(item.target, ast.Name)
    +                and item.simple == 1
    +            )
    +        )
    +        function_binding_names = frozenset(
    +            item.name
    +            for item in statement.body
    +            if isinstance(
    +                item,
    +                (ast.FunctionDef, ast.AsyncFunctionDef),
    +            )
    +        )
    +        if not annotated_names.isdisjoint(
    +            function_binding_names
    +        ):
    +            return False
    +
             seen_default_field = False
     
             uses_field_call = any(
    diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
    index a8b5de5..805202e 100644
    --- a/tests/test_cycle_semantics_namespace_bound_model.py
    +++ b/tests/test_cycle_semantics_namespace_bound_model.py
    @@ -968,3 +968,23 @@ def test_p8_unreachable_module_bad_hash_still_rejected():
         assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
         assert result.source_evidence_sha256 is None
         assert result.conditional_assessment is None
    +
    +
    +def test_p7_public_conditional_field_collision_unknown():
    +    result = _dataclass_result(
    +        "from dataclasses import dataclass\n"
    +        "@dataclass(frozen=True)\n"
    +        "class C:\n"
    +        "    x: int\n"
    +        "    @property\n"
    +        "    def x(self):\n"
    +        "        return 1\n"
    +        "    y: int\n",
    +        decorate=True,
    +    )
    +
    +    assert result.outcome == "UNKNOWN"
    +    assert result.conditional_assessment is not None
    +    model = result.conditional_assessment.model_assessment
    +    assert model is not None
    +    assert model.assumed_dataclass_decorations == ()
    diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
    index 72a01da..358a539 100644
    --- a/tests/test_cycle_semantics_package_model.py
    +++ b/tests/test_cycle_semantics_package_model.py
    @@ -2919,3 +2919,53 @@ def test_p11_strict_mode_remains_whole_module_unknown():
             and event.symbol == "value"
             for event in opt_in.events
         )
    +
    +
    +@pytest.mark.parametrize(
    +    "class_body",
    +    [
    +        pytest.param(
    +            "    x: int\n"
    +            "    @property\n"
    +            "    def x(self):\n"
    +            "        return 1\n"
    +            "    y: int\n",
    +            id="property-binding",
    +        ),
    +        pytest.param(
    +            "    token: int\n"
    +            "    def token(self):\n"
    +            "        pass\n"
    +            "    required: int\n",
    +            id="function-binding",
    +        ),
    +    ],
    +)
    +def test_p7_dataclass_field_function_binding_unknown(
    +    class_body,
    +):
    +    result = _r8_frozen_dataclass_result(
    +        "@dataclass(frozen=True)\n"
    +        "class C:\n"
    +        + class_body
    +    )
    +
    +    _r8_assert_rejected(result, class_name="C")
    +
    +
    +def test_p7_dataclass_unrelated_property_remains_admitted():
    +    result = _r8_frozen_dataclass_result(
    +        "@dataclass(frozen=True)\n"
    +        "class C:\n"
    +        "    x: int\n"
    +        "    y: int\n"
    +        "    @property\n"
    +        "    def label(self):\n"
    +        "        return 1\n"
    +    )
    +
    +    assert result.outcome == "MODEL_PASS"
    +    assert tuple(
    +        item.class_name
    +        for item in result.assumed_dataclass_decorations
    +    ) == ("C",)
