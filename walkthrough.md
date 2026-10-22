# CONTEXTOR_CYCLE_PROOF_P0_INDEX_BOUND_SCC_MODEL_EVIDENCE

## TASK
Controlled implementation of a pure, deterministic index-bound SCC model-evidence consistency gate. This is not runtime SAFE certification and does not change warning policy.

## HEAD_BEFORE
a96ccf2e3fdb00c0cc39e37032c338ba9a54c62f. Before edits, only walkthrough.md was modified.

## HEAD_AFTER
a96ccf2e3fdb00c0cc39e37032c338ba9a54c62f. No commit made.

## FILES_CHANGED
- contextor/core/cycle_semantics/evidence.py
- tests/test_cycle_semantics_evidence.py
walkthrough.md is this required report and is excluded from source/test/docs changes.

## PRE_EDIT_ARCHITECTURE_AND_DIFF_PLAN
Contextor MCP established evidence.py as canonical owner of SourceBoundCycleEvidence and source-bound scenario assessment, with test-only confirmed consumers. Existing facade materialization remains separate. Planned and actual scope: add one frozen result contract and a read-only assessor in evidence.py; add distinct T01–T16 focused tests in test_cycle_semantics_evidence.py. No changes to scenario model, SCC algorithm, snapshot schema, public warning interfaces, or MCP.

## EXACT_IMPLEMENTATION
assess_index_bound_scc_models computes current structural topology and fingerprint_hard_edges from the supplied hard_edges. It checks snapshot graph hash, the source-evidence graph fingerprint using evidence.py's own _digest(normalized adjacency) representation, exact topology and one-to-one component identity. Per SCC it checks exact internal edges, reachable closure, complete unique signatures, SHA-256-shaped raw/AST signatures, equality to supplied index fingerprints, component token, complete cyclic snapshot coverage, no source issues, and cyclic observed/index fingerprint equality. Positive model classification is retained only with exact member entry assessments, complete coverage and all MODEL_PASS outcomes. Internal hazard is retained only with a matching SCC-internal early-binding event. Other conditions return INDETERMINATE and an explicit reason. Results are frozen, deterministic, and always carry SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED. No I/O, AST parsing, scenario rerun, graph mutation or warning action.

## SCC_IDENTITY_PROOF
The assessor recomputes analyze_import_cycle_topology(hard_edges), compares complete topology objects against snapshot.import_sites.topology and source_evidence.scenarios.topology, checks exact component sequence/count and each internal edge tuple, and emits exactly one output per structural cyclic SCC. Tests T08, T12, T13 and T14 cover tampered identity, two independent SCCs, self-loop and empty cyclic set. DFS paths are never enumerated or modified.

## SOURCE_INDEX_CONSISTENCY
The raw source fingerprint for every exact reachable-closure module must match indexed_fingerprints_by_module; missing, malformed, duplicate/extra closure identities and mismatch fail closed. Snapshot cyclic fingerprints must match the same index, with FILESYSTEM_STABLE_NON_ATOMIC coverage and no issues. Source-evidence graph fingerprint is verified with _digest(graph_items), not compared to snapshot.graph_sha256, which uses a different graph representation. The assessor also reconstructs each existing component evidence token. This only checks declared input consistency: ParsedSourceInput may carry AST and fingerprint values supplied by a caller without proof they came from authoritative bytes. No atomic graph/source/LIVE claim follows.

## MODEL_CLASSIFICATION_GATES
Allowed model outcomes are MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS, MODEL_INTERNAL_EARLY_BINDING_HAZARD and INDETERMINATE. Allowed evidence states are DECLARED_INPUTS_CONSISTENT, INCOMPLETE_EVIDENCE and EVIDENCE_MISMATCH. The new result contains exactly members, model_classification, evidence_state, reason, authority. No SAFE, runtime certification or warning suppression field was added. The semantic meaning of MODEL_PASS is unchanged.

