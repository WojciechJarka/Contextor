# P9-I1-R1 — STOP na obowiązkowym checkpoincie

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP jako pierwsze źródło: LIVE revision 1492, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `resync_required=false`, `syntax_errors=0` (fresh) **przed zmianami**. Per-file `workspace_sync=verified` dla `execution/calls.py`, `package_model.py` i obu docelowych plików testowych.
- DIRECT_EVIDENCE: HEAD `bd8276602665c3c4f1a6758d6ca7a14710e60f38`; początkowy `git status --short` pusty. Stare kotwice `allow_builtin_property`, `uses_property`, `CHECK_BUILTIN_PROPERTY` obecne, brak częściowych zmian P9-I1.

## CHECKPOINTS

- DIRECT_EVIDENCE: edycja `execution/calls.py` po `_RestrictedFunction` — `ast.parse` PASS, `git diff --check` PASS, diff zgodny z lokalną kotwicą.
- DIRECT_EVIDENCE: importy, `_safe_passive_function_definition` i `_safe_passive_class_definition` w `package_model.py` — po każdym kroku `ast.parse` PASS i `git diff --check` PASS.
- DIRECT_EVIDENCE: checkpoint `_compile` FAIL. Patch zbyt szeroko dopasował początek bloku w pętli `for body_statement in stmt.body` i wstawił 88 linii przed dotychczasowym warunkiem `AnnAssign`, zamiast zastąpić wyłącznie blok `CHECK_BUILTIN_PROPERTY`. `ast.parse(package_model.py)` zakończył się `SyntaxError: invalid syntax`, linia 1073. Diff pokazuje przerwaną strukturę `elif isinstance(stmt, ast.FunctionDef)`.
- Zgodnie z instrukcją „jeśli struktura zostanie naruszona: STOP, bez samodzielnej korekty projektu” zatrzymano dalsze edycje. Nie wykonano `git restore`, pytest ani dalszej implementacji. **Repozytorium pozostaje z niepoprawnym składniowo `package_model.py`; nie należy traktować zadania jako zakończonego.**

## EXACT_CHANGES

- Faktycznie zmieniono tylko `contextor/core/cycle_semantics/execution/calls.py` oraz `contextor/core/cycle_semantics/package_model.py`. Testy pozostały nietknięte.
- W `calls.py` dodano `_KnownBuiltinCallable` i wskazane helpery.
- W `package_model.py` dodano dwa importy helperów, zmieniono predykaty dopuszczania dekoratora, a następnie powstała błędna wstawka w `_compile`. Handler importu, `ALIAS` i dekoratora nie zostały zmienione.

## CPYTHON_315_PARITY

- NOT_PROVED w tym ponowieniu: nie powtarzano eksperymentów CPython A–M z poprzedniego P9-I1, ponieważ checkpoint edycji nie przeszedł. Źródłowy audyt semantyczny P9-R2 i wcześniejsze izolowane wyniki nie zostały unieważnione przez kod, który teraz nie parsuje się.

## TARGETED_RESULTS

- NOT_PROVED: nie uruchomiono pytest, zgodnie z nakazem STOP przed regresją.
- DIRECT_EVIDENCE, traceback obowiązkowego `ast.parse`:

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import ast,pathlib; ast.parse(pathlib.Path('contextor/core/cycle_semantics/package_model.py').read_text()); print('AST_OK')
                        ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python315\Lib\ast.py", line 46, in parse
    return compile(source, filename, mode, flags,
                   _feature_version=feature_version, optimize=optimize,
                   module=module)
  File "<unknown>", line 1073
    and body_statement.value is not None
    ^^^
SyntaxError: invalid syntax
```

## MODEL_AFTER

- NOT_PROVED: nie można wykonać evaluatora po bieżącej niepoprawnej składni `package_model.py`. Brak deklaracji MODEL_PASS/UNKNOWN po zmianie.

## PRODUCTION_AUTHORITY

- CODE_PATH_PROVED ze stanu przed zmianą: warunkowy wewnętrzny `MODEL_PASS` nie jest zwykłym produkcyjnym PASS. W tym zadaniu nie zmieniono ścieżki publikacji ani warning suppression. Nie jest to certyfikacja bieżącego, nieparsującego się kodu.

## MCP_POST_AUDIT

- NOT_PROVED: post-change audit nie został wykonany, ponieważ obowiązkowy checkpoint zgłosił STOP. Preflight `syntax_errors=0` odnosi się wyłącznie do stanu sprzed edycji i **nie** opisuje bieżącego pliku.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/calls.py`
- `contextor/core/cycle_semantics/package_model.py` — obecnie niepoprawny składniowo
- `walkthrough.md` — sam raport

## FULL_DIFFS

Pełny rzeczywisty diff dwóch plików source na moment zatrzymania:

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 8f7db99..81e787d 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -12,6 +12,43 @@ class _RestrictedFunction:
     parameters: tuple[str, ...] = ()
 
 
