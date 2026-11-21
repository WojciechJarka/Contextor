# P9-I1-R3 — naprawa zatwierdzonego błędu składni

## PREFLIGHT

- DIRECT_EVIDENCE: pierwszym źródłem był Contextor MCP `get_project_architecture(fields=[])`: LIVE revision 1496, `canonical_state=stale`, globalny `workspace_sync=unverified`, `syntax_errors=1` (fresh), `resync_required=false`.
- DIRECT_EVIDENCE: `git rev-parse HEAD` = `f38c340836f7cf8c39828d55c5`; `git rev-parse HEAD:contextor/core/cycle_semantics/package_model.py` = `2ca3ff964b2c7dcce7aaaf8a8a87781bb9655d36`. `git status --short` pokazywał tylko `M walkthrough.md`; `git diff -- contextor/core/cycle_semantics/package_model.py` był pusty. Wszystkie wymagane warunki Git spełnione.
- DIRECT_EVIDENCE: aktualne linie 984–1071 miały dokładnie zadane kotwice: początek `conditional_dataclass / and type(body_statement)` i koniec błędnie dodanym `elif isinstance(stmt, ast.FunctionDef):`. Linia 983 to zachowane `if (`; od linii 1072 następował zachowany warunek `AnnAssign`.

## EXACT_88_LINE_REMOVAL

- Usunięto wyłącznie 88 linii 984–1071 z `contextor/core/cycle_semantics/package_model.py`. Nie edytowano `execution/calls.py`, testów ani żadnych innych linii produkcyjnych. Nie użyto `git restore` ani `reset`.
- Po usunięciu gałąź `ast.ClassDef` zawiera bezpośrednio `if (` z istniejącym `isinstance(body_statement, ast.AnnAssign)` i `body_statement.value is not None`; dalsze kroki definicji klasy pozostały.

## AST_VALIDATION

- DIRECT_EVIDENCE: wskazane `.venv/Scripts/python.exe` (CPython 3.15.2) wykonało `ast.parse(package_model.py)` i wypisało `AST_OK` (exit 0).
- DIRECT_EVIDENCE: `git diff --check` exit 0. Narzędzie wypisało jedynie ostrzeżenie o przyszłej konwersji LF/CRLF dla `walkthrough.md`, bez błędu diff.
- Nie uruchamiano pytest ani FULL.

## DIFF_VALIDATION

- DIRECT_EVIDENCE: `git diff --numstat -- package_model.py` = `0\t88\tcontextor/core/cycle_semantics/package_model.py`. `git diff` wykazał dokładnie jeden hunk `@@ -981,94 +981,6 @@ def _compile(`, zero dodanych i 88 usuniętych linii. `git status --short` po korekcie zawierał `M package_model.py` i `M walkthrough.md`; brak zmian `calls.py` i testów.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: pierwszy odczyt po korekcie nadal widział revision 1496, `canonical_state=stale`, `syntax_errors=1`; był to stan LIVE przed adopcją zmiany przez watcher, odrębny od lokalnego `AST_OK`.
- DIRECT_EVIDENCE: późniejszy per-file `get_symbol_implementation` dla `_compile` dał revision 1497, `workspace_sync=verified`, `canonical_state=fresh`, `syntax_errors=0` (fresh). Ponowne `get_project_architecture(fields=[])` dało LIVE revision 1497, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`; globalny `workspace_sync` pozostał `unverified`. Nie wykonywano ręcznego resync ani restartu.

## REMAINING_PARTIAL_IMPLEMENTATION

- CODE_PATH_PROVED: `execution/calls.py` w HEAD zawiera `_KnownBuiltinCallable` i helpery, a `package_model.py` w HEAD importuje helpery oraz zawiera `allow_known_class_decorator` i `class_decorator_names`. Po naprawie nadal istnieją `CHECK_BUILTIN_PROPERTY` w `_compile` i jego handlerze (`package_model.py:1018,2559`); nie ma jeszcze `APPLY_KNOWN_CLASS_DECORATOR`. Handler `FROM` ani `ALIAS` nie został ukończony w tym zadaniu.
- Status P9-I1: **PARTIAL — NOT FINAL PASS**. `AST_OK` i świeże MCP nie są wynikiem semantycznej regresji ani ukończeniem P9-I1.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — jedyny zmieniony plik source.
- `walkthrough.md` — sam raport, wyłączony z wymaganego diffu source/tests.

## FULL_DIFFS

Pełny aktualny diff `package_model.py` względem bieżącego HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 2ca3ff9..b0bf6a2 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -981,94 +981,6 @@ def _compile(
                     (ast.Import, ast.ImportFrom),
                 ):
                     if (
-                        conditional_dataclass
-                        and type(body_statement)
-                        is ast.FunctionDef
-                        and len(body_statement.decorator_list) == 1
-                        and type(
-                            body_statement.decorator_list[0]
-                        ) is ast.Name
-                    ):
-                        decorator = (
-                            body_statement.decorator_list[0]
-                        )
-                        steps.append(
-                            _Step(
-                                "APPLY_KNOWN_CLASS_DECORATOR",
-                                target=decorator.id,
-                                binding=body_statement.name,
-                                source_line=decorator.lineno,
-                                source_column=decorator.col_offset,
-                            )
-                        )
-
-                    continue
-
-                fragment = ast.Module(
-                    body=[body_statement],
-                    type_ignores=[],
-                )
-                compiled = _compile(
-                    fragment,
-                    logical,
-                    package,
-                    _depth=_depth + 1,
-                    assume_frozen_dataclass=assume_frozen_dataclass,
-                )
-                if (
-                    compiled is None
-                    or any(
-                        item.op not in {
-                            "IMPORT",
-                            "FROM",
-                            "PREPARE_FROM_MEMBER",
-                        }
-                        for item in compiled
-                    )
-                ):
-                    return None
-
-                steps.extend(
-                    replace(item, class_local=True)
-                    for item in compiled
-                )
-
-            if conditional_dataclass:
-                steps.append(
-                    _Step(
-                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
-                        binding=stmt.name,
-                        source_line=stmt.decorator_list[0].lineno,
-                        source_column=stmt.decorator_list[0].col_offset,
-                        annotation_builtin_names=tuple(sorted({
-                            node.id
-                            for field in stmt.body
-                            if isinstance(field, ast.AnnAssign)
-                            for node in ast.walk(field.annotation)
-                            if isinstance(node, ast.Name)
-                        })),
-                    )
-                )
-            else:
-                steps.append(
-                    _Step(
-                        (
-                            "DEFINE_DECORATED_PASSIVE_CLASS"
-                            if ordinary_named_decorators
-                            else "DEFINE_PASSIVE_CLASS"
-                        ),
-                        binding=stmt.name,
-                        source_line=stmt.lineno,
-                        source_column=stmt.col_offset,
-                        definition_id=(
-                            f"{logical}:{stmt.lineno}:{stmt.col_offset}"
-                        ),
-                        defines_init_subclass=has_init_subclass,
-                        passive_metaclass_body=passive_metaclass_body,
-                    )
-                )
-
-        elif isinstance(stmt, ast.FunctionDef):
                         isinstance(body_statement, ast.AnnAssign)
                         and body_statement.value is not None
                     ):
```