## T01_T16_RESULTS
All T01–T16 passed in the targeted file:
- T01 mutual import, all entry pass: PASS.
- T02 early from-import binding hazard: PASS.
- T03 binding before read: PASS.
- T04 same graph, changed binding order: PASS.
- T05 raw hash mismatch plus malformed signature: PASS.
- T06 missing closure fingerprint: PASS.
- T07 snapshot and source graph fingerprint mismatches: PASS.
- T08 SCC edge/component mismatch plus token tamper: PASS.
- T09 partial cyclic cohort: PASS.
- T10 source issue: PASS.
- T11 one UNKNOWN entry: PASS.
- T12 two independent SCCs, separate verdicts: PASS.
- T13 self-loop: PASS.
- T14 no cyclic SCC: PASS.
- T15 repeatability and input immutability: PASS.
- T16 no warning/public API activation: PASS.
These are local T identifiers; no C01–C30 remapping was made.

## FOCUSED_NON_REGRESSION
Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_initialization_model.py
Actual final result: 71 passed in 3.61s, exit code 0. Earlier targeted run before a small validation hardening: 71 passed in 5.27s. git diff --check: exit code 0 (Git emitted only LF/CRLF conversion notices). No full pytest suite.

## RUNTIME_AUTHORITY_LIMITATION
Active 127.0.0.1:8765 listener owner PID 3128; process command is python.exe -u -m contextor.mcp_main; creation time 2026-10-22 12:08:36 local, before these edits. Contextor static blast radius of existing builder showed only a test consumer; literal import verification found no production/MCP import of cycle_semantics.evidence. The newly added symbol was not yet in canonical artifact registry at revision 624. Remote sys.modules of PID 3128 was not inspected or instrumented, so actual loaded-module state cannot be certified. This pure API is not currently exposed by MCP. If the process had imported evidence.py and needs to serve the new API, it needs reload/restart by the runtime owner. No restart was performed.

## LIVE_REVISION_BEFORE_AFTER
Before: revision 624, resync_required=false. After: revision 624, resync_required=false, continuity=continuous for after_revision=624. Aggregate architecture workspace_sync=unverified by contract. Target evidence.py blast-radius after edit reports workspace_sync=out_of_sync and advisory_warning that disk changed since canonical revision. Therefore LIVE adoption/freshness for edited code is not verified.

## WATCHER_EVENTS
get_live_events(after_revision=624): no canonical events, twice; no desktop_watcher event for these edits. No update_file call, FULL analysis or manual restart. The absent event does not prove no watcher exists; it leaves this post-edit gate unconfirmed.

## RESTART_REQUIREMENTS
MCP serving backend restart: conditional on whether PID 3128 had imported evidence.py and must serve the new module; loaded state UNKNOWN. No confirmed production static consumer, so no direct MCP API adoption was required for current registered tools. LIVE service restart: NO known requirement from this isolated pure module change. Agent performed no restarts.

## FULL_DIFFS
Complete actual unified diff of every changed source/test file follows.

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index b691410..b3aaa66 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -14,7 +14,12 @@ from dataclasses import dataclass
 
 from contextor.core.source import ParsedSourceInput
 
-from .scenarios import CycleScenarioReport, analyze_cycle_scenarios
+from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
+from .scc import analyze_import_cycle_topology
+from .initialization_model import ImportOrderAssessment
+from .scenarios import (
+    CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
+)
 
 EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/1"
 _MISSING = "MISSING"
@@ -56,6 +61,229 @@ class CycleEvidenceChange:
     after_token: str | None
 
 
