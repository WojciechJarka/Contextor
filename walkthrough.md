# P9-I1-R7 — BUILTIN IDENTITY THROUGH ALIAS

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP jako pierwsze źródło: LIVE revision 1500, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`. Globalny `workspace_sync=unverified`, per-file dla `package_model.py::evaluate_package_import_order`: `verified`.
- DIRECT_EVIDENCE: HEAD `b1d8d1a202bc1372d018568f893a7f6cd8bff686`; początkowy `git status --short` pusty.
- CODE_PATH_PROVED: import `_known_builtin_callable` (`package_model.py:69`), emisja `APPLY_KNOWN_CLASS_DECORATOR` (`:1019`), rozpoznanie znanego builtinu w external `FROM` (`:2046`) i handler dekoratora (`:2576`) były obecne. MCP potwierdził stary blok `ALIAS` dokładnie raz przy linii 3066.

## EXACT_REPLACEMENT

- Zastąpiono wyłącznie wskazany blok `elif step.op == "ALIAS"`. Event `ALIAS` i sąsiedni handler `ATTR` pozostały bez zmian.
- Nie zmieniono `_compile`, `FROM`, `calls.py`, innych handlerów ani testów.

## ALIAS_BINDING_SEMANTICS

- CODE_PATH_PROVED: gdy `step.target` istnieje w `namespaces[module]`, kopiowana jest jego aktualna reprezentowana wartość, także `None`. Fallback do `_known_builtin_callable(step.target)` zachodzi jedynie dla nazwy niezwiązanej i przy `_assume_frozen_dataclass_decoration`. Nierozpoznana nazwa zwraca `UNKNOWN`.
- INFERENCE: fallback pozostaje częścią warunkowego założenia o konwencjonalnym `builtins`, a nie dowodem rzeczywistej tożsamości obiektu w runtime. Zachowanie aliasu po późniejszym rebindingu źródła wymaga jeszcze kontraktów testowych P9-I1.

## AST_VALIDATION

- DIRECT_EVIDENCE: `.venv/Scripts/python.exe` (CPython 3.15.2) wykonało `ast.parse(package_model.py)`; `AST_OK`, exit 0. Nie uruchomiono pytest ani FULL.

## DIFF_VALIDATION

- DIRECT_EVIDENCE: `git diff --check` exit 0. Aktualny diff source/tests względem HEAD ma jeden hunk w handlerze `ALIAS` w `evaluate_package_import_order`; brak zmian w innych funkcjach i modułach.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: `get_live_events(after_revision=1500)` potwierdziło event `desktop_watcher` `UPDATED` dla `package_model.py`, revision 1501, `continuity=continuous`, `resync_required=false`.
- DIRECT_EVIDENCE: LIVE revision 1501, `canonical_state=fresh`, `syntax_errors=0` (fresh), per-file `workspace_sync=verified` dla `package_model.py::evaluate_package_import_order`. Globalny `workspace_sync=unverified`.
- Zweryfikowany canonical nie dowodzi adopcji zmienionego kodu przez proces backendu MCP. Nie restartowano.

## REMAINING_IMPLEMENTATION

- CONTRACT_PROVED: zgodnie z etapem R7 kontrakty testowe i pełna walidacja P9-I1 pozostają niewykonane. Status: **P9-I1 PARTIAL — NOT FINAL PASS**.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — jedyny zmieniony plik source/tests.
- `walkthrough.md` — raport, poza diffem source/tests.

## FULL_DIFFS

Pełny aktualny diff source/tests względem HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 81ad46e..1326eba 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -3064,20 +3064,23 @@ def evaluate_package_import_order(
             )
 
         elif step.op == "ALIAS":
-            if (
-                not step.target
-                or not step.binding
-                or step.target not in namespaces[module]
-            ):
+            if not step.target or not step.binding:
+                return result("UNKNOWN", module, step.target)
+
+            if step.target in namespaces[module]:
+                value = namespaces[module][step.target]
+            elif _assume_frozen_dataclass_decoration:
+                value = _known_builtin_callable(step.target)
+                if value is None:
+                    return result(
+                        "UNKNOWN", module, step.target,
+                    )
+            else:
                 return result(
-                    "UNKNOWN",
-                    module,
-                    step.target,
+                    "UNKNOWN", module, step.target,
                 )
 
-            namespaces[module][step.binding] = (
-                namespaces[module][step.target]
-            )
+            namespaces[module][step.binding] = value
 
             events.append(
                 PackageModelEvent(
```
