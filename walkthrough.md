# CONTEXTOR C16-B03-P1D3G12

## IMPLEMENTATION

FILES_CHANGED: `contextor/core/cycle_semantics/package_graph_consistency.py`, `tests/test_cycle_semantics_package_graph_proof_boundary.py`. HEAD before change: `da8ee7732ba766ab3d0da0c4a7dee35b0fd92110`.

Added `internal_graph_state` (default `NOT_PROVED`) and `checked_source_modules` (default empty). The full graph proof is set only after all selected source modules pass the expected/hard_edges comparison. Earlier returns retain defaults. Existing status, reason, namespace/external diagnostics, and error precedence remain unchanged. Added focused proof-boundary tests.

## TARGETED_TESTS

Python 3.15.2, `-B -m pytest -q -rs -p no:cacheprovider`, external `--basetemp C:\Temp\Contextor_G12_pytest_tmp`, `PYTHONDONTWRITEBYTECODE=1`. Exactly the four requested modules were run: proof boundary, namespace boundary, external boundary, optional child scenarios. Result: **50 passed in 6.27s**, exit 0. No full suite.

## SCC1_REPLAY

DIRECT_EVIDENCE: canonical revision 1071, state_id `20261106_195021`; current FileState metadata matches. Of 221 selected files across both closures, 0 SHA-256 mismatches. SCC1: 44 members, 201 evidence source modules. Graph status `INDETERMINATE`, reason `NAMESPACE_IMPORT_RESOLUTION_UNMODELED`; `internal_graph_state=INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES`; checked modules exactly equal the 201 selected modules in sorted order. Namespace records: 4; opaque external records: 605. Scenario classification `INDETERMINATE`, coverage `NONE`, same reason, 0 entry assessments.

## SCC2_REPLAY

DIRECT_EVIDENCE: same revision and FileState binding. SCC2: 9 members, 221 evidence source modules. Graph status `INDETERMINATE`, reason `NAMESPACE_IMPORT_RESOLUTION_UNMODELED`; `internal_graph_state=INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES`; checked modules exactly equal the 221 selected modules in sorted order. Namespace records: 4; opaque external records: 723. Scenario classification `INDETERMINATE`, coverage `NONE`, same reason, 0 entry assessments. Snapshot has no `cycle_optional_source_publication` receipt. Metadata revision was 1071 before and after replay.

## PROOF_SCOPE

