# P8-I1 — SEMANTYKA FIELD BEZ WARTOŚCI DOMYŚLNEJ

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP był pierwszym źródłem. Przed zmianą LIVE revision 1483, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `resync_required=false`, `syntax_errors=0` (fresh), `cycle_semantics=stale`. Per-file MCP: cztery docelowe pliki `verified`.
- DIRECT_EVIDENCE: HEAD `1cbae7758c297b8c08cce3dacf083cde206d1599`; zastany git status `M CHANGELOG.md`, `M walkthrough.md`. Nie zmieniono `CHANGELOG.md`. Kotwice P8-R1 w `definition_checks.py:27–40` i `package_model.py:365–451, 979–991, 2539–2550` były aktualne.
- CODE_PATH_PROVED: właścicielem dopuszczania wywołania był stary helper AST; `_safe_passive_class_definition` ustawiało `seen_default_field` dla samego wywołania; `_compile` emitował `CHECK_DATACLASS_FIELD_FACTORY`; handler wymagał bieżącego znacznika importu `dataclasses.field`. Konsument publiczny mapuje wewnętrzny wynik na wynik warunkowy.

## CPYTHON_315_COUNTEREXAMPLE

DIRECT_EVIDENCE: CPython `.venv/Scripts/python.exe` 3.15.2, osobny katalog tymczasowy i podproces na każdy przypadek. `pkg.child` zawierał `pass`. Trace końca ramki `pkg/__init__.py` sprawdzał związanie `C`.

- A `a: int = field(hash=False); b: int`: `import pkg` OK, `C` związana, `pkg.child` zaimportowany. `field(hash=False)` ma `default=MISSING` i `default_factory=MISSING` (`C:\Python315\Lib\dataclasses.py:384–405, 663–681, 1085–1103`).
- B `a: int = 1; b: int = field(hash=False)`: `TypeError: non-default argument 'b' follows default argument 'a'`; `C` niezwiązana, `pkg.child` niezaimportowany. Wynik wynika z kolejności argumentów generowanego `__init__`, nie z nazwy pola.

## MODEL_BEFORE

DIRECT_EVIDENCE: identyczne źródła, `entry_module='pkg'`, `annotation_semantics='DEFERRED'`, `_compile_on_first_import=True`, `_assume_passive_external_imports=True`, `_assume_frozen_dataclass_decoration=True`. Oba miały `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`.

- A: `UNKNOWN`, zero assumed decoration. Events: `ENTRY START_IMPORT pkg`; cztery `ASSUMED_EXTERNAL_IMPORT` dla `dataclasses.dataclass`, `dataclasses.field` (po dwa); `UNMODELED_STATEMENT ClassDef 2:1`.
- B: wewnętrzny warunkowy `MODEL_PASS`, jedna assumed decoration. Po tych samych czterech assumed imports events: `CLASS_LOCAL_BIND a`, `CLASS_LOCAL_BIND b`, `ASSUMED_FROZEN_DATACLASS_DECORATION C`, `DEFINE_PASSIVE_CLASS C`, `START_IMPORT pkg.child`, `pkg.child READY`, `BIND_CHILD`, `IMPORT`, `pkg READY`. To była potwierdzona fałszywa warunkowa akceptacja względem CPython, bez produkcyjnej authority.

## EXACT_CHANGES

- W `execution/definition_checks.py` dokładnie zastąpiono helper rozpoznający wyłącznie `field(hash=False)` przez `_restricted_defaultless_dataclass_field_call`. Dopuszcza tylko prostą nazwę i argumenty `hash` (`bool` lub `None`) oraz `compare` (`bool`) bez default/default_factory; zwraca nazwę wywoływanej funkcji, a nie dowód jej tożsamości.
- W `package_model.py` `seen_default_field` powstaje tylko od literalnego defaultu; brak `value` i dopuszczony call znaczą brak defaultu. Check nazwy funkcji jest wykonany przed class-local bind i porównuje aktualny namespace ze znacznikiem `dataclasses.field`. Zachowano ochronę przed kolizją z nazwą fabryki oraz pozostałe ścieżki dekoracji i publikacji.
- W dwóch plikach testowych dodano pozytywne, negatywne i publiczne kontrakty. Z historycznej listy odmów usunięto dokładnie `field()`, `field(hash=True)`, `field(hash=False, compare=True)`, które mieszczą się w nowym ograniczonym zakresie.
- Semantyczny audyt: pozytywne i negatywne przykłady opierają się na default/default_factory z CPython, tożsamości aktualnego importu i kolejności pól. Formy poza ograniczonym zakresem pozostają `UNKNOWN`; brak wyjątków opartych na nazwach pól/klas.

