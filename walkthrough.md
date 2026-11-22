# P10-R4-A2-I1 — semantyczny dispatch i konstrukcja unii

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])` przed zmianą: canonical LIVE revision 1521, `canonical_state=fresh`, `resync_required=false`; per-file `get_module_context` dla `execution.annotation_effects` pokazał `workspace_sync=verified`. `get_symbol_lineage(A9503/1, mode="preview")` rozwiązał `_eval`, revision 1521, `metadata_consistent=true`.
- HEAD przed zmianą: `6aa63381abbe5386a0c52afdf54828bcef3e2853`. `git status --short`: przed zmianą tylko `M walkthrough.md`; nie było lokalnej zmiany w pliku produkcyjnym. Anchory: `annotation_effects.py:12-45` klas symbolicznych, `:112` `_type_operand`, `:124` `_eval`, `:246` konstrukcja `_TypeUnion((left, right))`. SOURCE_DRIFT nie wystąpił.
- CONTRACT_PROVED: CPython 3.15.2 `C:\Python315\python.exe` potwierdził `None | None` jako TypeError oraz normalizację `int | int`, `list[int] | list[int]`, `list[int | str] | list[str | int]`, `list[[]] | list[[]]`. Nie czytano ani nie zmieniano `issues.md`.

## ZAKRES ZMIANY

- CODE_PATH_PROVED: `execution/annotation_effects.py` — wspólna symboliczna reprezentacja slotu `_BuiltinUnionOr` wyłącznie dla `_Type`, `_Class`, `_Alias`, `_TypeUnion`; `_Scalar`, `_Module`, `_Seq` nie dziedziczą po niej. `_unionable` odróżnia dopuszczalny operand `None` od dostępności slotu. `_proven_key` tworzy klucz dla bezpiecznie rozpoznanych wartości, wykluczając `_Module`. `_construct_union` rozwija zagnieżdżone unie, normalizuje `None` do `builtins.NoneType`, zachowuje pierwsze wystąpienie i usuwa duplikaty. `_eval` wywołuje tę funkcję tylko dla BitOr. Pozostałe gałęzie nie zostały zmienione.
- Nowy `tests/test_cycle_semantics_annotation_union_i1.py` porównuje izolowany import CPython 3.15.2 z `_eval` i warunkowym `evaluate_package_import_order`. Model uruchamiany jest na AST, bez wykonywania analizowanego pakietu. `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`; nie jest to dowód runtime safety bez założeń. Testy sprawdzają deterministyczność oraz brak mutacji AST.

## CPYTHON / MODEL

Każdy wiersz dodatni: CPython `Field.type` jak poniżej, import OK; `_eval` zwraca oczekiwaną strukturę, model `MODEL_PASS` z jedną `ASSUMED_FROZEN_DATACLASS_DECORATION`. Każdy przypadek używa osobnego podprocesu CPython 3.15.2 oraz osobnego tymczasowego `pkg`.

| Adnotacja | CPython `repr(Field.type)` | Kluczowy wynik symboliczny |
|---|---|---|
| `int | int` | `<class 'int'>` | jeden `_Type(builtins.int)` |
| `list[int] | list[int]` | `list[int]` | jeden `_Alias` |
| `int | None` | `int | None` | `_TypeUnion(int, NoneType)` |
| `None | int` | `None | int` | `_TypeUnion(NoneType, int)` |
| `int | None | None` | `int | None` | dwa człony |
| `int | str | int` | `int | str` | dwa człony |
| `(int | str) | (str | None)` | `int | str | None` | trzy człony, pierwsza kolejność |
| `list[int] | list[str]` | `list[int] | list[str]` | dwie różne `_Alias` |
| `list[[]] | int` | `list[[]] | int` | `_Alias`, `_Type` |
| `list[[]] | list[[]]` | `list[[]]` | jedna `_Alias` |
| `list[int | str] | list[str | int]` | `list[int | str]` | jeden `_Alias`, równość zagnieżdżonej unii niezależna od kolejności |

- Kontrprzykłady `None | None`, `(None | None) | int`, `None | (None | None)`: izolowany CPython kończy import z `TypeError unsupported operand type(s) for |: 'NoneType' and 'NoneType'`; `_eval=None`, model `UNKNOWN`, brak `ASSUMED_FROZEN_DATACLASS_DECORATION`.
- Test `_proven_key` potwierdza identyczny klucz dla unii z odwróconą kolejnością, a `_construct_union` jest idempotentne dla powtórzonego członu. Test porządku wykonania: CPython przy `L[int] | R[int]` drukuje `LEFT`, `RIGHT`, następnie `FIELD int | str`; model `UNKNOWN` bez wykonania metod. Ścieżka `_eval` odwiedza `n.left` przed `n.right` (`annotation_effects.py`, gałąź `ast.BinOp`).
- Dynamiczne granice: własne `__class_getitem__` powoduje wyłącznie efekt `USER_GETITEM` w izolowanym CPython; niestandardowe `Meta.__or__` powoduje `USER_OR`; przesłonięte modułowo `list` i zewnętrzne `from builtins import list as Alias` są `UNKNOWN` w modelu bez założonej dekoracji. `NOT_REACHED`: niestandardowa metaklasa może być odrzucona już przy definicji `T`; taki test nie dowodzi samej gałęzi BitOr.

## TESTY

- `C:\Python315\python.exe -m pytest ...` nie uruchomił testów: interpreter nie ma zainstalowanego pytest (`No module named pytest`). Bez instalacji użyto repozytoryjnego `.venv\Scripts\python.exe`, zweryfikowanego jako CPython **3.15.2**, pytest 9.1.1.
- `.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_annotation_union_i1.py tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_package_model.py -k 'union or annotation_effects or r8 or r10 or frozen_dataclass'`: **97 passed, 189 deselected**.
- `.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_annotation_union_i1.py`: **45 passed**. Po doprecyzowaniu asercji rzeczywistego `Field.type`: `.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_annotation_union_i1.py`: **20 passed**.
- Nie uruchamiano pełnego pytest ani FULL. `git diff --check` bez błędów; ostrzeżenie Git o planowanej konwersji LF/CRLF nie jest błędem składni.

## POST-CHANGE LIVE

- DIRECT_EVIDENCE: `get_live_events(after_revision=1521)` zwrócił ciągłe eventy `desktop_watcher UPDATED`: revision 1522 dla `annotation_effects.py`, revision 1523 i 1524 dla nowego testu. Brak `resync_required`.
- `get_module_context` przy revision **1524**: oba zmienione moduły `canonical_state=fresh`, `workspace_sync=verified`. `get_file_edit_context(mode="minimal")`: dla obu plików `syntax_diagnostics.status=checked_and_none`, `availability=fresh`, `errors=[]`. `cycle_semantics` jako osobna rodzina pozostaje `stale`; nie jest dowodem o wykonaniu tych testów.

## GRANICE I WERDYKT

- Klasy symboliczne są faktami modelu, nie obiektami analizowanego procesu. Warunkowy `MODEL_PASS` zakłada konwencjonalne builtins i pasywne importy/dekorację. Nie udowodniono stanu `__builtins__` docelowego procesu, hooków importu ani zachowania poza rozpoznawanym fragmentem Pythona.
- Dla zbadanych próbek nie wykryto nowego FALSE_PASS ani błędnej normalizacji. **PASS w zakresie literalnej zmiany i ukierunkowanych prób**; nie stanowi certyfikacji dowolnego kodu Pythona.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/annotation_effects.py`
- `tests/test_cycle_semantics_annotation_union_i1.py`

