# P9-I1-R9 — TRWAŁE KONTRAKTY A–O

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP jako pierwsze źródło: LIVE revision 1501, `canonical_state=fresh`, `syntax_errors=0`, `resync_required=false`. Per-file `workspace_sync=verified` dla `tests/test_cycle_semantics_package_model.py::_actual`; globalny `workspace_sync=unverified`.
- HEAD: `728711a2de8f830c0e789260d839260db186702a`. Przed edycją status obejmował wyłącznie zastany raport `walkthrough.md`; test i source były czyste.
- MCP i literalny odczyt potwierdziły importy `evaluate_package_import_order`, `STANDARD_BUILTINS_PRECONDITION`, `pytest`, helper `_actual(tmp_path, source, entry)` oraz dokładną kotwicę EOF. Helper uruchamia import próbki w osobnym procesie `sys.executable -I -B`.
- CONTRACT_PROVED: poprzedni audyt R8 porównał A–M z CPython 3.15.2, w tym pozytywne i negatywne kontrprzykłady. N/O pozostają tylko kontraktem konserwatywnego UNKNOWN.

## EXACT_TEST_ADDITION

- Dopisano dosłownie `_P9_I1_CASES` oraz jeden test parametryczny `test_p9_i1_known_builtin_decorator_identity` na końcu pliku. Istniejące funkcje i asercje pozostały bez zmian.
- Diff obejmuje 193 dodane linie w jednym pliku testowym. Produkcji nie zmieniano.

## MATRIX_A_O

- A–F: wymagany warunkowy `MODEL_PASS`, jedna założona dekoracja C, `DEFINE_PASSIVE_CLASS(C)` przed `START_IMPORT(pkg.child)`; zwykły evaluator zwraca `UNKNOWN`.
- G–O: wymagany `UNKNOWN`, bez założonej dekoracji C, bez `DEFINE_PASSIVE_CLASS(C)` i bez dojścia do `pkg.child`.
- B/C/H: dodatkowo potwierdzenie założonego external `FROM builtins import property`.
- Każdy wariant sprawdza `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF` i `builtin_environment_precondition=STANDARD_BUILTINS_PRECONDITION`.

## CPYTHON_315_PARITY

- DIRECT_EVIDENCE: `_actual` uruchamia A–M w izolowanych podprocesach CPython 3.15.2. A–F oraz I/J/L/M importują się poprawnie; G/H/K kończą się niepowodzeniem importu. To zgadza się z niezależnymi wynikami discovery R8.
- N/O mają `python_success=None`; test nie wykonuje dla nich próby importu CPythona. Ich runtime parity: NOT_PROVED. Modelowy `UNKNOWN` w I/J/L/M jest konserwatywną odmową, nie błędem CPythona.

## TARGETED_RESULTS

- `ast.parse(tests/test_cycle_semantics_package_model.py)`: `AST_OK`, exit 0.
- `git diff --check`: exit 0.
- `-k "test_p9_i1_known_builtin_decorator_identity"`: **15 passed, 228 deselected**.
- `-k "r10 or r11 or p7 or p8 or p9_i1"`: **85 passed, 158 deselected**.
- Oba zestawy uruchomiono przez `.venv/Scripts/python.exe` (CPython 3.15.2). Bez FAIL; bez pełnego pytest i FULL.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: `desktop_watcher` opublikował `UPDATED` dla pliku testowego w LIVE revision 1502; `continuity=continuous`, `resync_required=false`.
- LIVE revision 1502, `canonical_state=fresh`, `syntax_errors=0` (fresh), per-file `workspace_sync=verified` dla nowego testu. Globalny `workspace_sync=unverified`.
- Status P9-I1: **VALIDATION IN PROGRESS**.

## FILES_CHANGED

- `tests/test_cycle_semantics_package_model.py` — jedyny zmieniony plik source/tests.
- `walkthrough.md` — nadpisany raport; nie jest liczony jako plik source/tests.

## FULL_DIFFS

Pełny aktualny diff pliku testowego względem HEAD:

