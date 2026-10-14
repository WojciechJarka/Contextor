# CONTEXTOR_B0G4C10_IMPORT_ACTIVATION_CANDIDATE_VIEW

## HEAD_BEFORE
b6bcfb118c54c0f6d85cb9969c80dba381d49f86

## HEAD_AFTER
b6bcfb118c54c0f6d85cb9969c80dba381d49f86

## GIT_STATUS
Before: clean. After writing report: M walkthrough.md and the two untracked files in FILES_CHANGED.

## LIVE_REVISION_BEFORE
435; activity_epoch=1beab26da2ff4932852caa7db6ff4242; resync_required=false; graph/cycles/collisions fresh. Structural cycle paths 16; name collisions 0.

## LIVE_REVISION_AFTER
437; same activity_epoch; continuous event feed, resync_required=false. DIRECT_EVIDENCE: desktop_watcher UPDATED activation_view.py at 436 and test_cycle_semantics_activation_view.py at 437. Both module contexts report workspace_sync=verified, canonical_state=fresh, graph/cycles/collisions fresh.

## FILES_CHANGED
- contextor/core/cycle_semantics/activation_view.py (new)
- tests/test_cycle_semantics_activation_view.py (new)
walkthrough.md is the requested report artifact.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: Both files exactly match the auditor-supplied CONTENT blocks after newline normalization. Existing CyclicImportSiteReport, SCCImportSiteEvidence, HardEdgeSiteEvidence, LexicalEdgeSite, ImportCycleTopology and analyze_import_cycle_topology contracts matched current Contextor source at revision 435. The new pure view consumes existing evidence and creates separate per-SCC candidate topology without changing the input graph or any existing module. Canonical owners were workspace_sync=verified. Static direct consumer of analyze_cyclic_import_sites before change was its test module; SCC topology analyzer had three confirmed direct consumers.

## TEST_COMMAND
Baseline:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_activation_view.py tests/test_cycle_semantics_scc02_entry_order.py tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

## TEST_RESULTS
DIRECT_EVIDENCE: baseline 212 passed in 13.24s; post-change 226 passed in 13.66s. Fourteen new test cases passed. Full suite was not run.

## STRUCTURAL_EDGE_PRESERVATION
CODE_PATH_PROVED: Every component retains every input internal HardEdgeSiteEvidence as an EdgeActivationView. The original structural_topology is the input topology. The separate selected mapping contains only candidate direct edges. Tests cover direct cycles, missing/unmatched sites, multiple SCCs, self-loop, input immutability and deterministic serialization.

## UNGUARDED_DIRECT_PROJECTION
CODE_PATH_PROVED: Only MODULE_TOP_LEVEL sites with DIRECT_MODULE or FROM_BASE increment unguarded_direct_count and select an edge. A deterministic adjacency mapping includes every member, including those with no selected outgoing edge. The derived topology is computed independently for each SCC. The tests cover cyclic and acyclic candidate subgraphs.

## CALL_DEPENDENT_EVIDENCE
CODE_PATH_PROVED: FUNCTION_SCOPED sites contribute to function_scoped_count and, absent a higher-priority candidate, classify the edge CALL_DEPENDENT_CANDIDATE. A mixed top-level/function edge retains both counts. Function scope does not certify late activation.

## GUARDED_AND_INDIRECT_EVIDENCE
CODE_PATH_PROVED: GUARDED_TOP_LEVEL is counted but never promoted to an unguarded direct edge. OPTIONAL_FROM_CHILD and PARENT_INITIALIZER are counted as indirect candidates and remain outside the direct subset unless another direct site exists. Tests cover both categories.

## OTHER_SCOPE_FAIL_CLOSED
CODE_PATH_PROVED: OTHER_SCOPED sites classify as OTHER_SCOPE_CANDIDATE unless a higher-priority site is present. Class-body imports may execute during definition; no deferral is inferred.

## MULTI_SCC_AND_SELF_LOOP_REGRESSIONS
DIRECT_EVIDENCE: Tests passed for two independent structural SCCs with distinct candidate topologies and for a self-loop candidate. Empty acyclic input returns no components.

## DETERMINISM_AND_IMMUTABILITY
DIRECT_EVIDENCE: Repeated calls yield equal frozen dataclasses; asdict serializes to JSON; attempted mutation raises FrozenInstanceError; source graph and evidence stay equal to their original values in tests.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0; canonical diagnostics fresh.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 reported paths; canonical diagnostics fresh.

## NO_SAFETY_CERTIFICATION
The result evidence_scope is ACTIVATION_CANDIDATES_NOT_RUNTIME_SAFETY. Even an acyclic direct-candidate projection does not classify the original SCC as SAFE, FALSE_POSITIVE or RESOLVED.

