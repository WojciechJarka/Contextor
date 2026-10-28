# CONTEXTOR P1D3-D2A-R2 — canonical reexport edge consistency repair

## 1. EXECUTIVE VERDICT
**GO** dla dokładnego R2. DIRECT_EVIDENCE: siedmioplikowy focused suite zakończył się `246 passed in 57.62s`, exit 0. Oficjalny izolowany FULL/receipt, wcześniej failing, przeszedł. Nie uruchomiono global pytest ani FULL na aktywnym Contextor.

## 2. INITIAL/FINAL HEAD
Initial i final: `2390fe4d485c8efc49038f1c944928783e68df1a`. Bez Git mutation.

## 3. INITIAL/FINAL WORKTREE
Initial: tylko `M walkthrough.md` (poprzedni raport). Final: `M contextor/core/cycle_semantics/package_graph_consistency.py`, `M tests/test_p1d3_package_cycle_integration.py`, `M walkthrough.md`. Unrelated files zachowane.

## 4. EXACT PRODUCTION DIFF
CODE_PATH_PROVED: jedyny production edit w `package_graph_consistency.py`: dodano literalny nested `initializer_direct_child_binding` po istniejącym `restricted_relative_initializer`; zastąpiono tylko końcowe dodanie optional child edge przez dokładne `suppressed_by_canonical_reexport` i warunek jego negacji. Existing D2A initializer validator pozostał bez zmiany. Final exact hard-edge equality pozostała bez zmiany. Pełny diff niżej.

## 5. CANONICAL REEXPORT RULE
CONTRACT_PROVED: oczekiwane optional child edge może zostać pominięte tylko gdy importer różni się od initializer, cały initializer przechodzi istniejącą restricted walidację, a jego bezpośredni top-level `from . import child` bez aliasu wiąże wskazaną nazwę. Helper nie przeszukuje nested `if` i nie wykonuje Python. `pkg.__init__ → pkg.a` pozostaje wymagane.

## 6. CANONICAL GRAPH
DIRECT_EVIDENCE: D2A-specific helper używa oryginalnego `index_repository`, canonical `materialize_reexport_facts_by_module`, `build_trie`, `detect_package_root` oraz `build_graph(..., reexport_facts_by_module=facts)` jak ścieżka Facade. D2A_ACTIVE_CHAIN hard graph: `pkg.__init__ → pkg.a`; `pkg.a → pkg.__init__, pkg.b`; `pkg.b → pkg.__init__`. Dokładnie cztery wewnętrzne hard edges. Nie dodano krawędzi w produkcyjnym graph resolver.

## 7. SCC MEMBERS
DIRECT_EVIDENCE: jeden SCC `('pkg.__init__','pkg.a','pkg.b')` w teście aktywnego łańcucha.

## 8. SOURCE CLOSURE
DIRECT_EVIDENCE: evidence closure `('pkg.__init__','pkg.a','pkg.b')`; canonical checker `CONSISTENT`.

## 9. FORGED EXTRA EDGE
DIRECT_EVIDENCE: nowy `test_p1d3_d2a_canonical_reexport_edge_rule` potwierdził `INDETERMINATE / GRAPH_SOURCE_IMPORT_MISMATCH` po dodaniu `pkg.b → pkg.a` do przekazanego grafu bez modyfikacji AST.

## 10. FORGED MISSING EDGE
DIRECT_EVIDENCE: ten sam test potwierdził `INDETERMINATE / GRAPH_SOURCE_IMPORT_MISMATCH` zarówno po usunięciu `pkg.a → pkg.b`, jak i po usunięciu obowiązkowego `pkg.__init__ → pkg.a`.

## 11. NESTED IMPORT NON-SUPPRESSION
DIRECT_EVIDENCE: nowy `test_p1d3_d2a_nested_initializer_import_does_not_suppress_child` potwierdził, że `if True: from . import a` w initializer nie tłumi canonical `pkg.b → pkg.a`; checker zwrócił `CONSISTENT`.

## 12. ORIGINAL D2A NEGATIVE MATRIX
DIRECT_EVIDENCE: wszystkie dziesięć istniejących wariantów N01–N10 wykonano na canonical graph helper i pozostały fail-closed bez pozytywnego modelowego/manifestowego awansu. Asercje negatywne nie były zmieniane.

