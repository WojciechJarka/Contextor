# P9-I1-R10 — SOURCE-BOUND PUBLIC CONTRACT

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP jako pierwsze źródło: LIVE revision 1502, `canonical_state=fresh`, `syntax_errors=0`, `resync_required=false`; per-file `workspace_sync=verified` dla `tests/test_cycle_semantics_namespace_bound_model.py::_dataclass_result`. Globalny `workspace_sync=unverified`.
- HEAD `43479a05f20bac69499b987e884f18cd334db9ad`; status wejściowy czysty. MCP i odczyt pliku potwierdziły `_dataclass_result`, `_external_case`, `pytest`, `frozen_dataclass_t01–t04` oraz kotwicę EOF.
- CODE_PATH_PROVED: `_dataclass_result` uruchamia source-bound publiczny evaluator z `target_python_version=(3,15)`, flagami `decorate` i `external`; `_external_case` buduje snapshot źródła oraz fingerprint.

## EXACT_TEST_ADDITION

- Dopisano dosłownie `_P9_I1_SOURCE_BOUND_CASES` i jeden test parametryczny `test_p9_i1_source_bound_decorator_identity` na końcu wskazanego pliku.
- Diff: 164 dodane linie; brak edycji istniejących testów, helperów i kodu produkcyjnego.

## PUBLIC_OUTCOME_MATRIX

| Przypadki | Oczekiwany publiczny wynik | Wewnętrzny wynik | Dekoracja C i import `pkg.ns.b` |
|---|---|---|---|
| A, B, C, E | `CONDITIONAL_MODEL_PASS` | `MODEL_PASS` pod założeniami | jedna dekoracja, klasa przed importem |
| G, H, I, M, N, O | `UNKNOWN` | `UNKNOWN` | brak dekoracji i importu |

- B/C/H potwierdzają rekord założonego `FROM builtins import property`. C/E potwierdzają event `ALIAS`. Każdy wariant sprawdza, że ścieżka bez flag warunkowych zwraca `UNKNOWN`.

## CONDITIONAL_AUTHORITY

- CONTRACT_PROVED: test wymaga `authority=SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF`, wewnętrznego `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF` i `builtin_environment_precondition=CONVENTIONAL_BUILTINS_ASSUMED_NOT_RUNTIME_ATTESTED`.
- W A/B/C/E test wymaga niepustego `source_evidence_sha256`; ten fingerprint nie jest dowodem stanu runtime ani LIVE. Publiczny wynik nie jest bezwarunkowym `MODEL_PASS`.

## IMPORT_ORDER_CONTRACT

- A/B/C/E wymagają dokładnie jednego `DEFINE_PASSIVE_CLASS(C)` przed dokładnie jednym `START_IMPORT(pkg.ns.b)`. G/H/I/M/N/O nie mogą osiągnąć żadnego z tych eventów.
- `pkg.ns.b` zawiera `from pkg.ns.a import C`, więc kolejność wiązania klasy przed importem dziecka jest częścią sprawdzanego kontraktu.

## TARGETED_RESULTS

- `ast.parse(tests/test_cycle_semantics_namespace_bound_model.py)`: `AST_OK`, exit 0.
- `git diff --check`: exit 0.
- `-k "p9_i1_source_bound_decorator_identity"`: **10 passed, 54 deselected**.
- `-k "frozen_dataclass or p9_i1"`: **31 passed, 33 deselected**.
- Testy uruchomiono przez `.venv/Scripts/python.exe` (CPython 3.15.2). Bez FAIL; bez pełnego pytest i FULL.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: `desktop_watcher` opublikował `UPDATED` dla pliku testowego w LIVE revision 1503; `continuity=continuous`, `resync_required=false`.
- LIVE revision 1503, `canonical_state=fresh`, `syntax_errors=0` (fresh), per-file `workspace_sync=verified` dla nowego testu. Globalny `workspace_sync=unverified`.
- Status: **P9-I1 VALIDATION IN PROGRESS**.

## ISSUES_MD_CHECK

- `issues.md` istnieje; odczyt nie wykazał wpisów P9. Pliku nie zmieniano.

## FILES_CHANGED

- `tests/test_cycle_semantics_namespace_bound_model.py` — jedyny zmieniony plik source/tests.
- `walkthrough.md` — nadpisany raport, poza diffem source/tests.

## FULL_DIFFS

