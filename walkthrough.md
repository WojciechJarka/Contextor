# CONTEXTOR_B0G4C12_SINGLE_NON_DIRECT_EDGE_CLOSURE_WITNESSES

## HEAD_BEFORE
ba3a57cc7f413807d762e21afa1f3e272c0a9268

## HEAD_AFTER
ba3a57cc7f413807d762e21afa1f3e272c0a9268

## GIT_STATUS
Before: clean. After report: M walkthrough.md plus the two untracked files listed below.

## LIVE_REVISION_BEFORE
437; activity_epoch=1beab26da2ff4932852caa7db6ff4242; resync_required=false. Canonical syntax/collisions/cycles fresh; collisions 0; structural cycle paths 16.

## LIVE_REVISION_AFTER
439; same activity_epoch; resync_required=false; continuous event feed. DIRECT_EVIDENCE: desktop_watcher UPDATED closure_witness.py at revision 438 and test_cycle_semantics_closure_witness.py at 439. Both modules canonical_state=fresh and workspace_sync=verified. Graph/cycles/collisions fresh.

## FILES_CHANGED
- contextor/core/cycle_semantics/closure_witness.py (new)
- tests/test_cycle_semantics_closure_witness.py (new)
walkthrough.md is the requested report artifact. No existing source or test file changed.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: Both files match the auditor-supplied CONTENT blocks exactly after newline normalization. Current activation_view, edge_sites and scc owners were fresh and workspace_sync=verified at revision 437. Relevant dataclass and function contracts matched. The witness consumes approved activation and lexical site reports; it does not independently reclassify source imports. Contextor blast radius showed one direct test consumer each for activation and edge-site analyzers and five static direct consumers of the SCC analyzer.

## TEST_COMMAND
Baseline:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_activation_view.py tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_closure_witness.py tests/test_cycle_semantics_activation_view.py tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

## TEST_RESULTS
DIRECT_EVIDENCE: baseline 226 passed in 13.91s; post-change 242 passed in 13.22s. Sixteen new cases passed. Full pytest suite was not run.

## DIRECT_GRAPH_PRESERVATION
CODE_PATH_PROVED: The algorithm reads view.unguarded_direct_edges, validates each view edge's membership against its unguarded_direct_count and builds sorted adjacency. It does not alter the original structural topology or direct-candidate topology. Tests keep direct-cycle SCCs distinct and check input equality after repeated calls.

## SINGLE_NON_DIRECT_CLOSURE_EVIDENCE
CODE_PATH_PROVED: For every excluded U -> V, the function searches a direct-only path V -> U. If found, it retains a witness with the original non-direct lexical sites, direct_return_path and closed_walk. It preserves all qualifying edges, including multiple separate closures. This is lexical evidence only.

## MULTIPLE_NON_DIRECT_LIMITATION
DIRECT_EVIDENCE: The two-non-direct regression produces no single-edge witness and retains both edges in non_direct_without_direct_return. Absence of a single-edge witness does not exclude a cycle needing multiple non-direct edges.

## SHORTEST_PATH_DETERMINISM
CODE_PATH_PROVED: Iterative BFS finds the minimum edge-count return path; sorted lexical neighbors resolve equal-length alternatives deterministically. The tie regression selects a -> b -> z. The 140-node regression passes without recursive traversal.

## GUARDED_INDIRECT_UNRESOLVED_EVIDENCE
DIRECT_EVIDENCE: Tests preserve GUARDed, PARENT_INITIALIZER and missing-source non-direct closure candidates without promoting them to execution proof. Missing-source witness carries empty non_direct_sites. Raw site tuples, including scope/control frames when present, are copied unchanged.

## SELF_LOOP_AND_MULTI_SCC_REGRESSIONS
DIRECT_EVIDENCE: Non-direct self-loop yields closed_walk=(a,a) and direct_return_path=(a). Two SCCs are processed independently; one can have a witness while the other remains a direct cyclic SCC.

