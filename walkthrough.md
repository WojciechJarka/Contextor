# TASK
CONTEXTOR_B0G4C38D2_CANONICAL_CYCLE_SEMANTICS_INVALIDATION

HEAD_BEFORE=cbabd449e5f967bcb3793b8431326defe22c4782
HEAD_AFTER=cbabd449e5f967bcb3793b8431326defe22c4782
GIT_STATUS=engine.py and plan_executor.py modified; lifecycle.py and test_cycle_semantics_invalidation.py new. No Git mutation.
PRECHECK=DIRECT_EVIDENCE: Contextor LIVE source verified at revision 491; CandidateState, _prepare_candidate_state, IncrementalAnalysisEngine methods, contracts, state carrier, and direct implementation anchors inspected. Git clean before this task. Approved anchors present.
CONTEXTOR_DISCOVERY_COVERAGE=Contextor get_symbol_implementation and get_module_context for state, candidate preparation, engine and contracts; get_live_events and get_file_edit_context for post-edit architectural impact. Existing source consumers include incremental engine, plan executor, state manager, persistent registry, and LIVE watcher call path. No unrelated implementation changed.
FILES_CHANGED=contextor/core/cycle_semantics/lifecycle.py; contextor/core/analysis/incremental/plan_executor.py; contextor/core/analysis/incremental/engine.py; tests/test_cycle_semantics_invalidation.py
CENTRAL_LIFECYCLE_CONTRACT=CONTRACT_PROVED: only four exact reasons accepted; helper performs no I/O or publication and retains evidence.
INVALIDATION_REASON_POLICY=First source invalidation reason retained while stale; CANONICAL_RESYNC_REQUIRED overrides. Invalid reason raises ValueError.
ABSENT_EVIDENCE_POLICY=None/deferred/None for all supported reasons.
PRESERVED_EVIDENCE_IDENTITY=PASS: immutable snapshot identity preserved in candidate and committed state.
CANDIDATE_STATE_FIELDS=Three fields appended after defaulted artifact_consumption_state.
COW_PREPARATION=getattr defaults preserve legacy state; snapshot is passed by identity.
NORMAL_COMMIT_INVALIDATION=Source change/delete/resync reason selected on candidate before registry transaction and canonical publication.
NO_PLAN_INVALIDATION=SOURCE_CHANGED passed through guarded syntax candidate publication even when status is UNCHANGED and file bytes changed.
PARSE_FAILURE_INVALIDATION=SOURCE_PARSE_FAILED passed through guarded syntax candidate commit; old graph and semantic payload retained.
DELETE_INVALIDATION=SOURCE_DELETED applied to candidate; tested with indexed source deletion.
RESYNC_INVALIDATION=At update_file entry, existing resync_required marks current state CANONICAL_RESYNC_REQUIRED even for unchanged return.
ROLLBACK_PROOFS=Normal nonempty-plan and empty-plan acknowledgement-boundary injected failures propagated; state and fresh semantic evidence restored by _failed_commit_guard.
LEGACY_SHAPE_COMPATIBILITY=Missing three state instance attributes default via getattr; candidate remains deferred without evidence.
STRUCTURAL_FRESHNESS_INDEPENDENCE=Structural cycles remain fresh in body-only and empty-plan tests while semantic evidence is stale; no structural detector edits.
TARGETED_TEST_RESULTS=84 passed in 17.78s: exact four requested files and two selected refresh-plan nodes. git diff --check passed. No full suite or FULL analysis.
COLD_IMPORT_RESULT=Fresh interpreter import of lifecycle passed, with no contextor.ui, contextor.repo_generator, or contextor.mcp modules loaded.
LIVE_AUTHORITY_BEFORE_AFTER=Identity stable: repo_id ctx_8efc50d8; root C:\Temp\Contextor_Repo; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 6f13273feccb46cb9c23fbbfee03afe1; lease_generation 31; service_pid 11632; process_start_identity 134367226998365614; endpoint_fingerprint 1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd. One transient ConnectionRefusedError occurred on after-read; immediate read-only retry returned matching identity at revision 495. Cause UNKNOWN.
LIVE_REVISION_BEFORE_AFTER=491 -> 495.
ACTIVITY_EPOCH_BEFORE_AFTER=bbd40ce1942841df94718acedc12561f -> same.
EVENT_CONTINUITY=continuous; resync_required=false. desktop_watcher UPDATED lifecycle.py at 492, plan_executor.py at 493, engine.py at 494, test_cycle_semantics_invalidation.py at 495.
WORKSPACE_SYNC=verified for all four task source/test files at revision 495. Syntax checked_and_none for all.
COLLISIONS_BEFORE_AFTER=0 -> 0, fresh.
STRUCTURAL_CYCLES_BEFORE_AFTER=16 -> 16, fresh.
NEW_IMPORT_CYCLES=0 observed: total structural cycle diagnostics remain 16, fresh.
RUNTIME_CODE_ADOPTION_STATUS=UNKNOWN: source synchronization does not prove running service reloaded state or engine classes.
MCP_SERVER_RESTART_REQUIRED=NO_FOR_THIS_STAGE
DESKTOP_LIVE_RESTART_REQUIRED=YES_BEFORE_PRODUCTION_ACTIVATION
FINAL_VERDICT=B0G4C38D2_PASS for controlled source, focused tests, and canonical source synchronization; runtime code adoption remains an explicit later activation checkpoint.

