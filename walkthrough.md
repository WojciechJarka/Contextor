# L32E Graph-Derived Freshness Trust Gate

CURRENT_HEAD=7ebfadcab722e9c7492f0ebd04a4c645d1e04660
WORKTREE_BEFORE_EDITS=clean

## CONTEXTOR_MCP_DISCOVERY

- Contextor LIVE revision observed: 139; canonical_state=fresh; provenance=live.
- Contextor returned workspace_sync=verified for the complete implementations retrieved from materialization.py and graph.py. Source was checked before edits; no claim is made that the live backend loaded these new edits.
- Exact owners: ensure_topology_analytics at materialization.py:121-161 before edits; ensure_cycles at :211-245; materialize_incremental_state calls them at :563 and :565 respectively.
- get_symbol_call_context confirms materialize_incremental_state as the direct caller of both functions. ProjectGraph is a frozen dataclass in contextor/core/domain/graph.py with hard_edges and soft_edges typed as dict[str, set[str]]. The dataclass does not enforce those annotations at runtime.
- diagnostics_summary_for_state is the relevant public diagnostic projection for cycles: it emits a count only when the cycles family is fresh. The resync regression now checks its result after ensure_cycles.
- This helper checks the documented container shape only. It does not certify source-to-graph semantic correctness.

## SOURCE_DRIFT_CHECK

Git HEAD matched the discovered source. Before edits, git status was clean and git diff for the three scoped files was empty. Literal source anchors were confirmed with git show HEAD and rg. No production source outside contextor/core/analysis/incremental/materialization.py was changed.

## PRE_FIX_RED_RESULTS

Exact new-test run against HEAD before the production patch: 12 failed, 8 passed, 1 external Authlib warning, 5.39s. The failures were:

- topology resync-required: deferred and fresh-populated;
- topology malformed graph: hard_edges not dict, soft_edges not dict, hard-edge targets not set;
- topology missing graph: previously fresh;
- cycles resync-required: deferred and fresh-populated;
- cycles malformed graph: hard_edges not dict, soft_edges not dict, hard-edge targets not set;
- cycles missing graph: previously fresh.

The eight passing cases established the unaffected branches: deferred with absent graph stays deferred, valid deferred recomputation matches the independent oracle, and valid stale/fresh payloads are preserved for both families.

## PATCH

Added _canonical_graph_structure_valid with the exact ProjectGraph structural checks required by the task. Both ensure functions now gate before fresh early returns: resync invalidates the marker and returns; missing graph invalidates only a previously fresh marker and returns; malformed graph invalidates the marker and returns. All these paths preserve payload identity and skip computation. Valid graph behavior remains unchanged; no artifact_consumption freshness dependency was added. The patch does not inspect or alter parse freshness / last-known-good state, so it does not equate parse-stale with resync_required.

## POST_FIX_NEW_TESTS

20 passed, 1 external Authlib warning, 3.75s.

## TARGETED_REGRESSION_GATE

Command covered only the six requested files:

- tests/test_topology_bootstrap_and_consumer_truth.py
- tests/test_cycles_live_lifecycle.py
- tests/test_graph_only_live_analytics.py
- tests/test_cached_facts_live_analytics.py
- tests/test_mcp_incremental_hydration.py
- tests/test_mcp_diagnostics.py

Result: 139 passed, 1 external AuthlibDeprecationWarning, 28.84s. No full repository pytest run was performed. git diff --check exited 0; Git emitted only line-ending conversion notices (LF to CRLF).

## FILES_CHANGED

- contextor/core/analysis/incremental/materialization.py
- tests/test_topology_bootstrap_and_consumer_truth.py
- tests/test_cycles_live_lifecycle.py

RESTART_AND_RUNTIME_LIMIT

No Desktop/LIVE/MCP restart or runtime certification was performed. The MCP discovery describes the pre-edit source at revision 139. The focused test gate certifies the edited Python behavior in pytest only; runtime exposure requires the normal service reload outside this task.

REMAINING_RISKS

- The validator enforces graph edge-map structure, not graph freshness against source truth; this is the explicitly limited contract.
- The task's six-file test gate passed, but repository-wide tests were intentionally not run.
- No live runtime reload was performed.

