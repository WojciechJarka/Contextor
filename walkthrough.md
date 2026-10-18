# TASK
CONTEXTOR_B0G4C38D3A_FULL_SEMANTIC_FRESHNESS_AND_TIMING_HARDENING

HEAD_BEFORE=732c2203745ffe36e82051313e1542d6ac097c6e
HEAD_AFTER=732c2203745ffe36e82051313e1542d6ac097c6e
GIT_STATUS=Before D3A: facade.py, lifecycle.py, walkthrough.md modified and test_cycle_semantics_full_integration.py untracked from completed C38D3. After D3A: same path status. No Git mutation.
PRECHECK=DIRECT_EVIDENCE: Contextor workspace_sync=verified for facade, lifecycle, source_cohort, runtime_trace and test at LIVE revision 503. Exact classifier, shared FULL, trace_event, and test implementations inspected. Source cohort emits exactly the eight specified reasons. Pre-existing C38D3 changes were uncommitted at task start; D3A changes only the three approved source/test paths.
CONTEXTOR_DISCOVERY_COVERAGE=Contextor MCP documentation, get_symbol_implementation for classify_full_cycle_semantics, build_cycle_source_cohort, trace_event, ContextorFacade and timing test; get_live_events and get_file_edit_context for post-edit architecture and synchronization. Git/source used only for literal anchors and diffs after Contextor.
FILES_CHANGED=contextor/core/cycle_semantics/lifecycle.py; contextor/core/api/facade.py; tests/test_cycle_semantics_full_integration.py
ALL_SOURCE_ISSUE_REASONS=MISSING_OR_INVALID_CANONICAL_PATH; SOURCE_UNREADABLE; SOURCE_FILE_LIMIT; SOURCE_COHORT_BYTE_LIMIT; INVALID_CANONICAL_FINGERPRINT; CANONICAL_FINGERPRINT_MISMATCH; SOURCE_NOT_COMPILABLE; SOURCE_CHANGED_DURING_READ. Verified directly in source_cohort.py.
EXHAUSTIVE_CLASSIFIER_CONTRACT=Source drift first; authority unavailable second; unknown issue and unexplained partial deferred; recognized bounded partial and complete issue-free evidence fresh. Strict CycleSemanticsSnapshot type check retained. D2 invalidation set unchanged.
UNKNOWN_REASON_FAIL_CLOSED=UNKNOWN_FUTURE_SOURCE_ISSUE retained in immutable snapshot and classified deferred, alone and with SOURCE_FILE_LIMIT.
SOURCE_DRIFT_PRECEDENCE=CANONICAL_FINGERPRINT_MISMATCH plus unknown reason classified stale/SOURCE_CHANGED.
PARTIAL_COVERAGE_POLICY=SOURCE_FILE_LIMIT, SOURCE_COHORT_BYTE_LIMIT and SOURCE_NOT_COMPILABLE classified fresh/None while coverage remains PARTIAL_SOURCE_EVIDENCE; partial with zero explaining issues classified deferred/None.
ACYCLIC_FRESHNESS=Valid complete empty cyclic topology remained fresh/None through synthetic FULL.
SEMANTIC_TIMER_SOURCE=Only CYCLE_SEMANTICS_MATERIALIZATION timer changed from time.monotonic to time.perf_counter_ns; start remains outside try, measurement remains in finally. Runtime_trace.py unchanged.
INNER_MATERIALIZER_DURATION=Run 1: 4.57209 ms; run 2: 3.896445 ms by independent perf_counter_ns wrapper.
OUTER_FULL_PHASE_DURATION=Run 1: 4.605822 ms; run 2: 3.926267 ms in raw FULL trace_event fields; both status=fresh, count=2, reason=NONE.
TRACE_DURATION_CONSISTENCY=PASS: both outer durations numeric, nonzero and greater than corresponding inner durations (differences 0.033732 ms and 0.029822 ms); tolerance 0.05 ms condition passed.
TARGETED_TEST_RESULTS=61 passed in 17.74s for the four approved test files. After adding the eighth source issue parameter, exact affected test node ran again: 3 passed in 1.71s. Production diffs passed git diff --check. No full suite or real Contextor FULL analysis.
REPEATED_TIMING_TEST_RESULTS=Exact test_d3_full_materializer_called_once run separately twice: run 1 1 passed in 1.80s, outer 4.605822 ms / inner 4.57209 ms; run 2 1 passed in 1.78s, outer 3.926267 ms / inner 3.896445 ms.
LIVE_AUTHORITY_BEFORE_AFTER=Stable: repo_id ctx_8efc50d8; root C:\Temp\Contextor_Repo; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 88e879fa630c41299f7ba675009e267f; lease_generation 32; service_pid 7840; process_start_identity 134367770052413468; endpoint_fingerprint e73abe0959388d48a8c7608c2d13ed8e150314242e23433d2a0c3b36ab316770.
LIVE_REVISION_BEFORE_AFTER=503 -> 507.
ACTIVITY_EPOCH_BEFORE_AFTER=6b4c9554981b4b779b705089dac32739 -> same.
EVENT_CONTINUITY=continuous; resync_required=false. desktop_watcher UPDATED lifecycle.py at 504, facade.py at 505, test file at 506 and final test-file edit at 507.
WORKSPACE_SYNC=verified for all three approved paths at revision 507; syntax checked_and_none.
COLLISIONS_BEFORE_AFTER=0 -> 0, fresh.
STRUCTURAL_CYCLES_BEFORE_AFTER=16 -> 16, fresh.
NEW_IMPORT_CYCLES=none observed in fresh canonical diagnostics.
RUNTIME_CODE_ADOPTION_STATUS=UNKNOWN_UNTIL_RELOAD_VERIFIED: watcher source synchronization does not establish running process code adoption.
MCP_SERVER_RESTART_REQUIRED=NO_AUTOMATIC_RESTART_IN_THIS_STAGE
DESKTOP_LIVE_RESTART_REQUIRED=YES_BEFORE_PRODUCTION_ACTIVATION
FINAL_VERDICT=B0G4C38D3A_PASS for focused source/test and LIVE source-sync scope. No runtime adoption claim.

