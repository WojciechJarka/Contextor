# CONTEXTOR C16-B03-P1D3G10-R1 — DIRECT NAMESPACE BASE IMPORTS

## PREFLIGHT

- HEAD=cad207b6ffd97df8f7060e18b577728dccc4c737. The continuing G10 worktree already contained changes in package_graph_consistency.py, the new namespace test module, and walkthrough.md; these were preserved and extended.
- Contextor MCP first: revision=1063, canonical_state=fresh, workspace_sync=verified, structural DFS cycles=16, syntax errors=0, cycle_semantics freshness=stale. Symbol lineage resolved assess_package_graph_consistency to its canonical artifact; scenarios.analyze_cycle_scenarios remains the production consumer.
- Source inspection confirmed target("pkg.ns") is absent when only descendant pkg.ns.b is indexed, so G10's resolved-target parent classification did not admit the direct namespace base.

## IMPLEMENTATION

- Added a local missing_namespace_base classifier. It admits a missing base only when no direct indexed module or initializer exists, indexed descendants exist, and parent_classification validates every ancestor as REGULAR or NAMESPACE_CANDIDATE.
- Absolute ast.Import and ast.ImportFrom now record a structural namespace candidate for a qualifying missing base and continue checking imports. They add no expected hard edge to the unindexed base and do not infer an imported child or namespace attribute. Unresolved relative imports retain fail-closed MISSING_INDEXED_TARGET.
- The resolved-target branch now rejects a module with indexed descendants as AMBIGUOUS_PACKAGE_TARGET, preserving the module/package collision boundary. A resolved indexed initializer whose AST is missing returns MISSING_REQUIRED_INITIALIZER.
- Existing external diagnostics, namespace diagnostics, and final expected/hard_edges comparison remain. An invalid internal graph still returns GRAPH_SOURCE_IMPORT_MISMATCH before namespace results. package_model.py, scenarios.py, warning suppression, graph construction, and MODEL_PASS rules were not changed.

## TARGETED_TESTS

- Interpreter: repository CPython 3.15.2; PYTHONDONTWRITEBYTECODE=1. Command: .venv\Scripts\python.exe -B -m pytest -q -rs -p no:cacheprovider --basetemp C:\Temp\Contextor_G10_R1_pytest_tmp followed by the five named modules.
- Modules: tests/test_cycle_semantics_package_graph_namespace_boundary.py; tests/test_cycle_semantics_package_graph_external_boundary.py; tests/test_cycle_semantics_optional_child_scenarios.py; tests/test_cycle_semantics_package_model.py; tests/test_cycle_semantics_namespace_pep420_contract.py.
- Initial targeted run: 132 passed, 1 failed. The new missing-initializer-AST test exposed GRAPH_SOURCE_IMPORT_MISMATCH where the indexed initializer source was absent. The production guard was made explicit and the test now requires MISSING_REQUIRED_INITIALIZER.
- Final run after all source and test edits: 134 passed in 21.84s. The added cases cover direct import pkg.ns, direct from pkg.ns import b, top-level namespace, missing internal target, module/package collision, missing indexed initializer AST, external coexistence, no synthetic child hard edge, graph mismatch precedence, deterministic records, unchanged inputs, and optional SCC refusal of MODEL_PASS. The prior PEP 420 negative tests passed.
- No full pytest run.

## MCP_POST_CHANGE_AUDIT

- Read-only Contextor MCP after the final test edit: source and test module both at canonical_revision=1069, canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Syntax errors=0; structural DFS cycles=16, unchanged.
- cycle_semantics freshness remains stale. The focused tests and structural MCP count do not certify production runtime import resolution or fresh cycle-semantics generation.
- No production FULL, restart, update_file, warning suppression change, or manual commit.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_graph_consistency.py
- tests/test_cycle_semantics_package_graph_namespace_boundary.py
- walkthrough.md — report only, excluded from its own diff.

## FULL_DIFFS

