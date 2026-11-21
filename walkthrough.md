# P9-I1-R5 — APPLY_KNOWN_CLASS_DECORATOR HANDLER

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP był pierwszym źródłem. LIVE revision 1498, `canonical_state=fresh`, globalny `workspace_sync=unverified`, `syntax_errors=0` (fresh), `resync_required=false`; per-file `workspace_sync=verified` dla `package_model.py::evaluate_package_import_order`.
- DIRECT_EVIDENCE: HEAD `ace022b87457f7a2b4a12329efbdf8a9df5a175e`; początkowy `git status --short` i diff `package_model.py` były puste.
- CODE_PATH_PROVED: `_compile` emitował `APPLY_KNOWN_CLASS_DECORATOR` (`package_model.py:1019`), `_resolve_known_builtin_callable` był importowany (`:71`), a stary handler `CHECK_BUILTIN_PROPERTY` występował dokładnie raz (`:2563`). MCP potwierdził dokładną kotwicę sąsiednich handlerów.

## EXACT_REPLACEMENT

- Zastąpiono wyłącznie blok handlera `CHECK_BUILTIN_PROPERTY` blokiem `APPLY_KNOWN_CLASS_DECORATOR`. Handler pobiera `_resolve_known_builtin_callable(step.target, namespaces[module])` i odmawia `UNKNOWN`, gdy nie ma `binding`, faktu callable albo efektu `PASSIVE_PROPERTY`.
- Nie zmieniono `_compile`, `calls.py`, `FROM`, `ALIAS`, testów ani sąsiedniego `DEFINE_CONDITIONAL_FROZEN_DATACLASS`. Nie dodano eventów, symulacji gettera ani deskryptora.

## AST_VALIDATION

- DIRECT_EVIDENCE: `.venv/Scripts/python.exe` (CPython 3.15.2) wykonało `ast.parse(package_model.py)` i wypisało `AST_OK`, exit 0.
- Nie uruchomiono pytest ani FULL.

## DIFF_VALIDATION

- DIRECT_EVIDENCE: `git diff --check` exit 0. Aktualny diff ma jeden hunk w `evaluate_package_import_order` przy linii 2560. W `package_model.py` brak `CHECK_BUILTIN_PROPERTY`; `APPLY_KNOWN_CLASS_DECORATOR` występuje raz jako `_Step` (`:1019`) i dokładnie raz jako handler (`:2563`). Początkowy status był czysty, więc diff poniżej obejmuje jedyną zmianę aktualnego zadania.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1499, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`. Per-file `workspace_sync=verified` dla `package_model.py::evaluate_package_import_order`. Globalny `workspace_sync=unverified`.
- Per-file sync potwierdza zgodność canonical z plikiem, nie adopcję nowego kodu przez działający proces backendu MCP. Nie restartowano.

## REMAINING_IMPLEMENTATION

- CODE_PATH_PROVED: handler jest obecny, lecz P9-I1 nadal nie ma zakończonych zmian `FROM` i `ALIAS` oraz nowych kontraktów testowych. Status: **P9-I1 PARTIAL — NOT FINAL PASS**.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — jedyny zmieniony plik source.
- `walkthrough.md` — raport, wyłączony z diffu source/tests.

## FULL_DIFFS

Pełny aktualny diff source/tests względem HEAD (testy bez zmian):

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 2f92a87..b60810a 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -2560,10 +2560,15 @@ def evaluate_package_import_order(
                     step.target,
                 )
 
-        elif step.op == "CHECK_BUILTIN_PROPERTY":
+        elif step.op == "APPLY_KNOWN_CLASS_DECORATOR":
+            callable_fact = _resolve_known_builtin_callable(
+                step.target,
+                namespaces[module],
+            )
             if (
-                step.target != "property"
-                or "property" in namespaces[module]
+                not step.binding
+                or callable_fact is None
+                or callable_fact.effect != "PASSIVE_PROPERTY"
             ):
                 return result(
                     "UNKNOWN",
```
