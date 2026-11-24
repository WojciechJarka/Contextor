# P14-I1 — zachowanie tożsamości modułu przez IMPORT_NAME

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `9e9a6c3d35e2df710862ad6a4747cea1a1d612ef`. Contextor MCP przed zmianą: `initialization_model.py` i `test_cycle_semantics_initialization_model.py` na LIVE revision 1565, `canonical_state=fresh`, `workspace_sync=verified`; `cycle_semantics=stale`. `get_source_range(initialization_model.py:181-226)` potwierdził dokładną kotwicę w gałęzi IMPORT_NAME. `get_symbol_lineage` rozwiązał właściciela `evaluate_flat_import_order` (`A6320/1`), lecz jego narrow path ma `workspace_sync=unverified`; file-scoped stan potwierdza `get_module_context`.
- DIRECT_EVIDENCE: przed pracą `git status --short` pokazywał `M CHANGELOG.md`, `M audyt.txt`, `D issues.md`, `M walkthrough.md`; tych pierwszych trzech ścieżek nie zmieniano ani nie czytano `issues.md`. Zmiana jest bez operacji zapisu Git, restartów i FULL.

## FILES_CHANGED

- `contextor/core/cycle_semantics/initialization_model.py`
- `tests/test_cycle_semantics_initialization_model.py`
- `walkthrough.md` — raport, nie production/test diff.

## EXACT_IMPLEMENTATION

- CODE_PATH_PROVED: w `initialization_model.py:183-198` zachowano kontrolę brakującego symbolu i klasyfikację EARLY_BINDING_HAZARD/MISSING_EXPORT. Po udanym `IMPORT_NAME`, `:192-197` przenosi wyłącznie `aliases[target].get(step.symbol)`, czyli wcześniej znaną tożsamość modułu, albo usuwa stary alias bindingu. Nie dotknięto IMPORT_MODULE, BIND_CONSTANT, READ_ATTRIBUTE ani dataclasses ModelStep/ImportOrderAssessment. Tożsamość pochodzi z bieżącego stanu modułu źródłowego, nie ze zgodności pisowni (`:191-197`).
- DIRECT_EVIDENCE: `git diff --` dwóch zmienionych plików odpowiada pełnym diffom poniżej. Oba pliki przechodzą `ast.parse` w pamięci pod CPython 3.15.2. Contextor MCP `get_source_range:183-207` odczytał po zmianie dokładnie nową gałąź.

## SEMANTIC_EVIDENCE

- DIRECT_EVIDENCE z P14-D1, na dokładnym minimalnym przykładzie `a="from b import c as x\ny=x.value\n"`, `b="import c\n"`, `c="value=3\n"`: CPython 3.15.2 kończy sukcesem, x jest modułem c, y=3, a stary model zwracał UNKNOWN przy `x.value`. To luka dowodowa, którą ogranicza zmiana.
- CODE_PATH_PROVED + testy: dodatnie przypadki sprawdzają jedno i wiele przekazań tożsamości oraz CPython przez `_actual` (nowe testy `:203-233`). Negatywne sprawdzają, że stała usuwa alias, a zwykły binding nie zdobywa tożsamości tylko przez nazwę (`:236-258`). Piąty test sprawdza niezmieniony hazard brakującego `a_ref` przed READ_ATTRIBUTE (`:261-276`); nie wykonuje nowej gałęzi dla istniejącego symbolu, więc samodzielnie nie dowodzi hazardu późniejszego odczytu. Tę granicę należy zachować w interpretacji wyniku.
- INFERENCE: ponieważ alias celu jest unieważniany przez istniejące ścieżki BIND_CONSTANT/READ_ATTRIBUTE/IMPORT_NAME, transfer nie powinien zachowywać przestarzałej tożsamości w badanym ograniczonym modelu. Nie jest to dowód pełnej semantyki wszystkich obiektów modułu ani runtime safety.

## TARGETED_TESTS

- DIRECT_EVIDENCE: pięć nowych testów `-k` — `5 passed, 29 deselected in 0.98s`.
- DIRECT_EVIDENCE: pełny wskazany plik oraz `test_cycle_semantics_scenarios.py` i `test_cycle_semantics_evidence.py` — `129 passed in 5.65s`. Nie uruchomiono całego suite.

## MCP_POST_CHANGE

- DIRECT_EVIDENCE: watcher opublikował `initialization_model.py` jako `desktop_watcher UPDATED` na revision 1566 oraz plik testowy na revision 1567; `get_live_events(after_revision=1565)` podał ciągłą historię, `resync_required=false`. Nie użyto `update_file`.
- DIRECT_EVIDENCE: `get_module_context` obu plików po zmianie: `canonical_state=fresh`, `workspace_sync=verified`, LIVE revision 1567, provenance live. Rodziny module/graph/topology/artifact_consumption/cycles/lineage są fresh, `cycle_semantics=stale`. Świeże źródło/AST/graph nie dowodzi ponownego przeliczenia semantyki cykli ani adopcji zmienionego kodu przez już uruchomiony proces.
- DIRECT_EVIDENCE: zależności modelu obejmują `scenarios.py`, `evidence.py` oraz testy jako inbound hard dependencies; plik testowy ma outbound hard dependency do `initialization_model.py`. Oba pliki dają `AST_OK` przez izolowany CPython `ast.parse`. Kod runtime servera MCP nie był zmieniany; nie żądano restartu.