Pełny aktualny diff source/tests względem HEAD:

```diff
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index d209f5a..7a0b750 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -1047,3 +1047,167 @@ def test_p8_public_defaultless_field_order(class_body, expected_outcome):
         ) == ("C",)
     else:
         assert model.assumed_dataclass_decorations == ()
+
+
+_P9_I1_SOURCE_BOUND_CASES = (
+    ("A", "", "", "@property", True),
+    (
+        "B",
+        "from builtins import property as prop\n",
+        "", "@prop", True,
+    ),
+    (
+        "C",
+        "from builtins import property as prop\n"
+        "alias = prop\n",
+        "", "@alias", True,
+    ),
+    (
+        "E",
+        "alias = property\nproperty = None\n",
+        "", "@alias", True,
+    ),
+    (
+        "G",
+        "property = None\n",
+        "", "@property", False,
+    ),
+    (
+        "H",
+        "from builtins import property as prop\n"
+        "prop = None\n",
+        "", "@prop", False,
+    ),
+    (
+        "I",
+        "def property(fn):\n    return fn\n",
+        "", "@property", False,
+    ),
+    (
+        "M",
+        "",
+        "    from builtins import property as property\n",
+        "@property", False,
+    ),
+    ("N", "", "", "@property.setter", False),
+    ("O", "", "", "@property()", False),
+)
+
+
+@pytest.mark.parametrize(
+    "case_id,prelude,class_prelude,decorator,accepted",
+    _P9_I1_SOURCE_BOUND_CASES,
+    ids=[
+        case[0]
+        for case in _P9_I1_SOURCE_BOUND_CASES
+    ],
+)
+def test_p9_i1_source_bound_decorator_identity(
+    case_id,
+    prelude,
+    class_prelude,
+    decorator,
+    accepted,
+):
+    source = (
+        "from dataclasses import dataclass\n"
+        + prelude
+        + "@dataclass(frozen=True)\n"
+        + "class C:\n"
+        + "    x: int\n"
+        + "    y: int\n"
+        + class_prelude
+        + f"    {decorator}\n"
+        + "    def value(self):\n"
+        + "        return 1\n"
+        + "import pkg.ns.b\n"
+    )
+    child = "from pkg.ns.a import C\n"
+
+    result = _dataclass_result(
+        source,
+        decorate=True,
+        external=True,
+        child=child,
+    )
+
+    assert result.outcome == (
+        "CONDITIONAL_MODEL_PASS"
+        if accepted else "UNKNOWN"
+    )
+    assert result.authority == (
+        "SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_"
+        "NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+    assert result.conditional_assessment is not None
+
+    model = (
+        result.conditional_assessment.model_assessment
+    )
+    assert model is not None
+    assert model.outcome == (
+        "MODEL_PASS" if accepted else "UNKNOWN"
+    )
+    assert model.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert model.builtin_environment_precondition == (
+        "CONVENTIONAL_BUILTINS_ASSUMED_NOT_RUNTIME_ATTESTED"
+    )
+
+    decorated_classes = [
+        item
+        for item in model.assumed_dataclass_decorations
+        if item.class_name == "C"
+    ]
+    assert len(decorated_classes) == int(accepted)
+
+    events = list(model.events)
+    defined = [
+        index
+        for index, event in enumerate(events)
+        if (
+            event.operation == "DEFINE_PASSIVE_CLASS"
+            and event.symbol == "C"
+        )
+    ]
+    started_child = [
+        index
+        for index, event in enumerate(events)
+        if (
+            event.operation == "START_IMPORT"
+            and event.target == "pkg.ns.b"
+        )
+    ]
+
+    if accepted:
+        assert len(defined) == 1
+        assert len(started_child) == 1
+        assert defined[0] < started_child[0]
+        assert result.source_evidence_sha256 is not None
+    else:
+        assert defined == []
+        assert started_child == []
+
+    if case_id in {"B", "C", "H"}:
+        assert any(
+            item.target == "builtins"
+            and item.symbol == "property"
+            for item in model.assumed_external_imports
+        )
+
+    if case_id in {"C", "E"}:
+        assert any(
+            event.operation == "ALIAS"
+            and event.symbol == "alias"
+            for event in events
+        )
+
+    ordinary = _dataclass_result(
+        source,
+        decorate=False,
+        external=False,
+        child=child,
+    )
+    assert ordinary.outcome == "UNKNOWN"
```
