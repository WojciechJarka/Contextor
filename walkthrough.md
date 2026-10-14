TASK: CONTEXTOR_B0G4C17_CYCLE_EVIDENCE_DIGEST
HEAD_BEFORE: a2230967560af8ecde7772138ecb0514e354b09a
HEAD_AFTER: a2230967560af8ecde7772138ecb0514e354b09a
GIT_STATUS:
?? contextor/core/cycle_semantics/diagnostic_view.py
?? tests/test_cycle_semantics_diagnostic_view.py

LIVE_REVISION_BEFORE: 443
LIVE_REVISION_AFTER: 445
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242
FILES_CHANGED:
- contextor/core/cycle_semantics/diagnostic_view.py
- tests/test_cycle_semantics_diagnostic_view.py
walkthrough.md is the report artifact. No existing source/test file changed.
CONTRACT_VERIFICATION: CONTRACT_PROVED. Existing frozen SCC, lexical-site, activation-view and closure-witness report dataclasses match supplied design. Pre-edit four owner modules were workspace_sync=verified and canonical state fresh at revision 443. Contextor consumers: scc 6, edge_sites 5, activation_view 3, closure_witness 1; activation_view blast radius direct consumers 3. New implementation copied literally from auditor-supplied content; no package export or reporting integration.
INPUT_CONSISTENCY_GATES: TEST_COVERED type checks and recomputed activation/closure reports reject mismatches; component membership, internal edge identities, and lexical count checks remain explicit.
STRUCTURAL_EDGE_PRESERVATION: TEST_COVERED digest retains every structural internal edge with lexical and activation evidence; no structural graph mutation.
LEXICAL_SITE_PRESERVATION: TEST_COVERED function-scoped, guarded, indirect, missing, and unmatched evidence retained in edge rows.
DIRECT_CYCLE_DIAGNOSIS: TEST_COVERED direct cyclic projected subgraph receives UNGUARDED_DIRECT_CYCLIC_SUBGRAPH; structural SCC remains distinct.
SINGLE_EDGE_CLOSURE_DIAGNOSIS: TEST_COVERED witness and closed walk retained on non-direct edge; category distinguishes closure from direct cycle.
MULTI_NON_DIRECT_LIMITATIONS: TEST_COVERED two non-direct edges without one-edge direct return remain in non_direct_without_direct_return, without safety verdict.
UNRESOLVED_SOURCE_EVIDENCE: TEST_COVERED SOURCE_MISSING_OR_INVALID and NO_MATCHING_LEXICAL_SITE retained; unresolved counts explicit.
SCC_AND_SELF_LOOP_REGRESSIONS: TEST_COVERED independent SCCs and self-loops.
DETERMINISM_AND_IMMUTABILITY: TEST_COVERED deterministic equality, frozen result, JSON serialization, input representations unchanged, source_snapshot_binding=NOT_VERIFIED_BY_DIGEST.
ISOLATED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_diagnostic_view.py => 17 passed in 1.10s.
FOCUSED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q [the 17 task-specified cycle_semantics test files] => 289 passed in 18.19s.
LIVE_SYNCHRONIZATION: DIRECT_EVIDENCE desktop_watcher UPDATED diagnostic_view.py revision 444 and test_cycle_semantics_diagnostic_view.py revision 445; continuous event history, same epoch, resync_required=false. Both workspace_sync=verified at revision 445.
CANONICAL_FRESHNESS: Revision 445, syntax/graph/cycles/collisions fresh; both new modules canonical_state=fresh and workspace_sync=verified.
COLLISIONS_BEFORE_AFTER: 0/fresh -> 4/fresh. DIRECT_EVIDENCE four NAME_COLLISION warnings for variable names D, F, G, I between tests.test_cycle_semantics_closure_witness and tests.test_cycle_semantics_diagnostic_view. The supplied test content introduced constants with the same names but different tuple values. get_live_events at revision 445 reported collision additions (bounded diagnostic_changes total 4, truncated). get_name_collisions returned all four details. This violates the task PASS gate 'no structural warning changes' / 'no new name collisions'. Literal supplied design and scope prohibit altering the test content or warning policy.
STRUCTURAL_CYCLES_BEFORE_AFTER: 16/fresh -> 16/fresh. Exact cycle path identity not independently compared.
NO_RUNTIME_SAFETY_CERTIFICATION: Digest reports UNKNOWN_NOT_EVALUATED; no runtime safety or failure verdict, no actual production SCC import as analysis target.
NO_WARNING_SUPPRESSION: No warning-policy, graph, resolver, diagnostic or existing source changes.
UNRESOLVED_LIMITATIONS: New test constants cause four canonical name-collision warnings. A revised auditor-authorized test design is needed for FINAL PASS; no independent redesign was applied. Source snapshot atomicity remains NOT_VERIFIED_BY_DIGEST by contract.
FINAL_VERDICT: B0G4C17_PARTIAL