## 13. HAZARD/SAFE REORDER
DIRECT_EVIDENCE: istniejący test D2A hazard/safe przeszedł na canonical graph, rozróżniając `MODEL_INTERNAL_EARLY_BINDING_HAZARD` od `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` przy tym samym grafie i różnych tokenach.

## 14. CPYTHON DIFFERENTIAL
DIRECT_EVIDENCE: istniejące D2A testy wykonały tylko syntetyczne fixture’y w oddzielnych podprocesach CPython. Aktywny łańcuch `pkg`, `pkg.a`, `pkg.b` zakończył się powodzeniem; hazard/safe zgadzały się z wynikami modelu. Nie wykonywano kodu aktywnego repozytorium jako analizowanego fixture'a.

## 15. P0 GENUINE EVIDENCE
DIRECT_EVIDENCE: istniejący aktywny test D2A potwierdził P0 `DECLARED_INPUTS_CONSISTENT` przy canonical czterokrawędziowym grafie.

## 16. P1B GENUINE REPLAY
DIRECT_EVIDENCE: istniejący aktywny test D2A potwierdził `BYTE_AST_CONSISTENT_NON_ATOMIC` dla original-worker bytes.

## 17. P1B FORGED REPLAY
DIRECT_EVIDENCE: istniejący D2A forged-event test przeszedł: po zmianie jednego import eventu i przeliczeniu caller-controlled token P0 pozostaje consistent, a P1B zwraca `MODEL_REPLAY_MISMATCH`.

## 18. ORIGINAL-WORKER MANIFEST
DIRECT_EVIDENCE: istniejący test przygotowania D2A przeszedł: `PREPARED_UNPUBLISHED_NON_ATOMIC`, manifest `cycle-source-manifest/2`, `REGULAR_PACKAGE`, pozytywna klasyfikacja i dokładne source signatures.

## 19. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: `test_p1d3_d2a_official_isolated_full_receipt` przeszedł bez zmiany. Izolowana preview ma `PREPARED_UNPUBLISHED_NON_ATOMIC`, opt-in publication zakończyło się `live_publish_status=success` na syntetycznej ścieżce.

## 20. RECEIPT V2
DIRECT_EVIDENCE: ten sam test potwierdził manifest `cycle-source-manifest/2`, receipt `cycle-prepared-co-publication/2`, positive `REGULAR_PACKAGE` component oraz `verify_co_published_cycle_manifest(...) == True`. Bez aktywnego LIVE adoption claim.

## 21. REGRESSION RESULTS
DIRECT_EVIDENCE: siedem wskazanych plików obejmowało B/C, R1, D1, D2A, flat-module, source closure, P0/P1B i receipt; wszystkie 246 testów przeszły. Global suite nie był uruchomiony.

## 22. EXACT COMMANDS/EXIT CODES
- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/package_graph_consistency.py` → exit 0, 1.57 s.
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py` → `246 passed in 57.62s`, exit 0, failed 0.
- `& .\.venv\Scripts\python.exe -m pytest --collect-only -q tests/test_p1d3_package_cycle_integration.py | Select-String 'test_p1d3_d2a_canonical_reexport_edge_rule|test_p1d3_d2a_nested_initializer_import_does_not_suppress_child'` → oba dokładne node IDs obecne, exit 0. Ponieważ cały plik był w przechodzącym focused run, oba zostały także wykonane.
- `git diff --check` → exit 0; tylko ostrzeżenia normalizacji LF/CRLF.

## 23. FILES_CHANGED
- `contextor/core/cycle_semantics/package_graph_consistency.py` (production).
- `tests/test_p1d3_package_cycle_integration.py` (tests).
- `walkthrough.md` (raport, wyłączony z production/test diff).

## 25. CONTRACT CONFLICTS
None. Contextor MCP przed zmianą potwierdził `assess_package_graph_consistency` w aktualnym pliku, lines 18–282, canonical revision 730, `workspace_sync=verified`; literalne anchory pasowały. CONTRACT_PROVED: R2 nie zmienia publicznych typów, wersji evidence/manifest/receipt, modelu wykonania ani semantics grafu. UNKNOWN: global suite oraz aktywnie załadowana wersja serwera; nie badano.

## 26. FINAL GO/PARTIAL/NO_GO
**GO** dla R2 w dozwolonym zakresie i izolowanej walidacji. STOP; oczekiwanie na osobne `proceduj`.

