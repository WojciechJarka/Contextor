# TASK
CONTEXTOR_B0G4C38D1_CANONICAL_CYCLE_SEMANTICS_STATE_CARRIER

HEAD_BEFORE=5a710d1db3dab0fd872614d1061a55fef96d1789
HEAD_AFTER=5a710d1db3dab0fd872614d1061a55fef96d1789
GIT_STATUS=modified contextor/core/analysis/state_manager.py; untracked tests/test_cycle_semantics_canonical_state.py; walkthrough.md is the report.
PRECHECK=DIRECT_EVIDENCE: Contextor implementation/module context at revision 489 was verified. RepositoryAnalysisState had 36 prior fields; package_root was last. clone_for_update copies mutable top-level containers. Contracts snapshot is frozen. Engine, plan executor, and store paths were inspected; no modifications.
CONTEXTOR_DISCOVERY_COVERAGE=RepositoryAnalysisState, CycleSemanticsSnapshot, _prepare_candidate_state, IncrementalAnalysisEngine._apply_delta_and_commit, save_snapshot, load_snapshot; module contexts for state_manager, contracts, plan_executor, engine, store. State manager has 95 inbound dependencies before edit; after edit Contextor reports 96 consumers and 3 imports.
FILES_CHANGED=contextor/core/analysis/state_manager.py; tests/test_cycle_semantics_canonical_state.py
CANONICAL_FIELD_CONTRACT=PASS: exact three fields appended after RepositoryAnalysisState.package_root. No new fields in AnalysisResult. No production code assigns fresh.
POSITIONAL_CONSTRUCTOR_COMPATIBILITY=PASS: test asserts exact prior field order and all prior positional values.
FRESHNESS_INDEPENDENCE=PASS: structural cycles_state=fresh retains semantic state deferred and absent evidence.
IMMUTABLE_EVIDENCE_IDENTITY=PASS: valid frozen two-module snapshot is retained by identity in state and clone.
COW_ISOLATION=PASS: candidate marker/reason changes do not alter original. clone_for_update unchanged.
PICKLE_ROUNDTRIP=PASS: evidence and report types, marker, reason, structural cycles preserved.
LEGACY_SHAPE_COMPATIBILITY=PASS at state level: missing instance attributes resolve to class defaults after pickle and clone. Store migration was not certified.
TARGETED_TEST_RESULTS=First run failed 8 new tests because patch had been placed after AnalysisResult.package_root. Corrected placement; second run 86 passed in 8.36s across four requested test files. git diff --check passed. No FULL analysis.
LIVE_AUTHORITY_BEFORE_AFTER=Before: Contextor LIVE revision 489, repo ctx_8efc50d8. After: read-only endpoint client authority_status at revision 490: repo ctx_8efc50d8; root C:\Temp\Contextor_Repo; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 6f13273feccb46cb9c23fbbfee03afe1; lease_generation 31; service_pid 11632; process_start_identity 134367226998365614; endpoint_fingerprint 1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd. Pre-edit full identity was not independently captured; identity continuity beyond repo/epoch is UNKNOWN.
LIVE_REVISION_BEFORE_AFTER=489 -> 491.
ACTIVITY_EPOCH_BEFORE_AFTER=bbd40ce1942841df94718acedc12561f -> same.
EVENT_CONTINUITY=continuous; resync_required=false; desktop_watcher UPDATED state_manager.py at revision 490 and new test file at 491.
WORKSPACE_SYNC=verified for both target files at revision 491; graph/topology/cycles/collisions fresh; syntax_errors=0.
RUNTIME_CODE_ADOPTION_STATUS=UNKNOWN: watcher source indexing does not establish that the running LIVE process reloaded RepositoryAnalysisState. Separate manual runtime checkpoint is required before production activation.
COLLISIONS_BEFORE_AFTER=0 -> 0, fresh.
STRUCTURAL_CYCLES_BEFORE_AFTER=16 -> 16, fresh.
NEW_IMPORT_CYCLES=none observed in fresh canonical diagnostics; direct new state_manager -> contracts import confirmed.
MCP_SERVER_RESTART_REQUIRED=NO_FOR_THIS_STAGE
DESKTOP_LIVE_RESTART_REQUIRED=YES_BEFORE_PRODUCTION_ACTIVATION
FINAL_VERDICT=B0G4C38D1_PASS for approved state-carrier scope. Runtime adoption remains unverified as explicitly scoped.
FULL_DIFFS
`diff
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index ab19d9f..6f5e643 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -5,6 +5,9 @@ from dataclasses import dataclass, field, fields
 from typing import Dict, Any, Optional
 from pathlib import Path
 
+from contextor.core.cycle_semantics.contracts import (
+    CycleSemanticsSnapshot,
+)
 from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
 
 
@@ -127,6 +130,9 @@ class RepositoryAnalysisState:
 
     trie: Optional[Any] = None
     package_root: str = ""
+    cycle_semantics: CycleSemanticsSnapshot | None = None
+    cycle_semantics_state: str = "deferred"
+    cycle_semantics_invalidation_reason: str | None = None
 
     def clone_for_update(self) -> "RepositoryAnalysisState":
         """
diff --git a/tests/test_cycle_semantics_canonical_state.py b/tests/test_cycle_semantics_canonical_state.py
new file mode 100644
index 0000000..beb0efb
--- /dev/null
+++ b/tests/test_cycle_semantics_canonical_state.py
@@ -0,0 +1,191 @@
+"""State-carrier contracts for immutable cycle semantics evidence."""
+
+from __future__ import annotations
+
+import hashlib
+import pickle
+from dataclasses import fields
+
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
+from contextor.core.cycle_semantics.contracts import (
+    UNVERIFIED_RUNTIME_EXECUTION,
+    UNVERIFIED_SOURCE_BINDING,
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.edge_sites import (
+    CyclicImportSiteReport,
+    HardEdgeSiteEvidence,
+    SCCImportSiteEvidence,
+)
+from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology
+
+
+@pytest.fixture
+def semantic_snapshot() -> CycleSemanticsSnapshot:
+    members = ("pkg.a", "pkg.b")
+    edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
+    topology = ImportCycleTopology(
+        node_count=2,
+        hard_edge_count=2,
+        total_scc_count=1,
+        cyclic_components=(CyclicImportComponent(
+            members=members, internal_edges=edges, kind="MULTI_NODE_SCC"
+        ),),
+    )
+    sites = CyclicImportSiteReport(
+        topology=topology,
+        components=(SCCImportSiteEvidence(
+            members=members,
+            internal_edges=tuple(
+                HardEdgeSiteEvidence(source, target, "UNRESOLVED", ())
+                for source, target in edges
+            ),
+            matched_edge_count=0,
+            unresolved_edge_count=2,
+        ),),
+    )
+    discovery = ConditionalDiscoveryReport(
+        candidates=(),
+        examined_outgoing_count=0,
+        unavailable_source_modules=(),
+        unresolved_lexical_edge_count=2,
+        coverage_status="NO_CONDITIONAL_CANDIDATES",
+    )
+    return CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}),
+        cyclic_modules=members,
+        observed_source_fingerprints=tuple(
+            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
+        ),
+        source_issues=(),
+        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
+        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
+        import_sites=sites,
+        conditional_discovery=discovery,
+    )
+
+
+def test_new_canonical_family_defaults() -> None:
+    first = RepositoryAnalysisState()
+    second = RepositoryAnalysisState()
+    assert first.cycle_semantics is None
+    assert first.cycle_semantics_state == "deferred"
+    assert first.cycle_semantics_invalidation_reason is None
+    assert first.cycles == [] and first.cycles_state == "deferred"
+    assert first.cycles is not second.cycles
+
+
+def test_structural_fresh_does_not_imply_semantic_fresh() -> None:
+    state = RepositoryAnalysisState(cycles_state="fresh")
+    assert state.cycles_state == "fresh"
+    assert state.cycle_semantics is None
+    assert state.cycle_semantics_state == "deferred"
+
+
+def test_canonical_state_accepts_immutable_evidence(
+    semantic_snapshot: CycleSemanticsSnapshot,
+) -> None:
+    cycles = [["pkg.a", "pkg.b", "pkg.a"]]
+    state = RepositoryAnalysisState(
+        cycles=cycles, cycle_semantics=semantic_snapshot, cycle_semantics_state="deferred"
+    )
+    assert state.cycle_semantics is semantic_snapshot
+    assert state.cycle_semantics_state == "deferred"
+    assert state.cycles is cycles
+
+
+def test_clone_preserves_immutable_evidence_identity(
+    semantic_snapshot: CycleSemanticsSnapshot,
+) -> None:
+    state = RepositoryAnalysisState(cycle_semantics=semantic_snapshot)
+    candidate = state.clone_for_update()
+    assert candidate is not state
+    assert candidate.cycle_semantics is state.cycle_semantics
+    candidate.cycle_semantics_state = "stale"
+    candidate.cycle_semantics_invalidation_reason = "source changed"
+    assert state.cycle_semantics_state == "deferred"
+    assert state.cycle_semantics_invalidation_reason is None
+
+
+def test_state_pickle_roundtrip_preserves_family(
+    semantic_snapshot: CycleSemanticsSnapshot,
+) -> None:
+    cycles = [["pkg.a", "pkg.b", "pkg.a"]]
+    state = RepositoryAnalysisState(
+        cycles=cycles,
+        cycle_semantics=semantic_snapshot,
+        cycle_semantics_state="stale",
+        cycle_semantics_invalidation_reason="source changed",
+    )
+    restored = pickle.loads(pickle.dumps(state))
+    assert restored.cycle_semantics == semantic_snapshot
+    assert isinstance(restored.cycle_semantics, CycleSemanticsSnapshot)
+    assert isinstance(restored.cycle_semantics.import_sites, CyclicImportSiteReport)
+    assert isinstance(restored.cycle_semantics.conditional_discovery, ConditionalDiscoveryReport)
+    assert restored.cycle_semantics_state == "stale"
+    assert restored.cycle_semantics_invalidation_reason == "source changed"
+    assert restored.cycles == cycles
+
+
+def test_legacy_missing_family_is_not_fresh() -> None:
+    state = RepositoryAnalysisState(cycles_state="fresh")
+    for name in (
+        "cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"
+    ):
+        del state.__dict__[name]
+    restored = pickle.loads(pickle.dumps(state))
+    assert restored.cycle_semantics is None
+    assert restored.cycle_semantics_state == "deferred"
+    assert restored.cycle_semantics_invalidation_reason is None
+    assert restored.cycle_semantics_state != "fresh"
+    assert not isinstance(restored.cycle_semantics, CycleSemanticsSnapshot)
+    candidate = restored.clone_for_update()
+    assert candidate.cycle_semantics is None
+    assert candidate.cycle_semantics_state == "deferred"
+
+
+def test_existing_constructor_compatibility() -> None:
+    previous_fields = (
+        "modules", "artifacts", "reexport_facts_by_module", "dependency_graph",
+        "artifact_consumption", "artifact_consumption_state", "layer_information",
+        "metrics", "file_state", "module_parse_freshness", "syntax_diagnostics_by_path",
+        "syntax_diagnostics_state", "module_usages", "module_usages_manifest",
+        "lineage_facts_by_source", "lineage_facts_state",
+        "lineage_facts_semantic_version", "lineage_owner_source_index",
+        "lineage_source_owner_index", "lineage_query_index_state",
+        "lineage_semantic_anchor_bindings_complete", "topology_analytics",
+        "topology_metrics_state", "cached_analytics", "cached_analytics_state",
+        "cycles", "cycles_state", "collision_facts", "collisions", "collisions_state",
+        "dependency_matrix", "dependency_matrix_state", "shared_usage_clusters",
+        "shared_usage_clusters_state", "trie", "package_root",
+    )
+    assert tuple(field.name for field in fields(RepositoryAnalysisState)) == (
+        *previous_fields, "cycle_semantics", "cycle_semantics_state",
+        "cycle_semantics_invalidation_reason",
+    )
+    seed = RepositoryAnalysisState()
+    values = tuple(getattr(seed, name) for name in previous_fields)
+    state = RepositoryAnalysisState(*values)
+    assert all(getattr(state, name) is value for name, value in zip(previous_fields, values))
+    assert (state.cycle_semantics, state.cycle_semantics_state,
+            state.cycle_semantics_invalidation_reason) == (None, "deferred", None)
+
+
+def test_invalidating_candidate_does_not_mutate_original(
+    semantic_snapshot: CycleSemanticsSnapshot,
+) -> None:
+    state = RepositoryAnalysisState(cycle_semantics=semantic_snapshot)
+    candidate = state.clone_for_update()
+    candidate.cycle_semantics_state = "stale"
+    candidate.cycle_semantics_invalidation_reason = "graph changed"
+    assert state.cycle_semantics is semantic_snapshot
+    assert state.cycle_semantics_state == "deferred"
+    assert state.cycle_semantics_invalidation_reason is None
+    assert candidate.cycle_semantics is semantic_snapshot
+    assert candidate.cycle_semantics_state == "stale"
+    assert candidate.cycle_semantics_invalidation_reason == "graph changed"
```
