# P9-I1-R4 — CLASS DECORATOR STEP, ONE EXACT REPLACEMENT

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP jako pierwsze źródło: LIVE revision 1497, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `syntax_errors=0` (fresh), `resync_required=false`. Per-file `workspace_sync=verified` dla `package_model.py::_compile`.
- DIRECT_EVIDENCE: HEAD `1b4d2b4ba0ea9bc4a6154157709cb60f4593f8bb`; początkowy `git status --short` pusty. Naprawa R3 jest już w bieżącym HEAD, dlatego nie stanowi lokalnego diffu względem HEAD. `ast.parse(package_model.py)` przed zmianą wypisał `AST_OK`.
- CODE_PATH_PROVED: wcześniejsze P9-I1 pozostają: importy `_known_builtin_callable`/`_resolve_known_builtin_callable`, `allow_known_class_decorator`, `class_decorator_names` i `protected_names`. Dokładny stary blok `CHECK_BUILTIN_PROPERTY` występował raz w pętli `for body_statement in stmt.body` gałęzi `ast.ClassDef`; osobny handler wykonawczy pozostał.

## EXACT_REPLACEMENT

- Zastąpiono wyłącznie jeden stary blok emisji `CHECK_BUILTIN_PROPERTY` blokiem emisji `APPLY_KNOWN_CLASS_DECORATOR` w tym samym miejscu. Nowy `_Step` ma `target=decorator.id`, `binding=body_statement.name`, źródłowe `lineno` i `col_offset`.
- Poprzedzający warunek `AnnAssign`, następujący `continue`, obsługa importów i `DEFINE_CONDITIONAL_FROZEN_DATACLASS` pozostały. Nie zmieniono handlerów, `calls.py` ani testów.

## AST_VALIDATION

- DIRECT_EVIDENCE: CPython 3.15.2 `ast.parse(package_model.py)` wypisał `AST_OK` (exit 0). Literalne sprawdzenie gałęzi `_compile`: jedna `elif isinstance(stmt, ast.ClassDef)`, jedna `elif isinstance(stmt, ast.AnnAssign)`, jedna `elif isinstance(stmt, ast.FunctionDef)`; nowy krok występuje raz.
- Nie uruchomiono pytest. Nowy krok nie ma jeszcze handlera wykonawczego; status semantyczny pozostaje częściowy.

## DIFF_VALIDATION

- DIRECT_EVIDENCE: `git diff --check` exit 0. Aktualny diff `package_model.py` ma dokładnie jeden hunk `@@ -1006,17 +1006,21 @@ def _compile(`, 9 dodanych i 5 usuniętych linii; żadnej dodatkowej kopii fragmentu. Stary `CHECK_BUILTIN_PROPERTY` występuje jeszcze raz, wyłącznie w nietkniętym handlerze runtime.
- Pełny diff względem HEAD znajduje się w `FULL_DIFFS`. Nie może obejmować R3 jako lokalnej zmiany, bo R3 jest już zatwierdzone w aktualnym HEAD.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1498, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`. Per-file `workspace_sync=verified` dla `package_model.py::_compile`; globalny `workspace_sync=unverified`.
- Zmiana zwykłego kodu repo nie stanowi dowodu adopcji przez proces runtime serwera MCP. Nie wykonano restartu ani ręcznego resync.

## REMAINING_IMPLEMENTATION

- CODE_PATH_PROVED: istniejący handler `CHECK_BUILTIN_PROPERTY` pozostał, a handler `APPLY_KNOWN_CLASS_DECORATOR` jeszcze nie istnieje. Nie wykonano pozostałych kroków P9-I1 dotyczących `FROM`, `ALIAS` i testów. **P9-I1 PARTIAL — NOT FINAL PASS.**

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — jedyna zmiana source.
- `walkthrough.md` — raport, wyłączony z diffu source/tests.

## FULL_DIFFS

Cały aktualny diff `package_model.py` względem bieżącego HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b0bf6a2..2f92a87 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1006,17 +1006,21 @@ def _compile(
                         )
 
                     if (
-                        type(body_statement) is ast.FunctionDef
+                        conditional_dataclass
+                        and type(body_statement)
+                        is ast.FunctionDef
                         and len(body_statement.decorator_list) == 1
                         and type(body_statement.decorator_list[0])
                         is ast.Name
-                        and body_statement.decorator_list[0].id
-                        == "property"
                     ):
+                        decorator = body_statement.decorator_list[0]
                         steps.append(
                             _Step(
-                                "CHECK_BUILTIN_PROPERTY",
-                                target="property",
+                                "APPLY_KNOWN_CLASS_DECORATOR",
+                                target=decorator.id,
+                                binding=body_statement.name,
+                                source_line=decorator.lineno,
+                                source_column=decorator.col_offset,
                             )
                         )
 
```