FULL_DIFFS:
diff --git a/contextor/core/cycle_semantics/diagnostic_view.py b/contextor/core/cycle_semantics/diagnostic_view.py
new file mode 100644
index 0000000..978c355
--- /dev/null
+++ b/contextor/core/cycle_semantics/diagnostic_view.py
@@ -0,0 +1,204 @@
+"""Immutable structural and lexical cycle-evidence digest.
+
+Combines already approved analysis reports without execution or source reads.
+No runtime safety, failure or canonical warning policy is inferred.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from .activation_view import (
+    CycleActivationViewReport,
+    EdgeActivationView,
+    analyze_cycle_activation_view,
+)
+from .closure_witness import (
+    NonDirectClosureWitness,
+    SingleEdgeClosureReport,
+    analyze_single_edge_cycle_closures,
+)
+from .edge_sites import (
+    CyclicImportSiteReport,
+    HardEdgeSiteEvidence,
+)
+from .scc import CyclicImportComponent, ImportCycleTopology
+
+
+@dataclass(frozen=True)
+class CycleDiagnosticEdge:
+    source: str
+    target: str
+    lexical: HardEdgeSiteEvidence
+    activation: EdgeActivationView
+    in_direct_candidate_graph: bool
+    single_edge_closure: NonDirectClosureWitness | None
+
+
+@dataclass(frozen=True)
+class SCCCycleDiagnosis:
+    members: tuple[str, ...]
+    structural_kind: str
+    category: str
+    structural_edge_count: int
+    matched_edge_count: int
+    unresolved_edge_count: int
+    direct_candidate_edge_count: int
+    non_direct_candidate_edge_count: int
+    direct_cyclic_components: tuple[CyclicImportComponent, ...]
+    single_edge_closures: tuple[NonDirectClosureWitness, ...]
+    non_direct_without_direct_return: tuple[tuple[str, str], ...]
+    edges: tuple[CycleDiagnosticEdge, ...]
+    runtime_execution_status: str = "UNKNOWN_NOT_EVALUATED"
+
+
+@dataclass(frozen=True)
+class CycleEvidenceDigest:
+    structural_topology: ImportCycleTopology
+    components: tuple[SCCCycleDiagnosis, ...]
+    evidence_scope: str = "STRUCTURAL_AND_LEXICAL_NOT_RUNTIME"
+    source_snapshot_binding: str = "NOT_VERIFIED_BY_DIGEST"
+
+
+def build_cycle_evidence_digest(
+    sites: CyclicImportSiteReport,
+    activation: CycleActivationViewReport,
+    closures: SingleEdgeClosureReport,
+) -> CycleEvidenceDigest:
+    """Join consistent immutable reports without modifying original graphs.
+
+    Recomputing the approved pure projections rejects mismatched or altered
+    reports rather than silently combining inconsistent source evidence.
+    It cannot authenticate a canonical LIVE revision or source fingerprints.
+    """
+    if not isinstance(sites, CyclicImportSiteReport):
+        raise TypeError("sites must be CyclicImportSiteReport")
+    if not isinstance(activation, CycleActivationViewReport):
+        raise TypeError("activation must be CycleActivationViewReport")
+    if not isinstance(closures, SingleEdgeClosureReport):
+        raise TypeError("closures must be SingleEdgeClosureReport")
+
+    if activation != analyze_cycle_activation_view(sites):
+        raise ValueError("activation evidence differs from lexical sources")
+
+    if closures != analyze_single_edge_cycle_closures(
+        activation,
+        sites,
+    ):
+        raise ValueError("closure evidence differs from activation sources")
+
+    topology = sites.topology
+
+    if not (
+        len(topology.cyclic_components)
+        == len(sites.components)
+        == len(activation.components)
+        == len(closures.components)
+    ):
+        raise ValueError("SCC component cardinalities differ")
+
+    output: list[SCCCycleDiagnosis] = []
+
+    for structural, source, view, closure in zip(
+        topology.cyclic_components,
+        sites.components,
+        activation.components,
+        closures.components,
+    ):
+        if not (
+            structural.members
+            == source.members
+            == view.members
+            == closure.members
+        ):
+            raise ValueError("canonical SCC member identities differ")
+
+        source_ids = tuple(
+            (item.source, item.target)
+            for item in source.internal_edges
+        )
+
+        view_ids = tuple(
+            (item.source, item.target)
+            for item in view.edges
+        )
+
+        if (
+            source_ids != structural.internal_edges
+            or view_ids != structural.internal_edges
+        ):
+            raise ValueError("structural internal edge identities differ")
+
+        matched = sum(
+            item.status == "LEXICAL_CANDIDATES"
+            for item in source.internal_edges
+        )
+        unresolved = len(source.internal_edges) - matched
+
+        if (
+            source.matched_edge_count != matched
+            or source.unresolved_edge_count != unresolved
+        ):
+            raise ValueError("lexical evidence counts differ")
+
+        direct = set(view.unguarded_direct_edges)
+
+        witnesses = {
+            (item.source, item.target): item
+            for item in closure.single_edge_witnesses
+        }
+
+        edge_rows = tuple(
+            CycleDiagnosticEdge(
+                source=lexical.source,
+                target=lexical.target,
+                lexical=lexical,
+                activation=classification,
+                in_direct_candidate_graph=(
+                    (lexical.source, lexical.target) in direct
+                ),
+                single_edge_closure=witnesses.get(
+                    (lexical.source, lexical.target)
+                ),
+            )
+            for lexical, classification in zip(
+                source.internal_edges,
+                view.edges,
+            )
+        )
+
+        if view.unguarded_direct_topology.cyclic_components:
+            category = "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH"
+        elif closure.single_edge_witnesses:
+            category = (
+                "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES"
+            )
+        else:
+            category = (
+                "ACYCLIC_DIRECT_SUBGRAPH_NO_SINGLE_EDGE_CLOSURE"
+            )
+
+        output.append(
+            SCCCycleDiagnosis(
+                members=structural.members,
+                structural_kind=structural.kind,
+                category=category,
+                structural_edge_count=len(edge_rows),
+                matched_edge_count=matched,
+                unresolved_edge_count=unresolved,
+                direct_candidate_edge_count=len(direct),
+                non_direct_candidate_edge_count=(
+                    len(edge_rows) - len(direct)
+                ),
+                direct_cyclic_components=(
+                    view.unguarded_direct_topology.cyclic_components
+                ),
+                single_edge_closures=closure.single_edge_witnesses,
+                non_direct_without_direct_return=(
+                    closure.non_direct_without_direct_return
+                ),
+                edges=edge_rows,
+            )
+        )
+
+    return CycleEvidenceDigest(topology, tuple(output))

diff --git a/tests/test_cycle_semantics_diagnostic_view.py b/tests/test_cycle_semantics_diagnostic_view.py
new file mode 100644
index 0000000..d922566
--- /dev/null
+++ b/tests/test_cycle_semantics_diagnostic_view.py
@@ -0,0 +1,417 @@
+"""Structural/lexical evidence digest regressions, never safety verdicts."""
+
+import json
+from dataclasses import FrozenInstanceError, asdict, replace
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
+    analyze_cycle_activation_view,
+)
+from contextor.core.cycle_semantics.closure_witness import (
+    analyze_single_edge_cycle_closures,
+)
+from contextor.core.cycle_semantics.diagnostic_view import (
+    build_cycle_evidence_digest,
+)
+
+
+D = ("MODULE_TOP_LEVEL", "FROM_BASE")
+F = ("FUNCTION_SCOPED", "FROM_BASE")
+G = ("GUARDED_TOP_LEVEL", "FROM_BASE")
+I = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER")
+
+
+def _pipeline(graph, specs):
+    topology = analyze_import_cycle_topology(graph)
+    components = []
+
+    for structural in topology.cyclic_components:
+        edges = []
+
+        for source, target in structural.internal_edges:
+            specification = specs.get((source, target), None)
+
+            if specification is None:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source, target,
+                        "SOURCE_MISSING_OR_INVALID", (),
+                    )
+                )
+            elif not specification:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source, target,
+                        "NO_MATCHING_LEXICAL_SITE", (),
+                    )
+                )
+            else:
+                lexical = tuple(
+                    LexicalEdgeSite(
+                        ordinal=ordinal,
+                        line=ordinal + 1,
+                        column=0,
+                        form="IMPORT_FROM",
+                        match_kind=kind,
+                        requested_name=target,
+                        matched_member=None,
+                        scopes=(),
+                        controls=(),
+                        activation_scope=scope,
+                    )
+                    for ordinal, (scope, kind) in enumerate(specification)
+                )
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source, target,
+                        "LEXICAL_CANDIDATES", lexical,
+                    )
+                )
+
+        components.append(
+            SCCImportSiteEvidence(
+                members=structural.members,
+                internal_edges=tuple(edges),
+                matched_edge_count=sum(
+                    item.status == "LEXICAL_CANDIDATES"
+                    for item in edges
+                ),
+                unresolved_edge_count=sum(
+                    item.status != "LEXICAL_CANDIDATES"
+                    for item in edges
+                ),
+            )
+        )
+
+    sites = CyclicImportSiteReport(
+        topology, tuple(components),
+    )
+    activation = analyze_cycle_activation_view(sites)
+    closures = analyze_single_edge_cycle_closures(
+        activation, sites,
+    )
+    return sites, activation, closures
+
+
+def _digest(graph, specs):
+    return build_cycle_evidence_digest(
+        *_pipeline(graph, specs)
+    )
+
+
+def test_direct_cycle_is_still_structural():
+    result = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [D]},
+    )
+    component = result.components[0]
+
+    assert component.category == (
+        "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH"
+    )
+    assert component.structural_edge_count == 2
+    assert component.direct_candidate_edge_count == 2
+    assert len(component.direct_cyclic_components) == 1
+    assert len(component.edges) == 2
+    assert component.single_edge_closures == ()
+
+
+def test_function_local_edge_retains_closure_and_sites():
+    result = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+    component = result.components[0]
+
+    assert component.category == (
+        "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES"
+    )
+    assert component.direct_candidate_edge_count == 1
+    assert component.non_direct_candidate_edge_count == 1
+
+    row = next(
+        item for item in component.edges
+        if (item.source, item.target) == ("b", "a")
+    )
+    assert not row.in_direct_candidate_graph
+    assert row.activation.classification == (
+        "CALL_DEPENDENT_CANDIDATE"
+    )
+    assert row.lexical.sites[0].activation_scope == (
+        "FUNCTION_SCOPED"
+    )
+    assert row.single_edge_closure.closed_walk == (
+        "b", "a", "b"
+    )
+
+
+def test_multiple_nondirect_edges_without_one_edge_return():
+    component = _digest(
+        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
+        {
+            ("a", "b"): [D],
+            ("b", "c"): [F],
+            ("c", "a"): [F],
+        },
+    ).components[0]
+
+    assert component.category == (
+        "ACYCLIC_DIRECT_SUBGRAPH_NO_SINGLE_EDGE_CLOSURE"
+    )
+    assert component.structural_edge_count == 3
+    assert component.single_edge_closures == ()
+    assert component.non_direct_candidate_edge_count == 2
+    assert component.non_direct_without_direct_return == (
+        ("b", "c"), ("c", "a")
+    )
+
+
+def test_guarded_candidate_keeps_uncertainty():
+    component = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [G]},
+    ).components[0]
+
+    witness = component.single_edge_closures[0]
+    assert witness.classification == (
+        "GUARDED_TOP_LEVEL_CANDIDATE"
+    )
+    assert component.runtime_execution_status == (
+        "UNKNOWN_NOT_EVALUATED"
+    )
+
+
+def test_indirect_package_candidate_keeps_uncertainty():
+    component = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [I]},
+    ).components[0]
+
+    assert component.single_edge_closures[0].classification == (
+        "INDIRECT_TOP_LEVEL_CANDIDATE"
+    )
+    assert component.direct_candidate_edge_count == 1
+
+
+def test_missing_lexical_evidence_is_not_dropped():
+    component = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D]},
+    ).components[0]
+
+    assert component.structural_edge_count == 2
+    assert component.matched_edge_count == 1
+    assert component.unresolved_edge_count == 1
+    assert len(component.edges) == 2
+
+    missing = next(
+        item for item in component.edges
+        if item.source == "b"
+    )
+    assert missing.lexical.status == (
+        "SOURCE_MISSING_OR_INVALID"
+    )
+    assert missing.single_edge_closure is not None
+
+
+def test_unmatched_lexical_site_preserved():
+    component = _digest(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): []},
+    ).components[0]
+
+    assert any(
+        row.lexical.status == "NO_MATCHING_LEXICAL_SITE"
+        for row in component.edges
+    )
+    assert component.unresolved_edge_count == 1
+
+
+def test_two_independent_sccs_remain_distinct():
+    component_one, component_two = _digest(
+        {
+            "a": {"b"}, "b": {"a"},
+            "x": {"y"}, "y": {"x"},
+        },
+        {
+            ("a", "b"): [D], ("b", "a"): [F],
+            ("x", "y"): [D], ("y", "x"): [D],
+        },
+    ).components
+
+    assert component_one.members == ("a", "b")
+    assert component_two.members == ("x", "y")
+    assert len(component_one.single_edge_closures) == 1
+    assert len(component_two.direct_cyclic_components) == 1
+
+
+@pytest.mark.parametrize(
+    "site",
+    [D, F],
+)
+def test_self_loop_preserved(site):
+    component = _digest(
+        {"a": {"a"}},
+        {("a", "a"): [site]},
+    ).components[0]
+
+    assert component.structural_kind == "SELF_LOOP"
+    assert component.structural_edge_count == 1
+    assert len(component.edges) == 1
+
+
+def test_mismatched_activation_rejected():
+    sites, activation, closures = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+
+    view = activation.components[0]
+    changed_edge = replace(
+        view.edges[0],
+        classification="CALL_DEPENDENT_CANDIDATE",
+    )
+    changed_view = replace(
+        view,
+        edges=(changed_edge,) + view.edges[1:],
+    )
+    invalid = replace(
+        activation,
+        components=(changed_view,),
+    )
+
+    with pytest.raises(ValueError):
+        build_cycle_evidence_digest(
+            sites, invalid, closures,
+        )
+
+
+def test_mismatched_closure_rejected():
+    sites, activation, closures = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+
+    component = closures.components[0]
+    witness = component.single_edge_witnesses[0]
+    wrong = replace(
+        witness,
+        direct_return_path=("a",),
+    )
+    invalid_component = replace(
+        component,
+        single_edge_witnesses=(wrong,),
+    )
+    invalid = replace(
+        closures,
+        components=(invalid_component,),
+    )
+
+    with pytest.raises(ValueError):
+        build_cycle_evidence_digest(
+            sites, activation, invalid,
+        )
+
+
+def test_mismatched_site_topology_rejected():
+    sites, activation, closures = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+
+    wrong_component = replace(
+        sites.components[0],
+        internal_edges=tuple(
+            reversed(sites.components[0].internal_edges)
+        ),
+    )
+    invalid = replace(
+        sites,
+        components=(wrong_component,),
+    )
+
+    with pytest.raises(ValueError):
+        build_cycle_evidence_digest(
+            invalid, activation, closures,
+        )
+
+
+def test_mismatched_site_counts_rejected():
+    sites, activation, closures = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+    wrong = replace(
+        sites.components[0],
+        matched_edge_count=0,
+    )
+    invalid = replace(
+        sites,
+        components=(wrong,),
+    )
+
+    with pytest.raises(ValueError):
+        build_cycle_evidence_digest(
+            invalid, activation, closures,
+        )
+
+
+def test_determinism_immutability_and_json():
+    inputs = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+    before = tuple(repr(item) for item in inputs)
+
+    first = build_cycle_evidence_digest(*inputs)
+    second = build_cycle_evidence_digest(*inputs)
+
+    assert first == second
+    json.dumps(asdict(first))
+
+    with pytest.raises(FrozenInstanceError):
+        first.components[0].structural_edge_count = 9
+
+    assert before == tuple(repr(item) for item in inputs)
+    assert first.source_snapshot_binding == (
+        "NOT_VERIFIED_BY_DIGEST"
+    )
+
+
+def test_no_cycles_empty_digest():
+    result = _digest(
+        {"a": {"b"}, "b": set()},
+        {},
+    )
+    assert result.components == ()
+    assert result.structural_topology.cyclic_components == ()
+
+
+def test_bad_argument_types():
+    with pytest.raises(TypeError):
+        build_cycle_evidence_digest(None, None, None)
+
+    sites, activation, closures = _pipeline(
+        {"a": {"b"}, "b": {"a"}},
+        {("a", "b"): [D], ("b", "a"): [F]},
+    )
+
+    with pytest.raises(TypeError):
+        build_cycle_evidence_digest(
+            sites, None, closures,
+        )
+
+    with pytest.raises(TypeError):
+        build_cycle_evidence_digest(
+            sites, activation, None,
+        )
