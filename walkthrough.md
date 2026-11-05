# CONTEXTOR C16-B03-P1D2B

## PREFLIGHT

Local HEAD ee642788f095c2a824a2670a4247058b8c860a9f, matching the supplied base. Initial worktree clean. Contextor MCP preflight revision 1008: source_proof and evidence workspace_sync=verified; structural DFS path count 16; cycle_semantics=stale. Exact source anchors matched. New test path did not exist.

## EXACT_IMPLEMENTATION

Applied the supplied import changes and appended the supplied assess_optional_scc_source_bytes implementation to contextor/core/cycle_semantics/source_proof.py. Existing assess_scc_source_bytes was not modified. Added tests/test_cycle_semantics_optional_child_byte_replay.py with the supplied content. Edits used direct apply_patch, not a shell patch script. No other source/test files were edited.

## TARGETED_TESTS

Command: .venv CPython 3.15.2 with -B -m pytest -q -rs -p no:cacheprovider, external --basetemp C:\Temp\Contextor_C16_P1D2B_pytest_tmp, and exactly the four requested modules. Result: 103 passed, 1 failed. No full suite.

Failure: tests/test_cycle_semantics_optional_child_byte_replay.py::test_snapshot_lexical_evidence_must_match_bytes. The supplied test calls dataclasses.replace on CycleSemanticsSnapshot with import_sites=analyze_cyclic_import_sites({}, {}). CycleSemanticsSnapshot.__post_init__ rejects that object before assess_optional_scc_source_bytes is called: ValueError("Import-site topology and cyclic cohort differ"), from contextor/core/cycle_semantics/contracts.py:394. Expected test assertion OPTIONAL_GRAPH_OR_TOPOLOGY_MISMATCH was never reached. This is DIRECT_EVIDENCE of a test fixture/constructor contract conflict, not a demonstrated failure of the new replay function. Per user instruction, no independent correction was made.

## MCP_AUDIT

At revision 1011, source_proof and new test module report canonical_state=fresh, workspace_sync=verified, advisory_warning=null. Initial source_proof query at revision 1010 was unverified due generation proof in flight; final query at revision 1011 was verified. Structural DFS path count remains 16. cycle_semantics remains stale. Indexed-source freshness does not prove loaded backend code adoption. No FULL, update_file, restart, install or commit.

## FILES_CHANGED

- contextor/core/cycle_semantics/source_proof.py
- tests/test_cycle_semantics_optional_child_byte_replay.py

walkthrough.md is the report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/source_proof.py b/contextor/core/cycle_semantics/source_proof.py
index 36e7d1e..61eb75c 100644
--- a/contextor/core/cycle_semantics/source_proof.py
+++ b/contextor/core/cycle_semantics/source_proof.py
@@ -19,13 +19,24 @@ from contextor.core.source import (
     parse_source_snapshot,
 )
 
-from .contracts import CycleSemanticsSnapshot
+from .contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
 from .evidence import (
     SourceBoundCycleEvidence,
+    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
     assess_index_bound_scc_models,
     build_source_bound_cycle_evidence,
+    _digest,
     _scenario_fingerprint,
 )
+from .edge_sites import analyze_cyclic_import_sites
+from .model_source_closure import (
+    CycleModelSourceClosure,
+    compute_cycle_model_source_closures_with_optional_children,
+)
+from .scc import analyze_import_cycle_topology
 
 
 _BYTE_AUTHORITY = (
@@ -252,3 +263,272 @@ def assess_scc_source_bytes(
             ))
 
     return tuple(assessments)