## 24. FULL ACTUAL_DIFF
Kompletny raw diff każdego task-changed production/test pliku względem początkowego HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 0df3218..790c857 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -220,6 +220,30 @@ def assess_package_graph_consistency(
 
         return valid_body(tree.body, 0)
 
+    def initializer_direct_child_binding(
+        initializer_id: str,
+        member: str,
+    ) -> bool:
+        if not restricted_relative_initializer(
+            initializer_id
+        ):
+            return False
+
+        initializer = sources.get(initializer_id)
+
+        if not isinstance(initializer, ast.Module):
+            return False
+
+        return any(
+            isinstance(statement, ast.ImportFrom)
+            and statement.level == 1
+            and statement.module is None
+            and len(statement.names) == 1
+            and statement.names[0].name == member
+            and statement.names[0].asname is None
+            for statement in initializer.body
+        )
+
     for module_id in evidence_source_modules:
         expected: set[str] = set()
         for node in ast.walk(sources[module_id]):
@@ -273,7 +297,19 @@ def assess_package_graph_consistency(
                         child = target(base + "." + alias.name)
                         if child is None:
                             return unknown("MISSING_INDEXED_TARGET")
-                        if child != module_id:
+
+                        suppressed_by_canonical_reexport = (
+                            module_id != resolved
+                            and initializer_direct_child_binding(
+                                resolved,
+                                alias.name,
+                            )
+                        )
+
+                        if (
+                            child != module_id
+                            and not suppressed_by_canonical_reexport
+                        ):
                             expected.add(child)
 
         if expected != set(hard_edges[module_id]):
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index de27f31..050ff01 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -36,6 +36,13 @@ from contextor.core.cycle_semantics.publication_binding import (
 from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
 from contextor.core.cycle_semantics.source_proof import assess_scc_source_bytes
 from contextor.core.graph.graph import build_graph
+from contextor.core.graph.resolver import (
+    build_trie,
+    detect_package_root,
+)
+from contextor.core.reference.shared import (
+    materialize_reexport_facts_by_module,
+)
 from contextor.core.source import parse_source_snapshot
 from contextor.core.symbol_engine.indexer import index_repository
 from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository
@@ -811,8 +818,35 @@ def test_p1d3_d1_official_isolated_full_receipt(
         assert calls == [root.resolve()]
 
 
+def _d2a_canonical_index_graph(root):
+    index = index_repository(str(root))
+
+    facts = materialize_reexport_facts_by_module(
+        index.modules,
+        index.reference_facts_by_module,
+    )
+
+    trie = build_trie(index.modules.keys())
+
+    package_root = detect_package_root(
+        index.modules,
+        trie,
+    )
+
+    graph = build_graph(
+        index.modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=facts,
+    )
+
+    return index, graph
+
+
 def _d2a_source_evidence(root):
-    index, graph = _indexed(root)
+    index, graph = _d2a_canonical_index_graph(
+        root
+    )
     _, captured = _captured(root, index, graph)
     parsed = {
         module: parse_source_snapshot(snapshot, module)
@@ -829,7 +863,7 @@ def test_p1d3_d2a_active_initializer_chain_verified(tmp_path, isolated_dirs):
     assert {name: set(targets) for name, targets in graph.hard_edges.items()} == {
         "pkg.__init__": {"pkg.a"},
         "pkg.a": {"pkg.__init__", "pkg.b"},
-        "pkg.b": {"pkg.__init__", "pkg.a"},
+        "pkg.b": {"pkg.__init__"},
     }
     closure = compute_cycle_model_source_closures(graph.hard_edges)
     assert len(closure) == 1
@@ -860,6 +894,138 @@ def test_p1d3_d2a_active_initializer_chain_verified(tmp_path, isolated_dirs):
         assert run_synthetic_import(root, entry).returncode == 0
 
 
+def test_p1d3_d2a_canonical_reexport_edge_rule(
+    tmp_path,
+    isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo",
+        D2A_ACTIVE_CHAIN,
+    )
+
+    index, graph = _d2a_canonical_index_graph(
+        root
+    )
+
+    trees = {
+        module: ast.parse(
+            (root / item.path).read_text(
+                encoding="utf-8"
+            )
+        )
+        for module, item in index.modules.items()
+    }
+
+    closure = compute_cycle_model_source_closures(
+        graph.hard_edges
+    )
+
+    assert len(closure) == 1
+
+    members = closure[0].evidence_source_modules
+
+    assert assess_package_graph_consistency(
+        graph.hard_edges,
+        trees,
+        members,
+    ).status == "CONSISTENT"
+
+    assert graph.hard_edges["pkg.__init__"] == {
+        "pkg.a"
+    }
+
+    assert graph.hard_edges["pkg.a"] == {
+        "pkg.__init__",
+        "pkg.b",
+    }
+
+    assert graph.hard_edges["pkg.b"] == {
+        "pkg.__init__"
+    }
+
+    with_extra = {
+        name: set(targets)
+        for name, targets in graph.hard_edges.items()
+    }
+
+    with_extra["pkg.b"].add("pkg.a")
+
+    result_extra = assess_package_graph_consistency(
+        with_extra,
+        trees,
+        members,
+    )
+
+    assert result_extra.status == "INDETERMINATE"
+    assert result_extra.reason == (
+        "GRAPH_SOURCE_IMPORT_MISMATCH"
+    )
+
+    with_missing = {
+        name: set(targets)
+        for name, targets in graph.hard_edges.items()
+    }
+
+    with_missing["pkg.a"].remove("pkg.b")
+
+    result_missing = assess_package_graph_consistency(
+        with_missing,
+        trees,
+        members,
+    )
+
+    assert result_missing.status == "INDETERMINATE"
+    assert result_missing.reason == (
+        "GRAPH_SOURCE_IMPORT_MISMATCH"
+    )
+
+    with_missing_initializer = {
+        name: set(targets)
+        for name, targets in graph.hard_edges.items()
+    }
+
+    with_missing_initializer[
+        "pkg.__init__"
+    ].remove("pkg.a")
+
+    result_initializer = (
+        assess_package_graph_consistency(
+            with_missing_initializer,
+            trees,
+            members,
+        )
+    )
+
+    assert result_initializer.status == (
+        "INDETERMINATE"
+    )
+
+    assert result_initializer.reason == (
+        "GRAPH_SOURCE_IMPORT_MISMATCH"
+    )
+
+
+def test_p1d3_d2a_nested_initializer_import_does_not_suppress_child(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", {
+        "pkg/__init__.py": "if True:\n    from . import a\n",
+        "pkg/a.py": "from . import b\n",
+        "pkg/b.py": "from . import a\n",
+    })
+    index, graph = _d2a_canonical_index_graph(root)
+    trees = {
+        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
+        for module, item in index.modules.items()
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert "pkg.a" in graph.hard_edges["pkg.b"]
+    assert assess_package_graph_consistency(
+        graph.hard_edges, trees, closure[0].evidence_source_modules,
+    ).status == "CONSISTENT"
+
+
 def test_p1d3_d2a_initializer_reordering(tmp_path, isolated_dirs):
     records = []
     for name, fixture in (("hazard", D2A_INITIALIZER_HAZARD),
@@ -924,7 +1090,7 @@ def test_p1d3_d2a_initializer_restrictions(tmp_path, isolated_dirs, initializer)
         "pkg/__init__.py": initializer,
         "pkg/a.py": "import pkg\nvalue = 1\n",
     })
-    index, graph = _indexed(root)
+    index, graph = _d2a_canonical_index_graph(root)
     trees = {
         name: ast.parse((root / module.path).read_text(encoding="utf-8"))
         for name, module in index.modules.items()
@@ -956,7 +1122,7 @@ def test_p1d3_d2a_literal_initializer_branches(tmp_path, isolated_dirs):
             "pkg/__init__.py": f"if {literal}:\n    from . import a\n",
             "pkg/a.py": "import pkg\n",
         })
-        index, graph = _indexed(root)
+        index, graph = _d2a_canonical_index_graph(root)
         trees = {
             module: ast.parse((root / item.path).read_text(encoding="utf-8"))
             for module, item in index.modules.items()
@@ -982,7 +1148,7 @@ def test_p1d3_d2a_literal_initializer_branches(tmp_path, isolated_dirs):
 
 def test_p1d3_d2a_rejects_forged_graph(tmp_path, isolated_dirs):
     root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
-    index, graph = _indexed(root)
+    index, graph = _d2a_canonical_index_graph(root)
     altered = {name: set(targets) for name, targets in graph.hard_edges.items()}
     altered["pkg.a"].remove("pkg.b")
     trees = {
```
