# CONTEXTOR_B0G4B6_SCC_SCENARIO_DIAGNOSTICS

## HEAD_BEFORE
e356152af143a35e385631b4feed9c0fd475e142. Git status clean. B0G4B5 scc.py and B0G4B4 initialization_model.py existed and were indexed in fresh Contextor LIVE state. Both B0G4B6 target files were absent.

## HEAD_AFTER
e356152af143a35e385631b4feed9c0fd475e142. No commit. Git status shows only the two new B0G4B6 files as untracked.

## LIVE_REVISION_BEFORE
414; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; graph, topology, collisions and cycles fresh; name_collisions=0; structural cycles=16. Project overlay workspace_sync=unverified. Contextor confirms SCC kernel owner in contextor.core.cycle_semantics.scc and restricted model owner in contextor.core.cycle_semantics.initialization_model; each had only its targeted test as a direct consumer before this task.

## LIVE_REVISION_AFTER
416; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; all displayed families fresh; no parse-stale modules; collisions=0; cycles=16. Desktop watcher revision 415 UPDATED scenarios.py and revision 416 UPDATED test_cycle_semantics_scenarios.py, both blast_radius_state=fresh. New production module workspace_sync=verified by full get_file_edit_context at revision 416; project overlay remains unverified.

## FILES_CHANGED
- contextor/core/cycle_semantics/scenarios.py (new)
- tests/test_cycle_semantics_scenarios.py (new)

No existing file, including __init__.py, was edited. walkthrough.md is this report and excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: The two files implement the supplied literal design. The component obtains cyclic SCCs from the approved kernel, computes each component's reachable closure, requires all reachable ASTs, enforces entry/statement/AST-node budgets, requires exact graph-to-syntactic-import target parity, and evaluates the restricted initialization model independently from each SCC member. Result dataclasses are frozen and preserve per-entry assessments. Classifications are MODEL_INTERNAL_EARLY_BINDING_HAZARD, MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS, or INDETERMINATE. A hazard is internal only when the failing event's source and target are both SCC members.
CODE_PATH_PROVED: The component consumes in-memory graph and AST inputs; it does not execute analyzed code, read source files, mutate the graph/canonical state, publish diagnostics, or call LIVE/MCP. Contextor reports its only direct consumer as tests.test_cycle_semantics_scenarios, with zero downstream consumers.