+@dataclass(frozen=True)
+class SCCModelEvidenceAssessment:
+    members: tuple[str, ...]
+    model_classification: str
+    evidence_state: str
+    reason: str | None
+    authority: str = "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"
+
+
+def assess_index_bound_scc_models(
+    hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
+    indexed_fingerprints_by_module: Mapping[str, str],
+    snapshot: CycleSemanticsSnapshot,
+    source_evidence: SourceBoundCycleEvidence,
+) -> tuple[SCCModelEvidenceAssessment, ...]:
+    """Check declared index, structural and model evidence without refreshing it.
+
+    Caller-supplied AST provenance and LIVE generation are not certified here.
+    """
+    if not isinstance(indexed_fingerprints_by_module, Mapping):
+        raise TypeError("indexed fingerprints must be a mapping")
+    if not isinstance(snapshot, CycleSemanticsSnapshot):
+        raise TypeError("snapshot must be CycleSemanticsSnapshot")
+    if not isinstance(source_evidence, SourceBoundCycleEvidence):
+        raise TypeError("source_evidence must be SourceBoundCycleEvidence")
+
+    topology = analyze_import_cycle_topology(hard_edges)
+    graph_hash = fingerprint_hard_edges(hard_edges)
+    adjacency = {
+        source: tuple(sorted(set(targets)))
+        for source, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+    graph_items = tuple((node, adjacency[node]) for node in sorted(adjacency))
+
+    components = topology.cyclic_components
+    def result(members: tuple[str, ...], reason: str, *,
+               state: str = "EVIDENCE_MISMATCH") -> SCCModelEvidenceAssessment:
+        return SCCModelEvidenceAssessment(
+            members, "INDETERMINATE", state, reason,
+        )
+
+    if not components:
+        return ()
+
+    global_reason: str | None = None
+    if snapshot.graph_sha256 != graph_hash:
+        global_reason = "SNAPSHOT_GRAPH_FINGERPRINT_MISMATCH"
+    elif source_evidence.graph_fingerprint != _digest(graph_items):
+        global_reason = "SOURCE_GRAPH_FINGERPRINT_MISMATCH"
+    elif (
+        snapshot.import_sites.topology != topology
+        or source_evidence.scenarios.topology != topology
+    ):
+        global_reason = "SCC_TOPOLOGY_MISMATCH"
+    elif source_evidence.semantic_version != EVIDENCE_SEMANTIC_VERSION:
+        global_reason = "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
+    elif (
+        source_evidence.authority != "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
+        or source_evidence.scenarios.evidence_scope
+        != "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    ):
+        global_reason = "SOURCE_AUTHORITY_MISMATCH"
+    elif (
+        any(not isinstance(c, CycleComponentScenarios)
+            for c in source_evidence.scenarios.components)
+        or any(not isinstance(c, ComponentSourceEvidence)
+               for c in source_evidence.components)
+        or
+        len(snapshot.import_sites.components) != len(components)
+        or len(source_evidence.scenarios.components) != len(components)
+        or len(source_evidence.components) != len(components)
+        or tuple(site.members for site in snapshot.import_sites.components)
+        != tuple(c.members for c in components)
+        or tuple(c.members for c in source_evidence.scenarios.components)
+        != tuple(c.members for c in components)
+        or tuple(c.members for c in source_evidence.components)
+        != tuple(c.members for c in components)
+    ):
+        global_reason = "SCC_COMPONENT_IDENTITY_MISMATCH"
+
+    if global_reason is not None:
+        return tuple(result(c.members, global_reason) for c in components)
+
+    index = dict(indexed_fingerprints_by_module)
+    observed = dict(snapshot.observed_source_fingerprints)
+    cyclic_members = tuple(sorted(
+        member for component in components for member in component.members
+    ))
+    outputs: list[SCCModelEvidenceAssessment] = []
+    for position, (structural, scenario, evidence) in enumerate(zip(
+        components, source_evidence.scenarios.components,
+        source_evidence.components,
+    )):
+        members = structural.members
+        if scenario.internal_edges != structural.internal_edges:
+            outputs.append(result(members, "SCENARIO_INTERNAL_EDGES_MISMATCH"))
+            continue
+        site_edges = tuple(
+            (edge.source, edge.target)
+            for edge in snapshot.import_sites.components[position].internal_edges
+        )
+        if site_edges != structural.internal_edges:
+            outputs.append(result(members, "SNAPSHOT_INTERNAL_EDGES_MISMATCH"))
+            continue
+        if (
+            evidence.classification != scenario.classification
+            or evidence.coverage != scenario.coverage
+            or evidence.reason != scenario.reason
+        ):
+            outputs.append(result(members, "SCENARIO_EVIDENCE_MISMATCH"))
+            continue
+
+        closure = set(members)
+        pending = list(members)
+        while pending:
+            for target in adjacency[pending.pop()]:
+                if target not in closure:
+                    closure.add(target)
+                    pending.append(target)
+        expected_closure = tuple(sorted(closure))
+        signatures = evidence.source_signatures
+        if not isinstance(signatures, tuple) or any(
+            not isinstance(row, tuple) or len(row) != 3
+            for row in signatures
+        ):
+            outputs.append(result(members, "MALFORMED_SOURCE_SIGNATURES"))
+            continue
+        signature_names = tuple(
+            row[0] for row in signatures
+        )
+        if (
+            evidence.reachable_modules != expected_closure
+            or len(signatures) != len(expected_closure)
+            or signature_names != expected_closure
+        ):
+            outputs.append(result(members, "SOURCE_CLOSURE_IDENTITY_MISMATCH"))
+            continue
+        bad_source = next((
+            module for module, raw, ast_hash in signatures
+            if (
+                type(raw) is not str or len(raw) != 64
+                or any(ch not in "0123456789abcdef" for ch in raw)
+                or type(ast_hash) is not str or len(ast_hash) != 64
+                or any(ch not in "0123456789abcdef" for ch in ast_hash)
+                or type(index.get(module)) is not str
+                or index[module] != raw
+            )
+        ), None)
+        if bad_source is not None:
+            outputs.append(result(members, "SOURCE_INDEX_FINGERPRINT_MISMATCH:" + bad_source))
+            continue
+        subgraph = tuple((node, adjacency[node]) for node in expected_closure)
+        expected_token = _digest((
+            EVIDENCE_SEMANTIC_VERSION, members, subgraph, signatures,
+        ))
+        if evidence.evidence_token != expected_token:
+            outputs.append(result(members, "COMPONENT_EVIDENCE_TOKEN_MISMATCH"))
+            continue
+        if (
+            snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
+            or snapshot.source_issues
+            or tuple(sorted(observed)) != cyclic_members
+        ):
+            outputs.append(result(
+                members, "INCOMPLETE_CYCLIC_SOURCE_COHORT",
+                state="INCOMPLETE_EVIDENCE",
+            ))
+            continue
+        if (
+            snapshot.cyclic_modules != cyclic_members
+            or any(observed.get(member) != index.get(member) for member in members)
+        ):
+            outputs.append(result(members, "SNAPSHOT_SOURCE_IDENTITY_MISMATCH"))
+            continue
+        if (
+            scenario.evidence_scope != "CLOSED_FLAT_MODULE_FRESH_ENTRY_MODEL"
+            or scenario.coverage != "COMPLETE_FRESH_MEMBER_ENTRIES"
+            or not isinstance(scenario.entry_assessments, tuple)
+            or any(not isinstance(a, ImportOrderAssessment)
+                   for a in scenario.entry_assessments)
+            or tuple(a.entry_module for a in scenario.entry_assessments) != members
+            or any(a.outcome == "UNKNOWN" for a in scenario.entry_assessments)
+        ):
+            outputs.append(result(
+                members, "INCOMPLETE_MEMBER_ENTRY_ASSESSMENTS",
+                state="INCOMPLETE_EVIDENCE",
+            ))
+            continue
+        if scenario.classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS":
+            if all(a.outcome == "MODEL_PASS" for a in scenario.entry_assessments):
+                outputs.append(SCCModelEvidenceAssessment(
+                    members, scenario.classification,
+                    "DECLARED_INPUTS_CONSISTENT", None,
+                ))
+            else:
+                outputs.append(result(members, "MODEL_PASS_ENTRY_MISMATCH"))
+        elif scenario.classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD":
+            member_set = set(members)
+            if any(
+                a.outcome == "EARLY_BINDING_HAZARD"
+                and a.events
+                and a.events[-1].operation == "EARLY_BINDING_HAZARD"
+                and a.events[-1].module in member_set
+                and a.events[-1].target in member_set
+                for a in scenario.entry_assessments
+            ):
+                outputs.append(SCCModelEvidenceAssessment(
+                    members, scenario.classification,
+                    "DECLARED_INPUTS_CONSISTENT", None,
+                ))
+            else:
+                outputs.append(result(members, "INTERNAL_HAZARD_ENTRY_MISMATCH"))
+        else:
+            outputs.append(result(
+                members, scenario.reason or "INDETERMINATE_SCENARIO",
+                state="INCOMPLETE_EVIDENCE",
+            ))
+    return tuple(outputs)
+
+
 def build_source_bound_cycle_evidence(
     hard_edges: Mapping[str, set[str] | frozenset[str] | list[str] | tuple[str, ...]],
     parsed_sources: Mapping[str, ParsedSourceInput],
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index 2f3e6dc..bedc757 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -1,15 +1,22 @@
 import ast
 import hashlib
 import json
-from dataclasses import asdict
+from dataclasses import asdict, replace
 
 import pytest
 
 from contextor.core.source import ParsedSourceInput
 from contextor.core.cycle_semantics.evidence import (
+    SCCModelEvidenceAssessment,
+    assess_index_bound_scc_models as assess,
     build_source_bound_cycle_evidence as build,
     compare_source_bound_cycle_evidence as compare,
 )
+from contextor.core.cycle_semantics.contracts import (
+    CycleSemanticsSnapshot, fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
+from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
 
 
 def _sources(**source_map):
@@ -159,3 +166,185 @@ def test_snapshot_only_authority_no_warning_action():
     assert x.authority == "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
     assert x.scenarios.evidence_scope == "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
     assert "SAFE" not in x.components[0].classification
+
+
+def _bound(edges, sources):
+    parsed = _sources(**sources)
+    evidence = build(edges, parsed)
+    topology = evidence.scenarios.topology
+    cyclic = tuple(sorted(
+        name for component in topology.cyclic_components for name in component.members
+    ))
+    index = {name: source.source_fingerprint for name, source in parsed.items()}
+    snapshot = CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges(edges),
+        cyclic_modules=cyclic,
+        observed_source_fingerprints=tuple(
+            (name, index[name]) for name in cyclic
+        ),
+        source_issues=(),
+        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding="NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY",
+        runtime_execution_status="UNKNOWN_NOT_EVALUATED",
+        import_sites=analyze_cyclic_import_sites(edges, parsed),
+        conditional_discovery=ConditionalDiscoveryReport(
+            (), 0, (), 0, "COMPLETE",
+        ),
+    )
+    return index, snapshot, evidence
+
+
+PAIR = {"a": {"b"}, "b": {"a"}}
+PASS = {"a": "import b\nx=1", "b": "import a\ny=2"}
+HAZARD = {"a": "import b\nvalue=1", "b": "from a import value"}
+
+
+def _one(edges=PAIR, sources=PASS):
+    index, snapshot, evidence = _bound(edges, sources)
+    result = assess(edges, index, snapshot, evidence)
+    return result, index, snapshot, evidence
+
+
+def test_p0_t01_mutual_import_all_entries_pass():
+    result, _, _, _ = _one()
+    assert result == (SCCModelEvidenceAssessment(
+        ("a", "b"), "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+        "DECLARED_INPUTS_CONSISTENT", None,
+    ),)
+    assert result[0].authority == "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"
+
+
+def test_p0_t02_early_from_import_hazard():
+    result, _, _, _ = _one(sources=HAZARD)
+    assert result[0].model_classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    assert result[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+
+
+def test_p0_t03_symbol_bound_before_read():
+    sources = {"a": "value=1\nimport b", "b": "import a\nx=a.value"}
+    result, _, _, _ = _one(sources=sources)
+    assert result[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    assert result[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"
+
+
+def test_p0_t04_same_graph_changed_binding_order():
+    bad = _one(sources={"a": "import b\nvalue=1", "b": "import a\nx=a.value"})[0]
+    good = _one(sources={"a": "value=1\nimport b", "b": "import a\nx=a.value"})[0]
+    assert bad[0].model_classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
+    assert good[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_p0_t05_raw_source_fingerprint_mismatch():
+    _, index, snapshot, evidence = _one()
+    index["a"] = "0" * 64
+    result = assess(PAIR, index, snapshot, evidence)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
+    assert result[0].reason == "SOURCE_INDEX_FINGERPRINT_MISMATCH:a"
+    malformed = replace(evidence.components[0],
+                        source_signatures=(("a",),))
+    bad_evidence = replace(evidence, components=(malformed,))
+    assert assess(PAIR, index, snapshot, bad_evidence)[0].reason == "MALFORMED_SOURCE_SIGNATURES"
+
+
+def test_p0_t06_missing_closure_fingerprint():
+    _, index, snapshot, evidence = _one()
+    del index["b"]
+    result = assess(PAIR, index, snapshot, evidence)
+    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
+    assert result[0].reason == "SOURCE_INDEX_FINGERPRINT_MISMATCH:b"
+
+
+def test_p0_t07_graph_fingerprint_mismatch():
+    _, index, snapshot, evidence = _one()
+    bad = replace(snapshot, graph_sha256="0" * 64)
+    assert assess(PAIR, index, bad, evidence)[0].reason == "SNAPSHOT_GRAPH_FINGERPRINT_MISMATCH"
+    bad_evidence = replace(evidence, graph_fingerprint="0" * 64)
+    assert assess(PAIR, index, snapshot, bad_evidence)[0].reason == "SOURCE_GRAPH_FINGERPRINT_MISMATCH"
+
+
+def test_p0_t08_scc_membership_and_internal_edge_identity():
+    _, index, snapshot, evidence = _one()
+    component = evidence.scenarios.components[0]
+    altered = replace(component, internal_edges=())
+    bad_report = replace(evidence.scenarios, components=(altered,))
+    result = assess(PAIR, index, snapshot, replace(evidence, scenarios=bad_report))
+    assert result[0].reason == "SCENARIO_INTERNAL_EDGES_MISMATCH"
+    duplicate = replace(evidence, components=(evidence.components[0], evidence.components[0]))
+    assert assess(PAIR, index, snapshot, duplicate)[0].reason == "SCC_COMPONENT_IDENTITY_MISMATCH"
+    tampered_token = replace(evidence.components[0], evidence_token="0" * 64)
+    assert assess(PAIR, index, snapshot, replace(evidence, components=(tampered_token,)))[0].reason == "COMPONENT_EVIDENCE_TOKEN_MISMATCH"
+
+
+def test_p0_t09_partial_source_cohort():
+    _, index, snapshot, evidence = _one()
+    partial = replace(snapshot,
+        observed_source_fingerprints=(snapshot.observed_source_fingerprints[0],),
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+    )
+    result = assess(PAIR, index, partial, evidence)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+
+
+def test_p0_t10_source_issue_cannot_pass():
+    _, index, snapshot, evidence = _one()
+    issue = replace(snapshot, source_issues=(("a", "SOURCE_CHANGED_DURING_READ"),),
+                    coverage_status="PARTIAL_SOURCE_EVIDENCE")
+    result = assess(PAIR, index, issue, evidence)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+
+
+def test_p0_t11_unknown_entry_in_scc():
+    _, index, snapshot, evidence = _one()
+    component = evidence.scenarios.components[0]
+    entries = (replace(component.entry_assessments[0], outcome="UNKNOWN"),
+               component.entry_assessments[1])
+    changed = replace(component, entry_assessments=entries)
+    report = replace(evidence.scenarios, components=(changed,))
+    source = replace(evidence, scenarios=report)
+    result = assess(PAIR, index, snapshot, source)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"
+
+
+def test_p0_t12_independent_sccs_do_not_share_pass():
+    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
+    sources = dict(PASS, x="import y\nvalue=1", y="from x import value")
+    result, _, _, _ = _one(edges, sources)
+    assert [(r.members, r.model_classification) for r in result] == [
+        (("a", "b"), "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"),
+        (("x", "y"), "MODEL_INTERNAL_EARLY_BINDING_HAZARD"),
+    ]
+
+
+def test_p0_t13_self_loop():
+    result, _, _, _ = _one({"a": {"a"}}, {"a": "import a\nx=1"})
+    assert result[0].members == ("a",)
+    assert result[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+
+
+def test_p0_t14_no_cyclic_scc():
+    result, _, _, _ = _one({"a": {"b"}, "b": set()}, {"a": "import b", "b": "pass"})
+    assert result == ()
+
+
+def test_p0_t15_deterministic_without_input_mutation():
+    edges = {"a": {"b"}, "b": {"a"}}
+    _, index, snapshot, evidence = _one(edges)
+    before = (repr(edges), repr(index), repr(snapshot), repr(evidence))
+    first = assess(edges, index, snapshot, evidence)
+    assert first == assess(edges, index, snapshot, evidence)
+    assert before == (repr(edges), repr(index), repr(snapshot), repr(evidence))
+    json.dumps(asdict(first[0]))
+
+
+def test_p0_t16_no_warning_suppression_or_public_api_change():
+    result, _, _, _ = _one()
+    assert result[0].authority == "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"
+    assert set(asdict(result[0])) == {
+        "members", "model_classification", "evidence_state", "reason", "authority",
+    }
+    assert not any("SAFE" in value or "warning" in value.lower()
+                   for value in asdict(result[0]).values() if isinstance(value, str))
```

## FINAL_VERDICT
PARTIAL. Approved code and all targeted gates pass. The required LIVE watcher/workspace_sync confirmation and serving-process loaded-module proof are unavailable: revision stayed 624, no watcher event arrived, and the edited module is out_of_sync in Contextor. The result remains declared-input model evidence, never runtime SAFE certification.
