# CONTEXTOR_C16_P15_EXTERNAL_IMPORT_EFFECTS_F1 — etap implementacji

## PREFLIGHT
Globalne `C:\Users\DafoO\.codex\AGENTS.md` odczytane i stosowane w bieżącym łańcuchu E1. HEAD `4cad8cb2a7dd9cbbf4d4d277ac1ca3cb3070bf49`; początkowy worktree `M walkthrough.md`, `?? 0.17.0`, bez diffów source/test. Contextor MCP `get_file_edit_context` przed zmianą: `package_graph_consistency.py` i `package_model.py` status available, per-file `workspace_sync=verified`, LIVE rev 1158, cycle_semantics stale. Exact anchors potwierdzone lokalnym `rg` i odczytem źródła. Kanoniczny owner zewnętrznego gate: `package_graph_consistency.assess_package_graph_consistency`; owner wykonania: `package_model.evaluate_package_import_order`; consumer `scenarios.analyze_cycle_scenarios`. Nie zmieniono indexera.

## CONFIRMED_ROOT_CAUSE
`typing_guard.py` rozpoznaje składnię markera, lecz nie ustala runtime resolution ani pasywności importu. Przed zmianą `package_graph_consistency.py:443-448` pomijał taki import w gate, a `package_model.py:737-754,1819-1835` podstawiał bezefektowy `TYPING_MARKER_IMPORT`. Poprzedni niezależny syntetyczny CPython 3.15.2 witness: `typing.py` wykonywał `raise RuntimeError`, podczas gdy zwykły package evaluator dawał `MODEL_PASS` i SCC `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. Zatem to zwykła luka autorytetu, a nie tylko ograniczenie conditional API.

## EXACT_IMPLEMENTATION
Usunięto pomijanie markera w `package_graph_consistency.py`. AST `Import` / `ImportFrom` przechodzi zwykły gate, z dotychczasowym provenance site. W `package_model.py` usunięto kompilację `TYPING_MARKER_IMPORT` i jego gałąź wykonania; underlying AST import jest teraz kompilowany i wykonywany według zwykłych reguł. Syntaktyczne rozpoznanie guard nadal służy do rozpoznania samego warunku, ale osiągnięty import `typing` zatrzymuje zwykły model `UNKNOWN` przed założeniem wartości markera. Conditional API, flagi i scope pozostały bez zmian.

## REMOVED_UNSOUND_SPECIAL_CASES
Usunięto import `recognize_typing_guard` z `package_graph_consistency.py`, gdy nie jest już tam używany. Nie usunięto mechanizmu syntaktycznego `typing_guard.py` ani jego kontraktu indexera. W `package_model.py` nadal jest syntaktyczne rozpoznanie guard w kompilatorze, ale nie ma już wykonawczej ścieżki gwarantowanego importu. Żadnej nowej allowlisty ani wyjątku dla `typing` nie dodano.

## REGRESSION_TESTS
Nowy `tests/test_cycle_semantics_external_import_authority.py` zawiera cztery celowane testy: (A) ordinary evaluator, graph consistency i SCC odrzucają osiągnięty marker oraz CPython uruchamia syntetyczny `typing.py` z wyjątkiem; (B) metamorficzny inny opaque import ma tę samą granicę; (C) niepowołana funkcja z importem zachowuje model-relative PASS bez założenia; (D) conditional API zachowuje `CONDITIONAL_MODEL_PASS` i assumption scope. `4 passed`. Starszy focused subset `package_graph_external_boundary.py`/`package_model.py -k 'external or typing'`: `39 passed, 195 deselected`.

Istniejący `tests/test_p1d3_package_cycle_integration.py -k 'typing_guard or d2b'`: `58 passed, 12 failed, 61 deselected`. Nie jest to wynik PASS. Osiem niepowodzeń bezpośrednio lub przez helper zakłada `CONSISTENT`, `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`, `PREPARED_UNPUBLISHED_NON_ATOMIC` albo marker event po osiągniętym `typing` import; to historyczne oczekiwania sprzeczne z niezależnym CPython witness. Pozostałe failures są kaskadami tych założeń w fixture/receipt paths; jeden test fałszuje nieistniejący już event markera. Wśród wykonanych były oznaczone `@pytest.mark.live` testy z izolowanym syntetycznym LIVE; nie dotknęły produkcyjnego LIVE repo. Nie zmieniono starych expectation mechanicznie. Wymagają osobnej świadomej migracji asercji z zachowaniem kontraktów indexera i strukturalnego grafu. Wskazane failing tests: `d2b3_name_typed_side_import`, `d2b3_attribute_typed_side_import`, `d2b3_forged_hard_graph_rejected`, `d2b_name_guard_inactive`, `d2b_attribute_guard_inactive`, `d2b_else_activates_import`, `d2b_else_reordered_safe`, `d2b_original_worker_prepares_v2`, `d2b_forged_marker_event_rejected`, `d2b_official_isolated_full_receipt`, `d2b2_active_import_dominates_type_only`, `d2b3_official_isolated_full_receipt`.

## INDEPENDENT_CPYTHON_ORACLE
Nowy test tworzy poza repo syntetyczne `pkg/__init__.py`, `pkg/a.py`, `pkg/b.py`, `typing.py`. `typing.py` zawiera `TYPE_CHECKING = False\nraise RuntimeError("typing import executed")\n`. CPython 3.15.2 uruchomiony świeżo z `-I -S`, `sys.path` ustawiony na ten katalog; exit != 0, stderr zawiera `RuntimeError: typing import executed`. To potwierdza, że import markera jest rzeczywiście wykonywany. Test nie dowodzi runtime safety dla innych środowisk.

## POST_CHANGE_INVARIANT_PROOF
CODE_PATH_PROVED dla sprawdzonego ordinary package path: import markera nie jest pomijany w `package_graph_consistency`; unresolved external trafia do `unmodeled_external_imports` i statusu INDETERMINATE, chyba że spełni lexical-deferred gate. Sam lexical gate nie daje PASS, tylko przechodzi do ordinary simulator w `scenarios.py:282-337`. `package_model.py` kompiluje marker jako zwykły import; jeśli jest osiągnięty i target nie należy do programów, `:1836-1902` zwraca UNKNOWN przy domyślnych flagach. `scenarios.py:355-358` wymaga wszystkich ordinary `MODEL_PASS`. Flat model `initialization_model.py:152-156` również zwraca UNKNOWN dla missing target. Conditional simulator zachowuje osobne scope i zewnętrzny outcome `CONDITIONAL_MODEL_PASS`. Dowód obejmuje te gałęzie źródłowe, nie wszelką semantykę CPython. Stare testy integracyjne pozostają nieprzeniesione, więc pełny kontrakt regresji nie jest zamknięty.

## MCP_POST_CHANGE_AUDIT
Contextor `get_live_events(after_revision=1158)` dał ciągłość `continuous`, bez resync: desktop_watcher `UPDATED` rev 1159 (`package_graph_consistency.py`), 1160 (`package_model.py`), 1161 (nowy test). `get_file_edit_context` po zmianie: oba production files per-file `workspace_sync=verified`, rev 1161, syntax `checked_and_none`, graph/topology/cycles fresh, cycle_semantics **stale**. `get_live_events` bieżąca warning view: structural 16, model_pass 0, active 16. Brak nieoczekiwanej zmiany liczby strukturalnych ścieżek względem preflight. To nie certyfikuje nowej semantyki w LIVE ani adopcji kodu przez MCP process. Nie wykonywano resync/FULL/restartu; kod serwera MCP nie zmieniony.

## REMAINING_UNVERIFIED
12 starych focused regressions nie przechodzi i wymaga semantycznej migracji; z tego powodu FINAL PASS zabroniony. Pełny suite celowo niewykonany. Canonical LIVE cycle_semantics pozostaje stale; runtime adoption, source/graph semantic parity i runtime-safety niecertyfikowane. Istniejące structural graph 16 jest fresh, lecz nie wystarcza do semantycznej certyfikacji. Nie ma dowodu rzeczywistej accepted receipt po zmianie.

## FILES_CHANGED
`contextor/core/cycle_semantics/package_graph_consistency.py`
`contextor/core/cycle_semantics/package_model.py`
`tests/test_cycle_semantics_external_import_authority.py`
`walkthrough.md` (raport; poza listą production/test/docs diffs).

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index b49eef3..e974797 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -10,7 +10,6 @@ from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .typing_guard import (
     _typing_guard_parent_initializers,
     _typing_guard_passive_initializer,
-    recognize_typing_guard,
     type_only_candidate_statement_ids,
 )
 
@@ -404,10 +403,6 @@ def assess_package_graph_consistency(
 
     for module_id in evidence_source_modules:
         expected: set[str] = set()
-        typing_guard = recognize_typing_guard(
-            sources[module_id],
-            indexed,
-        )
         type_only_ids = (
             type_only_candidate_statement_ids(
                 sources[module_id],
@@ -441,12 +436,6 @@ def assess_package_graph_consistency(
         )
 
         for node in ast.walk(sources[module_id]):
-            if (
-                typing_guard is not None
-                and node is typing_guard.marker_statement
-            ):
-                continue
-
             if isinstance(node, ast.Import):
                 for alias_ordinal, alias in enumerate(node.names):
                     if not all(part.isidentifier() for part in alias.name.split(".")):
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index d01ac09..16fb3f9 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -734,25 +734,6 @@ def _compile(
             # supported attribute/import operations.
             continue
 
-        if (
-            _depth == 0
-            and typing_guard is not None
-            and stmt is typing_guard.marker_statement
-        ):
-            steps.append(
-                _Step(
-                    "TYPING_MARKER_IMPORT",
-                    target="typing",
-                    symbol="TYPE_CHECKING",
-                    binding=(
-                        "TYPE_CHECKING"
-                        if typing_guard.form == "NAME"
-                        else "typing"
-                    ),
-                )
-            )
-            continue
-
         if isinstance(stmt, ast.Import):
             if getattr(stmt, "is_lazy", False):
                 return None
@@ -1816,24 +1797,7 @@ def evaluate_package_import_order(
 
         step = steps[index]
 
-        if step.op == "TYPING_MARKER_IMPORT":
-            if not step.binding:
-                return result("UNKNOWN")
-
-            namespaces[module][step.binding] = (
-                "\x00TYPING_MARKER:" + module + ":" + step.binding
-            )
-
-            events.append(
-                PackageModelEvent(
-                    module,
-                    "TYPING_MARKER_IMPORT",
-                    target="typing",
-                    symbol="TYPE_CHECKING",
-                )
-            )
-
-        elif step.op in {
+        if step.op in {
             "IMPORT",
             "FROM",
             "PREPARE_FROM_MEMBER",
```