# FULL_DIFFS
~~~diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 13e137c..2abf579 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -8,6 +8,9 @@ from typing import Optional, List, Set, Dict, Iterable, Tuple, Any
 
 from contextor.core.domain.graph import ProjectGraph
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
+from contextor.core.cycle_semantics.lifecycle import (
+    invalidate_cycle_semantics,
+)
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.runtime_trace import trace_event
@@ -245,6 +248,7 @@ class IncrementalAnalysisEngine:
         degrade_syntax_family: bool = False,
         extracted_lineage_facts: Any | None = None,
         invalidate_lineage: bool = False,
+        invalidate_cycle_semantics_reason: str | None = None,
     ) -> None:
         """Commit syntax, parse-freshness, and lineage changes through one COW candidate."""
         candidate = _prepare_candidate_state(self.state)
@@ -301,6 +305,11 @@ class IncrementalAnalysisEngine:
             )
         elif clear_parse_module is not None:
             clear_module_parse_failure(candidate, clear_parse_module)
+        if invalidate_cycle_semantics_reason is not None:
+            invalidate_cycle_semantics(
+                candidate,
+                invalidate_cycle_semantics_reason,
+            )
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
         self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
         self.state.module_parse_freshness = candidate.module_parse_freshness
@@ -315,6 +324,15 @@ class IncrementalAnalysisEngine:
         self.state.lineage_semantic_anchor_bindings_complete = (
             candidate.lineage_semantic_anchor_bindings_complete
         )
+        self.state.cycle_semantics = (
+            candidate.cycle_semantics
+        )
+        self.state.cycle_semantics_state = (
+            candidate.cycle_semantics_state
+        )
+        self.state.cycle_semantics_invalidation_reason = (
+            candidate.cycle_semantics_invalidation_reason
+        )
 
     def _update_candidate_lineage_slice(
         self,
@@ -571,6 +589,10 @@ class IncrementalAnalysisEngine:
                 # Every exit path, including a semantic no-op, must expose the
                 # already-lost incremental continuity as fail-closed.
                 self.state.artifact_consumption_state = "stale"
+                invalidate_cycle_semantics(
+                    self.state,
+                    "CANONICAL_RESYNC_REQUIRED",
+                )
             path = Path(file_path)
             rel_path = path.relative_to(self.root_path)
             module_path = ".".join(rel_path.with_suffix("").parts)
@@ -696,18 +718,22 @@ class IncrementalAnalysisEngine:
                     if prep.error_status == "SYNTAX_ERROR"
                     else None
                 )