## FULL_DIFFS

### contextor/core/cycle_semantics/initialization_model.py — pełny ACTUAL_DIFF

```diff
diff --git a/contextor/core/cycle_semantics/initialization_model.py b/contextor/core/cycle_semantics/initialization_model.py
index 3bc2117..74242e1 100644
--- a/contextor/core/cycle_semantics/initialization_model.py
+++ b/contextor/core/cycle_semantics/initialization_model.py
@@ -190,7 +190,11 @@ def evaluate_flat_import_order(
                     events.append(ModelEvent(module, outcome, target, step.symbol))
                     return result(outcome, target, step.symbol)
                 bindings[module].add(step.binding)
-                aliases[module].pop(step.binding, None)
+                imported_module = aliases[target].get(step.symbol)
+                if imported_module is None:
+                    aliases[module].pop(step.binding, None)
+                else:
+                    aliases[module][step.binding] = imported_module
             events.append(ModelEvent(module, step.operation, target, step.symbol))
         elif step.operation == "BIND_CONSTANT":
             bindings[module].add(step.binding)
```

### tests/test_cycle_semantics_initialization_model.py — pełny ACTUAL_DIFF

```diff
diff --git a/tests/test_cycle_semantics_initialization_model.py b/tests/test_cycle_semantics_initialization_model.py
index 866beab..ffd0ce9 100644
--- a/tests/test_cycle_semantics_initialization_model.py
+++ b/tests/test_cycle_semantics_initialization_model.py
@@ -197,3 +197,76 @@ def test_single_attribute_flat_model_contract_after_nested_support(tmp_path):
         ("beta", "value"),
     ]
     assert _actual(tmp_path, sources, "alpha")
+
+
+def test_from_import_preserves_known_module_identity(tmp_path):
+    sources = {
+        "a": "from b import c as x\ny = x.value\n",
+        "b": "import c\n",
+        "c": "value = 3\n",
+    }
+    result = _assess(sources, "a")
+    assert result.outcome == "MODEL_PASS"
+    assert [
+        (event.target, event.symbol)
+        for event in result.events
+        if event.operation == "READ_ATTRIBUTE"
+    ] == [("c", "value")]
+    assert _actual(tmp_path, sources, "a")
+
+
+def test_from_import_identity_survives_multiple_hops(tmp_path):
+    sources = {
+        "a": "from b import x as y\nz = y.value\n",
+        "b": "from c import x\n",
+        "c": "import d as x\n",
+        "d": "value = 7\n",
+    }
+    result = _assess(sources, "a")
+    assert result.outcome == "MODEL_PASS"
+    assert [
+        (event.target, event.symbol)
+        for event in result.events
+        if event.operation == "READ_ATTRIBUTE"
+    ] == [("d", "value")]
+    assert _actual(tmp_path, sources, "a")
+
+
+def test_from_import_module_identity_invalidated_by_constant():
+    sources = {
+        "a": "from b import c as x\nx = 7\ny = x.value\n",
+        "b": "import c\n",
+        "c": "value = 3\n",
+    }
+    result = _assess(sources, "a")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "UNKNOWN", "x", "value"
+    )
+
+
+def test_from_import_ordinary_binding_does_not_gain_module_identity():
+    sources = {
+        "a": "from b import c as x\ny = x.value\n",
+        "b": "c = 3\n",
+        "c": "value = 7\n",
+    }
+    result = _assess(sources, "a")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "UNKNOWN", "x", "value"
+    )
+
+
+def test_from_import_module_identity_detects_later_hazard(tmp_path):
+    sources = {
+        "a": "import b\nvalue = 3\n",
+        "b": "from a import a_ref as x\ny = x.value\n",
+    }
+    # Brak a_ref zatrzymuje import nazwy przed READ_ATTRIBUTE.
+    result = _assess(sources, "a")
+    assert (result.outcome, result.target_module, result.symbol) == (
+        "EARLY_BINDING_HAZARD", "a", "a_ref"
+    )
+    assert not any(
+        event.operation == "READ_ATTRIBUTE"
+        for event in result.events
+    )
```

## FINAL_STATUS

- SOURCE/TEST change zgodne z podaną kotwicą i ograniczonym kontraktem; focused tests przechodzą, MCP potwierdza świeże źródła na rev 1567. Status: IMPLEMENTATION_VERIFIED_WITH_STALE_CYCLE_SEMANTICS. Nie zgłaszam FINAL PASS, ponieważ wymagana rodzina LIVE `cycle_semantics` pozostaje stale; świeżość źródeł nie jest dowodem jej przeliczenia ani runtime safety. Brak commit/push/staging/restart.