+@dataclass(frozen=True)
+class _KnownBuiltinCallable:
+    canonical_identity: str
+    effect: str
+
+
+_KNOWN_BUILTIN_CALLABLES = {
+    "property": _KnownBuiltinCallable(
+        "builtins.property", "PASSIVE_PROPERTY",
+    ),
+}
+
+
+def _known_builtin_callable(
+    name: str | None,
+) -> _KnownBuiltinCallable | None:
+    return _KNOWN_BUILTIN_CALLABLES.get(name)
+
+
+def _resolve_known_builtin_callable(
+    name: str | None,
+    namespace: dict[str, object | None],
+) -> _KnownBuiltinCallable | None:
+    if name is None:
+        return None
+    value = (
+        namespace[name]
+        if name in namespace
+        else _known_builtin_callable(name)
+    )
+    return (
+        value
+        if type(value) is _KnownBuiltinCallable
+        else None
+    )
+
+
 @dataclass(frozen=True, eq=False)
 class _DecoratorSnapshot:
     names: tuple[str, ...]
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 9e0bf3f..2ca3ff9 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -66,7 +66,9 @@ from .execution.calls import (
     _RestrictedFunction,
     _execute_restricted_call,
     _execute_restricted_object_call,
+    _known_builtin_callable,
     _new_restricted_function,
+    _resolve_known_builtin_callable,
     _snapshot_named_decorators,
 )
 
@@ -151,7 +153,7 @@ def _safe_passive_function_definition(
     *,
     allow_dunder: bool = False,
     annotation_semantics: str | None = None,
-    allow_builtin_property: bool = False,
+    allow_known_class_decorator: bool = False,
     allow_restricted_decorator: bool = False,
     allow_restricted_default_calls: bool = False,
 ) -> bool:
@@ -169,13 +171,13 @@ def _safe_passive_function_definition(
         or (
             bool(statement.decorator_list)
             and not (
-                allow_builtin_property
+                allow_known_class_decorator
                 and type(statement) is ast.FunctionDef
                 and len(statement.decorator_list) == 1
                 and type(statement.decorator_list[0])
                 is ast.Name
-                and statement.decorator_list[0].id
-                == "property"
+                and statement.decorator_list[0].id.isidentifier()
+                and not statement.decorator_list[0].id.startswith("__")
             )
             and not (
                 allow_restricted_decorator
@@ -377,18 +379,20 @@ def _safe_passive_class_definition(
                 if field_name is not None:
                     field_factory_names.add(field_name)
 
-        uses_property = any(
-            type(item) is ast.FunctionDef
-            and len(item.decorator_list) == 1
-            and type(item.decorator_list[0]) is ast.Name
-            and item.decorator_list[0].id == "property"
+        class_decorator_names = {
+            item.decorator_list[0].id
             for item in statement.body
-        )
-
-        protected_names = set(field_factory_names)
+            if (
+                type(item) is ast.FunctionDef
+                and len(item.decorator_list) == 1
+                and type(item.decorator_list[0]) is ast.Name
+            )
+        }
 
-        if uses_property:
-            protected_names.add("property")
+        protected_names = (
+            set(field_factory_names)
+            | class_decorator_names
+        )
 
         if any(
             (
@@ -523,7 +527,7 @@ def _safe_passive_class_definition(
                 body_statement,
                 allow_dunder=True,
                 annotation_semantics=annotation_semantics,
-                allow_builtin_property=conditional_dataclass,
+                allow_known_class_decorator=conditional_dataclass,
             )
         ):
             continue
@@ -977,6 +981,94 @@ def _compile(
                     (ast.Import, ast.ImportFrom),
                 ):
                     if (
+                        conditional_dataclass
+                        and type(body_statement)
+                        is ast.FunctionDef
+                        and len(body_statement.decorator_list) == 1
+                        and type(
+                            body_statement.decorator_list[0]
+                        ) is ast.Name
+                    ):
+                        decorator = (
+                            body_statement.decorator_list[0]
+                        )
+                        steps.append(
+                            _Step(
+                                "APPLY_KNOWN_CLASS_DECORATOR",
+                                target=decorator.id,
+                                binding=body_statement.name,
+                                source_line=decorator.lineno,
+                                source_column=decorator.col_offset,
+                            )
+                        )
+
+                    continue
+
+                fragment = ast.Module(
+                    body=[body_statement],
+                    type_ignores=[],
+                )
+                compiled = _compile(
+                    fragment,
+                    logical,
+                    package,
+                    _depth=_depth + 1,
+                    assume_frozen_dataclass=assume_frozen_dataclass,
+                )
+                if (
+                    compiled is None
+                    or any(
+                        item.op not in {
+                            "IMPORT",
+                            "FROM",
+                            "PREPARE_FROM_MEMBER",
+                        }
+                        for item in compiled
+                    )
+                ):
+                    return None
+
+                steps.extend(
+                    replace(item, class_local=True)
+                    for item in compiled
+                )
+
+            if conditional_dataclass:
+                steps.append(
+                    _Step(
+                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
+                        binding=stmt.name,
+                        source_line=stmt.decorator_list[0].lineno,
+                        source_column=stmt.decorator_list[0].col_offset,
+                        annotation_builtin_names=tuple(sorted({
+                            node.id
+                            for field in stmt.body
+                            if isinstance(field, ast.AnnAssign)
+                            for node in ast.walk(field.annotation)
+                            if isinstance(node, ast.Name)
+                        })),
+                    )
+                )
+            else:
+                steps.append(
+                    _Step(
+                        (
+                            "DEFINE_DECORATED_PASSIVE_CLASS"
+                            if ordinary_named_decorators
+                            else "DEFINE_PASSIVE_CLASS"
+                        ),
+                        binding=stmt.name,
+                        source_line=stmt.lineno,
+                        source_column=stmt.col_offset,
+                        definition_id=(
+                            f"{logical}:{stmt.lineno}:{stmt.col_offset}"
+                        ),
+                        defines_init_subclass=has_init_subclass,
+                        passive_metaclass_body=passive_metaclass_body,
+                    )
+                )
+
+        elif isinstance(stmt, ast.FunctionDef):
                         isinstance(body_statement, ast.AnnAssign)
                         and body_statement.value is not None
                     ):
```