## INPUT_IMMUTABILITY
DIRECT_EVIDENCE: Repeated calls produce equal frozen dataclasses; asdict JSON serialization succeeds; mutation raises FrozenInstanceError; test compares activation, evidence and graph before/after. This function does not parse or mutate ASTs.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0, fresh canonical diagnostics.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 reported paths, fresh canonical diagnostics.

## NO_RUNTIME_CERTIFICATION
No witness is classified SAFE, ERROR, FALSE_POSITIVE or RESOLVED. The evidence_scope expressly excludes runtime execution. No analyzed production import was run.

## NO_WARNING_SUPPRESSION
No warning, resolver, graph or cycle-diagnostic policy was changed.

## UNRESOLVED_LIMITATIONS
UNKNOWN: Actual execution timing of any excluded import. A lexical witness does not prove a runtime import cycle, and lack of a single-edge witness does not rule out paths needing multiple excluded edges. This stage did not run the new witness over the real SCC snapshot; its required validation was the focused synthetic test set.

## FINAL_VERDICT
B0G4C12_PASS

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/closure_witness.py b/contextor/core/cycle_semantics/closure_witness.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/closure_witness.py
@@ -0,0 +1,173 @@
+"""Single non-direct-edge closure witnesses over lexical activation views.
+
+These witnesses do not establish execution, import-time reachability or safety.
+They do not enumerate arbitrary simple cycles or mutate canonical graph state.
+"""
+
+from __future__ import annotations
+
+from collections import deque
+from dataclasses import dataclass
+
+from .activation_view import CycleActivationViewReport
+from .edge_sites import CyclicImportSiteReport, LexicalEdgeSite
+
+
+@dataclass(frozen=True)
+class NonDirectClosureWitness:
+    source: str
+    target: str
+    classification: str
+    non_direct_sites: tuple[LexicalEdgeSite, ...]
+    direct_return_path: tuple[str, ...]
+    closed_walk: tuple[str, ...]
+
+
+@dataclass(frozen=True)
+class SCCSingleEdgeClosure:
+    members: tuple[str, ...]
+    structural_edge_count: int
+    direct_edge_count: int
+    non_direct_edge_count: int
+    direct_cyclic_scc_count: int
+    single_edge_witnesses: tuple[NonDirectClosureWitness, ...]
+    non_direct_without_direct_return: tuple[tuple[str, str], ...]
+    evidence_scope: str = "ONE_NON_DIRECT_EDGE_PLUS_DIRECT_LEXICAL_PATH"
+
+
+@dataclass(frozen=True)
+class SingleEdgeClosureReport:
+    components: tuple[SCCSingleEdgeClosure, ...]
+    evidence_scope: str = "LEXICAL_CLOSURE_WITNESSES_NOT_RUNTIME_EXECUTION"
+
+
+def _shortest_direct_path(
+    start: str,
+    end: str,
+    adjacency: dict[str, tuple[str, ...]],
+) -> tuple[str, ...] | None:
+    """Shortest direct path with deterministic lexical tie resolution."""
+    queue = deque([start])
+    previous: dict[str, str | None] = {start: None}
+
+    while queue:
+        current = queue.popleft()
+        if current == end:
+            path: list[str] = []
+            while current is not None:
+                path.append(current)
+                current = previous[current]
+            return tuple(reversed(path))
+
+        for neighbor in adjacency[current]:
+            if neighbor not in previous:
+                previous[neighbor] = current
+                queue.append(neighbor)
+
+    return None
+
+
+def analyze_single_edge_cycle_closures(
+    activation: CycleActivationViewReport,
+    sites: CyclicImportSiteReport,
+) -> SingleEdgeClosureReport:
+    """Find each non-direct edge that alone closes a direct lexical path.
+
+    Absence of a witness does not mean absence of runtime cycles. Multiple
+    non-direct edges may jointly close a cycle; calls may run during imports.
+    """
+    if not isinstance(activation, CycleActivationViewReport):
+        raise TypeError("activation must be CycleActivationViewReport")
+    if not isinstance(sites, CyclicImportSiteReport):
+        raise TypeError("sites must be CyclicImportSiteReport")
+
+    if (
+        activation.structural_topology != sites.topology
+        or len(activation.components) != len(sites.components)
+    ):
+        raise ValueError("activation and site topology differ")
+
+    output: list[SCCSingleEdgeClosure] = []
+
+    for view, site_component in zip(
+        activation.components, sites.components
+    ):
+        if view.members != site_component.members:
+            raise ValueError("SCC member identities differ")
+
+        view_ids = tuple((e.source, e.target) for e in view.edges)
+        site_ids = tuple(
+            (e.source, e.target) for e in site_component.internal_edges
+        )
+        if view_ids != site_ids:
+            raise ValueError("SCC internal edge identities differ")
+
+        indexed_sites = {
+            (e.source, e.target): e
+            for e in site_component.internal_edges
+        }
+        direct = set(view.unguarded_direct_edges)
+        adjacency_sets: dict[str, set[str]] = {
+            member: set() for member in view.members
+        }
+
+        for edge in view.edges:
+            pair = (edge.source, edge.target)
+            if edge.site_count != len(indexed_sites[pair].sites):
+                raise ValueError("site counts differ")
+            if (edge.unguarded_direct_count > 0) != (pair in direct):
+                raise ValueError("direct edge membership differs")
+            if pair in direct:
+                adjacency_sets[edge.source].add(edge.target)
+
+        if len(direct) != sum(
+            e.unguarded_direct_count > 0 for e in view.edges
+        ):
+            raise ValueError("direct edge count differs")
+
+        adjacency = {
+            member: tuple(sorted(adjacency_sets[member]))
+            for member in view.members
+        }
+
+        witnesses: list[NonDirectClosureWitness] = []
+        no_return: list[tuple[str, str]] = []
+
+        for edge in view.edges:
+            pair = (edge.source, edge.target)
+            if pair in direct:
+                continue
+
+            return_path = _shortest_direct_path(
+                edge.target, edge.source, adjacency
+            )
+            if return_path is None:
+                no_return.append(pair)
+                continue
+
+            witnesses.append(
+                NonDirectClosureWitness(
+                    source=edge.source,
+                    target=edge.target,
+                    classification=edge.classification,
+                    non_direct_sites=indexed_sites[pair].sites,
+                    direct_return_path=return_path,
+                    closed_walk=(edge.source,) + return_path,
+                )
+            )
+
+        output.append(
+            SCCSingleEdgeClosure(
+                members=view.members,
+                structural_edge_count=len(view.edges),
+                direct_edge_count=len(direct),
+                non_direct_edge_count=len(view.edges) - len(direct),
+                direct_cyclic_scc_count=len(
+                    view.unguarded_direct_topology.cyclic_components
+                ),
+                single_edge_witnesses=tuple(witnesses),
+                non_direct_without_direct_return=tuple(no_return),
+            )
+        )
+
+    return SingleEdgeClosureReport(tuple(output))

