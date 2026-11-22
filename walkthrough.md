# P10-R4-A2-I2 — tożsamość instancji definicji klasy

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])` przed edycją: LIVE revision **1524**, `canonical_state=fresh`. `get_module_context` dla `package_model.py`, `execution/annotation_effects.py`, `execution/steps.py`: każdy `workspace_sync=verified`, revision 1524. `cycle_semantics=stale` jako odrębna rodzina; nie przesądza o obecnym zachowaniu ścieżki.
- `get_symbol_lineage(mode="preview")` rozwiązał `_compile` i `evaluate_package_import_order` w `package_model.py` przy revision 1524. `get_file_edit_context(mode="minimal")`: właściciel `package_model.py`, 49 bezpośrednich i 396 tranzytywnych modułów konsumenckich; wynik jest statycznym blast radius, nie dowodem wykonania.
- Literalne anchory przed zmianą: `package_model.py:918-932` kontrola współrzędnych tylko w gałęzi zwykłej klasy, `:1057-1108` kroki definicji, `:2612-2675` wykonanie warunkowej dataclass. `execution/steps.py:definition_id` już zawiera pole `str | None`. `rg -F 'PASSIVE_CLASS:' . -g '*.py' -g '!issues.md'`: dwa użycia w Pythonie, konstrukcja w `package_model.py` i rozpoznanie prefiksu w `execution/annotation_effects.py`. Nie czytano ani nie zmieniano `issues.md`.
- `git status --short` przed edycją pusty; nie było lokalnego diffa source/tests. Anchory zgodne z aktualnym źródłem. Nie wykonywano restartu, FULL, staging, commit ani push.

## REPRODUKCJA PRZED ZMIANĄ

- Izolowany CPython **3.15.2** z rzeczywistym `dataclasses.dataclass(frozen=True)` dla `T; Old = T; T; C.x: Old | T`: `Old is T` = **False**, `repr(Field.type) = pkg.T | pkg.T`, `typing.get_args` zawiera **2** człony, pierwszy jest `Old`, drugi nim nie jest.
- CODE_PATH_PROVED: dotychczasowy `evaluate_package_import_order` dla tego źródła zwracał `MODEL_PASS`, trzy założone dekoracje i eventy obydwu definicji T. Stary sentinel obu wiązań miał tę samą wartość `\x00PASSIVE_CLASS:pkg:T`; `_eval(Old | T)` zwracał tylko `_Class(identity='\x00PASSIVE_CLASS:pkg:T')`. To osiągalna kolizja tożsamości symbolicznej mimo odrębnych klas CPython.

## IMPLEMENTACJA I REPRODUKCJA PO ZMIANIE

- Zmiana ograniczona do `package_model.py`: istniejąca kontrola `lineno` i `col_offset` została przeniesiona po `_safe_passive_class_definition`, przed rozgałęzienie warunkowe. Jeden `definition_id=f"{logical}:{stmt.lineno}:{stmt.col_offset}"` jest przekazywany do wszystkich trzech kroków definicji klasy. `DEFINE_CONDITIONAL_FROZEN_DATACLASS` wymaga niepustego ID przed publikacją dekoracji i zapisuje `\x00PASSIVE_CLASS:` + `step.definition_id`. Prefiks, anchory eventów dekoratora i klasy, kolejność eventów, założenia i evidence_scope pozostają takie jak przed zmianą. Nie zmieniono operatorów, `_proven_key`, `_BUILTINS`, `_GENERIC`, `annotation_effects.py` ani `steps.py`.
- Po zmianie kroki dwóch definicji T mają `definition_id='pkg:3:0'` i `'pkg:7:0'`. Ich `source_line` pozostaje linią dekoratora, odpowiednio 2 i 6. `_eval(Old | T)` zwraca `_TypeUnion` z `_Class('\x00PASSIVE_CLASS:pkg:3:0')` i `_Class('\x00PASSIVE_CLASS:pkg:7:0')` w tej kolejności. Pełny model pozostaje `MODEL_PASS` z trzema założonymi dekoracjami. To potwierdza usunięcie kolizji wartości symbolicznej; sam `MODEL_PASS` nie służył za dowód tożsamości.

## MACIERZ CPYTHON / MODEL A–G

Każda próba CPython odbywa się w osobnym podprocesie `.venv\\Scripts\\python.exe` (zweryfikowany CPython 3.15.2) z odrębnym tymczasowym `pkg`, a model czyta wyłącznie AST. Warunkowy `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF` we wszystkich osiągniętych przypadkach; wyniki modelu są warunkowe, nie atestują runtime builtins ani importów.

| Przypadek | CPython | Model i tożsamość symboliczna |
|---|---|---|
| A. Dwa T, alias Old, `Old | T` | `Old is T=False`, 2 człony, pierwszy Old | `MODEL_PASS`; dwa ID `pkg:3:0`, `pkg:7:0`; `_TypeUnion` z 2 `_Class` |
| B. `Old | Old` po ponownej definicji T | wynik jest pojedynczą klasą Old, `get_args=()` | `MODEL_PASS`; `_eval` zwraca pojedynczą `_Class` pierwszej definicji |
| C. T i U w jednym module | `Old is T=True`, `Old | U` ma 2 człony | `MODEL_PASS`; różne ID według pozycji definicji, 2 człony |
| D. T w `pkg.a` i `pkg.b` | `Old is T=False`, 2 człony | `MODEL_PASS`; różne ID `pkg.a:3:0`, `pkg.b:3:0`, 2 człony |
| E. Alias pierwszej T, późniejsze `T=1` | `Old is T=False`, `Old | Old` jedna klasa | `MODEL_PASS`; wiązanie Old zachowuje pierwsze ID |
| F. Przesunięcie definicji o linię | CPython nadal 2 odrębne obiekty i 2 człony | `MODEL_PASS`; obydwa ID przesunięte o linię |
| G. Zwykłe klasy | zwykłe definicje nadal tworzą odrębne obiekty Pythona | `_compile` nadal daje `pkg:1:0`, `pkg:2:0` w `DEFINE_PASSIVE_CLASS` |

- `test_cycle_semantics_conditional_class_identity_i2.py` sprawdza AST bez mutacji, deterministyczność pełnego modelu, dokładne `definition_id` z kroków, liczbę i wartości członów `_eval`, CPython `is` i `typing.get_args`. Dla G test dotyczy zachowania ID w kompilatorze; nie używa podprocesu CPython, ponieważ ID jest wyłącznie faktem modelu.

## TESTY

- `.venv\\Scripts\\python.exe -m pytest -q tests/test_cycle_semantics_conditional_class_identity_i2.py`: **5 passed**.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_cycle_semantics_conditional_class_identity_i2.py tests/test_cycle_semantics_annotation_union_i1.py tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_class_decorator_import_admission.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_baseline.py`: **207 passed**.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k 'r8 or r10 or frozen_dataclass'`: **52 passed, 189 deselected**. Bez pełnego pytest i FULL.

## POST-CHANGE LIVE

- `get_live_events(after_revision=1524)`: ciągły dziennik, `resync_required=false`, `desktop_watcher UPDATED` revision **1525** dla `package_model.py`, revisions **1526–1527** dla nowego testu.
- `get_project_architecture(fields=[])`: LIVE **1527**, `canonical_state=fresh`. `get_module_context`: `package_model.py`, `execution/annotation_effects.py`, `execution/steps.py` i nowy test — `workspace_sync=verified`, revision 1527. `get_file_edit_context(mode="minimal")`: oba zmienione pliki mają `syntax_diagnostics=checked_and_none`, `availability=fresh`, `errors=[]`.

## POBOCZNA OBSERWACJA / GRANICE

- CODE_PATH_PROVED: w istniejącej ścieżce `DEFINE_CONDITIONAL_FROZEN_DATACLASS` `package_model.py` ma dwa kolejno identyczne wywołania `_consume(value, module, namespaces)` przed publikacją (`:2652–2658` po zmianie). To zastany duplikat, niezwiązany z identyfikatorem; nie zmieniano go w tym zadaniu. Nie wykazano na tej podstawie FALSE_PASS ani efektu ubocznego.
- `definition_id` jest identyfikatorem lokalizacji źródłowej przyjętym przez istniejący model. Dowód obejmuje odrębne definicje AST z odrębnymi lokalizacjami oraz jawne założenia warunkowe; nie certyfikuje dowolnej dynamicznej ewaluacji Pythona.
- Werdykt: **PASS dla określonego kontraktu A–G**. Nie znaleziono SOURCE_DRIFT, nowego FALSE_PASS ani sprzeczności z CPython w zbadanych próbach.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_conditional_class_identity_i2.py`