## TEST_COMMAND
Pre-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`
Post-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS
Repository Python 3.10.9. Pre-edit exit 0: 92 passed in 2.78s. Post-edit exit 0: 108 passed in 4.15s (16 new plus 92 existing). No other tests, full suite or FULL analysis run. New production syntax diagnostics are fresh and error-free at revision 416.

## SCC_SCENARIO_EVIDENCE
CONTRACT_PROVED: Tests show the same hard-edge topology can yield an internal early-binding hazard or all modeled fresh-member entries passing when only binding order changes. Every member has an independent ImportOrderAssessment. Two independent SCCs receive separate classifications. An acyclic graph yields no component scenarios. A self-loop is analyzed as a cyclic unit. A successful reachable noncyclic dependency is included in the closure without becoming a separate component diagnosis.

## GRAPH_SOURCE_PARITY_EVIDENCE
CONTRACT_PROVED: The declared AST import targets are compared exactly against hard-edge adjacency for every reachable module. A graph/source discrepancy yields INDETERMINATE with GRAPH_SOURCE_IMPORT_MISMATCH and no entry assessments; a missing reachable source yields MISSING_OR_INVALID_SOURCE. Relative, star and dotted imports cannot be promoted to a closed flat-module proof. Tests cover discrepancy and missing-source cases.

## CROSS_SCC_ATTRIBUTION_EVIDENCE
CONTRACT_PROVED: Internal hazard attribution requires the final EARLY_BINDING_HAZARD event's source and target to be members of the component. A downstream SCC hazard is not attributed to an upstream SCC. An error in an external noncyclic dependency similarly leaves the current SCC INDETERMINATE. Targeted tests cover both cases.

## BUDGET_EVIDENCE
CONTRACT_PROVED: More than 64 members yields ENTRY_BUDGET_EXCEEDED, more than 4096 closure statements yields STATEMENT_BUDGET_EXCEEDED, and more than 16384 closure AST nodes yields AST_NODE_BUDGET_EXCEEDED. Each path returns INDETERMINATE with coverage NONE and no entry assessments. Tests cover all three.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0 from fresh canonical get_name_collisions at revisions 414 and 416. No new name collision.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 from fresh canonical diagnostics. Existing structural graph and cycle detection code were not edited. Watcher indexing of two new modules may add ordinary dependency edges; a byte-identical whole-repository graph is not claimed.

## NO_SAFETY_CERTIFICATION
CODE_PATH_PROVED: Report scope is SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION and component scope is CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL. MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS is explicitly limited to modeled fresh entry scenarios, not SAFE or a general runtime proof. Unsupported or incomplete inputs fail closed to INDETERMINATE.

## NO_WARNING_SUPPRESSION
CODE_PATH_PROVED: No ArchitectureCycle or warning-publication code was edited or called. Canonical structural cycles remain 16. No suppression rule was added.

## NO_DIRECT_LIVE_PUBLICATION
CODE_PATH_PROVED: The new module is imported only by its test and not exported from __init__.py or integrated with FULL/incremental, MCP, LIVE, Desktop or snapshots. Watcher indexing is external observation. No direct update_file, restart or commit.

## UNRESOLVED_LIMITATIONS
UNKNOWN: The model does not certify general runtime reachability, safety, or failure. It requires a closed flat-module import subset and fresh-entry assessment of each SCC member. Missing ASTs, graph/source mismatch, unsupported syntax and budget excess are explicit INDETERMINATE outcomes. Project-wide workspace synchronization is unverified in the global overlay, though the target production file was verified against disk.

## FINAL_VERDICT
B0G4B6_PASS — exact isolated two-file implementation, 108 focused tests passed, both watcher events observed, fresh canonical state, zero name collisions and unchanged structural cycle count. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/scenarios.py

diff --git a/contextor/core/cycle_semantics/scenarios.py b/contextor/core/cycle_semantics/scenarios.py
new file mode 100644
index 0000000..25b839b
--- /dev/null
+++ b/contextor/core/cycle_semantics/scenarios.py
@@ -0,0 +1,194 @@
+"""Bounded SCC scenario analysis over an explicitly closed flat-module model.
+
+This is deliberately not a safety certificate, publication policy or LIVE state.
+"""
+
+from __future__ import annotations
+
+import ast
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from .initialization_model import ImportOrderAssessment, evaluate_flat_import_order
+from .scc import CyclicImportComponent, ImportCycleTopology, analyze_import_cycle_topology
+
+MAX_COMPONENT_ENTRIES = 64
+MAX_CLOSURE_STATEMENTS = 4096
+MAX_CLOSURE_AST_NODES = 16384
+
+
+@dataclass(frozen=True)
+class CycleComponentScenarios:
+    members: tuple[str, ...]
+    internal_edges: tuple[tuple[str, str], ...]
+    classification: str
+    coverage: str
+    reason: str | None
+    entry_assessments: tuple[ImportOrderAssessment, ...]
+    evidence_scope: str = "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
+
+
+@dataclass(frozen=True)
+class CycleScenarioReport:
+    topology: ImportCycleTopology
+    components: tuple[CycleComponentScenarios, ...]
+    evidence_scope: str = "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+
+
+def _declared_import_targets(tree: ast.Module) -> set[str] | None:
+    """Return syntactic targets; refuse relative/star or dotted imports."""
+    found: set[str] = set()
+    for node in ast.walk(tree):
+        if isinstance(node, ast.Import):
+            for alias in node.names:
+                if not alias.name.isidentifier():
+                    return None
+                found.add(alias.name)
+        elif isinstance(node, ast.ImportFrom):
+            if node.level or not node.module or not node.module.isidentifier():
+                return None
+            if any(alias.name == "*" for alias in node.names):
+                return None
+            found.add(node.module)
+    return found
+
+
+def _closure(
+    members: tuple[str, ...], adjacency: Mapping[str, frozenset[str]]
+) -> set[str]:
+    visited = set(members)
+    pending = list(members)
+    while pending:
+        for target in adjacency[pending.pop()]:
+            if target not in visited:
+                visited.add(target)
+                pending.append(target)
+    return visited
+
+
+def _component_result(
+    component: CyclicImportComponent,
+    classification: str,
+    *,
+    coverage: str,
+    reason: str | None = None,
+    assessments: tuple[ImportOrderAssessment, ...] = (),
+) -> CycleComponentScenarios:
+    return CycleComponentScenarios(
+        members=component.members,
+        internal_edges=component.internal_edges,
+        classification=classification,
+        coverage=coverage,
+        reason=reason,
+        entry_assessments=assessments,
+    )
+
+
+def analyze_cycle_scenarios(
+    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+    modules: Mapping[str, ast.AST],
+) -> CycleScenarioReport:
+    """Analyze every fresh entry module of each cyclic SCC, without executing code.
+
+    Source-to-graph edge equality is required for the entire reachable closure.
+    Missing, dynamic and unsupported semantics yield INDETERMINATE, never safe.
+    """
+    topology = analyze_import_cycle_topology(hard_edges)
+    if not isinstance(modules, Mapping):
+        raise TypeError("modules must be a mapping")
+
+    adjacency = {name: frozenset(targets) for name, targets in hard_edges.items()}
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, frozenset())
+
+    output: list[CycleComponentScenarios] = []
+    for component in topology.cyclic_components:
+        if len(component.members) > MAX_COMPONENT_ENTRIES:
+            output.append(_component_result(
+                component, "INDETERMINATE", coverage="NONE",
+                reason="ENTRY_BUDGET_EXCEEDED",
+            ))
+            continue
+
+        reachable = _closure(component.members, adjacency)
+        if any(name not in modules or not isinstance(modules[name], ast.Module)
+               for name in reachable):
+            output.append(_component_result(
+                component, "INDETERMINATE", coverage="NONE",
+                reason="MISSING_OR_INVALID_SOURCE",
+            ))
+            continue
+
+        if sum(len(modules[name].body) for name in reachable) > MAX_CLOSURE_STATEMENTS:
+            output.append(_component_result(
+                component, "INDETERMINATE", coverage="NONE",
+                reason="STATEMENT_BUDGET_EXCEEDED",
+            ))
+            continue
+
+        # A single top-level statement can contain an arbitrarily large AST.
+        ast_budget = MAX_CLOSURE_AST_NODES
+        for name in sorted(reachable):
+            for _ in ast.walk(modules[name]):
+                ast_budget -= 1
+                if ast_budget < 0:
+                    break
+            if ast_budget < 0:
+                break
+        if ast_budget < 0:
+            output.append(_component_result(
+                component, "INDETERMINATE", coverage="NONE",
+                reason="AST_NODE_BUDGET_EXCEEDED",
+            ))
+            continue
+
+        # The graph and AST must describe the exact same import targets.
+        # No name-based exceptions and no guessed package resolution.
+        if any(
+            _declared_import_targets(modules[name]) != set(adjacency[name])
+            for name in reachable
+        ):
+            output.append(_component_result(
+                component, "INDETERMINATE", coverage="NONE",
+                reason="GRAPH_SOURCE_IMPORT_MISMATCH",
+            ))
+            continue
+
+        sources = {name: modules[name] for name in sorted(reachable)}
+        assessments = tuple(
+            evaluate_flat_import_order(sources, entry)
+            for entry in component.members
+        )
+        member_set = set(component.members)
+        internal_hazard = any(
+            result.outcome == "EARLY_BINDING_HAZARD"
+            and result.events
+            and result.events[-1].operation == "EARLY_BINDING_HAZARD"
+            and result.events[-1].module in member_set
+            and result.events[-1].target in member_set
+            for result in assessments
+        )
+        if internal_hazard:
+            classification = "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+        elif all(result.outcome == "MODEL_PASS" for result in assessments):
+            classification = "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+        else:
+            classification = "INDETERMINATE"
+
+        coverage = (
+            "COMPLETE_FRESH_MEMBER_ENTRIES"
+            if all(result.outcome != "UNKNOWN" for result in assessments)
+            else "PARTIAL_FRESH_MEMBER_ENTRIES"
+        )
+        reason = (
+            "UNRESOLVED_SCENARIO"
+            if classification == "INDETERMINATE"
+            else None
+        )
+        output.append(_component_result(
+            component, classification, coverage=coverage,
+            reason=reason, assessments=assessments,
+        ))
+
+    return CycleScenarioReport(topology, tuple(output))

### FULL_DIFF: tests/test_cycle_semantics_scenarios.py

diff --git a/tests/test_cycle_semantics_scenarios.py b/tests/test_cycle_semantics_scenarios.py
new file mode 100644
index 0000000..2979b7b
--- /dev/null
+++ b/tests/test_cycle_semantics_scenarios.py
@@ -0,0 +1,178 @@
+import ast
+import json
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.scenarios import (
+    analyze_cycle_scenarios,
+    MAX_COMPONENT_ENTRIES,
+    MAX_CLOSURE_AST_NODES,
+)
+
+
+def _assess(sources, edges):
+    return analyze_cycle_scenarios(edges, {k: ast.parse(v) for k, v in sources.items()})
+
+
+def test_hazard_same_edges_safe_reordering():
+    graph = {"a": {"b"}, "b": {"a"}}
+    x = _assess(
+        {"a": "import b\nvalue=1\n", "b": "import a\nx=a.value\n"}, graph
+    )
+    assert x.components[0].classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    assert [s.outcome for s in x.components[0].entry_assessments] == [
+        "EARLY_BINDING_HAZARD", "MODEL_PASS"
+    ]
+    y = _assess(
+        {"a": "value=1\nimport b\n", "b": "import a\nx=a.value\n"}, graph
+    )
+    assert y.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert x.topology == y.topology
+    assert y.components[0].coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
+
+
+def test_two_independent_sccs():
+    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
+    sources = {
+        "a": "import b\nvalue=1",
+        "b": "import a\nx=a.value",
+        "x": "import y\na=1",
+        "y": "import x\nb=2",
+    }
+    r = _assess(sources, edges)
+    assert [c.classification for c in r.components] == [
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+    ]
+
+
+def test_unsupported_inside_component_is_unknown():
+    r = _assess(
+        {"a": "if True:\n    import b", "b": "import a"},
+        {"a": {"b"}, "b": {"a"}},
+    )
+    assert r.components[0].classification == "INDETERMINATE"
+    assert r.components[0].coverage == "PARTIAL_FRESH_MEMBER_ENTRIES"
+
+
+def test_graph_source_discrepancy_fails_closed():
+    r = _assess(
+        {"a": "import b\nimport c", "b": "import a", "c": "pass"},
+        {"a": {"b"}, "b": {"a"}, "c": set()},
+    )
+    assert r.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    assert r.components[0].entry_assessments == ()
+
+
+def test_missing_imported_source_fails_closed():
+    r = _assess(
+        {"a": "import b", "b": "import a\nimport c"},
+        {"a": {"b"}, "b": {"a", "c"}},
+    )
+    assert r.components[0].reason == "MISSING_OR_INVALID_SOURCE"
+
+
+def test_unrelated_unsupported_module_is_not_contamination():
+    r = _assess(
+        {"a": "import b", "b": "import a", "z": "class Dangerous:\n    pass"},
+        {"a": {"b"}, "b": {"a"}, "z": set()},
+    )
+    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_external_error_not_mislabeled_internal_cycle():
+    r = _assess(
+        {
+            "a": "import b\nimport c",
+            "b": "import a",
+            "c": "from d import missing",
+            "d": "pass",
+        },
+        {"a": {"b", "c"}, "b": {"a"}, "c": {"d"}, "d": set()},
+    )
+    assert r.components[0].classification == "INDETERMINATE"
+    assert all(
+        x.outcome == "MISSING_EXPORT"
+        for x in r.components[0].entry_assessments
+    )
+
+
+def test_acyclic_no_components():
+    r = _assess(
+        {"a": "import b", "b": "pass"},
+        {"a": {"b"}, "b": set()},
+    )
+    assert r.components == ()
+    assert r.topology.total_scc_count == 2
+
+
+def test_self_loop_is_not_error():
+    r = _assess({"a": "import a\nx=1"}, {"a": {"a"}})
+    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_large_scc_budget_unknown():
+    n = MAX_COMPONENT_ENTRIES + 1
+    edges = {f"m{i}": {f"m{(i+1)%n}"} for i in range(n)}
+    sources = {k: "import " + next(iter(targets)) for k, targets in edges.items()}
+    r = _assess(sources, edges)
+    assert r.components[0].classification == "INDETERMINATE"
+    assert r.components[0].reason == "ENTRY_BUDGET_EXCEEDED"
+
+
+def test_budget_statements():
+    n = 4097
+    s = "import b\n" + "pass\n" * n
+    r = _assess({"a": s, "b": "import a"}, {"a": {"b"}, "b": {"a"}})
+    assert r.components[0].reason == "STATEMENT_BUDGET_EXCEEDED"
+
+
+def test_determinism_immutability_serialization():
+    src = {"a": "import b", "b": "import a"}
+    edges = {"a": {"b"}, "b": {"a"}}
+    r = _assess(src, edges)
+    assert r == _assess(src, edges)
+    json.dumps(asdict(r))
+    with pytest.raises(Exception):
+        r.components[0].classification = "fake"
+    assert edges == {"a": {"b"}, "b": {"a"}}
+
+
+def test_invalid_modules_fail_type_check():
+    with pytest.raises(TypeError):
+        analyze_cycle_scenarios({"a": {"a"}}, None)
+
+
+def test_dependency_on_successful_noncyclic_module():
+    r = _assess(
+        {"a": "import b\nimport c", "b": "import a", "c": "x=1"},
+        {"a": {"b", "c"}, "b": {"a"}, "c": set()},
+    )
+    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_downstream_scc_hazard_not_attributed_to_upstream_scc():
+    r = _assess(
+        {
+            "a": "import b\nimport x",
+            "b": "import a",
+            "x": "import y\nvalue=1",
+            "y": "import x\nobserved=x.value",
+        },
+        {"a": {"b", "x"}, "b": {"a"}, "x": {"y"}, "y": {"x"}},
+    )
+    assert [c.classification for c in r.components] == [
+        "INDETERMINATE",
+        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+    ]
+
+
+def test_ast_budget_one_large_statement():
+    n = MAX_CLOSURE_AST_NODES + 2
+    literal = ",".join("1" for _ in range(n))
+    r = _assess(
+        {"a": "import b\nx=[" + literal + "]", "b": "import a"},
+        {"a": {"b"}, "b": {"a"}},
+    )
+    assert r.components[0].reason == "AST_NODE_BUDGET_EXCEEDED"