## TEST_CONTRACTS

- Pozytywne parametry: `field(hash=False)`, `field(compare=False)`, `field()`, `field(hash=False, compare=False)`, `field(hash=True)`, `field(hash=None)`, alias importu oraz `field(hash=False)` przed literalnym defaultem. Każdy wymaga jednego assumed decoration i importu dziecka po `DEFINE_PASSIVE_CLASS`.
- Negatywne parametry: literalny default przed trzema formami bezdefaultowego `field`, rebind `field=None`, funkcja o nieudowodnionej tożsamości, `default=1`, `default_factory=list`, `init=False`, niepoprawny typ `hash` i `compare`. Każdy wymaga `UNKNOWN`, braku assumed decoration i braku importu dziecka. Dla `init=False` jest to konserwatywna odmowa, nie stwierdzenie błędu CPython.
- Publiczna ścieżka source-bound: poprawna kolejność `CONDITIONAL_MODEL_PASS`, odwrotna `UNKNOWN`; w obu zachowano warunkowy charakter.

## TARGETED_RESULTS

DIRECT_EVIDENCE: wykonano wyłącznie wskazane podzbiory na CPython 3.15.2:

```
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_namespace_bound_model.py -k "r8 or r10 or r11 or frozen_dataclass or p7 or p8"
132 passed, 150 deselected in 7.19s

.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_import_authority.py tests/test_cycle_semantics_passive_classes.py -k "dataclass or conditional_external"
3 passed, 105 deselected in 1.56s
```

## MODEL_AFTER

DIRECT_EVIDENCE: ponowny odczyt evaluatora dla A/B z tymi samymi źródłami i flagami.

- A: wewnętrzny warunkowy `MODEL_PASS`, jedna assumed decoration, `CLASS_LOCAL_BIND a`, potem assumed decoration, `DEFINE_PASSIVE_CLASS C`, następnie import i READY `pkg.child` oraz READY `pkg`. Brak `CLASS_LOCAL_BIND b`, bo nie ma przypisania wartości. Scope nadal `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`.
- B: `UNKNOWN`, zero assumed decoration; po czterech assumed imports `UNMODELED_STATEMENT ClassDef 2:1`; bez importu `pkg.child`. Model odmawia przed runtime `TypeError` CPython, a nie emituje tego wyjątku.

## CONDITIONAL_AUTHORITY_BOUNDARY

CODE_PATH_PROVED: `evaluate_conditional_namespace_import_order` mapuje wewnętrzny `MODEL_PASS` na `CONDITIONAL_MODEL_PASS` (`package_model.py:3608–3640`), a source-bound projekcja nie promuje outcome. Produkcyjne `analyze_cycle_scenarios` wywołuje evaluator bez założeń (`scenarios.py:330–360`); ostrzeżenia wymagają zainstalowanego claim `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` (`warning_eligibility.py:20–109`, `partial_warning_eligibility.py:19–132`). Warunkowy wynik A nie stanowi zwykłego `MODEL_PASS` ani samodzielnej podstawy wyciszenia ostrzeżeń. Nie wykonywano FULL/LIVE produkcyjnej oceny tych pakietów.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1488, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `syntax_errors=0` (fresh), `resync_required=false`. Per-file `workspace_sync=verified` przy końcowym odczycie dla wszystkich czterech zmienionych plików: `execution/definition_checks.py`, `package_model.py` i obu plików testowych. Przejściowe `out_of_sync` przy rev 1484–1487 ustąpiło po eventach watcher; nie użyto ręcznego resync.
- `cycle_semantics` pozostało `stale`; per-file sync nie dowodzi adopcji zmienionego kodu przez proces serwera MCP.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/definition_checks.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (sam raport, poza wymaganym diffem source/tests). Zastanego `CHANGELOG.md` nie zmieniono.