## FULL_DIFFS

Poniżej pełne rzeczywiste diffy dwóch zmienionych plików source/tests. `walkthrough.md` jako raport nie jest liczony jako plik source/test.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 7b64146..6aa45d6 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -894,6 +894,18 @@ def _compile(
             ):
                 return None
 
+            if (
+                type(stmt.lineno) is not int
+                or stmt.lineno < 1
+                or type(stmt.col_offset) is not int
+                or stmt.col_offset < 0
+            ):
+                return None
+
+            definition_id = (
+                f"{logical}:{stmt.lineno}:{stmt.col_offset}"
+            )
+
             ordinary_named_decorators = (
                 bool(stmt.decorator_list)
                 and not conditional_dataclass
@@ -916,17 +928,6 @@ def _compile(
                     return None
 
             if not conditional_dataclass:
-                if (
-                    type(stmt.lineno) is not int
-                    or stmt.lineno < 1
-                    or type(stmt.col_offset) is not int
-                    or stmt.col_offset < 0
-                ):
-                    return None
-
-                definition_id = (
-                    f"{logical}:{stmt.lineno}:{stmt.col_offset}"
-                )
                 if ordinary_named_decorators:
                     steps.append(
                         _Step(
@@ -1059,6 +1060,7 @@ def _compile(
                     _Step(
                         "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
                         binding=stmt.name,
+                        definition_id=definition_id,
                         source_line=stmt.decorator_list[0].lineno,
                         source_column=stmt.decorator_list[0].col_offset,
                         annotation_fields=tuple(
@@ -1102,9 +1104,7 @@ def _compile(
                         binding=stmt.name,
                         source_line=stmt.lineno,
                         source_column=stmt.col_offset,
-                        definition_id=(
-                            f"{logical}:{stmt.lineno}:{stmt.col_offset}"
-                        ),
+                        definition_id=definition_id,
                         defines_init_subclass=has_init_subclass,
                         passive_metaclass_body=passive_metaclass_body,
                     )
@@ -2655,6 +2655,9 @@ def evaluate_package_import_order(
                 if not _consume(value, module, namespaces):
                     return result("UNKNOWN", module, name)
 
+            if not step.definition_id:
+                return result("UNKNOWN", module, step.binding)
+
             assumed_dataclass_decorations.append(
                 AssumedFrozenDataclassDecoration(
                     module=module,
@@ -2666,9 +2669,7 @@ def evaluate_package_import_order(
             )
             namespaces[module][step.binding] = (
                 "\x00PASSIVE_CLASS:"
-                + module
-                + ":"
-                + step.binding
+                + step.definition_id
             )
             events.append(
                 PackageModelEvent(
diff --git a/tests/test_cycle_semantics_conditional_class_identity_i2.py b/tests/test_cycle_semantics_conditional_class_identity_i2.py
new file mode 100644
index 0000000..54ab964
--- /dev/null
+++ b/tests/test_cycle_semantics_conditional_class_identity_i2.py
@@ -0,0 +1,192 @@
+"""Definition identity of conditional frozen dataclasses on CPython 3.15."""
+
+import ast
+import os
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.execution.annotation_effects import (
+    _Class,
+    _TypeUnion,
+    _eval,
+)
+from contextor.core.cycle_semantics.package_model import (
+    _compile,
+    evaluate_package_import_order,
+)
+
+
+pytestmark = pytest.mark.skipif(
+    sys.version_info[:2] != (3, 15),
+    reason="CPython 3.15 deferred frozen dataclass contract",
+)
+
+
+DECORATOR = "from dataclasses import dataclass\n"
+T = "@dataclass(frozen=True)\nclass T:\n    x: int\n"
+C = "@dataclass(frozen=True)\nclass C:\n    x: Old | T\n"
+
+
+def _compile_steps(source, logical="pkg"):
+    tree = ast.parse(source)
+    before = ast.dump(tree)
+    steps = _compile(
+        tree, logical, True,
+        annotation_semantics="DEFERRED",
+        assume_frozen_dataclass=True,
+    )
+    assert steps is not None
+    assert ast.dump(tree) == before
+    return steps
+
+
+def _definitions(source, name="T", logical="pkg"):
+    return [
+        step for step in _compile_steps(source, logical)
+        if step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS"
+        and step.binding == name
+    ]
+
+
+def _symbolic(expression, bindings):
+    namespace = {
+        name: "\x00PASSIVE_CLASS:" + identity
+        for name, identity in bindings.items()
+    }
+    return _eval(
+        ast.parse(expression, mode="eval").body,
+        {}, namespace, {"pkg": namespace},
+    )
+
+
+def _model(sources):
+    trees = {name: ast.parse(source) for name, source in sources.items()}
+    before = {name: ast.dump(tree) for name, tree in trees.items()}
+    options = dict(
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    first = evaluate_package_import_order(trees, "pkg", **options)
+    second = evaluate_package_import_order(trees, "pkg", **options)
+    assert first == second
+    assert before == {name: ast.dump(tree) for name, tree in trees.items()}
+    assert first.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    return first
+
+
+def _cpython(tmp_path, sources):
+    package = tmp_path / "pkg"
+    package.mkdir(parents=True)
+    for logical, source in sources.items():
+        name = "__init__.py" if logical == "pkg.__init__" else logical.removeprefix("pkg.") + ".py"
+        (package / name).write_text(source, encoding="utf-8")
+    env = os.environ.copy()
+    env["PYTHONPATH"] = str(tmp_path)
+    env["PYTHONDONTWRITEBYTECODE"] = "1"
+    code = (
+        "import pkg, typing\n"
+        "print('SAME', pkg.Old is pkg.T)\n"
+        "value = pkg.C.__dataclass_fields__['x'].type\n"
+        "print('ARGS', len(typing.get_args(value)))\n"
+        "print('MEMBERS', tuple(arg is pkg.Old for arg in typing.get_args(value)))\n"
+        "print('FIELD', repr(value))\n"
+    )
+    process = subprocess.run(
+        [sys.executable, "-u", "-c", code],
+        cwd=tmp_path, env=env,
+        capture_output=True, text=True,
+        timeout=15, check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    return process.stdout.splitlines()
+
+
+def test_redefinition_alias_and_union_have_two_identities(tmp_path):
+    source = DECORATOR + T + "Old = T\n" + T + C
+    definitions = _definitions(source)
+    assert len(definitions) == 2
+    first, second = (step.definition_id for step in definitions)
+    assert (first, second) == ("pkg:3:0", "pkg:7:0")
+    assert all(step.source_line == int(step.definition_id.split(":")[1]) - 1 for step in definitions)
+    value = _symbolic("Old | T", {"Old": first, "T": second})
+    assert isinstance(value, _TypeUnion)
+    assert value.args == (
+        _Class("\x00PASSIVE_CLASS:" + first),
+        _Class("\x00PASSIVE_CLASS:" + second),
+    )
+    result = _model({"pkg.__init__": source})
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 3
+    assert _cpython(tmp_path, {"pkg.__init__": source})[:3] == [
+        "SAME False", "ARGS 2", "MEMBERS (True, False)",
+    ]
+
+
+def test_same_alias_deduplicates_and_rebinding_preserves_old(tmp_path):
+    source = DECORATOR + T + "Old = T\n" + T + "T = 1\n" + C.replace("Old | T", "Old | Old")
+    first, second = (step.definition_id for step in _definitions(source))
+    assert first != second
+    assert _symbolic("Old | Old", {"Old": first}) == _Class(
+        "\x00PASSIVE_CLASS:" + first
+    )
+    assert _model({"pkg.__init__": source}).outcome == "MODEL_PASS"
+    runtime = _cpython(tmp_path, {"pkg.__init__": source})
+    assert runtime[:3] == ["SAME False", "ARGS 0", "MEMBERS ()"]
+
+
+def test_two_names_and_two_modules_keep_distinct_identity(tmp_path):
+    local = DECORATOR + T + "Old = T\n" + T.replace("class T:", "class U:") + C.replace("Old | T", "Old | U")
+    t_id = _definitions(local)[0].definition_id
+    u_id = _definitions(local, "U")[0].definition_id
+    assert t_id != u_id
+    value = _symbolic("Old | U", {"Old": t_id, "U": u_id})
+    assert isinstance(value, _TypeUnion) and len(value.args) == 2
+    assert _model({"pkg.__init__": local}).outcome == "MODEL_PASS"
+    assert _cpython(tmp_path / "local", {"pkg.__init__": local})[:3] == [
+        "SAME True", "ARGS 2", "MEMBERS (True, False)",
+    ]
+
+    sources = {
+        "pkg.__init__": DECORATOR + "from .a import T as Old\nfrom .b import T\n" + C,
+        "pkg.a": DECORATOR + T,
+        "pkg.b": DECORATOR + T,
+    }
+    a_id = _definitions(sources["pkg.a"], logical="pkg.a")[0].definition_id
+    b_id = _definitions(sources["pkg.b"], logical="pkg.b")[0].definition_id
+    assert a_id != b_id
+    assert isinstance(_symbolic("Old | T", {"Old": a_id, "T": b_id}), _TypeUnion)
+    assert _model(sources).outcome == "MODEL_PASS"
+    assert _cpython(tmp_path, sources)[:3] == [
+        "SAME False", "ARGS 2", "MEMBERS (True, False)",
+    ]
+
+
+def test_shifted_definition_changes_id_not_runtime_semantics(tmp_path):
+    source = DECORATOR + T + "Old = T\n" + T + C
+    shifted = DECORATOR + "\n" + T + "Old = T\n" + T + C
+    original = [step.definition_id for step in _definitions(source)]
+    moved = [step.definition_id for step in _definitions(shifted)]
+    assert original != moved
+    assert [int(value.split(":")[1]) for value in moved] == [
+        int(value.split(":")[1]) + 1 for value in original
+    ]
+    assert _model({"pkg.__init__": shifted}).outcome == "MODEL_PASS"
+    assert _cpython(tmp_path, {"pkg.__init__": shifted})[:3] == [
+        "SAME False", "ARGS 2", "MEMBERS (True, False)",
+    ]
+
+
+def test_ordinary_class_definition_id_unchanged():
+    source = "class T: pass\nclass T: pass\n"
+    steps = _compile_steps(source)
+    defined = [step for step in steps if step.op == "DEFINE_PASSIVE_CLASS"]
+    assert [step.definition_id for step in defined] == [
+        "pkg:1:0", "pkg:2:0",
+    ]
```