CODE_PATH_PROVED: the positive field asserts agreement between provided AST imports and indexed hard edges for the selected source cohort after all module comparisons. It does not establish LIVE source authenticity, runtime finder selection, initializer safety, external import availability, or MODEL_PASS. Both real SCCs remain fail-closed. The separately checked FileState SHA-256 match binds this replay to current canonical source fingerprints; retained `cycle_semantics` freshness is stale and is not represented as fresh semantic certification.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: read-only Contextor MCP `get_module_context` for production and new test modules at canonical revision 1071: `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning, syntax errors 0, structural DFS cycles 16 (fresh), active warning count 16, model pass count 0. `cycle_semantics=stale`. No production FULL, backend restart, `update_file`, warning suppression edit, or commit.

## FULL_DIFFS

Complete actual source/test diffs follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 1bb649f..4e1d4de 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -21,6 +21,8 @@ class PackageGraphConsistency:
     reason: str | None
     unmodeled_external_imports: tuple[tuple[str, int, str, str], ...] = ()
     unmodeled_namespace_parents: tuple[tuple[str, int, str, str], ...] = ()
+    internal_graph_state: str = "NOT_PROVED"
+    checked_source_modules: tuple[str, ...] = ()
 
 
 def assess_package_graph_consistency(
@@ -469,17 +471,28 @@ def assess_package_graph_consistency(
         if expected != set(hard_edges[module_id]):
             return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
 
+    checked_source_modules = tuple(sorted(evidence_source_modules))
+    internal_graph_state = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
     if unmodeled_namespace_parents:
         return PackageGraphConsistency(
             "INDETERMINATE",
             "NAMESPACE_IMPORT_RESOLUTION_UNMODELED",
             tuple(sorted(unmodeled_external_imports)),
             tuple(sorted(unmodeled_namespace_parents)),
+            internal_graph_state,
+            checked_source_modules,
         )
     if unmodeled_external_imports:
         return PackageGraphConsistency(
             "INDETERMINATE",
             "EXTERNAL_IMPORT_EXECUTION_UNMODELED",
             tuple(sorted(unmodeled_external_imports)),
+            internal_graph_state=internal_graph_state,
+            checked_source_modules=checked_source_modules,
         )
-    return PackageGraphConsistency("CONSISTENT", None)
+    return PackageGraphConsistency(
+        "CONSISTENT",
+        None,
+        internal_graph_state=internal_graph_state,
+        checked_source_modules=checked_source_modules,
+    )
diff --git a/tests/test_cycle_semantics_package_graph_proof_boundary.py b/tests/test_cycle_semantics_package_graph_proof_boundary.py
new file mode 100644
index 0000000..1f34801
--- /dev/null
+++ b/tests/test_cycle_semantics_package_graph_proof_boundary.py
@@ -0,0 +1,198 @@
+"""Internal graph proof is separate from import execution uncertainty."""
+
+import ast
+from pathlib import Path
+
+import pytest
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
+PROVED = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
+
+
+def _case(source, *, namespace=False, edge=True):
+    target = "pkg.ns.b" if namespace else "pkg.b"
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.a": {target} if edge else set(),
+        target: set(),
+    }
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse(source),
+        target: ast.parse("pass\n"),
+    }
+    return graph, trees
+
+
+def _assess(graph, trees, order=None):
+    return assess_package_graph_consistency(
+        graph,
+        trees,
+        tuple(trees) if order is None else order,
+    )
+
+
+def _not_proved(result, reason):
+    assert result.status == "INDETERMINATE"
+    assert result.reason == reason
+    assert result.internal_graph_state == "NOT_PROVED"
+    assert result.checked_source_modules == ()
+
+
+def test_closed_internal_graph_has_bounded_proof():
+    graph, trees = _case("import pkg.b\n")
+    result = _assess(graph, trees)
+    assert result.status == "CONSISTENT"
+    assert result.reason is None
+    assert result.internal_graph_state == PROVED
+    assert result.checked_source_modules == tuple(sorted(trees))
+    assert result.unmodeled_external_imports == ()
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_external_uncertainty_preserves_internal_graph_proof():
+    graph, trees = _case("import os\nimport pkg.b\n")
+    result = _assess(graph, trees)
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert result.internal_graph_state == PROVED
+    assert result.checked_source_modules == tuple(sorted(trees))
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "os"),
+    )
+
+
+def test_namespace_uncertainty_preserves_internal_graph_proof():
+    graph, trees = _case("import pkg.ns.b\n", namespace=True)
+    result = _assess(graph, trees)
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.internal_graph_state == PROVED
+    assert result.checked_source_modules == tuple(sorted(trees))
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 1, "pkg.ns.b", "pkg.ns"),
+    )
+
+
+def test_combined_uncertainty_preserves_both_diagnostics_and_proof():
+    graph, trees = _case(
+        "import os\nimport pkg.ns.b\n", namespace=True
+    )
+    result = _assess(graph, trees)
+    assert result.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    assert result.internal_graph_state == PROVED
+    assert result.checked_source_modules == tuple(sorted(trees))
+    assert result.unmodeled_external_imports == (
+        ("pkg.a", 1, "import", "os"),
+    )
+    assert result.unmodeled_namespace_parents == (
+        ("pkg.a", 2, "pkg.ns.b", "pkg.ns"),
+    )
+
+
+@pytest.mark.parametrize(
+    "source,namespace",
+    [
+        ("import os\nimport pkg.b\n", False),
+        ("import pkg.ns.b\n", True),
+    ],
+)
+def test_graph_mismatch_never_exposes_partial_proof(source, namespace):
+    graph, trees = _case(source, namespace=namespace, edge=False)
+    _not_proved(
+        _assess(graph, trees),
+        "GRAPH_SOURCE_IMPORT_MISMATCH",
+    )
+
+
+def test_missing_indexed_target_has_no_proof():
+    graph, trees = _case("import pkg.missing\n", edge=False)
+    _not_proved(_assess(graph, trees), "MISSING_INDEXED_TARGET")
+
+
+def test_missing_indexed_initializer_ast_has_no_proof():
+    graph, trees = _case("import pkg.ns\n", namespace=True, edge=False)
+    graph["pkg.ns.__init__"] = set()
+    _not_proved(_assess(graph, trees), "MISSING_REQUIRED_INITIALIZER")
+
+
+def test_unsupported_import_form_has_no_proof():
+    graph, trees = _case("from pkg import *\n", edge=False)
+    _not_proved(_assess(graph, trees), "UNSUPPORTED_IMPORT_FORM")
+
+
+def test_ambiguous_module_package_collision_has_no_proof():
+    graph, trees = _case("import pkg.ns\n", namespace=True, edge=False)
+    graph["pkg.ns"] = set()
+    trees["pkg.ns"] = ast.parse("pass\n")
+    _not_proved(_assess(graph, trees), "AMBIGUOUS_PACKAGE_TARGET")
+
+
+def test_proof_is_deterministic_and_inputs_are_unchanged():
+    graph, trees = _case(
+        "import os\nimport pkg.ns.b\n", namespace=True
+    )
+    graph_before = {name: set(targets) for name, targets in graph.items()}
+    trees_before = dict(trees)
+    first = _assess(graph, trees, tuple(trees))
+    second = _assess(graph, trees, tuple(reversed(trees)))
+    assert first == second
+    assert first.checked_source_modules == tuple(sorted(trees))
+    assert graph == graph_before
+    assert trees == trees_before
+    assert all(trees[name] is tree for name, tree in trees_before.items())
+
+
+@pytest.mark.parametrize("namespace", [False, True])
+def test_optional_scc_remains_indeterminate(namespace):
+    target = "pkg.ns.b" if namespace else "pkg.b"
+    source = (
+        "import pkg.ns.b\nimport os\n"
+        if namespace
+        else "import pkg.b\nimport os\n"
+    )
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.a": {target},
+        target: {"pkg.a"},
+    }
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse(source),
+        target: ast.parse("import pkg.a\n"),
+    }
+    imports = {}
+    for name, tree in trees.items():
+        extracted, error = read_imports(
+            Path(*name.split(".")).with_suffix(".py"),
+            tree=tree,
+        )
+        assert error is None
+        imports[name] = extracted
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
+    assert component.entry_assessments == ()
+    assert component.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+        if namespace
+        else "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    )
```

## FINAL_VERDICT

PASS — full indexed AST/graph proof is explicit and bounded; execution uncertainty remains INDETERMINATE; 50 targeted tests pass; both FileState-bound SCC replays preserve 4 namespace candidates and 16 structural cycles.