# FULL_DIFFS
The following are complete actual Git working-tree diffs against HEAD. Because the C38D3 baseline was uncommitted before D3A, these diffs also contain pre-existing C38D3 hunks; no C38D3 source was newly changed outside the three approved D3A paths.
~~~diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 3ea2f0a..a76ec5d 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -768,6 +768,79 @@ class ContextorFacade:
 
         emit_stage_end("metrics", metrics_started)
 
+        cycle_semantics = None
+        cycle_semantics_state = "deferred"
+        cycle_semantics_invalidation_reason = None
+        semantic_started_ns = time.perf_counter_ns()
+
+        try:
+            from contextor.core.cycle_semantics.materialization import (
+                materialize_cycle_semantics,
+            )
+            from contextor.core.cycle_semantics.lifecycle import (
+                classify_full_cycle_semantics,
+            )
+
+            cycle_semantics = materialize_cycle_semantics(
+                path,
+                graph.hard_edges,
+                {
+                    module_id: module.path
+                    for module_id, module in modules.items()
+                },
+                index.source_fingerprints_by_module,
+            )
+
+            (
+                cycle_semantics_state,
+                cycle_semantics_invalidation_reason,
+            ) = classify_full_cycle_semantics(
+                cycle_semantics
+            )
+
+        except AnalysisCancelled:
+            raise
+
+        except Exception as exc:
+            cycle_semantics = None
+            cycle_semantics_state = "deferred"
+            cycle_semantics_invalidation_reason = None
+
+            if log:
+                log(
+                    "Warning: cycle-semantic materialization "
+                    "unavailable ("
+                    + type(exc).__name__
+                    + ")."
+                )
+
+            trace_event(
+                "FULL",
+                "CYCLE_SEMANTICS_MATERIALIZATION_ERROR",
+                status="deferred",
+                exception_class=type(exc).__name__,
+            )
+
+        finally:
+            trace_event(
+                "FULL",
+                "CYCLE_SEMANTICS_MATERIALIZATION",
+                elapsed_ms=(
+                    time.perf_counter_ns()
+                    - semantic_started_ns
+                ) / 1_000_000.0,
+                status=cycle_semantics_state,
+                count=(
+                    len(cycle_semantics.cyclic_modules)
+                    if cycle_semantics is not None
+                    else 0
+                ),
+                reason=(
+                    cycle_semantics_invalidation_reason
+                    or "NONE"
+                ),
+            )
+
         from datetime import datetime
         datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
