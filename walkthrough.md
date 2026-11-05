# CONTEXTOR C16-B03-P1D1

## PREFLIGHT

Local HEAD 416f9626f741974d04dfb0bda36b8c6762960b36. Initial worktree had only modified walkthrough.md. Contextor MCP preflight: scenarios and model_source_closure workspace_sync=verified at canonical revision 1003; structural DFS path count 16; cycle_semantics=stale. Exact source anchors matched supplied patch; new test path did not exist.

## EXACT_CHANGE

Applied the supplied literal patch to contextor/core/cycle_semantics/scenarios.py and added tests/test_cycle_semantics_optional_child_scenarios.py using direct apply_patch edits. HARD_ONLY remains default. Optional mode validates supplied indexed import domain and per-SCC closures against the P1A planner; invalid identity returns INDETERMINATE with OPTIONAL_COHORT_IDENTITY_MISMATCH. Optional report/component evidence scopes are distinct and diagnostic only. No evidence, source proof, manifest, publication, graph, version or warning code changed.

## TARGETED_PYTEST_RESULTS

- New optional scenarios file: 11 passed.
- Existing scenarios, P1A, P1C0 and selected P0 regressions: 61 passed, 119 deselected.
- CPython 3.15.2 via .venv, -B -q -rs -p no:cacheprovider; --basetemp=C:\Temp\Contextor_C16_P1D1_pytest_tmp outside repo.
- No full suite.

## MCP_POST_CHANGE_AUDIT

Initial post-edit MCP query of scenarios at revision 1004 returned workspace_sync=unverified with generation proof advisory while indexing was in progress. At revision 1005, both scenarios and the new test module report canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Structural DFS path count remains 16. cycle_semantics is stale; loaded backend code adoption and production optional model certification are not established. No FULL, update_file or restart.

## FILES_CHANGED

- contextor/core/cycle_semantics/scenarios.py
- tests/test_cycle_semantics_optional_child_scenarios.py