```diff
diff --git a/tests/test_cycle_semantics_external_import_authority.py b/tests/test_cycle_semantics_external_import_authority.py
new file mode 100644
index 0000000..d177e9e
--- /dev/null
+++ b/tests/test_cycle_semantics_external_import_authority.py
@@ -0,0 +1,123 @@
+"""External import effects are not ordinary execution evidence."""
+
+import ast
+import subprocess
+import sys
+
+from contextor.core.cycle_semantics.namespace_path_model import SearchPortion
+from contextor.core.cycle_semantics.package_graph_consistency import (
+    assess_package_graph_consistency,
+)
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_conditional_namespace_import_order,
+    evaluate_package_import_order,
+)
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+
+
+def _cycle(import_line):
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.a": (
+            import_line
+            + "if False:\n    import pkg.b\n"
+            + "value = 1\nimport pkg.b\n"
+        ),
+        "pkg.b": "from pkg.a import value\n",
+    }
+    trees = {name: ast.parse(source) for name, source in sources.items()}
+    edges = {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+    }
+    return sources, trees, edges
+
+
+def test_reached_typing_import_is_not_ordinary_evidence(tmp_path):
+    sources, trees, edges = _cycle("from typing import TYPE_CHECKING\n")
+    ordinary = evaluate_package_import_order(trees, "pkg.a")
+    consistency = assess_package_graph_consistency(
+        edges, trees, tuple(sorted(trees)),
+    )
+    scenarios = analyze_cycle_scenarios(edges, trees)
+
+    assert ordinary.outcome == "UNKNOWN"
+    assert ordinary.reached_unmodeled_import.target == "typing"
+    assert ordinary.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert consistency.unmodeled_external_imports == (
+        ("pkg.a", 1, "from", "typing"),
+    )
+    assert scenarios.components[0].classification == "INDETERMINATE"
+
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_bytes(sources["pkg.__init__"].encode())
+    (package / "a.py").write_bytes(sources["pkg.a"].encode())
+    (package / "b.py").write_bytes(sources["pkg.b"].encode())
+    (tmp_path / "typing.py").write_bytes(
+        b'TYPE_CHECKING = False\nraise RuntimeError("typing import executed")\n'
+    )
+    run = subprocess.run(
+        [
+            sys.executable, "-I", "-S", "-c",
+            "import sys;sys.path.insert(0,sys.argv[1]);import pkg.a",
+            str(tmp_path),
+        ],
+        capture_output=True, text=True, timeout=10,
+    )
+    assert run.returncode != 0
+    assert "RuntimeError: typing import executed" in run.stderr
+
+
+def test_other_reached_external_import_has_same_boundary():
+    _, trees, edges = _cycle("import opaque_dependency\n")
+    ordinary = evaluate_package_import_order(trees, "pkg.a")
+    consistency = assess_package_graph_consistency(
+        edges, trees, tuple(sorted(trees)),
+    )
+    scenarios = analyze_cycle_scenarios(edges, trees)
+
+    assert ordinary.outcome == "UNKNOWN"
+    assert ordinary.reached_unmodeled_import.target == "opaque_dependency"
+    assert consistency.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert scenarios.components[0].classification == "INDETERMINATE"
+
+
+def test_unreached_external_import_keeps_restricted_pass():
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse(
+            "def later():\n    import opaque_dependency\nvalue = 1\n"
+        ),
+    }
+    ordinary = evaluate_package_import_order(trees, "pkg.a")
+
+    assert ordinary.outcome == "MODEL_PASS"
+    assert ordinary.reached_unmodeled_import is None
+    assert ordinary.assumed_external_imports == ()
+
+
+def test_conditional_external_assumption_stays_conditional():
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.ns.a": ast.parse("import opaque_dependency\nvalue = 1\n"),
+    }
+    roots = (SearchPortion(
+        "root", frozenset({"pkg/__init__.py", "pkg/ns/a.py"}),
+    ),)
+    result = evaluate_conditional_namespace_import_order(
+        trees, "pkg.ns.a", roots,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+    )
+
+    assert result.outcome == "CONDITIONAL_MODEL_PASS"
+    assert result.model_assessment.outcome == "MODEL_PASS"
+    assert result.model_assessment.evidence_scope == (
+        "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_ASSUMPTION_NOT_RUNTIME_PROOF"
+    )
+    assert result.model_assessment.assumed_external_imports[0].target == (
+        "opaque_dependency"
+    )
```

## FINAL_VERDICT
PARTIAL / NOT FINAL PASS. Potwierdzona luka w produkcyjnych gałęziach została usunięta i nowe testy przechodzą. 12 istniejących focused integration tests utrwala poprzednią, semantycznie nieuprawnioną akceptację i nie zostało jeszcze świadomie zmigrowanych. Zgodnie z `AGENTS.md` kończę ten istotny etap, pozostawiając dokładny stan i diff do przeglądu; oczekiwanie na `proceduj`.