-                self._commit_syntax_candidate(
-                    source_path=source_path,
-                    syntax_fact=syntax_fact,
-                    mark_parse_error=(
-                        prep.error_message,
-                        prep.line_number,
-                        prep.column_number,
-                    ),
-                    clear_parse_module=module_path,
-                    degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
-                    invalidate_lineage=True,
-                )
+                with self._failed_commit_guard():
+                    self._commit_syntax_candidate(
+                        source_path=source_path,
+                        syntax_fact=syntax_fact,
+                        mark_parse_error=(
+                            prep.error_message,
+                            prep.line_number,
+                            prep.column_number,
+                        ),
+                        clear_parse_module=module_path,
+                        degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
+                        invalidate_lineage=True,
+                        invalidate_cycle_semantics_reason=(
+                            "SOURCE_PARSE_FAILED"
+                        ),
+                    )
                 return IncrementalUpdateResult(
                     status=prep.error_status,
                     file_path=file_path,
@@ -750,6 +776,9 @@ class IncrementalAnalysisEngine:
                         syntax_fact=checked_and_none,
                         clear_parse_module=module_path,
                         extracted_lineage_facts=prep.extracted_lineage_facts,
+                        invalidate_cycle_semantics_reason=(
+                            "SOURCE_CHANGED"
+                        ),
                     )
                     self.state_manager.update_state(file_path)
                     self.state.module_usages_manifest = _updated_module_usage_manifest(
@@ -939,6 +968,27 @@ class IncrementalAnalysisEngine:
         )
 
         candidate = outcome.candidate_state
+        if (
+            resync_required
+            or plan.refresh_completeness
+            == "requires_resync"
+        ):
+            semantic_invalidation_reason = (
+                "CANONICAL_RESYNC_REQUIRED"
+            )
+        elif delta.is_deleted:
+            semantic_invalidation_reason = (
+                "SOURCE_DELETED"
+            )
+        else:
+            semantic_invalidation_reason = (
+                "SOURCE_CHANGED"
+            )
+
+        invalidate_cycle_semantics(
+            candidate,
+            semantic_invalidation_reason,
+        )
 
         # Persistent identity sync and lineage materialization share one registry view.
         if outcome.identity_sync_required:
@@ -1093,6 +1143,15 @@ class IncrementalAnalysisEngine:
         self.state.cached_analytics_state = candidate.cached_analytics_state
         self.state.cycles = candidate.cycles
         self.state.cycles_state = candidate.cycles_state
+        self.state.cycle_semantics = (
+            candidate.cycle_semantics
+        )
+        self.state.cycle_semantics_state = (
+            candidate.cycle_semantics_state
+        )
+        self.state.cycle_semantics_invalidation_reason = (
+            candidate.cycle_semantics_invalidation_reason
+        )
         self.state.collision_facts = candidate.collision_facts
         self.state.collisions = candidate.collisions
         self.state.collisions_state = candidate.collisions_state
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 9621914..6ce7638 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -21,6 +21,9 @@ from contextor.core.analysis.state_manager import (
     canonical_artifact_consumption_targets,
     validate_canonical_artifact_consumption_coverage,
 )
+from contextor.core.cycle_semantics.contracts import (
+    CycleSemanticsSnapshot,
+)
 from contextor.core.domain.graph import ProjectGraph
 from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
 from contextor.core.domain.module import Module
@@ -79,6 +82,9 @@ class CandidateState:
     collisions: list
     collisions_state: str
     artifact_consumption_state: str = "deferred"
+    cycle_semantics: CycleSemanticsSnapshot | None = None
+    cycle_semantics_state: str = "deferred"
+    cycle_semantics_invalidation_reason: str | None = None
 
 
 @dataclass(frozen=True)
@@ -766,6 +772,21 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
         collisions=list(getattr(state, "collisions", []) or []),
         collisions_state=getattr(state, "collisions_state", "deferred"),
         artifact_consumption_state=getattr(state, "artifact_consumption_state", "deferred"),
+        cycle_semantics=getattr(
+            state,
+            "cycle_semantics",
+            None,
+        ),
+        cycle_semantics_state=getattr(
+            state,
+            "cycle_semantics_state",
+            "deferred",
+        ),
+        cycle_semantics_invalidation_reason=getattr(
+            state,
+            "cycle_semantics_invalidation_reason",
+            None,
+        ),
     )
 
 