Complete actual worktree diffs for both source/test files follow. These diffs include the preserved G10 worktree edits and the R1 continuation.
```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 609b50c..1bb649f 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -20,6 +20,7 @@ class PackageGraphConsistency:
     status: str
     reason: str | None
     unmodeled_external_imports: tuple[tuple[str, int, str, str], ...] = ()
+    unmodeled_namespace_parents: tuple[tuple[str, int, str, str], ...] = ()
 
 
 def assess_package_graph_consistency(
@@ -27,7 +28,7 @@ def assess_package_graph_consistency(
     sources: Mapping[str, ast.Module],
     evidence_source_modules: tuple[str, ...],
 ) -> PackageGraphConsistency:
-    """Check indexed imports and retain unresolved external candidates."""
+    """Check indexed imports and retain unmodeled import candidates."""
     def unknown(reason: str) -> PackageGraphConsistency:
         return PackageGraphConsistency("INDETERMINATE", reason)
 
@@ -36,6 +37,7 @@ def assess_package_graph_consistency(
     indexed = frozenset(hard_edges)
     indexed_roots = frozenset(name.split(".", 1)[0] for name in indexed)
     unmodeled_external_imports: list[tuple[str, int, str, str]] = []
+    unmodeled_namespace_parents: list[tuple[str, int, str, str]] = []
     if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
            for name in evidence_source_modules):
         return unknown("MISSING_INDEXED_TARGET")
@@ -43,14 +45,36 @@ def assess_package_graph_consistency(
     def target(name: str) -> str | None:
         return logical_to_indexed_module(name, indexed)
 
-    def regular_parents(name: str) -> bool:
+    def parent_classification(name: str) -> tuple[str, tuple[str, ...]]:
         parts = name.split(".")
-        return all(
-            target(".".join(parts[:length]))
-            == ".".join(parts[:length]) + ".__init__"
-            and ".".join(parts[:length]) + ".__init__" in sources
-            for length in range(1, len(parts))
-        )
+        namespace_parents: list[str] = []
+        for length in range(1, len(parts)):
+            parent = ".".join(parts[:length])
+            initializer = parent + ".__init__"
+            if initializer in indexed:
+                if parent in indexed or not isinstance(
+                    sources.get(initializer), ast.Module
+                ):
+                    return "INVALID", ()
+                continue
+            if parent in indexed or not any(
+                module.startswith(parent + ".") for module in indexed
+            ):
+                return "INVALID", ()
+            namespace_parents.append(parent)
+        if namespace_parents:
+            return "NAMESPACE_CANDIDATE", tuple(namespace_parents)
+        return "REGULAR", ()
+
+    def missing_namespace_base(name: str) -> tuple[str, ...] | None:
+        if name in indexed or name + ".__init__" in indexed:
+            return None
+        if not any(module.startswith(name + ".") for module in indexed):
+            return None
+        parent_state, namespace_parents = parent_classification(name)
+        if parent_state == "INVALID":
+            return None
+        return (*namespace_parents, name)
 
     def relative_base(module_id: str, level: int, named: str | None) -> str | None:
         logical = indexed_to_logical_module(module_id)
@@ -187,9 +211,9 @@ def assess_package_graph_consistency(
                         child_indexed is None
                         or child_indexed == initializer_id
                         or child_indexed not in sources
-                        or not regular_parents(
+                        or parent_classification(
                             child_logical
-                        )
+                        )[0] != "REGULAR"
                     ):
                         return False
 
@@ -301,15 +325,38 @@ def assess_package_graph_consistency(
                     resolved = target(alias.name)
                     if resolved is None:
                         if alias.name.split(".", 1)[0] in indexed_roots:
-                            return unknown("MISSING_INDEXED_TARGET")
+                            namespace_parents = missing_namespace_base(alias.name)
+                            if namespace_parents is None:
+                                return unknown("MISSING_INDEXED_TARGET")
+                            unmodeled_namespace_parents.extend(
+                                (module_id, node.lineno, alias.name, parent)
+                                for parent in namespace_parents
+                            )
+                            continue
                         unmodeled_external_imports.append(
                             (module_id, node.lineno, "import", alias.name)
                         )
                         continue
                     if resolved != alias.name and resolved != alias.name + ".__init__":
                         return unknown("AMBIGUOUS_PACKAGE_TARGET")
-                    if "." in alias.name and not regular_parents(alias.name):
+                    if resolved == alias.name and any(
+                        module.startswith(alias.name + ".")
+                        for module in indexed
+                    ):
+                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                    if resolved.endswith(".__init__") and not isinstance(
+                        sources.get(resolved), ast.Module
+                    ):
                         return unknown("MISSING_REQUIRED_INITIALIZER")
+                    parent_state, namespace_parents = parent_classification(
+                        alias.name
+                    )
+                    if parent_state == "INVALID":
+                        return unknown("MISSING_REQUIRED_INITIALIZER")
+                    unmodeled_namespace_parents.extend(
+                        (module_id, node.lineno, alias.name, parent)
+                        for parent in namespace_parents
+                    )
                     if (
                         resolved != module_id
                         and id(node) not in type_only_ids
@@ -329,13 +376,31 @@ def assess_package_graph_consistency(
                 resolved = target(base)
                 if resolved is None:
                     if node.level or base.split(".", 1)[0] in indexed_roots:
-                        return unknown("MISSING_INDEXED_TARGET")
+                        if node.level:
+                            return unknown("MISSING_INDEXED_TARGET")
+                        namespace_parents = missing_namespace_base(base)
+                        if namespace_parents is None:
+                            return unknown("MISSING_INDEXED_TARGET")
+                        unmodeled_namespace_parents.extend(
+                            (module_id, node.lineno, base, parent)
+                            for parent in namespace_parents
+                        )
+                        continue
                     unmodeled_external_imports.append(
                         (module_id, node.lineno, "from", base)
                     )
                     continue
-                if "." in base and not regular_parents(base):
+                if resolved == base and any(
+                    module.startswith(base + ".") for module in indexed
+                ):
+                    return unknown("AMBIGUOUS_PACKAGE_TARGET")
+                parent_state, namespace_parents = parent_classification(base)
+                if parent_state == "INVALID":
                     return unknown("MISSING_REQUIRED_INITIALIZER")
+                unmodeled_namespace_parents.extend(
+                    (module_id, node.lineno, base, parent)
+                    for parent in namespace_parents
+                )
                 if resolved != module_id:
                     expected.add(resolved)
                 if resolved.endswith(".__init__"):
@@ -404,6 +469,13 @@ def assess_package_graph_consistency(
         if expected != set(hard_edges[module_id]):
             return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
 
+    if unmodeled_namespace_parents:
+        return PackageGraphConsistency(
+            "INDETERMINATE",
+            "NAMESPACE_IMPORT_RESOLUTION_UNMODELED",
+            tuple(sorted(unmodeled_external_imports)),
+            tuple(sorted(unmodeled_namespace_parents)),
+        )
     if unmodeled_external_imports:
         return PackageGraphConsistency(
             "INDETERMINATE",
diff --git a/tests/test_cycle_semantics_package_graph_namespace_boundary.py b/tests/test_cycle_semantics_package_graph_namespace_boundary.py
new file mode 100644
index 0000000..4030704
--- /dev/null
+++ b/tests/test_cycle_semantics_package_graph_namespace_boundary.py
@@ -0,0 +1,267 @@
+"""Namespace package parents stay diagnostic during graph checks."""
+
+import ast
+from pathlib import Path
+
+from contextor.core.cycle_semantics.model_source_closure import (
+    compute_cycle_model_source_closures_with_optional_children,
+)
+from contextor.core.cycle_semantics.package_graph_consistency import (
+    assess_package_graph_consistency,
+)
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.symbol_engine.indexer import read_imports
+
+
+def _check(graph, source_texts, order=None):
+    trees = {name: ast.parse(text) for name, text in source_texts.items()}
+    selected = tuple(source_texts) if order is None else order
+    return assess_package_graph_consistency(graph, trees, selected)
+
+
+def _base(import_text="import pkg.ns.b\n"):
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.ns.b"},
+        "pkg.ns.b": set(),
+    }
+    source_texts = {
+        "pkg.__init__": "pass\n",
+        "pkg.a": import_text,
+        "pkg.ns.b": "value = 1\n",
+    }
+    return graph, source_texts
+
+
+def test_namespace_under_regular_package():
+    graph, sources = _base()
+    result = _check(graph, sources)
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
+    )
+    assert result.unmodeled_external_imports == ()
+
+
+def test_direct_import_of_namespace_base_has_no_synthetic_hard_edge():
+    graph, sources = _base("import pkg.ns\n")
+    graph["pkg.a"] = set()
+    result = _check(graph, sources)
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
+    )
+
+
+def test_direct_from_namespace_base_does_not_assume_child_binding():
+    graph, sources = _base("from pkg.ns import b\n")
+    graph["pkg.a"] = set()
+    result = _check(graph, sources)
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
+    )
+
+
+def test_direct_namespace_base_does_not_claim_child_hard_edge():
+    graph, sources = _base("from pkg.ns import b\n")
+    result = _check(graph, sources)
+    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_top_level_namespace_base_is_structural_candidate():
+    graph = {"consumer": set(), "ns.b": set()}
+    result = _check(
+        graph,
+        {"consumer": "import ns\n", "ns.b": "pass\n"},
+    )
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_namespace_parents == (
+        ("consumer", 1, "ns", "ns"),
+    )
+
+
+def test_import_between_namespace_modules():
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.ns.a": {"pkg.ns.b"},
+        "pkg.ns.b": set(),
+    }
+    result = _check(
+        graph,
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.ns.a": "import pkg.ns.b\n",
+            "pkg.ns.b": "pass\n",
+        },
+    )
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.ns.a", 1, "pkg.ns.b", "pkg.ns"),
+    )
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+
+
+def test_import_from_through_namespace():
+    graph, sources = _base("from pkg.ns.b import value\n")
+    result = _check(graph, sources)
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
+    )
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+
+
+def test_missing_indexed_initializer_is_invalid():
+    graph, sources = _base()
+    graph["pkg.ns.__init__"] = set()
+    result = _check(graph, sources)
+    assert result.reason == "MISSING_REQUIRED_INITIALIZER"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_direct_namespace_base_with_missing_initializer_ast_rejected():
+    graph, sources = _base("import pkg.ns\n")
+    graph["pkg.a"] = set()
+    graph["pkg.ns.__init__"] = set()
+    result = _check(graph, sources)
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "MISSING_REQUIRED_INITIALIZER"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_module_package_collision_is_invalid():
+    graph, sources = _base()
+    graph["pkg.ns"] = set()
+    sources["pkg.ns"] = "pass\n"
+    result = _check(graph, sources)
+    assert result.reason == "MISSING_REQUIRED_INITIALIZER"
+
+
+def test_direct_namespace_base_colliding_with_module_rejected():
+    graph, sources = _base("import pkg.ns\n")
+    graph["pkg.a"] = set()
+    graph["pkg.ns"] = set()
+    sources["pkg.ns"] = "pass\n"
+    result = _check(graph, sources)
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "AMBIGUOUS_PACKAGE_TARGET"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_missing_internal_target_is_not_namespace():
+    graph, sources = _base("import pkg.ns.missing\n")
+    graph["pkg.a"] = set()
+    result = _check(graph, sources)
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_namespace_does_not_hide_graph_source_mismatch():
+    graph, sources = _base()
+    graph["pkg.a"] = set()
+    result = _check(graph, sources)
+    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_namespace_and_external_records_are_both_retained():
+    graph, sources = _base("import os\nimport pkg.ns.b\n")
+    result = _check(graph, sources)
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "os"),
+    )
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
+    )
+
+
+def test_direct_namespace_base_preserves_external_record():
+    graph, sources = _base("import unknown_vendor_xyz\nimport pkg.ns\n")
+    graph["pkg.a"] = set()
+    result = _check(graph, sources)
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "unknown_vendor_xyz"),
+    )
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 2, "pkg.ns", "pkg.ns"),
+    )
+
+
+def test_records_are_deterministic_and_inputs_unchanged():
+    graph, sources = _base("import pkg.ns.b\nimport pkg.ns.b\n")
+    trees = {name: ast.parse(text) for name, text in sources.items()}
+    graph_before = {name: set(targets) for name, targets in graph.items()}
+    trees_before = dict(trees)
+    first = assess_package_graph_consistency(
+        graph, trees, tuple(trees)
+    )
+    second = assess_package_graph_consistency(
+        graph, trees, tuple(reversed(trees))
+    )
+    assert first == second
+    assert first.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
+        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
+    )
+    assert graph == graph_before
+    assert trees == trees_before
+
+
+def test_direct_namespace_records_are_deterministic():
+    graph, sources = _base("import pkg.ns\nimport pkg.ns\n")
+    graph["pkg.a"] = set()
+    trees = {name: ast.parse(text) for name, text in sources.items()}
+    before_graph = {name: set(targets) for name, targets in graph.items()}
+    before_trees = dict(trees)
+    first = assess_package_graph_consistency(
+        graph, trees, tuple(trees)
+    )
+    second = assess_package_graph_consistency(
+        graph, trees, tuple(reversed(trees))
+    )
+    assert first == second
+    assert first.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns", "pkg.ns"),
+        ("pkg.a", 2, "pkg.ns", "pkg.ns"),
+    )
+    assert graph == before_graph
+    assert trees == before_trees
+
+
+def test_optional_namespace_scc_never_model_passes():
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.ns.a": {"pkg.ns.b"},
+        "pkg.ns.b": {"pkg.ns.a"},
+    }
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.ns.a": ast.parse("import pkg.ns\nimport pkg.ns.b\n"),
+        "pkg.ns.b": ast.parse("import pkg.ns.a\n"),
+    }
+    imports = {}
+    for module_id, tree in trees.items():
+        extracted, error = read_imports(
+            Path(*module_id.split(".")).with_suffix(".py"),
+            tree=tree,
+        )
+        assert error is None
+        imports[module_id] = extracted
+    closures = compute_cycle_model_source_closures_with_optional_children(
+        graph, imports
+    )
+    report = analyze_cycle_scenarios(
+        graph,
+        trees,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=imports,
+        source_closures=closures,
+    )
+    component = report.components[0]
+    assert component.classification == "INDETERMINATE"
+    assert component.coverage == "NONE"
+    assert component.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
```

## FINAL_VERDICT

PASS — 134 targeted tests passed; direct namespace bases remain INDETERMINATE without synthetic hard edges or MODEL_PASS, and structural cycles remain 16. Production cycle_semantics freshness remains stale.
