# P7-I2 — REPEATED DATACLASS FIELD ANNOTATIONS

## PREFLIGHT

- DIRECT_EVIDENCE: pierwszym źródłem był Contextor MCP `get_project_architecture(fields=[])`: LIVE revision 1480, provenance `live`, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `resync_required=false`, `syntax_errors=0` (fresh), `cycle_semantics=stale`.
- DIRECT_EVIDENCE: `get_symbol_implementation` przed zmianą potwierdził per-file `workspace_sync=verified` dla `package_model.py` i obu plików testowych. HEAD `c4b93be8c9d19e0d413b4c85e1f300c97be08b1a`; początkowy status zawierał tylko zastany `M walkthrough.md`.
- CODE_PATH_PROVED: kotwica I1 w `_safe_passive_class_definition`, `package_model.py:336–355`, budowała `annotated_names` jako `frozenset` i sprawdzała przecięcie z `function_binding_names`. Zbiór usuwał informację o powtórnej adnotacji pola. Nie zmieniono istniejącej kontroli przecięcia.

## CPYTHON_315_PARITY

DIRECT_EVIDENCE: `.venv/Scripts/python.exe` zgłosił wersję 3.15.2. Każdy przypadek wykonano w osobnym izolowanym pakiecie tymczasowym i osobnym podprocesie; trace `pkg/__init__.py` sprawdzał, czy `C` było związane po zakończeniu ramki modułu.

| Przypadek | Wynik `import pkg` | Wyjątek | `C` związana |
|---|---|---|---|
| A: `x: int; y: int; x: int = 1` | niepowodzenie | `TypeError: non-default argument 'y' follows default argument 'x'` | nie |
| B: `x: int = 1; y: int = 2` | powodzenie; pola `x`, `y` | brak | tak |
| Kontrprzykład bez defaultu: `x: int; y: int; x: int` | powodzenie; pola `x`, `y` | brak | tak |

INFERENCE: odrzucenie wszystkich powtórnych adnotacji przez model jest konserwatywnym `UNKNOWN`; nie twierdzi, że każdy taki program zgłasza wyjątek w CPythonie. Kontrprzykład uzasadnia to rozróżnienie.

## MODEL_BEFORE

DIRECT_EVIDENCE: te same źródła oceniono przez `evaluate_package_import_order` z `annotation_semantics="DEFERRED"`, `_compile_on_first_import=True`, `_assume_passive_external_imports=True`, `_assume_frozen_dataclass_decoration=True`, `entry_module="pkg"`, źródło `pkg.__init__`. Wspólny `evidence_scope`: `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`.

- A: `MODEL_PASS`, jedna assumed decoration `C`; events: `ENTRY START_IMPORT pkg`, `ASSUMED_EXTERNAL_IMPORT dataclasses.dataclass`, `CLASS_LOCAL_BIND x`, `ASSUMED_FROZEN_DATACLASS_DECORATION C`, `DEFINE_PASSIVE_CLASS C`, `READY pkg`.
- B: `MODEL_PASS`, jedna assumed decoration `C`; events: `ENTRY START_IMPORT pkg`, `ASSUMED_EXTERNAL_IMPORT dataclasses.dataclass`, `CLASS_LOCAL_BIND x`, `CLASS_LOCAL_BIND y`, `ASSUMED_FROZEN_DATACLASS_DECORATION C`, `DEFINE_PASSIVE_CLASS C`, `READY pkg`.
- Bez defaultu: `MODEL_PASS`, jedna assumed decoration `C`; events: `ENTRY START_IMPORT pkg`, `ASSUMED_EXTERNAL_IMPORT dataclasses.dataclass`, `ASSUMED_FROZEN_DATACLASS_DECORATION C`, `DEFINE_PASSIVE_CLASS C`, `READY pkg`.

`ENTRY` oznacza techniczny moduł `\u0000ENTRY`. Przed zmianą A był potwierdzoną rozbieżnością warunkowego modelu względem CPython: model przechodził poza nieudaną dekorację.

## EXACT_CHANGE

- W `package_model.py` wyłącznie zastąpiono zbiorowe zebranie adnotowanych nazw krotką `annotated_field_names`, następnie utworzono `annotated_names=frozenset(...)` i zwrot `False`, gdy długości są różne. Kontrola kolizji z `function_binding_names` pozostała.
- W `test_cycle_semantics_package_model.py` dodano dwa negatywne przypadki parametryzowane (z końcowym defaultem i bez), oba z istniejącym `_r8_frozen_dataclass_result` i `_r8_assert_rejected`, oraz pozytywny B z jednym rekordem assumed decoration.
- W `test_cycle_semantics_namespace_bound_model.py` dodano publiczną kontrolę `UNKNOWN` i braku assumed decoration dla A.
- Zakres strażnika wynika z tożsamości nazwy pola w semantyce dataclass; brak wyjątków zależnych od fixture, nazw pól lub tekstu wyjątku.

## TARGETED_RESULTS