## FULL_DIFFS

Pełny rzeczywisty diff czterech plików source/tests aktualnego zadania:

```diff
diff --git a/contextor/core/cycle_semantics/execution/definition_checks.py b/contextor/core/cycle_semantics/execution/definition_checks.py
index 1d470b3..6a4cfff 100644
--- a/contextor/core/cycle_semantics/execution/definition_checks.py
+++ b/contextor/core/cycle_semantics/execution/definition_checks.py
@@ -24,20 +24,39 @@ def _exact_frozen_dataclass_decorator(
     )
 
 
-def _exact_restricted_dataclass_hash_field_call(
+def _restricted_defaultless_dataclass_field_call(
     node: ast.AST,
-) -> bool:
-    return (
-        type(node) is ast.Call
-        and type(node.func) is ast.Name
-        and node.func.id == "field"
-        and not node.args
-        and len(node.keywords) == 1
-        and node.keywords[0].arg == "hash"
-        and type(node.keywords[0].value) is ast.Constant
-        and type(node.keywords[0].value.value) is bool
-        and node.keywords[0].value.value is False
-    )
+) -> str | None:
+    if (
+        type(node) is not ast.Call
+        or type(node.func) is not ast.Name
+        or not node.func.id.isidentifier()
+        or node.func.id.startswith("__")
+        or node.args
+    ):
+        return None
+
+    seen: set[str] = set()
+
+    for keyword in node.keywords:
+        if (
+            keyword.arg not in {"hash", "compare"}
+            or keyword.arg in seen
+            or type(keyword.value) is not ast.Constant
+        ):
+            return None
+
+        value = keyword.value.value
+
+        if keyword.arg == "hash":
+            if type(value) not in {bool, type(None)}:
+                return None
+        elif type(value) is not bool:
+            return None
+
+        seen.add(keyword.arg)
+
+    return node.func.id
 
 
 def _restricted_dataclass_field_annotation(
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 674b3b3..9e0bf3f 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -32,7 +32,7 @@ from .execution.expressions import (
 )
 from .execution.definition_checks import (
     _exact_frozen_dataclass_decorator,
-    _exact_restricted_dataclass_hash_field_call,
+    _restricted_defaultless_dataclass_field_call,
     _restricted_dataclass_field_annotation,
 )
 from .execution.class_facts import (
@@ -365,14 +365,17 @@ def _safe_passive_class_definition(
 
         seen_default_field = False
 
-        uses_field_call = any(
-            isinstance(item, ast.AnnAssign)
-            and item.value is not None
-            and _exact_restricted_dataclass_hash_field_call(
-                item.value
-            )
-            for item in statement.body
-        )
+        field_factory_names: set[str] = set()
+
+        for item in statement.body:
+            if isinstance(item, ast.AnnAssign):
+                field_name = (
+                    _restricted_defaultless_dataclass_field_call(
+                        item.value
+                    )
+                )
+                if field_name is not None:
+                    field_factory_names.add(field_name)
 
         uses_property = any(
             type(item) is ast.FunctionDef
@@ -382,10 +385,7 @@ def _safe_passive_class_definition(
             for item in statement.body
         )
 
-        protected_names = set()
-
-        if uses_field_call:
-            protected_names.add("field")
+        protected_names = set(field_factory_names)
 
         if uses_property:
             protected_names.add("property")
@@ -421,34 +421,35 @@ def _safe_passive_class_definition(
                     return False
 
                 default_value = body_statement.value
-
-                if default_value is None:
-                    if seen_default_field:
-                        return False
-                else:
-                    literal_default = (
-                        type(default_value) is ast.Constant
-                        and type(default_value.value) in {
-                            type(None),
-                            bool,
-                            int,
-                            float,
-                            complex,
-                            str,
-                            bytes,
-                        }
+                literal_default = (
+                    type(default_value) is ast.Constant
+                    and type(default_value.value) in {
+                        type(None),
+                        bool,
+                        int,
+                        float,
+                        complex,
+                        str,
+                        bytes,
                     }
+                )
+                field_call_name = (
+                    _restricted_defaultless_dataclass_field_call(
+                        default_value
                     )
+                )
 
-                    if (
-                        not literal_default
-                        and not
-                        _exact_restricted_dataclass_hash_field_call(
-                            default_value
-                        )
-                    ):
-                        return False
+                if (
+                    default_value is not None
+                    and not literal_default
+                    and field_call_name is None
+                ):
+                    return False
 
+                if literal_default:
                     seen_default_field = True
+                elif seen_default_field:
+                    return False
 
             if isinstance(
                 body_statement,
@@ -478,9 +479,9 @@ def _safe_passive_class_definition(
                 and body_statement.simple == 1
                 and body_statement.target.id.isidentifier()
                 and not body_statement.target.id.startswith("__")
-                and _exact_restricted_dataclass_hash_field_call(
+                and _restricted_defaultless_dataclass_field_call(
                     body_statement.value
-                )
+                ) is not None
             ):
                 continue
 
@@ -979,13 +980,16 @@ def _compile(
                         isinstance(body_statement, ast.AnnAssign)
                         and body_statement.value is not None
                     ):
-                        if _exact_restricted_dataclass_hash_field_call(
-                            body_statement.value
-                        ):
+                        field_name = (
+                            _restricted_defaultless_dataclass_field_call(
+                                body_statement.value
+                            )
+                        )
+                        if field_name is not None:
                             steps.append(
                                 _Step(
                                     "CHECK_DATACLASS_FIELD_FACTORY",
-                                    target="field",
+                                    target=field_name,
                                 )
                             )
 
@@ -2538,8 +2542,8 @@ def evaluate_package_import_order(
 
         elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
             if (
-                step.target != "field"
-                or namespaces[module].get("field")
+                not step.target
+                or namespaces[module].get(step.target)
                 != "\x00ASSUMED_EXTERNAL:dataclasses:field"
             ):
                 return result(
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index b126b46..d209f5a 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -1006,3 +1006,44 @@ def test_p7_public_conditional_repeated_field_annotation_unknown():
     model = result.conditional_assessment.model_assessment
     assert model is not None
     assert model.assumed_dataclass_decorations == ()
+
+
+@pytest.mark.parametrize(
+    "class_body,expected_outcome",
+    [
+        pytest.param(
+            "    a: int = field(hash=False)\n"
+            "    b: int\n",
+            "CONDITIONAL_MODEL_PASS",
+            id="defaultless-field",
+        ),
+        pytest.param(
+            "    a: int = 1\n"
+            "    b: int = field(hash=False)\n",
+            "UNKNOWN",
+            id="invalid-order",
+        ),
+    ],
+)
+def test_p8_public_defaultless_field_order(class_body, expected_outcome):
+    result = _dataclass_result(
+        "from dataclasses import dataclass, field\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        + class_body
+        + "import pkg.ns.b\n",
+        decorate=True,
+        child="pass\n",
+    )
+
+    assert result.outcome == expected_outcome
+    assert result.conditional_assessment is not None
+    model = result.conditional_assessment.model_assessment
+    assert model is not None
+    if expected_outcome == "CONDITIONAL_MODEL_PASS":
+        assert tuple(
+            item.class_name
+            for item in model.assumed_dataclass_decorations
+        ) == ("C",)
+    else:
+        assert model.assumed_dataclass_decorations == ()
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 9217482..1f92467 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1025,11 +1025,8 @@ def test_r11_requires_exact_field_factory_binding(
 @pytest.mark.parametrize(
     "default_expression",
     [
-        "field()",
         "field(default=1)",
-        "field(hash=True)",
         "field(hash=0)",
-        "field(hash=False, compare=True)",
         "other(hash=False)",
         "field(hash=False) or None",
     ],
@@ -3011,3 +3008,168 @@ def test_p7_distinct_defaulted_dataclass_fields_admitted():
         item.class_name
         for item in result.assumed_dataclass_decorations
     ) == ("C",)
+
+
+def _p8_field_result(class_body, *, import_line=None, prelude=""):
+    if import_line is None:
+        import_line = "from dataclasses import dataclass, field\n"
+    sources = {
+        "pkg.__init__": ast.parse(
+            import_line
+            + prelude
+            + "@dataclass(frozen=True)\n"
+            + "class C:\n"
+            + class_body
+            + "import pkg.child\n"
+        ),
+        "pkg.child": ast.parse("pass"),
+    }
+    return evaluate_package_import_order(
+        sources,
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+
+@pytest.mark.parametrize(
+    "class_body,import_line",
+    [
+        pytest.param(
+            "    a: int = field(hash=False)\n    b: int\n",
+            None,
+            id="hash-false-before-required",
+        ),
+        pytest.param(
+            "    a: int = field(compare=False)\n    b: int\n",
+            None,
+            id="compare-false-before-required",
+        ),
+        pytest.param(
+            "    a: int = field()\n    b: int\n",
+            None,
+            id="empty-field-before-required",
+        ),
+        pytest.param(
+            "    a: int = field(hash=False, compare=False)\n"
+            "    b: int\n",
+            None,
+            id="hash-and-compare",
+        ),
+        pytest.param(
+            "    a: int = field(hash=True)\n    b: int\n",
+            None,
+            id="hash-true",
+        ),
+        pytest.param(
+            "    a: int = field(hash=None)\n    b: int\n",
+            None,
+            id="hash-none",
+        ),
+        pytest.param(
+            "    a: int = make_field(compare=False)\n"
+            "    b: int\n",
+            "from dataclasses import dataclass, field as make_field\n",
+            id="import-alias",
+        ),
+        pytest.param(
+            "    a: int = field(hash=False)\n    b: int = 1\n",
+            None,
+            id="before-literal-default",
+        ),
+    ],
+)
+def test_p8_defaultless_field_conditional_pass(class_body, import_line):
+    result = _p8_field_result(class_body, import_line=import_line)
+
+    assert result.outcome == "MODEL_PASS"
+    assert tuple(
+        item.class_name
+        for item in result.assumed_dataclass_decorations
+    ) == ("C",)
+    events = list(result.events)
+    class_positions = [
+        index
+        for index, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "C"
+    ]
+    child_positions = [
+        index
+        for index, event in enumerate(events)
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    ]
+    assert len(class_positions) == len(child_positions) == 1
+    assert class_positions[0] < child_positions[0]
+
+
+@pytest.mark.parametrize(
+    "class_body,prelude",
+    [
+        pytest.param(
+            "    a: int = 1\n    b: int = field(hash=False)\n",
+            "",
+            id="literal-before-hash-false",
+        ),
+        pytest.param(
+            "    a: int = 1\n    b: int = field(compare=False)\n",
+            "",
+            id="literal-before-compare-false",
+        ),
+        pytest.param(
+            "    a: int = 1\n    b: int = field()\n",
+            "",
+            id="literal-before-empty-field",
+        ),
+        pytest.param(
+            "    a: int = field(hash=False)\n    b: int\n",
+            "field = None\n",
+            id="rebound-to-none",
+        ),
+        pytest.param(
+            "    a: int = make_field(compare=False)\n"
+            "    b: int\n",
+            "def make_field(*, compare):\n    pass\n",
+            id="unproven-function",
+        ),
+        pytest.param(
+            "    a: int = field(default=1)\n    b: int\n",
+            "",
+            id="explicit-default",
+        ),
+        pytest.param(
+            "    a: int = field(default_factory=list)\n"
+            "    b: int\n",
+            "",
+            id="default-factory",
+        ),
+        pytest.param(
+            "    a: int = field(init=False)\n    b: int\n",
+            "",
+            id="init-false",
+        ),
+        pytest.param(
+            "    a: int = field(hash=0)\n    b: int\n",
+            "",
+            id="invalid-hash-type",
+        ),
+        pytest.param(
+            "    a: int = field(compare=0)\n    b: int\n",
+            "",
+            id="invalid-compare-type",
+        ),
+    ],
+)
+def test_p8_field_boundary_unknown(class_body, prelude):
+    result = _p8_field_result(class_body, prelude=prelude)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+        for event in result.events
+    )
```
