## TASK

CONTEXTOR_B0G4C38D4C_CANONICAL_LIVE_CYCLE_SEMANTICS_FRESHNESS; strict controlled implementation. STOP after D4C.

## HEAD_BEFORE

0af8a24314d1f00857878bea28a6f297e938e4a9

## HEAD_AFTER

0af8a24314d1f00857878bea28a6f297e938e4a9

## GIT_STATUS

Pre-edit clean. Post-edit before report:
```text
M contextor/mcp/docs/get_project_architecture.json
 M contextor/mcp/query_helpers.py
 M tests/mcp/tools/test_get_project_architecture_full_reports.py
```

## PRECHECK

DIRECT_EVIDENCE: Contextor MCP first. get_symbol_implementation resolved build_state_freshness, _normalize_public_family_marker, get_project_architecture, RepositoryAnalysisState, CycleSemanticsSnapshot, classify_full_cycle_semantics with workspace_sync=verified at revision 516. Actual source confirms generation_coherent calculation, resync handling, semantic state fields, D4B reader and six-section default. Current Contextor get_mcp_documentation for get_project_architecture returned documentation identity mismatch because running MCP has not adopted D4B docs; other tool documentation was read. This is a runtime adoption limitation, not an edited source-anchor mismatch. Baseline LIVE revision 516, epoch 6b4c9554981b4b779b705089dac32739, continuous, resync=false, syntax=0, collisions=0, cycles=16 fresh.

## CONTEXTOR_DISCOVERY_COVERAGE

Contextor get_file_edit_context for query_helpers and existing MCP integration tests established direct consumers, broad static tests_covering and blast radius. Source/Git used afterward for exact anchors. D4B reader source remained untouched. Documentation JSON has no Python module identity for Contextor file edit context; inspected directly. Post-edit helper and test symbols are workspace_sync=verified at revision 518.

## FILES_CHANGED

- contextor/mcp/query_helpers.py
- tests/mcp/tools/test_get_project_architecture_full_reports.py
- contextor/mcp/docs/get_project_architecture.json

walkthrough.md is report only.

## LIVE_SEMANTIC_FAMILY_CONTRACT

Pure _cycle_semantics_family_freshness returns fresh/stale/deferred/unavailable from canonical snapshot identity, lifecycle marker, resync, generation coherence and current in-memory graph hash. Added as families.cycle_semantics after structural cycles; other family entries unchanged.

## GENERATION_COHERENCE_GATE

Existing generation_coherent calculation unchanged. Fresh marker plus evidence is unavailable without positive proof. Synthetic public envelope test proves fresh with matching FileState state_id/revision and unavailable on revision mismatch.

## GRAPH_SHA_IDENTITY_GATE

For otherwise eligible fresh evidence, helper hashes only dependency_graph.hard_edges with existing fingerprint_hard_edges and compares to immutable snapshot.graph_sha256. Match=fresh; drift=stale; missing/malformed mapping=unavailable.

## STRUCTURAL_CYCLE_INDEPENDENCE

families.cycles still uses cycles_state. Semantic stale test leaves cycles_state=fresh. No cycle detector or report reader source changed.

## ABSENT_EVIDENCE_POLICY

No snapshot plus deferred marker returns deferred; no snapshot plus fresh marker returns unavailable. Legacy missing semantic instance attributes return deferred without crash.

## MALFORMED_EVIDENCE_POLICY

Non-CycleSemanticsSnapshot evidence returns unavailable. Existing marker normalizer handles invalid lifecycle markers.

## RESYNC_POLICY

Evidence plus resync_required=True returns stale even with matching graph.

## STALE_EVIDENCE_POLICY

Existing stale marker returns stale without upgrading; deferred marker remains deferred. Graph drift with fresh marker returns stale.

## HISTORICAL_REPORT_INDEPENDENCE

Focused reader test retains original historical report freshness=fresh and unverified publication_binding while current live_state.state_freshness.families.cycle_semantics=stale at mocked LIVE revision 77. This divergence is valid.

## NO_REPORT_MUTATION

D4B get_project_architecture reader file unchanged. Historical report persisted bytes and body are not rewritten; focused test compares returned body to fixture.

## NO_SEMANTIC_RECOMPUTATION

Helper hashes only existing in-memory hard graph; no semantic materializer, source cohort, AST, SCC detection or analyzed Python source read. Focused tests patch materializer/source cohort to fail and still pass. Existing build_state_freshness generation metadata behavior is unchanged.

## TARGETED_TEST_RESULTS

tests/mcp/tools/test_get_project_architecture_full_reports.py, tests/test_cycle_semantics_invalidation.py, tests/test_cycle_semantics_canonical_state.py: 58 passed in 17.26s; 1 third-party AuthlibDeprecationWarning. No full suite or real repository FULL analysis.