diff --git a/contextor/core/cycle_semantics/lifecycle.py b/contextor/core/cycle_semantics/lifecycle.py
new file mode 100644
index 0000000..0496f01
--- /dev/null
+++ b/contextor/core/cycle_semantics/lifecycle.py
@@ -0,0 +1,79 @@
+"""Canonical freshness lifecycle for cycle-semantic evidence.
+
+This module does not analyze cycles, read source,
+open LIVE IPC, persist snapshots, or publish state.
+
+Invalidation preserves immutable historical
+evidence while marking it unavailable as fresh.
+
+The caller owns COW, transaction and publication
+boundaries.
+"""
+
+from __future__ import annotations
+
+
+CYCLE_SEMANTICS_INVALIDATION_REASONS = frozenset({
+    "SOURCE_CHANGED",
+    "SOURCE_DELETED",
+    "SOURCE_PARSE_FAILED",
+    "CANONICAL_RESYNC_REQUIRED",
+})
+
+
+def invalidate_cycle_semantics(
+    state: object,
+    reason: str,
+) -> None:
+    """Invalidate semantic evidence without destroying it.
+
+    An absent snapshot remains deferred.
+
+    An existing snapshot becomes stale.
+
+    Preserve the first invalidation reason unless
+    a canonical resync overrides it.
+    """
+
+    if reason not in (
+        CYCLE_SEMANTICS_INVALIDATION_REASONS
+    ):
+        raise ValueError(
+            "Unsupported cycle semantics invalidation reason"
+        )
+
+    evidence = getattr(
+        state,
+        "cycle_semantics",
+        None,
+    )
+
+    if evidence is None:
+        state.cycle_semantics_state = "deferred"
+        state.cycle_semantics_invalidation_reason = None
+        return
+
+    previous_state = getattr(
+        state,
+        "cycle_semantics_state",
+        "deferred",
+    )
+
+    previous_reason = getattr(
+        state,
+        "cycle_semantics_invalidation_reason",
+        None,
+    )
+
+    state.cycle_semantics_state = "stale"
+
+    if (
+        reason == "CANONICAL_RESYNC_REQUIRED"
+        or previous_state != "stale"
+        or previous_reason not in (
+            CYCLE_SEMANTICS_INVALIDATION_REASONS
+        )
+    ):
+        state.cycle_semantics_invalidation_reason = (
+            reason
+        )

