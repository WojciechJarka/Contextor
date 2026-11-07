# C16-B03-P1D3G18-P2-P4

## HEAD_BEFORE/AFTER

`2612044b8b17826c252cdf014e182ca91debae65` before and after. Worktree initially clean; no Git mutation.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_graph_consistency.py`
- `tests/test_cycle_semantics_package_graph_namespace_boundary.py`

`walkthrough.md` was overwritten as this report.

## CPYTHON_IDENTITY

Repository `.venv\Scripts\python.exe`: CPython 3.15.2.

## EXACT_IMPLEMENTATION

DIRECT_EVIDENCE: The existing deferred-only predicate now feeds one `external_gate` value. The terminal namespace result retains this independent external lexical evidence; the terminal external result reuses the same value. Status, reason, scope records, graph validation, scenario admission, evaluator, warning policy and early-failure return were not edited. Appended seven supplied regression tests.

## TARGETED_TEST_RESULTS

Three specified modules: **66 passed in 6.20s**, exit code 0. `git diff --check` exited 0.

## SYNTHETIC_NEGATIVE_TESTS

CONTRACT_PROVED by passing assertions: namespace-only gives `NOT_ESTABLISHED`; namespace plus eager or mixed external imports gives `OPAQUE_EXECUTION_POSSIBLE`; namespace plus deferred external import gives `LEXICALLY_DEFERRED_ONLY`; graph mismatch discards partial evidence; results are deterministic; a namespace SCC remains INDETERMINATE with coverage NONE and no entry assessments. These gate labels do not establish execution safety.

## REAL_SCC_REPLAY

DIRECT_EVIDENCE: Read-only replay on revision 1093. SCC1: 44 members, 201 selected sources, 605 external records and 605 scope records; MODULE_BODY 555, FUNCTION_BODY 24, METHOD_BODY 26; 4 namespace records. SCC2: 9 members, 221 selected sources, 723 external and 723 scope records; MODULE_BODY 647, FUNCTION_BODY 32, METHOD_BODY 44; 4 namespace records. Both have zero missing/extra scope projection records, `external_execution_gate=OPAQUE_EXECUTION_POSSIBLE`, consistency `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, scenario classification INDETERMINATE, coverage NONE and 0 entry assessments. Structural DFS cycles remain 16. The cohorts overlap.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot and metadata-selected FileState agreed on revision 1093 and state_id `20261106_195021`. Current SHA-256 matched FileState for all 221 selected source files in the union; zero missing or mismatched. An earlier replay encountered a generation race and was rejected without using its result.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP reported revision 1093, canonical_state fresh, workspace_sync verified for both modified modules, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0, cycle_semantics stale. No FULL, update_file or restart was performed.

## REMAINING_UNKNOWN_GATES

Namespace resolution and external execution effects remain unmodeled for real SCCs. Active runtime adoption of modified code was not certified; local replay used current repository source. No MODEL_PASS or optional /3 receipt was claimed for the real SCCs.

## FULL_DIFFS

Complete actual Git diff follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 1d58427..b49eef3 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -670,6 +670,16 @@ def assess_package_graph_consistency(
         )
     )
 
+    external_gate = (
+        "NOT_ESTABLISHED"
+        if not unmodeled_external_imports
+        else (
+            "LEXICALLY_DEFERRED_ONLY"
+            if external_effects_deferred_only
+            else "OPAQUE_EXECUTION_POSSIBLE"
+        )
+    )
+
     checked_source_modules = tuple(sorted(evidence_source_modules))
     internal_graph_state = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
     if unmodeled_namespace_parents:
@@ -681,6 +691,7 @@ def assess_package_graph_consistency(
             internal_graph_state,
             checked_source_modules,
             external_scope_records=ordered_external_scopes,
+            external_execution_gate=external_gate,
         )
     if unmodeled_external_imports:
         return PackageGraphConsistency(
@@ -690,11 +701,7 @@ def assess_package_graph_consistency(
             internal_graph_state=internal_graph_state,
             checked_source_modules=checked_source_modules,
             external_scope_records=ordered_external_scopes,
-            external_execution_gate=(
-                "LEXICALLY_DEFERRED_ONLY"
-                if external_effects_deferred_only
-                else "OPAQUE_EXECUTION_POSSIBLE"
-            ),
+            external_execution_gate=external_gate,
         )
     return PackageGraphConsistency(
         "CONSISTENT",
diff --git a/tests/test_cycle_semantics_package_graph_namespace_boundary.py b/tests/test_cycle_semantics_package_graph_namespace_boundary.py
index 4030704..3f28f0d 100644
--- a/tests/test_cycle_semantics_package_graph_namespace_boundary.py
+++ b/tests/test_cycle_semantics_package_graph_namespace_boundary.py
@@ -265,3 +265,171 @@ def test_optional_namespace_scc_never_model_passes():
     assert component.classification == "INDETERMINATE"
     assert component.coverage == "NONE"
     assert component.reason == "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+
+
+def test_g18_p2_p4_namespace_only_gate():
+    graph, sources = _base()
+
+    result = _check(graph, sources)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    )
+    assert result.external_execution_gate == (
+        "NOT_ESTABLISHED"
+    )
+    assert result.unmodeled_external_imports == ()
+
+
+def test_g18_p2_p4_namespace_and_eager_external():
+    graph, sources = _base(
+        "import os\n"
+        "import pkg.ns.b\n"
+    )
+
+    result = _check(graph, sources)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    )
+    assert result.external_execution_gate == (
+        "OPAQUE_EXECUTION_POSSIBLE"
+    )
+    assert len(result.unmodeled_namespace_parents) == 1
+    assert len(result.unmodeled_external_imports) == 1
+    assert len(result.external_scope_records) == 1
+    assert result.external_scope_records[0].primary_scope == (
+        "MODULE_BODY"
+    )
+
+
+def test_g18_p2_p4_namespace_and_deferred_external():
+    graph, sources = _base(
+        "def unused():\n"
+        "    import os\n"
+        "import pkg.ns.b\n"
+    )
+
+    result = _check(graph, sources)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    )
+    assert result.external_execution_gate == (
+        "LEXICALLY_DEFERRED_ONLY"
+    )
+    assert len(result.unmodeled_namespace_parents) == 1
+    assert len(result.unmodeled_external_imports) == 1
+    assert result.external_scope_records[0].primary_scope == (
+        "FUNCTION_BODY"
+    )
+
+
+def test_g18_p2_p4_namespace_and_mixed_external():
+    graph, sources = _base(
+        "def unused():\n"
+        "    import os\n"
+        "import json\n"
+        "import pkg.ns.b\n"
+    )
+
+    result = _check(graph, sources)
+
+    assert result.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    )
+    assert result.external_execution_gate == (
+        "OPAQUE_EXECUTION_POSSIBLE"
+    )
+    assert len(result.unmodeled_external_imports) == 2
+    assert len(result.external_scope_records) == 2
+
+
+def test_g18_p2_p4_mismatch_rejects_partial_gates():
+    graph, sources = _base(
+        "import os\n"
+        "import pkg.ns.b\n"
+    )
+
+    graph["pkg.a"] = set()
+
+    result = _check(graph, sources)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert result.external_execution_gate == (
+        "NOT_ESTABLISHED"
+    )
+    assert result.external_scope_records == ()
+    assert result.unmodeled_external_imports == ()
+    assert result.unmodeled_namespace_parents == ()
+
+
+def test_g18_p2_p4_namespace_gate_determinism():
+    graph, sources = _base(
+        "def unused():\n"
+        "    import os\n"
+        "import json\n"
+        "import pkg.ns.b\n"
+    )
+
+    first = _check(graph, sources)
+    second = _check(graph, sources, tuple(reversed(sources)))
+
+    assert first == second
+
+
+def test_g18_p2_p4_namespace_scc_remains_blocked():
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.ns.a": {"pkg.ns.b"},
+        "pkg.ns.b": {"pkg.ns.a"},
+    }
+
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.ns.a": ast.parse(
+            "def unused():\n"
+            "    import os\n"
+            "import pkg.ns.b\n"
+        ),
+        "pkg.ns.b": ast.parse(
+            "import pkg.ns.a\n"
+        ),
+    }
+
+    imports = {}
+
+    for module_id, tree in trees.items():
+        extracted, error = read_imports(
+            Path(*module_id.split(".")).with_suffix(".py"),
+            tree=tree,
+        )
+        assert error is None
+        imports[module_id] = extracted
+
+    closures = compute_cycle_model_source_closures_with_optional_children(
+        graph, imports
+    )
+
+    report = analyze_cycle_scenarios(
+        graph,
+        trees,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=imports,
+        source_closures=closures,
+    )
+
+    assert len(report.components) == 1
+
+    component = report.components[0]
+
+    assert component.classification == "INDETERMINATE"
+    assert component.coverage == "NONE"
+    assert component.reason == (
+        "NAMESPACE_IMPORT_RESOLUTION_UNMODELED"
+    )
+    assert component.entry_assessments == ()
```

## FINAL_VERDICT

PASS — exact change, 66 targeted tests passed, both FileState-bound SCCs preserve namespace blocking and 16 structural cycles.