@@ -989,6 +1062,13 @@ class ContextorFacade:
                 topology_metrics_state="fresh",
                 cycles=getattr(analysis_result, "cycles", []),
                 cycles_state="fresh",
+                cycle_semantics=cycle_semantics,
+                cycle_semantics_state=(
+                    cycle_semantics_state
+                ),
+                cycle_semantics_invalidation_reason=(
+                    cycle_semantics_invalidation_reason
+                ),
                 collision_facts=cf if isinstance(cf, dict) else {},
                 collisions=canonical_collisions,
                 collisions_state=collisions_state,
diff --git a/contextor/core/cycle_semantics/lifecycle.py b/contextor/core/cycle_semantics/lifecycle.py
index 0496f01..ec041d5 100644
--- a/contextor/core/cycle_semantics/lifecycle.py
+++ b/contextor/core/cycle_semantics/lifecycle.py
@@ -12,6 +12,77 @@ boundaries.
 
 from __future__ import annotations
 
+from .contracts import CycleSemanticsSnapshot
+
+
+FULL_SOURCE_DRIFT_ISSUES = frozenset({
+    "CANONICAL_FINGERPRINT_MISMATCH",
+    "SOURCE_CHANGED_DURING_READ",
+})
+
+FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES = frozenset({
+    "MISSING_OR_INVALID_CANONICAL_PATH",
+    "SOURCE_UNREADABLE",
+    "INVALID_CANONICAL_FINGERPRINT",
+})
+
+FULL_SOURCE_BOUNDED_EVALUATION_ISSUES = frozenset({
+    "SOURCE_FILE_LIMIT",
+    "SOURCE_COHORT_BYTE_LIMIT",
+    "SOURCE_NOT_COMPILABLE",
+})
+
+
+def classify_full_cycle_semantics(
+    snapshot: CycleSemanticsSnapshot,
+) -> tuple[str, str | None]:
+    """Classify FULL evidence freshness, not completeness.
+
+    A source mismatch cannot be marked fresh.
+
+    Missing source authority cannot certify freshness.
+
+    Bounded or otherwise explicitly incomplete
+    evaluation may still be a current diagnostic.
+
+    The snapshot itself always preserves its
+    explicit source coverage and issue details.
+    """
+
+    if type(snapshot) is not CycleSemanticsSnapshot:
+        raise TypeError(
+            "Expected CycleSemanticsSnapshot"
+        )
+
+    reasons = {
+        reason
+        for _, reason in snapshot.source_issues
+    }
+
+    if reasons & FULL_SOURCE_DRIFT_ISSUES:
+        return "stale", "SOURCE_CHANGED"
+
+    if reasons & FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES:
+        return "deferred", None
+
+    classified_reasons = (
+        FULL_SOURCE_DRIFT_ISSUES
+        | FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES
+        | FULL_SOURCE_BOUNDED_EVALUATION_ISSUES
+    )
+
+    if reasons - classified_reasons:
+        return "deferred", None
+
+    if (
+        snapshot.coverage_status
+        == "PARTIAL_SOURCE_EVIDENCE"
+        and not reasons
+    ):
+        return "deferred", None
+
+    return "fresh", None
+
 
 CYCLE_SEMANTICS_INVALIDATION_REASONS = frozenset({
     "SOURCE_CHANGED",

diff --git a/tests/test_cycle_semantics_full_integration.py b/tests/test_cycle_semantics_full_integration.py
new file mode 100644
index 0000000..ba2eb5b
--- /dev/null
+++ b/tests/test_cycle_semantics_full_integration.py
@@ -0,0 +1,298 @@
+"""Synthetic FULL integration of canonical cycle semantics evidence."""
+
+from __future__ import annotations
+
+import hashlib
+from dataclasses import replace
+from pathlib import Path
+from time import perf_counter_ns
+
+import pytest
+
+from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
+from contextor.core.cycle_semantics.contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
+from contextor.core.cycle_semantics.edge_sites import CyclicImportSiteReport
+from contextor.core.cycle_semantics.lifecycle import classify_full_cycle_semantics
+from contextor.core.cycle_semantics.materialization import materialize_cycle_semantics
+from contextor.core.errors import AnalysisCancelled
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state.store import read_metadata
+from contextor.core.paths import repo_cache_dir
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+@pytest.fixture
+def pair_repo(tmp_path, isolated_dirs, monkeypatch) -> Path:
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    package = root / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_text("", encoding="utf-8")
+    (package / "a.py").write_text("import pkg.b\ndef fa():\n    return 1\n", encoding="utf-8")
+    (package / "b.py").write_text("import pkg.a\ndef fb():\n    return 2\n", encoding="utf-8")
+    return root
+
+
+def _run_full(root: Path) -> tuple[RepositoryAnalysisState, object]:
+    errors, result = ContextorFacade.analyze_project(str(root))
+    assert all(error.kind == "ArchitectureCycle" for error in errors), errors
+    assert result is not None
+    metadata = read_metadata(repo_cache_dir(root))
+    assert metadata is not None
+    state = load_engine_state(
+        str(repo_cache_dir(root)), metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(root.resolve()),
+    )
+    assert isinstance(state, RepositoryAnalysisState)
+    return state, result
+
+
+def _partial_snapshot(root: Path, reason: str) -> CycleSemanticsSnapshot:
+    index = index_repository(str(root))
+    edges = {
+        "pkg.__init__": set(), "pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"},
+    }
+    complete = materialize_cycle_semantics(
+        root, edges,
+        {module_id: module.path for module_id, module in index.modules.items()},
+        index.source_fingerprints_by_module,
+    )
+    assert complete.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+    return replace(
+        complete,
+        observed_source_fingerprints=complete.observed_source_fingerprints[1:],
+        source_issues=((complete.cyclic_modules[0], reason),),
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+    )
+
+
+def test_d3_complete_full_cycle_materialization(pair_repo) -> None:
+    state, _ = _run_full(pair_repo)
+    snapshot = state.cycle_semantics
+    assert isinstance(snapshot, CycleSemanticsSnapshot)
+    assert state.cycle_semantics_state == "fresh"
+    assert state.cycle_semantics_invalidation_reason is None
+    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
+    assert len(snapshot.import_sites.topology.cyclic_components) == 1
+    assert snapshot.graph_sha256 == fingerprint_hard_edges(state.dependency_graph.hard_edges)
+    assert snapshot.source_issues == ()
+    assert snapshot.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+    assert snapshot.observed_source_count == 2
+    assert dict(snapshot.observed_source_fingerprints) == {
+        module: hashlib.sha256((pair_repo / "pkg" / f"{module[-1]}.py").read_bytes()).hexdigest()
+        for module in snapshot.cyclic_modules
+    }
+    assert snapshot.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+    assert snapshot.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+    assert state.cycles_state == "fresh" and state.cycles
+
+
+def test_d3_full_acyclic_repository(pair_repo) -> None:
+    (pair_repo / "pkg" / "b.py").write_text("def fb():\n    return 2\n", encoding="utf-8")
+    state, _ = _run_full(pair_repo)
+    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
+    assert state.cycle_semantics.cyclic_modules == ()
+    assert state.cycle_semantics.source_issues == ()
+    assert state.cycle_semantics_state == "fresh"
+    assert state.cycle_semantics_invalidation_reason is None
+    assert state.cycles == [] and state.cycles_state == "fresh"
+
+
+@pytest.mark.parametrize("reason", [
+    "CANONICAL_FINGERPRINT_MISMATCH", "SOURCE_CHANGED_DURING_READ",
+])
+def test_d3_classify_source_drift_as_stale(pair_repo, reason) -> None:
+    snapshot = _partial_snapshot(pair_repo, reason)
+    assert classify_full_cycle_semantics(snapshot) == ("stale", "SOURCE_CHANGED")
+    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+
+
+@pytest.mark.parametrize("reason", [
+    "SOURCE_FILE_LIMIT", "SOURCE_COHORT_BYTE_LIMIT", "SOURCE_NOT_COMPILABLE",
+])
+def test_d3_classify_bounded_partial_as_fresh(pair_repo, reason) -> None:
+    snapshot = _partial_snapshot(pair_repo, reason)
+    assert classify_full_cycle_semantics(snapshot) == ("fresh", None)
+    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+
+
+def test_d3a_unknown_source_issue_is_not_fresh(pair_repo) -> None:
+    snapshot = _partial_snapshot(pair_repo, "UNKNOWN_FUTURE_SOURCE_ISSUE")
+    assert snapshot.source_issues == (("pkg.a", "UNKNOWN_FUTURE_SOURCE_ISSUE"),)
+    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)
+
+
+def test_d3a_unexplained_partial_coverage_is_not_fresh(pair_repo) -> None:
+    snapshot = replace(
+        _partial_snapshot(pair_repo, "SOURCE_FILE_LIMIT"),
+        source_issues=(),
+    )
+    assert isinstance(snapshot, CycleSemanticsSnapshot)
+    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+    assert snapshot.unobserved_source_count == 1
+    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)
+
+
+def test_d3a_unknown_issue_combined_with_bounded_limit(pair_repo) -> None:
+    snapshot = replace(
+        _partial_snapshot(pair_repo, "SOURCE_FILE_LIMIT"),
+        observed_source_fingerprints=(),
+        source_issues=(
+            ("pkg.a", "SOURCE_FILE_LIMIT"),
+            ("pkg.b", "UNKNOWN_FUTURE_SOURCE_ISSUE"),
+        ),
+    )
+    assert snapshot.source_issues == tuple(sorted(set(snapshot.source_issues)))
+    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)
+
+
+def test_d3a_source_drift_precedes_unknown_reason(pair_repo) -> None:
+    snapshot = replace(
+        _partial_snapshot(pair_repo, "CANONICAL_FINGERPRINT_MISMATCH"),
+        observed_source_fingerprints=(),
+        source_issues=(
+            ("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH"),
+            ("pkg.b", "UNKNOWN_FUTURE_SOURCE_ISSUE"),
+        ),
+    )
+    assert classify_full_cycle_semantics(snapshot) == ("stale", "SOURCE_CHANGED")
+
+
+def test_d3a_complete_empty_cycle_remains_fresh(pair_repo) -> None:
+    (pair_repo / "pkg" / "b.py").write_text("def fb():\n    return 2\n", encoding="utf-8")
+    state, _ = _run_full(pair_repo)
+    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
+    assert state.cycle_semantics.cyclic_modules == ()
+    assert classify_full_cycle_semantics(state.cycle_semantics) == ("fresh", None)
+
+
+@pytest.mark.parametrize("reason", [
+    "SOURCE_UNREADABLE", "MISSING_OR_INVALID_CANONICAL_PATH",
+    "INVALID_CANONICAL_FINGERPRINT",
+])
+def test_d3_classify_authority_unavailable_as_deferred(pair_repo, reason) -> None:
+    snapshot = _partial_snapshot(pair_repo, reason)
+    assert classify_full_cycle_semantics(snapshot) == ("deferred", None)
+
+
+def test_d3_failed_materialization_keeps_full_available(pair_repo, monkeypatch) -> None:
+    def fail(*args, **kwargs):
+        raise ValueError("synthetic materializer failure")
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail,
+    )
+    state, _ = _run_full(pair_repo)
+    assert state.cycles_state == "fresh" and state.cycles
+    assert state.cycle_semantics is None
+    assert state.cycle_semantics_state == "deferred"
+    assert state.cycle_semantics_invalidation_reason is None
+
+
+def test_d3_full_materializer_called_once(pair_repo, monkeypatch) -> None:
+    import contextor.core.api.facade as facade_module
+    import contextor.core.cycle_semantics.materialization as materialization
+    original = materialization.materialize_cycle_semantics
+    calls = []
+    durations_ms = []
+    semantic_events = []
+    original_trace = facade_module.trace_event
+    def collect_trace(domain, event, **fields):
+        if event == "CYCLE_SEMANTICS_MATERIALIZATION":
+            semantic_events.append(dict(fields))
+        return original_trace(domain, event, **fields)
+    def counted(root, edges, paths, fingerprints):
+        calls.append((root, edges, paths, fingerprints))
+        started = perf_counter_ns()
+        try:
+            return original(root, edges, paths, fingerprints)
+        finally:
+            durations_ms.append((perf_counter_ns() - started) / 1_000_000)
+    monkeypatch.setattr(facade_module, "trace_event", collect_trace)
+    monkeypatch.setattr(materialization, "materialize_cycle_semantics", counted)
+    state, _ = _run_full(pair_repo)
+    assert len(calls) == 1
+    root, edges, paths, fingerprints = calls[0]
+    assert Path(root).resolve() == pair_repo.resolve()
+    assert fingerprint_hard_edges(edges) == fingerprint_hard_edges(state.dependency_graph.hard_edges)
+    assert set(paths) == set(state.modules)
+    assert set(fingerprints) == set(paths)
+    assert all(fingerprints[module] for module in paths)
+    assert len(semantic_events) == 1
+    assert semantic_events[0]["status"] == "fresh"
+    assert semantic_events[0]["count"] == 2
+    assert isinstance(semantic_events[0]["elapsed_ms"], (int, float))
+    assert semantic_events[0]["elapsed_ms"] > 0
+    assert semantic_events[0]["elapsed_ms"] >= durations_ms[0] - 0.05
+    print("D3_SYNTHETIC_SEMANTIC_EVENT", semantic_events[0])
+    print("D3_SYNTHETIC_MATERIALIZER_MS", durations_ms[0])
+
+
+def test_d3_full_snapshot_persistence_roundtrip(pair_repo, monkeypatch) -> None:
+    state, _ = _run_full(pair_repo)
+    import contextor.core.cycle_semantics.materialization as materialization
+    def fail(*args, **kwargs):
+        raise AssertionError("load must not rematerialize")
+    monkeypatch.setattr(materialization, "materialize_cycle_semantics", fail)
+    metadata = read_metadata(repo_cache_dir(pair_repo))
+    loaded = load_engine_state(
+        str(repo_cache_dir(pair_repo)), metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=str(pair_repo.resolve()),
+    )
+    assert loaded.cycle_semantics == state.cycle_semantics
+    assert isinstance(loaded.cycle_semantics.import_sites, CyclicImportSiteReport)
+    assert isinstance(loaded.cycle_semantics.conditional_discovery, ConditionalDiscoveryReport)
+    assert loaded.cycle_semantics_state == state.cycle_semantics_state
+    assert loaded.cycles == state.cycles
+
+
+def test_d3_incremental_update_invalidates_full_evidence(pair_repo) -> None:
+    state, _ = _run_full(pair_repo)
+    assert state.cycle_semantics_state == "fresh"
+    hydrated = hydrate_repository_engine(pair_repo)
+    assert hydrated is not None
+    engine = hydrated.engine
+    evidence = engine.state.cycle_semantics
+    assert isinstance(evidence, CycleSemanticsSnapshot)
+    assert engine.state.cycle_semantics_state == "fresh"
+    source = pair_repo / "pkg" / "a.py"
+    source.write_text("import pkg.b\ndef fa():\n    return 10\n", encoding="utf-8")
+    result = engine.update_file(str(source.resolve()))
+    assert result.status in {"UPDATED", "UNCHANGED"}
+    assert engine.state.cycle_semantics is evidence
+    assert engine.state.cycle_semantics_state == "stale"
+    assert engine.state.cycle_semantics_invalidation_reason == "SOURCE_CHANGED"
+    assert engine.state.cycles_state == "fresh"
+
+
+def test_d3_full_does_not_execute_indexed_python(pair_repo) -> None:
+    (pair_repo / "pkg" / "a.py").write_text(
+        "import pkg.b\nraise RuntimeError('should not execute')\n", encoding="utf-8",
+    )
+    state, _ = _run_full(pair_repo)
+    assert isinstance(state.cycle_semantics, CycleSemanticsSnapshot)
+    assert state.cycle_semantics.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_d3_full_cancellation_not_swallowed(pair_repo, monkeypatch) -> None:
+    def cancel(*args, **kwargs):
+        raise AnalysisCancelled()
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", cancel,
+    )
+    with pytest.raises(AnalysisCancelled):
+        ContextorFacade.analyze_project(str(pair_repo))
+
+
+def test_d3_report_contract_unchanged(pair_repo) -> None:
+    state, result = _run_full(pair_repo)
+    output = pair_repo.parent / "output"
+    reports = sorted(output.rglob("*.json"))
+    assert reports
+    assert state.cycles_state == "fresh" and state.cycles
+    assert result.cycles == state.cycles
+    assert all("cycle_semantics" not in report.read_text(encoding="utf-8") for report in reports)
~~~