```diff
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 1f92467..2278282 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -3173,3 +3173,196 @@ def test_p8_field_boundary_unknown(class_body, prelude):
         and event.target == "pkg.child"
         for event in result.events
     )
+
+
+_P9_I1_CASES = (
+    ("A", "", "", "@property", "", "", True, True),
+    (
+        "B",
+        "from builtins import property as prop\n",
+        "", "@prop", "", "", True, True,
+    ),
+    (
+        "C",
+        "from builtins import property as prop\n"
+        "alias = prop\n",
+        "", "@alias", "", "", True, True,
+    ),
+    (
+        "D", "alias = property\n",
+        "", "@alias", "", "", True, True,
+    ),
+    (
+        "E", "alias = property\nproperty = None\n",
+        "", "@alias", "", "", True, True,
+    ),
+    (
+        "F", "", "", "@property", "",
+        "property = None\n", True, True,
+    ),
+    (
+        "G", "property = None\n",
+        "", "@property", "", "", False, False,
+    ),
+    (
+        "H",
+        "from builtins import property as prop\n"
+        "prop = None\n",
+        "", "@prop", "", "", False, False,
+    ),
+    (
+        "I",
+        "def property(fn):\n    return fn\n",
+        "", "@property", "", "", False, True,
+    ),
+    (
+        "J",
+        "def ta_nazwa(fn):\n    return fn\n",
+        "", "@ta_nazwa", "", "", False, True,
+    ),
+    (
+        "K", "",
+        "    property: object = None\n",
+        "@property", "", "", False, False,
+    ),
+    (
+        "L", "",
+        "    def property(fn):\n        return fn\n",
+        "@property", "", "", False, True,
+    ),
+    (
+        "M", "",
+        "    from builtins import property as property\n",
+        "@property", "", "", False, True,
+    ),
+    (
+        "N", "", "", "@property.setter",
+        "", "", False, None,
+    ),
+    (
+        "O", "", "", "@property()",
+        "", "", False, None,
+    ),
+)
+
+
+@pytest.mark.parametrize(
+    (
+        "case_id,before_class,class_before,"
+        "decorator,class_after,after_class,"
+        "model_pass,python_success"
+    ),
+    _P9_I1_CASES,
+    ids=[case[0] for case in _P9_I1_CASES],
+)
+def test_p9_i1_known_builtin_decorator_identity(
+    tmp_path,
+    case_id,
+    before_class,
+    class_before,
+    decorator,
+    class_after,
+    after_class,
+    model_pass,
+    python_success,
+):
+    source = (
+        "from dataclasses import dataclass\n"
+        + before_class
+        + "@dataclass(frozen=True)\n"
+        + "class C:\n"
+        + "    x: int\n"
+        + "    y: int\n"
+        + class_before
+        + f"    {decorator}\n"
+        + "    def value(self):\n"
+        + "        return 1\n"
+        + class_after
+        + after_class
+        + "import pkg.child\n"
+    )
+    sources = {
+        "pkg.__init__": source,
+        "pkg.child": "pass\n",
+    }
+    trees = {
+        name: ast.parse(code)
+        for name, code in sources.items()
+    }
+
+    model = evaluate_package_import_order(
+        trees,
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+    assert model.outcome == (
+        "MODEL_PASS" if model_pass else "UNKNOWN"
+    )
+    assert model.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert (
+        model.builtin_environment_precondition
+        == STANDARD_BUILTINS_PRECONDITION
+    )
+
+    decorations = [
+        item
+        for item in model.assumed_dataclass_decorations
+        if item.class_name == "C"
+    ]
+    assert len(decorations) == int(model_pass)
+
+    events = list(model.events)
+    class_positions = [
+        index
+        for index, event in enumerate(events)
+        if (
+            event.operation == "DEFINE_PASSIVE_CLASS"
+            and event.symbol == "C"
+        )
+    ]
+    child_positions = [
+        index
+        for index, event in enumerate(events)
+        if (
+            event.operation == "START_IMPORT"
+            and event.target == "pkg.child"
+        )
+    ]
+
+    if model_pass:
+        assert len(class_positions) == 1
+        assert len(child_positions) == 1
+        assert class_positions[0] < child_positions[0]
+        assert model.reached_unmodeled_import is None
+    else:
+        assert class_positions == []
+        assert child_positions == []
+
+    if case_id in {"B", "C", "H"}:
+        assert any(
+            item.target == "builtins"
+            and item.symbol == "property"
+            for item in model.assumed_external_imports
+        )
+
+    if model_pass:
+        ordinary = evaluate_package_import_order(
+            trees,
+            "pkg",
+            annotation_semantics="DEFERRED",
+            _compile_on_first_import=True,
+        )
+        assert ordinary.outcome == "UNKNOWN"
+
+    if python_success is not None:
+        assert (
+            _actual(tmp_path, sources, "pkg")
+            is python_success
+        )
```
