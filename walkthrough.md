# P10-R4-I3 — semantyczna ocena adnotacji

## PREFLIGHT / LIVE PRZED ZMIANĄ

- DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])`: LIVE revision **1510**, `canonical_state=fresh`, `resync_required=false`, `cycle_semantics=fresh`, globalne `workspace_sync=unverified`.
- DIRECT_EVIDENCE: `get_module_context(..., compact=true)` dla `package_model`, `execution.definition_checks`, `execution.steps`, `execution.class_facts`: każdy per-file `workspace_sync=verified` przy revision 1510.
- Git HEAD przed zmianą `5d2477252bd2a87d420a77ff67e6b759af6ab979`; poza raportem `walkthrough.md` nie było zastanych zmian. Dokładne anchory `_restricted_dataclass_field_annotation`, `annotation_builtin_names` i gałąź `DEFINE_CONDITIONAL_FROZEN_DATACLASS` pasowały do źródła. SOURCE_DRIFT=NO.

## MECHANIZMY ZMIENIONE

- CODE_PATH_PROVED: nowy `execution/annotation_effects.py` ocenia ograniczony AST w dwóch fazach: `_eval` rozpoznaje wartości i pasywne operacje, `_consume` sprawdza konsekwencje konsumpcji tekstowych adnotacji w ścieżce `dataclasses`. Nie uruchamia kodu analizowanego pakietu. Fakty typu, aliasu, union i indeksowanego modułu są symboliczne.
- CODE_PATH_PROVED: `_Step` zachowuje teraz uporządkowane `(nazwa_pola, AST_adnotacji)` i ograniczone wartości class-local (`execution/steps.py:19–22`, `package_model.py` w gałęzi kompilacji klasy). Usunięto `annotation_builtin_names` i dawny filtr składniowy `execution/definition_checks.py`; wszystkie inne kontrole klasy, pól, defaultów, `field()` i dekoratora pozostały.
- CODE_PATH_PROVED: `DEFINE_CONDITIONAL_FROZEN_DATACLASS` najpierw sprawdza sentinel założonego `dataclass`, następnie ocenia wszystkie pola w kolejności źródłowej, dopiero potem konsumuje ich wyniki. Przy nieudowodnionej operacji zwraca `UNKNOWN` z nazwą pola przed zapisem założonej dekoracji. Wcześniejsze eventy importów pozostają. Po sukcesie dotychczasowa kolejność `assumed_dataclass_decorations` → wiązanie klasy → event dekoracji → event klasy jest zachowana.
- CONTRACT_PROVED: wyniki nadal mają `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`. Model nadal nie poświadcza rzeczywistego importu zewnętrznego, builtins ani runtime Desktop.

## NIEZALEŻNY AUDYT SEMANTYCZNY

- CPython 3.15.2 `C:\Python315\Lib\dataclasses.py:1057–1058` pobiera adnotacje w FORWARDREF przed `_get_field`; `:759–817,855–858` dla tekstu przechodzi po ścieżce `getattr` w module. `C:\Python315\Lib\annotationlib.py:798–879` opisuje ewaluację i ewentualne ponowienie. To uzasadnia oddzielenie `_eval` od `_consume` i sprawdzanie obu konsumpcji tekstu.
- DIRECT_EVIDENCE: przypadek `"side.missing"` z `C:\Temp\p10_i2_string_probe.py`: pasywny import `side`, a potem `side.__getattr__` podnosi `SystemExit("annotation-effect")` podczas dekoracji. Nowy model zwraca `UNKNOWN` bez eventu założonej dekoracji; test `test_textual_attribute_can_invoke_external_getattr` porównuje oba wyniki i nie uruchamia `side.py` w evaluatorze.
- CONTRACT_PROVED: odczyt `ast.AST` po tylko założonym pasywnym imporcie `ast` nie ma autorytatywnego faktu o atrybucie. Poprzedni specjalny predykat dopuszczał tę dokładną nazwę mimo braku dowodu późniejszego odczytu. To istniejący wyjątek zależny od nazwy i kodu Contextora; został usunięty. Siedem dawnych oczekiwań R10 i odpowiadające nazwy testów skorygowano z tej przyczyny semantycznej, nie dla uzyskania zielonego testu. Dotychczasowa ścieżka `ast.AST` staje się konserwatywnym `UNKNOWN`; lokalne `list[int]` i `int | None` pozostają rozstrzygalne.
- Nie dodano nowych wyjątków nazwowych dla kodu Contextora. Zbiór standardowych typów i operacji odzwierciedla ograniczony kontrakt CPython, a nie identyfikatory projektu. Nie stwierdzono nowego hardcode pod Contextora w zmianie.

## CPYTHON / MODEL — WYNIKI

- DIRECT_EVIDENCE: `tests/test_cycle_semantics_annotation_effects_i3.py` uruchamia każdą próbkę w osobnym procesie `sys.executable` = CPython 3.15.2, z osobnym katalogiem, i analizuje AST tych samych źródeł lokalnym evaluatorem. Dwie oceny modelu są identyczne i nie mutują oryginalnego AST.
- AGREEMENT przy aktywnych założeniach warunkowych: `list[int]`, `list[str] | None`, `None | list[str]`, `int | None`, `str | None`, `str | int`, `str | None | None`, alias znanej klasy, `[T][0]`, tekst `"str"`, nieaktywna gałąź `1 if True else T[int]` i tekst `"T[int]"`: CPython importuje, model daje warunkowy `MODEL_PASS`. Efektowne `T.__class_getitem__` nie wywołuje się dla nieaktywnej gałęzi ani tekstu. Model przyjmuje także znany atrybut klasy z indeksowanego modułu w osobnej próbce.
- CONSERVATIVE_UNKNOWN przed założoną dekoracją: efektowne `T[int]`, przeciążone `T | str` na niestandardowej metaklasie, atrybut z deskryptorem, zewnętrzne `ast.AST`, przesłonięty builtin, brakujące wiązanie, nieznane class-local oraz `"side.missing"`. Dla trzech dynamicznych przypadków CPython podnosi odpowiednio `SystemExit getitem-effect`, `or-effect`, `descriptor-effect`; `ast.AST`, przesłonięty `str` i brakująca nazwa mogą się zaimportować w CPython, lecz model pozostaje nieautorytatywny. Dla `"side.missing"` CPython zgłasza `SystemExit annotation-effect` po `SIDE_GETATTR missing`.
- DIRECT_EVIDENCE: class-local `T: int = 1; x: T = 2` przy przesłonięciu modułowego T daje w CPython `Field.type` równy `1` i warunkowy `MODEL_PASS`; pole `T: int` bez wartości nie tworzy class-local wiązania. Rebinding aliasu modułowego przed dekoracją daje `Field.type=<class 'pkg.New'>` mimo późniejszego `T=Old`. W izolowanej próbie wrapper dekoratora wypisał `BOUND_BEFORE False`; C wiązane jest po dekoracji.
- DIRECT_EVIDENCE: próba dwuetapowa wypisała `GETITEM` przed `SIDE_GETATTR missing`; potwierdza, że ewaluacja wszystkich pól w FORWARDREF poprzedza tekstową konsumpcję w `_get_field`. Model kończy `UNKNOWN` przed założoną dekoracją. To nie jest dowód, że liczba ponowień `annotationlib` jest stała w innych przypadkach.

## TESTY I REGRESJE

- `.venv\Scripts\python.exe -V` → Python 3.15.2. Końcowy targeted pytest: `.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_package_model_annotations315.py tests/test_cycle_semantics_package_model.py -k 'annotation_effects_i3 or annotations315 or r8 or r9 or r10 or r11 or p7 or frozen_dataclass'` → **153 passed, 142 deselected**. Nie uruchomiono pełnego suite ani FULL.
- Wcześniejszy targeted R10 ujawnił 7 oczekiwań dawnego `ast.AST MODEL_PASS`; skorygowano je z powodu braku autorytatywnego faktu o atrybucie importu zewnętrznego. Wcześniejszy subset R8 wykazał dwa dawne `UNKNOWN` dla bezpiecznych `str | int` i `str | None | None`; niezależne próby CPython w nowym teście potwierdziły poprawny import, więc usunięto je z listy „unsupported”. Nie pozostawiono tych starych kontraktów jako sprzecznych testów.
- Testy adnotacji 3.15 sprawdzają zwykłe funkcje, zwykłe klasy i ich class-local import/binding bez wprowadzania zmian w ich ścieżkach. Ukierunkowane R8–R11/P7 obejmują dotychczasowe kontrole warunkowej dataclass. Nie deklaruję globalnego braku regresji poza tym zakresem.

## LIVE PO ZMIANIE / GRANICE

- DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(..., fields=[])`: LIVE revision **1518**, `canonical_state=fresh`, `resync_required=false`, `syntax_errors=0 (fresh)`, `module/graph/topology/lineage=fresh`, ale `cycle_semantics=stale`; globalne `workspace_sync=unverified`. Nie wyciągam wniosku z samego `stale` o zachowaniu CPython/modelu.
- DIRECT_EVIDENCE: `get_module_context(..., compact=true)` dla czterech zmienionych modułów source (`execution.annotation_effects`, `execution.steps`, `execution.definition_checks`, `package_model`) daje `workspace_sync=verified` i revision 1518. Wykonane testy używały kodu source z dysku; nie przeprowadzono restartu backendu ani poświadczenia załadowanych `sys.modules` procesu MCP.
- Nie zmieniono kodu serwera MCP. Świeża semantyka całego LIVE nie jest potwierdzona, ponieważ rodzina `cycle_semantics` jest stale. To ograniczenie raportu, nie wynik testu semantycznego.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/annotation_effects.py` (nowy source)
- `contextor/core/cycle_semantics/execution/definition_checks.py` (source)
- `contextor/core/cycle_semantics/execution/steps.py` (source)
- `contextor/core/cycle_semantics/package_model.py` (source)
- `tests/test_cycle_semantics_annotation_effects_i3.py` (nowy test)
- `tests/test_cycle_semantics_package_model.py` (test)
- `walkthrough.md` (raport; jego własny diff nie jest liczony)

## FULL_DIFFS — SOURCE/TESTS

Poniżej pełne rzeczywiste diffy wszystkich sześciu zmienionych plików source/tests. `walkthrough.md` nie jest produkcyjnym/testowym diffem.

```diff
diff --git a/contextor/core/cycle_semantics/execution/definition_checks.py b/contextor/core/cycle_semantics/execution/definition_checks.py
index 6a4cfff..31c555d 100644
--- a/contextor/core/cycle_semantics/execution/definition_checks.py
+++ b/contextor/core/cycle_semantics/execution/definition_checks.py
@@ -57,66 +57,3 @@ def _restricted_defaultless_dataclass_field_call(
         seen.add(keyword.arg)
 
     return node.func.id
-
-
-def _restricted_dataclass_field_annotation(
-    node: ast.AST,
-) -> bool:
-    if isinstance(node, ast.Name):
-        return (
-            node.id.isidentifier()
-            and not node.id.startswith("__")
-            and node.id != "ast"
-        )
-
-    if type(node) is ast.Attribute:
-        return (
-            type(node.value) is ast.Name
-            and node.value.id == "ast"
-            and node.attr == "AST"
-        )
-
-    if isinstance(node, ast.Constant):
-        return type(node.value) is str
-
-    if isinstance(node, ast.BinOp):
-        if not isinstance(node.op, ast.BitOr):
-            return False
-
-        if (
-            isinstance(node.left, ast.Constant)
-            and type(node.left.value) is type(None)
-            and not isinstance(node.right, ast.BinOp)
-        ):
-            return _restricted_dataclass_field_annotation(
-                node.right
-            )
-
-        if (
-            isinstance(node.right, ast.Constant)
-            and type(node.right.value) is type(None)
-            and not isinstance(node.left, ast.BinOp)
-        ):
-            return _restricted_dataclass_field_annotation(
-                node.left
-            )
-
-        return False
-
-    if isinstance(node, ast.Tuple):
-        return all(
-            _restricted_dataclass_field_annotation(item)
-            for item in node.elts
-        )
-
-    if isinstance(node, ast.Subscript):
-        return (
-            _restricted_dataclass_field_annotation(
-                node.value
-            )
-            and _restricted_dataclass_field_annotation(
-                node.slice
-            )
-        )
-
-    return False
diff --git a/contextor/core/cycle_semantics/execution/steps.py b/contextor/core/cycle_semantics/execution/steps.py
index 1288c81..e46a053 100644
--- a/contextor/core/cycle_semantics/execution/steps.py
+++ b/contextor/core/cycle_semantics/execution/steps.py
@@ -1,5 +1,6 @@
 from __future__ import annotations
 
+import ast
 from dataclasses import dataclass
 
 
@@ -15,7 +16,10 @@ class _Step:
     class_local: bool = False
     source_line: int | None = None
     source_column: int | None = None
-    annotation_builtin_names: tuple[str, ...] = ()
+    annotation_fields: tuple[tuple[str, ast.expr], ...] = ()
+    annotation_class_bindings: tuple[
+        tuple[str, ast.expr | None], ...
+    ] = ()
     definition_id: str | None = None
     defines_init_subclass: bool = False
     base_names: tuple[str, ...] = ()
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 1326eba..7b64146 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -33,7 +33,11 @@ from .execution.expressions import (
 from .execution.definition_checks import (
     _exact_frozen_dataclass_decorator,
     _restricted_defaultless_dataclass_field_call,
-    _restricted_dataclass_field_annotation,
+)
+from .execution.annotation_effects import (
+    _Scalar,
+    _eval,
+    _consume,
 )
 from .execution.class_facts import (
     _ClassFact,
@@ -419,11 +423,6 @@ def _safe_passive_class_definition(
                 return False
 
             if isinstance(body_statement, ast.AnnAssign):
-                if not _restricted_dataclass_field_annotation(
-                    body_statement.annotation
-                ):
-                    return False
-
                 default_value = body_statement.value
                 literal_default = (
                     type(default_value) is ast.Constant
@@ -1062,13 +1061,34 @@ def _compile(
                         binding=stmt.name,
                         source_line=stmt.decorator_list[0].lineno,
                         source_column=stmt.decorator_list[0].col_offset,
-                        annotation_builtin_names=tuple(sorted({
-                            node.id
-                            for field in stmt.body
-                            if isinstance(field, ast.AnnAssign)
-                            for node in ast.walk(field.annotation)
-                            if isinstance(node, ast.Name)
-                        })),
+                        annotation_fields=tuple(
+                            (item.target.id, item.annotation)
+                            for item in stmt.body
+                            if isinstance(item, ast.AnnAssign)
+                        ),
+                        annotation_class_bindings=(
+                            tuple(
+                                (
+                                    item.target.id,
+                                    item.value
+                                    if type(item.value) is ast.Constant
+                                    else None,
+                                )
+                                for item in stmt.body
+                                if (
+                                    isinstance(item, ast.AnnAssign)
+                                    and item.value is not None
+                                )
+                            )
+                            + tuple(
+                                (item.name, None)
+                                for item in stmt.body
+                                if isinstance(
+                                    item,
+                                    (ast.FunctionDef, ast.AsyncFunctionDef),
+                                )
+                            )
+                        ),
                     )
                 )
             else:
@@ -2593,44 +2613,48 @@ def evaluate_package_import_order(
             if (
                 namespaces[module].get("dataclass")
                 != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
-                or any(
-                    (
-                        namespaces[module].get(name)
-                        != "\x00ASSUMED_EXTERNAL:ast"
-                        if name == "ast"
-                        else (
-                            name in namespaces[module]
-                            if name in {
-                                "str",
-                                "int",
-                                "bool",
-                                "float",
-                                "bytes",
-                                "dict",
-                                "list",
-                                "set",
-                                "tuple",
-                            }
-                            else not (
-                                isinstance(
-                                    namespaces[module].get(name),
-                                    _ClassFact,
-                                )
-                                or (
-                                    type(namespaces[module].get(name))
-                                    is str
-                                    and namespaces[module][name].startswith(
-                                        "\x00PASSIVE_CLASS:"
-                                    )
-                                )
-                            )
-                        )
-                    )
-                    for name in step.annotation_builtin_names
-                )
             ):
                 return result("UNKNOWN", module, step.binding)
 
+            class_bindings = {
+                "__module__": _Scalar(module),
+                "__qualname__": _Scalar(step.binding),
+                "__annotations__": None,
+                "__annotate__": None,
+                "__classdict__": None,
+                "__classcell__": None,
+                "__doc__": None,
+            }
+
+            for name, expression in step.annotation_class_bindings:
+                class_bindings[name] = (
+                    _Scalar(expression.value)
+                    if type(expression) is ast.Constant
+                    else None
+                )
+
+            evaluated = []
+
+            for name, expression in step.annotation_fields:
+                value = _eval(
+                    expression,
+                    class_bindings,
+                    namespaces[module],
+                    namespaces,
+                )
+
+                if value is None:
+                    return result("UNKNOWN", module, name)
+
+                evaluated.append((name, value))
+
+            for name, value in evaluated:
+                if not _consume(value, module, namespaces):
+                    return result("UNKNOWN", module, name)
+
+                if not _consume(value, module, namespaces):
+                    return result("UNKNOWN", module, name)
+
             assumed_dataclass_decorations.append(
                 AssumedFrozenDataclassDecoration(
                     module=module,
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 2278282..f8e38eb 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -308,9 +308,7 @@ def test_r8_constant_field_defaults(literal):
         "value: bool = 1 + 2",
         "value: bool = (1, 2)",
         "value: bool = {}",
-        "value: str | int",
         "value: str | UnknownName",
-        "value: str | None | None",
         "value: str + None",
         "value: str | None = factory()",
         "first: bool = False\n    later: int",
@@ -588,7 +586,7 @@ def _r10_assert_rejected(result):
     )
 
 
-def test_r10_parsed_source_input_crosses_class():
+def test_r10_external_ast_attribute_has_no_authoritative_binding():
     source = (
         "@dataclass(frozen=True)\n"
         "class ParsedSourceInput:\n"
@@ -598,47 +596,15 @@ def test_r10_parsed_source_input_crosses_class():
 
     result = _r10_qualified_ast_result(source)
 
-    assert result.outcome == "MODEL_PASS"
+    assert result.outcome == "UNKNOWN"
     assert result.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
     )
-
-    assert len(result.assumed_dataclass_decorations) == 1
-
-    decoration = result.assumed_dataclass_decorations[0]
-
-    assert decoration.class_name == "ParsedSourceInput"
-    assert decoration.decorator == (
-        "dataclasses.dataclass(frozen=True)"
-    )
-
-    events = list(result.events)
-
-    decorated = next(
-        index for index, event in enumerate(events)
-        if event.operation
-        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
-        and event.symbol == "ParsedSourceInput"
-    )
-
-    bound = next(
-        index for index, event in enumerate(events)
-        if event.operation == "DEFINE_PASSIVE_CLASS"
-        and event.symbol == "ParsedSourceInput"
-    )
-
-    imported = next(
-        index for index, event in enumerate(events)
-        if event.operation == "START_IMPORT"
-        and event.target == "pkg.child"
-    )
-
-    assert decorated < bound < imported
-    assert result.reached_unmodeled_import is None
+    _r10_assert_rejected(result)
 
 
-def test_r10_both_source_dataclasses_cross():
+def test_r10_external_ast_attribute_stops_before_both_dataclasses():
     source = (
         "@dataclass(frozen=True)\n"
         "class ParsedSourceInput:\n"
@@ -653,15 +619,7 @@ def test_r10_both_source_dataclasses_cross():
 
     result = _r10_qualified_ast_result(source)
 
-    assert result.outcome == "MODEL_PASS"
-
-    assert tuple(
-        record.class_name
-        for record in result.assumed_dataclass_decorations
-    ) == (
-        "ParsedSourceInput",
-        "SourceSnapshot",
-    )
+    _r10_assert_rejected(result)
 
 
 @pytest.mark.parametrize(
@@ -673,7 +631,7 @@ def test_r10_both_source_dataclasses_cross():
         "list[ast.AST]",
     ],
 )
-def test_r10_restricted_qualified_annotations(annotation):
+def test_r10_external_qualified_annotations_unknown(annotation):
     source = (
         "@dataclass(frozen=True)\n"
         "class ParsedSourceInput:\n"
@@ -682,8 +640,7 @@ def test_r10_restricted_qualified_annotations(annotation):
 
     result = _r10_qualified_ast_result(source)
 
-    assert result.outcome == "MODEL_PASS"
-    assert len(result.assumed_dataclass_decorations) == 1
+    _r10_assert_rejected(result)
 
 
 @pytest.mark.parametrize(
@@ -735,7 +692,7 @@ def test_r10_rejects_unproven_ast_binding(prelude):
     _r10_assert_rejected(result)
 
 
-def test_r10_later_ast_rebinding_does_not_retroactively_fail():
+def test_r10_later_ast_rebinding_cannot_certify_earlier_attribute():
     source = (
         "@dataclass(frozen=True)\n"
         "class ParsedSourceInput:\n"
@@ -747,25 +704,12 @@ def test_r10_later_ast_rebinding_does_not_retroactively_fail():
         after_class="ast = 42\n",
     )
 
-    assert result.outcome == "MODEL_PASS"
-    assert len(result.assumed_dataclass_decorations) == 1
-
-    events = list(result.events)
-
-    bound = next(
-        index for index, event in enumerate(events)
-        if event.operation == "DEFINE_PASSIVE_CLASS"
-        and event.symbol == "ParsedSourceInput"
-    )
-
-    rebound = next(
-        index for index, event in enumerate(events)
-        if event.operation == "BIND"
-        and event.symbol == "ast"
+    _r10_assert_rejected(result)
+    assert not any(
+        event.operation == "BIND" and event.symbol == "ast"
+        for event in result.events
     )
 
-    assert bound < rebound
-
 
 def test_r10_requires_explicit_dataclass_assumption():
     source = (
diff --git a/contextor/core/cycle_semantics/execution/annotation_effects.py b/contextor/core/cycle_semantics/execution/annotation_effects.py
new file mode 100644
index 0000000..9a7cfa9
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/annotation_effects.py
@@ -0,0 +1,383 @@
+from __future__ import annotations
+
+import ast
+import re
+from dataclasses import dataclass
+from typing import Mapping
+
+from .class_facts import _ClassFact, _BUILTIN_TYPE_ID
+
+
+@dataclass(frozen=True)
+class _Scalar:
+    value: object
+
+
+@dataclass(frozen=True)
+class _Type:
+    identity: str
+    generic: bool
+
+
+@dataclass(frozen=True)
+class _Class:
+    identity: str
+
+
+@dataclass(frozen=True)
+class _Module:
+    name: str
+
+
+@dataclass(frozen=True)
+class _Seq:
+    kind: str
+    items: tuple[object, ...]
+
+
+@dataclass(frozen=True)
+class _Alias:
+    origin: _Type
+    args: tuple[object, ...]
+
+
+@dataclass(frozen=True)
+class _TypeUnion:
+    args: tuple[object, ...]
+
+
+_GENERIC = frozenset({
+    "list", "dict", "tuple", "set", "frozenset", "type",
+})
+
+_BUILTINS = {
+    name: _Type("builtins." + name, name in _GENERIC)
+    for name in (
+        "bool", "bytes", "complex", "dict", "float",
+        "frozenset", "int", "list", "object", "set",
+        "str", "tuple", "type",
+    )
+}
+
+# CPython 3.15.2 dataclasses._get_type_from_annotation.
+_STRING_PATH = re.compile(
+    r"^\s*(\w+(?:\s*\.\s*\w+)*)"
+)
+
+_MISSING = object()
+_UNKNOWN = object()
+
+
+def _value(
+    v: object,
+    namespaces: Mapping[str, Mapping[str, object]],
+) -> object | None:
+    if isinstance(v, _ClassFact):
+        if v.origin == "BUILTIN":
+            builtin = _BUILTINS.get(
+                v.identity.removeprefix("builtins.")
+            )
+            if (
+                builtin is not None
+                and builtin.identity == v.identity
+            ):
+                return builtin
+
+        if v.metaclass_identity == _BUILTIN_TYPE_ID:
+            return _Class(v.identity)
+
+        return None
+
+    if type(v) is str:
+        if v in namespaces:
+            return _Module(v)
+
+        if v.startswith("\x00PASSIVE_CLASS:"):
+            return _Class(v)
+
+        return None
+
+    if isinstance(
+        v,
+        (
+            _Scalar, _Type, _Class, _Module,
+            _Seq, _Alias, _TypeUnion,
+        ),
+    ):
+        return v
+
+    return None
+
+
+def _type_operand(v: object) -> bool:
+    return (
+        isinstance(
+            v, (_Type, _Class, _Alias, _TypeUnion)
+        )
+        or (
+            isinstance(v, _Scalar)
+            and v.value is None
+        )
+    )
+
+
+def _eval(
+    expr: ast.expr,
+    class_ns: Mapping[str, object],
+    module_ns: Mapping[str, object],
+    namespaces: Mapping[str, Mapping[str, object]],
+) -> object | None:
+    budget = 256
+
+    def visit(
+        n: ast.expr,
+        depth: int,
+    ) -> object | None:
+        nonlocal budget
+
+        budget -= 1
+        if budget < 0 or depth > 16:
+            return None
+
+        if type(n) is ast.Constant:
+            if type(n.value) not in (
+                type(None), bool, int, float, complex,
+                str, bytes, type(Ellipsis),
+            ):
+                return None
+            return _Scalar(n.value)
+
+        if (
+            type(n) is ast.Name
+            and type(n.ctx) is ast.Load
+        ):
+            if n.id in class_ns:
+                return _value(class_ns[n.id], namespaces)
+
+            if n.id in module_ns:
+                return _value(module_ns[n.id], namespaces)
+
+            return _BUILTINS.get(n.id)
+
+        if (
+            type(n) in (ast.List, ast.Tuple)
+            and type(n.ctx) is ast.Load
+        ):
+            values = []
+
+            for element in n.elts:
+                value = visit(element, depth + 1)
+                if value is None:
+                    return None
+                values.append(value)
+
+            return _Seq(
+                "tuple" if type(n) is ast.Tuple else "list",
+                tuple(values),
+            )
+
+        if (
+            type(n) is ast.Attribute
+            and type(n.ctx) is ast.Load
+        ):
+            receiver = visit(n.value, depth + 1)
+
+            if not isinstance(receiver, _Module):
+                return None
+
+            namespace = namespaces.get(receiver.name)
+
+            if (
+                namespace is None
+                or n.attr not in namespace
+            ):
+                return None
+
+            return _value(namespace[n.attr], namespaces)
+
+        if (
+            type(n) is ast.Subscript
+            and type(n.ctx) is ast.Load
+        ):
+            receiver = visit(n.value, depth + 1)
+            index = visit(n.slice, depth + 1)
+
+            if receiver is None or index is None:
+                return None
+
+            if (
+                isinstance(receiver, _Seq)
+                and isinstance(index, _Scalar)
+                and type(index.value) in (int, bool)
+            ):
+                try:
+                    return receiver.items[index.value]
+                except IndexError:
+                    return None
+
+            if (
+                isinstance(receiver, _Type)
+                and receiver.generic
+            ):
+                args = (
+                    index.items
+                    if (
+                        isinstance(index, _Seq)
+                        and index.kind == "tuple"
+                    )
+                    else (index,)
+                )
+                return _Alias(receiver, tuple(args))
+
+            return None
+
+        if type(n) is ast.BinOp:
+            left = visit(n.left, depth + 1)
+            right = visit(n.right, depth + 1)
+
+            if left is None or right is None:
+                return None
+
+            if (
+                type(n.op) is ast.BitOr
+                and _type_operand(left)
+                and _type_operand(right)
+            ):
+                return _TypeUnion((left, right))
+
+            if (
+                isinstance(left, _Scalar)
+                and isinstance(right, _Scalar)
+                and type(left.value) is int
+                and type(right.value) is int
+            ):
+                if type(n.op) is ast.Add:
+                    value = left.value + right.value
+                elif type(n.op) is ast.Sub:
+                    value = left.value - right.value
+                elif type(n.op) is ast.Mult:
+                    value = left.value * right.value
+                else:
+                    return None
+
+                return (
+                    _Scalar(value)
+                    if value.bit_length() <= 64
+                    else None
+                )
+
+            return None
+
+        if type(n) is ast.UnaryOp:
+            operand = visit(n.operand, depth + 1)
+
+            if (
+                not isinstance(operand, _Scalar)
+                or type(operand.value) is not int
+            ):
+                return None
+
+            if type(n.op) is ast.UAdd:
+                value = +operand.value
+            elif type(n.op) is ast.USub:
+                value = -operand.value
+            else:
+                return None
+
+            return (
+                _Scalar(value)
+                if value.bit_length() <= 64
+                else None
+            )
+
+        if type(n) is ast.IfExp:
+            condition = visit(n.test, depth + 1)
+
+            if (
+                not isinstance(condition, _Scalar)
+                or type(condition.value) is not bool
+            ):
+                return None
+
+            return visit(
+                n.body if condition.value else n.orelse,
+                depth + 1,
+            )
+
+        return None
+
+    return visit(expr, 0)
+
+
+def _text_attribute(
+    receiver: object,
+    name: str,
+    namespaces: Mapping[
+        str, Mapping[str, object]
+    ],
+) -> object:
+    if not isinstance(receiver, _Module):
+        return _UNKNOWN
+
+    namespace = namespaces.get(receiver.name)
+    if namespace is None:
+        return _UNKNOWN
+
+    if name in namespace:
+        value = _value(namespace[name], namespaces)
+        return value if value is not None else _UNKNOWN
+
+    # A missing module attribute can reach module
+    # __getattr__. Intrinsic module attributes also
+    # cannot be inferred from the module dict alone.
+    if "__getattr__" in namespace or name.startswith("__"):
+        return _UNKNOWN
+
+    return _MISSING
+
+
+def _consume(
+    value: object,
+    module: str,
+    namespaces: Mapping[
+        str, Mapping[str, object]
+    ],
+) -> bool:
+    if (
+        not isinstance(value, _Scalar)
+        or type(value.value) is not str
+    ):
+        return isinstance(
+            value,
+            (
+                _Scalar, _Type, _Class, _Module,
+                _Seq, _Alias, _TypeUnion,
+            ),
+        )
+
+    match = _STRING_PATH.match(value.value)
+    if match is None:
+        return True
+
+    receiver: object = _Module(module)
+
+    for component in match.group(1).split("."):
+        receiver = _text_attribute(
+            receiver,
+            component.strip(),
+            namespaces,
+        )
+
+        if receiver is _UNKNOWN:
+            return False
+
+        if receiver is _MISSING:
+            return True
+
+    return isinstance(
+        receiver,
+        (
+            _Scalar, _Type, _Class, _Module,
+            _Seq, _Alias, _TypeUnion,
+        ),
+    )
diff --git a/tests/test_cycle_semantics_annotation_effects_i3.py b/tests/test_cycle_semantics_annotation_effects_i3.py
new file mode 100644
index 0000000..648b5b8
--- /dev/null
+++ b/tests/test_cycle_semantics_annotation_effects_i3.py
@@ -0,0 +1,278 @@
+"""CPython 3.15 annotation consumption versus the conditional package model."""
+
+import ast
+import os
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+pytestmark = pytest.mark.skipif(
+    sys.version_info[:2] != (3, 15),
+    reason="CPython 3.15 annotation consumption contract",
+)
+
+
+def _model(source, **other_sources):
+    trees = {"pkg.__init__": ast.parse(source)}
+    trees.update({name: ast.parse(body) for name, body in other_sources.items()})
+    original = {name: ast.dump(tree) for name, tree in trees.items()}
+    options = dict(
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    first = evaluate_package_import_order(trees, "pkg", **options)
+    second = evaluate_package_import_order(trees, "pkg", **options)
+    assert first == second
+    assert original == {name: ast.dump(tree) for name, tree in trees.items()}
+    assert first.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    return first
+
+
+def _runtime(tmp_path, source, *, side=None, other=None, inspect=False):
+    package = tmp_path / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    if side is not None:
+        (tmp_path / "side.py").write_text(side, encoding="utf-8")
+    if other is not None:
+        (package / "other.py").write_text(other, encoding="utf-8")
+    env = os.environ.copy()
+    env["PYTHONPATH"] = str(tmp_path)
+    env["PYTHONDONTWRITEBYTECODE"] = "1"
+    code = (
+        "try:\n"
+        " import pkg\n"
+        + (
+            " print('FIELD_TYPE', repr(pkg.C.__dataclass_fields__['x'].type), flush=True)\n"
+            " print('T_BOUND', 'T' in vars(pkg.C), flush=True)\n"
+            if inspect else ""
+        )
+        +
+        " print('RESULT', 'OK', flush=True)\n"
+        "except BaseException as error:\n"
+        " print('RESULT', type(error).__name__, str(error), flush=True)\n"
+    )
+    completed = subprocess.run(
+        [sys.executable, "-u", "-c", code],
+        cwd=tmp_path,
+        env=env,
+        capture_output=True,
+        text=True,
+        timeout=15,
+        check=False,
+    )
+    assert completed.returncode == 0, completed.stderr
+    return completed.stdout.splitlines()
+
+
+@pytest.mark.parametrize("annotation", [
+    "list[int]", "list[str] | None", "None | list[str]",
+    "int | None", "str | None", "str | int", "str | None | None",
+    "[T][0]", "Alias", "\"str\"",
+    "1 if True else T[int]", "\"T[int]\"",
+])
+def test_passive_annotations_remain_conditional_pass(tmp_path, annotation):
+    source = (
+        "from dataclasses import dataclass\n"
+        "class T:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        raise SystemExit('getitem-effect')\n"
+        "Alias = T\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        f"    x: {annotation}\n"
+    )
+    result = _model(source)
+    assert result.outcome == "MODEL_PASS", annotation
+    assert len(result.assumed_dataclass_decorations) == 1
+    assert _runtime(tmp_path, source)[-1] == "RESULT OK"
+
+
+def test_indexed_module_attribute_with_known_binding(tmp_path):
+    source = (
+        "import pkg.other\n"
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: pkg.other.T\n"
+    )
+    other = "class T: pass\n"
+    result = _model(source, **{"pkg.other": other})
+    assert result.outcome == "MODEL_PASS"
+    assert _runtime(tmp_path, source, other=other)[-1] == "RESULT OK"
+
+
+@pytest.mark.parametrize("prelude,annotation,runtime_result", [
+    (
+        "class T:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        raise SystemExit('getitem-effect')\n",
+        "T[int]", "RESULT SystemExit getitem-effect",
+    ),
+    (
+        "class Meta(type):\n"
+        "    def __or__(cls, other):\n"
+        "        raise SystemExit('or-effect')\n"
+        "class T(metaclass=Meta): pass\n",
+        "T | str", "RESULT SystemExit or-effect",
+    ),
+    (
+        "class Meta(type):\n"
+        "    @property\n"
+        "    def x(cls):\n"
+        "        raise SystemExit('descriptor-effect')\n"
+        "class Holder(metaclass=Meta): pass\n",
+        "Holder.x", "RESULT SystemExit descriptor-effect",
+    ),
+    ("import ast\n", "ast.AST", "RESULT OK"),
+    ("str = 42\n", "str", "RESULT OK"),
+    ("", "Missing", "RESULT OK"),
+])
+def test_unproved_operations_stop_before_decoration(
+    tmp_path, prelude, annotation, runtime_result,
+):
+    source = (
+        prelude
+        + "from dataclasses import dataclass\n"
+        + "@dataclass(frozen=True)\n"
+        + "class C:\n"
+        + f"    x: {annotation}\n"
+    )
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert all(
+        event.operation != "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        for event in result.events
+    )
+    assert _runtime(tmp_path, source)[-1] == runtime_result
+
+
+def test_textual_attribute_can_invoke_external_getattr(tmp_path):
+    source = (
+        "import side\n"
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: \"side.missing\"\n"
+    )
+    side = (
+        "def __getattr__(name):\n"
+        "    print('SIDE_GETATTR', name, flush=True)\n"
+        "    raise SystemExit('annotation-effect')\n"
+    )
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert _runtime(tmp_path, source, side=side) == [
+        "SIDE_GETATTR missing", "RESULT SystemExit annotation-effect",
+    ]
+
+
+def test_class_local_precedes_module_and_missing_field_does_not_bind(tmp_path):
+    source = (
+        "T = 3\n"
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    T: int = 1\n"
+        "    x: T = 2\n"
+    )
+    assert _model(source).outcome == "MODEL_PASS"
+    runtime = _runtime(tmp_path, source, inspect=True)
+    assert "FIELD_TYPE 1" in runtime
+    assert "T_BOUND True" in runtime
+    assert runtime[-1] == "RESULT OK"
+    absent = (
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    T: int\n"
+        "    x: T\n"
+    )
+    assert _model(absent).outcome == "UNKNOWN"
+    absent_runtime = _runtime(tmp_path / "absent", absent, inspect=True)
+    assert "T_BOUND False" in absent_runtime
+
+
+def test_module_alias_rebinding_is_read_at_decoration(tmp_path):
+    source = (
+        "from dataclasses import dataclass\n"
+        "class Old: pass\n"
+        "class New: pass\n"
+        "T = Old\n"
+        "T = New\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: T\n"
+        "T = Old\n"
+    )
+    assert _model(source).outcome == "MODEL_PASS"
+    lines = _runtime(tmp_path, source, inspect=True)
+    assert "FIELD_TYPE <class 'pkg.New'>" in lines
+    assert lines[-1] == "RESULT OK"
+
+
+def test_class_name_is_bound_only_after_decorator(tmp_path):
+    source = (
+        "from dataclasses import dataclass\n"
+        "def decorate(cls):\n"
+        "    print('BOUND_BEFORE', 'C' in globals(), flush=True)\n"
+        "    return dataclass(frozen=True)(cls)\n"
+        "@decorate\n"
+        "class C:\n"
+        "    x: int\n"
+    )
+    assert _runtime(tmp_path, source) == ["BOUND_BEFORE False", "RESULT OK"]
+
+
+def test_unknown_class_local_and_prior_events_survive(tmp_path):
+    source = (
+        "from dataclasses import dataclass, field\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    T: int = field()\n"
+        "    x: T\n"
+    )
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert any(event.operation == "ASSUMED_EXTERNAL_IMPORT" for event in result.events)
+    _runtime(tmp_path, source)
+
+
+def test_annotation_phase_precedes_text_consumption(tmp_path):
+    source = (
+        "import side\n"
+        "from dataclasses import dataclass\n"
+        "class T:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        print('GETITEM', flush=True)\n"
+        "        return int\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    a: \"side.missing\"\n"
+        "    b: T[int]\n"
+    )
+    side = (
+        "def __getattr__(name):\n"
+        "    print('SIDE_GETATTR', name, flush=True)\n"
+        "    raise SystemExit('annotation-effect')\n"
+    )
+    lines = _runtime(tmp_path, source, side=side)
+    assert "SIDE_GETATTR missing" in lines, lines
+    assert lines.index("GETITEM") < lines.index("SIDE_GETATTR missing")
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
```