## FULL_DIFFS

Pełne rzeczywiste diffy dwóch zmienionych plików source/tests znajdują się poniżej. `walkthrough.md` jest wyłącznie raportem i nie jest liczony jako zmiana source/tests.

```diff
diff --git a/contextor/core/cycle_semantics/execution/annotation_effects.py b/contextor/core/cycle_semantics/execution/annotation_effects.py
index 9a7cfa9..eabe4d2 100644
--- a/contextor/core/cycle_semantics/execution/annotation_effects.py
+++ b/contextor/core/cycle_semantics/execution/annotation_effects.py
@@ -8,19 +8,25 @@ from typing import Mapping
 from .class_facts import _ClassFact, _BUILTIN_TYPE_ID
 
 
+class _BuiltinUnionOr:
+    """Proven CPython built-in union number slot."""
+
+    __slots__ = ()
+
+
 @dataclass(frozen=True)
 class _Scalar:
     value: object
 
 
 @dataclass(frozen=True)
-class _Type:
+class _Type(_BuiltinUnionOr):
     identity: str
     generic: bool
 
 
 @dataclass(frozen=True)
-class _Class:
+class _Class(_BuiltinUnionOr):
     identity: str
 
 
@@ -36,13 +42,13 @@ class _Seq:
 
 
 @dataclass(frozen=True)
-class _Alias:
+class _Alias(_BuiltinUnionOr):
     origin: _Type
     args: tuple[object, ...]
 
 
 @dataclass(frozen=True)
-class _TypeUnion:
+class _TypeUnion(_BuiltinUnionOr):
     args: tuple[object, ...]
 
 
@@ -109,18 +115,123 @@ def _value(
     return None
 
 
-def _type_operand(v: object) -> bool:
+def _unionable(value: object) -> bool:
     return (
-        isinstance(
-            v, (_Type, _Class, _Alias, _TypeUnion)
-        )
+        isinstance(value, _BuiltinUnionOr)
         or (
-            isinstance(v, _Scalar)
-            and v.value is None
+            type(value) is _Scalar
+            and value.value is None
         )
     )
 
 
+def _proven_key(value: object) -> object | None:
+    if type(value) is _Scalar:
+        return ("scalar", value.value)
+
+    if type(value) is _Type:
+        return ("type", value.identity)
+
+    if type(value) is _Class:
+        return ("class", value.identity)
+
+    if type(value) is _Seq:
+        keys = tuple(
+            _proven_key(item)
+            for item in value.items
+        )
+        if any(key is None for key in keys):
+            return None
+        return ("sequence", value.kind, keys)
+
+    if type(value) is _Alias:
+        origin = _proven_key(value.origin)
+        arguments = tuple(
+            _proven_key(arg)
+            for arg in value.args
+        )
+        if (
+            origin is None
+            or any(arg is None for arg in arguments)
+        ):
+            return None
+        return ("alias", origin, arguments)
+
+    if type(value) is _TypeUnion:
+        keys = tuple(
+            _proven_key(arg)
+            for arg in value.args
+        )
+        if any(key is None for key in keys):
+            return None
+        return ("union", frozenset(keys))
+
+    return None
+
+
+def _construct_union(
+    left: object,
+    right: object,
+) -> object | None:
+    if not (
+        _unionable(left)
+        and _unionable(right)
+    ):
+        return None
+
+    # Dostępny musi być rzeczywisty,
+    # zamodelowany slot operatora po
+    # co najmniej jednej stronie.
+    if not (
+        isinstance(left, _BuiltinUnionOr)
+        or isinstance(right, _BuiltinUnionOr)
+    ):
+        return None
+
+    members: list[object] = []
+    seen: set[object] = set()
+
+    def insert(value: object) -> bool:
+        if type(value) is _TypeUnion:
+            candidates = value.args
+        else:
+            candidates = (value,)
+
+        for candidate in candidates:
+            # Reguła CPython unionbuilder:
+            # None jako element unii jest
+            # normalizowane do typu NoneType.
+            if (
+                type(candidate) is _Scalar
+                and candidate.value is None
+            ):
+                candidate = _Type(
+                    "builtins.NoneType",
+                    False,
+                )
+
+            key = _proven_key(candidate)
+            if key is None:
+                return False
+
+            if key not in seen:
+                seen.add(key)
+                members.append(candidate)
+
+        return True
+
+    if not insert(left):
+        return None
+
+    if not insert(right):
+        return None
+
+    if len(members) == 1:
+        return members[0]
+
+    return _TypeUnion(tuple(members))
+
+
 def _eval(
     expr: ast.expr,
     class_ns: Mapping[str, object],
@@ -238,12 +349,8 @@ def _eval(
             if left is None or right is None:
                 return None
 
-            if (
-                type(n.op) is ast.BitOr
-                and _type_operand(left)
-                and _type_operand(right)
-            ):
-                return _TypeUnion((left, right))
+            if type(n.op) is ast.BitOr:
+                return _construct_union(left, right)
 
             if (
                 isinstance(left, _Scalar)
diff --git a/tests/test_cycle_semantics_annotation_union_i1.py b/tests/test_cycle_semantics_annotation_union_i1.py
new file mode 100644
index 0000000..c6d5a98
--- /dev/null
+++ b/tests/test_cycle_semantics_annotation_union_i1.py
@@ -0,0 +1,213 @@
+"""CPython 3.15 union operator and restricted annotation model parity."""
+
+import ast
+import os
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.execution.annotation_effects import (
+    _Alias,
+    _BuiltinUnionOr,
+    _Class,
+    _Module,
+    _Scalar,
+    _Seq,
+    _Type,
+    _TypeUnion,
+    _construct_union,
+    _eval,
+    _proven_key,
+)
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
+def _source(annotation, prelude=""):
+    return (
+        prelude
+        + "from dataclasses import dataclass\n"
+        + "@dataclass(frozen=True)\n"
+        + "class C:\n"
+        + f"    x: {annotation}\n"
+    )
+
+
+def _model(source):
+    tree = ast.parse(source)
+    before = ast.dump(tree)
+    options = dict(
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    first = evaluate_package_import_order(
+        {"pkg.__init__": tree}, "pkg", **options,
+    )
+    second = evaluate_package_import_order(
+        {"pkg.__init__": tree}, "pkg", **options,
+    )
+    assert first == second
+    assert ast.dump(tree) == before
+    assert first.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    return first
+
+
+def _runtime(tmp_path, source):
+    package = tmp_path / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    env = os.environ.copy()
+    env["PYTHONPATH"] = str(tmp_path)
+    env["PYTHONDONTWRITEBYTECODE"] = "1"
+    code = (
+        "try:\n"
+        " import pkg\n"
+        " print('FIELD', repr(pkg.C.__dataclass_fields__['x'].type))\n"
+        " print('RESULT OK')\n"
+        "except BaseException as error:\n"
+        " print('RESULT', type(error).__name__, str(error))\n"
+    )
+    process = subprocess.run(
+        [sys.executable, "-u", "-c", code],
+        cwd=tmp_path,
+        env=env,
+        capture_output=True,
+        text=True,
+        timeout=15,
+        check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    return process.stdout.splitlines()
+
+
+@pytest.mark.parametrize("annotation", [
+    "None | None",
+    "(None | None) | int",
+    "None | (None | None)",
+])
+def test_none_without_union_slot_stays_unknown(
+    tmp_path, annotation,
+):
+    assert _eval(ast.parse(annotation, mode="eval").body, {}, {}, {}) is None
+    result = _model(_source(annotation))
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert all(
+        event.operation != "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        for event in result.events
+    )
+    assert _runtime(tmp_path, _source(annotation))[-1].startswith(
+        "RESULT TypeError unsupported operand type(s) for |:"
+    )
+
+
+@pytest.mark.parametrize("annotation,expected,field_type", [
+    ("int | int", _Type("builtins.int", False), "<class 'int'>"),
+    ("list[int] | list[int]", _Alias(_Type("builtins.list", True), (_Type("builtins.int", False),)), "list[int]"),
+    ("int | None", _TypeUnion((_Type("builtins.int", False), _Type("builtins.NoneType", False))), "int | None"),
+    ("None | int", _TypeUnion((_Type("builtins.NoneType", False), _Type("builtins.int", False))), "None | int"),
+    ("int | None | None", _TypeUnion((_Type("builtins.int", False), _Type("builtins.NoneType", False))), "int | None"),
+    ("int | str | int", _TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False))), "int | str"),
+    ("(int | str) | (str | None)", _TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False), _Type("builtins.NoneType", False))), "int | str | None"),
+    ("list[int] | list[str]", _TypeUnion((_Alias(_Type("builtins.list", True), (_Type("builtins.int", False),)), _Alias(_Type("builtins.list", True), (_Type("builtins.str", False),)))), "list[int] | list[str]"),
+    ("list[[]] | int", _TypeUnion((_Alias(_Type("builtins.list", True), (_Seq("list", ()),)), _Type("builtins.int", False))), "list[[]] | int"),
+    ("list[[]] | list[[]]", _Alias(_Type("builtins.list", True), (_Seq("list", ()),)), "list[[]]"),
+    ("list[int | str] | list[str | int]", _Alias(_Type("builtins.list", True), (_TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False))),)), "list[int | str]"),
+])
+def test_union_normalization_matches_cpython(
+    tmp_path, annotation, expected, field_type,
+):
+    expression = ast.parse(annotation, mode="eval").body
+    before = ast.dump(expression)
+    assert _eval(expression, {}, {}, {}) == expected
+    assert _eval(expression, {}, {}, {}) == expected
+    assert ast.dump(expression) == before
+    result = _model(_source(annotation))
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+    runtime = _runtime(tmp_path, _source(annotation))
+    assert runtime[-1] == "RESULT OK"
+    assert runtime[0] == f"FIELD {field_type}"
+
+
+def test_union_keys_and_dispatch_boundary():
+    integer = _Type("builtins.int", False)
+    string = _Type("builtins.str", False)
+    left = _construct_union(integer, string)
+    right = _construct_union(string, integer)
+    assert isinstance(left, _TypeUnion)
+    assert isinstance(right, _TypeUnion)
+    assert left.args == (integer, string)
+    assert right.args == (string, integer)
+    assert _proven_key(left) == _proven_key(right)
+    assert _construct_union(left, integer) == left
+    assert _construct_union(_Scalar(None), _Scalar(None)) is None
+    assert _proven_key(_Module("external")) is None
+    assert not isinstance(_Scalar(None), _BuiltinUnionOr)
+    assert not isinstance(_Seq("list", ()), _BuiltinUnionOr)
+    assert not isinstance(_Module("pkg"), _BuiltinUnionOr)
+    assert isinstance(_Class("pkg.T"), _BuiltinUnionOr)
+
+
+@pytest.mark.parametrize("prelude,annotation,effect", [
+    (
+        "class T:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        print('USER_GETITEM', flush=True)\n"
+        "        raise SystemExit('getitem-effect')\n",
+        "T[int]", "USER_GETITEM",
+    ),
+    (
+        "class Meta(type):\n"
+        "    def __or__(cls, other):\n"
+        "        print('USER_OR', flush=True)\n"
+        "        raise SystemExit('or-effect')\n"
+        "class T(metaclass=Meta): pass\n",
+        "T | int", "USER_OR",
+    ),
+    ("list = 1\n", "list[int]", None),
+    ("from builtins import list as Alias\n", "Alias[int]", None),
+])
+def test_dynamic_boundaries_do_not_gain_pass(
+    tmp_path, prelude, annotation, effect,
+):
+    source = _source(annotation, prelude)
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    runtime = _runtime(tmp_path, source)
+    if effect:
+        assert effect in runtime
+
+
+def test_operand_evaluation_order_remains_left_to_right(tmp_path):
+    prelude = (
+        "class L:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        print('LEFT', flush=True)\n"
+        "        return int\n"
+        "class R:\n"
+        "    def __class_getitem__(cls, item):\n"
+        "        print('RIGHT', flush=True)\n"
+        "        return str\n"
+    )
+    source = _source("L[int] | R[int]", prelude)
+    result = _model(source)
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert _runtime(tmp_path, source) == [
+        "LEFT", "RIGHT", "FIELD int | str", "RESULT OK",
+    ]
```