FINAL_VERDICT=FOCUSED_PASS

## FULL_DIFFS

`diff
diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py
index a3c8a01..ff26d73 100644
--- a/contextor/core/analysis/incremental/materialization.py
+++ b/contextor/core/analysis/incremental/materialization.py
@@ -118,6 +118,30 @@ def ensure_module_usages(state: RepositoryAnalysisState) -> None:
             )
 
 
+def _canonical_graph_structure_valid(state: RepositoryAnalysisState) -> bool:
+    graph = getattr(state, "dependency_graph", None)
+    if graph is None:
+        return False
+
+    for field_name in ("hard_edges", "soft_edges"):
+        edges = getattr(graph, field_name, None)
+        if not isinstance(edges, dict):
+            return False
+
+        for source, targets in edges.items():
+            if not isinstance(source, str) or not source:
+                return False
+            if not isinstance(targets, set):
+                return False
+            if any(
+                not isinstance(target, str) or not target
+                for target in targets
+            ):
+                return False
+
+    return True
+
+
 def ensure_topology_analytics(state: RepositoryAnalysisState) -> None:
     """
     Ensures state.topology_analytics is fresh and complete from canonical graph.
@@ -131,6 +155,19 @@ def ensure_topology_analytics(state: RepositoryAnalysisState) -> None:
     if not hasattr(state, "topology_analytics") or state.topology_analytics is None:
         state.topology_analytics = {}
 
+    if getattr(state, "resync_required", False):
+        state.topology_metrics_state = "stale"
+        return
+
+    if getattr(state, "dependency_graph", None) is None:
+        if state.topology_metrics_state == "fresh":
+            state.topology_metrics_state = "stale"
+        return
+
+    if not _canonical_graph_structure_valid(state):
+        state.topology_metrics_state = "stale"
+        return
+
     # A. Fresh + populated analytics: preserve, zero recomputation
     if state.topology_metrics_state == "fresh" and state.topology_analytics:
         return
@@ -222,6 +259,19 @@ def ensure_cycles(state: RepositoryAnalysisState) -> None:
     if not hasattr(state, "cycles") or state.cycles is None:
         state.cycles = []
 
+    if getattr(state, "resync_required", False):
+        state.cycles_state = "stale"
+        return
+
+    if getattr(state, "dependency_graph", None) is None:
+        if state.cycles_state == "fresh":
+            state.cycles_state = "stale"
+        return
+
+    if not _canonical_graph_structure_valid(state):
+        state.cycles_state = "stale"
+        return
+
     # A. Fresh state: preserve, zero recomputation (even if cycles == [])
     if state.cycles_state == "fresh":
         return
diff --git a/tests/test_cycles_live_lifecycle.py b/tests/test_cycles_live_lifecycle.py
index 1b927b3..d1b6f08 100644
--- a/tests/test_cycles_live_lifecycle.py
+++ b/tests/test_cycles_live_lifecycle.py
@@ -456,3 +456,131 @@ def test_soft_edges_ignored_for_cycles():
 
     assert state.cycles_state == "fresh"
     assert state.cycles == []
+
+
+@pytest.mark.parametrize(
+    "marker,cycles",
+    [
+        ("deferred", [["previous", "cycle"]]),
+        ("fresh", [["a", "b", "a"]]),
+    ],
+    ids=["deferred", "fresh-populated"],
+)
+def test_cycles_lose_freshness_and_preserve_payload_when_resync_required(
+    marker, cycles
+):
+    from contextor.core.diagnostics_projection import diagnostics_summary_for_state
+
+    graph = ProjectGraph(hard_edges={"a": {"b"}, "b": {"a"}}, soft_edges={})
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        cycles_state=marker,
+        cycles=cycles,
+    )
+    state.resync_required = True
+    previous = state.cycles
+
+    with patch("contextor.core.graph.cycles.detect_cycles", return_value=[]) as compute:
+        ensure_cycles(state)
+        diagnostics = diagnostics_summary_for_state(state)
+
+    assert state.cycles_state == "stale"
+    assert state.cycles is previous
+    compute.assert_not_called()
+    assert diagnostics["cycles"] == {"count": None, "availability": "stale"}
+
+
+@pytest.mark.parametrize(
+    "graph",
+    [
+        pytest.param(ProjectGraph(hard_edges=[], soft_edges={}), id="hard-edges-not-dict"),
+        pytest.param(ProjectGraph(hard_edges={}, soft_edges=[]), id="soft-edges-not-dict"),
+        pytest.param(
+            ProjectGraph(hard_edges={"a": ["b"]}, soft_edges={}),
+            id="hard-edge-targets-not-set",
+        ),
+    ],
+)
+def test_cycles_malformed_graph_stales_without_recomputation(graph):
+    previous = [["previous", "cycle"]]
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        cycles_state="deferred",
+        cycles=previous,
+    )
+
+    with patch("contextor.core.graph.cycles.detect_cycles", return_value=[]) as compute:
+        ensure_cycles(state)
+
+    assert state.cycles_state == "stale"
+    assert state.cycles is previous
+    compute.assert_not_called()
+
+
+@pytest.mark.parametrize(
+    "marker,cycles,expected_marker",
+    [
+        ("deferred", [], "deferred"),
+        ("fresh", [["a", "b", "a"]], "stale"),
+    ],
+    ids=["deferred-remains-deferred", "fresh-becomes-stale"],
+)
+def test_cycles_missing_graph_does_not_compute_or_discard_payload(
+    marker, cycles, expected_marker
+):
+    state = RepositoryAnalysisState(
+        dependency_graph=None,
+        cycles_state=marker,
+        cycles=cycles,
+    )
+    previous = state.cycles
+
+    with patch("contextor.core.graph.cycles.detect_cycles", return_value=[]) as compute:
+        ensure_cycles(state)
+
+    assert state.cycles_state == expected_marker
+    assert state.cycles is previous
+    compute.assert_not_called()
+
+
+def test_cycles_valid_deferred_matches_independent_compute_oracle():
+    hard_edges = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
+    graph = ProjectGraph(hard_edges=hard_edges, soft_edges={})
+    expected = detect_cycles(hard_edges)
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        cycles_state="deferred",
+        cycles=[["previous", "cycle"]],
+    )
+
+    ensure_cycles(state)
+
+    assert state.cycles_state == "fresh"
+    assert state.cycles == expected
+
+
+@pytest.mark.parametrize(
+    "marker,cycles",
+    [
+        ("stale", [["previous", "stale"]]),
+        ("fresh", []),
+    ],
+    ids=["stale-preserved", "fresh-empty-preserved"],
+)
+def test_cycles_valid_graph_preserves_certified_markers_and_payload_identity(
+    marker, cycles
+):
+    graph = ProjectGraph(hard_edges={"a": {"b"}, "b": set()}, soft_edges={})
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        cycles_state=marker,
+        cycles=cycles,
+    )
+    previous = state.cycles
+
+    with patch("contextor.core.graph.cycles.detect_cycles", return_value=[["x"]]) as compute:
+        ensure_cycles(state)
+
+    assert state.cycles_state == marker
+    assert state.cycles is previous
+    compute.assert_not_called()
diff --git a/tests/test_topology_bootstrap_and_consumer_truth.py b/tests/test_topology_bootstrap_and_consumer_truth.py
index 6fb0a10..5496518 100644
--- a/tests/test_topology_bootstrap_and_consumer_truth.py
+++ b/tests/test_topology_bootstrap_and_consumer_truth.py
@@ -427,3 +427,152 @@ def test_ensure_topology_analytics_lifecycle_invariants():
     ensure_topology_analytics(state_cached)
     assert state_cached.topology_metrics_state == "fresh"
     assert state_cached.cached_analytics_state == "deferred"  # untouched!
+
+
+@pytest.mark.parametrize(
+    "marker,analytics",
+    [
+        ("deferred", {"previous": "keep"}),
+        ("fresh", {"pagerank": {"a": 1.0}}),
+    ],
+    ids=["deferred", "fresh-populated"],
+)
+def test_topology_loses_freshness_and_preserves_payload_when_resync_required(
+    marker, analytics
+):
+    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics
+
+    graph = ProjectGraph(hard_edges={"a": {"b"}, "b": set()}, soft_edges={})
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        topology_metrics_state=marker,
+        topology_analytics=analytics,
+    )
+    state.resync_required = True
+    previous = state.topology_analytics
+
+    with patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_topology_analytics",
+        return_value={"recomputed": True},
+    ) as compute:
+        ensure_topology_analytics(state)
+
+    assert state.topology_metrics_state == "stale"
+    assert state.topology_analytics is previous
+    compute.assert_not_called()
+
+
+@pytest.mark.parametrize(
+    "graph",
+    [
+        pytest.param(ProjectGraph(hard_edges=[], soft_edges={}), id="hard-edges-not-dict"),
+        pytest.param(ProjectGraph(hard_edges={}, soft_edges=[]), id="soft-edges-not-dict"),
+        pytest.param(
+            ProjectGraph(hard_edges={"a": ["b"]}, soft_edges={}),
+            id="hard-edge-targets-not-set",
+        ),
+    ],
+)
+def test_topology_malformed_graph_stales_without_recomputation(graph):
+    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics
+
+    previous = {"previous": "keep"}
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        topology_metrics_state="deferred",
+        topology_analytics=previous,
+    )
+
+    with patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_topology_analytics",
+        return_value={"recomputed": True},
+    ) as compute:
+        ensure_topology_analytics(state)
+
+    assert state.topology_metrics_state == "stale"
+    assert state.topology_analytics is previous
+    compute.assert_not_called()
+
+
+@pytest.mark.parametrize(
+    "marker,analytics,expected_marker",
+    [
+        ("deferred", {}, "deferred"),
+        ("fresh", {"pagerank": {"a": 1.0}}, "stale"),
+    ],
+    ids=["deferred-remains-deferred", "fresh-becomes-stale"],
+)
+def test_topology_missing_graph_does_not_compute_or_discard_payload(
+    marker, analytics, expected_marker
+):
+    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics
+
+    state = RepositoryAnalysisState(
+        dependency_graph=None,
+        topology_metrics_state=marker,
+        topology_analytics=analytics,
+    )
+    previous = state.topology_analytics
+
+    with patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_topology_analytics",
+        return_value={"recomputed": True},
+    ) as compute:
+        ensure_topology_analytics(state)
+
+    assert state.topology_metrics_state == expected_marker
+    assert state.topology_analytics is previous
+    compute.assert_not_called()
+
+
+def test_topology_valid_deferred_matches_independent_compute_oracle():
+    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics
+
+    hard_edges = {"a": {"b"}, "b": set()}
+    soft_edges = {"a": set(), "b": set()}
+    graph = ProjectGraph(hard_edges=hard_edges, soft_edges=soft_edges)
+    metrics = {}
+    expected = compute_topology_analytics(hard_edges, soft_edges, metrics)
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        metrics=metrics,
+        topology_metrics_state="deferred",
+        topology_analytics={"previous": "keep"},
+    )
+
+    ensure_topology_analytics(state)
+
+    assert state.topology_metrics_state == "fresh"
+    assert state.topology_analytics == expected
+
+
+@pytest.mark.parametrize(
+    "marker,analytics",
+    [
+        ("stale", {"previous": "stale"}),
+        ("fresh", {"pagerank": {"a": 1.0}}),
+    ],
+    ids=["stale-preserved", "fresh-preserved"],
+)
+def test_topology_valid_graph_preserves_certified_markers_and_payload_identity(
+    marker, analytics
+):
+    from contextor.core.analysis.incremental.materialization import ensure_topology_analytics
+
+    graph = ProjectGraph(hard_edges={"a": {"b"}, "b": set()}, soft_edges={})
+    state = RepositoryAnalysisState(
+        dependency_graph=graph,
+        topology_metrics_state=marker,
+        topology_analytics=analytics,
+    )
+    previous = state.topology_analytics
+
+    with patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_topology_analytics",
+        return_value={"recomputed": True},
+    ) as compute:
+        ensure_topology_analytics(state)
+
+    assert state.topology_metrics_state == marker
+    assert state.topology_analytics is previous
+    compute.assert_not_called()
```
