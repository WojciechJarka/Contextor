# P9-I1-R6 — KNOWN BUILTIN IDENTITY IN EXTERNAL FROM

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP był pierwszym źródłem. LIVE revision 1499, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`. Globalny `workspace_sync=unverified`; per-file dla `package_model.py::evaluate_package_import_order` był `verified`.
- DIRECT_EVIDENCE: HEAD `5455e6bda4e2e53cfd4f41d55c5c906f9f769088`; początkowy `git status --short` był pusty.
- CODE_PATH_PROVED: `_known_builtin_callable` jest importowany (`package_model.py:69`), `_compile` emituje `APPLY_KNOWN_CLASS_DECORATOR` (`:1019`), a handler wykonawczy istnieje (`:2563` przed edycją). MCP pokazał wskazany stary blok dokładnie w gałęzi `external_decision == "ASSUME"`, przy liniach 2045–2053. Kotwica występowała raz.

## EXACT_REPLACEMENT

- Zastąpiono wyłącznie wskazany blok przypisujący znacznik `ASSUMED_EXTERNAL` do `namespaces[module][step.binding]`. Otaczający warunek, event, rekord założonego importu i obsługa pozostałych importów pozostały bez zmian.
- Nie edytowano `_compile`, `ALIAS`, handlera dekoratora, `calls.py` ani testów.

## IMPORT_IDENTITY

- CODE_PATH_PROVED: tylko przy `_assume_frozen_dataclass_decoration`, `step.op == "FROM"` i `target == "builtins"` model wywołuje `_known_builtin_callable(step.symbol)`. Rozpoznany fakt trafia do namespace pod `step.binding`. Przy braku faktu pozostaje dotychczasowy znacznik `ASSUMED_EXTERNAL`.
- INFERENCE: ta zmiana zachowuje tożsamość znanej funkcji w warunkowej ścieżce `from builtins import ...`; nie potwierdza runtime tożsamości obiektu importowanego z faktycznego środowiska. Kontrakt nadal zależy od założenia konwencjonalnego `builtins`.

## AST_VALIDATION

- DIRECT_EVIDENCE: `.venv/Scripts/python.exe` (CPython 3.15.2) wykonało `ast.parse(package_model.py)`; wynik `AST_OK`, exit 0.
- Zgodnie z zadaniem nie uruchomiono pytest ani FULL.

## DIFF_VALIDATION

- DIRECT_EVIDENCE: `git diff --check` exit 0. Aktualny diff source/tests względem HEAD ma jeden hunk, wyłącznie we wskazanym bloku. Nowy fragment `known_builtin = (` występuje raz przy linii 2045. `APPLY_KNOWN_CLASS_DECORATOR` nadal występuje jako jeden emitowany krok i jeden handler.

## MCP_POST_AUDIT

- DIRECT_EVIDENCE: `get_live_events(after_revision=1499)` zwróciło pojedynczy event `desktop_watcher` `update_file`, `UPDATED`, dla `package_model.py`, revision 1500; ciągłość `continuous`, `resync_required=false`.
- DIRECT_EVIDENCE: po publikacji LIVE revision 1500, `canonical_state=fresh`, `syntax_errors=0` (fresh), `resync_required=false`; per-file `workspace_sync=verified` dla `package_model.py::evaluate_package_import_order`. Globalny `workspace_sync=unverified`.
- Weryfikacja LIVE canonical nie dowodzi adopcji nowego kodu przez działający proces backendu MCP. Nie restartowano.

## REMAINING_IMPLEMENTATION

- CODE_PATH_PROVED: etap ALIAS i kontrakty testowe P9-I1 pozostają poza zakresem R6. Status: **P9-I1 PARTIAL — NOT FINAL PASS**.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — jedyny zmieniony plik source/tests.
- `walkthrough.md` — niniejszy raport; nie jest plikiem source/tests.

## FULL_DIFFS

Pełny aktualny diff source/tests względem HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b60810a..81ad46e 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -2042,13 +2042,26 @@ def evaluate_package_import_order(
                         and not step.function_local
                         and not step.class_local
                     ):
+                        known_builtin = (
+                            _known_builtin_callable(step.symbol)
+                            if (
+                                _assume_frozen_dataclass_decoration
+                                and step.op == "FROM"
+                                and target == "builtins"
+                            )
+                            else None
+                        )
                         namespaces[module][step.binding] = (
-                            "\x00ASSUMED_EXTERNAL:"
-                            + target
-                            + (
-                                ":" + step.symbol
-                                if step.op == "FROM"
-                                else ""
+                            known_builtin
+                            if known_builtin is not None
+                            else (
+                                "\x00ASSUMED_EXTERNAL:"
+                                + target
+                                + (
+                                    ":" + step.symbol
+                                    if step.op == "FROM"
+                                    else ""
+                                )
                             )
                         )
                     frames[-1] = _advance_frame(frames[-1])
```