walkthrough.md was overwritten as report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
index 6dadb47..6f46286 100644
--- a/contextor/core/cycle_semantics/scenarios.py
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -7,7 +7,7 @@ from __future__ import annotations
 
 import ast
 from collections.abc import Mapping
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 
 from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
 from .package_model import (
@@ -15,7 +15,11 @@ from .package_model import (
     _PackageSourceSession,
     evaluate_package_import_order,
 )
-from .model_source_closure import compute_cycle_model_source_closures
+from .model_source_closure import (
+    CycleModelSourceClosure,
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
 from .model_identity import indexed_to_logical_module, logical_to_indexed_module
 from .package_graph_consistency import assess_package_graph_consistency
 from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycle_topology
@@ -103,6 +107,11 @@ def _component_result(
 def analyze_cycle_scenarios(
     hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
     modules: Mapping[str, ast.AST],
+    *,
+    source_selection: str = "HARD_ONLY",
+    indexed_imports_by_module: Mapping[str, object] | None = None,
+    package_root: str | None = None,
+    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
 ) -> CycleScenarioReport:
     """Analyze every fresh entry module of each cyclic SCC, without executing code.
 
@@ -113,13 +122,84 @@ def analyze_cycle_scenarios(
     if not isinstance(modules, Mapping):
         raise TypeError("modules must be a mapping")
 
+    if source_selection not in ("HARD_ONLY", "OPTIONAL_NAMED_CHILDREN"):
+        raise ValueError("SOURCE_SELECTION_INVALID")
+
+    if source_selection == "HARD_ONLY" and (
+        indexed_imports_by_module is not None
+        or package_root is not None
+        or source_closures is not None
+    ):
+        raise ValueError("HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED")
+
+    def report(
+        components: tuple[CycleComponentScenarios, ...],
+    ) -> CycleScenarioReport:
+        if source_selection == "HARD_ONLY":
+            return CycleScenarioReport(topology, components)
+        return CycleScenarioReport(
+            topology=topology,
+            components=tuple(
+                replace(
+                    component,
+                    evidence_scope=(
+                        "CLOSED_REGULAR_PACKAGE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
+                        if component.model_kind == "REGULAR_PACKAGE"
+                        else "CLOSED_FLAT_MODULE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
+                    ),
+                )
+                for component in components
+            ),
+            evidence_scope=(
+                "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+            ),
+        )
+
     adjacency = {name: frozenset(targets) for name, targets in hard_edges.items()}
     for targets in tuple(adjacency.values()):
         for target in targets:
             adjacency.setdefault(target, frozenset())
 
     output: list[CycleComponentScenarios] = []
-    closures = compute_cycle_model_source_closures(hard_edges)
+    if source_selection == "HARD_ONLY":
+        closures = compute_cycle_model_source_closures(hard_edges)
+    else:
+        try:
+            if (
+                not isinstance(indexed_imports_by_module, Mapping)
+                or type(source_closures) is not tuple
+                or any(type(row) is not CycleModelSourceClosure
+                       for row in source_closures)
+            ):
+                raise ValueError("Invalid optional cohort input")
+            expected = compute_cycle_model_source_closures_with_optional_children(
+                hard_edges,
+                indexed_imports_by_module,
+                package_root=package_root,
+            )
+            if (
+                source_closures != expected
+                or len(expected) != len(topology.cyclic_components)
+                or any(
+                    row.members != component.members
+                    for row, component in zip(
+                        expected, topology.cyclic_components
+                    )
+                )
+            ):
+                raise ValueError("Optional cohort identity mismatch")
+            closures = expected
+        except (TypeError, ValueError, AttributeError):
+            return report(tuple(
+                _component_result(
+                    component,
+                    "INDETERMINATE",
+                    coverage="NONE",
+                    reason="OPTIONAL_COHORT_IDENTITY_MISMATCH",
+                )
+                for component in topology.cyclic_components
+            ))
+
     for component, source_closure in zip(topology.cyclic_components, closures):
         if len(component.members) > MAX_COMPONENT_ENTRIES:
             output.append(_component_result(
@@ -267,4 +347,4 @@ def analyze_cycle_scenarios(
             model_kind=model_kind,
         ))
 
-    return CycleScenarioReport(topology, tuple(output))
+    return report(tuple(output))
diff --git a/tests/test_cycle_semantics_optional_child_scenarios.py b/tests/test_cycle_semantics_optional_child_scenarios.py
new file mode 100644
index 0000000..9b94d3a
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_scenarios.py
@@ -0,0 +1,278 @@
+"""P1D1: optional scenario source closure is diagnostic, not certified."""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.model_source_closure import (
+    compute_cycle_model_source_closures,
+    compute_cycle_model_source_closures_with_optional_children,
+)
+from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.resolver import build_trie, detect_package_root
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
+from contextor.core.symbol_engine.indexer import index_repository
+from tests.cycle_semantics_lab import write_synthetic_repository
+
+
+@pytest.fixture(autouse=True)
+def _inline(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+FILES = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": "import pkg.b\nfrom pkg import child\n",
+    "pkg/b.py": "import pkg.a\n",
+    "pkg/child.py": "pass\n",
+}
+
+
+def _case(tmp_path, files=None):
+    root = tmp_path / "repo"
+    write_synthetic_repository(root, FILES if files is None else files)
+    index = index_repository(str(root))
+    trie = build_trie(index.modules)
+    package_root = detect_package_root(index.modules, trie)
+    reexports = materialize_reexport_facts_by_module(
+        index.modules, index.reference_facts_by_module
+    )
+    graph = build_graph(
+        index.modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=reexports,
+    )
+    imports = {
+        name: module.imports for name, module in index.modules.items()
+    }
+    trees = {
+        name: ast.parse(Path(module.absolute_path).read_bytes())
+        for name, module in index.modules.items()
+    }
+    closures = compute_cycle_model_source_closures_with_optional_children(
+        graph.hard_edges, imports, package_root=package_root
+    )
+    return graph, trees, imports, package_root, closures
+
+
+def _run(case, *, graph=None, trees=None, imports=None, root=None, closures=None):
+    g, t, i, r, c = case
+    return analyze_cycle_scenarios(
+        g.hard_edges if graph is None else graph,
+        t if trees is None else trees,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=i if imports is None else imports,
+        package_root=r if root is None else root,
+        source_closures=c if closures is None else closures,
+    )
+
+
+def test_legacy_mode_unchanged(tmp_path):
+    graph, trees, imports, _, _ = _case(tmp_path)
+    default = analyze_cycle_scenarios(graph.hard_edges, trees)
+    explicit = analyze_cycle_scenarios(
+        graph.hard_edges, trees, source_selection="HARD_ONLY"
+    )
+    assert default == explicit
+    assert default.evidence_scope == "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    with pytest.raises(ValueError, match="^HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED$"):
+        analyze_cycle_scenarios(
+            graph.hard_edges, trees,
+            indexed_imports_by_module=imports,
+        )
+
+
+def test_named_child_missing_from_old_closure_but_present_in_optional(tmp_path):
+    case = _case(tmp_path)
+    graph, trees, _, _, closures = case
+    old = analyze_cycle_scenarios(graph.hard_edges, trees)
+    optional = _run(case)
+    assert "pkg.child" not in compute_cycle_model_source_closures(
+        graph.hard_edges
+    )[0].evidence_source_modules
+    assert "pkg.child" in closures[0].evidence_source_modules
+    assert old.components[0].reason == "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+    assert optional.components[0].reason != "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+    assert len(optional.components[0].entry_assessments) == len(
+        closures[0].members
+    )
+    assert optional.evidence_scope == (
+        "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    )
+    assert optional.components[0].evidence_scope == (
+        "CLOSED_REGULAR_PACKAGE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
+    )
+
+
+def test_reexport_shadow_does_not_remove_indexed_child(tmp_path):
+    case = _case(
+        tmp_path, {**FILES, "pkg/__init__.py": "child = 1\n"}
+    )
+    graph, _, _, _, closures = case
+    assert "pkg.child" not in graph.soft_edges["pkg.a"]
+    assert "pkg.child" in closures[0].evidence_source_modules
+    assert _run(case).components[0].reason != (
+        "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
+    )
+
+
+def test_hard_dependency_and_second_optional_child(tmp_path):
+    files = {
+        **FILES,
+        "pkg/child.py": "import pkg.helper\nfrom pkg.nested import next_child\n",
+        "pkg/helper.py": "pass\n",
+        "pkg/nested/__init__.py": "pass\n",
+        "pkg/nested/next_child.py": "pass\n",
+    }
+    case = _case(tmp_path, files)
+    _, _, _, _, closures = case
+    selected = set(closures[0].evidence_source_modules)
+    assert {
+        "pkg.child", "pkg.helper",
+        "pkg.nested.__init__", "pkg.nested.next_child",
+    } <= selected
+    assert _run(case).components[0].reason != "MISSING_OR_INVALID_SOURCE"
+
+
+def test_old_or_forged_cohort_is_rejected_before_model(tmp_path):
+    case = _case(tmp_path)
+    graph, _, imports, _, closures = case
+    old = compute_cycle_model_source_closures(graph.hard_edges)
+    forged = (
+        replace(
+            closures[0],
+            evidence_source_modules=tuple(
+                name for name in closures[0].evidence_source_modules
+                if name != "pkg.child"
+            ),
+        ),
+    )
+    invalid_imports = dict(imports)
+    invalid_imports.pop("pkg.child")
+    for kwargs in (
+        {"closures": old},
+        {"closures": forged},
+        {"imports": invalid_imports},
+        {"closures": (replace(closures[0], members=("forged",)),)},
+    ):
+        row = _run(case, **kwargs).components[0]
+        assert row.classification == "INDETERMINATE"
+        assert row.coverage == "NONE"
+        assert row.entry_assessments == ()
+        assert row.reason == "OPTIONAL_COHORT_IDENTITY_MISMATCH"
+        assert row.evidence_scope == (
+            "CLOSED_FLAT_MODULE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
+        )
+
+
+def test_missing_selected_ast_fails_closed(tmp_path):
+    case = _case(tmp_path)
+    trees = dict(case[1])
+    trees.pop("pkg.child")
+    row = _run(case, trees=trees).components[0]
+    assert row.reason == "MISSING_OR_INVALID_SOURCE"
+    assert row.classification == "INDETERMINATE"
+    assert row.entry_assessments == ()
+
+
+def test_changed_graph_invalidates_old_optional_closure(tmp_path):
+    case = _case(tmp_path)
+    graph = {
+        name: set(targets)
+        for name, targets in case[0].hard_edges.items()
+    }
+    graph["pkg.a"].add("pkg.child")
+    row = _run(case, graph=graph).components[0]
+    assert row.reason == "OPTIONAL_COHORT_IDENTITY_MISMATCH"
+    assert row.classification == "INDETERMINATE"
+
+
+def test_budget_rejection_uses_optional_scope(tmp_path, monkeypatch):
+    case = _case(tmp_path)
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.scenarios.MAX_CLOSURE_STATEMENTS", 1
+    )
+    row = _run(case).components[0]
+    assert row.reason == "STATEMENT_BUDGET_EXCEEDED"
+    assert row.classification == "INDETERMINATE"
+    assert "OPTIONAL_NAMED_CHILDREN" in row.evidence_scope
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.scenarios.MAX_CLOSURE_STATEMENTS", 4096
+    )
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.scenarios.MAX_CLOSURE_AST_NODES", 1
+    )
+    assert _run(case).components[0].reason == "AST_NODE_BUDGET_EXCEEDED"
+
+
+def test_explicit_lazy_import_never_passes(tmp_path):
+    case = _case(tmp_path)
+    trees = dict(case[1])
+    for node in ast.walk(trees["pkg.a"]):
+        if isinstance(node, ast.Import):
+            node.is_lazy = True
+            break
+    row = _run(case, trees=trees).components[0]
+    assert row.classification == "INDETERMINATE"
+    assert row.reason == "UNMODELED_EXPLICIT_LAZY_IMPORT"
+
+
+def test_two_sccs_and_graph_immutability(tmp_path):
+    files = {
+        **FILES,
+        "pkg/x.py": "import pkg.y\n",
+        "pkg/y.py": "import pkg.x\n",
+    }
+    case = _case(tmp_path, files)
+    graph = case[0]
+    before = {
+        name: set(targets)
+        for name, targets in graph.hard_edges.items()
+    }
+    report = _run(case)
+    assert len(report.components) == 2
+    assert tuple(row.members for row in report.components) == tuple(
+        row.members for row in case[4]
+    )
+    assert all(
+        "OPTIONAL_NAMED_CHILDREN" in row.evidence_scope
+        for row in report.components
+    )
+    assert graph.hard_edges == before
+
+
+def test_optional_flat_model_has_distinct_scope():
+    from contextor.core.domain.imports import ImportRef
+
+    hard = {"a": {"b"}, "b": {"a"}}
+    trees = {
+        "a": ast.parse("import b\n"),
+        "b": ast.parse("import a\n"),
+    }
+    imports = {
+        "a": [ImportRef(module="b", level=0, names=[],
+                        is_from_import=False)],
+        "b": [ImportRef(module="a", level=0, names=[],
+                        is_from_import=False)],
+    }
+    closures = compute_cycle_model_source_closures_with_optional_children(
+        hard, imports
+    )
+    result = analyze_cycle_scenarios(
+        hard, trees,
+        source_selection="OPTIONAL_NAMED_CHILDREN",
+        indexed_imports_by_module=imports,
+        source_closures=closures,
+    )
+    assert result.components[0].evidence_scope == (
+        "CLOSED_FLAT_MODULE_OPTIONAL_NAMED_CHILDREN_FRESH_ENTRY_MODEL"
+    )
+    assert result.components[0].model_kind == "FLAT_MODULE"
+    assert not hasattr(result, "prepared_manifest")
+    assert not hasattr(result, "installed_claim")
```

## FINAL_VERDICT

PASS

The literal patch and its targeted tests passed. This stage remains diagnostic and does not produce source-bound evidence or publication.