## PUBLIC_ENVELOPE_TEST_RESULTS

D4C helper cases A-L pass inside 58-pass run. Exact public MCP documentation/registration nodes: get_project_architecture_signature, get_project_architecture_docs_complete, every_runtime_parameter_and_default_is_documented: 3 passed in 4.14s.

## HELPER_LATENCY_EVIDENCE

One foreground one-shot invocation on synthetic 100-node/200-hard-edge mapping: fresh, elapsed 541689 ns (0.542 ms) from perf_counter_ns. No repeated profiling loop or extrapolation to Contextor repository.

## LIVE_AUTHORITY_BEFORE_AFTER

Read-only LiveStateClient(is_owner=False) authority_status matched endpoint before and after; same nonsecret identity: repo_id ctx_8efc50d8; root C:\Temp\Contextor_Repo; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 88e879fa630c41299f7ba675009e267f; lease_generation 32; service_pid 7840; process_start_identity 134367770052413468; endpoint_fingerprint e73abe0959388d48a8c7608c2d13ed8e150314242e23433d2a0c3b36ab316770. No owner/reconciliation mutation.

## LIVE_REVISION_BEFORE_AFTER

516 -> 518. desktop_watcher UPDATED 517 query_helpers.py and 518 MCP integration test. JSON documentation is not indexed as a Python module.

## ACTIVITY_EPOCH_BEFORE_AFTER

6b4c9554981b4b779b705089dac32739 -> same.

## EVENT_CONTINUITY

continuous, resync_required=false at revision 518.

## WORKSPACE_SYNC

Contextor get_symbol_implementation state_freshness.workspace_sync=verified for query_helpers.py and test source at revision 518. JSON docs validated on disk and by contract tests; Python module workspace_sync is not applicable to JSON.

## COLLISIONS_BEFORE_AFTER

0 -> 0, fresh.

## STRUCTURAL_CYCLES_BEFORE_AFTER

16 -> 16, fresh.

## NEW_IMPORT_CYCLES

0 increase in fresh structural cycle count. Only collections.abc Mapping and function-local existing contracts import added to query_helpers; no new cycle diagnostic observed. Exact membership was not enumerated.

## MCP_SERVER_RESTART_REQUIRED

YES_BEFORE_PRODUCTION_ACTIVATION. No restart performed.

## DESKTOP_LIVE_RESTART_REQUIRED

YES_PENDING_CYCLE_SEMANTICS_ACTIVATION. No restart performed.

## RUNTIME_CODE_ADOPTION_STATUS

UNKNOWN_UNTIL_RELOAD_VERIFIED. Existing MCP documentation identity mismatch makes current serving-process adoption unproven. Source synchronization is not runtime adoption.

## FINAL_VERDICT

B0G4C38D4C_PASS for scoped source, focused tests, freshness gates, LIVE sync and complete diffs. Production activation remains pending explicit MCP/Desktop reload and subsequent runtime verification. Stop and await proceduj.

## FULL_DIFFS

Complete actual current-task diff for all three approved source/test/docs paths. Pre-edit Git status was clean and HEAD unchanged; report diff excluded.

