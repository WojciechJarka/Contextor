# TASK
CONTEXTOR_B0G4C38E3A_SEMANTIC_FAIL_CLOSED_AND_VIEW_HARDENING

# HEAD_BEFORE
8e41396e65f2a64074fffe649907461c70f7823e

# HEAD_AFTER
8e41396e65f2a64074fffe649907461c70f7823e

# GIT_STATUS
`M contextor/mcp/cycle_semantics_views.py`; `M tests/mcp/tools/test_get_project_architecture_full_reports.py`; `M walkthrough.md` (this report). No Git mutation. `git diff --check` passed for the two changed code/test files; Git printed CRLF conversion advisories but no whitespace error.

# CONTEXTOR_DISCOVERY_COVERAGE
DIRECT_EVIDENCE: Contextor MCP documentation was consulted for implementation, lineage, edit-context, LIVE-event, and blast-radius tools. `get_symbol_implementation` returned complete, source-synchronized implementations of `live_cycle_semantic_diagnostics`, `project_historical_cycle_semantics`, `analyze_cycle_activation_view`, `build_cycle_evidence_digest`, and `CycleSemanticsSnapshot` at canonical revision 539. Both target files had fresh syntax checks with no errors. Contextor identified `contextor.mcp.cycle_semantics_views` as adapter-owned, with two direct consumers (`contextor.mcp.tools.get_project_architecture` and the focused test module), 38 transitive consumers, and no layer violations. Canonical lineage resolved the LIVE diagnostic symbol. Planned and actual changes were restricted to the two allowed files below. The existing contracts matched the auditor's instructions.

# ROOT_CAUSE_FALSE_NEGATIVE
CODE_PATH_PROVED: The previous `False` branch checked only `coverage_status == FILESYSTEM_STABLE_NON_ATOMIC`. That status establishes source coverage, while the existing pure evidence retained unresolved lexical/activation classifications. The fixture had two unresolved lexical edges, yet the prior branch produced `False`. This was an unsupported negative conclusion.

# ROOT_CAUSE_MUTABLE_ALIASING
CODE_PATH_PROVED: Overview construction copied selected top-level dictionaries but passed nested values from `report_header`, `publication_binding`, `semantic_evidence`, projection metadata, and projection summary by reference. Mutating a returned overview could mutate the loaded historical report. Full view's exact pass-through and diagnostic view's copy-before-redaction behavior were already correct.

# FILES_CHANGED
- `C:\Temp\Contextor_Repo\contextor\mcp\cycle_semantics_views.py`
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_project_architecture_full_reports.py`

# FULL_DIFFS
Complete actual working-tree diff for every changed production/test file follows. `walkthrough.md` is excluded from its own diff.

```diffdiff --git a/contextor/mcp/cycle_semantics_views.py b/contextor/mcp/cycle_semantics_views.py
index adf21d2..801669b 100644
--- a/contextor/mcp/cycle_semantics_views.py
+++ b/contextor/mcp/cycle_semantics_views.py
@@ -43,6 +43,8 @@ _OVERVIEW_EVIDENCE_FIELDS = (
     "observed_source_count",
     "unobserved_source_count",
     "source_issues",
+    "snapshot_schema_version",
+    "invalidation_reason",
     "source_snapshot_binding",
     "runtime_execution_status",
 )
