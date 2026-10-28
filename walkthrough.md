# CONTEXTOR P1D3-D2A — active regular-package initializers

## 1. EXECUTIVE VERDICT
**PARTIAL.** Literalny checker i izolowane testy źródłowe przeszły, lecz wymagana oficjalna izolowana ścieżka FULL/receipt nie przygotowała manifestu. DIRECT_EVIDENCE: `test_p1d3_d2a_official_isolated_full_receipt` otrzymał `UNAVAILABLE`, reason `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`, zamiast `PREPARED_UNPUBLISHED_NON_ATOMIC`. Nie rozszerzano zakresu produkcyjnego ani nie osłabiano asercji.

## 2. INITIAL AND FINAL HEAD/WORKTREE
- Initial HEAD: `9b77c31607f7d3a5b732f02e260402b7d858893d`.
- Final HEAD: `9b77c31607f7d3a5b732f02e260402b7d858893d`.
- Initial worktree: tylko `M walkthrough.md` (raport poprzedniego etapu).
- Final worktree: `M contextor/core/cycle_semantics/package_graph_consistency.py`, `M tests/test_p1d3_package_cycle_integration.py`, `M walkthrough.md`.
- Bez commit/push/reset/checkout/clean; brak aktywnego FULL/LIVE/MCP/desktop mutation.

## 3. EXACT PRODUCTION CHANGE
CODE_PATH_PROVED: jedyny zmieniony plik produkcyjny to `package_graph_consistency.py`. Po `relative_base` dodano literalny `restricted_relative_initializer`, który dopuszcza tylko Pass, literalny string, skalarne przypisanie poza nazwami dzieci, jednoelementowy `from . import child` oraz rekurencyjne literalne bool `if/else` do głębokości 31. W istniejącej bramce `ImportFrom` inert-only test zastąpiono wywołaniem tego helpera. Finalna równość `expected == hard_edges[module_id]`, bramki identity/target/regular-parent i reason strings pozostały. `package_model.py`, `scenarios.py`, graf, evidence, manifest i receipt nie były zmieniane.

## 4. RESTRICTED INITIALIZER VALIDATION
CONTRACT_PROVED: helper waliduje kształt AST obu gałęzi bool; nie interpretuje aktywacji. Zwraca bool tylko do `PackageGraphConsistency` (`CONSISTENT`/`INDETERMINATE`), nie twierdzi MODEL_PASS. Twarde krawędzie pozostają rozstrzygane przez istniejący graph resolver.

## 5. CANONICAL SCC COMPARISON
DIRECT_EVIDENCE: test `test_p1d3_d2a_active_initializer_chain_verified` użył realnego izolowanego index/capture i potwierdził dokładnie:

```text
pkg.__init__ -> pkg.a
pkg.a        -> pkg.__init__, pkg.b
pkg.b        -> pkg.__init__, pkg.a
```

Jeden SCC: `('pkg.__init__','pkg.a','pkg.b')`. Hazard/safe reordering miały ten sam hard graph i SCC `('pkg.__init__','pkg.a')`. Nie dodano krawędzi kanonicznych.

## 6. SOURCE CLOSURE
DIRECT_EVIDENCE: aktywny łańcuch miał evidence closure dokładnie `('pkg.__init__','pkg.a','pkg.b')`; checker zwrócił `CONSISTENT`. `test_p1d3_d2a_original_worker_prepares_v2` potwierdził source signatures dla tych trzech modułów.

## 7. ACTIVE-CHAIN RESULTS
DIRECT_EVIDENCE: trzy fresh entry assessments w scenariuszu miały `MODEL_PASS`; `model_kind=REGULAR_PACKAGE`, `classification=MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`, `coverage=COMPLETE_FRESH_MEMBER_ENTRIES`. P0: `DECLARED_INPUTS_CONSISTENT`. P1B: `BYTE_AST_CONSISTENT_NON_ATOMIC`. Kontrolowane osobne podprocesy CPython dla `pkg`, `pkg.a`, `pkg.b`: exit 0.