```diff
diff --git a/contextor/mcp/docs/get_project_architecture.json b/contextor/mcp/docs/get_project_architecture.json
index 7fc3bfc..cf8adf6 100644
--- a/contextor/mcp/docs/get_project_architecture.json
+++ b/contextor/mcp/docs/get_project_architecture.json
@@ -1,5 +1,5 @@
 {
-  "version": "1.1.0",
+  "version": "1.2.0",
   "tool": "get_project_architecture",
   "purpose": [
     "[OPTIMIZED] Return the complete persisted global project-analysis report bundle with an explicit current canonical LIVE freshness overlay. The default bundle contains summary, structure, name_collisions, artifacts_compact, graph_analytics, and report_diff. The optional cycle_semantics field exposes a historical FULL evidence report only when explicitly selected. Report bodies are returned losslessly."
@@ -24,7 +24,9 @@
     "live_state.state_freshness reports the current canonical revision, provenance, family states, workspace-sync status, and advisory warning independently from the report snapshot.",
     "A newer LIVE revision does not relabel persisted report-only analytics as fresh LIVE facts.",
     "If one or more modules are parse-stale, live_state.state_freshness.canonical_state is stale and live_state.parse_stale_modules identifies the affected last-known-good module truths; persisted completed-analysis reports remain independently retrievable.",
-    "The explicitly selected cycle_semantics report remains historical even when current LIVE revision is newer or structural diagnostics are fresh. Missing optional files do not affect default six-section completeness."
+    "The explicitly selected cycle_semantics report remains historical even when current LIVE revision is newer or structural diagnostics are fresh. Missing optional files do not affect default six-section completeness.",
+    "live_state.state_freshness.families.cycle_semantics independently describes current canonical semantic evidence as fresh, stale, deferred, or unavailable; structural cycles remain a separate family. Fresh requires positive canonical generation coherence and a SHA-256 match with the current in-memory hard dependency graph.",
+    "The cycle_semantics family does not reread analyzed Python source or rerun semantic AST analysis. Historical FULL report freshness never proves current LIVE freshness."
   ],
   "errors": [
     "unsupported_fields: one or more requested fields are not global project report sections.",
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index e1db1b7..7d706ae 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -1,4 +1,5 @@
 import difflib
+from collections.abc import Mapping
 from pathlib import Path
 from typing import Any
 
@@ -32,6 +33,86 @@ def _normalize_public_family_marker(
     return "unavailable"
 
 
+def _cycle_semantics_family_freshness(
+    state: Any,
+    *,
+    generation_coherent: bool,
+) -> str:
+    """Fail-closed canonical cycle-semantic freshness.
+
+    Evidence identity, lifecycle marker, canonical
+    generation and current graph must agree before
+    publicly claiming fresh.
+
+    No filesystem reads or semantic recomputation.
+    """
+
+    from contextor.core.cycle_semantics.contracts import (
+        CycleSemanticsSnapshot,
+        fingerprint_hard_edges,
+    )
+
+    evidence = getattr(
+        state,
+        "cycle_semantics",
+        None,
+    )
+
+    marker = _normalize_public_family_marker(
+        getattr(
+            state,
+            "cycle_semantics_state",
+            "deferred",
+        ),
+        _PUBLIC_DERIVED_FAMILY_STATES,
+    )
+
+    if evidence is None:
+        return (
+            "deferred"
+            if marker == "deferred"
+            else "unavailable"
+        )
+
+    if type(evidence) is not CycleSemanticsSnapshot:
+        return "unavailable"
+
+    if getattr(state, "resync_required", False):
+        return "stale"
+
+    if marker != "fresh":
+        return marker
+
+    if not generation_coherent:
+        return "unavailable"
+
+    graph = getattr(
+        state,
+        "dependency_graph",
+        None,
+    )
+    hard_edges = getattr(
+        graph,
+        "hard_edges",
+        None,
+    )
+
+    if not isinstance(hard_edges, Mapping):
+        return "unavailable"
+
+    try:
+        current_graph_sha256 = fingerprint_hard_edges(
+            hard_edges
+        )
+    except (TypeError, ValueError):
+        return "unavailable"
+
+    if current_graph_sha256 != evidence.graph_sha256:
+        return "stale"
+
+    return "fresh"
+
+
 def fuzzy_choice_candidates(
     query: str,
     choices: list[str] | tuple[str, ...] | set[str],
@@ -505,6 +586,12 @@ def build_state_freshness(
             getattr(state, "cycles_state", "deferred"),
             _PUBLIC_DERIVED_FAMILY_STATES,
         ),
+        "cycle_semantics": (
+            _cycle_semantics_family_freshness(
+                state,
+                generation_coherent=generation_coherent,
+            )
+        ),
         "collisions": _normalize_public_family_marker(
             getattr(state, "collisions_state", "deferred"),
             _PUBLIC_DERIVED_FAMILY_STATES,
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index fe3022a..df955a6 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -7,7 +7,10 @@ import pytest
 
 from contextor import mcp_server
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
+from contextor.core.cycle_semantics.contracts import fingerprint_hard_edges
+from contextor.core.domain.graph import ProjectGraph
 from contextor.mcp.query_helpers import build_state_freshness
+from contextor.mcp import query_helpers
 from contextor.core.cycle_semantics.report_projection import build_cycle_semantics_report
 from tests.test_cycle_semantics_report_projection import _snapshot
 
@@ -508,3 +511,130 @@ def test_cycle_semantics_selected_missing_does_not_change_default(tmp_path, monk
     assert _read_architecture(tmp_path, fields=["cycle_semantics"])["status"] == "partial"
     after = _read_architecture(tmp_path)
     assert before == after
+
+
+def _semantic_state(*, marker="fresh"):
+    state = RepositoryAnalysisState(
+        cycles_state="fresh",
+        cycle_semantics=_snapshot(),
+        cycle_semantics_state=marker,
+    )
+    state.dependency_graph = ProjectGraph(
+        hard_edges={"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}},
+        soft_edges={},
+    )
+    return state
+
+
+def _install_real_freshness(tmp_path, monkeypatch, state):
+    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
+    engine.state = state
+    state.state_id = "synthetic-generation"
+    state.revision = 77
+    engine.state_manager = SimpleNamespace(state_id="synthetic-generation", revision=77)
+    monkeypatch.setattr(architecture_tool.query_helpers, "build_state_freshness", build_state_freshness)
+    monkeypatch.setattr(query_helpers, "is_explicit_generation_mismatch", lambda *args, **kwargs: False)
+    monkeypatch.setattr("contextor.mcp.analysis_jobs._latest_analysis_job", lambda _root: None)
+    return engine
+
+
+def test_d4c_default_missing_semantics_is_deferred():
+    state = RepositoryAnalysisState(cycle_semantics=None, cycle_semantics_state="deferred")
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "deferred"
+
+
+def test_d4c_no_snapshot_cannot_claim_fresh():
+    state = RepositoryAnalysisState(cycle_semantics=None, cycle_semantics_state="fresh")
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "unavailable"
+
+
+def test_d4c_current_semantics_fresh_with_generation_proof():
+    state = _semantic_state()
+    assert fingerprint_hard_edges(state.dependency_graph.hard_edges) == state.cycle_semantics.graph_sha256
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "fresh"
+
+
+def test_d4c_unverified_generation_cannot_claim_fresh():
+    assert query_helpers._cycle_semantics_family_freshness(
+        _semantic_state(), generation_coherent=False,
+    ) == "unavailable"
+
+
+def test_d4c_graph_drift_marks_semantics_stale():
+    state = _semantic_state()
+    snapshot = state.cycle_semantics
+    state.dependency_graph = ProjectGraph(hard_edges={"pkg.a": set()}, soft_edges={})
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"
+    assert state.cycle_semantics is snapshot
+    assert snapshot.graph_sha256 == fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}})
+
+
+def test_d4c_semantic_stale_independent_of_cycles():
+    state = _semantic_state(marker="stale")
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"
+    assert state.cycles_state == "fresh"
+
+
+def test_d4c_resync_fail_closed():
+    state = _semantic_state()
+    state.resync_required = True
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"
+
+
+def test_d4c_malformed_evidence_is_unavailable():
+    state = _semantic_state()
+    state.cycle_semantics = {"graph_sha256": state.cycle_semantics.graph_sha256}
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "unavailable"
+
+
+def test_d4c_legacy_state_remains_deferred():
+    state = RepositoryAnalysisState()
+    for name in ("cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"):
+        delattr(state, name)
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=False) == "deferred"
+
+
+def test_d4c_public_envelope_includes_new_family(tmp_path, monkeypatch):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    state = _semantic_state()
+    engine = _install_real_freshness(tmp_path, monkeypatch, state)
+    def fail(*args, **kwargs):
+        raise AssertionError("semantic materializer called")
+    monkeypatch.setattr("contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail)
+    fresh = build_state_freshness(tmp_path, state, engine=engine)
+    assert fresh["families"]["cycle_semantics"] == "fresh"
+    assert fresh["families"]["cycles"] == "fresh"
+    assert {"module", "graph", "topology", "artifact_consumption", "collisions", "lineage"} <= set(fresh["families"])
+    engine.state_manager.revision = 76
+    unverified = build_state_freshness(tmp_path, state, engine=engine)
+    assert unverified["families"]["cycle_semantics"] == "unavailable"
+
+
+def test_d4c_reader_reports_historical_and_live_separately(tmp_path, monkeypatch):
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    state = _semantic_state(marker="stale")
+    _install_real_freshness(tmp_path, monkeypatch, state)
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["reports"]["cycle_semantics"] == report
+    assert result["reports"]["cycle_semantics"]["semantic_evidence"]["freshness_at_report_generation"] == "fresh"
+    assert result["live_state"]["state_freshness"]["families"]["cycle_semantics"] == "stale"
+    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
+    assert result["reports"]["cycle_semantics"]["publication_binding"]["live_revision"] is None
+
+
+def test_d4c_no_semantic_source_io(tmp_path, monkeypatch):
+    report = _historical_report()
+    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
+    state = _semantic_state()
+    snapshot = state.cycle_semantics
+    _install_real_freshness(tmp_path, monkeypatch, state)
+    def fail(*args, **kwargs):
+        raise AssertionError("semantic source access or recomputation")
+    monkeypatch.setattr("contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail)
+    monkeypatch.setattr("contextor.core.cycle_semantics.source_cohort.build_cycle_source_cohort", fail)
+    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "fresh"
+    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
+    assert result["reports"]["cycle_semantics"] == report
+    assert result["live_state"]["state_freshness"]["families"]["cycle_semantics"] == "fresh"
+    assert state.cycle_semantics is snapshot
```
