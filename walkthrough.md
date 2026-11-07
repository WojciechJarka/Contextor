# CONTEXTOR C16-B03-P1D3G8 — OPAQUE EXTERNAL IMPORT BOUNDARY

## PREFLIGHT

- HEAD: 705b5e0db58afa8d73c8ca8f73e3e79be0cd5de6. Initial worktree contained only the pre-existing walkthrough.md change.
- Contextor MCP module context and symbol lineage identified assess_package_graph_consistency as the owner. The canonical consumer is scenarios.analyze_cycle_scenarios. MCP before editing: revision 1056, canonical_state=fresh, workspace_sync=verified, structural DFS cycles=16, syntax errors=0.
- Source inspection confirmed exact branches for ast.Import, ast.ImportFrom, relative imports, named children, initializer checks, and expected/hard_edges comparison. The existing package_model test requires UNKNOWN for pkg.__init__: import os.

## IMPLEMENTATION

- PackageGraphConsistency now carries immutable, default-empty unmodeled_external_imports records of (module_id, lineno, import_form, target_name).
- assess_package_graph_consistency derives top-level roots from the indexed hard_edges keys. Unresolved absolute Import and ImportFrom targets whose root is absent from that set are recorded and omitted from the internal expected-edge set. Unresolved imports under an indexed root and all unresolved relative imports retain MISSING_INDEXED_TARGET.
- The expected/hard_edges comparison still runs before the opaque result. A completed check with recorded candidates returns INDETERMINATE / EXTERNAL_IMPORT_EXECUTION_UNMODELED and a sorted tuple. Without candidates it returns CONSISTENT.
- No name whitelist, installed-package metadata, or runtime availability inference was added. package_model.py, scenarios.py, the structural graph, and warning suppression were not changed.

## TARGETED_TESTS

- CPython 3.15.2; command: .venv\Scripts\python.exe -B -m pytest -q -rs -p no:cacheprovider --basetemp C:\Temp\Contextor_G8_pytest_tmp, with PYTHONDONTWRITEBYTECODE=1.
- Modules: tests/test_cycle_semantics_package_graph_external_boundary.py; tests/test_cycle_semantics_optional_child_scenarios.py; tests/test_cycle_semantics_package_model.py.
- Result: 110 passed in 14.05s. The new tests cover standard-library imports, third-party and nonexistent candidates, missing indexed and relative targets, internal graph mismatch despite an opaque candidate, deterministic records, unchanged inputs, and optional SCC refusal of MODEL_PASS. The existing package_model UNKNOWN test passed.
- Full pytest was not run.

## MCP_POST_CHANGE_AUDIT

- Contextor MCP after edits: canonical_revision=1059; canonical_state=fresh; workspace_sync=verified; advisory_warning=null.
- Syntax errors=0, availability=fresh. Structural DFS cycles=16, availability=fresh, matching the 16-cycle baseline. model_pass_count=0 and active_warning_count=16. This audit is source/index freshness evidence, not a backend runtime adoption claim.
- No production FULL, restart, or update_file was invoked.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_graph_consistency.py
- tests/test_cycle_semantics_package_graph_external_boundary.py
- walkthrough.md — report only, excluded from its own diff.

## FULL_DIFFS

