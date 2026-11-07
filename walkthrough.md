# C16-B03-P1D3G18-P2-P3

## HEAD_BEFORE/AFTER

`394858f0205237205adc2d728ecc9362d13f113d` before and after. Worktree was clean before implementation. No Git mutation.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_graph_consistency.py`
- `contextor/core/cycle_semantics/scenarios.py`
- `tests/test_cycle_semantics_package_graph_external_boundary.py`

`walkthrough.md` was overwritten as the report.

## CPYTHON_IDENTITY

Repository `.venv\Scripts\python.exe` is CPython 3.15.2. No interpreter switch.

## EXACT_IMPLEMENTATION

DIRECT_EVIDENCE: Appended `external_execution_gate` with default `NOT_ESTABLISHED`. The existing final external INDETERMINATE result now marks all-records deferred lexical placement as `LEXICALLY_DEFERRED_ONLY`, and other external placement as `OPAQUE_EXECUTION_POSSIBLE`. Namespace, CONSISTENT and early-failure results retain the default. The scenario gate admits only the exact source/graph-proved, full-cohort, no-namespace, all-deferred external case to the unchanged restricted evaluator. No evaluator, aggregation, graph or warning policy was edited. Appended the supplied scenario helper and eleven exact tests.

## TARGETED_TEST_RESULTS

The five specified modules: **179 passed in 32.68s**, exit code 0. `git diff --check` exited 0.

## SYNTHETIC_SCENARIO_RESULTS

CONTRACT_PROVED by the passing supplied assertions: an uncalled deferred external import can reach `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` through the existing evaluator; explicit calls, async invocation, decorators and dynamic defaults remain UNKNOWN/INDETERMINATE; eager external imports remain blocked with coverage NONE; internal graph mismatch retains empty early evidence. Lexical deferral alone is not a safety certificate.

## REAL_SCC_REPLAY

DIRECT_EVIDENCE: Read-only revision 1091 replay. Canonical production inventory 307 modules. SCC1: 44 members, closure 201, 605 external records and 605 scope records; primary lexical scopes MODULE_BODY 555, FUNCTION_BODY 24, METHOD_BODY 26. SCC2: 9 members, closure 221, 723 external and 723 scope records; MODULE_BODY 647, FUNCTION_BODY 32, METHOD_BODY 44. Both retain four namespace records, `external_execution_gate=NOT_ESTABLISHED`, consistency `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, scenario classification INDETERMINATE, coverage NONE, and zero entry assessments. The namespace branch remains independently blocking. Structural DFS cycles remain 16.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot and metadata-selected FileState agreed on revision 1091, state_id `20261106_195021`. Current SHA-256 matched FileState for all 221 selected files in the union of the two closures; zero missing or mismatched. SCC cohorts overlap.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP returned canonical revision 1091, canonical_state fresh, workspace_sync verified for all three modified modules, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0, and cycle_semantics stale. No production FULL, update_file or restart was performed.

## REMAINING_UNKNOWN_GATES

Real SCC namespace resolution and external import execution remain unmodeled. The current LIVE runtime code adoption of changed source was not certified; the read-only replay invoked current source under the repository Python. No optional /3 receipt or runtime safety claim was made.

## FULL_DIFFS

Complete actual Git diff follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 5c4e23c..1d58427 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -39,6 +39,7 @@ class PackageGraphConsistency:
     internal_graph_state: str = "NOT_PROVED"
     checked_source_modules: tuple[str, ...] = ()
     external_scope_records: tuple[ExternalImportScopeRecord, ...] = ()
+    external_execution_gate: str = "NOT_ESTABLISHED"
 
 
 def _external_import_scope_index(
@@ -655,6 +656,20 @@ def assess_package_graph_consistency(
         )
     )
 
+    external_effects_deferred_only = (
+        bool(unmodeled_external_imports)
+        and len(ordered_external_scopes)
+        == len(unmodeled_external_imports)
+        and all(
+            row.primary_scope in {
+                "FUNCTION_BODY",
+                "ASYNC_FUNCTION_BODY",
+                "METHOD_BODY",
+            }
+            for row in ordered_external_scopes
+        )
+    )
+
     checked_source_modules = tuple(sorted(evidence_source_modules))
     internal_graph_state = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
     if unmodeled_namespace_parents:
@@ -675,6 +690,11 @@ def assess_package_graph_consistency(
             internal_graph_state=internal_graph_state,
             checked_source_modules=checked_source_modules,
             external_scope_records=ordered_external_scopes,
+            external_execution_gate=(
+                "LEXICALLY_DEFERRED_ONLY"
+                if external_effects_deferred_only
+                else "OPAQUE_EXECUTION_POSSIBLE"
+            ),
         )
     return PackageGraphConsistency(
         "CONSISTENT",
diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
index 6f46286..86abc32 100644
--- a/contextor/core/cycle_semantics/scenarios.py
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -279,7 +279,35 @@ def analyze_cycle_scenarios(
             consistency = assess_package_graph_consistency(
                 hard_edges, sources, source_closure.evidence_source_modules,
             )
-            if consistency.status != "CONSISTENT":
+            deferred_external_only = (
+                consistency.status == "INDETERMINATE"
+                and consistency.reason
+                == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+                and consistency.internal_graph_state
+                == "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
+                and consistency.checked_source_modules
+                == tuple(sorted(
+                    source_closure.evidence_source_modules
+                ))
+                and consistency.external_execution_gate
+                == "LEXICALLY_DEFERRED_ONLY"
+                and bool(consistency.unmodeled_external_imports)
+                and not consistency.unmodeled_namespace_parents
+                and len(consistency.external_scope_records)
+                == len(consistency.unmodeled_external_imports)
+                and all(
+                    row.primary_scope in {
+                        "FUNCTION_BODY",
+                        "ASYNC_FUNCTION_BODY",
+                        "METHOD_BODY",
+                    }
+                    for row in consistency.external_scope_records
+                )
+            )
+            if (
+                consistency.status != "CONSISTENT"
+                and not deferred_external_only
+            ):
                 output.append(_component_result(
                     component, "INDETERMINATE", coverage="NONE",
                     reason=consistency.reason,
diff --git a/tests/test_cycle_semantics_package_graph_external_boundary.py b/tests/test_cycle_semantics_package_graph_external_boundary.py
index 089dbf8..87e0b03 100644
--- a/tests/test_cycle_semantics_package_graph_external_boundary.py
+++ b/tests/test_cycle_semantics_package_graph_external_boundary.py
@@ -335,3 +335,200 @@ def test_g18_p2_p2_unknown_stays_fail_closed():
 
     assert result.reason == "MISSING_INDEXED_TARGET"
     assert result.external_scope_records == ()
+
+
+def _g18_p2_p3_scenario(a_source, b_source="import pkg.a\n"):
+    graph = {
+        "pkg.__init__": set(),
+        "pkg.a": {"pkg.b"},
+        "pkg.b": {"pkg.a"},
+    }
+
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.a": ast.parse(a_source),
+        "pkg.b": ast.parse(b_source),
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
+    return report.components[0]
+
+
+def test_g18_p2_p3_deferred_gate_preserves_indeterminate():
+    result = _check(
+        "def unused():\n"
+        "    import os\n"
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert result.external_execution_gate == (
+        "LEXICALLY_DEFERRED_ONLY"
+    )
+    assert len(result.unmodeled_external_imports) == 1
+
+
+def test_g18_p2_p3_eager_gate_stays_blocking():
+    result = _check(
+        "import os\n"
+        "def unused():\n"
+        "    import json\n"
+    )
+
+    assert result.external_execution_gate == (
+        "OPAQUE_EXECUTION_POSSIBLE"
+    )
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+
+
+def test_g18_p2_p3_uncalled_external_function_model_pass():
+    component = _g18_p2_p3_scenario(
+        "import pkg.b\n"
+        "def unused():\n"
+        "    import os\n"
+    )
+
+    assert component.classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+    assert component.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+    assert all(
+        assessment.outcome == "MODEL_PASS"
+        for assessment in component.entry_assessments
+    )
+
+
+def test_g18_p2_p3_called_external_function_unknown():
+    component = _g18_p2_p3_scenario(
+        "def load():\n"
+        "    import os\n"
+        "load()\n"
+        "import pkg.b\n"
+    )
+
+    assert component.classification == "INDETERMINATE"
+    assert component.coverage != "NONE"
+    assert any(
+        assessment.outcome == "UNKNOWN"
+        for assessment in component.entry_assessments
+    )
+
+
+def test_g18_p2_p3_async_body_deferred():
+    component = _g18_p2_p3_scenario(
+        "import pkg.b\n"
+        "async def worker():\n"
+        "    import os\n"
+    )
+
+    assert component.classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+
+
+def test_g18_p2_p3_async_invocation_not_assumed_safe():
+    component = _g18_p2_p3_scenario(
+        "import pkg.b\n"
+        "async def worker():\n"
+        "    import os\n"
+        "worker()\n"
+    )
+
+    assert component.classification == "INDETERMINATE"
+    assert any(
+        assessment.outcome == "UNKNOWN"
+        for assessment in component.entry_assessments
+    )
+
+
+def test_g18_p2_p3_decorated_function_unknown():
+    component = _g18_p2_p3_scenario(
+        "import pkg.b\n"
+        "@decorator\n"
+        "def unused():\n"
+        "    import os\n"
+    )
+
+    assert component.classification == "INDETERMINATE"
+    assert any(
+        assessment.outcome == "UNKNOWN"
+        for assessment in component.entry_assessments
+    )
+
+
+def test_g18_p2_p3_dynamic_default_unknown():
+    component = _g18_p2_p3_scenario(
+        "import pkg.b\n"
+        "def unused(x=side_effect()):\n"
+        "    import os\n"
+    )
+
+    assert component.classification == "INDETERMINATE"
+    assert any(
+        assessment.outcome == "UNKNOWN"
+        for assessment in component.entry_assessments
+    )
+
+
+def test_g18_p2_p3_eager_external_scenario_still_blocked():
+    component = _g18_p2_p3_scenario(
+        "import os\n"
+        "import pkg.b\n"
+    )
+
+    assert component.classification == "INDETERMINATE"
+    assert component.coverage == "NONE"
+    assert component.reason == (
+        "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    )
+    assert component.entry_assessments == ()
+
+
+def test_g18_p2_p3_internal_graph_mismatch_stays_blocked():
+    result = _check(
+        "def unused():\n"
+        "    import os\n"
+        "import pkg.missing\n"
+    )
+
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.external_execution_gate == "NOT_ESTABLISHED"
+    assert result.external_scope_records == ()
+
+
+def test_g18_p2_p3_source_evidence_deterministic():
+    source = (
+        "def worker():\n"
+        "    import os\n"
+        "    from collections import deque\n"
+    )
+
+    first = _check(source)
+    second = _check(source)
+
+    assert first == second
+    assert first.external_execution_gate == (
+        "LEXICALLY_DEFERRED_ONLY"
+    )
```

## FINAL_VERDICT

PASS — exact implementation, 179 targeted tests passed, FileState-bound replay preserved both real SCC namespace gates and 16 structural cycles.