@@ -249,12 +251,12 @@ def project_historical_cycle_semantics(
     overview_projection = None
     if projection is not None:
         overview_projection = {
-            field: projection[field]
+            field: deepcopy(projection[field])
             for field in _OVERVIEW_PROJECTION_FIELDS
             if field in projection
         }
         overview_projection["summary"] = {
-            field: summary[field]
+            field: deepcopy(summary[field])
             for field in (
                 "cyclic_scc_total",
                 "cyclic_scc_returned",
@@ -294,10 +296,10 @@ def project_historical_cycle_semantics(
         "materialized_projection_components_truncated": original_truncated,
     }
     if component is not None:
-        presentation["component_selection"] = selection_metadata
+        presentation["component_selection"] = deepcopy(selection_metadata)
 
     result = {
-        key: report[key]
+        key: deepcopy(report[key])
         for key in (
             "schema_version",
             "status",
@@ -308,7 +310,7 @@ def project_historical_cycle_semantics(
         if key in report
     }
     result["semantic_evidence"] = {
-        key: evidence[key]
+        key: deepcopy(evidence[key])
         for key in _OVERVIEW_EVIDENCE_FIELDS
         if key in evidence
     }
@@ -489,19 +491,37 @@ def live_cycle_semantic_diagnostics(
         raise ValueError("Unresolved lexical edge count is invalid")
 
     complete = snapshot.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
+    lexical_complete = (
+        unresolved == 0
+        and all(
+            component.unresolved_edges == 0
+            for component in activation.components
+        )
+        and all(
+            component.unresolved_edge_count == 0
+            for component in components
+        )
+    )
     status = "fresh" if complete else "partial"
     attention = (
         True
         if direct_count > 0
         else False
-        if complete
+        if complete and lexical_complete
         else None
     )
-    reason = (
-        None
-        if complete
-        else "Canonical semantic evidence has partial source coverage; absence of direct cycles is unproven."
-    )
+    if not complete:
+        reason = (
+            "Canonical semantic evidence has partial source coverage; "
+            "absence of direct cycles is unproven."
+        )
+    elif not lexical_complete and direct_count == 0:
+        reason = (
+            "Canonical semantic evidence has unresolved lexical activation "
+            "classifications; absence of direct cycles is unproven."
+        )
+    else:
+        reason = None
 
     return {
         "status": status,
diff --git a/tests/mcp/tools/test_get_project_architecture_full_reports.py b/tests/mcp/tools/test_get_project_architecture_full_reports.py
index c3c79bb..a9a747d 100644
--- a/tests/mcp/tools/test_get_project_architecture_full_reports.py
+++ b/tests/mcp/tools/test_get_project_architecture_full_reports.py
@@ -9,6 +9,7 @@ import pytest
 from contextor import mcp_server
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.core.cycle_semantics.contracts import fingerprint_hard_edges
+from contextor.core.cycle_semantics.edge_sites import LexicalEdgeSite
 from contextor.core.domain.graph import ProjectGraph
 from contextor.mcp.query_helpers import build_state_freshness
 from contextor.mcp import query_helpers
@@ -495,6 +496,10 @@ def test_cycle_semantics_overview_omits_edges_and_witness_chains(tmp_path, monke
     assert projected["semantic_evidence"]["observed_source_count"] == report[
         "semantic_evidence"
     ]["observed_source_count"]
+    assert projected["semantic_evidence"]["snapshot_schema_version"] == report[
+        "semantic_evidence"
+    ]["snapshot_schema_version"]
+    assert projected["semantic_evidence"]["invalidation_reason"] is None
     assert projected["projection"]["summary"] == report["projection"]["summary"]
     assert "source_fingerprints" not in projected["semantic_evidence"]
     component = projected["projection"]["components"][0]
@@ -521,6 +526,46 @@ def test_reduced_historical_views_do_not_mutate_loaded_report():
         assert report == original
 
 
+def test_overview_mutable_values_are_independent_of_historical_report():
+    report = _historical_report()
+    report["report_header"]["nested"] = {"items": ["original"]}
+    report["publication_binding"]["nested"] = {"items": ["original"]}
+    report["semantic_evidence"]["source_issues"] = [
+        {"module": "pkg.a", "details": ["original"]}
+    ]
+    report["projection"]["selection_scope"] = {"items": ["original"]}
+    report["projection"]["summary"]["cyclic_scc_total"] = {
+        "items": ["original"]
+    }
+    original = deepcopy(report)
+
+    overview, error = project_historical_cycle_semantics(
+        report, view="overview", component=None,
+    )
+    assert error is None
+    overview["report_header"]["nested"]["items"].append("changed")
+    overview["publication_binding"]["nested"]["items"].append("changed")
+    overview["semantic_evidence"]["source_issues"][0]["details"].append("changed")
+    overview["projection"]["selection_scope"]["items"].append("changed")
+    overview["projection"]["summary"]["cyclic_scc_total"]["items"].append("changed")
+    overview["projection"]["components"][0]["members"].append("changed")
+
+    assert report == original
+
+
+def test_historical_overview_preserves_invalidation_reason():
+    report = _historical_report()
+    report["semantic_evidence"]["invalidation_reason"] = "GRAPH_CHANGED"
+    overview, error = project_historical_cycle_semantics(
+        report, view="overview", component=None,
+    )
+    assert error is None
+    assert overview["semantic_evidence"]["invalidation_reason"] == "GRAPH_CHANGED"
+    assert overview["semantic_evidence"]["snapshot_schema_version"] == report[
+        "semantic_evidence"
+    ]["snapshot_schema_version"]
+
+
 def test_cycle_semantics_component_selection_is_bounded_and_preserves_total(
     tmp_path,
     monkeypatch,
@@ -812,6 +857,44 @@ def _semantic_state(*, marker="fresh"):
     return state
 
 
+def _snapshot_with_lexical_sites(*, activation_scope):
+    snapshot = _snapshot()
+    component = snapshot.import_sites.components[0]
+    edges = tuple(
+        replace(
+            edge,
+            status="LEXICAL_CANDIDATES",
+            sites=(LexicalEdgeSite(
+                ordinal=index,
+                line=index + 1,
+                column=0,
+                form="IMPORT",
+                match_kind="DIRECT_MODULE",
+                requested_name=edge.target,
+                matched_member=None,
+                scopes=(),
+                controls=(),
+                activation_scope=activation_scope,
+            ),),
+        )
+        for index, edge in enumerate(component.internal_edges)
+    )
+    sites = replace(
+        snapshot.import_sites,
+        components=(replace(
+            component,
+            internal_edges=edges,
+            matched_edge_count=len(edges),
+            unresolved_edge_count=0,
+        ),),
+    )
+    discovery = replace(
+        snapshot.conditional_discovery,
+        unresolved_lexical_edge_count=0,
+    )
+    return replace(snapshot, import_sites=sites, conditional_discovery=discovery)
+
+
 def _install_real_freshness(tmp_path, monkeypatch, state):
     engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
     engine.state = state
@@ -931,11 +1014,54 @@ def test_live_semantic_diagnostics_uses_positive_current_snapshot_gate(
     assert semantic["cyclic_scc_count"] == 1
     assert semantic["cyclic_module_count"] == 2
     assert semantic["unresolved_lexical_edge_count"] == 2
-    assert semantic["direct_candidate_attention_required"] is False
+    assert semantic["direct_candidate_attention_required"] is None
+    assert "unresolved lexical activation" in semantic["reason"]
     assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
     assert result["live_state"]["diagnostics_attention_required"] is False
 
 
+def test_live_semantic_diagnostics_resolved_lexical_absence_allows_false(
+    tmp_path, monkeypatch,
+):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    state = _semantic_state()
+    state.cycle_semantics = _snapshot_with_lexical_sites(
+        activation_scope="FUNCTION_SCOPED",
+    )
+    _install_real_freshness(tmp_path, monkeypatch, state)
+
+    semantic = _read_architecture(tmp_path)["live_state"][
+        "cycle_semantic_diagnostics"
+    ]
+    assert semantic["status"] == "fresh"
+    assert semantic["unguarded_direct_cyclic_scc_count"] == 0
+    assert semantic["unresolved_lexical_edge_count"] == 0
+    assert semantic["direct_candidate_attention_required"] is False
+    assert semantic["reason"] is None
+    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_live_semantic_diagnostics_unrecognized_activation_blocks_false(
+    tmp_path, monkeypatch,
+):
+    _install_runtime(tmp_path, monkeypatch, _small_bundle())
+    state = _semantic_state()
+    state.cycle_semantics = _snapshot_with_lexical_sites(
+        activation_scope="UNKNOWN_SCOPE",
+    )
+    _install_real_freshness(tmp_path, monkeypatch, state)
+
+    semantic = _read_architecture(tmp_path)["live_state"][
+        "cycle_semantic_diagnostics"
+    ]
+    assert semantic["status"] == "fresh"
+    assert semantic["unguarded_direct_cyclic_scc_count"] == 0
+    assert semantic["unresolved_lexical_edge_count"] == 0
+    assert semantic["direct_candidate_attention_required"] is None
+    assert "unresolved lexical activation" in semantic["reason"]
+    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
+
+
 def test_live_semantic_diagnostics_partial_coverage_never_infers_absence(
     tmp_path,
     monkeypatch,
@@ -967,7 +1093,7 @@ def test_live_semantic_diagnostics_retains_positive_partial_evidence(
     monkeypatch,
 ):
     _install_runtime(tmp_path, monkeypatch, _small_bundle())
-    snapshot = _snapshot()
+    snapshot = _snapshot_with_lexical_sites(activation_scope="MODULE_TOP_LEVEL")
     partial_snapshot = replace(
         snapshot,
         observed_source_fingerprints=snapshot.observed_source_fingerprints[:1],
@@ -977,20 +1103,13 @@ def test_live_semantic_diagnostics_retains_positive_partial_evidence(
     state = _semantic_state()
     state.cycle_semantics = partial_snapshot
     _install_real_freshness(tmp_path, monkeypatch, state)
-    monkeypatch.setattr(
-        "contextor.mcp.cycle_semantics_views.build_cycle_evidence_digest",
-        lambda *_args: SimpleNamespace(components=(SimpleNamespace(
-            members=partial_snapshot.cyclic_modules,
-            category="UNGUARDED_DIRECT_CYCLIC_SUBGRAPH",
-        ),)),
-    )
-
     semantic = _read_architecture(tmp_path)["live_state"][
         "cycle_semantic_diagnostics"
     ]
     assert semantic["status"] == "partial"
     assert semantic["unguarded_direct_cyclic_scc_count"] == 1
     assert semantic["direct_candidate_attention_required"] is True
+    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
 
 
 @pytest.mark.parametrize(
```

# LEXICAL_COMPLETENESS_DECISION_TABLE
| Direct cyclic SCC count | Source coverage complete | Conditional unresolved count | Activation unresolved count | Digest unresolved count | Attention |
| --- | --- | --- | --- | --- | --- |
| >0 | either | any | any | any | `true` |
| 0 | yes | 0 | all 0 | all 0 | `false` |
| 0 | no | any | any | any | `null` |
| 0 | yes | any nonzero | any | any | `null` |
| 0 | yes | 0 | any nonzero | any | `null` |
| 0 | yes | 0 | all 0 | any nonzero | `null` |

# ATTENTION_TRUE_FALSE_NULL_GATES
`direct_candidate_attention_required=true` requires a positive direct cyclic SCC in the pure digest. `false` requires complete source coverage and zero unresolved counters in conditional discovery, every activation component, and every digest component. All other zero-direct cases return `null`. A fresh semantic result with unresolved activation evidence retains `status=fresh` and includes an explicit reason explaining that direct-cycle absence is unproven. The runtime execution field remains `UNKNOWN_NOT_EVALUATED`. Structural `diagnostics_attention_required` and SCC category calculations were not changed.

# HISTORICAL_VIEW_COPY_PROOF
Reduced overview now deep-copies each included mutable report value, semantic evidence value, projection metadata value, projection summary value, component field, and selection metadata. The regression mutates nested data in returned `report_header`, `publication_binding`, `source_issues`, projection metadata/summary, and component membership, then verifies the input report is unchanged. Diagnostic view retains its full initial deepcopy before fingerprint redaction. Full view retains exact pass-through semantics. No loaded historical report is mutated.

# OVERVIEW_EVIDENCE_FIELDS
Added `snapshot_schema_version` and `invalidation_reason` to the overview whitelist. The output retains their exact historical values, including null, from `semantic_evidence`. Existing coverage, source issues, publication binding, runtime unknown status, and overview detail restrictions remain. Overview still excludes source fingerprints, detailed edges, and witness chains.

# TARGETED_TEST_RESULTS
Command: `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\mcp\tools\test_get_project_architecture_full_reports.py`
Result after final edit: `67 passed, 1 warning in 12.99s`. The warning was an Authlib deprecation warning from the installed dependency. Cases now cover unresolved lexical evidence with complete source coverage => null; fully resolved function-scoped lexical evidence => false; real pure positive direct cyclic evidence => true; partial coverage => null; unrecognized activation => null; historical overview fields and nested copy isolation; diagnostic/full compatibility; unknown runtime safety. No full suite or FULL analysis was run.

# LIVE_REVISION_BEFORE_AFTER
Before edit: revision 539, activity epoch `324f298b8a8041d8a89181c4a03b83d1`, `resync_required=false`. After watcher processing: revision 542, same epoch, `resync_required=false`.

# WATCHER_EVENT
DIRECT_EVIDENCE: Continuous `get_live_events(after_revision=539)` feed showed desktop watcher `UPDATED` for `contextor/mcp/cycle_semantics_views.py` at revision 540, focused test at revision 541, and the final production adjustment at revision 542. No event-retention gap or forced update was reported.

# WORKSPACE_SYNC
At revision 542, target-specific `get_file_edit_context` reported `workspace_sync=verified` for both changed files, canonical state fresh, syntax diagnostics `checked_and_none`, and no warnings. This verifies on-disk bytes match the current canonical file tracking. `families.cycle_semantics=stale` remains a separate semantic-materialization state.

# STRUCTURAL_CYCLES
16 fresh structural DFS cycle diagnostics before and after. This is not an all-simple-cycles count and is not a runtime-safety conclusion.

# NAME_COLLISIONS
0 fresh name collisions before and after, per Contextor LIVE diagnostic summary.

# MCP_BACKEND_RESTART_REQUIRED
Yes. E3 serving MCP backend still predates the E3 implementation, and this E3A production edit also requires code adoption. No process was restarted in this task.

# SERVING_RUNTIME_ADOPTION_STATUS
Pending MCP backend reload and subsequent runtime verification. Focused tests executed current source; they do not prove the running MCP process adopted it. The current canonical cycle-semantics family remains stale, so current LIVE semantic SCC totals are not certified here.

# E2_PUBLICATION_TIMEOUT_REMAINS_OPEN
The E2 timed-out publication record remains separate and unresolved. This correction did not retry, publish, or alter it.

# FINAL_VERDICT
E3A_SOURCE_PASS_PENDING_RUNTIME

All three focused source-contract corrections and targeted tests passed. Both allowed files synchronized at revision 542; structural diagnostics remained fresh with 16 cycles and 0 collisions. Serving runtime adoption and fresh LIVE semantic materialization remain pending.