diff --git a/tests/test_cycle_semantics_closure_witness.py b/tests/test_cycle_semantics_closure_witness.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_closure_witness.py
@@ -0,0 +1,383 @@
+import json
+from dataclasses import FrozenInstanceError, asdict, replace
+
+import pytest
+
+from contextor.core.cycle_semantics.scc import analyze_import_cycle_topology
+from contextor.core.cycle_semantics.edge_sites import (
+    CyclicImportSiteReport,
+    SCCImportSiteEvidence,
+    HardEdgeSiteEvidence,
+    LexicalEdgeSite,
+)
+from contextor.core.cycle_semantics.activation_view import (
+    analyze_cycle_activation_view,
+)
+from contextor.core.cycle_semantics.closure_witness import (
+    analyze_single_edge_cycle_closures,
+)
+
+
+D = ("MODULE_TOP_LEVEL", "FROM_BASE", 1)
+F = ("FUNCTION_SCOPED", "FROM_BASE", 23)
+G = ("GUARDED_TOP_LEVEL", "FROM_BASE", 9)
+I = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER", 5)
+
+
+def _make(graph, specs):
+    topology = analyze_import_cycle_topology(graph)
+    components = []
+
+    for component in topology.cyclic_components:
+        edges = []
+
+        for source, target in component.internal_edges:
+            specification = specs.get((source, target), None)
+
+            if specification is None:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source,
+                        target,
+                        "SOURCE_MISSING_OR_INVALID",
+                        (),
+                    )
+                )
+            elif not specification:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source,
+                        target,
+                        "NO_MATCHING_LEXICAL_SITE",
+                        (),
+                    )
+                )
+            else:
+                sites = tuple(
+                    LexicalEdgeSite(
+                        ordinal,
+                        line,
+                        0,
+                        "IMPORT_FROM",
+                        kind,
+                        target,
+                        None,
+                        (),
+                        (),
+                        scope,
+                    )
+                    for ordinal, (scope, kind, line)
+                    in enumerate(specification)
+                )
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source,
+                        target,
+                        "LEXICAL_CANDIDATES",
+                        sites,
+                    )
+                )
+
+        components.append(
+            SCCImportSiteEvidence(
+                component.members,
+                tuple(edges),
+                sum(
+                    edge.status == "LEXICAL_CANDIDATES"
+                    for edge in edges
+                ),
+                sum(
+                    edge.status != "LEXICAL_CANDIDATES"
+                    for edge in edges
+                ),
+            )
+        )
+
+    evidence = CyclicImportSiteReport(
+        topology,
+        tuple(components),
+    )
+    return analyze_cycle_activation_view(evidence), evidence
+
+
+def _examine(graph, specifications):
+    activation, evidence = _make(graph, specifications)
+    return analyze_single_edge_cycle_closures(
+        activation,
+        evidence,
+    )
+
+
+def test_function_single_closure():
+    result = _examine(
+        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "c"): [D],
+            ("c", "a"): [F],
+        },
+    )
+    component = result.components[0]
+    assert component.direct_edge_count == 2
+    assert component.non_direct_edge_count == 1
+    witness = component.single_edge_witnesses[0]
+    assert witness.closed_walk == ("c", "a", "b", "c")
+    assert witness.direct_return_path == ("a", "b", "c")
+    assert witness.non_direct_sites[0].line == 23
+    assert component.direct_cyclic_scc_count == 0
+
+
+def test_two_separate_closures():
+    graph = {
+        "a": {"b"},
+        "b": {"c", "d"},
+        "c": {"a"},
+        "d": {"a"},
+    }
+    specifications = {
+        ("a", "b"): [D],
+        ("b", "c"): [D],
+        ("b", "d"): [D],
+        ("c", "a"): [F],
+        ("d", "a"): [F],
+    }
+    component = _examine(graph, specifications).components[0]
+    assert {
+        (witness.source, witness.target)
+        for witness in component.single_edge_witnesses
+    } == {
+        ("c", "a"),
+        ("d", "a"),
+    }
+    assert component.non_direct_without_direct_return == ()
+
+
+def test_two_non_direct_needed():
+    component = _examine(
+        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "c"): [F],
+            ("c", "a"): [F],
+        },
+    ).components[0]
+    assert component.single_edge_witnesses == ()
+    assert component.non_direct_without_direct_return == (
+        ("b", "c"),
+        ("c", "a"),
+    )
+
+
+def test_direct_cycle_kept():
+    component = _examine(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [D],
+        },
+    ).components[0]
+    assert component.direct_cyclic_scc_count == 1
+    assert component.single_edge_witnesses == ()
+
+
+def test_shortest_lexical_tie():
+    graph = {
+        "a": {"b", "c"},
+        "b": {"z"},
+        "c": {"z"},
+        "z": {"a"},
+    }
+    specs = {
+        ("a", "b"): [D],
+        ("a", "c"): [D],
+        ("b", "z"): [D],
+        ("c", "z"): [D],
+        ("z", "a"): [F],
+    }
+    component = _examine(graph, specs).components[0]
+    assert (
+        component.single_edge_witnesses[0].direct_return_path
+        == ("a", "b", "z")
+    )
+
+
+def test_guarded_closure_candidate_only():
+    result = _examine(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [G],
+        },
+    )
+    witness = result.components[0].single_edge_witnesses[0]
+    assert witness.classification == "GUARDED_TOP_LEVEL_CANDIDATE"
+    assert "NOT_RUNTIME" in result.evidence_scope
+
+
+def test_indirect_closure_candidate_only():
+    component = _examine(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [I],
+        },
+    ).components[0]
+    assert (
+        component.single_edge_witnesses[0].classification
+        == "INDIRECT_TOP_LEVEL_CANDIDATE"
+    )
+
+
+def test_missing_source_closure_with_empty_sites():
+    component = _examine(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+        },
+    ).components[0]
+    witness = component.single_edge_witnesses[0]
+    assert witness.classification == "UNRESOLVED_SOURCE_SITE"
+    assert witness.non_direct_sites == ()
+
+
+def test_self_loop_non_direct():
+    component = _examine(
+        {"a": {"a"}},
+        {("a", "a"): [F]},
+    ).components[0]
+    witness = component.single_edge_witnesses[0]
+    assert witness.closed_walk == ("a", "a")
+    assert witness.direct_return_path == ("a",)
+
+
+def test_two_sccs_independent():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "x": {"y"},
+        "y": {"x"},
+    }
+    specifications = {
+        ("a", "b"): [D],
+        ("b", "a"): [F],
+        ("x", "y"): [D],
+        ("y", "x"): [D],
+    }
+    components = _examine(graph, specifications).components
+    assert len(components) == 2
+    assert len(components[0].single_edge_witnesses) == 1
+    assert components[1].direct_cyclic_scc_count == 1
+
+
+def test_mismatched_topologies():
+    activation, _ = _make(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [D],
+        },
+    )
+    _, other_sources = _make(
+        {"x": {"y"}, "y": {"x"}},
+        {
+            ("x", "y"): [D],
+            ("y", "x"): [D],
+        },
+    )
+    with pytest.raises(ValueError):
+        analyze_single_edge_cycle_closures(
+            activation,
+            other_sources,
+        )
+
+
+def test_mismatched_internal_edge_order():
+    activation, evidence = _make(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [D],
+        },
+    )
+    component = replace(
+        evidence.components[0],
+        internal_edges=tuple(
+            reversed(evidence.components[0].internal_edges)
+        ),
+    )
+    modified = replace(evidence, components=(component,))
+
+    with pytest.raises(ValueError):
+        analyze_single_edge_cycle_closures(
+            activation,
+            modified,
+        )
+
+
+def test_determinism_json_and_no_mutation():
+    graph = {"a": {"b"}, "b": {"a"}}
+    activation, evidence = _make(
+        graph,
+        {
+            ("a", "b"): [D],
+            ("b", "a"): [F],
+        },
+    )
+
+    before = (repr(activation), repr(evidence), repr(graph))
+
+    first = analyze_single_edge_cycle_closures(
+        activation,
+        evidence,
+    )
+    second = analyze_single_edge_cycle_closures(
+        activation,
+        evidence,
+    )
+
+    assert first == second
+    json.dumps(asdict(first))
+
+    with pytest.raises(FrozenInstanceError):
+        first.components[0].direct_edge_count = 3
+
+    assert (repr(activation), repr(evidence), repr(graph)) == before
+
+
+def test_empty_no_cycle():
+    result = _examine(
+        {"a": {"b"}, "b": set()},
+        {("a", "b"): [D]},
+    )
+    assert result.components == ()
+
+
+def test_long_direct_chain_iterative():
+    size = 140
+    graph = {
+        f"n{i:03d}": {f"n{i+1:03d}"}
+        for i in range(size - 1)
+    }
+    graph[f"n{size-1:03d}"] = {"n000"}
+
+    specifications = {
+        (source, target): [D]
+        for source, targets in graph.items()
+        for target in targets
+    }
+    specifications[(f"n{size-1:03d}", "n000")] = [F]
+
+    component = _examine(
+        graph,
+        specifications,
+    ).components[0]
+
+    assert len(component.single_edge_witnesses) == 1
+    assert len(
+        component.single_edge_witnesses[0].closed_walk
+    ) == size + 1
+
+
+def test_invalid_type():
+    with pytest.raises(TypeError):
+        analyze_single_edge_cycle_closures(None, None)
```