The following are complete actual diffs for the production and test files.
```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 8e63ccd..609b50c 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -19,6 +19,7 @@ from .typing_guard import (
 class PackageGraphConsistency:
     status: str
     reason: str | None
+    unmodeled_external_imports: tuple[tuple[str, int, str, str], ...] = ()
 
 
 def assess_package_graph_consistency(
@@ -26,13 +27,15 @@ def assess_package_graph_consistency(
     sources: Mapping[str, ast.Module],
     evidence_source_modules: tuple[str, ...],
 ) -> PackageGraphConsistency:
-    """Require exact indexed targets for every supported source import."""
+    """Check indexed imports and retain unresolved external candidates."""
     def unknown(reason: str) -> PackageGraphConsistency:
         return PackageGraphConsistency("INDETERMINATE", reason)
 
     if not isinstance(hard_edges, Mapping) or not isinstance(sources, Mapping):
         return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
     indexed = frozenset(hard_edges)
+    indexed_roots = frozenset(name.split(".", 1)[0] for name in indexed)
+    unmodeled_external_imports: list[tuple[str, int, str, str]] = []
     if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
            for name in evidence_source_modules):
         return unknown("MISSING_INDEXED_TARGET")
@@ -297,7 +300,12 @@ def assess_package_graph_consistency(
                         return unknown("UNSUPPORTED_IMPORT_FORM")
                     resolved = target(alias.name)
                     if resolved is None:
-                        return unknown("MISSING_INDEXED_TARGET")
+                        if alias.name.split(".", 1)[0] in indexed_roots:
+                            return unknown("MISSING_INDEXED_TARGET")
+                        unmodeled_external_imports.append(
+                            (module_id, node.lineno, "import", alias.name)
+                        )
+                        continue
                     if resolved != alias.name and resolved != alias.name + ".__init__":
                         return unknown("AMBIGUOUS_PACKAGE_TARGET")
                     if "." in alias.name and not regular_parents(alias.name):
@@ -320,7 +328,12 @@ def assess_package_graph_consistency(
                     return unknown("UNSUPPORTED_IMPORT_FORM")
                 resolved = target(base)
                 if resolved is None:
-                    return unknown("MISSING_INDEXED_TARGET")
+                    if node.level or base.split(".", 1)[0] in indexed_roots:
+                        return unknown("MISSING_INDEXED_TARGET")
+                    unmodeled_external_imports.append(
+                        (module_id, node.lineno, "from", base)
+                    )
+                    continue
                 if "." in base and not regular_parents(base):
                     return unknown("MISSING_REQUIRED_INITIALIZER")
                 if resolved != module_id:
@@ -391,4 +404,10 @@ def assess_package_graph_consistency(
         if expected != set(hard_edges[module_id]):
             return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
 
+    if unmodeled_external_imports:
+        return PackageGraphConsistency(
+            "INDETERMINATE",
+            "EXTERNAL_IMPORT_EXECUTION_UNMODELED",
+            tuple(sorted(unmodeled_external_imports)),
+        )
     return PackageGraphConsistency("CONSISTENT", None)
diff --git a/tests/test_cycle_semantics_package_graph_external_boundary.py b/tests/test_cycle_semantics_package_graph_external_boundary.py
new file mode 100644
index 0000000..73272f6
--- /dev/null
+++ b/tests/test_cycle_semantics_package_graph_external_boundary.py
@@ -0,0 +1,133 @@
+"""External imports remain opaque to the closed package cycle model."""
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
+def _check(source, *, edges=None):
+    graph = {"pkg.__init__": set(), "pkg.a": set()}
+    if edges is not None:
+        graph["pkg.a"] = set(edges)
+        graph["pkg.b"] = set()
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse(source),
+    }
+    if edges is not None:
+        trees["pkg.b"] = ast.parse("pass\n")
+    return assess_package_graph_consistency(
+        graph, trees, tuple(sorted(trees))
+    )
+
+
+def test_stdlib_import_is_opaque():
+    result = _check("import os\n")
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "os"),
+    )
+
+
+def test_stdlib_from_import_is_opaque():
+    result = _check("from collections import Counter\n")
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "from", "collections"),
+    )
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+
+
+def test_third_party_and_nonexistent_imports_are_equally_opaque():
+    result = _check(
+        "import orjson\nimport definitely_nonexistent_package_xyz\n"
+    )
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "orjson"),
+        ("pkg.a", 2, "import", "definitely_nonexistent_package_xyz"),
+    )
+    assert result.status == "INDETERMINATE"
+
+
+def test_missing_internal_target_still_fails_closed():
+    result = _check("import pkg.missing\n")
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.unmodeled_external_imports == ()
+
+
+def test_unresolved_relative_target_still_fails_closed():
+    result = _check("from .missing import thing\n")
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.unmodeled_external_imports == ()
+
+
+def test_external_import_does_not_hide_internal_graph_mismatch():
+    result = _check("import os\nimport pkg.b\n", edges=())
+    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert result.unmodeled_external_imports == ()
+
+
+def test_external_records_are_sorted_without_mutating_inputs():
+    graph = {"pkg.__init__": set(), "pkg.a": set()}
+    trees = {
+        "pkg.a": ast.parse("import zzz\nimport aaa\n"),
+        "pkg.__init__": ast.parse("pass\n"),
+    }
+    before_graph = {name: set(targets) for name, targets in graph.items()}
+    before_trees = dict(trees)
+    first = assess_package_graph_consistency(
+        graph, trees, ("pkg.a", "pkg.__init__")
+    )
+    second = assess_package_graph_consistency(
+        graph, trees, ("pkg.__init__", "pkg.a")
+    )
+    assert first == second
+    assert first.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "zzz"),
+        ("pkg.a", 2, "import", "aaa"),
+    )
+    assert graph == before_graph
+    assert trees == before_trees
+
+
+def test_optional_scc_with_external_import_never_model_passes():
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+    }
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse("import pkg.b\nimport os\n"),
+        "pkg.b": ast.parse("import pkg.a\n"),
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
+    assert component.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
```

## FINAL_VERDICT

PASS — 110 targeted tests passed; opaque external imports remain fail-closed, internal graph mismatch remains detectable, and MCP reports 16 structural cycles.