DIRECT_EVIDENCE: uruchomiono wyłącznie wskazany podzbiór:

```
.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_namespace_bound_model.py -k "r8 or r10 or r11 or frozen_dataclass or p7"
113 passed, 152 deselected in 4.47s
```

CONTRACT_PROVED: testy potwierdzają lokalny kontrakt modelu, lecz sam zielony wynik nie jest dowodem ogólnej poprawności semantycznej ani runtime safety dekoratora.

## MODEL_AFTER

DIRECT_EVIDENCE: powtórzono ocenę tych samych źródeł i flag. Wspólny `evidence_scope` pozostał `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`.

- A: `UNKNOWN`, `assumed_dataclass_decorations=()`; events: `ENTRY START_IMPORT pkg`, `pkg ASSUMED_EXTERNAL_IMPORT dataclasses dataclass`, `pkg UNMODELED_STATEMENT ClassDef 2:1`.
- B: `MODEL_PASS`, jeden rekord assumed decoration `C`; events: `ENTRY START_IMPORT pkg`, assumed external dataclasses, `CLASS_LOCAL_BIND x`, `CLASS_LOCAL_BIND y`, `ASSUMED_FROZEN_DATACLASS_DECORATION C`, `DEFINE_PASSIVE_CLASS C`, `READY pkg`.
- Bez defaultu: `UNKNOWN`, `assumed_dataclass_decorations=()`; events jak A. CPython akceptuje ten przypadek; wynik modelu jest konserwatywny.

## MCP_AUDIT

- DIRECT_EVIDENCE: po edycjach LIVE kolejno zaobserwowano revision 1481, 1482, 1483. Ostatecznie per-file `workspace_sync=verified` dla `package_model.py`, `test_cycle_semantics_package_model.py` i `test_cycle_semantics_namespace_bound_model.py` (przy 1482 ostatni z tych plików testowych był chwilowo `out_of_sync`; ponowny odczyt przy 1483 dał `verified`).
- `get_project_architecture(fields=[])` po zmianach przy 1481: `canonical_state=fresh`, globalny `workspace_sync=unverified`, `resync_required=false`, `syntax_errors=0` (fresh), `cycle_semantics=stale`. Per-file odczyt nie jest dowodem odświeżenia rodziny `cycle_semantics` ani adopcji kodu przez proces backendu.
- Nie wykonywano ręcznego resync ani restartu.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_bound_model.py`
- `walkthrough.md` (wyłącznie raport; wyłączony z FULL_DIFFS zgodnie z AGENTS.md).

## FULL_DIFFS

Pełny rzeczywisty diff trzech plików source/tests aktualnego zadania:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index ea520f5..674b3b3 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -334,7 +334,7 @@ def _safe_passive_class_definition(
         return False
 
     if conditional_dataclass:
-        annotated_names = frozenset(
+        annotated_field_names = tuple(
             item.target.id
             for item in statement.body
             if (
@@ -343,6 +343,13 @@ def _safe_passive_class_definition(
                 and item.simple == 1
             )
         )
+        annotated_names = frozenset(
+            annotated_field_names
+        )
+        if len(annotated_field_names) != len(
+            annotated_names
+        ):
+            return False
         function_binding_names = frozenset(
             item.name
             for item in statement.body
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 805202e..b126b46 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -988,3 +988,21 @@ def test_p7_public_conditional_field_collision_unknown():
     model = result.conditional_assessment.model_assessment
     assert model is not None
     assert model.assumed_dataclass_decorations == ()
+
+
+def test_p7_public_conditional_repeated_field_annotation_unknown():
+    result = _dataclass_result(
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+        "    y: int\n"
+        "    x: int = 1\n",
+        decorate=True,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.conditional_assessment is not None
+    model = result.conditional_assessment.model_assessment
+    assert model is not None
+    assert model.assumed_dataclass_decorations == ()
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 358a539..9217482 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -2969,3 +2969,45 @@ def test_p7_dataclass_unrelated_property_remains_admitted():
         item.class_name
         for item in result.assumed_dataclass_decorations
     ) == ("C",)
+
+
+@pytest.mark.parametrize(
+    "class_body",
+    [
+        pytest.param(
+            "    x: int\n"
+            "    y: int\n"
+            "    x: int = 1\n",
+            id="repeated-with-final-default",
+        ),
+        pytest.param(
+            "    x: int\n"
+            "    y: int\n"
+            "    x: int\n",
+            id="repeated-without-default",
+        ),
+    ],
+)
+def test_p7_repeated_dataclass_field_annotation_unknown(class_body):
+    result = _r8_frozen_dataclass_result(
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        + class_body
+    )
+
+    _r8_assert_rejected(result, class_name="C")
+
+
+def test_p7_distinct_defaulted_dataclass_fields_admitted():
+    result = _r8_frozen_dataclass_result(
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int = 1\n"
+        "    y: int = 2\n"
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert tuple(
+        item.class_name
+        for item in result.assumed_dataclass_decorations
+    ) == ("C",)
```