## 8. HAZARD AND SAFE REORDERING
DIRECT_EVIDENCE: dla `from . import a; value=1` scenariusz zwrócił `MODEL_INTERNAL_EARLY_BINDING_HAZARD`; modelowy event wskazywał logical `pkg` i `value`, odpowiadający indexed `pkg.__init__`. Dla `value=1; from . import a` zwrócił `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. Grafy były identyczne, tokeny dowodowe różne. Oba warianty przeszły P0/P1B. Osobne syntetyczne importy CPython `pkg`/`pkg.a` dla hazardu kończyły się błędem z `AttributeError`, a bezpieczne exit 0.

## 9. NEGATIVE MATRIX
DIRECT_EVIDENCE: 10 nowych wariantów N01–N10 przeszło w ukierunkowanym pytest: alias, multi-import, brak dziecka, zewnętrzny `os`, przypisanie do `a`, nieznany warunek, try/except, exec, `__getattr__`, klasa. Żaden wynik scenariusza nie otrzymał `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`; tam gdzie pozostał SCC i checker był wywołany, był `INDETERMINATE`; dla gotowego planu reindex nie otrzymano pozytywnego manifestu. Warianty z wcześniejszą bramką braku celu nie wymagają konkretnego reason.

## 10. BOOLEAN BRANCH TEST
DIRECT_EVIDENCE: `if True: from . import a` i `if False: from . import a` miały ten sam lexical hard edge oraz `CONSISTENT`; model użył `REGULAR_PACKAGE`. Fresh entry `pkg` w gałęzi False nie emitował `START_IMPORT pkg.a`, a True emitował. Kontrolowane CPython importy `pkg` zakończyły się exit 0.

## 11. CPYTHON DIFFERENTIAL
DIRECT_EVIDENCE: tylko fixture’y napisane do `tmp_path` przez `write_synthetic_repository` były uruchamiane przez `run_synthetic_import` w osobnych `-I -B` podprocesach. Wyniki opisano w punktach 7, 8 i 10. Nie uruchomiono kodu analizowanego aktywnego repozytorium.

## 12. P0/P1B RESULTS
DIRECT_EVIDENCE: aktywny łańcuch i hazard/safe dały P0 `DECLARED_INPUTS_CONSISTENT` oraz P1B `BYTE_AST_CONSISTENT_NON_ATOMIC` dla caller-supplied original-worker bytes. Te wyniki nie są aktywnym LIVE certification.

## 13. FORGED EVENT REPLAY
DIRECT_EVIDENCE: `test_p1d3_d2a_forged_event_rejected_by_p1b` zmienił jeden realny event FROM/FROM_REENTRANT_CHILD na `FORGED_D2A_IMPORT`, przeliczył caller-controlled component token, zachował bytes/fingerprints. P0 zwrócił `DECLARED_INPUTS_CONSISTENT`; P1B reason `MODEL_REPLAY_MISMATCH`. Z forged evidence nie mintowano pozytywnego manifestu.

## 14. ORIGINAL-WORKER MANIFEST V2
DIRECT_EVIDENCE: osobna realna izolowana ścieżka index/capture/`prepare_original_worker_cycle_manifest` zwróciła `PREPARED_UNPUBLISHED_NON_ATOMIC`; manifest `cycle-source-manifest/2`, `REGULAR_PACKAGE`, positive classification, dokładne trzy source signatures i niepusty model digest.

## 15. OFFICIAL ISOLATED FULL RECEIPT V2
DIRECT_EVIDENCE: istniejący `_official_live` harness i `ContextorFacade.analyze_project` na syntetycznym `D2A_ACTIVE_CHAIN` wykonały się, lecz `result.cycle_source_preparation_preview.status == 'UNAVAILABLE'`, reason `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`. Test zatrzymał się na tej asercji. Nie ma potwierdzenia v2 receipt ani successful opt-in publication dla tego fixture'a. CODE_PATH_PROVED: `original_worker_preparation.py` zwraca tę zewnętrzną przyczynę, gdy `prepare_cycle_source_manifest` nie dostarcza kompletnego digestu/komponentów. UNKNOWN: dokładny wewnętrzny reason P0/P1B tej ścieżki FULL; nie został wyeksponowany przez preview. Nie zmieniano innych plików, by wymusić wynik.

## 16. REGRESSION RESULTS
DIRECT_EVIDENCE: wymagany siedmioplikowy focused suite: 243 passed, 1 failed (wyłącznie nowy oficjalny D2A FULL test). Inert initializer, D1, BC/R1 i pozostałe istniejące przypadki przeszły w tym przebiegu.

## 17. COMMANDS AND EXIT CODES
- `& .\.venv\Scripts\python.exe -m py_compile contextor/core/cycle_semantics/package_graph_consistency.py` → exit 0, 1.02 s.
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_package_cycle_integration.py -k p1d3_d2a` → 16 passed, 1 failed, exit 1, 7.83 s.
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_package_cycle_integration.py::test_p1d3_d2a_official_isolated_full_receipt` → 1 failed, exit 1, 5.34 s; ujawniło exact reason `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`.
- `& .\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py` → 243 passed, 1 failed in 48.54 s, exit 1.
- `git diff --check` → exit 0; jedynie ostrzeżenia LF/CRLF.

## 18. FILES_CHANGED
- `contextor/core/cycle_semantics/package_graph_consistency.py` — production.
- `tests/test_p1d3_package_cycle_integration.py` — tests.
- `walkthrough.md` — raport, wyłączony z source/test diff.

## 20. UNSUPPORTED CASES
CONTRACT_PROVED: TYPE_CHECKING, try/except import recovery, alias/multi relative initializer imports, dynamic calls, external imports, class/function definitions, nieznane warunki, missing/ambiguous targets pozostają poza D2A. Nie ma twierdzenia o ogólnym Python runtime safety.

## 21. CONTRACT CONFLICTS
DIRECT_EVIDENCE: standalone original-worker preparation dla aktywnego łańcucha jest pozytywne, ale oficjalna izolowana FULL preview dla identycznego fixture'a jest `UNAVAILABLE / P1C0_SOURCE_EVIDENCE_UNAVAILABLE`. To blokuje wymagane G14 i FINAL GO. Nie rozstrzygnięto przyczyny wewnętrznej w tym etapie; wymagane byłoby dokładne source-evidence/check reason z oficjalnej ścieżki. W dozwolonym zakresie nie zmieniono produkcji poza checkerem.

## 22. FINAL GO / PARTIAL / NO_GO
**PARTIAL.** Stop po D2A. Bez D2B, bez aktywnego FULL/LIVE, bez commit/push. Oczekiwanie na osobne `proceduj`.

## 19. ACTUAL_DIFF / FULL_DIFF
Kompletny raw diff obu zmienionych production/test plików wobec początkowego HEAD:

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 69b67ad..0df3218 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -52,6 +52,174 @@ def assess_package_graph_consistency(
         prefix = ".".join(parts[:len(parts) - level + 1])
         return prefix + ("." + named if named else "")
 
+    def restricted_relative_initializer(
+        initializer_id: str,
+    ) -> bool:
+        tree = sources.get(initializer_id)
+
+        if (
+            not initializer_id.endswith(".__init__")
+            or not isinstance(tree, ast.Module)
+        ):
+            return False
+
+        package_name = initializer_id.removesuffix(
+            ".__init__"
+        )
+
+        child_names: set[str] = set()
+
+        for indexed_id in indexed:
+            prefix = package_name + "."
+
+            if not indexed_id.startswith(prefix):
+                continue
+
+            remainder = indexed_id[len(prefix):]
+
+            if remainder and remainder != "__init__":
+                child_names.add(
+                    remainder.split(".", 1)[0]
+                )
+
+        def valid_body(
+            statements: list[ast.stmt],
+            depth: int,
+        ) -> bool:
+            if depth >= 32:
+                return False
+
+            for statement in statements:
+                if isinstance(statement, ast.Pass):
+                    continue
+
+                if (
+                    isinstance(statement, ast.Expr)
+                    and isinstance(
+                        statement.value,
+                        ast.Constant,
+                    )
+                    and type(
+                        statement.value.value
+                    ) is str
+                ):
+                    continue
+
+                if isinstance(
+                    statement,
+                    ast.Assign,
+                ):
+                    if (
+                        len(statement.targets) != 1
+                        or not isinstance(
+                            statement.targets[0],
+                            ast.Name,
+                        )
+                        or not isinstance(
+                            statement.value,
+                            ast.Constant,
+                        )
+                        or type(
+                            statement.value.value
+                        ) not in {
+                            type(None),
+                            bool,
+                            int,
+                            float,
+                            complex,
+                            str,
+                            bytes,
+                        }
+                    ):
+                        return False
+
+                    binding = statement.targets[0].id
+
+                    if (
+                        not binding.isidentifier()
+                        or binding.startswith("__")
+                        or binding in child_names
+                    ):
+                        return False
+
+                    continue
+
+                if isinstance(
+                    statement,
+                    ast.ImportFrom,
+                ):
+                    if (
+                        statement.level != 1
+                        or statement.module is not None
+                        or len(statement.names) != 1
+                    ):
+                        return False
+
+                    alias = statement.names[0]
+
+                    if (
+                        not alias.name.isidentifier()
+                        or alias.name.startswith("__")
+                        or alias.asname is not None
+                    ):
+                        return False
+
+                    child_logical = (
+                        package_name
+                        + "."
+                        + alias.name
+                    )
+
+                    child_indexed = target(
+                        child_logical
+                    )
+
+                    if (
+                        child_indexed is None
+                        or child_indexed == initializer_id
+                        or child_indexed not in sources
+                        or not regular_parents(
+                            child_logical
+                        )
+                    ):
+                        return False
+
+                    continue
+
+                if isinstance(statement, ast.If):
+                    condition = statement.test
+
+                    if not (
+                        isinstance(
+                            condition,
+                            ast.Constant,
+                        )
+                        and type(
+                            condition.value
+                        ) is bool
+                    ):
+                        return False
+
+                    if not valid_body(
+                        statement.body,
+                        depth + 1,
+                    ):
+                        return False
+
+                    if not valid_body(
+                        statement.orelse,
+                        depth + 1,
+                    ):
+                        return False
+
+                    continue
+
+                return False
+
+            return True
+
+        return valid_body(tree.body, 0)
+
     for module_id in evidence_source_modules:
         expected: set[str] = set()
         for node in ast.walk(sources[module_id]):
@@ -95,16 +263,8 @@ def assess_package_graph_consistency(
                     initializer = sources.get(resolved)
                     if initializer is None:
                         return unknown("MISSING_REQUIRED_INITIALIZER")
-                    # Only an inert initializer proves that the imported
-                    # name cannot be a pre-existing package attribute.
-                    if any(
-                        not isinstance(statement, ast.Pass)
-                        and not (
-                            isinstance(statement, ast.Expr)
-                            and isinstance(statement.value, ast.Constant)
-                            and isinstance(statement.value.value, str)
-                        )
-                        for statement in initializer.body
+                    if not restricted_relative_initializer(
+                        resolved
                     ):
                         return unknown("AMBIGUOUS_PACKAGE_TARGET")
                     for alias in node.names:
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 151845b..de27f31 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -2,6 +2,7 @@
 
 from __future__ import annotations
 
+import ast
 import copy
 from dataclasses import replace
 
@@ -22,6 +23,9 @@ from contextor.core.cycle_semantics.model_identity import (
     logical_to_indexed_module,
 )
 from contextor.core.cycle_semantics.model_source_closure import compute_cycle_model_source_closures
+from contextor.core.cycle_semantics.package_graph_consistency import (
+    assess_package_graph_consistency,
+)
 from contextor.core.cycle_semantics.original_worker_preparation import prepare_original_worker_cycle_manifest
 from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
 from contextor.core.cycle_semantics.publication_binding import (
@@ -95,6 +99,37 @@ D1_INITIALIZER_SAFE = {
     "pkg/__init__.py": "value = 1\nif True:\n    import pkg.a\n",
 }
 
+D2A_ACTIVE_CHAIN = {
+    "pkg/__init__.py": (
+        "from . import a\n"
+    ),
+    "pkg/a.py": (
+        "from . import b\n"
+    ),
+    "pkg/b.py": (
+        "from . import a\n"
+    ),
+}
+
+D2A_INITIALIZER_HAZARD = {
+    "pkg/__init__.py": (
+        "from . import a\n"
+        "value = 1\n"
+    ),
+    "pkg/a.py": (
+        "import pkg\n"
+        "x = pkg.value\n"
+    ),
+}
+
+D2A_INITIALIZER_SAFE = {
+    **D2A_INITIALIZER_HAZARD,
+    "pkg/__init__.py": (
+        "value = 1\n"
+        "from . import a\n"
+    ),
+}
+
 
 @pytest.fixture(autouse=True)
 def _inline(monkeypatch):
@@ -774,3 +809,287 @@ def test_p1d3_d1_official_isolated_full_receipt(
         )
         assert result.live_publish_status == "success"
         assert calls == [root.resolve()]
+
+
+def _d2a_source_evidence(root):
+    index, graph = _indexed(root)
+    _, captured = _captured(root, index, graph)
+    parsed = {
+        module: parse_source_snapshot(snapshot, module)
+        for module, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    snapshot = _snapshot(root, index, graph)
+    return index, graph, captured, parsed, evidence, snapshot
+
+
+def test_p1d3_d2a_active_initializer_chain_verified(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
+    index, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+    assert {name: set(targets) for name, targets in graph.hard_edges.items()} == {
+        "pkg.__init__": {"pkg.a"},
+        "pkg.a": {"pkg.__init__", "pkg.b"},
+        "pkg.b": {"pkg.__init__", "pkg.a"},
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert closure[0].members == ("pkg.__init__", "pkg.a", "pkg.b")
+    assert closure[0].evidence_source_modules == closure[0].members
+    assert assess_package_graph_consistency(
+        graph.hard_edges,
+        {name: source.tree for name, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    ).status == "CONSISTENT"
+    scenario = evidence.scenarios.components[0]
+    assert scenario.model_kind == "REGULAR_PACKAGE"
+    assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert scenario.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+    assert len(scenario.entry_assessments) == 3
+    assert all(item.outcome == "MODEL_PASS" for item in scenario.entry_assessments)
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, evidence,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, evidence, captured.original_worker_source_snapshots,
+    )
+    assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    for entry in ("pkg", "pkg.a", "pkg.b"):
+        assert run_synthetic_import(root, entry).returncode == 0
+
+
+def test_p1d3_d2a_initializer_reordering(tmp_path, isolated_dirs):
+    records = []
+    for name, fixture in (("hazard", D2A_INITIALIZER_HAZARD),
+                          ("safe", D2A_INITIALIZER_SAFE)):
+        root = write_synthetic_repository(tmp_path / name, fixture)
+        _, graph, captured, parsed, evidence, snapshot = _d2a_source_evidence(root)
+        closure = compute_cycle_model_source_closures(graph.hard_edges)
+        assert closure[0].members == ("pkg.__init__", "pkg.a")
+        assert assess_package_graph_consistency(
+            graph.hard_edges,
+            {module: source.tree for module, source in parsed.items()},
+            closure[0].evidence_source_modules,
+        ).status == "CONSISTENT"
+        scenario = evidence.scenarios.components[0]
+        assert scenario.classification == (
+            "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+            if name == "hazard"
+            else "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        )
+        p0 = assess_index_bound_scc_models(
+            graph.hard_edges, captured.source_fingerprints_by_module,
+            snapshot, evidence,
+        )
+        assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+        p1b = assess_scc_source_bytes(
+            graph.hard_edges, captured.source_fingerprints_by_module,
+            snapshot, evidence, captured.original_worker_source_snapshots,
+        )
+        assert p1b[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+        for entry in ("pkg", "pkg.a"):
+            actual = run_synthetic_import(root, entry)
+            assert (actual.returncode == 0) is (name == "safe")
+            if name == "hazard":
+                assert "AttributeError" in actual.stderr
+        if name == "hazard":
+            assert any(
+                event.operation == "EARLY_BINDING_HAZARD"
+                and event.target == "pkg"
+                and event.symbol == "value"
+                for assessment in scenario.entry_assessments
+                for event in assessment.events
+            )
+        records.append((graph.hard_edges, evidence.components[0].evidence_token))
+    assert records[0][0] == records[1][0]
+    assert records[0][1] != records[1][1]
+
+
+@pytest.mark.parametrize("initializer", [
+    "from . import a as alias\n",
+    "from . import a, a\n",
+    "from . import missing\n",
+    "import os\nfrom . import a\n",
+    "from . import a\na = 1\n",
+    "if unknown:\n    from . import a\n",
+    "try:\n    from . import a\nexcept ImportError:\n    pass\n",
+    "from . import a\nexec('unexpected')\n",
+    "def __getattr__(name):\n    return None\nfrom . import a\n",
+    "from . import a\nclass C:\n    pass\n",
+])
+def test_p1d3_d2a_initializer_restrictions(tmp_path, isolated_dirs, initializer):
+    root = write_synthetic_repository(tmp_path / "repo", {
+        "pkg/__init__.py": initializer,
+        "pkg/a.py": "import pkg\nvalue = 1\n",
+    })
+    index, graph = _indexed(root)
+    trees = {
+        name: ast.parse((root / module.path).read_text(encoding="utf-8"))
+        for name, module in index.modules.items()
+    }
+    scenario = analyze_cycle_scenarios(graph.hard_edges, trees)
+    assert all(
+        item.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for item in scenario.components
+    )
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    if closure:
+        consistency = assess_package_graph_consistency(
+            graph.hard_edges, trees, closure[0].evidence_source_modules,
+        )
+        assert consistency.status == "INDETERMINATE"
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    if plan.status == "READY_FOR_REINDEX_NON_ATOMIC":
+        captured = index_repository(str(root), source_capture_module_ids=plan.selected_module_ids)
+        prepared = prepare_original_worker_cycle_manifest(
+            captured, graph.hard_edges, _snapshot(root, index, graph),
+        )
+        assert prepared.manifest is None
+
+
+def test_p1d3_d2a_literal_initializer_branches(tmp_path, isolated_dirs):
+    records = []
+    for name, literal in (("active", "True"), ("inactive", "False")):
+        root = write_synthetic_repository(tmp_path / name, {
+            "pkg/__init__.py": f"if {literal}:\n    from . import a\n",
+            "pkg/a.py": "import pkg\n",
+        })
+        index, graph = _indexed(root)
+        trees = {
+            module: ast.parse((root / item.path).read_text(encoding="utf-8"))
+            for module, item in index.modules.items()
+        }
+        assert graph.hard_edges["pkg.__init__"] == {"pkg.a"}
+        closure = compute_cycle_model_source_closures(graph.hard_edges)
+        assert assess_package_graph_consistency(
+            graph.hard_edges, trees, closure[0].evidence_source_modules,
+        ).status == "CONSISTENT"
+        scenario = analyze_cycle_scenarios(graph.hard_edges, trees).components[0]
+        assert scenario.model_kind == "REGULAR_PACKAGE"
+        assert scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        entry = next(item for item in scenario.entry_assessments if item.entry_module == "pkg")
+        starts_child = any(
+            event.operation == "START_IMPORT" and event.target == "pkg.a"
+            for event in entry.events
+        )
+        assert starts_child is (literal == "True")
+        assert run_synthetic_import(root, "pkg").returncode == 0
+        records.append(graph.hard_edges)
+    assert records[0] == records[1]
+
+
+def test_p1d3_d2a_rejects_forged_graph(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
+    index, graph = _indexed(root)
+    altered = {name: set(targets) for name, targets in graph.hard_edges.items()}
+    altered["pkg.a"].remove("pkg.b")
+    trees = {
+        module: ast.parse((root / item.path).read_text(encoding="utf-8"))
+        for module, item in index.modules.items()
+    }
+    result = analyze_cycle_scenarios(altered, trees)
+    assert all(
+        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        for component in result.components
+    )
+    assert all(
+        component.reason in {
+            "GRAPH_SOURCE_IMPORT_MISMATCH", "AMBIGUOUS_PACKAGE_TARGET",
+            "MISSING_INDEXED_TARGET", "MISSING_OR_INVALID_SOURCE",
+        }
+        for component in result.components
+    )
+    assert graph.hard_edges["pkg.a"] == {"pkg.__init__", "pkg.b"}
+
+
+def test_p1d3_d2a_original_worker_prepares_v2(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
+    _, graph, captured, _, _, snapshot = _d2a_source_evidence(root)
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, snapshot,
+    )
+    assert prepared.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert prepared.manifest.version == "cycle-source-manifest/2"
+    component = prepared.manifest.components[0]
+    assert component.model_kind == "REGULAR_PACKAGE"
+    assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert tuple(row[0] for row in component.source_signatures) == (
+        "pkg.__init__", "pkg.a", "pkg.b",
+    )
+    assert component.model_evidence_sha256
+
+
+def test_p1d3_d2a_forged_event_rejected_by_p1b(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
+    _, graph, captured, _, evidence, snapshot = _d2a_source_evidence(root)
+    scenario = evidence.scenarios.components[0]
+    assessment = scenario.entry_assessments[0]
+    event = next(item for item in assessment.events if item.operation in {"FROM", "FROM_REENTRANT_CHILD"})
+    forged_assessment = replace(
+        assessment,
+        events=tuple(
+            replace(item, operation="FORGED_D2A_IMPORT") if item is event else item
+            for item in assessment.events
+        ),
+    )
+    forged_scenario = replace(
+        scenario,
+        entry_assessments=(forged_assessment, *scenario.entry_assessments[1:]),
+    )
+    component = evidence.components[0]
+    subgraph = tuple(
+        (name, tuple(sorted(graph.hard_edges[name])))
+        for name in component.reachable_modules
+    )
+    forged_component = replace(
+        component,
+        evidence_token=_component_token(
+            component.members, subgraph, component.source_signatures, forged_scenario,
+        ),
+    )
+    forged = replace(
+        evidence,
+        components=(forged_component,),
+        scenarios=replace(evidence.scenarios, components=(forged_scenario,)),
+    )
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged,
+    )
+    assert p0[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges, captured.source_fingerprints_by_module,
+        snapshot, forged, captured.original_worker_source_snapshots,
+    )
+    assert p1b[0].reason == "MODEL_REPLAY_MISMATCH"
+
+
+@pytest.mark.live
+def test_p1d3_d2a_official_isolated_full_receipt(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2A_ACTIVE_CHAIN)
+    with _official_live(root, monkeypatch) as (client, server, identity, calls):
+        _, result = ContextorFacade.analyze_project(
+            str(root), cycle_source_preparation_preview=True,
+            cycle_source_publication_opt_in=True,
+        )
+        assert result.cycle_source_preparation_preview.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        ), result.cycle_source_preparation_preview.reason
+        state, metadata = _persisted(root)
+        receipt = state.cycle_source_publication
+        assert receipt.version == PUBLICATION_BINDING_VERSION
+        assert receipt.prepared_manifest.version == MANIFEST_VERSION
+        component = receipt.prepared_manifest.components[0]
+        assert component.model_kind == "REGULAR_PACKAGE"
+        assert component.model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        assert verify_co_published_cycle_manifest(
+            state, revision=metadata.revision,
+            state_id=metadata.state_id, repo_id=metadata.repo_id,
+            root_path=metadata.root_path,
+        )
+        assert result.live_publish_status == "success"
+        assert calls == [root.resolve()]
```