+
+
+def assess_optional_scc_source_bytes(
+    hard_edges: Mapping[str, object],
+    indexed_fingerprints_by_module: Mapping[str, str],
+    snapshot: CycleSemanticsSnapshot,
+    source_evidence: SourceBoundCycleEvidence,
+    source_snapshots: Mapping[str, SourceSnapshot],
+    indexed_imports_by_module: Mapping[str, object],
+    *,
+    package_root: str | None = None,
+    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
+    max_source_bytes: int = 2 * 1024 * 1024,
+    max_closure_bytes: int = 32 * 1024 * 1024,
+) -> tuple[SCCSourceByteAssessment, ...]:
+    """Recheck optional evidence from caller-supplied bytes, never LIVE."""
+
+    if not isinstance(hard_edges, Mapping):
+        raise TypeError("hard_edges must be a mapping")
+    if not isinstance(indexed_fingerprints_by_module, Mapping):
+        raise TypeError("fingerprints must be a mapping")
+    if not isinstance(snapshot, CycleSemanticsSnapshot):
+        raise TypeError("snapshot must be CycleSemanticsSnapshot")
+    if not isinstance(source_evidence, SourceBoundCycleEvidence):
+        raise TypeError("invalid source evidence")
+    if not isinstance(source_snapshots, Mapping):
+        raise TypeError("source_snapshots must be a mapping")
+
+    if (
+        type(max_source_bytes) is not int
+        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
+        or type(max_closure_bytes) is not int
+        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
+    ):
+        raise ValueError("invalid source byte budget")
+
+    topology = analyze_import_cycle_topology(hard_edges)
+    structural = topology.cyclic_components
+
+    if not structural:
+        return ()
+
+    def reject(
+        reason: str,
+        state: str = "UNAVAILABLE",
+    ) -> tuple[SCCSourceByteAssessment, ...]:
+        return tuple(
+            SCCSourceByteAssessment(
+                members=component.members,
+                model_classification="INDETERMINATE",
+                bytes_state=state,
+                reason=reason,
+            )
+            for component in structural
+        )
+
+    if (
+        source_evidence.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or source_evidence.semantic_version
+        != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+        or source_evidence.authority
+        != "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
+        or source_evidence.scenarios.evidence_scope
+        != "OPTIONAL_NAMED_CHILDREN_SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
+    ):
+        return reject("OPTIONAL_EVIDENCE_IDENTITY_MISMATCH")
+
+    adjacency = {
+        name: tuple(sorted(set(targets)))
+        for name, targets in hard_edges.items()
+    }
+    for targets in tuple(adjacency.values()):
+        for target in targets:
+            adjacency.setdefault(target, ())
+
+    graph_hash = _digest(tuple(
+        (name, adjacency[name])
+        for name in sorted(adjacency)
+    ))
+
+    if (
+        snapshot.graph_sha256 != fingerprint_hard_edges(hard_edges)
+        or source_evidence.graph_fingerprint != graph_hash
+        or snapshot.import_sites.topology != topology
+        or source_evidence.scenarios.topology != topology
+    ):
+        return reject("OPTIONAL_GRAPH_OR_TOPOLOGY_MISMATCH")
+
+    if (
+        snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
+        or snapshot.source_issues
+    ):
+        return reject("OPTIONAL_CYCLIC_SNAPSHOT_INCOMPLETE")
+
+    cyclic_members = tuple(sorted({
+        member
+        for component in structural
+        for member in component.members
+    }))
+    observed = snapshot.observed_source_fingerprints
+
+    if (
+        snapshot.cyclic_modules != cyclic_members
+        or tuple(sorted(name for name, _ in observed)) != cyclic_members
+        or any(
+            fingerprint != indexed_fingerprints_by_module.get(name)
+            for name, fingerprint in observed
+        )
+    ):
+        return reject("OPTIONAL_CYCLIC_SOURCE_IDENTITY_MISMATCH")
+
+    try:
+        expected = (
+            compute_cycle_model_source_closures_with_optional_children(
+                hard_edges,
+                indexed_imports_by_module,
+                package_root=package_root,
+            )
+        )
+    except (AttributeError, TypeError, ValueError):
+        return reject("OPTIONAL_COHORT_UNAVAILABLE")
+
+    if (
+        type(source_closures) is not tuple
+        or source_closures != expected
+        or len(expected) != len(structural)
+        or tuple(row.members for row in expected)
+        != tuple(row.members for row in structural)
+    ):
+        return reject("OPTIONAL_COHORT_IDENTITY_MISMATCH")
+
+    selected = tuple(sorted({
+        name
+        for row in expected
+        for name in row.evidence_source_modules
+    }))
+
+    if (
+        set(indexed_fingerprints_by_module) != set(hard_edges)
+        or set(source_snapshots) != set(selected)
+    ):
+        return reject("OPTIONAL_CAPTURE_SET_MISMATCH")
+
+    parsed: dict[str, ParsedSourceInput] = {}
+    total_bytes = 0
+
+    for module in selected:
+        supplied = source_snapshots[module]
+
+        if (
+            type(supplied) is not SourceSnapshot
+            or type(supplied.raw) is not bytes
+            or type(supplied.source_fingerprint) is not str
+        ):
+            return reject("SOURCE_BYTES_UNAVAILABLE:" + module)
+
+        size = len(supplied.raw)
+        total_bytes += size
+
+        if (
+            size > max_source_bytes
+            or total_bytes > max_closure_bytes
+        ):
+            return reject(
+                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module
+            )
+
+        actual_hash = hashlib.sha256(supplied.raw).hexdigest()
+
+        if actual_hash != supplied.source_fingerprint:
+            return reject(
+                "SOURCE_SNAPSHOT_HASH_MISMATCH:" + module,
+                "EVIDENCE_MISMATCH",
+            )
+
+        if actual_hash != indexed_fingerprints_by_module[module]:
+            return reject(
+                "SOURCE_INDEX_BYTES_MISMATCH:" + module,
+                "EVIDENCE_MISMATCH",
+            )
+
+        try:
+            parsed[module] = parse_source_snapshot(
+                supplied, module
+            )
+        except SourceError:
+            return reject("SOURCE_BYTES_UNPARSABLE:" + module)
+
+    try:
+        replay_sites = analyze_cyclic_import_sites(
+            hard_edges, parsed
+        )
+    except (TypeError, ValueError, RecursionError, OverflowError):
+        return reject("OPTIONAL_LEXICAL_REPLAY_UNAVAILABLE")
+
+    if replay_sites != snapshot.import_sites:
+        return reject(
+            "OPTIONAL_LEXICAL_EVIDENCE_MISMATCH",
+            "EVIDENCE_MISMATCH",
+        )
+
+    if any(
+        site.matched_edge_count != len(site.internal_edges)
+        or site.unresolved_edge_count != 0
+        or any(
+            edge.status != "LEXICAL_CANDIDATES"
+            or not edge.sites
+            for edge in site.internal_edges
+        )
+        for site in replay_sites.components
+    ):
+        return reject("OPTIONAL_CYCLIC_IMPORT_SITES_INCOMPLETE")
+
+    try:
+        replay = build_source_bound_cycle_evidence(
+            hard_edges,
+            parsed,
+            source_selection="OPTIONAL_NAMED_CHILDREN",
+            indexed_imports_by_module=indexed_imports_by_module,
+            package_root=package_root,
+            source_closures=expected,
+        )
+    except (
+        AttributeError,
+        TypeError,
+        ValueError,
+        KeyError,
+        IndexError,
+        RecursionError,
+        OverflowError,
+    ):
+        return reject("OPTIONAL_MODEL_REPLAY_UNAVAILABLE")
+
+    if (
+        replay.scenarios != source_evidence.scenarios
+        or len(replay.components) != len(source_evidence.components)
+        or replay.components != source_evidence.components
+    ):
+        return reject(
+            "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH",
+            "EVIDENCE_MISMATCH",
+        )
+
+    results: list[SCCSourceByteAssessment] = []
+
+    for component in replay.components:
+        if (
+            component.coverage != "COMPLETE_FRESH_MEMBER_ENTRIES"
+            or component.classification not in {
+                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+            }
+        ):
+            results.append(SCCSourceByteAssessment(
+                members=component.members,
+                model_classification="INDETERMINATE",
+                bytes_state="UNAVAILABLE",
+                reason=component.reason or "OPTIONAL_MODEL_INCOMPLETE",
+            ))
+            continue
+
+        results.append(SCCSourceByteAssessment(
+            members=component.members,
+            model_classification=component.classification,
+            bytes_state="BYTE_AST_CONSISTENT_NON_ATOMIC",
+            reason=None,
+        ))
+
+    return tuple(results)
diff --git a/tests/test_cycle_semantics_optional_child_byte_replay.py b/tests/test_cycle_semantics_optional_child_byte_replay.py
new file mode 100644
index 0000000..801aeca
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_byte_replay.py
@@ -0,0 +1,224 @@
+"""P1D2B: optional byte and model replay without LIVE authority."""
+
+import hashlib
+from dataclasses import replace
+from pathlib import Path
+
+from contextor.core.source import SourceSnapshot
+from contextor.core.cycle_semantics.contracts import (
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.edge_sites import (
+    analyze_cyclic_import_sites,
+)
+from contextor.core.cycle_semantics.conditional_discovery import (
+    ConditionalDiscoveryReport,
+)
+from contextor.core.cycle_semantics.source_proof import (
+    assess_optional_scc_source_bytes,
+    assess_scc_source_bytes,
+)
+from tests.test_cycle_semantics_optional_child_scenarios import _case
+from tests.test_cycle_semantics_optional_child_evidence import (
+    _inputs,
+    _build,
+)
+
+
+def _fixture(tmp_path):
+    case = _case(tmp_path)
+    parsed, _ = _inputs(tmp_path, case)
+    graph, _, imports, root, closures = case
+    evidence = _build(case, parsed)
+
+    index = {
+        name: source.source_fingerprint
+        for name, source in parsed.items()
+    }
+    members = tuple(sorted({
+        name
+        for row in closures
+        for name in row.members
+    }))
+
+    snapshot = CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges(graph.hard_edges),
+        cyclic_modules=members,
+        observed_source_fingerprints=tuple(
+            (name, index[name]) for name in members
+        ),
+        source_issues=(),
+        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding="NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY",
+        runtime_execution_status="UNKNOWN_NOT_EVALUATED",
+        import_sites=analyze_cyclic_import_sites(
+            graph.hard_edges, parsed
+        ),
+        conditional_discovery=ConditionalDiscoveryReport(
+            (), 0, (), 0, "COMPLETE",
+        ),
+    )
+
+    selected = {
+        name
+        for row in closures
+        for name in row.evidence_source_modules
+    }
+
+    source_snapshots = {}
+    for name in selected:
+        path = (
+            tmp_path / "repo"
+            / Path(*name.split(".")).with_suffix(".py")
+        )
+        raw = path.read_bytes()
+        source_snapshots[name] = SourceSnapshot(
+            raw, hashlib.sha256(raw).hexdigest()
+        )
+
+    return (
+        graph.hard_edges,
+        index,
+        snapshot,
+        evidence,
+        source_snapshots,
+        imports,
+        root,
+        closures,
+    )
+
+
+def _verify(case):
+    hard, index, snap, evidence, sources, imports, root, closures = case
+    return assess_optional_scc_source_bytes(
+        hard,
+        index,
+        snap,
+        evidence,
+        sources,
+        imports,
+        package_root=root,
+        source_closures=closures,
+    )
+
+
+def test_optional_bytes_and_model_replay(tmp_path):
+    case = _fixture(tmp_path)
+    result = _verify(case)
+
+    assert len(result) == 1
+    assert result[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    assert result[0].model_classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+    assert result[0].authority == (
+        "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
+    )
+    assert result == _verify(case)
+
+
+def test_missing_selected_child_is_unavailable(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[4] = dict(case[4])
+    case[4].pop("pkg.child")
+
+    result = _verify(case)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].bytes_state == "UNAVAILABLE"
+    assert result[0].reason == "OPTIONAL_CAPTURE_SET_MISMATCH"
+
+
+def test_changed_raw_bytes_rejected(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[4] = dict(case[4])
+    original = case[4]["pkg.child"]
+    case[4]["pkg.child"] = SourceSnapshot(
+        original.raw + b"# modified\n",
+        original.source_fingerprint,
+    )
+
+    result = _verify(case)
+    assert result[0].reason == (
+        "SOURCE_SNAPSHOT_HASH_MISMATCH:pkg.child"
+    )
+    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
+
+
+def test_changed_index_fingerprint_rejected(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[1] = dict(case[1])
+    case[1]["pkg.child"] = "0" * 64
+
+    result = _verify(case)
+    assert result[0].reason == (
+        "SOURCE_INDEX_BYTES_MISMATCH:pkg.child"
+    )
+
+
+def test_forged_component_token_rejected(tmp_path):
+    case = list(_fixture(tmp_path))
+    evidence = case[3]
+    component = replace(
+        evidence.components[0],
+        evidence_token="0" * 64,
+    )
+    case[3] = replace(
+        evidence, components=(component,)
+    )
+
+    result = _verify(case)
+    assert result[0].reason == (
+        "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH"
+    )
+
+
+def test_legacy_evidence_cannot_enter_optional_replay(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[3] = replace(case[3], source_selection="HARD_ONLY")
+
+    result = _verify(case)
+    assert result[0].reason == (
+        "OPTIONAL_EVIDENCE_IDENTITY_MISMATCH"
+    )
+
+
+def test_snapshot_lexical_evidence_must_match_bytes(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[2] = replace(
+        case[2],
+        import_sites=analyze_cyclic_import_sites(
+            {}, {},
+        ),
+    )
+
+    result = _verify(case)
+    assert result[0].reason == (
+        "OPTIONAL_GRAPH_OR_TOPOLOGY_MISMATCH"
+    )
+
+
+def test_wrong_import_facts_fail_closed(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[5] = dict(case[5])
+    case[5]["pkg.b"] = []
+
+    result = _verify(case)
+    assert result[0].model_classification == "INDETERMINATE"
+    assert result[0].bytes_state != (
+        "BYTE_AST_CONSISTENT_NON_ATOMIC"
+    )
+
+
+def test_existing_byte_verifier_still_rejects_optional(tmp_path):
+    case = _fixture(tmp_path)
+    hard, index, snap, evidence, sources, _, _, _ = case
+
+    result = assess_scc_source_bytes(
+        hard, index, snap, evidence, sources,
+    )
+
+    assert all(
+        row.bytes_state != "BYTE_AST_CONSISTENT_NON_ATOMIC"
+        for row in result
+    )
```

## FINAL_VERDICT

TEST_FAILURE

The exact supplied implementation is present, but the required targeted test set does not pass. No optional byte-replay certification is claimed.