## NO_WARNING_SUPPRESSION
No diagnostic policy, warning suppression, resolver or cycle detection change.

## UNRESOLVED_LIMITATIONS
UNKNOWN: Runtime activation and actual Python import resolution remain outside this view. Guard truth, call timing and class-body execution are not determined. The view was verified by focused tests; it was not run over the current 72-edge real SCC snapshot in this stage.

## FINAL_VERDICT
B0G4C10_PASS

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/activation_view.py b/contextor/core/cycle_semantics/activation_view.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/activation_view.py
@@ -0,0 +1,165 @@
+"""Candidate import activation topology for source-attributed cyclic SCCs.
+
+Retains every canonical hard edge. Top-level lexical sites can only support
+candidate import activation, never runtime reachability or safety decisions.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from .edge_sites import CyclicImportSiteReport
+from .scc import ImportCycleTopology, analyze_import_cycle_topology
+
+_DIRECT = frozenset({"DIRECT_MODULE", "FROM_BASE"})
+_INDIRECT = frozenset({"OPTIONAL_FROM_CHILD", "PARENT_INITIALIZER"})
+
+
+@dataclass(frozen=True)
+class EdgeActivationView:
+    source: str
+    target: str
+    source_status: str
+    classification: str
+    site_count: int
+    unguarded_direct_count: int
+    function_scoped_count: int
+    guarded_top_level_count: int
+    other_scoped_count: int
+    indirect_candidate_count: int
+
+
+@dataclass(frozen=True)
+class SCCActivationView:
+    members: tuple[str, ...]
+    edges: tuple[EdgeActivationView, ...]
+    unguarded_direct_edges: tuple[tuple[str, str], ...]
+    unguarded_direct_topology: ImportCycleTopology
+    unresolved_edges: int
+    evidence_scope: str = "INTERNAL_UNGUARDED_LEXICAL_SUBGRAPH_ONLY"
+
+
+@dataclass(frozen=True)
+class CycleActivationViewReport:
+    structural_topology: ImportCycleTopology
+    components: tuple[SCCActivationView, ...]
+    evidence_scope: str = "ACTIVATION_CANDIDATES_NOT_RUNTIME_SAFETY"
+
+
+def analyze_cycle_activation_view(
+    import_sites: CyclicImportSiteReport,
+) -> CycleActivationViewReport:
+    """Project each retained internal edge onto candidate activation classes.
+
+    Even a cycle-free unguarded subset cannot certify the original SCC as safe:
+    a function-scoped import may execute during module initialization.
+    """
+    if not isinstance(import_sites, CyclicImportSiteReport):
+        raise TypeError("import_sites must be CyclicImportSiteReport")
+
+    views: list[SCCActivationView] = []
+
+    for component in import_sites.components:
+        edge_views: list[EdgeActivationView] = []
+        selected: dict[str, set[str]] = {
+            member: set() for member in component.members
+        }
+
+        for edge in component.internal_edges:
+            sites = edge.sites
+
+            direct = sum(
+                site.activation_scope == "MODULE_TOP_LEVEL"
+                and site.match_kind in _DIRECT
+                for site in sites
+            )
+
+            functions = sum(
+                site.activation_scope == "FUNCTION_SCOPED"
+                for site in sites
+            )
+
+            guarded = sum(
+                site.activation_scope == "GUARDED_TOP_LEVEL"
+                for site in sites
+            )
+
+            other = sum(
+                site.activation_scope == "OTHER_SCOPED"
+                for site in sites
+            )
+
+            indirect = sum(
+                site.match_kind in _INDIRECT
+                for site in sites
+            )
+
+            unguarded_indirect = any(
+                site.activation_scope == "MODULE_TOP_LEVEL"
+                and site.match_kind in _INDIRECT
+                for site in sites
+            )
+
+            if edge.status != "LEXICAL_CANDIDATES" or not sites:
+                classification = "UNRESOLVED_SOURCE_SITE"
+
+            elif direct:
+                classification = "UNGUARDED_DIRECT_CANDIDATE"
+                selected[edge.source].add(edge.target)
+
+            elif unguarded_indirect:
+                classification = "INDIRECT_TOP_LEVEL_CANDIDATE"
+
+            elif guarded:
+                classification = "GUARDED_TOP_LEVEL_CANDIDATE"
+
+            elif other:
+                classification = "OTHER_SCOPE_CANDIDATE"
+
+            elif functions:
+                classification = "CALL_DEPENDENT_CANDIDATE"
+
+            else:
+                classification = "UNRECOGNIZED_SITE_SEMANTICS"
+
+            edge_views.append(
+                EdgeActivationView(
+                    edge.source,
+                    edge.target,
+                    edge.status,
+                    classification,
+                    len(sites),
+                    direct,
+                    functions,
+                    guarded,
+                    other,
+                    indirect,
+                )
+            )
+
+        direct_edges = tuple(
+            (source, target)
+            for source in sorted(selected)
+            for target in sorted(selected[source])
+        )
+
+        views.append(
+            SCCActivationView(
+                component.members,
+                tuple(edge_views),
+                direct_edges,
+                analyze_import_cycle_topology(selected),
+                sum(
+                    edge.classification in {
+                        "UNRESOLVED_SOURCE_SITE",
+                        "UNRECOGNIZED_SITE_SEMANTICS",
+                    }
+                    for edge in edge_views
+                ),
+            )
+        )
+
+    return CycleActivationViewReport(
+        structural_topology=import_sites.topology,
+        components=tuple(views),
+    )

diff --git a/tests/test_cycle_semantics_activation_view.py b/tests/test_cycle_semantics_activation_view.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_activation_view.py
@@ -0,0 +1,444 @@
+from dataclasses import asdict, FrozenInstanceError
+import json
+
+import pytest
+
+from contextor.core.cycle_semantics.scc import (
+    analyze_import_cycle_topology,
+)
+from contextor.core.cycle_semantics.edge_sites import (
+    CyclicImportSiteReport,
+    SCCImportSiteEvidence,
+    HardEdgeSiteEvidence,
+    LexicalEdgeSite,
+)
+from contextor.core.cycle_semantics.activation_view import (
+    analyze_cycle_activation_view as analyze,
+)
+
+
+def _site(
+    activation="MODULE_TOP_LEVEL",
+    kind="FROM_BASE",
+    ordinal=0,
+):
+    return LexicalEdgeSite(
+        ordinal,
+        ordinal + 1,
+        0,
+        "IMPORT_FROM",
+        kind,
+        "b",
+        None,
+        (),
+        (),
+        activation,
+    )
+
+
+def _report(graph, data):
+    topology = analyze_import_cycle_topology(graph)
+    components = []
+
+    for scc in topology.cyclic_components:
+        edges = []
+
+        for src, dst in scc.internal_edges:
+            specs = data.get((src, dst))
+
+            if specs is None:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        src,
+                        dst,
+                        "SOURCE_MISSING_OR_INVALID",
+                        (),
+                    )
+                )
+
+            elif specs:
+                sites = tuple(
+                    _site(*item)
+                    for item in specs
+                )
+
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        src,
+                        dst,
+                        "LEXICAL_CANDIDATES",
+                        sites,
+                    )
+                )
+
+            else:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        src,
+                        dst,
+                        "NO_MATCHING_LEXICAL_SITE",
+                        (),
+                    )
+                )
+
+        components.append(
+            SCCImportSiteEvidence(
+                scc.members,
+                tuple(edges),
+                sum(
+                    x.status == "LEXICAL_CANDIDATES"
+                    for x in edges
+                ),
+                sum(
+                    x.status != "LEXICAL_CANDIDATES"
+                    for x in edges
+                ),
+            )
+        )
+
+    return CyclicImportSiteReport(
+        topology,
+        tuple(components),
+    )
+
+
+def test_direct_two_node_cycle_remains_candidate():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [()],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    component = result.components[0]
+
+    assert len(
+        component.unguarded_direct_topology.cyclic_components
+    ) == 1
+
+    assert component.unguarded_direct_edges == (
+        ("a", "b"),
+        ("b", "a"),
+    )
+
+    assert all(
+        edge.classification == "UNGUARDED_DIRECT_CANDIDATE"
+        for edge in component.edges
+    )
+
+
+def test_function_scoped_reverse_does_not_enter_direct_subgraph():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    ("FUNCTION_SCOPED", "FROM_BASE", 0)
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    component = result.components[0]
+
+    assert len(result.structural_topology.cyclic_components) == 1
+
+    assert len(
+        component.unguarded_direct_topology.cyclic_components
+    ) == 0
+
+    assert (
+        component.edges[0].classification
+        == "CALL_DEPENDENT_CANDIDATE"
+    )
+
+    assert result.evidence_scope.endswith(
+        "NOT_RUNTIME_SAFETY"
+    )
+
+
+def test_call_dependent_cycle_not_certified_safe():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    ("FUNCTION_SCOPED", "FROM_BASE", 0)
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    assert "SAFE" not in [
+        edge.classification
+        for edge in result.components[0].edges
+    ]
+
+    assert len(result.components[0].edges) == 2
+
+
+def test_indirect_parent_candidate_is_not_unguarded_direct():
+    result = analyze(
+        _report(
+            {"p": {"c"}, "c": {"p"}},
+            {
+                ("p", "c"): [
+                    ("MODULE_TOP_LEVEL", "OPTIONAL_FROM_CHILD", 0)
+                ],
+                ("c", "p"): [
+                    ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER", 0)
+                ],
+            },
+        )
+    )
+
+    component = result.components[0]
+
+    assert all(
+        edge.classification == "INDIRECT_TOP_LEVEL_CANDIDATE"
+        for edge in component.edges
+    )
+
+    assert not component.unguarded_direct_edges
+
+    assert all(
+        edge.indirect_candidate_count == 1
+        for edge in component.edges
+    )
+
+
+def test_guarded_top_level_not_promoted():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    ("GUARDED_TOP_LEVEL", "FROM_BASE", 0)
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    assert (
+        result.components[0].edges[0].classification
+        == "GUARDED_TOP_LEVEL_CANDIDATE"
+    )
+
+    assert len(
+        result.components[0]
+        .unguarded_direct_topology.cyclic_components
+    ) == 0
+
+
+def test_other_scoped_class_body_not_mistaken_for_deferral():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    ("OTHER_SCOPED", "FROM_BASE", 0)
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    assert (
+        result.components[0].edges[0].classification
+        == "OTHER_SCOPE_CANDIDATE"
+    )
+
+
+def test_mixed_eager_and_function_sites_preserved():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    (),
+                    ("FUNCTION_SCOPED", "FROM_BASE", 1),
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    component = result.components[0]
+    edge = component.edges[0]
+
+    assert (
+        edge.site_count,
+        edge.unguarded_direct_count,
+        edge.function_scoped_count,
+    ) == (2, 1, 1)
+
+    assert (
+        edge.classification
+        == "UNGUARDED_DIRECT_CANDIDATE"
+    )
+
+    assert len(
+        component.unguarded_direct_topology.cyclic_components
+    ) == 1
+
+
+def test_missing_source_and_unmatched_remain_explicit():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [],
+                ("b", "a"): None,
+            },
+        )
+    )
+
+    component = result.components[0]
+
+    assert len(component.edges) == 2
+    assert component.unresolved_edges == 2
+
+    assert {
+        edge.source_status
+        for edge in component.edges
+    } == {
+        "NO_MATCHING_LEXICAL_SITE",
+        "SOURCE_MISSING_OR_INVALID",
+    }
+
+
+def test_indirect_function_counts_as_call_dependent():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": {"a"}},
+            {
+                ("a", "b"): [
+                    ("FUNCTION_SCOPED", "PARENT_INITIALIZER", 0)
+                ],
+                ("b", "a"): [()],
+            },
+        )
+    )
+
+    edge = result.components[0].edges[0]
+
+    assert (
+        edge.function_scoped_count,
+        edge.indirect_candidate_count,
+    ) == (1, 1)
+
+    assert (
+        edge.classification
+        == "CALL_DEPENDENT_CANDIDATE"
+    )
+
+
+def test_multiple_sccs_preserved_separately():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "x": {"y"},
+        "y": {"x"},
+    }
+
+    data = {
+        ("a", "b"): [()],
+        ("b", "a"): [
+            ("FUNCTION_SCOPED", "FROM_BASE", 0)
+        ],
+        ("x", "y"): [()],
+        ("y", "x"): [()],
+    }
+
+    result = analyze(_report(graph, data))
+
+    assert len(result.components) == 2
+
+    assert tuple(
+        component.members
+        for component in result.components
+    ) == (
+        ("a", "b"),
+        ("x", "y"),
+    )
+
+    assert [
+        len(
+            component.unguarded_direct_topology.cyclic_components
+        )
+        for component in result.components
+    ] == [0, 1]
+
+
+def test_self_loop_supported():
+    result = analyze(
+        _report(
+            {"a": {"a"}},
+            {("a", "a"): [()]},
+        )
+    )
+
+    assert len(
+        result.components[0]
+        .unguarded_direct_topology.cyclic_components
+    ) == 1
+
+
+def test_empty_no_cycles():
+    result = analyze(
+        _report(
+            {"a": {"b"}, "b": set()},
+            {},
+        )
+    )
+
+    assert result.components == ()
+
+
+def test_deterministic_serializable_immutable_input_unchanged():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+    }
+
+    projection = _report(
+        graph,
+        {
+            ("a", "b"): [()],
+            ("b", "a"): [()],
+        },
+    )
+
+    first = analyze(projection)
+    second = analyze(projection)
+
+    assert first == second
+
+    json.dumps(asdict(first))
+
+    with pytest.raises(FrozenInstanceError):
+        first.components[0].unresolved_edges = 99
+
+    assert graph == {
+        "a": {"b"},
+        "b": {"a"},
+    }
+
+    assert projection == _report(
+        graph,
+        {
+            ("a", "b"): [()],
+            ("b", "a"): [()],
+        },
+    )
+
+
+def test_invalid_input():
+    with pytest.raises(TypeError):
+        analyze(None)
```