diff --git a/tests/test_cycle_semantics_invalidation.py b/tests/test_cycle_semantics_invalidation.py
new file mode 100644
index 0000000..5c1ffd1
--- /dev/null
+++ b/tests/test_cycle_semantics_invalidation.py
@@ -0,0 +1,265 @@
+"""Incremental invalidation of canonical cycle semantics evidence."""
+
+from __future__ import annotations
+
+import hashlib
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
+from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
+from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
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
+from contextor.core.cycle_semantics.lifecycle import (
+    CYCLE_SEMANTICS_INVALIDATION_REASONS,
+    invalidate_cycle_semantics,
+)
+from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+
+def _snapshot() -> CycleSemanticsSnapshot:
+    members = ("pkg.a", "pkg.b")
+    edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
+    topology = ImportCycleTopology(
+        node_count=2, hard_edge_count=2, total_scc_count=1,
+        cyclic_components=(CyclicImportComponent(
+            members=members, internal_edges=edges, kind="MULTI_NODE_SCC",
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
+            matched_edge_count=0, unresolved_edge_count=2,
+        ),),
+    )
+    discovery = ConditionalDiscoveryReport(
+        candidates=(), examined_outgoing_count=0,
+        unavailable_source_modules=(), unresolved_lexical_edge_count=2,
+        coverage_status="NO_CONDITIONAL_CANDIDATES",
+    )
+    return CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}),
+        cyclic_modules=members,
+        observed_source_fingerprints=tuple(
+            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
+        ),
+        source_issues=(), coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
+        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
+        import_sites=sites, conditional_discovery=discovery,
+    )
+
+
+@pytest.fixture
+def cyclic_engine(tmp_path: Path) -> tuple[IncrementalAnalysisEngine, Path, Path]:
+    pkg = tmp_path / "pkg"
+    pkg.mkdir()
+    a = pkg / "a.py"
+    b = pkg / "b.py"
+    a.write_text("import pkg.b\ndef fa():\n    return 1\n", encoding="utf-8")
+    b.write_text("import pkg.a\ndef fb():\n    return 2\n", encoding="utf-8")
+    cache = tmp_path / "cache"
+    cache.mkdir()
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache)),
+        str(tmp_path),
+    )
+    assert engine.update_file(str(a)).status in {"UPDATED", "ADDED"}
+    assert engine.update_file(str(b)).status in {"UPDATED", "ADDED"}
+    assert engine.state.cycles_state == "fresh"
+    engine.state.cycle_semantics = _snapshot()
+    engine.state.cycle_semantics_state = "fresh"
+    engine.state.cycle_semantics_invalidation_reason = None
+    return engine, a, b
+
+
+def _assert_stale(engine: IncrementalAnalysisEngine, evidence: CycleSemanticsSnapshot,
+                  reason: str) -> None:
+    assert engine.state.cycle_semantics is evidence
+    assert engine.state.cycle_semantics_state == "stale"
+    assert engine.state.cycle_semantics_invalidation_reason == reason
+
+
+def test_d2_invalidation_preserves_evidence_identity(cyclic_engine) -> None:
+    engine, _, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    candidate = engine.state.clone_for_update()
+    invalidate_cycle_semantics(candidate, "SOURCE_CHANGED")
+    assert candidate.cycle_semantics is evidence
+    assert candidate.cycle_semantics_state == "stale"
+    assert candidate.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
+    assert engine.state.cycle_semantics_state == "fresh"
+
+
+def test_d2_absent_snapshot_remains_deferred() -> None:
+    for reason in CYCLE_SEMANTICS_INVALIDATION_REASONS:
+        state = RepositoryAnalysisState(cycle_semantics_state="fresh")
+        invalidate_cycle_semantics(state, reason)
+        assert (state.cycle_semantics, state.cycle_semantics_state,
+                state.cycle_semantics_invalidation_reason) == (None, "deferred", None)
+
+
+def test_d2_repeated_stale_preserves_first_reason() -> None:
+    state = RepositoryAnalysisState(cycle_semantics=_snapshot(), cycle_semantics_state="fresh")
+    invalidate_cycle_semantics(state, "SOURCE_CHANGED")
+    invalidate_cycle_semantics(state, "SOURCE_DELETED")
+    assert state.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
+    invalidate_cycle_semantics(state, "CANONICAL_RESYNC_REQUIRED")
+    assert state.cycle_semantics_invalidation_reason == "CANONICAL_RESYNC_REQUIRED"
+
+
+def test_d2_true_unchanged_file_preserves_fresh(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    result = engine.update_file(str(a))
+    assert result.status == "UNCHANGED"
+    assert engine.state.cycle_semantics is evidence
+    assert engine.state.cycle_semantics_state == "fresh"
+    assert engine.state.cycle_semantics_invalidation_reason is None
+
+
+def test_d2_body_only_change_stales_semantics(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    cycles = engine.state.cycles
+    a.write_text("import pkg.b\ndef fa():\n    return 10\n", encoding="utf-8")
+    engine.update_file(str(a))
+    assert engine.state.cycles_state == "fresh"
+    assert engine.state.cycles == cycles
+    _assert_stale(engine, evidence, "SOURCE_CHANGED")
+
+
+def test_d2_empty_refresh_plan_stales_semantics(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    old_sha = engine.state_manager.get_tracked_sha256(str(a))
+    a.write_text("import pkg.b\ndef fa():\n    return 1\n# changed\n", encoding="utf-8")
+    result = engine.update_file(str(a))
+    assert result.shadow_plan is not None and result.shadow_plan.is_empty
+    assert result.status == "UNCHANGED"
+    assert engine.state_manager.get_tracked_sha256(str(a)) != old_sha
+    assert engine.state.cycles_state == "fresh"
+    _assert_stale(engine, evidence, "SOURCE_CHANGED")
+
+
+def test_d2_parse_failure_stales_semantics(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    old_graph = engine.state.dependency_graph
+    a.write_text("def broken(:\n", encoding="utf-8")
+    result = engine.update_file(str(a))
+    assert result.status == "SYNTAX_ERROR"
+    assert engine.state.dependency_graph is old_graph
+    _assert_stale(engine, evidence, "SOURCE_PARSE_FAILED")
+
+
+def test_d2_import_change_stales_semantics(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    a.write_text("def fa():\n    return 1\n", encoding="utf-8")
+    result = engine.update_file(str(a))
+    assert result.shadow_plan is not None and not result.shadow_plan.is_empty
+    assert engine.state.cycles_state == "fresh"
+    assert engine.state.cycles == []
+    _assert_stale(engine, evidence, "SOURCE_CHANGED")
+
+
+def test_d2_delete_stales_semantics(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    a.unlink()
+    result = engine.update_file(str(a))
+    assert result.status == "DELETED"
+    _assert_stale(engine, evidence, "SOURCE_DELETED")
+
+
+def test_d2_resync_overrides_reason(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    engine.state.cycle_semantics_state = "stale"
+    engine.state.cycle_semantics_invalidation_reason = "SOURCE_CHANGED"
+    engine.state.resync_required = True
+    result = engine.update_file(str(a))
+    assert result.status == "UNCHANGED"
+    _assert_stale(engine, evidence, "CANONICAL_RESYNC_REQUIRED")
+
+
+def test_d2_normal_commit_rollback_restores_fresh(cyclic_engine, monkeypatch) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    original = engine.state
+    cycles = engine.state.cycles
+    a.write_text("def fa():\n    return 1\n", encoding="utf-8")
+    def fail(*args, **kwargs):
+        raise RuntimeError("ack failure")
+    monkeypatch.setattr(engine.state_manager, "update_state", fail)
+    with pytest.raises(RuntimeError, match="ack failure"):
+        engine.update_file(str(a))
+    assert engine.state is original
+    assert engine.state.cycle_semantics is evidence
+    assert engine.state.cycle_semantics_state == "fresh"
+    assert engine.state.cycle_semantics_invalidation_reason is None
+    assert engine.state.cycles == cycles
+
+
+def test_d2_empty_plan_rollback_restores_fresh(cyclic_engine, monkeypatch) -> None:
+    engine, a, _ = cyclic_engine
+    evidence = engine.state.cycle_semantics
+    a.write_text("import pkg.b\ndef fa():\n    return 1\n# changed\n", encoding="utf-8")
+    def fail(*args, **kwargs):
+        raise RuntimeError("ack failure")
+    monkeypatch.setattr(engine.state_manager, "update_state", fail)
+    with pytest.raises(RuntimeError, match="ack failure"):
+        engine.update_file(str(a))
+    assert engine.state.cycle_semantics is evidence
+    assert engine.state.cycle_semantics_state == "fresh"
+    assert engine.state.cycle_semantics_invalidation_reason is None
+
+
+def test_d2_legacy_state_defaults_fail_closed() -> None:
+    state = RepositoryAnalysisState()
+    for name in (
+        "cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"
+    ):
+        del state.__dict__[name]
+    candidate = _prepare_candidate_state(state)
+    assert candidate.cycle_semantics is None
+    invalidate_cycle_semantics(candidate, "SOURCE_CHANGED")
+    assert candidate.cycle_semantics is None
+    assert candidate.cycle_semantics_state == "deferred"
+    assert candidate.cycle_semantics_invalidation_reason is None
+
+
+def test_d2_cold_lifecycle_import_is_isolated() -> None:
+    code = (
+        "import sys; import contextor.core.cycle_semantics.lifecycle; "
+        "assert not any(name == prefix or name.startswith(prefix + '.') "
+        "for prefix in ('contextor.ui', 'contextor.repo_generator', 'contextor.mcp') "
+        "for name in sys.modules)"
+    )
+    result = subprocess.run(
+        [sys.executable, "-B", "-c", code], capture_output=True, text=True, check=False,
+    )
+    assert result.returncode == 0, result.stderr
~~~

